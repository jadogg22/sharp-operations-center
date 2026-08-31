'use client';

import { useMemo, useState } from 'react';
import { calculatePricing } from '../pricingCalculations';

type RateMode = 'per-mile' | 'whole-load';
type SurchargeMode = 'per-mile' | 'round-trip';

const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });

const inputNumber = (value: string) => {
  if (value.trim() === '') return 0;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.max(parsed, 0) : 0;
};

const editableNumber = (value: number, decimals = 2) =>
  value === 0 ? '0' : value.toFixed(decimals).replace(/\.00$/, '');

export default function LoadPricingCalculator() {
  const [cpm, setCpm] = useState(2.25);
  const [loadedMilesInput, setLoadedMilesInput] = useState('500');
  const [deadheadMilesInput, setDeadheadMilesInput] = useState('50');
  const [outboundRateInput, setOutboundRateInput] = useState('3');
  const [inboundRateInput, setInboundRateInput] = useState('2.5');
  const [rateMode, setRateMode] = useState<RateMode>('per-mile');
  const [fuelSurchargeInput, setFuelSurchargeInput] = useState('0');
  const [surchargeMode, setSurchargeMode] = useState<SurchargeMode>('round-trip');
  const [targetMargin, setTargetMargin] = useState(15);

  const loadedMiles = inputNumber(loadedMilesInput);
  const deadheadMiles = inputNumber(deadheadMilesInput);
  const outboundEnteredRate = inputNumber(outboundRateInput);
  const inboundEnteredRate = inputNumber(inboundRateInput);
  const enteredFuelSurcharge = inputNumber(fuelSurchargeInput);

  const results = useMemo(() => {
    return calculatePricing({ cpm, loadedMiles, deadheadMiles, outboundRate: outboundEnteredRate, inboundRate: inboundEnteredRate, rateMode, fuelSurcharge: enteredFuelSurcharge, surchargeMode, targetMargin });
  }, [cpm, deadheadMiles, enteredFuelSurcharge, inboundEnteredRate, loadedMiles, outboundEnteredRate, rateMode, surchargeMode, targetMargin]);

  const changeRateMode = (nextMode: RateMode) => {
    if (nextMode === rateMode) return;

    // Preserve revenue while converting the editable values between entry modes.
    if (nextMode === 'whole-load') {
      setOutboundRateInput(editableNumber(results.outboundTotal));
      setInboundRateInput(editableNumber(results.inboundTotal));
    } else {
      setOutboundRateInput(editableNumber(results.outboundPerMile));
      setInboundRateInput(editableNumber(results.inboundPerMile));
    }
    setRateMode(nextMode);
  };

  const changeSurchargeMode = (nextMode: SurchargeMode) => {
    if (nextMode === surchargeMode) return;

    // Keep fuel revenue unchanged when switching how the surcharge is entered.
    setFuelSurchargeInput(editableNumber(
      nextMode === 'round-trip' ? results.fuelSurchargeTotal : results.fuelSurchargePerMile,
    ));
    setSurchargeMode(nextMode);
  };

  const targetMet = results.margin >= targetMargin;
  const revenueGap = Math.max(results.targetRevenue - results.revenue, 0);
  const marginClass = targetMet ? 'target-met' : results.margin < 0 ? 'negative' : 'below-target';
  const revenueProgress = results.targetRevenue > 0
    ? Math.min((results.revenue / results.targetRevenue) * 100, 100)
    : 0;

  return (
    <div className="pricing-tool">
      <div className="pricing-intro">
        <div><p className="step-label">Sales planning</p><h2>Build a profitable round trip</h2></div>
        <p>Adjust the assumptions and see the required return rate update live. Enter customer rates per loaded mile or as the whole load amount.</p>
      </div>

      <div className="pricing-layout">
        <section className="pricing-inputs" aria-label="Load assumptions">
          <div className="pricing-step">
            <div className="pricing-step-heading">
              <span>01</span>
              <div><strong>Set the route</strong><small>Start with the miles the truck will actually run.</small></div>
            </div>
            <div className="pricing-number-grid">
              <label><span>Loaded miles, one way</span><input type="number" min="0" step="1" value={loadedMilesInput} onChange={(event) => setLoadedMilesInput(event.target.value)} placeholder="Enter miles" /></label>
              <label><span>Total deadhead miles</span><input type="number" min="0" step="1" value={deadheadMilesInput} onChange={(event) => setDeadheadMilesInput(event.target.value)} placeholder="Enter deadhead" /></label>
            </div>
          </div>

          <div className="pricing-step">
            <div className="pricing-step-heading">
              <span>02</span>
              <div><strong>Set cost and target</strong><small>Use the sliders to define the floor for the trip.</small></div>
            </div>
            <div className="pricing-goal-controls">
              <label className="pricing-slider-label">
                <span className="pricing-label-row"><span>Cost per mile</span><output>{money.format(cpm)}</output></span>
                <input className="range-input" type="range" min="1" max="5" step="0.05" value={cpm} onChange={(event) => setCpm(Number(event.target.value))} />
                <span className="range-endpoints"><small>$1.00</small><small>$5.00</small></span>
              </label>

              <label className="pricing-slider-label">
                <span className="pricing-label-row"><span>Target profit margin</span><output>{targetMargin}%</output></span>
                <input className="range-input" type="range" min="0" max="40" step="1" value={targetMargin} onChange={(event) => setTargetMargin(Number(event.target.value))} />
                <span className="range-endpoints"><small>0%</small><small>40%</small></span>
              </label>
            </div>
          </div>

          <div className="pricing-step">
            <div className="pricing-step-heading">
              <span>03</span>
              <div><strong>Enter customer rates</strong><small>Add the known linehaul and fuel revenue.</small></div>
            </div>

            <fieldset className="rate-entry-field">
              <legend>Enter customer rates as</legend>
              <div className="rate-entry-toggle">
                <button type="button" aria-pressed={rateMode === 'per-mile'} onClick={() => changeRateMode('per-mile')}>Rate per mile</button>
                <button type="button" aria-pressed={rateMode === 'whole-load'} onClick={() => changeRateMode('whole-load')}>Whole load rate</button>
              </div>
            </fieldset>

            <div className="pricing-number-grid pricing-rate-grid">
              <label>
                <span>Outbound {rateMode === 'per-mile' ? 'rate / loaded mile' : 'whole load rate'}</span>
                <input type="number" min="0" step="0.01" value={outboundRateInput} onChange={(event) => setOutboundRateInput(event.target.value)} placeholder="Enter outbound rate" />
                <small>{rateMode === 'per-mile' ? `${money.format(results.outboundTotal)} whole load` : `${money.format(results.outboundPerMile)} / loaded mile`}</small>
              </label>
              <label>
                <span>Inbound {rateMode === 'per-mile' ? 'rate / loaded mile' : 'whole load rate'}</span>
                <input type="number" min="0" step="0.01" value={inboundRateInput} onChange={(event) => setInboundRateInput(event.target.value)} placeholder="Enter inbound rate" />
                <small>{rateMode === 'per-mile' ? `${money.format(results.inboundTotal)} whole load` : `${money.format(results.inboundPerMile)} / loaded mile`}</small>
              </label>
            </div>

            <fieldset className="fuel-entry-field">
              <legend>Fuel surcharge</legend>
              <div className="fuel-entry-control">
                <input type="number" min="0" step="0.01" value={fuelSurchargeInput} onChange={(event) => setFuelSurchargeInput(event.target.value)} placeholder="Enter surcharge" aria-label="Fuel surcharge" />
                <div className="fuel-mode-toggle">
                  <button type="button" aria-pressed={surchargeMode === 'per-mile'} onClick={() => changeSurchargeMode('per-mile')}>Per mile</button>
                  <button type="button" aria-pressed={surchargeMode === 'round-trip'} onClick={() => changeSurchargeMode('round-trip')}>Total</button>
                </div>
              </div>
              <small>{surchargeMode === 'per-mile' ? `${money.format(results.fuelSurchargeTotal)} round-trip fuel revenue` : `${money.format(results.fuelSurchargePerMile)} per loaded mile across both legs`}</small>
            </fieldset>
          </div>
        </section>

        <section className="pricing-results" aria-live="polite">
          <article className="pricing-quote-card">
            <div className="quote-card-heading">
              <div><span>Recommended return quote</span><small>To reach a {targetMargin}% round-trip margin</small></div>
              <span className={targetMet ? 'quote-status target-met' : 'quote-status below-target'}>{targetMet ? 'Margin covered' : `${money.format(revenueGap)} gap`}</span>
            </div>
            <div className="quote-values">
              <div><span>Target inbound load</span><strong>{money.format(results.targetInboundTotal)}</strong></div>
              <div><span>Per loaded mile</span><strong>{money.format(results.targetInboundPerMile)}</strong></div>
            </div>
            <p>Outbound is held at {money.format(results.outboundTotal)} and fuel surcharge at {money.format(results.fuelSurchargeTotal)}. The recommendation is the remaining inbound linehaul needed for the target.</p>
          </article>

          <div className={`pricing-breakdown ${marginClass}`}>
            <div className="margin-heading">
              <div><span>Margin check</span><strong>{results.margin.toFixed(1)}%</strong><small>Actual margin</small></div>
              <span className="margin-status">{targetMet ? 'On target' : `Below ${targetMargin}% target`}</span>
            </div>
            <div className="pricing-label-row"><span>Revenue progress</span><strong>{money.format(results.revenue)} of {money.format(results.targetRevenue)}</strong></div>
            <div className="pricing-bar"><i style={{ width: `${revenueProgress}%` }} /></div>
            <p>{targetMet ? 'The entered rates clear the requested margin.' : `The round trip needs ${money.format(revenueGap)} more revenue to reach the target.`}</p>
          </div>

          <div className="pricing-results-section">
            <p className="pricing-results-label">Current plan</p>
            <div className="pricing-results-grid">
              <article className="pricing-result-card"><span>Total round-trip revenue</span><strong>{money.format(results.revenue)}</strong><small>Includes {money.format(results.fuelSurchargeTotal)} fuel surcharge</small></article>
              <article className="pricing-result-card"><span>Estimated fleet cost</span><strong>{money.format(results.operatingCost)}</strong><small>{results.totalMiles.toLocaleString()} total miles × {money.format(cpm)}</small></article>
              <article className={`pricing-result-card ${results.profit >= 0 ? '' : 'warning'}`}><span>Profit after fleet cost</span><strong>{money.format(results.profit)}</strong><small>{results.margin.toFixed(1)}% actual margin</small></article>
            </div>
          </div>
        </section>
      </div>

      <details className="pricing-math-details">
        <summary><div><span>Supporting target math</span><small>Revenue, average rate, and mileage behind the recommendation</small></div></summary>
        <div className="pricing-target-grid">
          <article className="target-card primary"><span>Target round-trip revenue</span><strong>{money.format(results.targetRevenue)}</strong><small>Revenue needed for a {targetMargin}% margin</small></article>
          <article className="target-card"><span>Target average loaded rate</span><strong>{money.format(results.targetAverageLoadedRate)}</strong><small>Per mile across both loaded legs</small></article>
          <article className="target-card"><span>Round-trip mileage</span><strong>{results.totalMiles.toLocaleString()}</strong><small>{results.totalLoadedMiles.toLocaleString()} loaded + {deadheadMiles.toLocaleString()} deadhead</small></article>
        </div>
        <p className="pricing-note">Assumes CPM applies to every loaded and deadhead mile, and both loaded legs use the same one-way mileage. Fuel surcharge is treated as additional revenue. The target inbound load is the remaining linehaul revenue required after outbound and fuel surcharge.</p>
      </details>
    </div>
  );
}
