# # app/services/route_pipeline.py
# import hashlib
# from datetime import datetime, timezone, timedelta
# from typing import List, Dict, Any
#
# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession
# import json
# from datetime import datetime
#
# from app.models.route import Route
# from app.models.scrape_result import ScrapeResult
# from app.models.nhmp_closure import NHMPClosure
# from app.schemas.scrape import RawScrapeData
# from app.services.scraper import ScraperService
# from app.services.graph_api_service import GraphAPIService
# from app.services.llm_extractor import LLMExtractor
# from app.utils.logger import get_logger
# from app.services.corridor import get_corridor,is_relevant_post
# logger = get_logger(__name__)
#
# GB_KEYWORDS = ["skardu", "gilgit", "hunza", "kkh", "karakoram", "astore", "northern"]
#
#
# def _hash_content(content: str) -> str:
#     return hashlib.sha256(content.encode("utf-8")).hexdigest()
#
#
# def is_gb_route(origin: str, destination: str) -> bool:
#     origin = origin.lower()
#     # print("*"*20)
#     # print("Kai scene hai?")
#     # print("*"*20)
#
#     destination = destination.lower()
#     if ( origin in GB_KEYWORDS) or (destination in GB_KEYWORDS):
#         # print("*"*20)
#         # print("Kai scene hai?")
#         # print("*"*20)
#
#         return True
#     else :
#         return False
#
# # app/services/route_pipeline.py — fetch_raw_sources, revised
# async def fetch_raw_sources(origin, destination, scraper, graph_api):
#     results = []
#
#     # Always try the general/motorway scraper — M-15, general road network,
#     # NHMP data isn't exclusive to non-GB routes; Burhan/Thakot etc. sit on
#     # both an M-series motorway AND lead into a GB corridor.
#     try:
#         results.extend(await scraper.scrape_route_news(origin, destination))
#     except Exception as e:
#         logger.error(f"Scrape failed for {origin}->{destination}: {e}")
#
#     try:
#             fb_results = await graph_api.fetch_recent_posts(limit=5)
#             corridor = get_corridor(origin, destination)
#             fb_results = [
#                 r for r in fb_results
#                 if is_relevant_post(r.get("content", ""), origin, destination, corridor)
#             ]
#             results.extend(fb_results)
#     except Exception as e:
#             logger.error(f"Graph API fetch failed for {origin}->{destination}: {e}")
#
#     try:
#         results.extend(await scraper.serpapi(origin, destination))
#     except Exception as e:
#         logger.error(f"Scrape fallback failed for {origin}->{destination}: {e}")
#
#     print("*"*20)
#     print("All Results:",results)
#     print("*"*20)
#     exit()
#     return results
#
# def _row_to_dict(row: ScrapeResult) -> Dict[str, Any]:
#     """Shape matches what RAGService._normalize_docs expects (already-structured)."""
#     return {
#         "source": row.source_name,
#         "url": row.source_url,
#         "content": row.summary or row.raw_content,
#         "scrape_success": True,
#         "error": None,
#         "from_db": True,  # tells RAG: skip re-extraction, already structured
#         "headline": row.headline,
#         "issue_type": row.issue_type,
#         "severity": row.severity,
#         "route_affected": row.route_affected,
#         "summary": row.summary,
#         "created_at": row.created_at,
#     }
#
#
#
# def _parse_nhmp_date(date_str: str) -> datetime:
#     if not date_str:
#         return datetime.min
#     try:
#         return datetime.fromisoformat(date_str)
#     except ValueError:
#         return datetime.min
#
#
# from typing import List, Dict, Any
# import json
# from datetime import datetime
#
# def filter_latest_nhmp_closure(raw_json_string: str) -> List[Dict[str, Any]]:
#     """
#     Parses NHMP API JSON and returns a list of dictionaries containing structured alerts
#     (Road Closed, Weather Alert, etc.) sorted by newest first.
#     """
#     try:
#         api_response = json.loads(raw_json_string)
#         data_list = api_response.get("data", [])
#     except json.JSONDecodeError:
#         return []
#
#     if not data_list:
#         return []
#
#     # 1. Look for important alerts (closures, weather, diversions, etc.)
#     allowed_types = ["Road Closed"]
#
#     valid_alerts = [
#         item for item in data_list
#         if item.get("type") in allowed_types
#     ]
#
#     if not valid_alerts:
#         return []
#
#     # 2. Sort explicitly by real Datetime
#     valid_alerts.sort(key=lambda x: _parse_nhmp_date(x.get("createdOn", "")), reverse=True)
#
#     data = []
#
#     # 3. Create dictionaries instead of strings
#     for alert in valid_alerts:
#         route_str = alert.get('route', '')
#
#         try:
#             alert_origin, alert_destination = route_str.split(" to ")
#         except ValueError:
#             alert_origin, alert_destination = "Unknown", "Unknown"
#
#         clean_dict = {
#             "origin": alert_origin,
#             "destination": alert_destination,
#             "alert_type": alert.get('type'),
#             "sub_type": alert.get('subType'),
#             "route": route_str,
#             "from_place": alert.get('fromPlace'),
#             "to_place": alert.get('toPlace'),
#             "reported_at": alert.get('createdOn'),
#             "remarks": alert.get('remarks'),
#             "lane_closure": alert.get('laneClosure'),
#         }
#
#         data.append(clean_dict)
#
#     return data
#
# from typing import List, Tuple, Dict, Any
#
# async def batch_extract(
#         scraped_results: List[dict],
# ) -> List[Tuple[dict, Any]]: # Any allows both strings (for web scrapes) and dicts (for NHMP)
#     """
#     Extract structured data from all scraped results.
#     Returns a list of tuples: (raw_data_dict, cleaned_data)
#     """
#     valid_results = [
#         r for r in scraped_results
#         if r.get("scrape_success") and r.get("content")
#     ]
#
#     if not valid_results:
#         return []
#
#     extracted_pairs = []
#
#     for result in valid_results:
#         if result["source"] == "NHMP_API":
#             # This returns our new list of dictionaries
#             cleaned_list = filter_latest_nhmp_closure(result["content"])
#
#             # Loop through the list and add each alert individually
#             for cleaned_dict in cleaned_list:
#                 extracted_pairs.append((result, cleaned_dict))
#
#         else:
#             # Fallback for standard text scraping (if you add back LLM extractor)
#             cleaned = result["content"]
#             if not cleaned or len(cleaned) < 10:
#                 continue
#             extracted_pairs.append((result, cleaned))
#
#     return extracted_pairs
#
# import hashlib
# from datetime import datetime
# from typing import List, Dict, Any, Tuple
# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession
#
# async def scrape_extract_and_store(
#         session: AsyncSession,
#         route: Route,
#         scraper: ScraperService,
#         graph_api: GraphAPIService,
#         extractor: LLMExtractor,
#         commit: bool = True,
# ) -> Tuple[List[Dict[str, Any]], int]:
#
#     origin = "All"
#     destination = "All"
#
#     try:
#         raw_results = await fetch_raw_sources(origin, destination, scraper, graph_api)
#     except Exception as e:
#         logger.error(f"Issue getting data: {e}")
#         raw_results = []
#
#     structured_items: List[Dict[str, Any]] = []
#     to_extract: List[dict] = []
#     hash_by_source_url: Dict[str, str] = {}
#
#     for raw in raw_results[0]:
#         if not raw.get("scrape_success") or not raw.get("content"):
#             continue
#
#         content = raw["content"]
#         new_hash = _hash_content(content)
#
#         existing = await session.execute(
#             select(NHMPClosure).where(
#                 NHMPClosure.origin == origin,
#                 NHMPClosure.destination == destination,
#                 NHMPClosure.source == raw["source"],
#                 NHMPClosure.content_hash == new_hash,
#                 )
#         )
#
#         if existing.scalar_one_or_none():
#             logger.info(f"[skip] {raw['source']} unchanged for {origin}->{destination}")
#             continue
#
#         min_len = 15 if raw["source"] == "own_fb_page" else 30
#         if len(content.strip()) < min_len:
#             continue
#
#         key = f"{raw['source']}::{raw.get('url','')}"
#         hash_by_source_url[key] = new_hash
#         to_extract.append(raw)
#
#     if to_extract:
#         extracted_pairs = await batch_extract(to_extract)
#
#         # cleaned_data is now our dictionary for NHMP!
#         for raw, cleaned_data in extracted_pairs:
#             key = f"{raw['source']}::{raw.get('url','')}"
#             new_hash = hash_by_source_url[key]
#
#             if raw["source"] == "NHMP_API":
#
#                 # Safely parse the datetime string from the dictionary
#                 reported_at_str = cleaned_data.get("reported_at")
#                 reported_at = None
#                 if reported_at_str:
#                     try:
#                         reported_at = datetime.fromisoformat(reported_at_str)
#                     except ValueError:
#                         pass
#
#                 # Build the database row directly using dictionary keys! No Regex needed!
#                 nhmp_row = NHMPClosure(
#                     origin=cleaned_data.get("origin", origin),
#                     destination=cleaned_data.get("destination", destination),
#                     source=raw["source"],
#                     alert_type=cleaned_data.get("alert_type"),
#                     sub_type=cleaned_data.get("sub_type"),
#                     route_label=cleaned_data.get("route"),
#                     from_place=cleaned_data.get("from_place"),
#                     to_place=cleaned_data.get("to_place"),
#                     remarks=cleaned_data.get("remarks"),
#                     lane_closure=cleaned_data.get("lane_closure"),
#                     reported_at=reported_at,
#                     content_hash=new_hash,
#                 )
#                 session.add(nhmp_row)
#                 await session.flush()
#
#                 structured_items.append({
#                     "source": raw["source"],
#                     "alert_type": nhmp_row.alert_type,
#                     "route": nhmp_row.route_label,
#                     "from_db": False
#                 })
#
#             else:
#                 # Here we will manage the GB route information
#                 pass
#
#     if commit:
#         await session.commit()
#
#     return structured_items, 0



