from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.api.common import attachment_response, validate_date_range
from app.reports.fleet_cost_revenue import (
    Granularity,
    fleet_cost_revenue_chart,
    fleet_cost_revenue_csv,
    serialize_analysis,
)
from app.services.fleet_cost_revenue import build_fleet_cost_revenue_analysis

router = APIRouter(prefix="/reports", tags=["Fleet cost vs revenue"])


def _analysis(
    start_date: date, end_date: date, granularity: Granularity
) -> dict:
    """Validate inputs once so preview and download endpoints stay consistent."""
    validate_date_range(start_date, end_date)
    return build_fleet_cost_revenue_analysis(start_date, end_date, granularity)


@router.get("/fleet-cost-revenue/preview")
def fleet_cost_revenue_preview(
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
    granularity: Annotated[Granularity, Query()] = "week",
) -> dict:
    """Return chart-ready fleet cost and revenue data."""
    return serialize_analysis(_analysis(start_date, end_date, granularity))


@router.get("/fleet-cost-revenue.csv")
def fleet_cost_revenue_csv_download(
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
    granularity: Annotated[Granularity, Query()] = "week",
) -> StreamingResponse:
    """Download the same period rows as a spreadsheet-friendly CSV."""
    filename = (
        f"fleet-cost-revenue-{granularity}-{start_date.isoformat()}-"
        f"{end_date.isoformat()}.csv"
    )
    return attachment_response(
        fleet_cost_revenue_csv(_analysis(start_date, end_date, granularity)),
        filename,
        "text/csv; charset=utf-8",
    )


@router.get("/fleet-cost-revenue.png")
def fleet_cost_revenue_chart_download(
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
    granularity: Annotated[Granularity, Query()] = "week",
) -> StreamingResponse:
    """Download a visual comparison of fleet cost, revenue, and margin."""
    filename = (
        f"fleet-cost-revenue-{granularity}-{start_date.isoformat()}-"
        f"{end_date.isoformat()}.png"
    )
    return attachment_response(
        fleet_cost_revenue_chart(_analysis(start_date, end_date, granularity)),
        filename,
        "image/png",
    )
