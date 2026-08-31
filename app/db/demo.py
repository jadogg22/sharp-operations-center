"""Create and connect to the synthetic SQLite database used by the showcase."""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

from app.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS lane_loads (
    order_id TEXT PRIMARY KEY, bill_date TEXT, origin_city TEXT, origin_state TEXT,
    destination_city TEXT, destination_state TEXT, empty_miles REAL,
    loaded_miles REAL, total_miles REAL, total_revenue REAL,
    customer_name TEXT, customer_category TEXT
);
CREATE TABLE IF NOT EXISTS invoice_stops (
    id INTEGER PRIMARY KEY, company_id TEXT, order_id TEXT, ordered_date TEXT,
    delivery_date TEXT, bill_date TEXT, origin_city TEXT, origin_state TEXT,
    origin_zip TEXT, destination_city TEXT, destination_state TEXT,
    destination_zip TEXT, consignee TEXT, miles REAL, bol_number TEXT,
    commodity TEXT, weight REAL, movement_sequence INTEGER, total_pallets INTEGER,
    pallets_dropped INTEGER, pallets_picked_up INTEGER, freight_charge REAL,
    fuel_surcharge REAL, extra_drops REAL, extra_pickups REAL, other_charges REAL,
    other_charge_total REAL, total_charge REAL, allocated_fuel REAL,
    allocated_freight REAL, trailer_number TEXT
);
CREATE TABLE IF NOT EXISTS fleet_cost_entries (
    id INTEGER PRIMARY KEY, gl_account TEXT, transaction_date TEXT, amount REAL
);
CREATE TABLE IF NOT EXISTS daily_revenue (
    revenue_date TEXT PRIMARY KEY, order_count INTEGER, revenue REAL
);
CREATE TABLE IF NOT EXISTS operations_daily (
    activity_date TEXT, manager_id TEXT, working_trucks INTEGER,
    movement_count INTEGER, total_miles REAL, loaded_miles REAL,
    empty_miles REAL, allocated_revenue REAL, stop_appointments INTEGER,
    on_time_stops INTEGER, order_appointments INTEGER, on_time_orders INTEGER,
    PRIMARY KEY (activity_date, manager_id)
);
CREATE TABLE IF NOT EXISTS operations_tractors (
    manager_id TEXT PRIMARY KEY, manager_name TEXT, assigned_trucks INTEGER,
    seated_trucks INTEGER
);
CREATE TABLE IF NOT EXISTS fleet_status (
    id INTEGER PRIMARY KEY CHECK (id = 1), active_fleet INTEGER,
    seated_tractors INTEGER, dispatch_ready INTEGER, ready_to_seat INTEGER,
    out_of_service INTEGER, special_hold INTEGER
);
"""

MANAGERS = (
    ("carter", "Alex Carter"),
    ("blake", "Jordan Blake"),
    ("reed", "Morgan Reed"),
    ("brooks", "Casey Brooks"),
    ("quinn", "Taylor Quinn"),
    ("hayes", "Riley Hayes"),
)


def connect() -> sqlite3.Connection:
    """Open the configured demo database and seed it on first use."""
    database_path = Path(get_settings().demo_database_path).expanduser().resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    if connection.execute("SELECT COUNT(*) FROM lane_loads").fetchone()[0] == 0:
        _seed(connection)
    return connection


def _seed(connection: sqlite3.Connection) -> None:
    """Populate three years of deterministic, clearly fictional operations data."""
    start = date(2025, 1, 1)
    end = date(2027, 12, 31)
    routes = (
        ("Salt Lake City", "UT", "Boise", "ID", 42, 338, 1_460),
        ("Ogden", "UT", "Denver", "CO", 65, 512, 2_080),
        ("Provo", "UT", "Las Vegas", "NV", 31, 395, 1_720),
        ("Boise", "ID", "Salt Lake City", "UT", 28, 342, 1_510),
        ("Denver", "CO", "Ogden", "UT", 54, 505, 2_230),
        ("Las Vegas", "NV", "Provo", "UT", 39, 388, 1_810),
    )
    for index, route in enumerate(routes):
        origin_city, origin_state, destination_city, destination_state, empty, loaded, revenue = route
        connection.execute(
            "INSERT INTO lane_loads VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f"DEMO-{index + 1001}", "2026-08-25", origin_city, origin_state,
             destination_city, destination_state, empty, loaded, empty + loaded,
             revenue, f"Demo Customer {index % 3 + 1}", "Synthetic"),
        )

    invoice_orders = (
        ("2001", ("Salt Lake City", "UT", "84104"), (("Boise", "ID", "83705", "North Warehouse", 12), ("Nampa", "ID", "83687", "West Warehouse", 8)), 1_250, 315, 420),
        ("2002", ("Ogden", "UT", "84404"), (("Reno", "NV", "89502", "Central Warehouse", 18),), 1_480, 370, 525),
        ("2003", ("Provo", "UT", "84601"), (("Las Vegas", "NV", "89115", "South Warehouse", 10), ("Henderson", "NV", "89011", "East Warehouse", 6)), 1_390, 345, 445),
    )
    for bill_date in (date(2026, 8, 24), date(2026, 8, 27)):
        for order_id, origin, stops, freight, fuel, miles in invoice_orders:
            total_pallets = sum(stop[4] for stop in stops)
            total = freight + fuel + 75
            for sequence, (city, state, postal_code, consignee, pallets) in enumerate(stops, 1):
                allocation = pallets / total_pallets
                connection.execute(
                    """INSERT INTO invoice_stops (
                        company_id, order_id, ordered_date, delivery_date, bill_date,
                        origin_city, origin_state, origin_zip, destination_city,
                        destination_state, destination_zip, consignee, miles, bol_number,
                        commodity, weight, movement_sequence, total_pallets,
                        pallets_dropped, pallets_picked_up, freight_charge, fuel_surcharge,
                        extra_drops, extra_pickups, other_charges, other_charge_total,
                        total_charge, allocated_fuel, allocated_freight, trailer_number
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    ("DEMO", order_id, str(bill_date - timedelta(days=4)),
                     str(bill_date - timedelta(days=1)), str(bill_date), *origin,
                     city, state, postal_code, consignee, miles, f"BOL-{order_id}",
                     "General merchandise", 18_500 + sequence * 850, sequence,
                     total_pallets, pallets, pallets, freight, fuel, 75, 0, 0,
                     fuel + 75, total, round(fuel * allocation, 2),
                     round(freight * allocation, 2), f"D-{410 + int(order_id[-1])}"),
                )

    current = start
    while current <= end:
        weekday = current.weekday() < 5
        connection.execute(
            "INSERT INTO daily_revenue VALUES (?, ?, ?)",
            (str(current), 14 if weekday else 6,
             (28_500 if weekday else 12_200) + (current.toordinal() % 5) * 900),
        )
        for index, (manager_id, _) in enumerate(MANAGERS):
            trucks = 18 + index * 2
            miles = trucks * (72 + index * 4)
            empty_pct = (7.4, 9.1, 8.2, 24.0, 15.2, 5.8)[index] / 100
            appointments = trucks
            connection.execute(
                "INSERT INTO operations_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (str(current), manager_id, trucks, appointments * 2, miles,
                 miles * (1 - empty_pct), miles * empty_pct,
                 miles * (2.75 + index * 0.08), appointments * 2,
                 round(appointments * 2 * (0.94 + index * 0.006)), appointments,
                 round(appointments * (0.93 + index * 0.007))),
            )
        if current.day == 1:
            connection.execute(
                "INSERT INTO fleet_cost_entries (gl_account, transaction_date, amount) VALUES (?, ?, ?)",
                ("FLEET_LEASE", str(current), 128_000 + current.month * 1_750),
            )
        current += timedelta(days=1)

    connection.executemany(
        "INSERT INTO operations_tractors VALUES (?, ?, ?, ?)",
        [(manager_id, name, 21 + index * 2, 19 + index * 2)
         for index, (manager_id, name) in enumerate(MANAGERS)],
    )
    connection.execute("INSERT INTO fleet_status VALUES (1, 154, 139, 127, 8, 11, 4)")
    connection.commit()
