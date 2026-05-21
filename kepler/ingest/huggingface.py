from datetime import datetime, timezone

import feedparser
import httpx

from kepler.config import Config
from kepler.ingest.base import RawItem


class HFBlogScraper:

    RSS_URL = "https://huggingface.co/blog/feed.xml"

    def __init__(self, config: Config):
        self.config = config

    async def fetch(self) -> list[RawItem]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.RSS_URL, timeout=30, follow_redirects=True)
            resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        items: list[RawItem] = []
        for entry in feed.entries:
            items.append(
                RawItem(
                    source="huggingface",
                    url=(entry.get("link") or "").strip(),
                    title=(entry.get("title") or "").strip(),
                    content=self._clean_content(
                        entry.get("summary") or entry.get("description") or ""
                    ),
                    published_at=self._parse_date(entry),
                    source_tags=["huggingface"],
                )
            )
        return items

    def _clean_content(self, raw: str) -> str:
        import re
        text = re.sub(r"<[^>]+>", "", raw)
        return text.strip()[: self.config.max_content_length]

    def _parse_date(self, entry) -> datetime:
        from email.utils import parsedate_to_datetime
        try:
            dt = parsedate_to_datetime(entry.published)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return datetime.now(timezone.utc)
