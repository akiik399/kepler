from openai import OpenAI
from sentence_transformers import SentenceTransformer

from kepler.config import Config


def create_openai_client(config: Config) -> OpenAI:
    return OpenAI(
        base_url="https://api.deepseek.com/v1",
        api_key=config.deepseek_api_key,
    )


def create_embedder(config: Config) -> SentenceTransformer:
    return SentenceTransformer(config.embedding_model)