import hashlib
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.route import Route
from app.models.scrape_result import ScrapeResult
from app.models.nhmp_closure import NHMPClosure
from app.schemas.scrape import RawScrapeData
from app.services.scraper import ScraperService
from app.services.graph_api_service import GraphAPIService
from app.services.llm_extractor import LLMExtractor
from app.services.corridor import get_corridor, is_relevant_post
from app.utils.logger import get_logger

logger = get_logger(__name__)

GB_KEYWORDS = ["skardu", "gilgit", "hunza", "kkh", "karakoram", "astore", "northern"]


# ============================================================
#  Helpers
# ============================================================

def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def is_gb_route(origin: str, destination: str) -> bool:
    o, d = origin.lower(), destination.lower()
    return any(k in o or k in d for k in GB_KEYWORDS)


def _parse_iso(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


# ============================================================
#  Source-specific extractors
#
#  Each function receives one raw scrape dict and returns
#  a list of structured dicts ready to become ScrapeResult rows.
#
#  For structured sources (NHMP) we extract fields directly.
#  For text sources (Facebook, SERPAPI) we return the raw text
#  so the LLM extractor can process it later.
# ============================================================
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

def extract_nhmp(raw: dict) -> List[Dict[str, Any]]:
    try:
        api_response = json.loads(raw['content'])
        data_list = api_response.get('data', [])
    except (json.JSONDecodeError, KeyError):
        return []

    # FIX: Use offset-naive datetime to match your _parse_iso output
    cutoff_date = datetime.now() - timedelta(days=7)

    allowed_types = {'Road Closed', 'Weather Alert', 'Road Diversion'}

    valid = [item for item in data_list if item.get('type') in allowed_types]
    valid.sort(key=lambda x: _parse_iso(x.get('createdOn', '')) or datetime.min, reverse=True)

    items = []
    for alert in valid:
        reported_at = _parse_iso(alert.get('createdOn', ''))

        # Safe comparison now that both are naive
        if not reported_at or reported_at < cutoff_date:
            continue

        route_str = alert.get('route', '')
        parts = route_str.split('to')
        origin_name = parts[0].strip() if len(parts) == 2 else 'Unknown'
        dest_name = parts[1].strip() if len(parts) == 2 else 'Unknown'

        alert_json = json.dumps(alert, sort_keys=True)

        items.append({
            'source_type': 'NHMP_API',
            'origin': origin_name,
            'destination': dest_name,
            'alert_type': alert.get('type'),
            'sub_type': alert.get('subType'),
            'route_label': route_str,
            'from_place': alert.get('fromPlace'),
            'to_place': alert.get('toPlace'),
            'reported_at': reported_at,
            'lane_closure': alert.get('laneClosure'),
            'remarks': alert.get('remarks'),
            'raw_content': alert_json,
            'individual_hash': _hash_content(alert_json),
        })

    return items


def extract_text_source(raw: dict) -> List[Dict[str, Any]]:
    """Return text sources as-is for LLM extraction later."""
    content = (raw.get("content") or "").strip()
    if len(content) < 10:
        return []
    return [{
        "source_type": raw["source"],
        "raw_content": content,
        "url": raw.get("url"),
        "reported_at": _parse_iso(raw.get("post_created_at", "")),
    }]

def extract_nhmp_html(raw: dict) -> List[Dict[str, Any]]:
    """Dispatcher for the NHMP HTML page source."""
    html = raw.get("content", "")
    if not html:
        return []
    return parse_nhmp_html(html)


# ── Registry: add new sources here ─────────────────────────
SOURCE_EXTRACTORS: Dict[str, Any] = {
    "NHMP_API": extract_nhmp,
    "NHMP_HTML": extract_nhmp_html,
}

# Everything else falls back to text extraction
DEFAULT_EXTRACTOR = extract_text_source


# ============================================================
#  fetch_raw_sources — unchanged, already multi-source
# ============================================================

async def fetch_raw_sources(origin, destination, scraper, graph_api):
    results = []

    # NHMP HTML page  ← new
    try:
        results.extend(await scraper.scrape_nhmp_html())
        # print("*"*20)
        # print("HTML page:",results)
        # print("*"*20)
        # exit()
    except Exception as e:
        logger.error(f"NHMP HTML scrape failed: {e}")
        exit()
    # NHMP JSON API
    try:
        results.extend(await scraper.scrape_route_news(origin, destination))
    except Exception as e:
        logger.error(f"NHMP API scrape failed: {e}")



    # Facebook
    try:
        fb_results = await graph_api.fetch_recent_posts(limit=5)
        corridor = get_corridor(origin, destination)
        fb_results = [
            r for r in fb_results
            if is_relevant_post(r.get("content", ""), origin, destination, corridor)
        ]
        results.extend(fb_results)
    except Exception as e:
        logger.error(f"Graph API fetch failed: {e}")

    # SERPAPI
    try:
        results.extend(await scraper.serpapi(origin, destination))
    except Exception as e:
        logger.error(f"SERPAPI failed: {e}")

    return results
# ============================================================
#  batch_extract — source-agnostic, uses registry
# ============================================================

async def batch_extract(scraped_results: List[dict]) -> List[Tuple[dict, Dict[str, Any]]]:
    """
    Dispatch each raw scrape to its source-specific extractor.
    Returns list of (raw_dict, structured_dict) tuples.
    """
    extracted_pairs: List[Tuple[dict, Dict[str, Any]]] = []

    for raw in scraped_results:
        if not raw.get("scrape_success") or not raw.get("content"):
            continue

        source_name = raw.get("source", "")
        extractor = SOURCE_EXTRACTORS.get(source_name, DEFAULT_EXTRACTOR)

        items = extractor(raw)
        for item in items:
            extracted_pairs.append((raw, item))

    return extracted_pairs


# ============================================================
#  Known Pakistani route keywords → canonical names
#  Add more as needed
# ============================================================
import re

ROUTE_KEYWORD_MAP: Dict[str, Dict[str, str]] = {
    # KKH / N-35
    "karakoram highway":    {"origin": "Islamabad", "destination": "Gilgit", "route": "Karakoram Highway (N-35)"},
    "karakorum highway":    {"origin": "Islamabad", "destination": "Gilgit", "route": "Karakoram Highway (N-35)"},
    "karakoram":            {"origin": "Islamabad", "destination": "Gilgit", "route": "Karakoram Highway (N-35)"},
    "kkh":                  {"origin": "Islamabad", "destination": "Gilgit", "route": "Karakoram Highway (N-35)"},
    "n-35":                 {"origin": "Islamabad", "destination": "Gilgit", "route": "Karakoram Highway (N-35)"},
    "n35":                  {"origin": "Islamabad", "destination": "Gilgit", "route": "Karakoram Highway (N-35)"},
    # Jaglot-Skardu  ← handles hyphen, en-dash, em-dash, space variants
    "jaglot skardu":        {"origin": "Jaglot", "destination": "Skardu", "route": "Jaglot-Skardu Road (S-1)"},
    "jaglot-skardu":        {"origin": "Jaglot", "destination": "Skardu", "route": "Jaglot-Skardu Road (S-1)"},
    "jaglot\u2013skardu":   {"origin": "Jaglot", "destination": "Skardu", "route": "Jaglot-Skardu Road (S-1)"},  # en-dash
    "jaglot\u2014skardu":   {"origin": "Jaglot", "destination": "Skardu", "route": "Jaglot-Skardu Road (S-1)"},  # em-dash
    "jsr":                  {"origin": "Jaglot", "destination": "Skardu", "route": "Jaglot-Skardu Road (S-1)"},
    "s-1":                  {"origin": "Jaglot", "destination": "Skardu", "route": "Jaglot-Skardu Road (S-1)"},
    # Babusar / N-15
    "babusar":              {"origin": "Naran",  "destination": "Gilgit", "route": "Babusar Pass / N-15"},
    "n-15":                 {"origin": "Naran",  "destination": "Gilgit", "route": "N-15 Naran-Gilgit"},
    "n15":                  {"origin": "Naran",  "destination": "Gilgit", "route": "N-15 Naran-Gilgit"},
    "naran":                {"origin": "Mansehra", "destination": "Naran", "route": "Kaghan Valley Road"},
    # Motorways
    "m-2":                  {"origin": "Lahore",     "destination": "Islamabad", "route": "M-2 Motorway"},
    "m2":                   {"origin": "Lahore",     "destination": "Islamabad", "route": "M-2 Motorway"},
    "m-1":                  {"origin": "Islamabad",  "destination": "Peshawar",  "route": "M-1 Motorway"},
    "m1":                   {"origin": "Islamabad",  "destination": "Peshawar",  "route": "M-1 Motorway"},
    "m-15":                 {"origin": "Burhan",     "destination": "Thakot",    "route": "M-15 Motorway"},
    "m15":                  {"origin": "Burhan",     "destination": "Thakot",    "route": "M-15 Motorway"},
    "m-11":                 {"origin": "Lahore",     "destination": "Sialkot",   "route": "M-11 Motorway"},
    "m-9":                  {"origin": "Karachi",    "destination": "Hyderabad", "route": "M-9 Motorway"},
    "m-16":                 {"origin": "Peshawar",   "destination": "Swat",      "route": "Swat Motorway (M-16)"},
    "m-3":                  {"origin": "Lahore",     "destination": "Abdul Hakim", "route": "M-3 Motorway"},
    # Cities / regions
    "gilgit":               {"origin": "Islamabad",  "destination": "Gilgit",   "route": "Karakoram Highway"},
    "skardu":               {"origin": "Jaglot",     "destination": "Skardu",   "route": "Jaglot-Skardu Road"},
    "hunza":                {"origin": "Islamabad",  "destination": "Hunza",    "route": "Karakoram Highway"},
    "chitral":              {"origin": "Peshawar",   "destination": "Chitral",  "route": "Chitral Road"},
    "swat":                 {"origin": "Peshawar",   "destination": "Swat",     "route": "Swat Motorway"},
    "quetta":               {"origin": "Karachi",    "destination": "Quetta",   "route": "N-25"},
    "n-25":                 {"origin": "Karachi",    "destination": "Quetta",   "route": "N-25"},
}

ISSUE_KEYWORDS: List[Tuple[str, str]] = [
    # ordered: most specific first
    ("no alternate route",  "blockage"),
    ("no alternative",      "blockage"),
    ("under construction",  "construction"),
    ("vehicle breakdown",   "incident"),
    ("flash flood",         "blockage"),
    ("landslide",           "blockage"),
    ("land sliding",        "blockage"),
    ("blocked",             "blockage"),
    ("blockage",            "blockage"),
    ("closed",              "incident"),
    ("closure",             "incident"),
    ("flood",               "blockage"),
    ("rain",                "weather"),
    ("fog",                 "weather"),
    ("snow",                "weather"),
    ("accident",            "accident"),
    ("breakdown",           "incident"),
    ("repair",              "construction"),
    ("security",            "security"),
    ("open",                "general"),
    ("reopened",            "general"),
]

SEVERITY_KEYWORDS: List[Tuple[str, str]] = [
    # ordered: most severe first
    ("no alternate route",  "high"),
    ("no alternative",      "high"),
    ("blocked",             "high"),
    ("flash flood",         "high"),
    ("landslide",           "high"),
    ("accident",            "high"),
    ("closed",              "high"),
    ("security",            "high"),
    ("flood",               "high"),
    ("rain",                "medium"),
    ("fog",                 "medium"),
    ("snow",                "medium"),
    ("repair",              "medium"),
    ("breakdown",           "medium"),
    ("open",                "low"),
    ("reopened",            "low"),
]


def _normalise(text: str) -> str:
    """
    Lowercase + replace all dash variants and extra whitespace
    so 'Jaglot–Skardu' matches 'jaglot skardu' and 'jaglot-skardu'.
    """
    text = text.lower()
    # Replace em-dash, en-dash, hyphen with a space AND keep the hyphenated version
    text = re.sub(r'[\u2013\u2014\u2012\u2015]', ' ', text)  # unicode dashes → space
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text


# route_pipeline.py

from app.services.nhmp_html_scraper import parse_nhmp_html



#

def _extract_text_source_metadata(content: str) -> Dict[str, Any]:
    """
    Keyword extraction for Facebook / SERPAPI text posts.
    Normalises dashes and whitespace before matching so variants
    like 'Jaglot–Skardu', 'jaglot-skardu', 'JSR' all match.
    """
    normalised = _normalise(content)

    # ── 1. Route match (longest keyword first) ──
    matched_route: Optional[Dict[str, str]] = None
    for keyword in sorted(ROUTE_KEYWORD_MAP.keys(), key=len, reverse=True):
        # also normalise the keyword itself (handles dash variants in map keys)
        norm_kw = _normalise(keyword)
        if norm_kw in normalised:
            matched_route = ROUTE_KEYWORD_MAP[keyword]
            break

    origin      = matched_route["origin"]      if matched_route else None
    destination = matched_route["destination"] if matched_route else None
    route_label = matched_route["route"]       if matched_route else None

    # ── 2. Issue type (first match wins) ──
    issue_type = "general"
    for kw, itype in ISSUE_KEYWORDS:
        if _normalise(kw) in normalised:
            issue_type = itype
            break

    # ── 3. Severity (first/most severe match wins) ──
    severity = "medium"
    for kw, sev in SEVERITY_KEYWORDS:
        if _normalise(kw) in normalised:
            severity = sev
            break

    # ── 4. Headline: first meaningful line, stripped of markdown ──
    headline = ""
    for line in content.splitlines():
        clean = re.sub(r'[*#_`]', '', line).strip()
        if len(clean) > 10:
            headline = clean[:150]
            break

    return {
        "origin":       origin,
        "destination":  destination,
        "route_label":  route_label,
        "issue_type":   issue_type,
        "severity":     severity,
        "headline":     headline,
    }


def extract_text_source(raw: dict) -> List[Dict[str, Any]]:
    """Facebook / SERPAPI — keyword extraction, store raw content."""
    content = (raw.get("content") or "").strip()
    if len(content) < 10:
        return []

    meta = _extract_text_source_metadata(content)

    return [{
        "source_type":  raw["source"],
        "raw_content":  content,
        "url":          raw.get("url"),
        "reported_at":  _parse_iso(
            raw.get("post_created_at") or raw.get("reported_at") or ""
        ),
        **meta,
    }]

def _build_scrape_result(
        route_id,
        raw: dict,
        extracted: Dict[str, Any],
        content_hash: str,
) -> ScrapeResult:
    source_type = extracted.get("source_type", raw.get("source", "unknown"))

    if source_type == "NHMP_API":
        lane = extracted.get("lane_closure", "")
        closed_count = lane.count("true") if lane else 0
        severity = "high" if closed_count >= 2 else ("medium" if closed_count == 1 else "low")

        alert_type = extracted.get("alert_type", "")
        sub_type   = extracted.get("sub_type", "")
        if alert_type == "Road Closed" and sub_type == "Repair":
            issue_type = "construction"
        elif alert_type == "Road Closed":
            issue_type = "incident"
        elif alert_type == "Weather Alert":
            issue_type = "weather"
        else:
            issue_type = "general"

        return ScrapeResult(
            route_id=route_id,
            source_name=source_type,
            source_url=raw.get("url") or "",
            headline=f"{alert_type}: {extracted.get('route_label', '')}",
            route_affected=extracted.get("route_label"),
            origin=extracted.get("origin"),
            destination=extracted.get("destination"),
            issue_type=issue_type,
            severity=severity,
            summary=(
                f"{alert_type} on {extracted.get('route_label', 'route')} "
                f"({extracted.get('from_place', '')} to {extracted.get('to_place', '')})"
            ),
            raw_content=extracted.get("raw_content") or raw.get("content", ""),
            content_hash=content_hash,
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )

    # ── Text sources: Facebook, SERPAPI — metadata extracted by keyword ──
    return ScrapeResult(
        route_id=route_id,
        source_name=source_type,
        source_url=extracted.get("url") or raw.get("url") or "",
        headline=extracted.get("headline") or "",
        route_affected=extracted.get("route_label") or "",
        origin=extracted.get("origin"),            # None if not recognised
        destination=extracted.get("destination"),  # None if not recognised
        issue_type=extracted.get("issue_type", "general"),
        severity=extracted.get("severity", "medium"),
        summary=extracted.get("raw_content", ""),  # raw text IS the summary until LLM processes it
        raw_content=extracted.get("raw_content", ""),
        content_hash=content_hash,
        is_active=True,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
# ============================================================
#  scrape_extract_and_store — the main pipeline
# ============================================================

async def scrape_extract_and_store(
        session: AsyncSession,
        route: Route,
        scraper: ScraperService,
        graph_api: GraphAPIService,
        extractor: LLMExtractor,
        commit: bool = True,
) -> Tuple[List[Dict[str, Any]], int]:

    origin = "All"
    destination = "All"

    # 1. Fetch raw from ALL sources
    try:
        raw_results = await fetch_raw_sources(origin, destination, scraper, graph_api)
    except Exception as e:
        logger.error(f"Issue getting data: {e}")
        raw_results = []

    # print("*"*20)
    # print("Raw Results:", raw_results)
    # print("*"*20)

    structured_items: List[Dict[str, Any]] = []
    to_extract: List[dict] = []
    hash_by_source_url: Dict[str, str] = {}

    # 2. Deduplicate by content hash
    for raw in raw_results:
        if not raw.get("scrape_success") or not raw.get("content"):
            continue

        content = raw["content"]
        new_hash = _hash_content(content)

        # Check ScrapeResult for existing row
        existing = await session.execute(
            select(ScrapeResult).where(
                ScrapeResult.content_hash == new_hash,
                ScrapeResult.is_active == True,
                )
        )
        if existing.scalar_one_or_none():
            logger.info(f"[skip] {raw['source']} unchanged for {origin}->{destination}")
            continue

        min_len = 15 if raw["source"] == "own_fb_page" else 30
        if len(content.strip()) < min_len:
            continue

        key = f"{raw['source']}::{raw.get('url', '')}"
        hash_by_source_url[key] = new_hash
        to_extract.append(raw)

    if not to_extract:
        return structured_items, 0

    # 3. Dispatch to source-specific extractors
    extracted_pairs = await batch_extract(to_extract)

    # print("*"*20)
    # print("Extracted paires",extracted_pairs)
    # print("*"*20)

    # 4. Store results
    for raw, extracted in extracted_pairs:
        # Use per-alert hash for NHMP, fallback to source-level hash for text
        new_hash = extracted.get("individual_hash")

        # Dedup check per individual alert
        existing_check = await session.execute(
            select(ScrapeResult).where(
                ScrapeResult.content_hash == new_hash,
                ScrapeResult.is_active == True,
                )
        )
        if existing_check.scalar_one_or_none():
            logger.info(f"[skip] {raw['source']} alert already stored (hash={new_hash[:12]}...)")
            continue
        # ── Store NHMP raw data in NHMPClosure (for NHMP-specific queries) ──
        if extracted.get("source_type") == "NHMP_API":
            nhmp_row = NHMPClosure(
                origin=extracted.get("origin", origin),
                destination=extracted.get("destination", destination),
                source=raw["source"],
                alert_type=extracted.get("alert_type"),
                sub_type=extracted.get("sub_type"),
                route_label=extracted.get("route_label"),
                from_place=extracted.get("from_place"),
                to_place=extracted.get("to_place"),
                remarks=extracted.get("remarks"),
                lane_closure=extracted.get("lane_closure"),
                reported_at=extracted.get("reported_at"),
                content_hash=new_hash,
            )
            session.add(nhmp_row)

        # ── Store EVERYTHING in ScrapeResult (unified table) ──
        scrape_row = _build_scrape_result(route, raw, extracted, new_hash)
        # print("*"*20)
        # print("Scraped row:",extracted)
        # print("*"*20)

        session.add(scrape_row)

        structured_items.append({
            "source": raw["source"],
            "headline": scrape_row.headline,
            "route": scrape_row.route_affected,
            "from_db": False,
        })

    if commit:
        await session.commit()

    return structured_items, 0


