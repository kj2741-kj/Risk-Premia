import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchValue, fetchValueHeatmap, type SeriesJson, type ValueCombo } from "../lib/api";
import { useDebouncedValue } from "../lib/useDebouncedValue";
import PlotlyChart from "./PlotlyChart";
import MetricCard from "./MetricCard";

const TC_OPTIONS = [0, 5, 10, 20];
const TIMING_OPTIONS = [
  { label: "Same Day (Shift-0)", shiftN: 0 },
  { label: "Lag-1 (Shift-1)", shiftN: 1 },
  { label: "Lag-2 (Shift-2)", shiftN: 2 },
];
const THRESHOLDS = [0.05, 0.10, 0.15, 0.20];

function comboLabel(c: ValueCombo): string {
  return `${c.contract} ${c.lookback} ±${(c.threshold * 100).toFixed(0)}%`;
}

interface ValueTabProps {
  assetClass: string;
  product: string;
  onPositionsChange?: (positions: Record<string, SeriesJson>) => void;
}

export default function ValueTab({ assetClass, product, onPositionsChange }: ValueTabProps) {
  const [tcBps, setTcBps] = useState(5);
  const [shiftN, setShiftN] = useState(2);
  // Starts empty rather than hardcoded F8/5yr/10% -- the correct default
  // combo is asset-specific (e.g. NGL uses F12/10yr/10%), seeded from the
  // first server response instead of guessed client-side.
  const [combos, setCombos] = useState<ValueCombo[]>([]);

  const [addContract, setAddContract] = useState("F8");
  const [addLookback, setAddLookback] = useState("5yr");
  const [addThreshold, setAddThreshold] = useState(0.10);

  const [metricsYearStart, setMetricsYearStart] = useState<number>();
  const [metricsYearEnd, setMetricsYearEnd] = useState<number>();
  const [featureLabel, setFeatureLabel] = useState<string>("");
  const [equityYearStart, setEquityYearStart] = useState<number>();
  const [equityYearEnd, setEquityYearEnd] = useState<number>();
  const [focusLabel, setFocusLabel] = useState<string>("");
  const [rsBasis, setRsBasis] = useState<"net" | "gross">("net");
  const [seeded, setSeeded] = useState(false);

  useEffect(() => {
    setSeeded(false);
    setCombos([]);
    setFeatureLabel("");
    setFocusLabel("");
  }, [assetClass, product]);

  const params = useMemo(
    () => ({
      tcBps, shiftN, combos,
      featureCombo: combos.find((c) => comboLabel(c) === featureLabel),
      focusCombo: combos.find((c) => comboLabel(c) === focusLabel),
      metricsYearStart, metricsYearEnd, equityYearStart, equityYearEnd, rsBasis,
    }),
    [tcBps, shiftN, combos, featureLabel, focusLabel, metricsYearStart, metricsYearEnd,
     equityYearStart, equityYearEnd, rsBasis],
  );
  const debouncedParams = useDebouncedValue(params, 400);

  const { data, isLoading, error } = useQuery({
    queryKey: ["value", assetClass, product, debouncedParams],
    queryFn: () => fetchValue(assetClass, product, debouncedParams),
    placeholderData: (prev) => prev,
  });

  useEffect(() => {
    if (data?.positions) onPositionsChange?.(data.positions);
    if (data && !seeded) {
      setCombos([data.default_combo]);
      setFeatureLabel(comboLabel(data.default_combo));
      setFocusLabel(comboLabel(data.default_combo));
      setAddContract(data.default_combo.contract);
      setAddLookback(data.default_combo.lookback);
      setAddThreshold(data.default_combo.threshold);
      setSeeded(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  const [hmThreshold, setHmThreshold] = useState(0.10);
  const [hmYearStart, setHmYearStart] = useState<number>();
  const [hmYearEnd, setHmYearEnd] = useState<number>();
  const [hmCommitted, setHmCommitted] = useState({ tcBps, shiftN, threshold: hmThreshold, yearStart: hmYearStart, yearEnd: hmYearEnd });
  const heatmapQuery = useQuery({
    queryKey: ["value-heatmap", assetClass, product, hmCommitted],
    queryFn: () => fetchValueHeatmap(assetClass, product, hmCommitted),
  });

  function addCombo() {
    const c = { contract: addContract, lookback: addLookback, threshold: addThreshold };
    if (!combos.some((x) => comboLabel(x) === comboLabel(c))) setCombos([...combos, c]);
  }
  function removeCombo(c: ValueCombo) {
    setCombos(combos.filter((x) => comboLabel(x) !== comboLabel(c)));
  }

  const yr = data?.year_range;
  const contracts = data?.contracts ?? [];
  const lookbackOptions = data?.lookback_options ?? ["1mo", "1qtr", "6mo", "1yr", "3yr", "5yr", "7yr", "10yr"];

  return (
    <div className="tab-panel">
      <p className="tab-caption">Moving-average reversion: deviation = (Fk − MA_N)/MA_N.</p>

      <div className="control-row">
        <label>Transaction Cost
          <select value={tcBps} onChange={(e) => setTcBps(Number(e.target.value))}>
            {TC_OPTIONS.map((bps) => <option key={bps} value={bps}>{bps === 0 ? "0 bps (Gross)" : `${bps} bps`}</option>)}
          </select>
        </label>
        <label>Execution Timing
          <select value={shiftN} onChange={(e) => setShiftN(Number(e.target.value))}>
            {TIMING_OPTIONS.map((t) => <option key={t.shiftN} value={t.shiftN}>{t.label}</option>)}
          </select>
        </label>
      </div>

      <div className="section-header">Add a Value Variant</div>
      <div className="control-row">
        <label>Contract
          <select value={addContract} onChange={(e) => setAddContract(e.target.value)}>
            {contracts.map((c) => <option key={c}>{c}</option>)}
          </select>
        </label>
        <label>Lookback
          <select value={addLookback} onChange={(e) => setAddLookback(e.target.value)}>
            {lookbackOptions.map((l) => <option key={l}>{l}</option>)}
          </select>
        </label>
        <label>Threshold
          <select value={addThreshold} onChange={(e) => setAddThreshold(Number(e.target.value))}>
            {THRESHOLDS.map((t) => <option key={t} value={t}>±{(t * 100).toFixed(0)}%</option>)}
          </select>
        </label>
        <button onClick={addCombo}>Add</button>
      </div>
      <div className="pill-row">
        {combos.map((c) => (
          <span className="pill" key={comboLabel(c)}>
            {comboLabel(c)}
            <button className="pill-remove" onClick={() => removeCombo(c)}>×</button>
          </span>
        ))}
      </div>

      {yr && (
        <div className="control-row">
          <label>Metrics year start <input type="number" value={metricsYearStart ?? yr.min}
            onChange={(e) => setMetricsYearStart(Number(e.target.value))} /></label>
          <label>Metrics year end <input type="number" value={metricsYearEnd ?? yr.max}
            onChange={(e) => setMetricsYearEnd(Number(e.target.value))} /></label>
          <label>Strategy to feature
            <select value={featureLabel} onChange={(e) => setFeatureLabel(e.target.value)}>
              {combos.map((c) => <option key={comboLabel(c)}>{comboLabel(c)}</option>)}
            </select>
          </label>
        </div>
      )}

      <div className="section-header">Performance Metrics</div>
      {isLoading && !data && <p>Loading…</p>}
      {error && <p className="error">{(error as Error).message}</p>}
      {data?.metrics && (
        <div className="metric-row">
          <MetricCard label="Gross Sharpe" value={data.metrics.gross} format={(v) => v.toFixed(2)} />
          <MetricCard label="Net Sharpe" value={data.metrics.net} format={(v) => v.toFixed(2)} />
          <MetricCard label="Ann PnL (Net)" value={data.metrics.ann} format={(v) => v.toLocaleString(undefined, { maximumFractionDigits: 2 })} unit={` ${data.unit_label}`} />
          <MetricCard label="Max DD (Net)" value={data.metrics.mdd} format={(v) => v.toLocaleString(undefined, { maximumFractionDigits: 2 })} unit={` ${data.unit_label}`} />
          <MetricCard label="% Flat" value={data.metrics.flat_pct} format={(v) => v.toFixed(0)} unit="%" />
        </div>
      )}

      <div className="section-header">Sharpe Heatmap — Contract × Lookback</div>
      <div className="control-row">
        <label>Threshold
          <select value={hmThreshold} onChange={(e) => setHmThreshold(Number(e.target.value))}>
            {THRESHOLDS.map((t) => <option key={t} value={t}>±{(t * 100).toFixed(0)}%</option>)}
          </select>
        </label>
        <label>Year start <input type="number" value={hmYearStart ?? yr?.min ?? ""}
          onChange={(e) => setHmYearStart(Number(e.target.value))} /></label>
        <label>Year end <input type="number" value={hmYearEnd ?? yr?.max ?? ""}
          onChange={(e) => setHmYearEnd(Number(e.target.value))} /></label>
        <button onClick={() => setHmCommitted({ tcBps, shiftN, threshold: hmThreshold, yearStart: hmYearStart, yearEnd: hmYearEnd })}>
          Recompute Heatmap
        </button>
      </div>
      {heatmapQuery.isFetching && <p>Computing heatmap…</p>}
      {heatmapQuery.data && (
        <>
          <PlotlyChart fig={heatmapQuery.data.fig} height={560} />
          {heatmapQuery.data.best && (
            <p className="caption">
              Best: {heatmapQuery.data.best.contract} / {heatmapQuery.data.best.lookback} gross Sharpe{" "}
              {heatmapQuery.data.best.sharpe.toFixed(2)}
            </p>
          )}
        </>
      )}

      {data && (
        <>
          <div className="section-header">Cumulative PnL (Equity Curve, {data.unit_label}) — Net of TC</div>
          <div className="control-row">
            <label>Equity year start <input type="number" value={equityYearStart ?? yr?.min ?? ""}
              onChange={(e) => setEquityYearStart(Number(e.target.value))} /></label>
            <label>Equity year end <input type="number" value={equityYearEnd ?? yr?.max ?? ""}
              onChange={(e) => setEquityYearEnd(Number(e.target.value))} /></label>
          </div>
          <PlotlyChart fig={data.equity_curve_fig} height={380} />

          <div className="section-header">Rolling Sharpe (252-Day)</div>
          <div className="control-row">
            <label><input type="radio" checked={rsBasis === "gross"} onChange={() => setRsBasis("gross")} /> Gross</label>
            <label><input type="radio" checked={rsBasis === "net"} onChange={() => setRsBasis("net")} /> Net of TC</label>
          </div>
          <PlotlyChart fig={data.rolling_sharpe_fig} height={320} />

          <div className="section-header">Signal & Position History</div>
          <div className="control-row">
            <label>Strategy to display
              <select value={focusLabel} onChange={(e) => setFocusLabel(e.target.value)}>
                {combos.map((c) => <option key={comboLabel(c)}>{comboLabel(c)}</option>)}
              </select>
            </label>
          </div>
          <PlotlyChart fig={data.signal_position_fig} height={500} />
        </>
      )}
    </div>
  );
}
