# app/services/route_pipeline.py
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import json
from datetime import datetime

from app.models.route import Route
from app.models.scrape_result import ScrapeResult
from app.models.nhmp_closure import NHMPClosure
from app.schemas.scrape import RawScrapeData
from app.services.scraper import ScraperService
from app.services.graph_api_service import GraphAPIService
from app.services.llm_extractor import LLMExtractor
from app.utils.logger import get_logger
from app.services.corridor import get_corridor,is_relevant_post
logger = get_logger(__name__)

GB_KEYWORDS = ["skardu", "gilgit", "hunza", "kkh", "karakoram", "astore", "northern"]


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def is_gb_route(origin: str, destination: str) -> bool:
    origin = origin.lower()
    print("*"*20)
    print("Kai scene hai?")
    print("*"*20)

    destination = destination.lower()
    if ( origin in GB_KEYWORDS) or (destination in GB_KEYWORDS):
        print("*"*20)
        print("Kai scene hai?")
        print("*"*20)

        return True
    else :
        return False

# app/services/route_pipeline.py — fetch_raw_sources, revised
async def fetch_raw_sources(origin, destination, scraper, graph_api):
    results = []

    # Always try the general/motorway scraper — M-15, general road network,
    # NHMP data isn't exclusive to non-GB routes; Burhan/Thakot etc. sit on
    # both an M-series motorway AND lead into a GB corridor.
    try:
        results.extend(await scraper.scrape_route_news(origin, destination))
    except Exception as e:
        logger.error(f"Scrape failed for {origin}->{destination}: {e}")

    if is_gb_route(origin, destination):
        try:
            fb_results = await graph_api.fetch_recent_posts(limit=5)
            corridor = get_corridor(origin, destination)
            fb_results = [
                r for r in fb_results
                if is_relevant_post(r.get("content", ""), origin, destination, corridor)
            ]
            results.extend(fb_results)
        except Exception as e:
            logger.error(f"Graph API fetch failed for {origin}->{destination}: {e}")

        try:
            results.extend(await scraper.serpapi(origin, destination))
        except Exception as e:
            logger.error(f"Scrape fallback failed for {origin}->{destination}: {e}")

    return results

def _row_to_dict(row: ScrapeResult) -> Dict[str, Any]:
    """Shape matches what RAGService._normalize_docs expects (already-structured)."""
    return {
        "source": row.source_name,
        "url": row.source_url,
        "content": row.summary or row.raw_content,
        "scrape_success": True,
        "error": None,
        "from_db": True,  # tells RAG: skip re-extraction, already structured
        "headline": row.headline,
        "issue_type": row.issue_type,
        "severity": row.severity,
        "route_affected": row.route_affected,
        "summary": row.summary,
        "created_at": row.created_at,
    }



def _parse_nhmp_date(date_str: str) -> datetime:
    if not date_str:
        return datetime.min
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        return datetime.min
from typing import List, Dict, Any
import json
from datetime import datetime

def filter_latest_nhmp_closure(raw_json_string: str) -> List[Dict[str, Any]]:
    """
    Parses NHMP API JSON and returns a list of dictionaries containing structured alerts
    (Road Closed, Weather Alert, etc.) sorted by newest first.
    """
    try:
        api_response = json.loads(raw_json_string)
        data_list = api_response.get("data", [])
    except json.JSONDecodeError:
        return []

    if not data_list:
        return []

    # 1. Look for important alerts (closures, weather, diversions, etc.)
    allowed_types = ["Road Closed"]

    valid_alerts = [
        item for item in data_list
        if item.get("type") in allowed_types
    ]

    if not valid_alerts:
        return []

    # 2. Sort explicitly by real Datetime
    valid_alerts.sort(key=lambda x: _parse_nhmp_date(x.get("createdOn", "")), reverse=True)

    data = []

    # 3. Create dictionaries instead of strings
    for alert in valid_alerts:
        route_str = alert.get('route', '')

        try:
            alert_origin, alert_destination = route_str.split(" to ")
        except ValueError:
            alert_origin, alert_destination = "Unknown", "Unknown"

        clean_dict = {
            "origin": alert_origin,
            "destination": alert_destination,
            "alert_type": alert.get('type'),
            "sub_type": alert.get('subType'),
            "route": route_str,
            "from_place": alert.get('fromPlace'),
            "to_place": alert.get('toPlace'),
            "reported_at": alert.get('createdOn'),
            "remarks": alert.get('remarks'),
            "lane_closure": alert.get('laneClosure'),
        }

        data.append(clean_dict)

    return data

