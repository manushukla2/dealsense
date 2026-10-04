from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = the folder that contains "config/", "src/", ".env" etc.
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """All project settings, loaded from environment variables / the .env file."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Speech-to-text (Groq-hosted Whisper) ---
    groq_api_key: str = ""
    whisper_model: str = "whisper-large-v3"

    # --- Speaker labelling (pyannote via Hugging Face) ---
    hf_token: str = ""

    # --- Reasoning layer (LLM) ---
    anthropic_api_key: str = ""
    llm_model: str = ""

    # --- Audio handling ---
    max_chunk_mb: int = 20
    target_sample_rate: int = 16000

    # --- Database ---
    database_url: str = "postgresql://user:password@localhost:5432/dealsense"

    # --- App ---
    app_env: str = "development"
    log_level: str = "INFO"

    # ---------- Folder locations ----------
    @property
    def data_dir(self) -> Path:
        return BASE_DIR / "data"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def synthetic_dir(self) -> Path:
        return self.data_dir / "synthetic"

    @property
    def samples_dir(self) -> Path:
        return self.data_dir / "samples"

    @property
    def models_dir(self) -> Path:
        return BASE_DIR / "models"

    # ---------- Helpers ----------
    def ensure_dirs(self) -> None:
        """Create the data and model folders if they do not exist yet."""
        for folder in (
            self.raw_dir,
            self.processed_dir,
            self.synthetic_dir,
            self.samples_dir,
            self.models_dir,
        ):
            folder.mkdir(parents=True, exist_ok=True)

    def missing_keys(self) -> list[str]:
        """Return the names of required API keys that are still empty."""
        required = {
            "GROQ_API_KEY": self.groq_api_key,
            "ANTHROPIC_API_KEY": self.anthropic_api_key,
        }
        return [name for name, value in required.items() if not value]

    @property
    def max_chunk_bytes(self) -> int:
        return self.max_chunk_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Build the Settings object once and reuse it everywhere."""
    return Settings()


settings = get_settings()
