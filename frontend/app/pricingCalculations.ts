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
  targetRevenue: number;
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
  // Solve margin = (revenue - cost) / revenue for target revenue.
  const targetRevenue = operatingCost / Math.max(1 - inputs.targetMargin / 100, 0.01);
  const targetInboundTotal = Math.max(targetRevenue - outboundTotal - fuelSurchargeTotal, 0);
  const targetInboundPerMile = inputs.loadedMiles > 0 ? targetInboundTotal / inputs.loadedMiles : 0;
  const targetAverageLoadedRate = totalLoadedMiles > 0 ? targetRevenue / totalLoadedMiles : 0;
  const actualAverageLoadedRate = totalLoadedMiles > 0 ? revenue / totalLoadedMiles : 0;
  return { totalLoadedMiles, totalMiles, operatingCost, outboundTotal, inboundTotal, outboundPerMile, inboundPerMile, fuelSurchargeTotal, fuelSurchargePerMile, revenue, profit, margin, targetRevenue, targetInboundTotal, targetInboundPerMile, targetAverageLoadedRate, actualAverageLoadedRate };
}
