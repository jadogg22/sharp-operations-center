SELECT
    RTRIM(t.dispatcher) AS manager_id,
    RTRIM(COALESCE(u.name, t.dispatcher)) AS manager_name,
    COUNT(*) AS assigned_trucks,
    SUM(CASE WHEN t.driver1_id IS NOT NULL AND RTRIM(t.driver1_id) <> '' THEN 1 ELSE 0 END) AS seated_trucks,
    SUM(CASE WHEN COALESCE(RTRIM(t.status), '') = '' THEN 1 ELSE 0 END) AS available_trucks,
    SUM(CASE WHEN COALESCE(RTRIM(t.status), '') = 'O' THEN 1 ELSE 0 END) AS out_of_service_trucks
FROM tractor AS t
LEFT JOIN users AS u
    ON u.id = t.dispatcher
    AND u.company_id = t.company_id
WHERE
    t.company_id = 'TMS'
    AND t.service_status = 'A'
    AND t.dispatcher IS NOT NULL
GROUP BY t.dispatcher, u.name
ORDER BY manager_name;
