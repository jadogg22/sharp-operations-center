from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.services.operations_overview import build_operations_overview

router = APIRouter(tags=["Operations overview"])


@router.get("/overview")
def operations_overview(
    report_date: Annotated[date | None, Query()] = None,
) -> dict:
    """Return the owner-facing morning brief for the requested report date."""
    return build_operations_overview(report_date or datetime.now().astimezone().date())
