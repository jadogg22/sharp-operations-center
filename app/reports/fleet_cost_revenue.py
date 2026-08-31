from __future__ import annotations

import calendar
import csv
import math
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from io import BytesIO, StringIO
from typing import Literal

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from app.models import DailyRevenue, FleetCostEntry

Granularity = Literal["day", "week", "month"]


@dataclass(frozen=True)
class FleetCostCategory:
    gl_account: str
    label: str


# Add future fleet-cost GL accounts here; query and output logic need no other changes.
FLEET_COST_CATEGORIES = (
    FleetCostCategory("FLEET_LEASE", "Fleet lease"),
)


def _as_date(value: date | datetime) -> date:
    return value.date() if isinstance(value, datetime) else value


def _week_start(value: date) -> date:
    return value - timedelta(days=(value.weekday() + 1) % 7)


def _period_bounds(value: date, granularity: Granularity) -> tuple[date, date]:
    """Return the Sunday–Saturday or calendar-month bucket containing a date."""
    if granularity == "day":
        return value, value
    if granularity == "week":
        start = _week_start(value)
        return start, start + timedelta(days=6)
    start = value.replace(day=1)
    end = value.replace(day=calendar.monthrange(value.year, value.month)[1])
    return start, end


def _short_date(value: date) -> str:
    return f'{value.strftime("%b")} {value.day}'


def _period_label(start: date, end: date, granularity: Granularity) -> str:
    if granularity == "day":
        return f'{start.strftime("%b")} {start.day}, {start.year}'
    if granularity == "month":
        return start.strftime("%B %Y")
    return f"{_short_date(start)}–{_short_date(end)}"


def _money(value: float) -> str:
    return f"${value:,.0f}"


def _csv_money(value: float) -> str:
    return f"${value:,.2f}"


def _axis_money(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:,.0f}"


def _build_periods(
    start_date: date, end_date: date, granularity: Granularity
) -> OrderedDict[date, dict]:
    """Create buckets while retaining the selected-range overlap for allocation."""
    # Keep the bucket dates separate from the selected dates. This lets a July
    # report display the surrounding Sunday-Saturday week while only counting
    # July revenue and July cost allocation.
    periods: OrderedDict[date, dict] = OrderedDict()
    cursor = start_date
    while cursor <= end_date:
        bucket_start, bucket_end = _period_bounds(cursor, granularity)
        period_start = max(bucket_start, start_date)
        period_end = min(bucket_end, end_date)
        periods[bucket_start] = {
            "label": _period_label(bucket_start, bucket_end, granularity),
            "bucket_start": bucket_start,
            "bucket_end": bucket_end,
            "period_start": period_start,
            "period_end": period_end,
            "days_in_period": (period_end - period_start).days + 1,
            "order_count": 0,
            "revenue": 0.0,
            "allocated_fleet_cost": 0.0,
        }
        cursor = period_end + timedelta(days=1)
    return periods


def _reconcile_cost_rounding(periods: OrderedDict[date, dict]) -> list[float]:
    """Round period costs to cents without losing the original GL total."""
    # Daily proration creates fractional cents. Spread the rounding pennies over
    # contributing periods so displayed rows add back to the source GL amount.
    allocated_total = round(
        sum(period["allocated_fleet_cost"] for period in periods.values()), 2
    )
    rounded_costs = [
        round(period["allocated_fleet_cost"], 2) for period in periods.values()
    ]
    rounding_delta = round(allocated_total - sum(rounded_costs), 2)
    if rounding_delta:
        eligible_indexes = [
            index for index, cost in enumerate(rounded_costs) if cost
        ]
        cents = round(rounding_delta * 100)
        cent = 0.01 if cents > 0 else -0.01
        for offset in range(abs(cents)):
            index = eligible_indexes[-1 - (offset % len(eligible_indexes))]
            rounded_costs[index] = round(rounded_costs[index] + cent, 2)
    return rounded_costs


