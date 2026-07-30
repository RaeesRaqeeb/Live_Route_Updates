#app/services/scraper.py
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
    # "kkh_fb_via_google": "https://www.google.com/search?q=site:facebook.com/p/KKH-Updates-100057494289275/+{query}",
    # "nhmp": "https://nhmp.gov.pk/latest-news",
    # "tribune": "https://tribune.com.pk/search?q={query}",
    # "pmd": "https://www.pmd.gov.pk/en/",
    # "NHMP":"https://beta.nhmp.gov.pk/ta/public/viewtravel.aspx",
    # "googl":"https://news.google.com/rss/search?q={query}",
    # Replace these:
# "gbdma_fb_via_google": "https://www.google.com/search?q=site:facebook.com/...",
# With direct:
# "gbdma_fb": "https://mbasic.facebook.com/p/Gilgit-Baltistan-Disaster-Management-Authority-100064570067356/",
# "kkh_fb": "https://mbasic.facebook.com/p/KKH-Updates-100057494289275/",
}


# ── Direct FB pages - crawlable via mbasic ──
# DIRECT_FB_SOURCES = {
#     "gbdma_fb": "https://mbasic.facebook.com/p/Gilgit-Baltistan-Disaster-Management-Authority-100064570067356/",
#     "kkh_fb": "https://mbasic.facebook.com/p/KKH-Updates-100057494289275/",
# }

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
NHMP_API_BASE = "http://cpo.nhmp.gov.pk:6788"
NHMP_API_ENDPOINT = f"{NHMP_API_BASE}/api/TravelAdvisory/FilteredAdvisory"
GB_KKH_KEYWORDS = {"skardu", "gilgit", "hunza", "gb", "kkh","astore",'baltistan'}

