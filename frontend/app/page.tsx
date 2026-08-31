'use client';

import { useEffect, useMemo, useState, type FormEvent } from 'react';
import Image from 'next/image';

import type { FleetGranularity } from './components/FleetPerformanceChart';
import FleetReportPanel from './components/FleetReportPanel';
import LoadPricingCalculator from './components/LoadPricingCalculator';
import OwnerOverview from './components/OwnerOverview';
import ReportGenerator from './components/ReportGenerator';
import CustomerReview from './components/CustomerReview';
import { downloadResponse, reportError } from './reportClient';
import type { BillingDateResponse, FleetPreview, PreviewOrder, ReportKind, CustomerPreview } from './reportTypes';

const reports = {
  overview: { eyebrow: 'Morning operations', title: 'Owner overview', description: 'See fleet capacity, manager performance, service risks, and today’s operational exceptions in one briefing.', button: 'View briefing', format: 'AUG 28' },
  lane: { eyebrow: 'Operations intelligence', title: 'Lane profitability', description: 'Compare outbound and inbound performance, trip volume, empty miles, and lane quality across a selected period.', button: 'Generate PDF report', format: 'PDF' },
  customer: { eyebrow: 'Customer billing', title: 'Customer invoice', description: 'Choose a recent billing day or enter a custom period, review every charge, and export a verified billing workbook.', button: 'Review billed loads', format: 'XLSX' },
  fleet: { eyebrow: 'Owner economics', title: 'Fleet cost vs revenue', description: 'Compare operating revenue with fleet cost by day, Sunday–Saturday week, or calendar month.', button: 'Build cost view', format: 'CSV + CHART' },
  pricing: { eyebrow: 'Sales planning', title: 'Load pricing builder', description: 'Test CPM, mileage, and both loaded rates together to find a target that covers the round trip and your margin.', button: 'Adjust assumptions', format: 'LIVE TOOL' },
} as const;

const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
const percent = new Intl.NumberFormat('en-US', { style: 'percent', maximumFractionDigits: 1 });

