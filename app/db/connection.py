"""Database connection selected by DATA_MODE.

demo       -> seeded SQLite database (fictional data, ships with the repo)
production -> read-only Mcloud SQL Server (requires local .env and sql/ queries)
"""

from app.config import get_settings
from app.db.demo import connect


def open_connection():
    """Open the active data source based on the configured mode."""
    settings = get_settings()
    if settings.data_mode.strip().lower() == "production":
        return _open_production(settings)
    return connect()


def _open_production(settings):
    missing = [
        name
        for name, value in (
            ("SQL_SERVER", settings.sql_server),
            ("SQL_DATABASE", settings.sql_database),
            ("SQL_USER", settings.sql_user),
            ("SQL_PASSWORD", settings.sql_password),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "DATA_MODE=production is missing SQL settings: " + ", ".join(missing)
        )
    try:
        import pymssql
    except ImportError as exc:
        raise RuntimeError(
            "DATA_MODE=production requires pymssql. Install dependencies with 'uv sync'."
        ) from exc
    try:
        return pymssql.connect(
            server=settings.sql_server,
            port=str(settings.sql_port),
            user=settings.sql_user,
            password=settings.sql_password,
            database=settings.sql_database,
            login_timeout=15,
            timeout=60,
            autocommit=True,
        )
    except Exception as exc:
        raise RuntimeError(f"production database connection failed: {exc}") from exc
