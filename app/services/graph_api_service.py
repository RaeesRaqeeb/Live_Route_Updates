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
        self.token = settings.FB_PAGE_ACCESS_TOKEN  # now a System User token — same usage

    async def fetch_recent_posts(self, limit: int = 25) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/{self.page_id}/posts"
        params = {
            "fields": "message,created_time,permalink_url",
            "access_token": self.token,
            "limit": limit,
        }

        timeout = aiohttp.ClientTimeout(total=15)  # explicit, avoids indefinite hangs
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error(f"Graph API error {resp.status}: {body}")
                        # Flag auth-specific failures distinctly, so callers
                        # can tell "token problem" apart from "no posts" —
                        # useful now that you've hit this twice already.
                        if resp.status in (400, 401) and "OAuthException" in body:
                            logger.error("Graph API token appears invalid/expired — check FB_PAGE_ACCESS_TOKEN")
                        return [self._empty_result(f"HTTP {resp.status}: {body[:200]}")]
                    data = await resp.json()
        except Exception as e:
            logger.error(f"Graph API fetch failed: {e}")
            return [self._empty_result(str(e))]

        posts = data.get("data", [])
        results = []
        for post in posts:
            message = post.get("message", "").strip()
            if not message:
                continue

            results.append({
                "source": "own_fb_page",
                "url": post.get("permalink_url", ""),
                "content": message,
                "scrape_success": True,
                "error": None,
                "post_created_at": post.get("created_time"),
            })

        logger.info(f"Graph API: fetched {len(results)} posts with content from own page")
        return results

    def _empty_result(self, err: str) -> Dict[str, Any]:
        return {"source": "own_fb_page", "url": "", "content": "", "scrape_success": False, "error": err}