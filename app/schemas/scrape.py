# app/schemas/scrape.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class IssueTypeEnum(str, Enum):
    ACCIDENT     = "accident"
    BLOCKAGE     = "blockage"
    WEATHER      = "weather"
    CONSTRUCTION = "construction"
    SECURITY     = "security"
    GENERAL      = "general"


class SeverityEnum(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


class ExtractedRouteInfo(BaseModel):
    """
    Schema for LLM-extracted structured data from raw scraped text.
    Used when passing scraped content through the LLM extractor.
    """
    headline: str
    route_affected: Optional[str] 
    issue_type: IssueTypeEnum = IssueTypeEnum.GENERAL
    severity: SeverityEnum = SeverityEnum.LOW
    timestamp: Optional[str] 
    summary: str
    is_route_related: bool = True


class ScrapeResultSchema(BaseModel):
    """Full scrape result schema including DB fields."""
    id: Optional[int] = None
    source_name: str
    source_url: str
    headline: Optional[str] = None
    route_affected: Optional[str] = None
    issue_type: str = "general"
    severity: str = "low"
    raw_content: Optional[str] = None
    summary: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RawScrapeData(BaseModel):
    """
    Internal schema: raw data returned by the scraper
    before LLM extraction.
    """
    source: str
    url: str
    content: str                  # fit_markdown from Crawl4AI
    scrape_success: bool = True
    error: Optional[str] = None

from pydantic import BaseModel
from typing import List

class BatchExtractedItem(ExtractedRouteInfo):
    source_id: str  # matches the label we inject in the prompt, e.g. "SRC_0"

class BatchExtractionResult(BaseModel):
    items: List[BatchExtractedItem]