-- Cost source for the fleet report. Account values are injected as parameter
-- placeholders by the repository; dates use an inclusive start/exclusive end.
-- BBF entries are opening-balance carry-forwards and should not be treated as
-- current-period fleet expense.
SELECT
    RTRIM(glid) AS gl_account,
    CAST(transaction_date AS date) AS transaction_date,
    CAST(SUM(COALESCE(amount, 0)) AS float) AS amount
FROM gl_ledger
WHERE
    company_id = 'TMS'
    AND glid IN ({{GL_ACCOUNT_PLACEHOLDERS}})
    AND transaction_date >= %s
    AND transaction_date < %s
    AND (transaction_no <> 'BBF' OR transaction_no IS NULL)
GROUP BY glid, CAST(transaction_date AS date)
ORDER BY CAST(transaction_date AS date), glid;
