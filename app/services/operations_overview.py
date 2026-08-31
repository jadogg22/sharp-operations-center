import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from app.db.repository import (
    fetch_operations_fleet_status,
    fetch_operations_performance,
    fetch_operations_tractors,
)
from app.services.errors import DataSourceQueryError

MANAGER_TEAMS = {
    "carter": "OTR",
    "blake": "OTR",
    "reed": "OTR",
    "brooks": "Local",
    "quinn": "Part time",
    "hayes": "Specialized",
}

MANAGER_NAMES = {
    "carter": "Alex Carter",
    "blake": "Jordan Blake",
    "reed": "Morgan Reed",
    "brooks": "Casey Brooks",
    "quinn": "Taylor Quinn",
    "hayes": "Riley Hayes",
}

@dataclass(frozen=True)
class OverviewConfig:
    """Business targets and alert rules used by the owner overview."""

    team_goals: dict[str, dict[str, float]]
    alert_stop_otp_pct: float = 98.0
    alert_deadhead_pct: float = 10.0
    max_alerts: int = 4


# Centralize the values most likely to change during a leadership review.
# Adjust this block when targets change; the calculations and UI labels will
# continue to consume the same configuration object.
OVERVIEW_CONFIG = OverviewConfig(
    team_goals={
        "OTR": {"mptpd": 565.0, "rptpd": 1250.0, "deadhead_pct": 10.0, "service_pct": 98.0},
        "Local": {"mptpd": 184.0, "rptpd": 500.0, "deadhead_pct": 45.0, "service_pct": 98.0},
    },
)

METHODOLOGY = [
    "The weekly window is Sunday at 12:00 AM through Saturday at 11:59 PM; the query implements this as Sunday 00:00 inclusive to the next Sunday 00:00 exclusive.",
    "Miles and deadhead use completed movement distance, based on tractor destination actual-arrival time, grouped by each tractor's current driver manager.",
    "Miles per truck and per-truck-per-day figures divide by distinct tractors with movement activity during the selected week; assigned and seated tractors remain separate capacity figures.",
    "Revenue is allocated to loaded movements by their share of the order's loaded miles.",
    "Stop OTP compares each stop's actual arrival with its scheduled late time; Order OTP uses the final delivery stop.",
    "Tractor seating and status use synthetic active-fleet assignments in SQLite.",
]


@dataclass(frozen=True)
class _OverviewWindows:
    """All calendar ranges and weekday counts used by one overview response."""

    report_date: date
    week_start: date
    week_end: date
    week_business_days: int
    month_start: date
    month_business_days: int
    month_total_business_days: int


def _business_days(start_date: date, end_date: date) -> int:
    """Count weekdays in an inclusive date range for per-day productivity rates."""
    if end_date < start_date:
        return 0
    return sum(
        1
        for offset in range((end_date - start_date).days + 1)
        if (start_date + timedelta(days=offset)).weekday() < 5
    )


def _ratio(numerator: float, denominator: float) -> float | None:
    """Return a safe ratio, preserving ``None`` when there is no denominator."""
    return numerator / denominator if denominator else None


def _percentage(numerator: float, denominator: float) -> float | None:
    """Return a safe percentage in the API's human-readable 0–100 scale."""
    ratio = _ratio(numerator, denominator)
    return ratio * 100 if ratio is not None else None


def _period_metrics(
    row: dict[str, Any], truck_denominator: int, business_days: int
) -> dict[str, Any]:
    """Normalize one SQL aggregate into dashboard metrics.

    Args:
        row: One manager's raw aggregate from ``operations_manager_performance``.
        truck_denominator: Number of trucks used for per-truck calculations.
        business_days: Weekdays used for per-truck-per-day calculations.

    Returns:
        A JSON-safe dictionary containing raw numerators and derived rates.
    """
    total_miles = float(row.get("total_miles") or 0)
    empty_miles = float(row.get("empty_miles") or 0)
    revenue = float(row.get("allocated_revenue") or 0)
    truck_days = truck_denominator * business_days
    return {
        "working_trucks": int(row.get("working_trucks") or 0),
        "movement_count": int(row.get("movement_count") or 0),
        "total_miles": total_miles,
        "loaded_miles": float(row.get("loaded_miles") or 0),
        "empty_miles": empty_miles,
        "miles_per_truck": _ratio(total_miles, truck_denominator),
        "mptpd": _ratio(total_miles, truck_days),
        "allocated_revenue": revenue,
        "rptpd": _ratio(revenue, truck_days),
        "deadhead_pct": _percentage(empty_miles, total_miles),
        "stop_otp": _percentage(
            float(row.get("on_time_stops") or 0),
            float(row.get("stop_appointments") or 0),
        ),
        "order_otp": _percentage(
            float(row.get("on_time_orders") or 0),
            float(row.get("order_appointments") or 0),
        ),
        "stop_appointments": int(row.get("stop_appointments") or 0),
        "order_appointments": int(row.get("order_appointments") or 0),
    }


