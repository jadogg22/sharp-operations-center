-- Return one row per order movement so the invoice can show every warehouse
-- stop. Charge columns remain order-level values and are repeated per movement;
-- the repository allocates them back to stops for the detail workbook.
SELECT
    RTRIM(o.company_id) AS company_id,
    RTRIM(o.id) AS order_id,
    o.ordered_date,
    s.actual_arrival AS delivery_date,
    o.bill_date,
    RTRIM(COALESCE(s.city_name, '')) AS stop_city,
    RTRIM(COALESCE(s.state, '')) AS stop_state,
    RTRIM(COALESCE(s.zip_code, '')) AS stop_zip,
    RTRIM(COALESCE(s.location_name, '')) AS consignee,
    CAST(COALESCE(o.bill_distance, 0) AS float) AS miles,
    RTRIM(COALESCE(o.blnum, '')) AS bol_number,
    RTRIM(COALESCE(o.commodity, '')) AS commodity,
    CAST(COALESCE(s.weight, 0) AS float) AS weight,
    CAST(COALESCE(s.movement_sequence, 0) AS int) AS movement_sequence,

    -- Some operating databases store these two values in the opposite fields.
    CAST(COALESCE(s.pallets_picked_up, 0) AS int) AS pallets_dropped,
    CAST(COALESCE(s.pallets_dropped, 0) AS int) AS pallets_picked_up,

    CAST(COALESCE(o.freight_charge, 0) AS float) AS freight_charge,
    CAST(COALESCE(o.otherchargetotal, 0) AS float) AS other_charge_total,
    CAST(COALESCE(o.total_charge, 0) AS float) AS total_charge,
    CAST(SUM(CASE WHEN oc.charge_id = 'FUD' THEN COALESCE(oc.amount, 0) ELSE 0 END) AS float) AS fuel_surcharge,
    CAST(SUM(CASE WHEN oc.charge_id = 'EDR' THEN COALESCE(oc.amount, 0) ELSE 0 END) AS float) AS extra_drops,
    CAST(SUM(CASE WHEN oc.charge_id = 'EPU' THEN COALESCE(oc.amount, 0) ELSE 0 END) AS float) AS extra_pickups,
    CAST(
        COALESCE(o.otherchargetotal, 0)
        - SUM(CASE WHEN oc.charge_id = 'FUD' THEN COALESCE(oc.amount, 0) ELSE 0 END)
        - SUM(CASE WHEN oc.charge_id = 'EDR' THEN COALESCE(oc.amount, 0) ELSE 0 END)
        - SUM(CASE WHEN oc.charge_id = 'EPU' THEN COALESCE(oc.amount, 0) ELSE 0 END)
        AS float
    ) AS other_charges,
    RTRIM(COALESCE(m.carrier_trailer, ei.equipment_id, '')) AS trailer_number
FROM orders AS o
JOIN stop AS s
    ON s.order_id = o.id
    AND s.company_id = o.company_id
LEFT JOIN other_charge AS oc
    ON oc.order_id = o.id
    AND oc.company_id = o.company_id
    AND oc.charge_id IN ('FUD', 'EDR', 'EPU')
LEFT JOIN movement AS m
    ON m.id = o.curr_movement_id
    AND m.company_id = o.company_id
LEFT JOIN equipment_item AS ei
    ON ei.equipment_group_id = m.equipment_group_id
    AND ei.company_id = o.company_id
    AND ei.equipment_type_id = 'T'
WHERE
    o.customer_id = %s
    AND o.bill_date >= %s
    AND o.bill_date < %s
GROUP BY
    o.company_id,
    o.id,
    o.ordered_date,
    s.actual_arrival,
    o.bill_date,
    s.city_name,
    s.state,
    s.zip_code,
    s.location_name,
    o.bill_distance,
    o.blnum,
    o.commodity,
    s.weight,
    s.movement_sequence,
    s.pallets_dropped,
    s.pallets_picked_up,
    o.freight_charge,
    o.otherchargetotal,
    o.total_charge,
    m.carrier_trailer,
    ei.equipment_id
ORDER BY o.company_id, o.id, s.movement_sequence, o.bill_date;
