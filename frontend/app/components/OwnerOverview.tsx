'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

type PerformanceView = 'week' | 'month';
type Team = 'OTR' | 'Local' | 'Part time' | 'Specialized';
type MetricName = 'mptpd' | 'rptpd' | 'deadhead_pct' | 'service_pct';

type PeriodMetrics = {
  working_trucks: number;
  movement_count: number;
  total_miles: number;
  loaded_miles: number;
  empty_miles: number;
  miles_per_truck: number | null;
  mptpd: number | null;
  allocated_revenue: number;
  rptpd: number | null;
  deadhead_pct: number | null;
  stop_otp: number | null;
  order_otp: number | null;
  stop_appointments: number;
  order_appointments: number;
};

type TeamGoals = {
  mptpd: number;
  rptpd: number;
  deadhead_pct: number;
  service_pct: number;
};

type ManagerPerformance = {
  manager_id: string;
  name: string;
  team: Team;
  assigned_trucks: number;
  seated_trucks: number;
  utilization_pct: number | null;
  week: PeriodMetrics;
  month: PeriodMetrics;
  month_mileage_pace_pct: number | null;
  goals: TeamGoals | null;
};

type OverviewResponse = {
  report_date: string;
  generated_at: string;
  week_start: string;
  week_end: string;
  month_start: string;
  business_days_elapsed: number;
  business_days_total: number;
  summary: {
    otr_assigned_trucks: number;
    otr_working_trucks: number;
    otr_miles_per_truck: number | null;
    otr_deadhead_pct: number | null;
    otr_stop_otp: number | null;
    otr_order_otp: number | null;
    active_fleet: number;
    seated_tractors: number;
    seating_pct: number | null;
    dispatch_ready: number;
    ready_to_seat: number;
    out_of_service: number;
    special_hold: number;
  };
  managers: ManagerPerformance[];
  alerts: { level: 'urgent' | 'watch' | 'positive'; title: string; detail: string }[];
  methodology: string[];
};

const number = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });
const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });

const localDateValue = () => {
  // Use the browser's local calendar date so the report does not shift around
  // midnight when the API and browser are running in different time zones.
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
};

const displayDate = (value: string, options?: Intl.DateTimeFormatOptions) =>
  new Date(`${value}T12:00:00`).toLocaleDateString('en-US', options ?? { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });

const percent = (value: number | null, digits = 1) => value === null ? '—' : `${value.toFixed(digits)}%`;

function metricStatus(manager: ManagerPerformance, metric: MetricName, value: number | null) {
  // Color status against the team's goal; deadhead is the one metric where
  // lower is better, while miles, revenue, and service improve when higher.
  if (value === null || !manager.goals) return 'neutral';
  const goal = manager.goals[metric];
  if (metric === 'deadhead_pct') {
    if (value <= goal) return 'good';
    return value <= goal * 1.15 ? 'watch' : 'bad';
  }
  if (value >= goal) return 'good';
  return value >= goal * 0.9 ? 'watch' : 'bad';
}

