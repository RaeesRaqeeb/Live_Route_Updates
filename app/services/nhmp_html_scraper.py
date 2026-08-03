# app/services/nhmp_html_scraper.py

import re
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup


# ── GridView id → route metadata (from the page's sector layout) ──
SECTOR_MAP: Dict[str, Dict[str, str]] = {
    "GridView1":  {"origin": "Peshawar",      "destination": "Islamabad",      "route": "M1 Motorway"},
    "GridView23": {"origin": "Burhan",        "destination": "Thakot",         "route": "E35/M15 Motorway"},
    "GridView7":  {"origin": "Islamabad",     "destination": "Kot Momin",      "route": "M2 Motorway North"},
    "GridView25": {"origin": "Hakla",         "destination": "Dera Ismail Khan","route": "M14 Motorway"},
    "GridView29": {"origin": "Col Sher Khan", "destination": "Chakdara",       "route": "Swat Expressway"},
    "GridView8":  {"origin": "Kot Momin",     "destination": "Lahore",         "route": "M2 Motorway South"},
    "GridView18": {"origin": "Lahore",        "destination": "Abdul Hakim",    "route": "M3 Motorway"},
    "GridView24": {"origin": "Lahore",        "destination": "Sialkot",        "route": "M11 Motorway"},
    "GridView19": {"origin": "Pindi Bhatian", "destination": "Abdul Hakim",    "route": "M4 Motorway"},
    "GridView27": {"origin": "Abdul Hakim",   "destination": "Sher Shah",      "route": "M4 Sub-Sector"},
    "GridView13": {"origin": "Sher Shah",     "destination": "Zahir Pir",      "route": "M5 Motorway"},
    "GridView20": {"origin": "Zahir Pir",     "destination": "Rohri",          "route": "M5 Motorway"},
    "GridView9":  {"origin": "Peshawar",      "destination": "Islamabad",      "route": "N5 GT Road North"},
    "GridView10": {"origin": "Islamabad",     "destination": "Kharian",        "route": "N5 GT Road"},
    "GridView11": {"origin": "Kharian",       "destination": "Lahore",         "route": "N5 GT Road"},
    "GridView16": {"origin": "Islamabad",     "destination": "Murree",         "route": "N75 Islamabad-Murree"},
    "GridView2":  {"origin": "Lahore",        "destination": "Chichawatni",    "route": "N5 Central"},
    "GridView3":  {"origin": "Mian Channu",   "destination": "Bahawalpur",     "route": "N5 Central"},
    "GridView4":  {"origin": "Ahmed Pur East","destination": "Sadiqabad",      "route": "N5 Central"},
    "GridView5":  {"origin": "Kot Sabzal",    "destination": "Halani",         "route": "N5 South"},
    "GridView6":  {"origin": "Halani",        "destination": "Hala",           "route": "N5 South"},
    "GridView12": {"origin": "Hala",          "destination": "Karachi",        "route": "N5 South"},
    "GridView22": {"origin": "Jamshoro",      "destination": "Bhan Saeedabad", "route": "N55 Indus Highway"},
    "GridView26": {"origin": "Bhan Saeedabad","destination": "Ratodero",       "route": "N55 Indus Highway"},
    "c":          {"origin": "Hub",           "destination": "Uthal",          "route": "N10 West"},
    "GridView14": {"origin": "Kalat",         "destination": "Quetta",         "route": "N25 Kalat-Quetta"},
    "GridView15": {"origin": "Gwadar",        "destination": "Makola",         "route": "N10 Coastal"},
    "GridView28": {"origin": "Kuchlak",       "destination": "Killasaifullah", "route": "N50"},
}

CLEAR_PHRASES = {"road & weather clear", "road and weather clear"}


def _parse_dt(text: str) -> Optional[datetime]:
    m = re.search(r'(\d{2}-\w{3}-\d{2,4}\s+\d{2}:\d{2}:\d{2})', text or "")
    if not m:
        return None
    for fmt in ("%d-%b-%y %H:%M:%S", "%d-%b-%Y %H:%M:%S"):
        try:
            return datetime.strptime(m.group(1), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _classify(text: str):
    """Return (alert_type, sub_type, issue_type, severity)."""
    t = text.lower()

    if t.startswith("weather"):
        alert_type, issue_type, severity = "Weather Alert", "weather", "low"
    elif t.startswith("road closed"):
        alert_type, issue_type, severity = "Road Closed", "incident", "high"
    elif t.startswith("lane closed"):
        alert_type, issue_type, severity = "Lane Closed", "incident", "medium"
    elif t.startswith("diversion"):
        alert_type, issue_type, severity = "Diversion", "incident", "medium"
    elif t.startswith("fog"):
        alert_type, issue_type, severity = "Weather Alert", "weather", "low"
    else:
        alert_type, issue_type, severity = "Advisory", "general", "low"

    # sub type
    sub_type = "General"
    for kw, st in [
        ("road work", "Repair"), ("vehicle breakdown", "Vehicle Breakdown"),
        ("road damage", "Road Damage"), ("law & order", "Security"),
        ("flood", "Flood"), ("landslide", "Landslide"),
        ("rain", "Rain"), ("cloudy", "Cloudy"), ("fog", "Fog"),
    ]:
        if kw in t:
            sub_type = st
            break

    if sub_type in ("Flood", "Landslide", "Road Damage", "Security"):
        severity = "high"

    return alert_type, sub_type, issue_type, severity


def _clean_text(text: str) -> str:
    """Collapse whitespace and strip noise."""
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_nhmp_html(html: str) -> List[Dict[str, Any]]:
    """
    Parse NHMP ViewTravel.aspx HTML into clean structured alert dicts.
    Skips 'Road & Weather Clear' and empty fog templates.
    """
    soup = BeautifulSoup(html, "html.parser")
    alerts: List[Dict[str, Any]] = []

    for grid_id, meta in SECTOR_MAP.items():
        table = soup.find("table", id=grid_id)
        if not table:
            continue

        # timestamp from the lbl* span in the parent <td>
        last_updated = None
        parent_td = table.find_parent("td")
        if parent_td:
            for span in parent_td.find_all("span"):
                if "last updated" in span.get_text(strip=True).lower():
                    last_updated = _parse_dt(span.get_text())
                    break

        for row in table.find_all("tr"):
            cell = row.find("td")
            if not cell:
                continue

            text = _clean_text(cell.get_text(separator=" ", strip=True))

            if not text:
                continue
            if text.lower() in CLEAR_PHRASES:
                continue
            # skip empty fog placeholders: "Fog from (KM ) to (KM ). Visibility = meters"
            if re.match(r'^fog from\s*\(km\s*\)\s*to\s*\(km\s*\)', text, re.I):
                continue

            alert_type, sub_type, issue_type, severity = _classify(text)

            alerts.append({
                "source_type":     "NHMP_HTML",
                "origin":          meta["origin"],
                "destination":     meta["destination"],
                "route_label":     meta["route"],
                "alert_type":      alert_type,
                "sub_type":        sub_type,
                "issue_type":      issue_type,
                "severity":        severity,
                "raw_content":     text,          # CLEAN one-line text, not raw HTML
                "reported_at":     last_updated,
                "individual_hash": hashlib.sha256(f"{grid_id}::{text}".encode()).hexdigest(),
            })

    return alerts