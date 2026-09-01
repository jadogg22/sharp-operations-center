"""Application service for the employee vacation report."""

from app.db.repository import fetch_vacation_balances
from app.reports.vacation import vacation_csv
from app.services.errors import DataSourceQueryError, ReportNotFoundError


def build_vacation_report() -> tuple[bytes, int, float]:
    """Load balances and return CSV bytes, employee count, and total payout."""
    try:
        rows = fetch_vacation_balances()
    except (RuntimeError, OSError) as error:
        raise DataSourceQueryError("Vacation data query failed") from error
    if not rows:
        raise ReportNotFoundError("No vacation balances found")
    return vacation_csv(rows), len(rows), round(sum(row.amount_due for row in rows), 2)


def get_vacation_preview() -> list:
    """Return domain rows for the interactive report preview."""
    try:
        rows = fetch_vacation_balances()
    except (RuntimeError, OSError) as error:
        raise DataSourceQueryError("Vacation data query failed") from error
    if not rows:
        raise ReportNotFoundError("No vacation balances found")
    return rows
