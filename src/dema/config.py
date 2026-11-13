from functools import lru_cache

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DEMA_", env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    database_url: PostgresDsn = PostgresDsn(
        "postgresql://dema:dema@localhost:5432/dema"
    )
    redis_url: RedisDsn = RedisDsn("redis://localhost:6379/0")
    year: int = Field(default=2026, ge=1)
    allow_runs: bool = False
    signing_key: SecretStr | None = None
    speed_factor: float = Field(default=120.0, gt=0)
    batch_size: int = Field(default=500, gt=0)
    broadcast_interval: float = Field(default=0.5, gt=0)
    pipeline_interval: float = Field(default=1.0, gt=0)
    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
