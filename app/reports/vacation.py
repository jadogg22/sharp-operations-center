"""CSV formatting for the current employee vacation-balance report."""

from __future__ import annotations

import csv
from io import StringIO

from app.models import VacationBalance


def vacation_csv(rows: list[VacationBalance]) -> bytes:
    """Return a portable CSV with balances, rates, and estimated payout."""
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([
        "Employee group", "Employee ID", "Employee", "Company",
        "Vacation hours due", "Vacation pay rate", "Estimated amount due",
    ])
    for row in rows:
        writer.writerow([
            row.employee_group,
            row.employee_id,
            row.employee_name,
            row.company_id,
            "" if row.vacation_hours_due is None else f"{row.vacation_hours_due:.2f}",
            "" if row.vacation_pay_rate is None else f"{row.vacation_pay_rate:.2f}",
            f"{row.amount_due:.2f}",
        ])
    return output.getvalue().encode("utf-8-sig")
