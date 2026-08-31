import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("SHARP_OPERATIONS_ENV_FILE", ".env"),
        extra="ignore",
    )

    data_mode: str = "demo"
    demo_database_path: str = "data/sharp_demo.sqlite3"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    frontend_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
