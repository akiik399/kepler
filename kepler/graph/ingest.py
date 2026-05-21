import logging
import os as _os
from collections.abc import Iterable
from pathlib import Path as _Path

import numpy as np
from graphiti_core import Graphiti
from graphiti_core.driver.kuzu_driver import KuzuDriver
from graphiti_core.embedder import EmbedderClient
from kepler.graph.deepseek_client import DeepSeekClient
from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer

from kepler.config import Config
from kepler.ingest.base import RawItem

logger = logging.getLogger(__name__)

# Resolve cached model path to avoid network access on startup
_SENTENCE_TRANSFORMERS_CACHE = (
    _Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / "models--sentence-transformers--all-MiniLM-L6-v2"
    / "snapshots"
)
_MODEL_PATH: str | None = None
if _SENTENCE_TRANSFORMERS_CACHE.exists():
    snaps = list(_SENTENCE_TRANSFORMERS_CACHE.iterdir())
    if snaps:
        _MODEL_PATH = str(snaps[0])


class SentenceTransformerEmbedder(EmbedderClient):
    """Custom embedder wrapping sentence-transformers for local embedding."""

    def __init__(self, model_path: str | None = _MODEL_PATH):
        if model_path is None:
            model_path = "all-MiniLM-L6-v2"
        self.model = SentenceTransformer(model_path)

    async def create(self, input_data: str | list[str] | Iterable[int] | Iterable[Iterable[int]]) -> list[float]:
        if isinstance(input_data, str):
            texts = [input_data]
        else:
            texts = list(input_data)
        result = self.model.encode(texts)
        if isinstance(result, np.ndarray):
            return result[0].tolist()
        return list(result[0])

    async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(input_data_list)
        return [e.tolist() for e in embeddings]


def build_graphiti(config: Config) -> Graphiti:
    from graphiti_core.llm_client.config import LLMConfig

    # Ensure the directory for kuzu db exists
    _Path(config.kuzu_db_path).parent.mkdir(parents=True, exist_ok=True)

    llm_config = LLMConfig(
        api_key=config.deepseek_api_key,
        model=config.graphiti_llm_model,
        small_model="deepseek-v4-flash",

        base_url="https://api.deepseek.com/v1",
        temperature=config.graphiti_llm_temperature,
        max_tokens=16384,
    )

    llm_client = DeepSeekClient(
        config=llm_config,
        client=AsyncOpenAI(
            base_url="https://api.deepseek.com/v1",
            api_key=config.deepseek_api_key,
        ),
    )

    embedder = SentenceTransformerEmbedder()

    graph_driver = KuzuDriver(db=config.kuzu_db_path)

    # Create FTS indices (KuzuDriver's build_indices_and_constraints is a no-op)
    try:
        import kuzu
        conn = kuzu.Connection(graph_driver.db)
        for table, name, cols in [
            ("Episodic", "episode_content", ["content", "source", "source_description"]),
            ("Entity", "node_name_and_summary", ["name", "summary"]),
            ("RelatesToNode_", "edge_name_and_fact", ["name", "fact"]),
            ("Community", "community_name", ["name"]),
        ]:
            try:
                conn.execute(f"CALL CREATE_FTS_INDEX('{table}', '{name}', {cols})")
            except Exception:
                pass
        conn.close()
        logger.info("Kuzu FTS indices created")
    except Exception as e:
        logger.warning("Failed to create FTS indices: %s", e)

    from graphiti_core.cross_encoder.client import CrossEncoderClient

    class PassThroughCrossEncoder(CrossEncoderClient):
        async def rank(self, query: str, passages: list[str]) -> list[tuple[str, float]]:
            return [(p, 1.0) for p in passages]

    return Graphiti(
        llm_client=llm_client,
        embedder=embedder,
        cross_encoder=PassThroughCrossEncoder(),
        graph_driver=graph_driver,
        max_coroutines=config.graphiti_semaphore_limit,
    )


async def ingest_items(graphiti: Graphiti, items: list[RawItem]) -> int:
    """Ingest a batch of items into the knowledge graph."""
    from graphiti_core.nodes import EpisodeType
    from graphiti_core.utils.bulk_utils import RawEpisode

    episodes = [
        RawEpisode(
            name=item.title[:255],
            content=item.content,
            source_description=f"{item.source}: {item.url}",
            source=EpisodeType.text,
            reference_time=item.published_at,
        )
        for item in items
    ]

    try:
        result = await graphiti.add_episode_bulk(episodes)
        logger.info("Ingested %d episodes", len(result.episodes))
        return len(result.episodes)
    except Exception as e:
        logger.warning("Failed to ingest batch: %s", e)
        return 0