from typing import List, Tuple, Dict, Any
async def batch_extract(
        scraped_results: List[dict],
) -> List[Tuple[dict, Any]]: # Any allows both strings (for web scrapes) and dicts (for NHMP)
    """
    Extract structured data from all scraped results.
    Returns a list of tuples: (raw_data_dict, cleaned_data)
    """
    valid_results = [
        r for r in scraped_results
        if r.get("scrape_success") and r.get("content")
    ]

    if not valid_results:
        return []

    extracted_pairs = []

    for result in valid_results:
        if result["source"] == "NHMP_API":
            # This returns our new list of dictionaries
            cleaned_list = filter_latest_nhmp_closure(result["content"])

            # Loop through the list and add each alert individually
            for cleaned_dict in cleaned_list:
                extracted_pairs.append((result, cleaned_dict))
        else:
            # Fallback for standard text scraping (if you add back LLM extractor)
            cleaned = result["content"]
            if not cleaned or len(cleaned) < 10:
                continue
            extracted_pairs.append((result, cleaned))

    return extracted_pairs

import hashlib
from datetime import datetime
from typing import List, Dict, Any, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ... (Keep your imports and fetch_raw_sources setup)

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

    try:
        raw_results = await fetch_raw_sources(origin, destination, scraper, graph_api)
    except Exception as e:
        logger.error(f"Issue getting data: {e}")
        raw_results = []

    structured_items: List[Dict[str, Any]] = []
    to_extract: List[dict] = []
    hash_by_source_url: Dict[str, str] = {}

    for raw in raw_results:
        if not raw.get("scrape_success") or not raw.get("content"):
            continue

        content = raw["content"]
        new_hash = _hash_content(content)

        existing = await session.execute(
            select(NHMPClosure).where(
                NHMPClosure.origin == origin,
                NHMPClosure.destination == destination,
                NHMPClosure.source == raw["source"],
                NHMPClosure.content_hash == new_hash,
                )
        )

        if existing.scalar_one_or_none():
            logger.info(f"[skip] {raw['source']} unchanged for {origin}->{destination}")
            continue

        min_len = 15 if raw["source"] == "own_fb_page" else 30
        if len(content.strip()) < min_len:
            continue

        key = f"{raw['source']}::{raw.get('url','')}"
        hash_by_source_url[key] = new_hash
        to_extract.append(raw)

    if to_extract:
        extracted_pairs = await batch_extract(to_extract)

        # cleaned_data is now our dictionary for NHMP!
        for raw, cleaned_data in extracted_pairs:
            key = f"{raw['source']}::{raw.get('url','')}"
            new_hash = hash_by_source_url[key]

            if raw["source"] == "NHMP_API":

                # Safely parse the datetime string from the dictionary
                reported_at_str = cleaned_data.get("reported_at")
                reported_at = None
                if reported_at_str:
                    try:
                        reported_at = datetime.fromisoformat(reported_at_str)
                    except ValueError:
                        pass

                # Build the database row directly using dictionary keys! No Regex needed!
                nhmp_row = NHMPClosure(
                    origin=cleaned_data.get("origin", origin),
                    destination=cleaned_data.get("destination", destination),
                    source=raw["source"],
                    alert_type=cleaned_data.get("alert_type"),
                    sub_type=cleaned_data.get("sub_type"),
                    route_label=cleaned_data.get("route"),
                    from_place=cleaned_data.get("from_place"),
                    to_place=cleaned_data.get("to_place"),
                    remarks=cleaned_data.get("remarks"),
                    lane_closure=cleaned_data.get("lane_closure"),
                    reported_at=reported_at,
                    content_hash=new_hash,
                )
                session.add(nhmp_row)
                await session.flush()

                structured_items.append({
                    "source": raw["source"],
                    "alert_type": nhmp_row.alert_type,
                    "route": nhmp_row.route_label,
                    "from_db": False
                })

    if commit:
        await session.commit()

    return structured_items, 0