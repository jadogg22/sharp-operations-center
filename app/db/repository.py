"""Repository interface backed by the public showcase's SQLite demo database.

The production project uses the same function boundary with a read-only SQL
adapter. That private adapter and its schema-specific queries are intentionally
not included here.
"""

from datetime import date
from typing import Any

from app.db.demo import connect
from app.models import (
    CustomerBillingDate,
    CustomerStop,
    DailyRevenue,
    FleetCostEntry,
    LaneLoad,
)


def _rows(sql: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    connection = connect()
    try:
        return [dict(row) for row in connection.execute(sql, parameters).fetchall()]
    finally:
        connection.close()


def _date_value(value: str | date | None) -> date | None:
    """Convert SQLite's ISO date text into the domain model's date type."""
    return date.fromisoformat(value) if isinstance(value, str) else value


def fetch_lane_loads(start_date: date, end_date: date) -> list[LaneLoad]:
    rows = _rows(
        "SELECT * FROM lane_loads WHERE bill_date BETWEEN ? AND ? ORDER BY bill_date, order_id",
        (str(start_date), str(end_date)),
    )
    return [LaneLoad(**{**row, "bill_date": _date_value(row["bill_date"])}) for row in rows]


def fetch_customer_billing_dates(start_date: date, end_date: date) -> list[CustomerBillingDate]:
    rows = _rows(
        """SELECT bill_date, COUNT(DISTINCT order_id) AS order_count,
                  SUM(order_total) AS calculated_total
           FROM (
             SELECT bill_date, company_id, order_id, MAX(total_charge) AS order_total
             FROM invoice_stops WHERE bill_date BETWEEN ? AND ?
             GROUP BY bill_date, company_id, order_id
           ) GROUP BY bill_date ORDER BY bill_date DESC""",
        (str(start_date), str(end_date)),
    )
    return [
        CustomerBillingDate(**{**row, "bill_date": _date_value(row["bill_date"])})
        for row in rows
    ]


def fetch_customer_stops(start_date: date, end_date: date) -> list[CustomerStop]:
    rows = _rows(
        """SELECT company_id, order_id, ordered_date, delivery_date, bill_date,
                  origin_city, origin_state, origin_zip, destination_city,
                  destination_state, destination_zip, consignee, miles, bol_number,
                  commodity, weight, movement_sequence, total_pallets,
                  pallets_dropped, pallets_picked_up, freight_charge, fuel_surcharge,
                  extra_drops, extra_pickups, other_charges, other_charge_total,
                  total_charge, allocated_fuel, allocated_freight, trailer_number
           FROM invoice_stops WHERE bill_date BETWEEN ? AND ?
           ORDER BY bill_date, order_id, movement_sequence""",
        (str(start_date), str(end_date)),
    )
    return [
        CustomerStop(
            **{
                **row,
                "ordered_date": _date_value(row["ordered_date"]),
                "delivery_date": _date_value(row["delivery_date"]),
                "bill_date": _date_value(row["bill_date"]),
            }
        )
        for row in rows
    ]


def fetch_fleet_cost_entries(
    start_date: date, end_date: date, gl_accounts: tuple[str, ...]
) -> list[FleetCostEntry]:
    if not gl_accounts:
        return []
    placeholders = ", ".join("?" for _ in gl_accounts)
    rows = _rows(
        f"""SELECT gl_account, transaction_date, amount FROM fleet_cost_entries
             WHERE gl_account IN ({placeholders}) AND transaction_date BETWEEN ? AND ?
             ORDER BY transaction_date""",
        (*gl_accounts, str(start_date), str(end_date)),
    )
    return [
        FleetCostEntry(
            **{**row, "transaction_date": _date_value(row["transaction_date"])}
        )
        for row in rows
    ]


def fetch_daily_revenue(start_date: date, end_date: date) -> list[DailyRevenue]:
    rows = _rows(
        "SELECT revenue_date, order_count, revenue FROM daily_revenue WHERE revenue_date BETWEEN ? AND ? ORDER BY revenue_date",
        (str(start_date), str(end_date)),
    )
    return [
        DailyRevenue(**{**row, "revenue_date": _date_value(row["revenue_date"])})
        for row in rows
    ]


def fetch_operations_performance(start_date: date, end_date: date) -> list[dict[str, Any]]:
    return _rows(
        """SELECT manager_id, MAX(working_trucks) AS working_trucks,
                  SUM(movement_count) AS movement_count, SUM(total_miles) AS total_miles,
                  SUM(loaded_miles) AS loaded_miles, SUM(empty_miles) AS empty_miles,
                  SUM(allocated_revenue) AS allocated_revenue,
                  SUM(stop_appointments) AS stop_appointments,
                  SUM(on_time_stops) AS on_time_stops,
                  SUM(order_appointments) AS order_appointments,
                  SUM(on_time_orders) AS on_time_orders
           FROM operations_daily WHERE activity_date BETWEEN ? AND ?
           GROUP BY manager_id ORDER BY manager_id""",
        (str(start_date), str(end_date)),
    )


def fetch_operations_tractors() -> list[dict[str, Any]]:
    return _rows("SELECT * FROM operations_tractors ORDER BY manager_id")


def fetch_operations_fleet_status() -> dict[str, Any]:
    rows = _rows(
        "SELECT active_fleet, seated_tractors, dispatch_ready, ready_to_seat, out_of_service, special_hold FROM fleet_status WHERE id = 1"
    )
    return rows[0] if rows else {}
