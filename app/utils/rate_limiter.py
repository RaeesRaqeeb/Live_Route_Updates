# app/utils/rate_limiter.py
import asyncio
import time
from collections import deque
from app.utils.logger import get_logger


logger = get_logger(__name__)


class GlobalGeminiLimiter:
    """
    Singleton rate limiter shared across the WHOLE app for Gemini calls.
    Tune `rpm` to match your actual quota tier — check the exact number
    in your 429 error message or at ai.google.dev/gemini-api/docs/rate-limits.
    """
    _instance = None

    def __new__(cls, rpm: int = 5):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init(rpm)
        return cls._instance

    def _init(self, rpm: int):
        self.rpm = rpm
        self.min_interval = 60.0 / rpm     # seconds required between calls
        self._lock = asyncio.Lock()
        self._last_call = 0.0

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            wait = self.min_interval - (now - self._last_call)
            if wait > 0:
                logger.debug(f"Gemini limiter: waiting {wait:.2f}s")
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()


groq_limiter = GlobalGeminiLimiter(rpm=20)   # ← match your real limit

class RateLimiter:
    """
    Async token-bucket rate limiter for web scraping.
    Prevents hammering a single domain and getting IP-banned.

    Usage:
        limiter = RateLimiter(max_calls=1, period=2.5)
        await limiter.acquire()   # Blocks if needed
    """

    def __init__(self, max_calls: int = 1, period: float = 2.0):
        self.max_calls = max_calls
        self.period = period          # Seconds between call bursts
        self._calls: deque = deque()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait if needed, then allow the call to proceed."""
        async with self._lock:
            now = time.monotonic()

            # Remove calls outside the window
            while self._calls and now - self._calls[0] >= self.period:
                self._calls.popleft()

            if len(self._calls) >= self.max_calls:
                # Need to wait
                sleep_time = self.period - (now - self._calls[0])
                if sleep_time > 0:
                    logger.debug(f"Rate limiter sleeping {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)

            self._calls.append(time.monotonic())


class DomainRateLimiter:
    """
    Per-domain rate limiter — each website gets its own independent limiter.
    Ensures dawn.com and geo.tv are throttled separately.
    """

    def __init__(self, max_calls: int = 1, period: float = 3.0):
        self.max_calls = max_calls
        self.period = period
        self._limiters: dict[str, RateLimiter] = {}

    def get_limiter(self, domain: str) -> RateLimiter:
        if domain not in self._limiters:
            self._limiters[domain] = RateLimiter(
                max_calls=self.max_calls,
                period=self.period,
            )
        return self._limiters[domain]

    async def acquire(self, url: str):
        """Acquire rate limit slot for the domain of this URL."""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        limiter = self.get_limiter(domain)
        await limiter.acquire()
        logger.debug(f"Acquired slot for domain: {domain}")