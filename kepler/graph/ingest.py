import logging
from collections.abc import Iterable

import numpy as np
from graphiti_core import Graphiti
from graphiti_core.driver.kuzu_driver import KuzuDriver
from graphiti_core.embedder import EmbedderClient
from graphiti_core.llm_client import OpenAIClient
from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer

from kepler.config import Config
from kepler.ingest.base import RawItem

logger = logging.getLogger(__name__)


class SentenceTransformerEmbedder(EmbedderClient):
    """Custom embedder wrapping sentence-transformers for local embedding."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    async def create(self, input_data: str | list[str] | Iterable[int] | Iterable[Iterable[int]]) -> list[float]:
        if isinstance(input_data, str):
            result = self.model.encode(input_data)
        else:
            result = self.model.encode(list(input_data))
        if isinstance(result, np.ndarray):
            return result.tolist()
        return list(result)

    async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(input_data_list)
        return [e.tolist() for e in embeddings]


def build_graphiti(config: Config) -> Graphiti:
    from pathlib import Path as _Path
    from graphiti_core.cross_encoder.bge_reranker_client import BGERerankerClient
    from graphiti_core.llm_client.config import LLMConfig

    # Ensure the directory for kuzu db exists
    _Path(config.kuzu_db_path).parent.mkdir(parents=True, exist_ok=True)

    llm_config = LLMConfig(
        api_key=config.deepseek_api_key,
        model=config.graphiti_llm_model,
        base_url="https://api.deepseek.com/v1",
        temperature=config.graphiti_llm_temperature,
    )

    llm_client = OpenAIClient(
        config=llm_config,
        client=AsyncOpenAI(
            base_url="https://api.deepseek.com/v1",
            api_key=config.deepseek_api_key,
        ),
    )

    embedder = SentenceTransformerEmbedder(model_name=config.embedding_model)

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

    return Graphiti(
        llm_client=llm_client,
        embedder=embedder,
        cross_encoder=BGERerankerClient(),
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
