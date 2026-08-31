'use client';

import FleetPerformanceChart, { type FleetGranularity } from './FleetPerformanceChart';
import type { FleetPreview } from '../reportTypes';

type Props = {
  preview: FleetPreview;
  granularity: FleetGranularity;
  loading: boolean;
  money: Intl.NumberFormat;
  percent: Intl.NumberFormat;
  downloadFleetFile: (format: 'csv' | 'png') => void;
};

export default function FleetReportPanel({ preview, granularity, loading, money, percent, downloadFleetFile }: Props) {
  return (
    <section className="fleet-card" aria-labelledby="fleet-results-title">
      <div className="review-heading fleet-heading">
        <div>
          <p className="step-label">{granularity} analysis</p>
          <h2 id="fleet-results-title">Fleet cost performance</h2>
          <p>{preview.methodology}</p>
        </div>
        <div className="download-actions">
          <button className="secondary-button" type="button" onClick={() => downloadFleetFile('csv')} disabled={loading}>Download CSV</button>
          <button className="primary-button" type="button" onClick={() => downloadFleetFile('png')} disabled={loading}>Download chart</button>
        </div>
      </div>

      <div className="fleet-summary">
        <div><span>Revenue</span><strong>{money.format(preview.summary.revenue)}</strong><small>{preview.summary.order_count.toLocaleString()} orders</small></div>
        <div><span>Allocated fleet cost</span><strong>{money.format(preview.summary.allocated_fleet_cost)}</strong><small>GL {preview.cost_categories.map((category) => category.gl_account).join(', ')}</small></div>
        <div><span>Revenue after fleet cost</span><strong>{money.format(preview.summary.revenue_after_fleet_cost)}</strong><small>Before all other expenses</small></div>
        <div><span>Fleet cost / revenue</span><strong>{preview.summary.fleet_cost_pct_revenue === null ? '—' : percent.format(preview.summary.fleet_cost_pct_revenue)}</strong><small>{preview.summary.revenue_per_fleet_cost === null ? 'No fleet cost' : `${money.format(preview.summary.revenue_per_fleet_cost)} revenue per $1`}</small></div>
      </div>

      <FleetPerformanceChart periods={preview.periods} granularity={preview.granularity} />

      <div className="fleet-table-wrap">
        <table className="fleet-table">
          <thead><tr><th>{granularity === 'day' ? 'Day' : granularity === 'week' ? 'Week' : 'Month'}</th><th>Orders</th><th>Revenue</th><th>Fleet cost</th><th>After fleet cost</th><th>Cost / revenue</th></tr></thead>
          <tbody>
            {preview.periods.map((period) => (
              <tr key={period.bucket_start}>
                <td><strong>{period.label}</strong>{(period.period_start !== period.bucket_start || period.period_end !== period.bucket_end) && <small>{period.period_start}–{period.period_end} selected</small>}</td>
                <td>{period.order_count.toLocaleString()}</td>
                <td>{money.format(period.revenue)}</td>
                <td>{money.format(period.allocated_fleet_cost)}</td>
                <td>{money.format(period.revenue_after_fleet_cost)}</td>
                <td>{period.fleet_cost_pct_revenue === null ? '—' : percent.format(period.fleet_cost_pct_revenue)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
