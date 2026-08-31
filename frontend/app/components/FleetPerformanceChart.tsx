'use client';

import { useMemo, useState } from 'react';

export type FleetGranularity = 'day' | 'week' | 'month';

export type FleetPeriod = {
  label: string;
  bucket_start: string;
  bucket_end: string;
  period_start: string;
  period_end: string;
  days_in_period: number;
  order_count: number;
  revenue: number;
  allocated_fleet_cost: number;
  revenue_after_fleet_cost: number;
  fleet_cost_pct_revenue: number | null;
  revenue_per_fleet_cost: number | null;
};

type FleetPerformanceChartProps = {
  periods: FleetPeriod[];
  granularity: FleetGranularity;
};

const money = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

const percent = new Intl.NumberFormat('en-US', {
  style: 'percent',
  maximumFractionDigits: 1,
});

const compactMoney = (value: number) => {
  if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `$${Math.round(value / 1_000)}K`;
  return `$${Math.round(value)}`;
};

export default function FleetPerformanceChart({ periods, granularity }: FleetPerformanceChartProps) {
  // The API provides one normalized period shape; this component only changes
  // presentation based on the selected day/week/month grouping.
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const requestedIndex = activeKey === null
    ? -1
    : periods.findIndex((period) => period.bucket_start === activeKey);
  const activeIndex = requestedIndex >= 0 ? requestedIndex : Math.max(periods.length - 1, 0);

  const geometry = useMemo(() => {
    const width = Math.max(900, periods.length * 34 + 150);
    const height = 430;
    const margin = { top: 30, right: 64, bottom: 68, left: 76 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    // Keep the chart readable for daily ranges by allowing the plot to scroll
    // horizontally instead of squeezing labels into an unusable width.
    const moneyCeiling = Math.max(
      1,
      ...periods.flatMap((period) => [period.revenue, period.allocated_fleet_cost]),
    ) * 1.12;
    const percentageCeiling = Math.max(
      0.2,
      ...periods.map((period) => (period.fleet_cost_pct_revenue ?? 0) * 1.2),
    );
    const step = plotWidth / Math.max(periods.length, 1);
    const groupWidth = Math.min(48, step * 0.7);
    const barWidth = Math.max(3, groupWidth * 0.42);
    const x = (index: number) => margin.left + step * index + step / 2;
    const moneyY = (value: number) => margin.top + plotHeight * (1 - value / moneyCeiling);
    const percentageY = (value: number) => margin.top + plotHeight * (1 - value / percentageCeiling);
    const labelEvery = Math.max(1, Math.ceil(periods.length / 8));
    const labelIndexes = periods
      .map((_, index) => index)
      .filter((index) => index % labelEvery === 0 || index === periods.length - 1);

    // Break the ratio line when revenue is zero; connecting across a missing
    // ratio would imply a value that was never calculated.
    let percentagePath = '';
    let segmentStarted = false;
    periods.forEach((period, index) => {
      if (period.fleet_cost_pct_revenue === null) {
        segmentStarted = false;
        return;
      }
      percentagePath += `${segmentStarted ? ' L' : ' M'} ${x(index)} ${percentageY(period.fleet_cost_pct_revenue)}`;
      segmentStarted = true;
    });

    return {
      width,
      height,
      margin,
      plotHeight,
      moneyCeiling,
      percentageCeiling,
      step,
      barWidth,
      x,
      moneyY,
      percentageY,
      labelIndexes,
      percentagePath,
    };
  }, [periods]);

  if (periods.length === 0) return null;

  const active = periods[Math.min(activeIndex, periods.length - 1)];
  const viewLabel = { day: 'Daily', week: 'Weekly', month: 'Monthly' }[granularity];
  const moneyTicks = [0, 0.25, 0.5, 0.75, 1];

  return (
    <div className="interactive-chart">
      <div className="chart-title-row">
        <div>
          <span>{viewLabel} performance</span>
          <strong>Revenue, fleet cost, and cost ratio</strong>
        </div>
        <div className="chart-legend" aria-label="Chart legend">
          <span><i className="legend-revenue" />Revenue</span>
          <span><i className="legend-cost" />Fleet cost</span>
          <span><i className="legend-ratio" />Cost / revenue</span>
        </div>
      </div>

      <div className="chart-readout" aria-live="polite">
        <div><span>Selected period</span><strong>{active.label}</strong></div>
        <div><span>Revenue</span><strong>{money.format(active.revenue)}</strong></div>
        <div><span>Fleet cost</span><strong>{money.format(active.allocated_fleet_cost)}</strong></div>
        <div><span>After fleet cost</span><strong>{money.format(active.revenue_after_fleet_cost)}</strong></div>
        <div><span>Cost / revenue</span><strong>{active.fleet_cost_pct_revenue === null ? '—' : percent.format(active.fleet_cost_pct_revenue)}</strong></div>
      </div>

      <div className="chart-scroll" role="region" aria-label={`${viewLabel} fleet cost versus revenue chart`}>
        <svg
          className="fleet-svg-chart"
          viewBox={`0 0 ${geometry.width} ${geometry.height}`}
          style={{ width: `${geometry.width}px` }}
          role="img"
          aria-labelledby="fleet-chart-title fleet-chart-description"
        >
          <title id="fleet-chart-title">{viewLabel} fleet cost versus revenue</title>
          <desc id="fleet-chart-description">Revenue and allocated fleet cost are bars. Fleet cost as a percentage of revenue is a line. Hover or focus a period for exact values.</desc>

          {moneyTicks.map((tick) => {
            const y = geometry.margin.top + geometry.plotHeight * (1 - tick);
            return (
              <g key={tick}>
                <line className="chart-gridline" x1={geometry.margin.left} x2={geometry.width - geometry.margin.right} y1={y} y2={y} />
                <text className="chart-axis-label" x={geometry.margin.left - 12} y={y + 4} textAnchor="end">{compactMoney(geometry.moneyCeiling * tick)}</text>
                <text className="chart-axis-label ratio-axis" x={geometry.width - geometry.margin.right + 12} y={y + 4}>{percent.format(geometry.percentageCeiling * tick)}</text>
              </g>
            );
          })}

          {periods.map((period, index) => {
            const center = geometry.x(index);
            const revenueY = geometry.moneyY(period.revenue);
            const costY = geometry.moneyY(period.allocated_fleet_cost);
            const isActive = index === activeIndex;
            return (
              <g
                key={`${period.bucket_start}-${granularity}`}
                className={isActive ? 'chart-period active' : 'chart-period'}
                tabIndex={0}
                onMouseEnter={() => setActiveKey(period.bucket_start)}
                onFocus={() => setActiveKey(period.bucket_start)}
                aria-label={`${period.label}: ${money.format(period.revenue)} revenue, ${money.format(period.allocated_fleet_cost)} fleet cost`}
              >
                {isActive && <rect className="chart-selection" x={center - geometry.step / 2} y={geometry.margin.top} width={geometry.step} height={geometry.plotHeight} />}
                <rect className="chart-bar revenue" x={center - geometry.barWidth - 2} y={revenueY} width={geometry.barWidth} height={geometry.margin.top + geometry.plotHeight - revenueY} rx="2" />
                <rect className="chart-bar cost" x={center + 2} y={costY} width={geometry.barWidth} height={geometry.margin.top + geometry.plotHeight - costY} rx="2" />
                <rect className="chart-hit-area" x={center - geometry.step / 2} y={geometry.margin.top} width={geometry.step} height={geometry.plotHeight} />
              </g>
            );
          })}

          <path className="chart-ratio-line" d={geometry.percentagePath} />
          {periods.map((period, index) => period.fleet_cost_pct_revenue === null ? null : (
            <circle
              key={`ratio-${period.bucket_start}`}
              className={index === activeIndex ? 'chart-ratio-point active' : 'chart-ratio-point'}
              cx={geometry.x(index)}
              cy={geometry.percentageY(period.fleet_cost_pct_revenue)}
              r={index === activeIndex ? 5 : 3.5}
            />
          ))}

          {geometry.labelIndexes.map((index) => (
            <text
              key={`label-${periods[index].bucket_start}`}
              className="chart-x-label"
              x={geometry.x(index)}
              y={geometry.height - 30}
              textAnchor="middle"
            >
              {periods[index].label}
            </text>
          ))}
          <text className="chart-axis-title" x={18} y={geometry.margin.top + geometry.plotHeight / 2} textAnchor="middle" transform={`rotate(-90 18 ${geometry.margin.top + geometry.plotHeight / 2})`}>Revenue and cost</text>
          <text className="chart-axis-title ratio-axis" x={geometry.width - 10} y={geometry.margin.top + geometry.plotHeight / 2} textAnchor="middle" transform={`rotate(90 ${geometry.width - 10} ${geometry.margin.top + geometry.plotHeight / 2})`}>Fleet cost / revenue</text>
        </svg>
      </div>
      <p className="chart-hint">Hover a period—or tab through the chart—for exact values. Daily ranges may scroll horizontally.</p>
    </div>
  );
}
