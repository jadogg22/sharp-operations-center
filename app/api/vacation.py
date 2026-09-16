import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse

from app.api.common import attachment_response
from app.config import get_settings
from app.services.vacation import build_vacation_report, get_vacation_preview

router = APIRouter(prefix="/reports/vacation", tags=["Vacation"])


def require_vacation_access(
    supplied_password: Annotated[
        str | None, Header(alias="X-Report-Password")
    ] = None,
) -> None:
    """Protect employee balances without exposing them in production."""
    settings = get_settings()
    configured_password = settings.vacation_report_password
    if not configured_password:
        if settings.data_mode.strip().lower() == "production":
            raise HTTPException(
                status_code=503,
                detail="Vacation report password is not configured",
            )
        return
    if not supplied_password or not secrets.compare_digest(
        supplied_password, configured_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Vacation report password is incorrect",
            headers={"WWW-Authenticate": "ReportPassword"},
        )


@router.post("/unlock")
def vacation_unlock(
    _access: Annotated[None, Depends(require_vacation_access)] = None,
) -> dict:
    """Validate a vacation-report password without returning employee data."""
    return {"unlocked": True}


@router.get("/preview")
def vacation_preview(
    _access: Annotated[None, Depends(require_vacation_access)] = None,
) -> dict:
    """Return summary values before the CSV is downloaded."""
    rows = get_vacation_preview()
    return {
        "employee_count": len(rows),
        "total_amount_due": round(sum(row.amount_due for row in rows), 2),
        "rows": [
            {
                "employee_group": row.employee_group,
                "employee_id": row.employee_id,
                "employee_name": row.employee_name,
                "company_id": row.company_id,
                "vacation_hours_due": row.vacation_hours_due,
                "vacation_pay_rate": row.vacation_pay_rate,
                "amount_due": row.amount_due,
            }
            for row in rows
        ],
    }


@router.get(".csv")
def vacation_csv_download(
    _access: Annotated[None, Depends(require_vacation_access)] = None,
) -> StreamingResponse:
    """Download the current vacation balances as a spreadsheet-friendly CSV."""
    content, employee_count, total_amount_due = build_vacation_report()
    return attachment_response(
        content,
        "employee-vacation-balances.csv",
        "text/csv; charset=utf-8",
        {"X-Vacation-Employees": str(employee_count), "X-Vacation-Total": f"{total_amount_due:.2f}"},
    )