export default function OwnerOverview({ apiBase }: { apiBase: string }) {
  const [view, setView] = useState<PerformanceView>('week');
  const [selectedDate, setSelectedDate] = useState(localDateValue);
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadOverview = useCallback(async (reportDate: string) => {
    setLoading(true);
    setError('');
    try {
      // Keep the API request date-only. The backend owns the Sunday–Saturday
      // boundary and the month-to-date cutoff so every client agrees.
      const parameters = new URLSearchParams({ report_date: reportDate });
      const response = await fetch(`${apiBase}/overview?${parameters.toString()}`);
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? 'The morning overview could not be loaded.');
      }
      setOverview((await response.json()) as OverviewResponse);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'The morning overview could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, [apiBase]);

  useEffect(() => {
    const timer = window.setTimeout(() => { void loadOverview(selectedDate); }, 0);
    return () => window.clearTimeout(timer);
  }, [loadOverview, selectedDate]);

  const generatedTime = useMemo(() => {
    if (!overview) return '';
    return new Date(overview.generated_at).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  }, [overview]);

  if (!overview && loading) {
    return <section className="ops-overview ops-loading" aria-live="polite"><span /><strong>Building the morning brief from synthetic data…</strong><small>Mileage, revenue, service, and tractor status</small></section>;
  }

  if (!overview) {
    return <section className="ops-overview ops-error" role="alert"><strong>Morning overview unavailable</strong><p>{error}</p><button type="button" onClick={() => void loadOverview(selectedDate)}>Try again</button></section>;
  }

  const summary = overview.summary;
  const periodLabel = view === 'week'
    ? `${displayDate(overview.week_start, { month: 'short', day: 'numeric' })}–${displayDate(overview.week_end, { month: 'short', day: 'numeric' })}`
    : `${displayDate(overview.month_start, { month: 'long' })} · ${overview.business_days_elapsed} of ${overview.business_days_total} workdays`;

  return (
    <section className="ops-overview" aria-labelledby="ops-brief-title">
      <div className="ops-hero">
        <div className="ops-hero-heading">
          <div>
            <p className="step-label">Live morning brief</p>
            <h2 id="ops-brief-title">{displayDate(overview.report_date)}</h2>
            <p>Generated from synthetic SQLite data at {generatedTime}. Weekly totals use the Sunday–Saturday operating window containing this date.</p>
          </div>
          <div className="ops-controls">
            <label><span>Report date</span><input type="date" value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)} /></label>
            <button type="button" onClick={() => void loadOverview(selectedDate)} disabled={loading}>{loading ? 'Refreshing…' : 'Refresh'}</button>
            <button className="quiet" type="button" onClick={() => window.print()}>Print</button>
          </div>
        </div>

        <div className="ops-pulse-grid">
          <div><span>OTR working</span><strong>{summary.otr_working_trucks}</strong><small>{summary.otr_assigned_trucks} currently assigned</small></div>
          <div><span>Week miles / truck</span><strong>{summary.otr_miles_per_truck === null ? '—' : number.format(summary.otr_miles_per_truck)}</strong><small>actual movement miles</small></div>
          <div className={summary.otr_deadhead_pct !== null && summary.otr_deadhead_pct <= 10 ? 'positive' : 'negative'}><span>OTR deadhead</span><strong>{percent(summary.otr_deadhead_pct)}</strong><small>target under 10%</small></div>
          <div className={summary.otr_stop_otp !== null && summary.otr_stop_otp >= 98 ? 'positive' : 'negative'}><span>Stop OTP</span><strong>{percent(summary.otr_stop_otp)}</strong><small>Order {percent(summary.otr_order_otp)}</small></div>
          <div><span>Fleet seated</span><strong>{percent(summary.seating_pct)}</strong><small>{summary.seated_tractors} of {summary.active_fleet}</small></div>
        </div>
      </div>

      {error && <div className="ops-inline-error" role="status">Showing the last successful brief. Refresh failed: {error}</div>}

      <div className="ops-main-grid">
        <article className="ops-panel ops-scorecard">
          <header className="ops-panel-heading">
            <div><p className="step-label">Driver-manager performance</p><h3>{view === 'week' ? 'This week at a glance' : 'Month-to-date pace'}</h3><small>{periodLabel}</small></div>
            <div className="ops-period-toggle" aria-label="Performance period">
              <button type="button" aria-pressed={view === 'week'} onClick={() => setView('week')}>Week</button>
              <button type="button" aria-pressed={view === 'month'} onClick={() => setView('month')}>Month to date</button>
            </div>
          </header>

          <div className="ops-table-wrap">
            <table className="ops-manager-table">
              <thead>
                <tr>
                  <th>Manager / fleet</th>
                  <th>{view === 'week' ? 'Miles / truck' : 'MPTPD'}</th>
                  <th>{view === 'week' ? 'Revenue / truck / day' : 'RPTPD'}</th>
                  <th>Deadhead</th>
                  <th>Stop OTP</th>
                  <th>Order OTP</th>
                </tr>
              </thead>
              <tbody>
                {overview.managers.map((manager) => {
                  const period = manager[view];
                  const milesValue = view === 'week' ? period.miles_per_truck : period.mptpd;
                  return (
                    <tr key={manager.manager_id}>
                      <td><strong>{manager.name}</strong><span>{manager.team} · {period.working_trucks} working · {manager.seated_trucks}/{manager.assigned_trucks} seated</span></td>
                      <td><b className={metricStatus(manager, 'mptpd', view === 'month' ? period.mptpd : null)}>{milesValue === null ? '—' : number.format(milesValue)}</b>{view === 'month' && manager.goals && <small>Goal {number.format(manager.goals.mptpd)}</small>}</td>
                      <td><b className={metricStatus(manager, 'rptpd', period.rptpd)}>{period.rptpd === null ? '—' : money.format(period.rptpd)}</b>{manager.goals && <small>Goal {money.format(manager.goals.rptpd)}</small>}</td>
                      <td><b className={metricStatus(manager, 'deadhead_pct', period.deadhead_pct)}>{percent(period.deadhead_pct)}</b>{manager.goals && <small>Goal &lt;{manager.goals.deadhead_pct}%</small>}</td>
                      <td><b className={metricStatus(manager, 'service_pct', period.stop_otp)}>{percent(period.stop_otp)}</b><small>{number.format(period.stop_appointments)} stops</small></td>
                      <td><b className={metricStatus(manager, 'service_pct', period.order_otp)}>{percent(period.order_otp)}</b><small>{number.format(period.order_appointments)} orders</small></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </article>

        <aside className="ops-side-stack">
          <article className="ops-panel ops-priority-panel">
            <header className="ops-panel-heading compact"><div><p className="step-label">Priority board</p><h3>What needs attention</h3></div><span>{overview.alerts.length}</span></header>
            <ol>
              {overview.alerts.map((alert, index) => (
                <li className={alert.level} key={alert.title}><span>{String(index + 1).padStart(2, '0')}</span><div><strong>{alert.title}</strong><p>{alert.detail}</p></div></li>
              ))}
            </ol>
          </article>
        </aside>
      </div>

      <div className="ops-footer-grid">
        <article className="ops-panel ops-capacity-panel">
          <header className="ops-panel-heading compact"><div><p className="step-label">Capacity by manager</p><h3>Seated tractor coverage</h3></div><span className="ops-legend"><i /> seated</span></header>
          <div className="ops-capacity-list">
            {overview.managers.map((manager) => (
              <div key={manager.manager_id}>
                <div><strong>{manager.name}</strong><small>{manager.seated_trucks} of {manager.assigned_trucks}</small></div>
                <span><i style={{ width: `${manager.utilization_pct ?? 0}%` }} /></span>
                <b>{percent(manager.utilization_pct, 0)}</b>
              </div>
            ))}
          </div>
        </article>

        <article className="ops-panel ops-readiness-panel">
          <header className="ops-panel-heading compact"><div><p className="step-label">Fleet readiness</p><h3>Current tractor status</h3></div></header>
          <div className="ops-readiness-list">
            <div><strong>{summary.dispatch_ready}</strong><span>Dispatch-ready</span><small>Seated and active</small></div>
            <div><strong>{summary.ready_to_seat}</strong><span>Ready to seat</span><small>Active, no driver</small></div>
            <div className="warning"><strong>{summary.out_of_service}</strong><span>Out of service</span><small>Active fleet status</small></div>
            <div><strong>{summary.special_hold}</strong><span>Special hold</span><small>Special or other</small></div>
          </div>
        </article>
      </div>

      <details className="ops-panel ops-methodology">
        <summary><div><p className="step-label">Calculation notes</p><h3>How these numbers are built</h3></div><span>+</span></summary>
        <ol>{overview.methodology.map((note) => <li key={note}>{note}</li>)}</ol>
        <p>This is a best-effort recreation of the morning sheet. The formulas are explicit here so they can be adjusted as the team validates them.</p>
      </details>
    </section>
  );
}
