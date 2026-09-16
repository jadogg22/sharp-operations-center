-- Resolve selected accounts against the authoritative active TMS GL chart.
-- The repository replaces the token with one parameter placeholder per ID.
SELECT
    RTRIM(id) AS gl_account,
    RTRIM(COALESCE(NULLIF(descr, ''), id)) AS label,
    RTRIM(COALESCE(type_id, '')) AS account_type
FROM gl_account
WHERE
    company_id = 'TMS'
    AND isactive = 'Y'
    AND id IN ({{GL_ACCOUNT_PLACEHOLDERS}})
ORDER BY id;
