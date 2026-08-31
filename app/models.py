from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class LaneLoad:
    order_id: str
    bill_date: date | datetime | None
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str
    empty_miles: float
    loaded_miles: float
    total_miles: float
    total_revenue: float
    customer_name: str
    customer_category: str


@dataclass(frozen=True)
class CustomerBillingDate:
    bill_date: date | datetime
    order_count: int
    calculated_total: float


@dataclass(frozen=True)
class FleetCostEntry:
    gl_account: str
    transaction_date: date | datetime
    amount: float


@dataclass(frozen=True)
class DailyRevenue:
    revenue_date: date | datetime
    order_count: int
    revenue: float


@dataclass(frozen=True)
class CustomerStop:
    order_id: str
    ordered_date: date | datetime | None
    delivery_date: date | datetime | None
    bill_date: date | datetime | None
    origin_city: str
    origin_state: str
    origin_zip: str
    destination_city: str
    destination_state: str
    destination_zip: str
    consignee: str
    miles: float
    bol_number: str
    commodity: str
    weight: float
    movement_sequence: int
    total_pallets: int
    pallets_dropped: int
    pallets_picked_up: int
    freight_charge: float
    fuel_surcharge: float
    extra_drops: float
    extra_pickups: float
    other_charges: float
    other_charge_total: float
    total_charge: float
    allocated_fuel: float
    allocated_freight: float
    trailer_number: str
    company_id: str = ""
