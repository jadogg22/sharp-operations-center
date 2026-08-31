from dataclasses import replace
from datetime import date
from io import BytesIO

from openpyxl import load_workbook
from pypdf import PdfReader

from app.models import CustomerStop, DailyRevenue, FleetCostEntry, LaneLoad
from app.reports.customer_invoice import generate_customer_invoice, invoice_total
from app.reports.fleet_cost_revenue import (
    analyze_fleet_cost_revenue,
    fleet_cost_revenue_chart,
    fleet_cost_revenue_csv,
)
from app.reports.lane_profitability import (
    analyze_lanes,
    generate_lane_profitability_pdf,
)


def lane_load(order_id: str, origin: str, destination: str, revenue: float) -> LaneLoad:
    return LaneLoad(
        order_id=order_id,
        bill_date=date(2026, 8, 1),
        origin_city="Logan",
        origin_state=origin,
        destination_city="Denver",
        destination_state=destination,
        empty_miles=50,
        loaded_miles=450,
        total_miles=500,
        total_revenue=revenue,
        customer_name="Example Customer",
        customer_category="DIRECT",
    )


def customer_stop(order_id: str, movement: int) -> CustomerStop:
    return CustomerStop(
        order_id=order_id,
        ordered_date=date(2026, 8, 1),
        delivery_date=date(2026, 8, 3),
        bill_date=date(2026, 8, 4),
        origin_city="Salt Lake City",
        origin_state="UT",
        origin_zip="84339",
        destination_city="Boise",
        destination_state="ID",
        destination_zip="83702",
        consignee="Delivery Location A",
        miles=350,
        bol_number="BOL-100",
        commodity="General merchandise",
        weight=12000,
        movement_sequence=movement,
        total_pallets=20,
        pallets_dropped=10,
        pallets_picked_up=10,
        freight_charge=1000,
        fuel_surcharge=250,
        extra_drops=25,
        extra_pickups=0,
        other_charges=10,
        other_charge_total=285,
        total_charge=1285,
        allocated_fuel=125,
        allocated_freight=500,
        trailer_number="TR-42",
    )


def test_lane_analysis_pairs_utah_round_trips() -> None:
    loads = [
        lane_load("1", "UT", "CO", 1500),
        lane_load("2", "CO", "UT", 1600),
        lane_load("3", "UT", "ID", 1400),
    ]
    lanes = analyze_lanes(loads)
    assert len(lanes) == 1
    assert lanes[0]["destination"] == "CO"
    assert lanes[0]["total_trips"] == 2


def test_lane_pdf_is_readable() -> None:
    loads = [
        lane_load("1", "UT", "CO", 1500),
        lane_load("2", "CO", "UT", 1600),
        lane_load("3", "UT", "ID", 1450),
        lane_load("4", "ID", "UT", 1525),
    ]
    report = generate_lane_profitability_pdf(loads, "2026-08-01", "2026-08-07")
    reader = PdfReader(BytesIO(report))
    assert len(reader.pages) == 3
    assert "Lane profitability" in (reader.pages[0].extract_text() or "")


def test_customer_workbook_has_formulas_and_layout() -> None:
    workbook_bytes = generate_customer_invoice(
        [customer_stop("100", 1), customer_stop("100", 2)],
        "INV-42",
        date(2026, 8, 4),
        1285,
    )
    workbook = load_workbook(BytesIO(workbook_bytes), data_only=False)
    summary = workbook["Invoice Summary"]
    detail = workbook["Load Detail"]
    assert summary["A1"].value == "MULTI-STOP CUSTOMER BILLING"
    assert summary["A11"].value == "100"
    assert summary["A12"].value.strip() == "↳ Movement 1"
    assert summary["C12"].value == "Delivery Location A"
    assert summary["D12"].value == "Boise, ID 83702"
    assert summary["J15"].value == "=SUM(K11:K13)"
    assert detail["A7"].value == "100"
    assert detail["AA7"].value == "=IF($Q7=0,0,$U7*$R7/$Q7)"
    assert detail.freeze_panes == "A7"
    assert invoice_total([customer_stop("100", 1), customer_stop("100", 2)]) == 1285


def test_customer_orders_are_unique_by_company_and_order_id() -> None:
    demo = replace(customer_stop("100", 1), company_id="DEMO")
    demo2 = replace(customer_stop("100", 1), company_id="DEMO2")
    assert invoice_total([demo, demo2]) == 2570


def test_fleet_cost_is_allocated_weekly_and_reconciles() -> None:
    analysis = analyze_fleet_cost_revenue(
        date(2026, 7, 1),
        date(2026, 7, 31),
        [FleetCostEntry("FLEET_LEASE", date(2026, 7, 1), 310.00)],
        [
            DailyRevenue(date(2026, 7, 1), 2, 1_000.00),
            DailyRevenue(date(2026, 7, 5), 3, 1_500.00),
        ],
    )

    assert analysis["weeks"][0]["week_start"] == date(2026, 6, 28)
    assert analysis["weeks"][0]["allocated_fleet_cost"] == 40.00
    assert analysis["weeks"][1]["allocated_fleet_cost"] == 70.00
    assert analysis["summary"]["allocated_fleet_cost"] == 310.00
    assert analysis["summary"]["revenue"] == 2_500.00
    assert analysis["summary"]["order_count"] == 5


def test_fleet_outputs_are_sendable_files() -> None:
    analysis = analyze_fleet_cost_revenue(
        date(2026, 7, 1),
        date(2026, 7, 2),
        [FleetCostEntry("FLEET_LEASE", date(2026, 7, 1), 310.00)],
        [DailyRevenue(date(2026, 7, 1), 1, 1_000.00)],
    )

    csv_bytes = fleet_cost_revenue_csv(analysis)
    assert csv_bytes.startswith(b"\xef\xbb\xbfPeriod")
    assert b"Fleet cost source,FLEET_LEASE,Fleet lease,$310.00" in csv_bytes
    assert fleet_cost_revenue_chart(analysis).startswith(b"\x89PNG\r\n\x1a\n")


def test_fleet_analysis_supports_day_and_month_views() -> None:
    arguments = (
        date(2026, 7, 1),
        date(2026, 7, 31),
        [FleetCostEntry("FLEET_LEASE", date(2026, 7, 1), 310.00)],
        [
            DailyRevenue(date(2026, 7, 1), 2, 1_000.00),
            DailyRevenue(date(2026, 7, 5), 3, 1_500.00),
        ],
    )

    daily = analyze_fleet_cost_revenue(*arguments, granularity="day")
    monthly = analyze_fleet_cost_revenue(*arguments, granularity="month")

    assert len(daily["periods"]) == 31
    assert daily["periods"][0]["label"] == "Jul 1, 2026"
    assert daily["periods"][0]["allocated_fleet_cost"] == 10.00
    assert monthly["granularity"] == "month"
    assert len(monthly["periods"]) == 1
    assert monthly["periods"][0]["label"] == "July 2026"
    assert monthly["summary"] == daily["summary"]
