import os
from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("SHARP_OPERATIONS_ENV_FILE", ".env"),
        extra="ignore",
    )

    # DATA_MODE=demo (default) serves the seeded SQLite showcase database.
    # DATA_MODE=production serves the read-only Mcloud SQL Server and requires
    # the SQL_* settings plus the local sql/ query pack.
    data_mode: str = "demo"
    demo_database_path: str = "data/sharp_demo.sqlite3"

    # Production data source. SQL_DATABASE also accepts the SQL_DB name used by
    # the legacy go-sharpGraphs environment file.
    sql_server: str = ""
    sql_port: int = 1433
    sql_database: str = Field(
        default="", validation_alias=AliasChoices("SQL_DATABASE", "SQL_DB")
    )
    sql_user: str = ""
    sql_password: str = ""

    # Mcloud customer code for the invoice/billing-dates queries. Kept out of
    # the repository so the committed query pack stays customer-agnostic.
    customer_code: str = ""

    @field_validator("sql_port", mode="before")
    @classmethod
    def _blank_port_becomes_default(cls, value):
        """Legacy .env files may carry SQL_PORT= empty; fall back to 1433."""
        if value is None or str(value).strip() in ("", "None"):
            return 1433
        return value

    # Fleet cost report categories: comma-separated "GL_ACCOUNT:Label" pairs.
    # The demo default matches the seeded SQLite data. Production deployments
    # set the real Mcloud GL account(s), e.g. 51601000:Fleet lease.
    fleet_cost_categories: str = "FLEET_LEASE:Fleet lease"

    # Application
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    frontend_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
