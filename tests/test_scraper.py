# tests/test_scraper.py
import pytest
from app.utils.text_cleaner import TextCleaner
from app.utils.rate_limiter import RateLimiter
import asyncio
import time


class TestTextCleaner:
    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_removes_advertisement(self):
        text = "Road blocked near Lahore.\nAdvertisement\nMore news below."
        cleaned = self.cleaner.clean(text)
        assert "Advertisement" not in cleaned
        assert "Road blocked" in cleaned

    def test_removes_extra_whitespace(self):
        text = "Some    news   about    roads."
        cleaned = self.cleaner.clean(text)
        assert "  " not in cleaned

    def test_handles_empty_string(self):
        assert self.cleaner.clean("") == ""

    def test_handles_none(self):
        assert self.cleaner.clean(None) == ""

    def test_truncate_respects_limit(self):
        long_text = "a" * 5000
        truncated = self.cleaner.truncate_for_llm(long_text, max_chars=3000)
        assert len(truncated) <= 3010   # Small buffer for "..."

    def test_removes_urls(self):
        text = "Check https://www.dawn.com/article/123 for details."
        cleaned = self.cleaner.clean(text)
        assert "https://" not in cleaned


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_first_call(self):
        limiter = RateLimiter(max_calls=1, period=1.0)
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1   # First call should be instant

    @pytest.mark.asyncio
    async def test_rate_limiter_delays_second_call(self):
        limiter = RateLimiter(max_calls=1, period=0.5)
        await limiter.acquire()
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.4   # Second call should be delayed