def _aggregate(rows: list[dict[str, Any]], manager_ids: set[str]) -> dict[str, float]:
    """Add manager-level numerators before calculating the weighted OTR summary."""
    selected = [row for row in rows if row.get("manager_id") in manager_ids]
    fields = (
        "total_miles",
        "empty_miles",
        "allocated_revenue",
        "stop_appointments",
        "on_time_stops",
        "order_appointments",
        "on_time_orders",
    )
    return {
        field: sum(float(row.get(field) or 0) for row in selected)
        for field in fields
    }


def _overview_windows(report_date: date) -> _OverviewWindows:
    """Resolve the full operating week and month-to-date calendar windows.

    Args:
        report_date: Date selected by the user; it anchors both windows.

    Returns:
        Calendar boundaries and weekday counts used by all downstream builders.
    """
    days_since_sunday = (report_date.weekday() + 1) % 7
    week_start = report_date - timedelta(days=days_since_sunday)
    week_end = week_start + timedelta(days=6)
    month_start = report_date.replace(day=1)
    month_end = report_date.replace(
        day=calendar.monthrange(report_date.year, report_date.month)[1]
    )
    return _OverviewWindows(
        report_date=report_date,
        week_start=week_start,
        week_end=week_end,
        week_business_days=max(_business_days(week_start, week_end), 1),
        month_start=month_start,
        month_business_days=max(_business_days(month_start, report_date), 1),
        month_total_business_days=_business_days(month_start, month_end),
    )


