"""Production data source: read-only Mcloud SQL Server.

Queries live in the gitignored `sql/` folder next to the repository root.
They reference the company's real schema and are intentionally not committed.

Connection settings are validated before any query file is read, so a
production run on a fresh clone fails with a clear configuration message
instead of a missing-file error.
"""

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.db.connection import open_connection
from app.models import (
    CustomerBillingDate,
    CustomerStop,
    DailyRevenue,
    FleetCostEntry,
    LaneLoad,
)

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"

GL_ACCOUNT_TOKEN = "{{GL_ACCOUNT_PLACEHOLDERS}}"


def _customer_code() -> str:
    code = get_settings().customer_code.strip()
    if not code:
        raise RuntimeError(
            "CUSTOMER_CODE is not set; production mode needs it for the "
            "customer invoice queries"
        )
    return code


def _query(name: str) -> str:
    path = SQL_DIR / name
    if not path.exists():
        raise RuntimeError(
            f"Missing production query pack: {path}. The real SQL queries are"
            " not part of the public repository; see sql/README.md for the"
            " expected files."
        )
    return path.read_text(encoding="utf-8")


def _rows(
    name: str,
    parameters: tuple[Any, ...],
    *,
    gl_accounts: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Open the connection first, then load and run one named query."""
    connection = open_connection()
    try:
        sql = _query(name)
        if gl_accounts is not None:
            # Account names are selected from the server-side category
            # configuration; only the resulting values are passed as SQL
            # parameters.
            sql = sql.replace(
                GL_ACCOUNT_TOKEN, ", ".join("%s" for _ in gl_accounts)
            )
        cursor = connection.cursor()
        cursor.execute(sql, parameters)
        columns = [column[0].lower() for column in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
    finally:
        connection.close()


def _bounds(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    # SQL uses [start, end), which includes the complete end date without
    # relying on a time component or accidentally excluding midnight rows.
    return (
        datetime.combine(start_date, time.min),
        datetime.combine(end_date + timedelta(days=1), time.min),
    )


def fetch_lane_loads(start_date: date, end_date: date) -> list[LaneLoad]:
    rows = _rows("lane_profitability.sql", _bounds(start_date, end_date))
    return [LaneLoad(**row) for row in rows]


def fetch_customer_billing_dates(
    start_date: date, end_date: date
) -> list[CustomerBillingDate]:
    rows = _rows(
        "customer_billing_dates.sql",
        (_customer_code(), *_bounds(start_date, end_date)),
    )
    return [
        CustomerBillingDate(
            bill_date=row["bill_date"],
            order_count=int(row["order_count"] or 0),
            calculated_total=float(row["calculated_total"] or 0),
        )
        for row in rows
    ]


def fetch_fleet_cost_entries(
    start_date: date, end_date: date, gl_accounts: tuple[str, ...]
) -> list[FleetCostEntry]:
    if not gl_accounts:
        return []
    start_bound, end_bound = _bounds(start_date, end_date)
    rows = _rows(
        "fleet_cost_entries.sql",
        (*gl_accounts, start_bound, end_bound),
        gl_accounts=gl_accounts,
    )
    return [FleetCostEntry(**row) for row in rows]


def fetch_daily_revenue(start_date: date, end_date: date) -> list[DailyRevenue]:
    rows = _rows("fleet_revenue.sql", _bounds(start_date, end_date))
    return [
        DailyRevenue(
            revenue_date=row["revenue_date"],
            order_count=int(row["order_count"] or 0),
            revenue=float(row["revenue"] or 0),
        )
        for row in rows
    ]


def fetch_operations_performance(
    start_date: date, end_date: date
) -> list[dict[str, Any]]:
    """Fetch manager aggregates for an inclusive calendar date range."""
    return _rows(
        "operations_manager_performance.sql", _bounds(start_date, end_date)
    )


def fetch_operations_tractors() -> list[dict[str, Any]]:
    return _rows("operations_tractors.sql", ())


def fetch_operations_fleet_status() -> dict[str, Any]:
    rows = _rows("operations_fleet_status.sql", ())
    return rows[0] if rows else {}


def fetch_customer_stops(start_date: date, end_date: date) -> list[CustomerStop]:
    raw_rows = _rows(
        "customer_invoice.sql",
        (_customer_code(), *_bounds(start_date, end_date)),
    )
    if not raw_rows:
        return []

    # The invoice is reviewed and billed at order level, but its customer-facing
    # detail must retain every movement in sequence.
    rows_by_order: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        rows_by_order[(row["company_id"], row["order_id"])].append(row)

    result: list[CustomerStop] = []
    for order_rows in rows_by_order.values():
        order_rows.sort(key=lambda row: row["movement_sequence"])
        origin = order_rows[0]
        # The SQL aliases compensate for Mcloud's swapped pallet fields. Use the
        # pickup total as the denominator for proportional freight/fuel splits.
        total_pallets = sum(max(int(row["pallets_picked_up"] or 0), 0) for row in order_rows)

        for row in order_rows:
            pallets_dropped = max(int(row["pallets_dropped"] or 0), 0)
            allocation = pallets_dropped / total_pallets if total_pallets else 0.0
            result.append(
                CustomerStop(
                    company_id=row["company_id"],
                    order_id=row["order_id"],
                    ordered_date=row["ordered_date"],
                    delivery_date=row["delivery_date"],
                    bill_date=row["bill_date"],
                    origin_city=origin["stop_city"],
                    origin_state=origin["stop_state"],
                    origin_zip=origin["stop_zip"],
                    destination_city=row["stop_city"],
                    destination_state=row["stop_state"],
                    destination_zip=row["stop_zip"],
                    consignee=row["consignee"],
                    miles=float(row["miles"] or 0),
                    bol_number=row["bol_number"],
                    commodity=row["commodity"],
                    weight=float(row["weight"] or 0),
                    movement_sequence=int(row["movement_sequence"] or 0),
                    total_pallets=total_pallets,
                    pallets_dropped=pallets_dropped,
                    pallets_picked_up=max(int(row["pallets_picked_up"] or 0), 0),
                    freight_charge=float(row["freight_charge"] or 0),
                    fuel_surcharge=float(row["fuel_surcharge"] or 0),
                    extra_drops=float(row["extra_drops"] or 0),
                    extra_pickups=float(row["extra_pickups"] or 0),
                    other_charges=float(row["other_charges"] or 0),
                    other_charge_total=float(row["other_charge_total"] or 0),
                    total_charge=float(row["total_charge"] or 0),
                    allocated_fuel=float(row["fuel_surcharge"] or 0) * allocation,
                    allocated_freight=float(row["freight_charge"] or 0) * allocation,
                    trailer_number=row["trailer_number"],
                )
            )

    return result
