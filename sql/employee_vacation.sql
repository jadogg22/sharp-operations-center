-- Return the latest active vacation balance for one employee group.
-- Parameters, in order: company id, employee group, employee group,
-- employee group, company id, employee group, employee group. The repeated group parameters keep the
-- driver and office rules in one reusable query.
WITH LatestLeaveTransaction AS (
    SELECT payee_id, amount,
           ROW_NUMBER() OVER (PARTITION BY payee_id ORDER BY trx_date DESC, id DESC) AS rn
    FROM leave_transaction
    WHERE company_id = %s
      AND applies_to = 'V'
      AND (is_void IS NULL OR is_void <> 'Y')
      AND ((%s = 'drivers' AND effect <> 'S') OR (%s <> 'drivers' AND effect IN ('B', 'S')))
)
SELECT
    p.company_id,
    %s AS employee_group,
    p.id AS employee_id,
    p.check_name AS employee_name,
    CASE WHEN %s = 'drivers' THEN d.vacation_pay_rate ELSE o.vacation_pay_rate END AS vacation_pay_rate,
    lt.amount AS vacation_hours_due
FROM payee p
LEFT JOIN off_payee o ON o.id = p.id AND o.company_id = p.company_id
LEFT JOIN drs_payee d ON d.id = p.id AND d.company_id = p.company_id
LEFT JOIN LatestLeaveTransaction lt ON lt.payee_id = p.id AND lt.rn = 1
WHERE p.company_id = %s
  AND p.status = 'A'
  AND ((%s = 'drivers' AND p.non_office_emp = 'Y') OR (%s <> 'drivers' AND p.office_employee = 'Y'))
ORDER BY p.id;
