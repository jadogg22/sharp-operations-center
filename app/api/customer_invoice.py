from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.api.common import attachment_response, validate_date_range
from app.api.schemas import CustomerInvoiceRequest
from app.models import CustomerStop
from app.services.customer_invoice import (
    build_customer_invoice,
    build_customer_preview,
    list_recent_billing_dates,
)

router = APIRouter(prefix="/reports/customer-invoice", tags=["Customer invoice"])


@router.get("/preview")
def customer_invoice_preview(
    bill_date: Annotated[date, Query()],
    end_date: Annotated[date | None, Query()] = None,
) -> dict:
    """Return a reviewable preview for one bill date or an optional date range."""
    range_end = end_date or bill_date
    validate_date_range(bill_date, range_end)
    return build_customer_preview(bill_date, range_end)


@router.get("/billing-dates")
def customer_billing_dates() -> dict:
    """Return recent bill dates that can be selected without manual entry."""
    today = datetime.now(UTC).astimezone().date()
    return list_recent_billing_dates(today)


@router.post("")
def customer_invoice(request: CustomerInvoiceRequest) -> StreamingResponse:
    """Generate the reviewed invoice workbook and expose variance headers."""
    range_end = request.end_date or request.bill_date
    validate_date_range(request.bill_date, range_end)
    reviewed_stops = [CustomerStop(**row.model_dump()) for row in request.rows]
    generated = build_customer_invoice(
        reviewed_stops,
        request.bill_date,
        range_end,
        request.invoice_number.strip(),
        request.expected_total,
    )
    headers = {"X-Invoice-Total": f"{generated.calculated_total:.2f}"}
    if generated.variance is not None:
        headers["X-Invoice-Variance"] = f"{generated.variance:.2f}"
    return attachment_response(
        generated.content,
        generated.filename,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers,
    )
