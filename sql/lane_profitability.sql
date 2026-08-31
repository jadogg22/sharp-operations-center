-- Preserve the legacy lane definition: a load is included only when it has
-- positive miles/revenue, is not void/quote/subject freight, and contains a
-- loaded movement. Arrival is preferred, with scheduled arrival as fallback.
SELECT
    RTRIM(o.id) AS order_id,
    o.bill_date,
    RTRIM(origin.city_name) AS origin_city,
    RTRIM(origin.state) AS origin_state,
    RTRIM(dest.city_name) AS destination_city,
    RTRIM(dest.state) AS destination_state,
    CAST(COALESCE(pod.empty_distance, 0) AS float) AS empty_miles,
    CAST(COALESCE(pod.loaded_distance, 0) AS float) AS loaded_miles,
    CAST(COALESCE(pod.empty_distance, 0) + COALESCE(pod.loaded_distance, 0) AS float) AS total_miles,
    CAST(COALESCE(o.total_charge, 0) AS float) AS total_revenue,
    RTRIM(COALESCE(c.name, 'Unknown')) AS customer_name,
    RTRIM(COALESCE(c.category, '')) AS customer_category
FROM orders AS o
LEFT JOIN customer AS c
    ON c.id = o.customer_id
    AND c.company_id = o.company_id
LEFT JOIN prorated_orderdist AS pod
    ON pod.order_id = o.id
    AND pod.company_id = o.company_id
JOIN stop AS origin
    ON origin.id = o.shipper_stop_id
    AND origin.company_id = o.company_id
JOIN stop AS dest
    ON dest.id = o.consignee_stop_id
    AND dest.company_id = o.company_id
WHERE
    o.company_id = 'TMS'
    AND o.status NOT IN ('Q', 'V')
    AND (o.subject_order_status IS NULL OR o.subject_order_status <> 'S')
    AND COALESCE(o.total_charge, 0) > 0
    AND (COALESCE(pod.empty_distance, 0) + COALESCE(pod.loaded_distance, 0)) > 0
    AND COALESCE(dest.actual_arrival, dest.sched_arrive_early) >= %s
    AND COALESCE(dest.actual_arrival, dest.sched_arrive_early) < %s
    AND EXISTS (
        SELECT 1
        FROM movement_order AS mo
        JOIN movement AS m
            ON m.id = mo.movement_id
            AND m.company_id = mo.company_id
        WHERE mo.order_id = o.id
            AND mo.company_id = o.company_id
            AND m.loaded = 'L'
    )
ORDER BY o.id;
