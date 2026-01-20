from dataclasses import dataclass
import os
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    qdrant_url: str
    qdrant_api_key: Optional[str]
    qdrant_collection: str
    llm_provider: str
    llm_api_key: Optional[str]
    openai_api_key: Optional[str]
    chat_model: str
    embedding_model: str
    ollama_base_url: str
    memory_top_k: int
    memory_dedup_threshold: float
    history_max_messages: int


def get_settings() -> Settings:
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY") or None
    qdrant_collection = os.getenv("QDRANT_COLLECTION", "memorias_miguel_urgiles")

    llm_provider = os.getenv("LLM_PROVIDER", "ollama").lower().strip()
    llm_api_key = os.getenv("LLM_API_KEY") or None
    openai_api_key = os.getenv("OPENAI_API_KEY") or None

    chat_model = os.getenv("CHAT_MODEL", "gemma3:4b")
    embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    ollama_base_url = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

    memory_top_k = int(os.getenv("MEMORY_TOP_K", "5"))
    memory_dedup_threshold = float(os.getenv("MEMORY_DEDUP_THRESHOLD", "0.90"))
    history_max_messages = int(os.getenv("HISTORY_MAX_MESSAGES", "8"))

    return Settings(
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
        qdrant_collection=qdrant_collection,
        llm_provider=llm_provider,
        llm_api_key=llm_api_key,
        openai_api_key=openai_api_key,
        chat_model=chat_model,
        embedding_model=embedding_model,
        ollama_base_url=ollama_base_url,
        memory_top_k=memory_top_k,
        memory_dedup_threshold=memory_dedup_threshold,
        history_max_messages=history_max_messages,
    )
