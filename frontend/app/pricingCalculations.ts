export type PricingInputs = {
  cpm: number;
  loadedMiles: number;
  deadheadMiles: number;
  outboundRate: number;
  inboundRate: number;
  rateMode: 'per-mile' | 'whole-load';
  fuelSurcharge: number;
  surchargeMode: 'per-mile' | 'round-trip';
  targetMargin: number;
  outOfBounds: boolean;
  outOfBoundsProfitUplift: number;
};

export type PricingResults = {
  totalLoadedMiles: number;
  totalMiles: number;
  operatingCost: number;
  outboundTotal: number;
  inboundTotal: number;
  outboundPerMile: number;
  inboundPerMile: number;
  fuelSurchargeTotal: number;
  fuelSurchargePerMile: number;
  revenue: number;
  profit: number;
  margin: number;
  baseTargetRevenue: number;
  baseTargetProfit: number;
  outOfBoundsPremium: number;
  targetRevenue: number;
  effectiveTargetMargin: number;
  targetInboundTotal: number;
  targetInboundPerMile: number;
  targetAverageLoadedRate: number;
  actualAverageLoadedRate: number;
};

/** Calculate all pricing outputs from normalized sales assumptions. */
export function calculatePricing(inputs: PricingInputs): PricingResults {
  const totalLoadedMiles = inputs.loadedMiles * 2;
  const totalMiles = totalLoadedMiles + inputs.deadheadMiles;
  const operatingCost = totalMiles * Math.max(inputs.cpm, 0);
  const outboundTotal = inputs.rateMode === 'per-mile' ? inputs.outboundRate * inputs.loadedMiles : inputs.outboundRate;
  const inboundTotal = inputs.rateMode === 'per-mile' ? inputs.inboundRate * inputs.loadedMiles : inputs.inboundRate;
  const fuelSurchargeTotal = inputs.surchargeMode === 'per-mile' ? inputs.fuelSurcharge * totalLoadedMiles : inputs.fuelSurcharge;
  const fuelSurchargePerMile = totalLoadedMiles > 0 ? fuelSurchargeTotal / totalLoadedMiles : 0;
  const outboundPerMile = inputs.loadedMiles > 0 ? outboundTotal / inputs.loadedMiles : 0;
  const inboundPerMile = inputs.loadedMiles > 0 ? inboundTotal / inputs.loadedMiles : 0;
  const revenue = outboundTotal + inboundTotal + fuelSurchargeTotal;
  const profit = revenue - operatingCost;
  const margin = revenue > 0 ? (profit / revenue) * 100 : 0;
  // Solve margin = (revenue - cost) / revenue for the normal target. For an
  // unfamiliar lane, increase only that target profit rather than marking up
  // the operating-cost portion of the quote.
  const baseTargetRevenue = operatingCost / Math.max(1 - inputs.targetMargin / 100, 0.01);
  const baseTargetProfit = Math.max(baseTargetRevenue - operatingCost, 0);
  const outOfBoundsProfitUplift = Math.min(Math.max(inputs.outOfBoundsProfitUplift, 20), 60);
  const outOfBoundsPremium = inputs.outOfBounds
    ? baseTargetProfit * (outOfBoundsProfitUplift / 100)
    : 0;
  const targetRevenue = baseTargetRevenue + outOfBoundsPremium;
  const effectiveTargetMargin = targetRevenue > 0
    ? ((targetRevenue - operatingCost) / targetRevenue) * 100
    : 0;
  const targetInboundTotal = Math.max(targetRevenue - outboundTotal - fuelSurchargeTotal, 0);
  const targetInboundPerMile = inputs.loadedMiles > 0 ? targetInboundTotal / inputs.loadedMiles : 0;
  const targetAverageLoadedRate = totalLoadedMiles > 0 ? targetRevenue / totalLoadedMiles : 0;
  const actualAverageLoadedRate = totalLoadedMiles > 0 ? revenue / totalLoadedMiles : 0;
  return { totalLoadedMiles, totalMiles, operatingCost, outboundTotal, inboundTotal, outboundPerMile, inboundPerMile, fuelSurchargeTotal, fuelSurchargePerMile, revenue, profit, margin, baseTargetRevenue, baseTargetProfit, outOfBoundsPremium, targetRevenue, effectiveTargetMargin, targetInboundTotal, targetInboundPerMile, targetAverageLoadedRate, actualAverageLoadedRate };
}
