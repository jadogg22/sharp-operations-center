import calendar
from datetime import date

from app.db.repository import fetch_daily_revenue, fetch_fleet_cost_entries
from app.reports.fleet_cost_revenue import (
    FLEET_COST_CATEGORIES,
    Granularity,
    analyze_fleet_cost_revenue,
)
from app.services.errors import DataSourceQueryError, ReportNotFoundError


def build_fleet_cost_revenue_analysis(
    start_date: date, end_date: date, granularity: Granularity = "week"
) -> dict:
    """Fetch source data and turn it into the requested fleet-cost view.

    GL costs are queried for complete source months because a monthly posting
    must be prorated across the selected calendar days before grouping.
    """
    # Query complete calendar months because a selected range may begin/end in
    # the middle of a month and the report prorates the monthly GL posting.
    cost_start = start_date.replace(day=1)
    cost_end = end_date.replace(
        day=calendar.monthrange(end_date.year, end_date.month)[1]
    )
    gl_accounts = tuple(category.gl_account for category in FLEET_COST_CATEGORIES)

    try:
        cost_entries = fetch_fleet_cost_entries(cost_start, cost_end, gl_accounts)
        daily_revenue = fetch_daily_revenue(start_date, end_date)
    except (RuntimeError, OSError) as error:
        raise DataSourceQueryError("Demo data query failed") from error

    if not cost_entries:
        raise ReportNotFoundError("No fleet cost entries found for this period")

    return analyze_fleet_cost_revenue(
        start_date, end_date, cost_entries, daily_revenue, granularity
    )