NHMP_ROAD_MAP: dict[tuple[str, str], tuple[str, str, str]] = {
    ("islamabad", "peshawar"): ("Motorway", "M1/Motorway M-1", "Islamabad to Peshawar"),
    ("peshawar", "islamabad"): ("Highway", "N5/GT Road", "Peshawar to Islamabad"),

    ("lahore", "islamabad"): ("All", "M2/Motorway M-2", "Lahore to Islamabad"),
    ("islamabad", "lahore"): ("Highway", "N5/GT Road", "Islamabad to Lahore"),

    ("lahore", "abdul hakim"): ("Motorway", "M3/Motorway M-3", "Lahore to Abdul Hakim"),
    ("abdul hakim", "lahore"): ("Motorway", "M3/Motorway M-3", "Lahore to Abdul Hakim"),

    ("pindi bhattian", "multan"): ("Motorway", "M4/Motorway M-4", "Pindi Bhattian to Multan"),
    ("multan", "pindi bhattian"): ("Motorway", "M4/Motorway M-4", "Pindi Bhattian to Multan"),

    ("multan", "sukkur"): ("Motorway", "M5/Motorway M-5", "Multan to Sukkur"),
    ("sukkur", "multan"): ("Motorway", "M5/Motorway M-5", "Multan to Sukkur"),

    ("lahore", "multan"): ("Highway", "N5/GT Road", "Lahore to Multan"),
    ("multan", "lahore"): ("Highway", "N5/GT Road", "Lahore to Multan"),

    ("multan", "rahimyar khan"): ("Highway", "N5/GT Road", "Multan to Rahimyar Khan"),
    ("rahimyar khan", "multan"): ("Highway", "N5/GT Road", "Multan to Rahimyar Khan"),

    ("sukkur", "rahimyar khan"): ("Highway", "N5/GT Road", "Rahimyar Khan to Sukkur"),
    ("rahimyar khan", "sukkur"): ("Highway", "N5/GT Road", "Rahimyar Khan to Sukkur"),


    ("sukkur", "hyderabad"): ("Highway", "N5/GT Road", "Sukkur to Hyderabad"),
    ("hyderabad", "sukkur"): ("Highway", "N5/GT Road", "Sukkur to Hyderabad"),


    ("hyderabad", "karachi"): ("Motorway", "M9/Motorway M-9", "Hyderabad to Karachi"),
    ("karachi", "hyderabad"): ("Motorway", "M9/Motorway M-9", "Hyderabad to Karachi"),

    # NOTE: duplicate section name also exists under N5/GT Road — see below

    ("lahore", "sialkot"): ("Motorway", "M11/Lahore Sialkot Motorway", "Lahore to Sialkot"),
    ("sialkot", "lahore"): ("Motorway", "M11/Lahore Sialkot Motorway", "Lahore to Sialkot"),

    ("hakla", "dera ismail khan"): ("Motorway", "M14/Motorway M-14", "Hakla to Dera Ismail Khan"),
    ("dera ismail khan", "hakla"): ("Motorway", "M14/Motorway M-14", "Hakla to Dera Ismail Khan"),

    ("burhan", "thakot"): ("Motorway", "M15/Motorway M-15", "Burhan to Thakot"),
    ("thakot", "burhan"): ("Motorway", "M15/Motorway M-15", "Burhan to Thakot"),

    ("kernal sher khan", "swat"): ("Motorway", "M16/Swat Expressway", "Kernal Sher Khan to Swat"),
    ("swat", "kernal sher khan"): ("Motorway", "M16/Swat Expressway", "Kernal Sher Khan to Swat"),

    ("karachi", "karachi"): ("Expressway", "LEW/Lyari Expressway", "Karachi to Karachi"),

    ("gwadar", "makola"): ("Highway", "N10/Coastal Highway", "Gwadar to Makola"),
    ("makola", "gwadar"): ("Highway", "N10/Coastal Highway", "Gwadar to Makola"),

    ("hub", "uthal"): ("Highway", "N25/RDC Highway", "Hub to Uthal"),
    ("uthal", "hub"): ("Highway", "N25/RDC Highway", "Hub to Uthal"),

    ("kalat", "quetta"): ("Highway", "N25/RDC Highway", "Kalat to Quetta"),
    ("quetta", "kalat"): ("Highway", "N25/RDC Highway", "Kalat to Quetta"),

    ("quetta", "pishin"): ("Highway", "N25/RDC Highway", "Quetta to Pishin"),
    ("pishin", "quetta"): ("Highway", "N25/RDC Highway", "Quetta to Pishin"),

    ("kuchlak", "muslim bagh"): ("Highway", "N50/N-50", "Kuchlak to Muslim Bagh"),
    ("muslim bagh", "kuchlak"): ("Highway", "N50/N-50", "Kuchlak to Muslim Bagh"),

    ("sehwan", "ratodero"): ("Highway", "N55/Indus Highway", "Sehwan to Ratodero"),
    ("ratodero", "sehwan"): ("Highway", "N55/Indus Highway", "Sehwan to Ratodero"),

    ("islamabad", "murree"): ("Highway", "N75/IMDC", "Islamabad to Murree"),
    ("murree", "islamabad"): ("Highway", "N75/IMDC", "Islamabad to Murree"),
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

    def _detect_road(self, origin: str, destination: str) -> tuple[str, str, str] | None:
        """
        Returns (network, road, section) for NHMP's FilteredAdvisory API,
        or None if this route isn't tracked by NHMP (e.g. GB/KKH) — caller
        should skip the NHMP call entirely in that case, not just expect a 404.
        """
        o, d = origin.strip().lower(), destination.strip().lower()

        if any(k in o or k in d for k in GB_KKH_KEYWORDS):
            return None

        if (o, d) in NHMP_ROAD_MAP:
            return NHMP_ROAD_MAP[(o, d)]
        if (d, o) in NHMP_ROAD_MAP:
            return NHMP_ROAD_MAP[(d, o)]

        return None

    def _empty_result(self, src, err):
        return {"source": src, "url": "", "content": "", "scrape_success": False, "error": err}

    async def _fetch_nhmp_direct(self) -> Dict[str, Any]:

        # route = self._detect_road(origin, destination)
        # if route is None:
        #
        #     logger.info(f"{origin}->{destination} not in NHMP road list, skipping NHMP_API call")
        #     return self._empty_result("NHMP_API", "Route not tracked by NHMP")

        # network, road, section = route
        params = {"network": "All", "road": "All", "section": "All", "filter": "true"}
        check = False
        while(1):

            if (check):
                params = {"network": "All", "road": "All", "section": "All", "filter": "true"}

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(NHMP_API_ENDPOINT, params=params, timeout=10) as resp:

                        if resp.status == 200:
                            data = await resp.json()

                            return {"source": "NHMP_API", "url": str(resp.url), "content": json.dumps(data), "scrape_success": True, "error": None}


                        if resp.status == 404:
                            check = True
                            continue


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

    async def serpapi(self,origin:str,destination:str)-> List[Dict[str,Any]]:
        results=[]
        serp_queries = self._build_serp_queries(origin, destination)
        serp_tasks = [self._fetch_serpapi(q["q"], q["label"]) for q in serp_queries]
        serp_results = await asyncio.gather(*serp_tasks)
        results.extend(serp_results)
        logger.info(f"Total Success: {len([r for r in results if r['scrape_success']])}/{len(results)}")
        return results

    
    async def scrape_route_news(self, origin: str, destination: str) -> List[Dict[str, Any]]:
        results = []


        
        # 1. NHMP
        results.append(await self._fetch_nhmp_direct())

       
        

      

        logger.info(f"Total Success: {len([r for r in results if r['scrape_success']])}/{len(results)}")
        return results

