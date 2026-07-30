# app/services/nhmp_page_scraper.py
import re
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)

NHMP_ADVISORY_URL = "https://beta.nhmp.gov.pk/TA/Public/ViewTravel.aspx"

SEVERITY_CLASS_MAP = {
    "alert-success": "low",       # Road & Weather Clear
    "alert-warning": "medium",    # Road Closed / lane closures / weather
    "alert-danger": "high",       # not seen in sample, but map defensively
}
# Legend: yellow = Public Protest — no fixed class name in sample, handled by row bgcolor if needed

def _parse_section_route(sector_text: str) -> tuple[str, str] | None:
    """'(Burhan to Thakot)' -> ('Burhan', 'Thakot')"""
    m = re.search(r"\((.+?)\s+to\s+(.+?)\)", sector_text, re.IGNORECASE)
    if not m:
        return None
    return m.group(1).strip(), m.group(2).strip()


async def fetch_nhmp_advisory_html() -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(NHMP_ADVISORY_URL, timeout=20) as resp:
            resp.raise_for_status()
            return await resp.text()


def parse_nhmp_advisory_page(html: str) -> List[Dict[str, Any]]:
    """
    Returns one dict per sector, e.g.:
    {
        "zone": "Motorway North Zone",
        "sector_name": "E35",
        "origin": "Burhan", "destination": "Thakot",
        "phone": "0992-402281",
        "alerts": [{"text": "...", "severity": "medium"}, ...],
        "last_updated": "30-Jul-26 12:54:04",
    }
    """
    soup = BeautifulSoup(html, "html.parser")
    outer_table = soup.find("table", {"class": "table"})  # top-level table
    if not outer_table:
        logger.error("NHMP page structure changed — outer table not found")
        return []

    sectors = []
    current_zone = None

    for tr in outer_table.find_all("tr", recursive=False):
        tds = tr.find_all("td", recursive=False)
        if not tds:
            continue

        # rowspan zone cell present -> first td is zone
        if len(tds) == 3:
            current_zone = tds[0].get_text(strip=True)
            sector_td, info_td = tds[1], tds[2]
        elif len(tds) == 2:
            sector_td, info_td = tds[0], tds[1]
        else:
            continue

        sector_raw = sector_td.get_text(" ", strip=True)
        route = _parse_section_route(sector_raw)
        if not route:
            continue
        origin, destination = route

        sector_name_match = re.match(r"([A-Za-z0-9\- ]+?)\s*\(", sector_raw)
        sector_name = sector_name_match.group(1).strip() if sector_name_match else sector_raw

        phone_match = re.search(r"Ph[:\.]?\s*([\d\-\s]+)", sector_td.get_text(" ", strip=True))
        phone = phone_match.group(1).strip() if phone_match else ""

        alerts = []
        for row in info_td.find_all("tr"):
            cell = row.find("td")
            if not cell:
                continue
            text = cell.get_text(" ", strip=True)
            if not text:
                continue
            css_class = " ".join(row.get("class", []))
            severity = SEVERITY_CLASS_MAP.get(css_class, "low" if "clear" in text.lower() else "medium")
            alerts.append({"text": text, "severity": severity})

        last_updated_tag = info_td.find("span", id=re.compile(r"^lbl"))
        last_updated = None
        if last_updated_tag:
            b_tag = last_updated_tag.find("b")
            if b_tag:
                try:
                    last_updated = datetime.strptime(b_tag.get_text(strip=True), "%d-%b-%y %H:%M:%S")
                except ValueError:
                    last_updated = None

        sectors.append({
            "zone": current_zone,
            "sector_name": sector_name,
            "origin": origin,
            "destination": destination,
            "phone": phone,
            "alerts": alerts,
            "last_updated": last_updated,
        })

    logger.info(f"Parsed {len(sectors)} NHMP sectors from advisory page")
    return sectors