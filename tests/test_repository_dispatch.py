"""The repository dispatcher must pick the backend from DATA_MODE."""

from datetime import date

import pytest

from app.config import get_settings
from app.db import repository


@pytest.fixture(autouse=True)
def _fresh_settings(monkeypatch):
    """Re-resolve settings per test and restore the cache afterwards."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_defaults_to_demo_backend(monkeypatch):
    monkeypatch.delenv("DATA_MODE", raising=False)
    assert repository._is_production() is False
    loads = repository.fetch_lane_loads(date(2025, 1, 1), date(2027, 12, 31))
    assert loads, "demo database should seed lane loads"


def test_demo_backend_uses_sqlite(monkeypatch):
    monkeypatch.delenv("DATA_MODE", raising=False)
    revenue = repository.fetch_daily_revenue(date(2025, 1, 1), date(2027, 12, 31))
    assert isinstance(revenue, list)


def test_production_mode_without_credentials_fails_clearly(monkeypatch):
    monkeypatch.setenv("DATA_MODE", "production")
    monkeypatch.delenv("SQL_SERVER", raising=False)
    monkeypatch.delenv("SQL_DATABASE", raising=False)
    monkeypatch.delenv("SQL_DB", raising=False)
    monkeypatch.delenv("SQL_USER", raising=False)
    monkeypatch.delenv("SQL_PASSWORD", raising=False)
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="missing SQL settings"):
        repository.fetch_lane_loads(date(2026, 6, 1), date(2026, 6, 30))


def test_production_mode_alias_reads_sql_db(monkeypatch):
    """The legacy go-sharpGraphs SQL_DB variable name satisfies the config."""
    monkeypatch.setenv("DATA_MODE", "production")
    monkeypatch.setenv("SQL_SERVER", "192.0.2.10")
    monkeypatch.setenv("SQL_DB", "lme")
    monkeypatch.setenv("SQL_USER", "user")
    monkeypatch.setenv("SQL_PASSWORD", "pass")
    monkeypatch.setenv("SQL_PORT", "1433")
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.sql_database == "lme"
        assert repository._is_production() is True
    finally:
        monkeypatch.delenv("SQL_SERVER", raising=False)
        monkeypatch.delenv("SQL_DB", raising=False)
        monkeypatch.delenv("SQL_USER", raising=False)
        monkeypatch.delenv("SQL_PASSWORD", raising=False)
        monkeypatch.delenv("SQL_PORT", raising=False)
