"""Configuration for the private inference service."""
from functools import lru_cache
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_local_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_env()


class Settings:
    def __init__(self) -> None:
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_VISION_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5vl:3b"))
        self.ollama_timeout = float(os.getenv("OLLAMA_TIMEOUT", "300"))
        self.ollama_retries = max(0, min(int(os.getenv("OLLAMA_RETRIES", "3")), 5))
        self.ollama_retry_delay = max(0.0, float(os.getenv("OLLAMA_RETRY_DELAY", "2")))
        self.service_token = os.getenv("AI_SERVICE_TOKEN", "")
        default_rag = PROJECT_ROOT / "AI Chatbot" / "data" / "rag_knowledge_base"
        self.rag_dir = Path(os.getenv("RAG_DIR", str(default_rag)))
        if not self.rag_dir.is_absolute():
            self.rag_dir = PROJECT_ROOT / self.rag_dir
        self.rag_top_k = max(1, min(int(os.getenv("RAG_TOP_K", "5")), 10))
        self.max_image_bytes = int(os.getenv("AI_MAX_IMAGE_BYTES", str(10 * 1024 * 1024)))
        self.max_image_pixels = int(os.getenv("AI_MAX_IMAGE_PIXELS", str(20_000_000)))
        self.max_text_chars = int(os.getenv("AI_MAX_TEXT_CHARS", "2000"))
        self.max_context_chars = int(os.getenv("AI_MAX_CONTEXT_CHARS", "12000"))


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
