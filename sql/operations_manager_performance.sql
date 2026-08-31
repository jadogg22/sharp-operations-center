-- Operational mileage follows the tractor's current driver-manager assignment,
-- matching how the morning scorecard is organized. Revenue is allocated across
-- an order's loaded movements by mileage so multi-leg orders are not counted in
-- full for every manager who touched the load.
WITH scoped_movements AS (
    -- One row per non-void tractor movement completed in the requested window.
    -- DISTINCT protects the aggregate from duplicate continuity/order joins.
    SELECT DISTINCT
        m.id AS movement_id,
        RTRIM(t.dispatcher) AS manager_id,
        RTRIM(ct.equipment_id) AS truck_id,
        m.loaded,
        CAST(COALESCE(m.move_distance, 0) AS float) AS miles
    FROM movement AS m
    JOIN continuity AS ct
        ON ct.movement_id = m.id
        AND ct.company_id = m.company_id
        AND ct.equipment_type_id = 'T'
    JOIN tractor AS t
        ON t.id = ct.equipment_id
        AND t.company_id = ct.company_id
    WHERE
        m.company_id = 'TMS'
        AND m.status <> 'V'
        AND t.dispatcher IS NOT NULL
        AND ct.dest_actualarrival >= %s
        AND ct.dest_actualarrival < %s
),
movement_totals AS (
    -- These are the movement numerators; working_trucks is the distinct-truck
    -- denominator used by the Python service for productivity rates.
    SELECT
        manager_id,
        COUNT(DISTINCT truck_id) AS working_trucks,
        COUNT(*) AS movement_count,
        CAST(SUM(miles) AS float) AS total_miles,
        CAST(SUM(CASE WHEN loaded = 'E' THEN miles ELSE 0 END) AS float) AS empty_miles,
        CAST(SUM(CASE WHEN loaded = 'L' THEN miles ELSE 0 END) AS float) AS loaded_miles
    FROM scoped_movements
    GROUP BY manager_id
),
scoped_orders AS (
    -- Keep one manager/order pair so a multi-stop order can contribute service
    -- results without multiplying its appointments by every loaded movement.
    SELECT DISTINCT sm.manager_id, mo.order_id
    FROM scoped_movements AS sm
    JOIN movement_order AS mo
        ON mo.movement_id = sm.movement_id
        AND mo.company_id = 'TMS'
    WHERE sm.loaded = 'L'
),
loaded_distance_by_order AS (
    -- The full loaded-mile denominator lets revenue be split fairly across
    -- loaded legs instead of charging the whole order to each leg.
    SELECT
        mo.order_id,
        CAST(SUM(COALESCE(m.move_distance, 0)) AS float) AS loaded_miles
    FROM movement AS m
    JOIN movement_order AS mo
        ON mo.movement_id = m.id
        AND mo.company_id = m.company_id
    WHERE
        m.company_id = 'TMS'
        AND m.status <> 'V'
        AND m.loaded = 'L'
    GROUP BY mo.order_id
),
revenue_totals AS (
    -- Allocate each order's total charge to the manager's loaded miles.
    SELECT
        sm.manager_id,
        CAST(SUM(
            CASE
                WHEN ldo.loaded_miles > 0
                THEN COALESCE(o.total_charge, 0) * sm.miles / ldo.loaded_miles
                ELSE 0
            END
        ) AS float) AS allocated_revenue
    FROM scoped_movements AS sm
    JOIN movement_order AS mo
        ON mo.movement_id = sm.movement_id
        AND mo.company_id = 'TMS'
    JOIN orders AS o
        ON o.id = mo.order_id
        AND o.company_id = mo.company_id
    JOIN loaded_distance_by_order AS ldo
        ON ldo.order_id = mo.order_id
    WHERE sm.loaded = 'L'
    GROUP BY sm.manager_id
),
stop_performance AS (
    -- Stop service is measured from actual arrival against the customer's late
    -- appointment threshold, not against the report-generation timestamp.
    SELECT
        so.manager_id,
        COUNT(*) AS stop_appointments,
        SUM(CASE WHEN s.actual_arrival <= s.sched_arrive_late THEN 1 ELSE 0 END) AS on_time_stops
    FROM scoped_orders AS so
    JOIN stop AS s
        ON s.order_id = so.order_id
        AND s.company_id = 'TMS'
        AND s.status <> 'V'
    WHERE
        s.actual_arrival IS NOT NULL
        AND s.sched_arrive_late IS NOT NULL
    GROUP BY so.manager_id
),
order_performance AS (
    -- Order service uses the final consignee stop as the order-level result.
    SELECT
        so.manager_id,
        COUNT(*) AS order_appointments,
        SUM(CASE WHEN dest.actual_arrival <= dest.sched_arrive_late THEN 1 ELSE 0 END) AS on_time_orders
    FROM scoped_orders AS so
    JOIN orders AS o
        ON o.id = so.order_id
        AND o.company_id = 'TMS'
    JOIN stop AS dest
        ON dest.id = o.consignee_stop_id
        AND dest.company_id = o.company_id
    WHERE
        dest.actual_arrival IS NOT NULL
        AND dest.sched_arrive_late IS NOT NULL
    GROUP BY so.manager_id
)
SELECT
    mt.manager_id,
    mt.working_trucks,
    mt.movement_count,
    mt.total_miles,
    mt.empty_miles,
    mt.loaded_miles,
    COALESCE(rt.allocated_revenue, 0) AS allocated_revenue,
    COALESCE(sp.stop_appointments, 0) AS stop_appointments,
    COALESCE(sp.on_time_stops, 0) AS on_time_stops,
    COALESCE(op.order_appointments, 0) AS order_appointments,
    COALESCE(op.on_time_orders, 0) AS on_time_orders
FROM movement_totals AS mt
LEFT JOIN revenue_totals AS rt ON rt.manager_id = mt.manager_id
LEFT JOIN stop_performance AS sp ON sp.manager_id = mt.manager_id
LEFT JOIN order_performance AS op ON op.manager_id = mt.manager_id
ORDER BY mt.manager_id;
