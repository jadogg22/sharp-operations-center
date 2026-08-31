-- Revenue is intentionally sourced from operational orders rather than a
-- reporting table. The report groups this daily result into day/week/month
-- views in Python so every view reconciles to the same order total.
SELECT
    CAST(bol_recv_date AS date) AS revenue_date,
    COUNT(*) AS order_count,
    CAST(SUM(COALESCE(total_charge, 0)) AS float) AS revenue
FROM orders
WHERE
    company_id = 'TMS'
    AND bol_recv_date >= %s
    AND bol_recv_date < %s
GROUP BY CAST(bol_recv_date AS date)
ORDER BY CAST(bol_recv_date AS date);
