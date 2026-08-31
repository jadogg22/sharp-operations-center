'use client';

import type { FormEvent } from 'react';
import type { BillingDateResponse, ReportKind } from '../reportTypes';
import type { FleetGranularity } from './FleetPerformanceChart';

type ReportMeta = { button: string };

type Props = {
  activeReport: Exclude<ReportKind, 'overview' | 'pricing'>;
  report: ReportMeta;
  startDate: string;
  endDate: string;
  invoiceEndDate: string;
  invoiceNumber: string;
  expectedTotal: string;
  billingDates: BillingDateResponse | null;
  billingDatesLoading: boolean;
  fleetGranularity: FleetGranularity;
  loading: boolean;
  previewExists: boolean;
  error: string;
  success: string;
  setStartDate: (value: string) => void;
  setEndDate: (value: string) => void;
  setInvoiceEndDate: (value: string) => void;
  setInvoiceNumber: (value: string) => void;
  setExpectedTotal: (value: string) => void;
  handlePrimaryAction: (event: FormEvent<HTMLFormElement>) => void;
  selectBillingDate: (billDate: string) => void;
  changeFleetGranularity: (granularity: FleetGranularity) => void;
};

export default function ReportGenerator({
  activeReport,
  report,
  startDate,
  endDate,
  invoiceEndDate,
  invoiceNumber,
  expectedTotal,
  billingDates,
  billingDatesLoading,
  fleetGranularity,
  loading,
  previewExists,
  error,
  success,
  setStartDate,
  setEndDate,
  setInvoiceEndDate,
  setInvoiceNumber,
  setExpectedTotal,
  handlePrimaryAction,
  selectBillingDate,
  changeFleetGranularity,
}: Props) {
  return (
    <form className="generator-card" aria-labelledby="generator-title" onSubmit={handlePrimaryAction}>
      <div className="card-heading">
        <div><p className="step-label">Report parameters</p><h2 id="generator-title">{activeReport === 'customer' ? 'Choose a billing date' : 'Choose a date range'}</h2></div>
        <span className="step-count">01</span>
      </div>

      {activeReport === 'customer' && (
        <div className="billing-date-picker">
          <div className="billing-date-heading">
            <div><strong>Recent billing dates</strong><span>{billingDates ? `${billingDates.start_date} through ${billingDates.end_date}` : 'Two Mondays back through Friday'}</span></div>
            <small>Selecting a date opens its review immediately.</small>
          </div>
          <div className="billing-date-options">
            {billingDatesLoading && <span className="billing-date-empty">Checking demo billing records…</span>}
            {!billingDatesLoading && billingDates?.dates.map((option) => (
              <button className={startDate === option.bill_date && !invoiceEndDate ? 'billing-date-option selected' : 'billing-date-option'} type="button" key={option.bill_date} onClick={() => selectBillingDate(option.bill_date)} disabled={loading}>
                <strong>{new Date(`${option.bill_date}T12:00:00`).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</strong>
                <span>{option.order_count} {option.order_count === 1 ? 'load' : 'loads'}</span>
                <small>{new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(option.calculated_total)}</small>
              </button>
            ))}
            {!billingDatesLoading && billingDates?.dates.length === 0 && <span className="billing-date-empty">No billing dates were found in this window. Enter a date below.</span>}
            {!billingDatesLoading && !billingDates && <span className="billing-date-empty">Recent dates are unavailable. You can still enter them below.</span>}
          </div>
        </div>
      )}

      <div className={activeReport === 'customer' ? 'date-grid customer-grid' : activeReport === 'fleet' ? 'date-grid fleet-date-grid' : 'date-grid'}>
        <label><span>{activeReport === 'customer' ? 'Bill date' : 'Start date'}</span><input type="date" value={startDate} onChange={(event) => { setStartDate(event.target.value); }} required /></label>
        {activeReport !== 'customer' && <label><span>End date</span><input type="date" min={startDate || undefined} value={endDate} onChange={(event) => setEndDate(event.target.value)} required /></label>}
        {activeReport === 'customer' && <>
          <label><span>End date <small>Optional</small></span><input type="date" min={startDate || undefined} value={invoiceEndDate} onChange={(event) => setInvoiceEndDate(event.target.value)} /></label>
          <label><span>Invoice number</span><input type="text" value={invoiceNumber} onChange={(event) => setInvoiceNumber(event.target.value)} placeholder="Optional reference" maxLength={80} /></label>
          <label><span>Expected total</span><input type="number" min="0" step="0.01" value={expectedTotal} onChange={(event) => setExpectedTotal(event.target.value)} placeholder="Optional check amount" /></label>
        </>}
        {activeReport === 'fleet' && <fieldset className="granularity-field"><legend>Group results by</legend><div className="segmented-control">{(['day', 'week', 'month'] as const).map((granularity) => <button type="button" key={granularity} aria-pressed={fleetGranularity === granularity} onClick={() => changeFleetGranularity(granularity)} disabled={loading}>{granularity === 'day' ? 'Days' : granularity === 'week' ? 'Weeks' : 'Months'}</button>)}</div></fieldset>}
      </div>

      <div className="card-footer">
        <p>{activeReport === 'lane' && 'The report groups Utah outbound and inbound lanes for the selected period.'}{activeReport === 'customer' && 'Leave the end date blank for one billing day, or add it to review a billing period.'}{activeReport === 'fleet' && 'Select any date range and switch between daily, Sunday–Saturday weekly, or monthly views.'}</p>
        <button className="primary-button" type="submit" disabled={loading}>{loading ? 'Working…' : previewExists && activeReport === 'customer' ? 'Refresh billed loads' : report.button}<span aria-hidden="true">→</span></button>
      </div>
      {(error || success) && <div className={error ? 'report-message error' : 'report-message success'} role="status">{error || success}</div>}
    </form>
  );
}
