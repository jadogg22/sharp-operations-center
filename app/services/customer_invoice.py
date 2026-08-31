from dataclasses import asdict, dataclass
from datetime import date, timedelta

from app.db.repository import (
    fetch_customer_billing_dates,
    fetch_customer_stops,
)
from app.models import CustomerStop
from app.reports.customer_invoice import (
    generate_customer_invoice,
    group_stops_by_order,
    invoice_total,
)
from app.services.errors import (
    DataSourceQueryError,
    InvalidReportError,
    ReportNotFoundError,
)


@dataclass(frozen=True)
class GeneratedCustomerInvoice:
    content: bytes
    filename: str
    calculated_total: float
    variance: float | None


def default_billing_window(today: date) -> tuple[date, date]:
    """Return the date-picker search window around the current Monday."""
    monday = today - timedelta(days=today.weekday())
    return monday - timedelta(weeks=2), monday + timedelta(days=4)


def list_recent_billing_dates(today: date) -> dict:
    """List bill dates in the recent review window for quick selection."""
    start_date, end_date = default_billing_window(today)
    try:
        billing_dates = fetch_customer_billing_dates(start_date, end_date)
    except (RuntimeError, OSError) as error:
        raise DataSourceQueryError("Demo data query failed") from error

    return {
        "start_date": start_date,
        "end_date": end_date,
        "dates": [asdict(item) for item in billing_dates],
    }


def build_customer_preview(bill_date: date, end_date: date) -> dict:
    """Build an editable order-level preview while retaining movement detail."""
    try:
        stops = fetch_customer_stops(bill_date, end_date)
    except (RuntimeError, OSError) as error:
        raise DataSourceQueryError("Demo data query failed") from error

    if not stops:
        detail = (
            f"No customer loads found from {bill_date.isoformat()} "
            f"through {end_date.isoformat()}"
            if end_date != bill_date
            else (
                "No customer loads found with bill date "
                f"{bill_date.isoformat()}"
            )
        )
        raise ReportNotFoundError(detail)

    # The source query is movement-level; the review screen is order-level so a
    # user can include/exclude or edit a bill without losing stop detail.
    orders = []
    for (company_id, order_id), order_stops in group_stops_by_order(stops).items():
        first = order_stops[0]
        last = order_stops[-1]
        orders.append(
            {
                "order_id": order_id,
                "company_id": company_id,
                "bol_number": first.bol_number,
                "origin": f"{first.origin_city}, {first.origin_state}".strip(", "),
                "destination": (
                    f"{last.destination_city}, {last.destination_state}".strip(", ")
                ),
                "trailer_number": first.trailer_number,
                "miles": first.miles,
                "total_pallets": first.total_pallets,
                "freight_charge": first.freight_charge,
                "fuel_surcharge": first.fuel_surcharge,
                "extra_drops": first.extra_drops,
                "extra_pickups": first.extra_pickups,
                "other_charges": first.other_charges,
                "other_charge_total": first.other_charge_total,
                "total_charge": first.total_charge,
                "stops": [asdict(stop) for stop in order_stops],
            }
        )

    return {
        "bill_date": bill_date,
        "end_date": end_date,
        "summary": {
            "order_count": len(orders),
            "row_count": len(stops),
            "calculated_total": invoice_total(stops),
        },
        "orders": orders,
    }


def build_customer_invoice(
    stops: list[CustomerStop],
    bill_date: date,
    end_date: date,
    invoice_number: str,
    expected_total: float | None,
) -> GeneratedCustomerInvoice:
    """Generate the reviewed workbook and report any expected-total variance."""
    calculated_total = invoice_total(stops)
    normalized_expected = (
        None if expected_total is None else round(expected_total, 2)
    )
    variance = (
        None
        if normalized_expected is None
        else round(calculated_total - normalized_expected, 2)
    )
    date_label: date | str = (
        bill_date
        if end_date == bill_date
        else f"{bill_date.isoformat()} through {end_date.isoformat()}"
    )

    try:
        content = generate_customer_invoice(
            stops,
            invoice_number,
            date_label,
            normalized_expected,
        )
    except ValueError as error:
        raise InvalidReportError(str(error)) from error

    suffix = invoice_number or (
        bill_date.isoformat()
        if end_date == bill_date
        else f"{bill_date.isoformat()}-{end_date.isoformat()}"
    )
    safe_suffix = "".join(
        character for character in suffix if character.isalnum() or character in "-_"
    )
    return GeneratedCustomerInvoice(
        content=content,
        filename=f"customer-invoice-{safe_suffix}.xlsx",
        calculated_total=calculated_total,
        variance=variance,
    )
