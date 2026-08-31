from datetime import date, datetime

from pydantic import BaseModel, Field


class ReviewedCustomerStop(BaseModel):
    company_id: str = Field(default="", max_length=20)
    order_id: str = Field(min_length=1, max_length=40)
    ordered_date: date | datetime | None = None
    delivery_date: date | datetime | None = None
    bill_date: date | datetime | None = None
    origin_city: str = ""
    origin_state: str = ""
    origin_zip: str = ""
    destination_city: str = ""
    destination_state: str = ""
    destination_zip: str = ""
    consignee: str = ""
    miles: float = 0
    bol_number: str = ""
    commodity: str = ""
    weight: float = 0
    movement_sequence: int = 0
    total_pallets: int = 0
    pallets_dropped: int = 0
    pallets_picked_up: int = 0
    freight_charge: float = 0
    fuel_surcharge: float = 0
    extra_drops: float = 0
    extra_pickups: float = 0
    other_charges: float = 0
    other_charge_total: float = 0
    total_charge: float = 0
    allocated_fuel: float = 0
    allocated_freight: float = 0
    trailer_number: str = ""


class CustomerInvoiceRequest(BaseModel):
    bill_date: date
    end_date: date | None = None
    invoice_number: str = Field(default="", max_length=80)
    expected_total: float | None = Field(default=None, ge=0)
    rows: list[ReviewedCustomerStop] = Field(min_length=1)
