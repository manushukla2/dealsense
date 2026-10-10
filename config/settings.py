from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        env_file_override=False,
        extra="ignore",
    )

    groq_api_key: str = ""
    whisper_model: str = "whisper-large-v3"
    groq_llm_model: str = "openai/gpt-oss-120b"
    hf_token: str = ""
    max_chunk_mb: int = 20
    target_sample_rate: int = 16000
    database_url: str = "postgresql://user:password@localhost:5432/dealsense"
    app_env: str = "development"
    log_level: str = "INFO"

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

    def ensure_dirs(self) -> None:
        for folder in (
            self.raw_dir,
            self.processed_dir,
            self.synthetic_dir,
            self.samples_dir,
            self.models_dir,
        ):
            folder.mkdir(parents=True, exist_ok=True)

    def missing_keys(self) -> list[str]:
        return [name for name, value in {
            "GROQ_API_KEY": self.groq_api_key,
        }.items() if not value]

    @property
    def max_chunk_bytes(self) -> int:
        return self.max_chunk_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
