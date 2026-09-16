import secrets
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.common import attachment_response, validate_date_range
from app.config import get_settings
from app.reports.fleet_cost_revenue import (
    Granularity,
    fleet_cost_revenue_chart,
    fleet_cost_revenue_csv,
    serialize_analysis,
)
from app.services.fleet_cost_revenue import (
    build_fleet_cost_revenue_analysis,
    find_fleet_cost_accounts,
)

router = APIRouter(prefix="/reports", tags=["Fleet cost vs revenue"])


def require_revenue_access(
    supplied_password: Annotated[
        str | None, Header(alias="X-Report-Password")
    ] = None,
) -> None:
    """Protect live revenue data with a constant-time password comparison."""
    settings = get_settings()
    configured_password = settings.revenue_report_password
    if not configured_password:
        if settings.data_mode.strip().lower() == "production":
            raise HTTPException(
                status_code=503,
                detail="Revenue report password is not configured",
            )
        return
    if not supplied_password or not secrets.compare_digest(
        supplied_password, configured_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Revenue report password is incorrect",
            headers={"WWW-Authenticate": "ReportPassword"},
        )


def _analysis(
    start_date: date,
    end_date: date,
    granularity: Granularity,
    gl_accounts: list[str] | None,
) -> dict:
    """Validate inputs once so preview and download endpoints stay consistent."""
    validate_date_range(start_date, end_date)
    return build_fleet_cost_revenue_analysis(
        start_date,
        end_date,
        granularity,
        tuple(gl_accounts) if gl_accounts else None,
    )


@router.get("/fleet-cost-revenue/accounts")
def fleet_cost_account_search(
    search: Annotated[str, Query(max_length=60)] = "",
    _access: Annotated[None, Depends(require_revenue_access)] = None,
) -> dict:
    """Search and verify active GL accounts available to the report."""
    return find_fleet_cost_accounts(search)


@router.post("/fleet-cost-revenue/unlock")
def fleet_cost_revenue_unlock(
    _access: Annotated[None, Depends(require_revenue_access)] = None,
) -> dict:
    """Validate a password without returning any financial data."""
    return {"unlocked": True}


@router.get("/fleet-cost-revenue/preview")
def fleet_cost_revenue_preview(
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
    granularity: Annotated[Granularity, Query()] = "week",
    gl_accounts: Annotated[list[str] | None, Query(alias="gl_account")] = None,
    _access: Annotated[None, Depends(require_revenue_access)] = None,
) -> dict:
    """Return chart-ready fleet cost and revenue data."""
    return serialize_analysis(
        _analysis(start_date, end_date, granularity, gl_accounts)
    )


@router.get("/fleet-cost-revenue.csv")
def fleet_cost_revenue_csv_download(
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
    granularity: Annotated[Granularity, Query()] = "week",
    gl_accounts: Annotated[list[str] | None, Query(alias="gl_account")] = None,
    _access: Annotated[None, Depends(require_revenue_access)] = None,
) -> StreamingResponse:
    """Download the same period rows as a spreadsheet-friendly CSV."""
    filename = (
        f"fleet-cost-revenue-{granularity}-{start_date.isoformat()}-"
        f"{end_date.isoformat()}.csv"
    )
    return attachment_response(
        fleet_cost_revenue_csv(
            _analysis(start_date, end_date, granularity, gl_accounts)
        ),
        filename,
        "text/csv; charset=utf-8",
    )


@router.get("/fleet-cost-revenue.png")
def fleet_cost_revenue_chart_download(
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
    granularity: Annotated[Granularity, Query()] = "week",
    gl_accounts: Annotated[list[str] | None, Query(alias="gl_account")] = None,
    _access: Annotated[None, Depends(require_revenue_access)] = None,
) -> StreamingResponse:
    """Download a visual comparison of fleet cost, revenue, and margin."""
    filename = (
        f"fleet-cost-revenue-{granularity}-{start_date.isoformat()}-"
        f"{end_date.isoformat()}.png"
    )
    return attachment_response(
        fleet_cost_revenue_chart(
            _analysis(start_date, end_date, granularity, gl_accounts)
        ),
        filename,
        "image/png",
    )
