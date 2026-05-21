import hashlib
from datetime import datetime, timezone

import httpx

from kepler.config import Config
from kepler.ingest.base import RawItem


class HackerNewsScraper:
    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    def __init__(self, config: Config):
        self.config = config

    async def fetch(self) -> list[RawItem]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/topstories.json", timeout=30)
            resp.raise_for_status()
            story_ids = resp.json()[: self.config.hn_top_n]

            items: list[RawItem] = []
            for sid in story_ids:
                try:
                    story_resp = await client.get(
                        f"{self.BASE_URL}/item/{sid}.json", timeout=15
                    )
                    story_resp.raise_for_status()
                    story = story_resp.json()
                    if not story or story.get("type") != "story":
                        continue
                    title = (story.get("title") or "").strip()
                    url = (story.get("url") or "").strip() or (
                        f"https://news.ycombinator.com/item?id={sid}"
                    )
                    if not self._is_relevant(title):
                        continue
                    items.append(
                        RawItem(
                            source="hackernews",
                            url=url,
                            title=title,
                            content=(story.get("text") or title),
                            published_at=datetime.fromtimestamp(
                                story.get("time", 0), tz=timezone.utc
                            ),
                            source_tags=[],
                        )
                    )
                except Exception:
                    continue
            return items

    def _is_relevant(self, title: str) -> bool:
        lower = title.lower()
        return any(kw in lower for kw in self.config.hn_keywords)


def sha256_url(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()
