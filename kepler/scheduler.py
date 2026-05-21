import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from graphiti_core import Graphiti

from kepler.config import Config

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def daily_ingest(config: Config, graphiti: Graphiti):
    """Fetch all sources and ingest into the knowledge graph."""
    logger.info("Starting daily ingest...")

    from kepler.ingest.hackernews import HackerNewsScraper
    from kepler.ingest.arxiv import ArxivScraper
    from kepler.ingest.huggingface import HFBlogScraper
    from kepler.ingest.extractor import deduplicate, filter_content_length
    from kepler.graph.ingest import ingest_items

    scrapers = [
        HackerNewsScraper(config),
        ArxivScraper(config),
        HFBlogScraper(config),
    ]

    all_items: list = []
    results = await asyncio.gather(
        *(s.fetch() for s in scrapers), return_exceptions=True
    )
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning("Scraper %d failed: %s", i, result)
        elif result is None:
            logger.warning("Scraper %d returned None", i)
        else:
            all_items.extend(result)

    if not all_items:
        logger.warning("No items fetched from any source")
        return

    filtered = filter_content_length(all_items, config.max_content_length)

    if not filtered:
        logger.info("No new items to ingest")
        return

    count = await ingest_items(graphiti, filtered)
    logger.info("Daily ingest complete: %d items ingested", count)


def start_scheduler(config: Config, graphiti: Graphiti):
    scheduler.add_job(
        daily_ingest,
        "cron",
        hour=config.schedule_hour,
        minute=config.schedule_minute,
        args=[config, graphiti],
        id="daily_ingest",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started, daily ingest at %02d:%02d",
        config.schedule_hour,
        config.schedule_minute,
    )


def stop_scheduler():
    scheduler.shutdown(wait=False)
