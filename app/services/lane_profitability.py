from datetime import date

from app.db.repository import fetch_lane_loads
from app.reports.lane_profitability import generate_lane_profitability_pdf
from app.services.errors import (
    DataSourceQueryError,
    InvalidReportError,
    ReportNotFoundError,
)


def build_lane_profitability_pdf(start_date: date, end_date: date) -> bytes:
    try:
        loads = fetch_lane_loads(start_date, end_date)
    except (RuntimeError, OSError) as error:
        raise DataSourceQueryError("Demo data query failed") from error

    if not loads:
        raise ReportNotFoundError("No lane data found for this period")

    try:
        return generate_lane_profitability_pdf(
            loads, start_date.isoformat(), end_date.isoformat()
        )
    except ValueError as error:
        raise InvalidReportError(str(error)) from error
