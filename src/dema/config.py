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
    signing_key: SecretStr | None = None
    speed_factor: float = Field(default=120.0, gt=0)
    batch_size: int = Field(default=500, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
