# app/services/graph_api_service.py
import aiohttp
from datetime import datetime, timezone
from typing import List, Dict, Any

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GraphAPIService:
    def __init__(self):
        self.base_url = f"https://graph.facebook.com/{settings.GRAPH_API_VERSION}"
        self.page_id = settings.FB_PAGE_ID
        self.token = settings.FB_PAGE_ACCESS_TOKEN

    async def fetch_recent_posts(self, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Pull recent posts from the Page. Returns raw dicts shaped like
        your other scraper sources: {source, url, content, scrape_success, error}
        """
        url = f"{self.base_url}/{self.page_id}/posts"
        params = {
            "fields": "message,created_time,permalink_url",
            "access_token": self.token,
            "limit": limit,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=15) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error(f"Graph API error {resp.status}: {body}")
                        return [self._empty_result(f"HTTP {resp.status}")]
                    data = await resp.json()
        except Exception as e:
            logger.error(f"Graph API fetch failed: {e}")
            return [self._empty_result(str(e))]

        posts = data.get("data", [])
        results = []
        for post in posts:
            message = post.get("message", "").strip()
            if not message:
                continue  # skip posts with no text (pure image/video posts)

            results.append({
                "source": "own_fb_page",
                "url": post.get("permalink_url", ""),
                "content": message,
                "scrape_success": True,
                "error": None,
                "post_created_at": post.get("created_time"),  # useful for freshness
            })

        logger.info(f"Graph API: fetched {len(results)} posts with content from own page")
        return results

    def _empty_result(self, err: str) -> Dict[str, Any]:
        return {"source": "own_fb_page", "url": "", "content": "", "scrape_success": False, "error": err}