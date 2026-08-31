import type { FleetGranularity, FleetPeriod } from './components/FleetPerformanceChart';

export type ReportKind = 'overview' | 'lane' | 'customer' | 'fleet' | 'pricing';

export type FleetPreview = {
  start_date: string;
  end_date: string;
  granularity: FleetGranularity;
  summary: {
    order_count: number;
    revenue: number;
    source_fleet_cost: number;
    allocated_fleet_cost: number;
    revenue_after_fleet_cost: number;
    fleet_cost_pct_revenue: number | null;
    revenue_per_fleet_cost: number | null;
  };
  cost_categories: { gl_account: string; label: string; source_amount: number }[];
  periods: FleetPeriod[];
  methodology: string;
};

export type CustomerStop = {
  company_id: string;
  order_id: string;
  ordered_date: string | null;
  delivery_date: string | null;
  bill_date: string | null;
  origin_city: string;
  origin_state: string;
  origin_zip: string;
  destination_city: string;
  destination_state: string;
  destination_zip: string;
  consignee: string;
  miles: number;
  bol_number: string;
  commodity: string;
  weight: number;
  movement_sequence: number;
  total_pallets: number;
  pallets_dropped: number;
  pallets_picked_up: number;
  freight_charge: number;
  fuel_surcharge: number;
  extra_drops: number;
  extra_pickups: number;
  other_charges: number;
  other_charge_total: number;
  total_charge: number;
  allocated_fuel: number;
  allocated_freight: number;
  trailer_number: string;
};

export type PreviewOrder = {
  included: boolean;
  company_id: string;
  order_id: string;
  bol_number: string;
  origin: string;
  destination: string;
  trailer_number: string;
  miles: number;
  total_pallets: number;
  freight_charge: number;
  fuel_surcharge: number;
  extra_drops: number;
  extra_pickups: number;
  other_charges: number;
  other_charge_total: number;
  total_charge: number;
  stops: CustomerStop[];
};

export type CustomerPreview = {
  bill_date: string;
  end_date: string;
  summary: { order_count: number; row_count: number; calculated_total: number };
  orders: PreviewOrder[];
};

export type BillingDateOption = {
  bill_date: string;
  order_count: number;
  calculated_total: number;
};

export type BillingDateResponse = {
  start_date: string;
  end_date: string;
  dates: BillingDateOption[];
};
