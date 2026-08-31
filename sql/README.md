# Production query pack (not committed)

The production adapter (`app/db/production_repository.py`) loads its SQL from
this folder at runtime. The queries reference the company's real Mcloud schema
and stay out of the public repository.

A fresh clone does not need any of these files — `DATA_MODE=demo` (the default)
runs entirely on the seeded SQLite database.

Expected files when running `DATA_MODE=production`:

- `lane_profitability.sql`
- `sportsman_billing_dates.sql`
- `sportsman_invoice.sql`
- `fleet_cost_entries.sql` (contains a `{{GL_ACCOUNT_PLACEHOLDERS}}` token)
- `fleet_revenue.sql`
- `operations_manager_performance.sql`
- `operations_tractors.sql`
- `operations_fleet_status.sql`

Queries use `%s` parameter placeholders (pymssql style) and receive `[start, end)`
datetime bounds, except the tractor and fleet-status queries which take no
parameters.
