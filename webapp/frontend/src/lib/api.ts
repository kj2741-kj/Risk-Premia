const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface PlotlyFigure {
  data: unknown[];
  layout: Record<string, unknown>;
}

export interface Metrics {
  gross: number | null;
  net: number | null;
  ann: number | null;
  mdd: number | null;
  nact: number;
  flat_pct: number | null;
}

export interface SeriesJson {
  dates: string[];
  values: number[];
}

export interface MomentumResponse {
  year_range: { min: number; max: number };
  unit_label: string;
  active_pairs: [number, number][];
  feature_pair: [number, number];
  focus_pair: [number, number];
  metrics: Metrics | null;
  equity_curve_fig: PlotlyFigure;
  rolling_sharpe_fig: PlotlyFigure;
  signal_position_fig: PlotlyFigure;
  positions: Record<string, SeriesJson>;
}

export interface MomentumHeatmapResponse {
  fig: PlotlyFigure | null;
  plot_config: Record<string, unknown>;
  best: { fast: number; slow: number; sharpe: number } | null;
}

export interface MomentumParams {
  rollMethod?: "ltd" | "5td";
  rollN?: number;
  tcBps?: number;
  shiftN?: number;
  pairs?: [number, number][];
  metricsYearStart?: number;
  metricsYearEnd?: number;
  featurePair?: [number, number];
  equityYearStart?: number;
  equityYearEnd?: number;
  focusPair?: [number, number];
  rsBasis?: "net" | "gross";
}

