import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchMomentum, fetchMomentumHeatmap, type SeriesJson } from "../lib/api";
import { useDebouncedValue } from "../lib/useDebouncedValue";
import PlotlyChart from "./PlotlyChart";
import MetricCard from "./MetricCard";

const TC_OPTIONS = [0, 5, 10, 20];
const TIMING_OPTIONS: { label: string; shiftN: number }[] = [
  { label: "Same Day (Shift-0)", shiftN: 0 },
  { label: "Lag-1 (Shift-1)", shiftN: 1 },
  { label: "Lag-2 (Shift-2)", shiftN: 2 },
];
const DEFAULT_PAIRS: [number, number][] = [[1, 20], [5, 60], [20, 250]];

function pairLabel([f, s]: [number, number]) {
  return `MA(${f},${s})`;
}

interface MomentumTabProps {
  assetClass: string;
  product: string;
  onPositionsChange?: (positions: Record<string, SeriesJson>) => void;
}

export default function MomentumTab({ assetClass, product, onPositionsChange }: MomentumTabProps) {
  const [tcBps, setTcBps] = useState(5);
  const [shiftN, setShiftN] = useState(1);
  const [activePairs, setActivePairs] = useState<[number, number][]>(DEFAULT_PAIRS);
  const [customFast, setCustomFast] = useState(10);
  const [customSlow, setCustomSlow] = useState(50);

  const [metricsYearStart, setMetricsYearStart] = useState<number | undefined>(undefined);
  const [metricsYearEnd, setMetricsYearEnd] = useState<number | undefined>(undefined);
  const [featurePair, setFeaturePair] = useState<[number, number]>([1, 20]);

  const [equityYearStart, setEquityYearStart] = useState<number | undefined>(undefined);
  const [equityYearEnd, setEquityYearEnd] = useState<number | undefined>(undefined);
  const [focusPair, setFocusPair] = useState<[number, number]>([1, 20]);
  const [rsBasis, setRsBasis] = useState<"net" | "gross">("net");

  const params = useMemo(
    () => ({
      tcBps, shiftN, pairs: activePairs,
      metricsYearStart, metricsYearEnd, featurePair,
      equityYearStart, equityYearEnd, focusPair, rsBasis,
    }),
    [tcBps, shiftN, activePairs, metricsYearStart, metricsYearEnd, featurePair,
     equityYearStart, equityYearEnd, focusPair, rsBasis],
  );
  const debouncedParams = useDebouncedValue(params, 400);

  const { data, isLoading, error } = useQuery({
    queryKey: ["momentum", assetClass, product, debouncedParams],
    queryFn: () => fetchMomentum(assetClass, product, debouncedParams),
    placeholderData: (prev) => prev,
  });

  useEffect(() => {
    if (data?.positions) onPositionsChange?.(data.positions);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  // Heatmap: explicit-refresh only (not tied to the debounced params above) --
  // a 250x250 grid scan is expensive enough that it must never fire on every
  // slider tick of the OTHER controls on this tab.
  const [heatmapMaxWindow, setHeatmapMaxWindow] = useState(250);
  const [heatmapYearStart, setHeatmapYearStart] = useState<number | undefined>(undefined);
  const [heatmapYearEnd, setHeatmapYearEnd] = useState<number | undefined>(undefined);
  const [heatmapCommitted, setHeatmapCommitted] = useState({
    tcBps, shiftN, maxWindow: heatmapMaxWindow,
    yearStart: heatmapYearStart, yearEnd: heatmapYearEnd,
  });

  const heatmapQuery = useQuery({
    queryKey: ["momentum-heatmap", assetClass, product, heatmapCommitted],
    queryFn: () => fetchMomentumHeatmap(assetClass, product, heatmapCommitted),
  });

  function addCustomPair() {
    if (customSlow > customFast && !activePairs.some(([f, s]) => f === customFast && s === customSlow)) {
      setActivePairs([...activePairs, [customFast, customSlow]]);
    }
  }
  function resetPairs() {
    setActivePairs(DEFAULT_PAIRS);
  }
  function removePair(pair: [number, number]) {
    setActivePairs(activePairs.filter(([f, s]) => !(f === pair[0] && s === pair[1])));
  }

  const yr = data?.year_range;

  return (
    <div className="tab-panel">
      <p className="tab-caption">
        Moving-average crossover: signal(t) = sign[MA(F1_raw, fast) − MA(F1_raw, slow)].
      </p>

      <div className="control-row">
        <label>
          Transaction Cost
          <select value={tcBps} onChange={(e) => setTcBps(Number(e.target.value))}>
            {TC_OPTIONS.map((bps) => (
              <option key={bps} value={bps}>{bps === 0 ? "0 bps (Gross)" : `${bps} bps`}</option>
            ))}
          </select>
        </label>
        <label>
          Execution Timing
          <select value={shiftN} onChange={(e) => setShiftN(Number(e.target.value))}>
            {TIMING_OPTIONS.map((t) => (
              <option key={t.shiftN} value={t.shiftN}>{t.label}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="section-header">Strategies to Compare</div>
      <div className="control-row">
        <label>Custom Fast <input type="number" min={1} max={500} value={customFast}
          onChange={(e) => setCustomFast(Number(e.target.value))} /></label>
        <label>Custom Slow <input type="number" min={2} max={1000} value={customSlow}
          onChange={(e) => setCustomSlow(Number(e.target.value))} /></label>
        <button onClick={addCustomPair}>Add Custom MA</button>
        <button onClick={resetPairs}>Reset to Defaults</button>
      </div>
      <div className="pill-row">
        {activePairs.map((p) => (
          <span className="pill" key={pairLabel(p)}>
            {pairLabel(p)}
            <button className="pill-remove" onClick={() => removePair(p)}>×</button>
          </span>
        ))}
      </div>

      {yr && (
        <div className="control-row">
          <label>Metrics year start
            <input type="number" min={yr.min} max={yr.max} value={metricsYearStart ?? yr.min}
              onChange={(e) => setMetricsYearStart(Number(e.target.value))} />
          </label>
          <label>Metrics year end
            <input type="number" min={yr.min} max={yr.max} value={metricsYearEnd ?? yr.max}
              onChange={(e) => setMetricsYearEnd(Number(e.target.value))} />
          </label>
          <label>Strategy to feature
            <select value={pairLabel(featurePair)}
              onChange={(e) => {
                const p = activePairs.find((x) => pairLabel(x) === e.target.value);
                if (p) setFeaturePair(p);
              }}>
              {activePairs.map((p) => <option key={pairLabel(p)}>{pairLabel(p)}</option>)}
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

      <div className="section-header">Sharpe Heatmap — Fast × Slow MA Crossover</div>
      <div className="control-row">
        <label>Max window <input type="number" min={10} max={500} value={heatmapMaxWindow}
          onChange={(e) => setHeatmapMaxWindow(Number(e.target.value))} /></label>
        <label>Year start <input type="number" value={heatmapYearStart ?? yr?.min ?? ""}
          onChange={(e) => setHeatmapYearStart(Number(e.target.value))} /></label>
        <label>Year end <input type="number" value={heatmapYearEnd ?? yr?.max ?? ""}
          onChange={(e) => setHeatmapYearEnd(Number(e.target.value))} /></label>
        <button onClick={() => setHeatmapCommitted({
          tcBps, shiftN, maxWindow: heatmapMaxWindow, yearStart: heatmapYearStart, yearEnd: heatmapYearEnd,
        })}>
          Recompute Heatmap
        </button>
      </div>
      {heatmapQuery.isFetching && <p>Computing heatmap…</p>}
      {heatmapQuery.data && (
        <>
          <PlotlyChart fig={heatmapQuery.data.fig} plotConfig={heatmapQuery.data.plot_config} height={560} />
          {heatmapQuery.data.best && (
            <p className="caption">
              Best: MA({heatmapQuery.data.best.fast},{heatmapQuery.data.best.slow}) gross Sharpe{" "}
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
            <label>
              <input type="radio" checked={rsBasis === "gross"} onChange={() => setRsBasis("gross")} /> Gross
            </label>
            <label>
              <input type="radio" checked={rsBasis === "net"} onChange={() => setRsBasis("net")} /> Net of TC
            </label>
          </div>
          <PlotlyChart fig={data.rolling_sharpe_fig} height={320} />

          <div className="section-header">Signal & Position History</div>
          <div className="control-row">
            <label>Strategy to display
              <select value={pairLabel(focusPair)}
                onChange={(e) => {
                  const p = activePairs.find((x) => pairLabel(x) === e.target.value);
                  if (p) setFocusPair(p);
                }}>
                {activePairs.map((p) => <option key={pairLabel(p)}>{pairLabel(p)}</option>)}
              </select>
            </label>
          </div>
          <PlotlyChart fig={data.signal_position_fig} height={500} />
        </>
      )}
    </div>
  );
}
