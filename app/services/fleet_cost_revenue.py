import calendar
import re
from datetime import date

from app.db.repository import (
    fetch_daily_revenue,
    fetch_fleet_cost_account_details,
    fetch_fleet_cost_entries,
)
from app.db.repository import search_fleet_cost_accounts as search_account_catalog
from app.reports.fleet_cost_revenue import (
    FleetCostCategory,
    Granularity,
    analyze_fleet_cost_revenue,
    load_default_cost_categories,
)
from app.services.errors import DataSourceQueryError, InvalidReportError

ACCOUNT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,20}$")
MAX_SELECTED_ACCOUNTS = 8
MAX_ACCOUNT_SEARCH_LENGTH = 60


def _normalize_account_ids(gl_accounts: tuple[str, ...] | None) -> tuple[str, ...]:
    """Normalize, deduplicate, and cap account IDs supplied by the browser."""
    requested = gl_accounts or tuple(
        category.gl_account for category in load_default_cost_categories()
    )
    normalized: list[str] = []
    for value in requested:
        account = value.strip().upper()
        if not account or not ACCOUNT_ID_PATTERN.fullmatch(account):
            raise InvalidReportError(
                "GL account numbers may contain only letters, numbers, hyphens, and underscores"
            )
        if account not in normalized:
            normalized.append(account)
    if not normalized:
        raise InvalidReportError("Select at least one GL account")
    if len(normalized) > MAX_SELECTED_ACCOUNTS:
        raise InvalidReportError(
            f"Select no more than {MAX_SELECTED_ACCOUNTS} GL accounts"
        )
    return tuple(normalized)


def _resolve_cost_categories(
    gl_accounts: tuple[str, ...] | None,
) -> tuple[FleetCostCategory, ...]:
    """Verify selected IDs against the active company GL account catalog."""
    requested = _normalize_account_ids(gl_accounts)
    accounts = fetch_fleet_cost_account_details(requested)
    by_id = {account.gl_account.upper(): account for account in accounts}
    missing = [account for account in requested if account not in by_id]
    if missing:
        raise InvalidReportError(
            "Unknown or inactive GL account" + ("s" if len(missing) > 1 else "")
            + ": "
            + ", ".join(missing)
        )
    return tuple(
        FleetCostCategory(account, by_id[account].label) for account in requested
    )


def find_fleet_cost_accounts(search: str = "") -> dict:
    """Return verified active accounts plus the configured default selection."""
    query = search.strip()
    if len(query) > MAX_ACCOUNT_SEARCH_LENGTH or any(ord(char) < 32 for char in query):
        raise InvalidReportError(
            f"Account searches must be {MAX_ACCOUNT_SEARCH_LENGTH} characters or fewer"
        )
    try:
        defaults = _resolve_cost_categories(None)
        matches = search_account_catalog(query) if query else []
    except InvalidReportError:
        raise
    except (RuntimeError, OSError) as error:
        raise DataSourceQueryError("GL account lookup failed") from error
    return {
        "query": query,
        "default_accounts": [
            {"gl_account": item.gl_account, "label": item.label, "account_type": ""}
            for item in defaults
        ],
        "accounts": [
            {
                "gl_account": item.gl_account,
                "label": item.label,
                "account_type": item.account_type,
            }
            for item in matches
        ],
    }


def build_fleet_cost_revenue_analysis(
    start_date: date,
    end_date: date,
    granularity: Granularity = "week",
    gl_accounts: tuple[str, ...] | None = None,
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
    try:
        categories = _resolve_cost_categories(gl_accounts)
        selected_ids = tuple(category.gl_account for category in categories)
        cost_entries = fetch_fleet_cost_entries(cost_start, cost_end, selected_ids)
        daily_revenue = fetch_daily_revenue(start_date, end_date)
    except InvalidReportError:
        raise
    except (RuntimeError, OSError) as error:
        raise DataSourceQueryError("Fleet data query failed") from error

    return analyze_fleet_cost_revenue(
        start_date,
        end_date,
        cost_entries,
        daily_revenue,
        granularity,
        categories,
    )
