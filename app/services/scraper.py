import asyncio
import json
from typing import List, Dict, Any
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
import aiohttp # Required for fast API calls
from app.core.config import settings
from app.utils.logger import get_logger
from app.utils.rate_limiter import RateLimiter

logger = get_logger(__name__)

# # ── Pakistan-specific news sources ────────────────────────────────────────────
PAKISTAN_SOURCES = {
#     "dawn": "https://www.dawn.com/search?q={query}",
#     "geo": "https://www.geo.tv/latest-news?q={query}",
#     "ary": "https://arynews.tv/search/?q={query}",
#   "gbdma_fb_via_google": "https://www.google.com/search?q=site:facebook.com/p/Gilgit-Baltistan-Disaster-Management-Authority-100064570067356/+{query}",
    
    # Search inside the KKH Updates Facebook page using Google
    "kkh_fb_via_google": "https://www.google.com/search?q=site:facebook.com/p/KKH-Updates-100057494289275/+{query}",
    # "nhmp": "https://nhmp.gov.pk/latest-news",
    # "tribune": "https://tribune.com.pk/search?q={query}",
    # "pmd": "https://www.pmd.gov.pk/en/",
    # "NHMP":"https://beta.nhmp.gov.pk/ta/public/viewtravel.aspx",
    # "googl":"https://news.google.com/rss/search?q={query}",
    # Replace these:
"gbdma_fb_via_google": "https://www.google.com/search?q=site:facebook.com/...",
# With direct:
"gbdma_fb": "https://mbasic.facebook.com/p/Gilgit-Baltistan-Disaster-Management-Authority-100064570067356/",
"kkh_fb": "https://mbasic.facebook.com/p/KKH-Updates-100057494289275/",
}


# ── Direct FB pages - crawlable via mbasic ──
DIRECT_FB_SOURCES = {
    "gbdma_fb": "https://mbasic.facebook.com/p/Gilgit-Baltistan-Disaster-Management-Authority-100064570067356/",
    "kkh_fb": "https://mbasic.facebook.com/p/KKH-Updates-100057494289275/",
}

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
NHMP_API_BASE = "http://cpo.nhmp.gov.pk:6788"
NHMP_API_ENDPOINT = f"{NHMP_API_BASE}/api/TravelAdvisory/FilteredAdvisory"

ROAD_MAPPER = {
    ("rawalpindi", "skardu"): "S-1",
    ("islamabad", "skardu"): "S-1",
    ("islamabad", "gilgit"): "N-15",
    ("lahore", "islamabad"): "M-2",
}

def _get_fit_markdown(result) -> str:
    if hasattr(result, "markdown") and result.markdown:
        if getattr(result.markdown, "fit_markdown", None):
            return result.markdown.fit_markdown
        if getattr(result.markdown, "raw_markdown", None):
            return result.markdown.raw_markdown
    return getattr(result, "fit_markdown", "") or ""