def _add_revenue_to_periods(
    periods: OrderedDict[date, dict],
    daily_revenue: list[DailyRevenue],
    start_date: date,
    end_date: date,
    granularity: Granularity,
) -> None:
    """Populate each period with revenue rows that fall inside the selection."""
    for item in daily_revenue:
        revenue_date = _as_date(item.revenue_date)
        if start_date <= revenue_date <= end_date:
            bucket_start, _ = _period_bounds(revenue_date, granularity)
            periods[bucket_start]["order_count"] += item.order_count
            periods[bucket_start]["revenue"] += item.revenue


def _allocate_costs_to_periods(
    periods: OrderedDict[date, dict], cost_entries: list[FleetCostEntry]
) -> dict[str, float]:
    """Prorate monthly GL entries into the selected period buckets."""
    category_totals: dict[str, float] = {}
    for entry in cost_entries:
        category_totals[entry.gl_account] = category_totals.get(entry.gl_account, 0) + entry.amount
        transaction_date = _as_date(entry.transaction_date)
        month_start = transaction_date.replace(day=1)
        month_end = transaction_date.replace(
            day=calendar.monthrange(transaction_date.year, transaction_date.month)[1]
        )
        # A monthly posting is a source total, not a single-day expense. Spread
        # it over calendar days before assigning it to day/week/month buckets.
        daily_cost = entry.amount / ((month_end - month_start).days + 1)
        for period in periods.values():
            overlap_start = max(period["period_start"], month_start)
            overlap_end = min(period["period_end"], month_end)
            if overlap_end >= overlap_start:
                period["allocated_fleet_cost"] += daily_cost * (
                    (overlap_end - overlap_start).days + 1
                )
    return category_totals


def _build_period_rows(
    periods: OrderedDict[date, dict], granularity: Granularity
) -> list[dict]:
    """Finalize period values, reconcile cents, and calculate derived ratios."""
    rounded_costs = _reconcile_cost_rounding(periods)
    rows = []
    for period, fleet_cost in zip(periods.values(), rounded_costs, strict=True):
        revenue = round(period["revenue"], 2)
        row = {
            **period,
            "revenue": revenue,
            "allocated_fleet_cost": fleet_cost,
            "revenue_after_fleet_cost": round(revenue - fleet_cost, 2),
            "fleet_cost_pct_revenue": round(fleet_cost / revenue, 4) if revenue else None,
            "revenue_per_fleet_cost": round(revenue / fleet_cost, 2) if fleet_cost else None,
        }
        if granularity == "week":
            row["week_start"] = period["bucket_start"]
            row["week_end"] = period["bucket_end"]
        rows.append(row)
    return rows


def analyze_fleet_cost_revenue(
    start_date: date,
    end_date: date,
    cost_entries: list[FleetCostEntry],
    daily_revenue: list[DailyRevenue],
    granularity: Granularity = "week",
) -> dict:
    """Reconcile GL fleet costs with operational revenue by requested period.

    This function coordinates the analysis stages; each stage is isolated so
    cost allocation, period calculations, and serialization can be tested or
    changed independently.
    """
    if end_date < start_date:
        raise ValueError("End date must be on or after start date")

    periods = _build_periods(start_date, end_date, granularity)
    _add_revenue_to_periods(periods, daily_revenue, start_date, end_date, granularity)

    category_labels = {
        category.gl_account: category.label for category in FLEET_COST_CATEGORIES
    }
    category_totals = {
        category.gl_account: 0.0 for category in FLEET_COST_CATEGORIES
    }
    category_totals.update(_allocate_costs_to_periods(periods, cost_entries))
    source_fleet_cost = sum(entry.amount for entry in cost_entries)
    period_rows = _build_period_rows(periods, granularity)

    total_revenue = round(sum(row["revenue"] for row in period_rows), 2)
    allocated_fleet_cost = round(
        sum(row["allocated_fleet_cost"] for row in period_rows), 2
    )
    granularity_copy = {
        "day": "Results are grouped by calendar day.",
        "week": "Weeks run Sunday through Saturday.",
        "month": "Results are grouped by calendar month.",
    }[granularity]
    return {
        "start_date": start_date,
        "end_date": end_date,
        "granularity": granularity,
        "summary": {
            "order_count": sum(row["order_count"] for row in period_rows),
            "revenue": total_revenue,
            "source_fleet_cost": round(source_fleet_cost, 2),
            "allocated_fleet_cost": allocated_fleet_cost,
            "revenue_after_fleet_cost": round(
                total_revenue - allocated_fleet_cost, 2
            ),
            "fleet_cost_pct_revenue": (
                round(allocated_fleet_cost / total_revenue, 4)
                if total_revenue
                else None
            ),
            "revenue_per_fleet_cost": (
                round(total_revenue / allocated_fleet_cost, 2)
                if allocated_fleet_cost
                else None
            ),
        },
        "cost_categories": [
            {
                "gl_account": account,
                "label": category_labels.get(account, account),
                "source_amount": round(amount, 2),
            }
            for account, amount in category_totals.items()
        ],
        "periods": period_rows,
        "weeks": period_rows if granularity == "week" else [],
        "methodology": (
            "Revenue uses synthetic order totals by received date. "
            f"{granularity_copy} Monthly fleet costs are prorated by calendar day "
            "into each overlapping period."
        ),
    }