export default function Home() {
  const [activeReport, setActiveReport] = useState<ReportKind>('overview');
  const [startDate, setStartDate] = useState('2026-08-24');
  const [endDate, setEndDate] = useState('2026-08-30');
  const [invoiceEndDate, setInvoiceEndDate] = useState('');
  const [invoiceNumber, setInvoiceNumber] = useState('');
  const [expectedTotal, setExpectedTotal] = useState('');
  const [preview, setPreview] = useState<CustomerPreview | null>(null);
  const [fleetPreview, setFleetPreview] = useState<FleetPreview | null>(null);
  const [fleetGranularity, setFleetGranularity] = useState<FleetGranularity>('week');
  const [billingDates, setBillingDates] = useState<BillingDateResponse | null>(null);
  const [billingDatesLoading, setBillingDatesLoading] = useState(true);
  const [editMode, setEditMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const report = reports[activeReport];
  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? '/api';

  useEffect(() => {
    let active = true;
    const loadBillingDates = async () => {
      try {
        const response = await fetch(`${apiBase}/reports/customer-invoice/billing-dates`);
        if (!response.ok) await reportError(response, 'Recent billing dates could not be loaded.');
        const result = (await response.json()) as BillingDateResponse;
        if (active) setBillingDates(result);
      } catch {
        if (active) setBillingDates(null);
      } finally {
        if (active) setBillingDatesLoading(false);
      }
    };
    void loadBillingDates();
    return () => { active = false; };
  }, [apiBase]);

  const reviewedTotal = useMemo(() => preview?.orders.filter((order) => order.included).reduce((sum, order) => sum + order.total_charge, 0) ?? 0, [preview]);
  const includedOrders = preview?.orders.filter((order) => order.included).length ?? 0;
  const expected = expectedTotal === '' ? null : Number(expectedTotal);
  const variance = expected === null || Number.isNaN(expected) ? null : reviewedTotal - expected;

  const chooseReport = (kind: ReportKind) => {
    setActiveReport(kind); setPreview(null); setFleetPreview(null); setEditMode(false); setError(''); setSuccess('');
  };
  const setStartDateAndReset = (value: string) => { setStartDate(value); setPreview(null); setFleetPreview(null); };
  const setEndDateAndReset = (value: string) => { setEndDate(value); setFleetPreview(null); };
  const setInvoiceEndDateAndReset = (value: string) => { setInvoiceEndDate(value); setPreview(null); };
  const downloadReport = async (response: Response, fallbackFilename: string) => { setSuccess(`${await downloadResponse(response, fallbackFilename)} is ready.`); };

  const loadCustomerPreview = async (billDate: string, optionalEndDate = '') => {
    const parameters = new URLSearchParams({ bill_date: billDate });
    if (optionalEndDate) parameters.set('end_date', optionalEndDate);
    const response = await fetch(`${apiBase}/reports/customer-invoice/preview?${parameters.toString()}`);
    if (!response.ok) await reportError(response, 'The billed loads could not be loaded.');
    const result = await response.json() as Omit<CustomerPreview, 'orders'> & { orders: Omit<PreviewOrder, 'included'>[] };
    setPreview({ ...result, orders: result.orders.map((order) => ({ ...order, included: true })) }); setEditMode(false);
  };

  const selectBillingDate = async (billDate: string) => {
    setStartDate(billDate); setInvoiceEndDate(''); setError(''); setSuccess(''); setLoading(true);
    try { await loadCustomerPreview(billDate); } catch (errorValue) { setError(errorValue instanceof Error ? errorValue.message : 'The billed loads could not be loaded.'); } finally { setLoading(false); }
  };

  const loadFleetPreview = async (granularity: FleetGranularity) => {
    const parameters = new URLSearchParams({ start_date: startDate, end_date: endDate, granularity });
    const response = await fetch(`${apiBase}/reports/fleet-cost-revenue/preview?${parameters.toString()}`);
    if (!response.ok) await reportError(response, 'The fleet analysis could not be loaded.');
    setFleetPreview(await response.json() as FleetPreview);
  };

  const changeFleetGranularity = async (granularity: FleetGranularity) => {
    setFleetGranularity(granularity); if (!fleetPreview) return;
    setLoading(true); setError(''); setSuccess('');
    try { await loadFleetPreview(granularity); } catch (errorValue) { setError(errorValue instanceof Error ? errorValue.message : 'The fleet analysis could not be loaded.'); } finally { setLoading(false); }
  };

  const handlePrimaryAction = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(''); setSuccess('');
    if (activeReport === 'pricing' || activeReport === 'overview') return;
    if (!startDate) { setError(activeReport === 'customer' ? 'Choose the bill date.' : 'Choose a start date.'); return; }
    if (activeReport !== 'customer' && (!endDate || endDate < startDate)) { setError(!endDate ? 'Choose an end date.' : 'The end date must be on or after the start date.'); return; }
    if (activeReport === 'customer' && invoiceEndDate && invoiceEndDate < startDate) { setError('The optional end date must be on or after the bill date.'); return; }
    setLoading(true);
    try {
      if (activeReport === 'lane') {
        const response = await fetch(`${apiBase}/reports/lane-profitability?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`);
        await downloadReport(response, 'lane-profitability.pdf');
      } else if (activeReport === 'customer') await loadCustomerPreview(startDate, invoiceEndDate);
      else await loadFleetPreview(fleetGranularity);
    } catch (errorValue) { setError(errorValue instanceof Error ? errorValue.message : 'The report could not be generated.'); } finally { setLoading(false); }
  };

  const updateOrder = (index: number, field: keyof PreviewOrder, value: string | number | boolean) => {
    setPreview((current) => {
      if (!current) return current;
      const orders = [...current.orders]; const nextOrder = { ...orders[index], [field]: value };
      if (typeof value === 'number' && ['freight_charge', 'fuel_surcharge', 'extra_drops', 'extra_pickups', 'other_charges'].includes(field)) {
        nextOrder.other_charge_total = nextOrder.fuel_surcharge + nextOrder.extra_drops + nextOrder.extra_pickups + nextOrder.other_charges;
        nextOrder.total_charge = nextOrder.freight_charge + nextOrder.other_charge_total;
      }
      orders[index] = nextOrder; return { ...current, orders };
    });
  };

  const generateReviewedInvoice = async () => {
    if (!preview || includedOrders === 0) { setError('Include at least one order before generating the invoice.'); return; }
    setLoading(true); setError(''); setSuccess('');
    try {
      const rows = preview.orders.filter((order) => order.included).flatMap((order) => order.stops.map((stop) => ({ ...stop, bol_number: order.bol_number, trailer_number: order.trailer_number, miles: order.miles, total_pallets: order.total_pallets, freight_charge: order.freight_charge, fuel_surcharge: order.fuel_surcharge, extra_drops: order.extra_drops, extra_pickups: order.extra_pickups, other_charges: order.other_charges, other_charge_total: order.other_charge_total, total_charge: order.total_charge })));
      const response = await fetch(`${apiBase}/reports/customer-invoice`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bill_date: startDate, end_date: invoiceEndDate || null, invoice_number: invoiceNumber, expected_total: expected, rows }) });
      await downloadReport(response, 'customer-invoice.xlsx');
    } catch (errorValue) { setError(errorValue instanceof Error ? errorValue.message : 'The invoice could not be generated.'); } finally { setLoading(false); }
  };

  const downloadFleetFile = async (format: 'csv' | 'png') => {
    if (!fleetPreview) return;
    setLoading(true); setError(''); setSuccess('');
    try {
      const parameters = new URLSearchParams({ start_date: startDate, end_date: endDate, granularity: fleetGranularity });
      const response = await fetch(`${apiBase}/reports/fleet-cost-revenue.${format}?${parameters.toString()}`);
      await downloadReport(response, `fleet-cost-revenue.${format}`);
    } catch (errorValue) { setError(errorValue instanceof Error ? errorValue.message : 'The file could not be downloaded.'); } finally { setLoading(false); }
  };

  return (
    <main className="app-shell">
      <header className="topbar"><div className="brand-lockup"><span className="brand-mark" aria-hidden="true"><Image src="/sharp-35th-logo.png" alt="" width={68} height={48} priority /></span><div><p className="brand-name">Sharp Transportation</p><p className="brand-subtitle">Operations center</p></div></div><div className="connection-status"><span className="status-dot" aria-hidden="true" />Synthetic portfolio data</div></header>
      <section className="workspace">
        <aside className="report-nav" aria-label="Reports"><div><p className="nav-label">Reports</p><nav>{(['overview', 'lane', 'customer', 'fleet', 'pricing'] as const).map((kind) => <button key={kind} className={activeReport === kind ? 'nav-item active' : 'nav-item'} onClick={() => chooseReport(kind)}><span className="nav-icon">{kind === 'overview' ? 'OV' : kind === 'lane' ? 'LP' : kind === 'customer' ? 'CI' : kind === 'fleet' ? 'FR' : '$'}</span><span><strong>{reports[kind].title}</strong><small>{kind === 'overview' ? 'Morning brief' : kind === 'lane' ? 'PDF analysis' : kind === 'customer' ? 'Excel billing' : kind === 'fleet' ? 'CSV + chart' : 'Sales targets'}</small></span></button>)}</nav></div><div className="source-card"><span className="source-icon">DB</span><div><strong>SQLite demo mode</strong><p>Synthetic records exercise the complete reporting workflow.</p></div></div></aside>
        <div className="content-area">
          <div className="content-header"><div><p className="eyebrow">{report.eyebrow}</p><h1>{report.title}</h1><p className="lede">{report.description}</p></div><span className="format-chip">{report.format}</span></div>
          {activeReport === 'overview' && <OwnerOverview apiBase={apiBase} />}
          {activeReport === 'pricing' && <div className="generator-card"><LoadPricingCalculator /></div>}
          {(['lane', 'customer', 'fleet'] as const).includes(activeReport as 'lane' | 'customer' | 'fleet') && <ReportGenerator activeReport={activeReport as 'lane' | 'customer' | 'fleet'} report={report} startDate={startDate} endDate={endDate} invoiceEndDate={invoiceEndDate} invoiceNumber={invoiceNumber} expectedTotal={expectedTotal} billingDates={billingDates} billingDatesLoading={billingDatesLoading} fleetGranularity={fleetGranularity} loading={loading} previewExists={Boolean(preview)} error={error} success={success} setStartDate={setStartDateAndReset} setEndDate={setEndDateAndReset} setInvoiceEndDate={setInvoiceEndDateAndReset} setInvoiceNumber={setInvoiceNumber} setExpectedTotal={setExpectedTotal} handlePrimaryAction={handlePrimaryAction} selectBillingDate={(billDate) => void selectBillingDate(billDate)} changeFleetGranularity={(granularity) => void changeFleetGranularity(granularity)} />}
          {activeReport === 'customer' && preview && <CustomerReview preview={preview} editMode={editMode} setEditMode={setEditMode} includedOrders={includedOrders} reviewedTotal={reviewedTotal} expected={expected} variance={variance} loading={loading} money={money} updateOrder={updateOrder} generateReviewedInvoice={() => void generateReviewedInvoice()} />}
          {activeReport === 'fleet' && fleetPreview && <FleetReportPanel preview={fleetPreview} granularity={fleetGranularity} loading={loading} money={money} percent={percent} downloadFleetFile={(format) => void downloadFleetFile(format)} />}
          {!preview && !fleetPreview && activeReport !== 'pricing' && activeReport !== 'overview' && <div className="details-row"><article><span className="detail-number">01</span><div><h3>Replaceable data layer</h3><p>The public build queries a seeded SQLite database through the same repository boundary used in production.</p></div></article><article><span className="detail-number">02</span><div><h3>Review before download</h3><p>Verify orders and totals before creating the billing file.</p></div></article></div>}
        </div>
      </section>
    </main>
  );
}