class ScraperService:
    def __init__(self):
        self.rate_limiter = RateLimiter(max_calls=1, period=settings.SCRAPE_DELAY_SECONDS)
        self.browser_config = BrowserConfig(headless=True, verbose=False)
        self.run_config = CrawlerRunConfig(
            word_count_threshold=20,
            excluded_tags=["nav", "footer", "header", "script", "style"],
            magic=True,
        )
        self.serpapi_key = getattr(settings, "SERPAPI_API_KEY", "") or getattr(settings, "SERPAPI_KEY", "")

    def _build_serp_queries(self, origin: str, destination: str) -> List[Dict[str, str]]:
        o_d = f"{origin} {destination}".lower()
        base_rd = f"{origin} {destination} road closed landslide blocked"
        
        queries = []
        
        # SOST page is NOT in your hardcoded list, so we need generic site:facebook.com
        queries.append({
            "label": "fb_general_search",
            "q": f'site:facebook.com ({origin} OR {destination} OR "Karakoram Highway" OR "Jaglot Skardu Road") (blocked OR closed OR landslide)'
        })
        queries.append({
            "label": "kkh_gbdma_specific",
            "q": f'site:facebook.com ("KKH Updates" OR "Gilgit-Baltistan Disaster Management" OR SOST) {destination} road'
        })
        
        # Northern areas needs expanded terms
        if any(k in o_d for k in ["skardu", "gilgit", "hunza", "jaglot"]):
            queries.append({
                "label": "northern_roads",
                "q": f'"Karakoram Highway" OR "Jaglot Skardu Road" OR "S-1" OR Jutal OR "Goro Jaglot" landslide closed'
            })
        
        queries.append({"label": "google_news", "q": base_rd})
        return queries

    def _detect_road(self, origin: str, destination: str) -> str:
        o, d = origin.lower(), destination.lower()
        if (o, d) in ROAD_MAPPER: return ROAD_MAPPER[(o, d)]
        if (d, o) in ROAD_MAPPER: return ROAD_MAPPER[(d, o)]
        if any(k in o+d for k in ['skardu','gilgit','hunza']): return "S-1"
        return f"{origin} to {destination}"

    def _empty_result(self, src, err):
        return {"source": src, "url": "", "content": "", "scrape_success": False, "error": err}

    async def _fetch_nhmp_direct(self, origin: str, destination: str) -> Dict[str, Any]:
        road_name = self._detect_road(origin, destination)
        params = {"network": "Highway", "road": road_name, "section": f"{origin} to {destination}", "filter": "true"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(NHMP_API_ENDPOINT, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {"source": "NHMP_API", "url": str(resp.url), "content": json.dumps(data)[:4000], "scrape_success": True, "error": None}
                    return self._empty_result("NHMP_API", f"HTTP {resp.status}")
        except Exception as e:
            return self._empty_result("NHMP_API", str(e))

    async def _fetch_serpapi(self, query: str, label: str) -> Dict[str, Any]:
        if not self.serpapi_key:
            return self._empty_result(label, "SERPAPI_API_KEY missing")
        
        params = {
            "engine": "google",
            "q": query,
            "location": "Pakistan",
            "gl": "pk",
            "hl": "en",
            "num": 10,
            "api_key": self.serpapi_key
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(SERPAPI_ENDPOINT, params=params, timeout=15) as resp:
                    if resp.status != 200:
                        return self._empty_result(label, f"SerpAPI HTTP {resp.status}: {await resp.text()}")
                    data = await resp.json()
                    organic = data.get("organic_results", [])
                    if not organic:
                        return self._empty_result(label, f"No results for: {query}")
                    
                    # Format for LLM
                    blocks = []
                    for r in organic[:8]:
                        blocks.append(
                            f"Title: {r.get('title')}\n"
                            f"Link: {r.get('link')}\n"
                            f"Date: {r.get('date', 'N/A')}\n"
                            f"Snippet: {r.get('snippet')}\n"
                        )
                    content = "\n---\n".join(blocks)
                    logger.info(f"[SerpAPI:{label}] found {len(organic)} results for '{query}'")
                    return {"source": f"SERPAPI_{label}", "url": f"google search: {query}", "content": content, "scrape_success": True, "error": None}
        except Exception as e:
            logger.error(f"SerpAPI error {label}: {e}")
            return self._empty_result(label, str(e))

    async def scrape_single_source(self, crawler, source_name: str, url: str) -> Dict[str, Any]:
        try:
            await self.rate_limiter.acquire()
            result = await crawler.arun(url=url, config=self.run_config)
            content = _get_fit_markdown(result)
            if result.success and content:
                return {"source": source_name, "url": url, "content": content[:3000], "scrape_success": True, "error": None}
            return self._empty_result(source_name, "Empty Response")
        except Exception as e:
            return self._empty_result(source_name, str(e))

    async def scrape_route_news(self, origin: str, destination: str) -> List[Dict[str, Any]]:
        results = []
        
        # 1. NHMP
        results.append(await self._fetch_nhmp_direct(origin, destination))

        # 2. SerpAPI Google -> Facebook
        serp_queries = self._build_serp_queries(origin, destination)
        serp_tasks = [self._fetch_serpapi(q["q"], q["label"]) for q in serp_queries]
        serp_results = await asyncio.gather(*serp_tasks)
        results.extend(serp_results)

        # 3. Direct mbasic FB crawl
        semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_SCRAPERS)
        async def safe_scrape(crawler, name, url):
            async with semaphore:
                return await self.scrape_single_source(crawler, name, url)

        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            tasks = [safe_scrape(crawler, name, url) for name, url in DIRECT_FB_SOURCES.items()]
            fb_results = await asyncio.gather(*tasks)
            results.extend(fb_results)

        logger.info(f"Total Success: {len([r for r in results if r['scrape_success']])}/{len(results)}")
        return results

