import hashlib

from kepler.ingest.base import RawItem


def sha256_url(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def deduplicate(items: list[RawItem], existing_url_hashes: set[str]) -> list[RawItem]:
    seen = set(existing_url_hashes)
    result: list[RawItem] = []
    for item in items:
        h = sha256_url(item.url)
        if h not in seen:
            seen.add(h)
            result.append(item)
    return result


def filter_content_length(items: list[RawItem], max_length: int = 50000) -> list[RawItem]:
    for item in items:
        if len(item.content) > max_length:
            item.content = item.content[:max_length]
    return items
