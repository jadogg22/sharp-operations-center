"""Application service for the employee vacation report."""

import re

from app.db.repository import fetch_vacation_balances
from app.models import VacationBalance
from app.reports.vacation import vacation_csv
from app.services.errors import DataSourceQueryError, ReportNotFoundError


def _company_sort_key(company_id: str) -> tuple[int, int, str]:
    """Keep TMS companies together in the same order used by operations."""
    normalized = company_id.strip().casefold()
    if normalized == "tms":
        return (0, 0, normalized)
    match = re.fullmatch(r"tms(\d+)", normalized)
    if match:
        return (0, int(match.group(1)), normalized)
    return (1, 0, normalized)


def _ordered_rows(rows: list[VacationBalance]) -> list[VacationBalance]:
    """Order both preview and CSV output by TMS type, then employee name."""
    return sorted(
        rows,
        key=lambda row: (
            _company_sort_key(row.company_id),
            row.employee_group.casefold(),
            row.employee_name.casefold(),
        ),
    )


def build_vacation_report() -> tuple[bytes, int, float]:
    """Load balances and return CSV bytes, employee count, and total payout."""
    try:
        rows = _ordered_rows(fetch_vacation_balances())
    except (RuntimeError, OSError) as error:
        raise DataSourceQueryError("Vacation data query failed") from error
    if not rows:
        raise ReportNotFoundError("No vacation balances found")
    return vacation_csv(rows), len(rows), round(sum(row.amount_due for row in rows), 2)


def get_vacation_preview() -> list:
    """Return domain rows for the interactive report preview."""
    try:
        rows = _ordered_rows(fetch_vacation_balances())
    except (RuntimeError, OSError) as error:
        raise DataSourceQueryError("Vacation data query failed") from error
    if not rows:
        raise ReportNotFoundError("No vacation balances found")
    return rows
