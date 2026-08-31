SELECT
    SUM(CASE WHEN COALESCE(RTRIM(status), '') IN ('', 'O') THEN 1 ELSE 0 END) AS active_fleet,
    SUM(CASE WHEN COALESCE(RTRIM(status), '') IN ('', 'O') AND driver1_id IS NOT NULL AND RTRIM(driver1_id) <> '' THEN 1 ELSE 0 END) AS seated_tractors,
    SUM(CASE WHEN COALESCE(RTRIM(status), '') = '' AND driver1_id IS NOT NULL AND RTRIM(driver1_id) <> '' THEN 1 ELSE 0 END) AS dispatch_ready,
    SUM(CASE WHEN COALESCE(RTRIM(status), '') = '' AND (driver1_id IS NULL OR RTRIM(driver1_id) = '') THEN 1 ELSE 0 END) AS ready_to_seat,
    SUM(CASE WHEN COALESCE(RTRIM(status), '') = 'O' THEN 1 ELSE 0 END) AS out_of_service,
    SUM(CASE WHEN COALESCE(RTRIM(status), '') IN ('SP', 'OT') THEN 1 ELSE 0 END) AS special_hold
FROM tractor
WHERE
    company_id = 'TMS'
    AND service_status = 'A';
