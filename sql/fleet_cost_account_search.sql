-- Search the active TMS GL chart by exact account, account prefix, or label.
-- Parameters: raw search, escaped prefix, escaped contains, exact account,
-- escaped prefix. LIKE values use backslash escaping in the repository.
SELECT TOP 20
    RTRIM(id) AS gl_account,
    RTRIM(COALESCE(NULLIF(descr, ''), id)) AS label,
    RTRIM(COALESCE(type_id, '')) AS account_type
FROM gl_account
WHERE
    company_id = 'TMS'
    AND isactive = 'Y'
    AND (
        %s = ''
        OR RTRIM(id) LIKE %s ESCAPE '\'
        OR LOWER(RTRIM(COALESCE(descr, ''))) LIKE LOWER(%s) ESCAPE '\'
    )
ORDER BY
    CASE
        WHEN RTRIM(id) = %s THEN 0
        WHEN RTRIM(id) LIKE %s ESCAPE '\' THEN 1
        ELSE 2
    END,
    id;
