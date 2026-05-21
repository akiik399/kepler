from datetime import datetime, timezone

import feedparser
import httpx

from kepler.config import Config
from kepler.ingest.base import RawItem


class ArxivScraper:

    BASE_URL = "http://export.arxiv.org/rss"

    def __init__(self, config: Config):
        self.config = config

    async def fetch(self) -> list[RawItem]:
        items: list[RawItem] = []
        for category in self.config.arxiv_categories:
            try:
                url = f"{self.BASE_URL}/{category}"
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, timeout=30, follow_redirects=True)
                    resp.raise_for_status()
                feed = feedparser.parse(resp.text)
                for entry in feed.entries:
                    items.append(
                        RawItem(
                            source="arxiv",
                            url=(entry.get("link") or "").strip(),
                            title=(entry.get("title") or "").strip(),
                            content=self._clean_content(
                                entry.get("summary") or entry.get("description") or ""
                            ),
                            published_at=(
                                self._parse_date(entry)
                                if entry.get("published")
                                else datetime.now(timezone.utc)
                            ),
                            source_tags=[category],
                        )
                    )
            except Exception:
                continue
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
