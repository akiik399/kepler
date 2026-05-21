from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


SourceType = Literal["hackernews", "arxiv", "huggingface"]


@dataclass
class RawItem:
    source: SourceType
    url: str
    title: str
    content: str
    published_at: datetime
    source_tags: list[str] = field(default_factory=list)
