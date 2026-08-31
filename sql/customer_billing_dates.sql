-- This powers the quick-pick billing dates in the UI. The caller supplies the
-- customer code and a rolling window; only dates containing that customer's
-- orders are returned.
SELECT
    CAST(o.bill_date AS date) AS bill_date,
    COUNT(*) AS order_count,
    CAST(SUM(COALESCE(o.total_charge, 0)) AS float) AS calculated_total
FROM orders AS o
WHERE
    o.customer_id = %s
    AND o.bill_date >= %s
    AND o.bill_date < %s
GROUP BY CAST(o.bill_date AS date)
ORDER BY CAST(o.bill_date AS date) DESC;