def fleet_cost_revenue_csv(analysis: dict) -> bytes:
    """Serialize the displayed period rows into a reviewable CSV attachment."""
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "Period",
            "Selected period start",
            "Selected period end",
            "Days in selected period",
            "Order count",
            "Revenue",
            "Allocated fleet cost",
            "Revenue after fleet cost",
            "Fleet cost % of revenue",
            "Revenue per $1 fleet cost",
        ]
    )
    for row in analysis["periods"]:
        writer.writerow(
            [
                row["label"],
                row["period_start"].isoformat(),
                row["period_end"].isoformat(),
                row["days_in_period"],
                row["order_count"],
                _csv_money(row["revenue"]),
                _csv_money(row["allocated_fleet_cost"]),
                _csv_money(row["revenue_after_fleet_cost"]),
                (
                    ""
                    if row["fleet_cost_pct_revenue"] is None
                    else f'{row["fleet_cost_pct_revenue"]:.2%}'
                ),
                (
                    ""
                    if row["revenue_per_fleet_cost"] is None
                    else _csv_money(row["revenue_per_fleet_cost"])
                ),
            ]
        )
    writer.writerow([])
    summary = analysis["summary"]
    writer.writerow(
        [
            "TOTAL",
            analysis["start_date"].isoformat(),
            analysis["end_date"].isoformat(),
            sum(row["days_in_period"] for row in analysis["periods"]),
            summary["order_count"],
            _csv_money(summary["revenue"]),
            _csv_money(summary["allocated_fleet_cost"]),
            _csv_money(summary["revenue_after_fleet_cost"]),
            (
                ""
                if summary["fleet_cost_pct_revenue"] is None
                else f'{summary["fleet_cost_pct_revenue"]:.2%}'
            ),
            (
                ""
                if summary["revenue_per_fleet_cost"] is None
                else _csv_money(summary["revenue_per_fleet_cost"])
            ),
        ]
    )
    writer.writerow([])
    writer.writerow(["View", analysis["granularity"].title()])
    writer.writerow(["Methodology", analysis["methodology"]])
    for category in analysis["cost_categories"]:
        writer.writerow(
            [
                "Fleet cost source",
                category["gl_account"],
                category["label"],
                _csv_money(category["source_amount"]),
            ]
        )
    return output.getvalue().encode("utf-8-sig")


