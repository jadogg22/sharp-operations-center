"""Database connection selected by the showcase configuration."""

from app.config import get_settings
from app.db.demo import connect


def open_connection():
    """Open the active data source; the public build supports demo mode only."""
    if get_settings().data_mode != "demo":
        raise RuntimeError("Only demo mode is available in the public showcase")
    return connect()
