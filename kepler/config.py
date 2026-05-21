import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    deepseek_api_key: str = ""
    data_dir: Path = Path(os.getenv("KEPLER_DATA_DIR", "./data"))
    kuzu_db_path: str = field(default_factory=lambda: str(Path(os.getenv("KEPLER_DATA_DIR", "./data")) / "kuzu" / "kepler.db"))

    # Graphiti
    graphiti_semaphore_limit: int = 5
    graphiti_llm_model: str = "deepseek-chat"
    graphiti_llm_temperature: float = 0.0

    # Embedding (local)
    embedding_model: str = "all-MiniLM-L6-v2"

    # Scheduling
    schedule_hour: int = 8
    schedule_minute: int = 0

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Ingest
    hn_top_n: int = 100
    hn_keywords: list[str] = field(default_factory=lambda: ["agent", "llm", "ai", "gpt", "claude", "reasoning", "tool"])
    arxiv_categories: list[str] = field(default_factory=lambda: ["cs.AI", "cs.CL", "cs.MA"])
    max_content_length: int = 50000

    def __post_init__(self):
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.data_dir = Path(os.getenv("KEPLER_DATA_DIR", "./data"))
        self.kuzu_db_path = str(self.data_dir / "kuzu" / "kepler.db")
