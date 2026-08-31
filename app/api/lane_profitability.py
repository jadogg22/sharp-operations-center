from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.api.common import attachment_response, validate_date_range
from app.services.lane_profitability import build_lane_profitability_pdf

router = APIRouter(prefix="/reports", tags=["Lane profitability"])


@router.get("/lane-profitability")
def lane_profitability(
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
) -> StreamingResponse:
    """Generate the lane profitability PDF for the requested date range."""
    validate_date_range(start_date, end_date)
    report = build_lane_profitability_pdf(start_date, end_date)
    filename = f"lane-profitability-{start_date.isoformat()}-{end_date.isoformat()}.pdf"
    return attachment_response(report, filename, "application/pdf")
