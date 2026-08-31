# Production query pack

These queries run against a read-only Mcloud (McLeod) SQL Server database in
`DATA_MODE=production`. They are committed so other Mcloud shops can reuse the
patterns; the app-specific values live in configuration, not in the files.

| File | Used by | Parameters (in order) |
| --- | --- | --- |
| `lane_profitability.sql` | lane profitability report | start datetime, end datetime |
| `sportsman_billing_dates.sql` | customer invoice quick-pick dates | customer code, start datetime, end datetime |
| `sportsman_invoice.sql` | customer invoice review + XLSX | customer code, start datetime, end datetime |
| `fleet_cost_entries.sql` | fleet cost vs revenue | GL accounts (injected as `%s` list), start datetime, end datetime |
| `fleet_revenue.sql` | fleet cost vs revenue | start datetime, end datetime |
| `operations_manager_performance.sql` | owner overview | start datetime, end datetime |
| `operations_tractors.sql` | owner overview | none |
| `operations_fleet_status.sql` | owner overview | none |

Conventions:

- Placeholders are `%s` (pymssql style). Date bounds use `[start, end)` so the
  complete end date is included without depending on time components.
- `fleet_cost_entries.sql` contains a `{{GL_ACCOUNT_PLACEHOLDERS}}` token that
  the repository replaces with one `%s` per configured GL account
  (`FLEET_COST_CATEGORIES` setting).
- The two customer queries take the Mcloud customer code from the
  `CUSTOMER_CODE` setting, so the committed SQL stays customer-agnostic.
  `BBF` (opening-balance) rows are excluded from cost totals.

See the main README for the `.env` block that wires these settings up.
