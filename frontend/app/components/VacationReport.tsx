'use client';

import { useEffect, useState } from 'react';

import { downloadResponse, reportError } from '../reportClient';

type VacationRow = {
  employee_group: string;
  employee_id: string;
  employee_name: string;
  company_id: string;
  vacation_hours_due: number | null;
  vacation_pay_rate: number | null;
  amount_due: number;
};

type Props = { apiBase: string };

const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });

export default function VacationReport({ apiBase }: Props) {
  const [rows, setRows] = useState<VacationRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const response = await fetch(`${apiBase}/reports/vacation/preview`);
        if (!response.ok) await reportError(response, 'Vacation balances could not be loaded.');
        const result = await response.json() as { rows?: VacationRow[] };
        if (active) setRows(result.rows ?? []);
      } catch (errorValue) {
        if (active) setError(errorValue instanceof Error ? errorValue.message : 'Vacation balances could not be loaded.');
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    return () => { active = false; };
  }, [apiBase]);

  const download = async () => {
    setDownloading(true); setError('');
    try {
      const response = await fetch(`${apiBase}/reports/vacation.csv`);
      await downloadResponse(response, 'employee-vacation-balances.csv');
    } catch (errorValue) {
      setError(errorValue instanceof Error ? errorValue.message : 'The vacation report could not be downloaded.');
    } finally { setDownloading(false); }
  };

  return (
    <section className="vacation-card" aria-labelledby="vacation-title">
      <div className="card-heading">
        <div><p className="step-label">People operations</p><h2 id="vacation-title">Vacation balance report</h2></div>
        <button className="primary-button" type="button" onClick={() => void download()} disabled={loading || downloading}>{downloading ? 'Preparing…' : 'Download CSV'}<span aria-hidden="true">↓</span></button>
      </div>
      {loading && <p className="report-message">Loading current balances…</p>}
      {error && <p className="report-message error" role="status">{error}</p>}
      {!loading && !error && <>
        <div className="vacation-summary"><div><span>Employees</span><strong>{rows.length}</strong></div><div><span>Estimated amount due</span><strong>{money.format(rows.reduce((sum, row) => sum + row.amount_due, 0))}</strong></div><div><span>Missing inputs</span><strong>{rows.filter((row) => row.vacation_hours_due === null || row.vacation_pay_rate === null).length}</strong></div></div>
        <div className="vacation-table-wrap"><table className="vacation-table"><thead><tr><th>Employee</th><th>Group</th><th>Hours due</th><th>Pay rate</th><th>Estimated amount</th></tr></thead><tbody>{rows.map((row) => <tr key={`${row.company_id}-${row.employee_id}`}><td><strong>{row.employee_name}</strong><small>{row.employee_id} · {row.company_id}</small></td><td>{row.employee_group}</td><td>{row.vacation_hours_due === null ? 'Not entered' : row.vacation_hours_due.toFixed(2)}</td><td>{row.vacation_pay_rate === null ? 'Not entered' : money.format(row.vacation_pay_rate)}</td><td><strong>{money.format(row.amount_due)}</strong></td></tr>)}</tbody></table></div>
      </>}
    </section>
  );
}