def fleet_cost_revenue_chart(analysis: dict) -> bytes:
    """Render the cost, revenue, and margin trend used in the downloadable PNG."""
    periods = analysis["periods"]
    labels = [row["label"] for row in periods]
    revenue = [row["revenue"] for row in periods]
    fleet_cost = [row["allocated_fleet_cost"] for row in periods]
    percentages = [(row["fleet_cost_pct_revenue"] or 0) * 100 for row in periods]

    figure_width = min(28, max(14, len(periods) * 0.58))
    figure, axis = plt.subplots(figsize=(figure_width, 8), dpi=150)
    figure.patch.set_facecolor("#F5F6F2")
    axis.set_facecolor("#FFFFFF")
    positions = list(range(len(periods)))
    width = 0.34
    revenue_bars = axis.bar(
        [position - width / 2 for position in positions],
        revenue,
        width,
        label="Revenue",
        color="#174D37",
    )
    cost_bars = axis.bar(
        [position + width / 2 for position in positions],
        fleet_cost,
        width,
        label="Allocated fleet cost",
        color="#F0C75E",
    )
    axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: _axis_money(value)))
    tick_step = max(1, math.ceil(len(periods) / 12))
    tick_positions = positions[::tick_step]
    if positions and positions[-1] not in tick_positions:
        tick_positions.append(positions[-1])
    axis.set_xticks(tick_positions, [labels[index] for index in tick_positions])
    axis.tick_params(axis="x", labelsize=9, colors="#49524D", rotation=25)
    axis.tick_params(axis="y", labelsize=9, colors="#6B746E")
    axis.grid(axis="y", color="#E2E7E2", linewidth=0.8)
    axis.set_axisbelow(True)

    percent_axis = axis.twinx()
    percent_axis.plot(
        positions,
        percentages,
        color="#A14935",
        linewidth=2.2,
        marker="o" if len(periods) <= 62 else None,
        label="Fleet cost % of revenue",
    )
    percent_axis.set_ylim(0, max(20, max(percentages, default=0) * 1.35))
    percent_axis.yaxis.set_major_formatter(
        FuncFormatter(lambda value, _: f"{value:.0f}%")
    )
    percent_axis.tick_params(axis="y", labelsize=9, colors="#A14935")

    if len(periods) <= 12:
        for bars in (revenue_bars, cost_bars):
            for bar in bars:
                axis.annotate(
                    _money(bar.get_height()),
                    (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color="#26312B",
                )

    summary = analysis["summary"]
    title_prefix = {
        "day": "Daily",
        "week": "Weekly",
        "month": "Monthly",
    }[analysis["granularity"]]
    axis.set_title(
        f"{title_prefix} fleet cost vs revenue",
        loc="left",
        fontsize=20,
        fontweight="bold",
        color="#174D37",
        pad=22,
    )
    axis.text(
        0,
        1.02,
        (
            f'{analysis["start_date"].strftime("%B")} '
            f'{analysis["start_date"].day}, {analysis["start_date"].year}–'
            f'{analysis["end_date"].strftime("%B")} '
            f'{analysis["end_date"].day}, {analysis["end_date"].year}  |  '
            f'{_money(summary["revenue"])} revenue  |  '
            f'{_money(summary["allocated_fleet_cost"])} fleet cost'
        ),
        transform=axis.transAxes,
        fontsize=10,
        color="#6B746E",
        parse_math=False,
    )
    handles, legend_labels = axis.get_legend_handles_labels()
    percent_handles, percent_labels = percent_axis.get_legend_handles_labels()
    axis.legend(
        handles + percent_handles,
        legend_labels + percent_labels,
        loc="upper left",
        frameon=False,
        ncol=3,
        bbox_to_anchor=(0, 0.96),
    )
    axis.spines[["top", "right", "left"]].set_visible(False)
    percent_axis.spines[["top", "right", "left"]].set_visible(False)
    axis.spines["bottom"].set_color("#C9D1CA")
    figure.text(0.07, 0.02, analysis["methodology"], fontsize=8, color="#6B746E")
    figure.tight_layout(rect=(0.04, 0.07, 0.97, 0.96))
    output = BytesIO()
    figure.savefig(output, format="png", facecolor=figure.get_facecolor())
    plt.close(figure)
    return output.getvalue()


def serialize_analysis(analysis: dict) -> dict:
    return {
        **analysis,
        "periods": [dict(row) for row in analysis["periods"]],
        "weeks": [dict(row) for row in analysis["weeks"]],
        "cost_categories": [dict(category) for category in analysis["cost_categories"]],
    }
