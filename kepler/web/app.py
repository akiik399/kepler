import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from kepler.config import Config
from kepler.graph.ingest import build_graphiti
from kepler.scheduler import start_scheduler, stop_scheduler
from kepler.web.api import router as api_router, init_routes

logger = logging.getLogger(__name__)


def create_app(config: Config | None = None) -> FastAPI:
    if config is None:
        config = Config()

    graphiti = build_graphiti(config)
    init_routes(graphiti)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Starting Kepler...")
        start_scheduler(config, graphiti)
        yield
        logger.info("Shutting down Kepler...")
        stop_scheduler()
        await graphiti.close()

    app = FastAPI(title="Kepler", lifespan=lifespan)
    app.include_router(api_router, prefix="/api")

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
