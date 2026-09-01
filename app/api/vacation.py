from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.common import attachment_response
from app.services.vacation import build_vacation_report, get_vacation_preview

router = APIRouter(prefix="/reports/vacation", tags=["Vacation"])


@router.get("/preview")
def vacation_preview() -> dict:
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
def vacation_csv_download() -> StreamingResponse:
    """Download the current vacation balances as a spreadsheet-friendly CSV."""
    content, employee_count, total_amount_due = build_vacation_report()
    return attachment_response(
        content,
        "employee-vacation-balances.csv",
        "text/csv; charset=utf-8",
        {"X-Vacation-Employees": str(employee_count), "X-Vacation-Total": f"{total_amount_due:.2f}"},
    )
