"""Typed, centralized application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from FRAUD_* environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="FRAUD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "fraud-service"
    environment: Literal["development", "test", "production"] = "development"
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    model_path: Path = Path("models/fraud_xgb_v3.joblib")
    block_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    review_band_width: float = Field(default=0.15, ge=0.0, le=1.0)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    @field_validator("model_path")
    @classmethod
    def model_must_exist(cls, value: Path) -> Path:
        """Resolve and validate the model artefact during startup."""
        path = value.expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.is_file():
            raise ValueError(f"model artefact does not exist: {path}")
        return path.resolve()

    @model_validator(mode="after")
    def review_band_must_fit_threshold(self) -> "Settings":
        if self.review_band_width > self.block_threshold:
            raise ValueError("review_band_width cannot exceed block_threshold")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings object per process."""
    return Settings()
