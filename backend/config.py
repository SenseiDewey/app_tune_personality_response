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
    elevenlabs_api_key: Optional[str]
    elevenlabs_voice_id: Optional[str]
    elevenlabs_tts_model: str
    elevenlabs_stt_model: str
    elevenlabs_output_format: Optional[str]


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

    elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY") or None
    elevenlabs_voice_id = os.getenv("ELEVENLABS_VOICE_ID") or None
    elevenlabs_tts_model = os.getenv("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2")
    elevenlabs_stt_model = os.getenv("ELEVENLABS_STT_MODEL", "scribe_v1")
    elevenlabs_output_format = os.getenv("ELEVENLABS_OUTPUT_FORMAT") or None

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
        elevenlabs_api_key=elevenlabs_api_key,
        elevenlabs_voice_id=elevenlabs_voice_id,
        elevenlabs_tts_model=elevenlabs_tts_model,
        elevenlabs_stt_model=elevenlabs_stt_model,
        elevenlabs_output_format=elevenlabs_output_format,
    )
