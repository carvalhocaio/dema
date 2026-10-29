from functools import lru_cache

from pydantic import PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DEMA_", env_file=".env", extra="ignore"
    )

    database_url: PostgresDsn = PostgresDsn(
        "postgresql://dema:dema@localhost:5432/dema"
    )
    redis_url: RedisDsn = RedisDsn("redis://localhost:6379/0")


@lru_cache
def get_settings() -> Settings:
    return Settings()