function pairsToQuery(pairs?: [number, number][]) {
  return pairs?.map(([f, s]) => `${f}:${s}`).join(",");
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchMomentum(
  assetClass: string,
  product: string,
  p: MomentumParams = {},
): Promise<MomentumResponse> {
  const q = new URLSearchParams();
  if (p.rollMethod) q.set("roll_method", p.rollMethod);
  if (p.rollN) q.set("roll_n", String(p.rollN));
  if (p.tcBps !== undefined) q.set("tc_bps", String(p.tcBps));
  if (p.shiftN !== undefined) q.set("shift_n", String(p.shiftN));
  const pairsQ = pairsToQuery(p.pairs);
  if (pairsQ) q.set("pairs", pairsQ);
  if (p.metricsYearStart) q.set("metrics_year_start", String(p.metricsYearStart));
  if (p.metricsYearEnd) q.set("metrics_year_end", String(p.metricsYearEnd));
  if (p.featurePair) {
    q.set("feature_fast", String(p.featurePair[0]));
    q.set("feature_slow", String(p.featurePair[1]));
  }
  if (p.equityYearStart) q.set("equity_year_start", String(p.equityYearStart));
  if (p.equityYearEnd) q.set("equity_year_end", String(p.equityYearEnd));
  if (p.focusPair) {
    q.set("focus_fast", String(p.focusPair[0]));
    q.set("focus_slow", String(p.focusPair[1]));
  }
  if (p.rsBasis) q.set("rs_basis", p.rsBasis);

  return getJson(`${API_BASE}/api/${assetClass}/${product}/momentum?${q.toString()}`);
}

// ── Carry ────────────────────────────────────────────────────────────────

export interface CarryVariant {
  type: "V1" | "V2" | "V3";
  near?: string;
  far?: string;
  window?: number;
  horizon?: number;
}

export interface CarryResponse {
  year_range: { min: number; max: number };
  unit_label: string;
  contracts: string[];
  near_default: string;
  far_default: string;
  feature_label: string | null;
  focus_label: string | null;
  metrics: Metrics | null;
  equity_curve_fig: PlotlyFigure | null;
  rolling_sharpe_fig: PlotlyFigure | null;
  signal_position_fig: PlotlyFigure | null;
  positions: Record<string, SeriesJson>;
}

export interface CarryParams {
  tcBps?: number;
  shiftN?: number;
  variants?: CarryVariant[];
  metricsYearStart?: number;
  metricsYearEnd?: number;
  featureVariant?: CarryVariant;
  equityYearStart?: number;
  equityYearEnd?: number;
  focusVariant?: CarryVariant;
  rsBasis?: "net" | "gross";
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchCarry(assetClass: string, product: string, p: CarryParams = {}): Promise<CarryResponse> {
  return postJson(`${API_BASE}/api/${assetClass}/${product}/carry`, {
    tc_bps: p.tcBps, shift_n: p.shiftN, variants: p.variants,
    metrics_year_start: p.metricsYearStart, metrics_year_end: p.metricsYearEnd,
    feature_variant: p.featureVariant,
    equity_year_start: p.equityYearStart, equity_year_end: p.equityYearEnd,
    focus_variant: p.focusVariant, rs_basis: p.rsBasis,
  });
}

export interface CarryHeatmapResponse {
  fig: PlotlyFigure | null;
  best: { near: string; far: string; sharpe: number } | null;
}

export async function fetchCarryHeatmap(
  assetClass: string, product: string,
  p: { tcBps?: number; shiftN?: number; days?: number; mode?: "Momentum" | "Zscore";
       yearStart?: number; yearEnd?: number } = {},
): Promise<CarryHeatmapResponse> {
  const q = new URLSearchParams();
  if (p.tcBps !== undefined) q.set("tc_bps", String(p.tcBps));
  if (p.shiftN !== undefined) q.set("shift_n", String(p.shiftN));
  if (p.days !== undefined) q.set("days", String(p.days));
  if (p.mode) q.set("mode", p.mode);
  if (p.yearStart) q.set("year_start", String(p.yearStart));
  if (p.yearEnd) q.set("year_end", String(p.yearEnd));
  return getJson(`${API_BASE}/api/${assetClass}/${product}/carry/heatmap?${q.toString()}`);
}

// ── Value ────────────────────────────────────────────────────────────────

export interface ValueCombo {
  contract: string;
  lookback: string;
  threshold: number;
}

export interface ValueResponse {
  year_range: { min: number; max: number };
  unit_label: string;
  contracts: string[];
  lookback_options: string[];
  default_combo: ValueCombo;
  feature_label: string;
  focus_label: string;
  metrics: Metrics | null;
  equity_curve_fig: PlotlyFigure | null;
  rolling_sharpe_fig: PlotlyFigure | null;
  signal_position_fig: PlotlyFigure | null;
  positions: Record<string, SeriesJson>;
}

export interface ValueParams {
  tcBps?: number;
  shiftN?: number;
  combos?: ValueCombo[];
  metricsYearStart?: number;
  metricsYearEnd?: number;
  featureCombo?: ValueCombo;
  equityYearStart?: number;
  equityYearEnd?: number;
  focusCombo?: ValueCombo;
  rsBasis?: "net" | "gross";
}

export async function fetchValue(assetClass: string, product: string, p: ValueParams = {}): Promise<ValueResponse> {
  return postJson(`${API_BASE}/api/${assetClass}/${product}/value`, {
    tc_bps: p.tcBps, shift_n: p.shiftN, combos: p.combos,
    metrics_year_start: p.metricsYearStart, metrics_year_end: p.metricsYearEnd,
    feature_combo: p.featureCombo,
    equity_year_start: p.equityYearStart, equity_year_end: p.equityYearEnd,
    focus_combo: p.focusCombo, rs_basis: p.rsBasis,
  });
}

export interface ValueHeatmapResponse {
  fig: PlotlyFigure | null;
  best: { contract: string; lookback: string; sharpe: number } | null;
}

export async function fetchValueHeatmap(
  assetClass: string, product: string,
  p: { tcBps?: number; shiftN?: number; threshold?: number; yearStart?: number; yearEnd?: number } = {},
): Promise<ValueHeatmapResponse> {
  const q = new URLSearchParams();
  if (p.tcBps !== undefined) q.set("tc_bps", String(p.tcBps));
  if (p.shiftN !== undefined) q.set("shift_n", String(p.shiftN));
  if (p.threshold !== undefined) q.set("threshold", String(p.threshold));
  if (p.yearStart) q.set("year_start", String(p.yearStart));
  if (p.yearEnd) q.set("year_end", String(p.yearEnd));
  return getJson(`${API_BASE}/api/${assetClass}/${product}/value/heatmap?${q.toString()}`);
}

// ── Comparison ───────────────────────────────────────────────────────────

export interface ComparisonResponse {
  year_range: { min: number; max: number };
  unit_label: string;
  available_labels: string[];
  vol_fig: PlotlyFigure | null;
  equity_curve_fig: PlotlyFigure | null;
  rolling_sharpe_fig: PlotlyFigure | null;
}

export interface ComparisonParams {
  groups: Record<string, Record<string, SeriesJson>>;
  tcBps?: number;
  volWindowLabel?: string;
  chosen?: string[];
  equityYearStart?: number;
  equityYearEnd?: number;
  rsBasis?: "net" | "gross";
  showVolOverlay?: boolean;
}

export async function fetchComparison(
  assetClass: string, product: string, p: ComparisonParams,
): Promise<ComparisonResponse> {
  return postJson(`${API_BASE}/api/${assetClass}/${product}/comparison`, {
    groups: p.groups, tc_bps: p.tcBps, vol_window_label: p.volWindowLabel, chosen: p.chosen,
    equity_year_start: p.equityYearStart, equity_year_end: p.equityYearEnd,
    rs_basis: p.rsBasis, show_vol_overlay: p.showVolOverlay,
  });
}

export async function fetchMomentumHeatmap(
  assetClass: string,
  product: string,
  p: { rollMethod?: "ltd" | "5td"; rollN?: number; tcBps?: number; shiftN?: number;
       yearStart?: number; yearEnd?: number; maxWindow?: number } = {},
): Promise<MomentumHeatmapResponse> {
  const q = new URLSearchParams();
  if (p.rollMethod) q.set("roll_method", p.rollMethod);
  if (p.rollN) q.set("roll_n", String(p.rollN));
  if (p.tcBps !== undefined) q.set("tc_bps", String(p.tcBps));
  if (p.shiftN !== undefined) q.set("shift_n", String(p.shiftN));
  if (p.yearStart) q.set("year_start", String(p.yearStart));
  if (p.yearEnd) q.set("year_end", String(p.yearEnd));
  if (p.maxWindow) q.set("max_window", String(p.maxWindow));

  return getJson(`${API_BASE}/api/${assetClass}/${product}/momentum/heatmap?${q.toString()}`);
}

// ── Portfolio (asset-class level, not per-product) ─────────────────────────

export interface PortfolioLeg {
  fast?: number;
  slow?: number;
  type?: "V1 Level" | "V2 Z-score" | "V3 Carry-Momentum";
  near?: string;
  far?: string;
  zwindow?: number;
  horizon?: number;
  contract?: string;
  lookback?: number;
  threshold?: number;
}

export interface PortfolioSleeve {
  family: "Momentum" | "Carry" | "CarryMom" | "Value";
  legs: PortfolioLeg[];
  shift_n: number;
  combine_method: string;
}

export interface ReferenceStrategy {
  id: string;
  label: string;
  family: "Momentum" | "Carry" | "CarryMom" | "Value";
  shift_n: number;
  legs: PortfolioLeg[];
  legs_desc: string[];
}

export interface CustomPortfolioDef {
  label: string;
  sleeves: PortfolioSleeve[];
}

export interface PortfolioMetrics {
  gross: number | null;
  net: number | null;
  ann: number | null;
  vol: number | null;
  mdd: number | null;
}

export interface PortfolioResultsResponse {
  common_start: string;
  common_end: string;
  min_year: number;
  max_year: number;
  metric_labels: string[];
  metrics: PortfolioMetrics | null;
  equity_fig: PlotlyFigure | null;
  table_rows: { strategy: string; return: number | null; vol: number | null; ir: number | null }[];
}

export async function fetchPortfolioReference(assetClass: string): Promise<{ strategies: ReferenceStrategy[] }> {
  return getJson(`${API_BASE}/api/${assetClass}/portfolio/reference`);
}

export interface PortfolioResultsParams {
  tcBps?: number;
  combineMethod?: string;
  volWindow?: number;
  returnTilt?: number;
  customPortfolios?: CustomPortfolioDef[];
  yrStart?: number;
  yrEnd?: number;
  metricStrategy?: string;
  shown?: string[];
}

export async function fetchPortfolioResults(
  assetClass: string, p: PortfolioResultsParams = {},
): Promise<PortfolioResultsResponse> {
  return postJson(`${API_BASE}/api/${assetClass}/portfolio/results`, {
    tc_bps: p.tcBps, combine_method: p.combineMethod, vol_window: p.volWindow, return_tilt: p.returnTilt,
    custom_portfolios: p.customPortfolios,
    yr_start: p.yrStart, yr_end: p.yrEnd, metric_strategy: p.metricStrategy, shown: p.shown,
  });
}

// ── Fundamental Analysis (GHR inventory-vs-basis spline) ───────────────────

export interface GhrSlopes {
  slope_at_1: number | null;
  t_at_1: number | null;
  "slope_at_0.75": number | null;
  "t_at_0.75": number | null;
  diff: number | null;
  t_diff: number | null;
}

export interface GhrResponse {
  fig: PlotlyFigure;
  slopes: GhrSlopes;
  r2: number | null;
  period_start: string;
  period_end: string;
  n_obs: number;
}

export async function fetchFundamentalBounds(
  commodity: string, basisSource = "f1f2",
): Promise<{ data_min: string; data_max: string }> {
  return getJson(`${API_BASE}/api/fundamental/${commodity}/bounds?basis_source=${basisSource}`);
}

export interface FundamentalParams {
  basisSource?: "f1f2" | "cash3m";
  start?: string;
  end?: string;
  trailingWeeks?: number;
  nwBandwidth?: number;
  fixedScale?: boolean;
}

export async function fetchFundamental(commodity: string, p: FundamentalParams = {}): Promise<GhrResponse> {
  const q = new URLSearchParams();
  if (p.basisSource) q.set("basis_source", p.basisSource);
  if (p.start) q.set("start", p.start);
  if (p.end) q.set("end", p.end);
  if (p.trailingWeeks) q.set("trailing_weeks", String(p.trailingWeeks));
  if (p.nwBandwidth) q.set("nw_bandwidth", String(p.nwBandwidth));
  if (p.fixedScale !== undefined) q.set("fixed_scale", String(p.fixedScale));
  return getJson(`${API_BASE}/api/fundamental/${commodity}?${q.toString()}`);
}