def _load_sources(
    windows: _OverviewWindows,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Load the four independent datasets needed by the overview.

    Args:
        windows: Previously resolved weekly and month-to-date date ranges.

    Returns:
        Weekly movement rows, month-to-date movement rows, current tractor rows,
        and the current fleet-status aggregate, in that order.

    Raises:
        DataSourceQueryError: If the configured database adapter fails.
    """
    try:
        return (
            fetch_operations_performance(windows.week_start, windows.week_end),
            fetch_operations_performance(windows.month_start, windows.report_date),
            fetch_operations_tractors(),
            fetch_operations_fleet_status(),
        )
    except (RuntimeError, OSError) as error:
        raise DataSourceQueryError("Demo operations query failed") from error


def _build_manager(
    manager_id: str,
    team: str,
    week_by_manager: dict[str, dict[str, Any]],
    month_by_manager: dict[str, dict[str, Any]],
    tractors_by_manager: dict[str, dict[str, Any]],
    windows: _OverviewWindows,
) -> dict[str, Any]:
    """Combine movement, capacity, and target data for one manager.

    The returned object is already shaped for the frontend. A manager with no
    movement row is still emitted so the dashboard has a stable table order.
    """
    tractor = tractors_by_manager.get(manager_id, {})
    assigned = int(tractor.get("assigned_trucks") or 0)
    seated = int(tractor.get("seated_trucks") or 0)
    week_row = week_by_manager.get(manager_id, {})
    # The legacy scorecard's "# Trucks" behaves like distinct tractors that
    # moved during the selected week. Keep assigned/seated counts separate
    # for capacity, and use active weekly tractors for per-truck rates.
    truck_denominator = int(week_row.get("working_trucks") or 0) or assigned
    week = _period_metrics(week_row, truck_denominator, windows.week_business_days)
    month = _period_metrics(
        month_by_manager.get(manager_id, {}),
        truck_denominator,
        windows.month_business_days,
    )
    goal = OVERVIEW_CONFIG.team_goals.get(team)
    pace_pct = month["mptpd"] / goal["mptpd"] * 100 if goal and month["mptpd"] is not None else None
    return {
        "manager_id": manager_id,
        "name": MANAGER_NAMES.get(
            manager_id,
            str(tractor.get("manager_name") or manager_id).title(),
        ),
        "team": team,
        "assigned_trucks": assigned,
        "seated_trucks": seated,
        "utilization_pct": _percentage(seated, assigned),
        "week": week,
        "month": month,
        "month_mileage_pace_pct": pace_pct,
        "goals": goal,
    }


def _build_managers(
    week_rows: list[dict[str, Any]],
    month_rows: list[dict[str, Any]],
    tractor_rows: list[dict[str, Any]],
    windows: _OverviewWindows,
) -> list[dict[str, Any]]:
    """Build the stable manager list consumed by the scorecard.

    Missing SQL rows become zero-valued metric objects rather than disappearing
    from the response, which keeps the table and capacity panels aligned.
    """
    week_by_manager = {row["manager_id"]: row for row in week_rows}
    month_by_manager = {row["manager_id"]: row for row in month_rows}
    tractors_by_manager = {row["manager_id"]: row for row in tractor_rows}
    return [
        _build_manager(
            manager_id,
            team,
            week_by_manager,
            month_by_manager,
            tractors_by_manager,
            windows,
        )
        for manager_id, team in MANAGER_TEAMS.items()
    ]


def _build_summary(
    week_rows: list[dict[str, Any]],
    managers: list[dict[str, Any]],
    fleet_status: dict[str, Any],
) -> dict[str, Any]:
    """Create weighted OTR performance and current fleet-capacity metrics.

    OTR numerators are summed first and divided once at the end, preventing a
    simple average of manager percentages from distorting the team result.
    """
    otr_ids = {
        manager_id for manager_id, team in MANAGER_TEAMS.items() if team == "OTR"
    }
    otr_week = _aggregate(week_rows, otr_ids)
    otr_managers = [manager for manager in managers if manager["team"] == "OTR"]
    otr_assigned = sum(manager["assigned_trucks"] for manager in otr_managers)
    otr_working = sum(manager["week"]["working_trucks"] for manager in otr_managers)
    active_fleet = int(fleet_status.get("active_fleet") or 0)
    seated_tractors = int(fleet_status.get("seated_tractors") or 0)
    return {
        "otr_assigned_trucks": otr_assigned,
        "otr_working_trucks": otr_working,
        "otr_miles_per_truck": _ratio(otr_week["total_miles"], otr_working or otr_assigned),
        "otr_deadhead_pct": _percentage(otr_week["empty_miles"], otr_week["total_miles"]),
        "otr_stop_otp": _percentage(otr_week["on_time_stops"], otr_week["stop_appointments"]),
        "otr_order_otp": _percentage(otr_week["on_time_orders"], otr_week["order_appointments"]),
        "active_fleet": active_fleet,
        "seated_tractors": seated_tractors,
        "seating_pct": _percentage(seated_tractors, active_fleet),
        "dispatch_ready": int(fleet_status.get("dispatch_ready") or 0),
        "ready_to_seat": int(fleet_status.get("ready_to_seat") or 0),
        "out_of_service": int(fleet_status.get("out_of_service") or 0),
        "special_hold": int(fleet_status.get("special_hold") or 0),
    }


def _build_alerts(summary: dict[str, Any]) -> list[dict[str, str]]:
    """Translate summary exceptions into a short, configurable priority list.

    The alert list is deliberately capped so the owner sees the most useful
    signals first instead of receiving an unfiltered dump of every metric.
    """
    alerts: list[dict[str, str]] = []
    stop_otp = summary["otr_stop_otp"]
    stop_goal = OVERVIEW_CONFIG.alert_stop_otp_pct
    if stop_otp is not None and stop_otp < stop_goal:
        alerts.append({"level": "urgent", "title": "OTR stop service is below goal", "detail": f"{stop_otp:.1f}% on time versus the {stop_goal:.0f}% standard."})
    seat_gap = max(summary["active_fleet"] - summary["seated_tractors"], 0)
    if seat_gap:
        alerts.append({"level": "watch", "title": f"{seat_gap} active tractors are not seated", "detail": f"Fleet seating is {summary['seating_pct']:.1f}%."})
    if summary["out_of_service"]:
        alerts.append({"level": "watch", "title": f"{summary['out_of_service']} tractors are out of service", "detail": "Review maintenance status and expected return dates."})
    deadhead = summary["otr_deadhead_pct"]
    deadhead_goal = OVERVIEW_CONFIG.alert_deadhead_pct
    if deadhead is not None:
        alerts.append({
            "level": "positive" if deadhead <= deadhead_goal else "urgent",
            "title": "OTR deadhead is controlled" if deadhead <= deadhead_goal else "OTR deadhead is above goal",
            "detail": f"{deadhead:.1f}% empty miles versus the under-{deadhead_goal:.0f}% target.",
        })
    return alerts[: OVERVIEW_CONFIG.max_alerts]


def build_operations_overview(report_date: date) -> dict[str, Any]:
    """Build weekly operating results, month-to-date pace, and capacity alerts.

    The selected date identifies the operating week and the month-to-date
    cutoff. Weekly movement data is intentionally queried through Saturday,
    while month-to-date data stops on the selected date.
    """
    windows = _overview_windows(report_date)
    week_rows, month_rows, tractor_rows, fleet_status = _load_sources(windows)
    managers = _build_managers(week_rows, month_rows, tractor_rows, windows)
    summary = _build_summary(week_rows, managers, fleet_status)

    return {
        "report_date": report_date.isoformat(),
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "week_start": windows.week_start.isoformat(),
        "week_end": windows.week_end.isoformat(),
        "month_start": windows.month_start.isoformat(),
        "business_days_elapsed": windows.month_business_days,
        "business_days_total": windows.month_total_business_days,
        "summary": summary,
        "managers": managers,
        "alerts": _build_alerts(summary),
        "methodology": METHODOLOGY,
    }
