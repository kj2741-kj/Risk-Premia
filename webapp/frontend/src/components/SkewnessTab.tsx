import { useEffect, useMemo, useState } from "react";
import { useBasis } from "../lib/basis";
import { useQuery } from "@tanstack/react-query";
import { fetchSkewness, type SeriesJson } from "../lib/api";
import { useDebouncedValue } from "../lib/useDebouncedValue";
import PlotlyChart from "./PlotlyChart";
import MetricCard from "./MetricCard";
import { fmtSigned, fmtSignedComma } from "../lib/fmt";

const TC_OPTIONS = [0, 5, 10, 20];
const TIMING_OPTIONS: { label: string; shiftN: number }[] = [
  { label: "Same Day (Shift-0)", shiftN: 0 },
  { label: "Lag-1 (Shift-1)", shiftN: 1 },
  { label: "Lag-2 (Shift-2)", shiftN: 2 },
];

interface SkewnessTabProps {
  assetClass: string;
  product: string;
  onPositionsChange?: (positions: Record<string, SeriesJson>) => void;
}

export default function SkewnessTab({ assetClass, product, onPositionsChange }: SkewnessTabProps) {
  const { geometric } = useBasis();
  const [tcBps, setTcBps] = useState(5);
  const [shiftN, setShiftN] = useState(1);
  const [windows, setWindows] = useState<number[] | undefined>(undefined);
  const [customWindow, setCustomWindow] = useState(189);
  const [metricsYearStart, setMetricsYearStart] = useState<number | undefined>(undefined);
  const [metricsYearEnd, setMetricsYearEnd] = useState<number | undefined>(undefined);
  const [featureWindow, setFeatureWindow] = useState<number | undefined>(undefined);
  const [focusWindow, setFocusWindow] = useState<number | undefined>(undefined);   // undefined = follow the featured window
  const [equityYearStart, setEquityYearStart] = useState<number | undefined>(undefined);
  const [equityYearEnd, setEquityYearEnd] = useState<number | undefined>(undefined);
  const [rsBasis, setRsBasis] = useState<"net" | "gross">("net");

  const params = useMemo(
    () => ({ tcBps, shiftN, windows, metricsYearStart, metricsYearEnd, featureWindow, focusWindow, equityYearStart, equityYearEnd, rsBasis }),
    [tcBps, shiftN, windows, metricsYearStart, metricsYearEnd, featureWindow, focusWindow, equityYearStart, equityYearEnd, rsBasis],
  );
  const debounced = useDebouncedValue(params, 400);
  const { data, isLoading, error } = useQuery({
    queryKey: ["skewness", assetClass, product, debounced, geometric],
    queryFn: () => fetchSkewness(assetClass, product, debounced),
    placeholderData: (prev) => prev,
  });

  useEffect(() => {
    if (data?.positions) onPositionsChange?.(data.positions);
    if (data && windows === undefined) setWindows(data.windows);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  const active = windows ?? data?.windows ?? [];
  const yr = data?.year_range;

  return (
    <div>
      <div className="section-header">Skewness: {product}</div>
      <p className="tab-caption">
        signal(t) = sign[ &minus;skewness of the daily log returns of the roll-adjusted (ratio-stitched) continuous series over the
        past N observations ]. Long when skewness is negative, short when positive (Fernandez-Perez, Fuertes and Miffre 2021,
        Table 1, time-series form: one position per product, not a cross-sectional sort). N = 252 is the research window.
      </p>

      <div className="control-row">
        <label>Transaction Cost
          <select value={tcBps} onChange={(e) => setTcBps(Number(e.target.value))}>
            {TC_OPTIONS.map((b) => <option key={b} value={b}>{b === 0 ? "0 bps (Gross)" : `${b} bps`}</option>)}
          </select>
        </label>
        <label>Execution Timing
          <select value={shiftN} onChange={(e) => setShiftN(Number(e.target.value))}>
            {TIMING_OPTIONS.map((t) => <option key={t.shiftN} value={t.shiftN}>{t.label}</option>)}
          </select>
        </label>
      </div>

      <div className="section-header">Strategies to Compare</div>
      <div className="control-row">
        <label>Custom Window (days)
          <input type="number" min={20} max={1000} value={customWindow} onChange={(e) => setCustomWindow(Number(e.target.value))} />
        </label>
        <button onClick={() => setWindows([...new Set([...active, customWindow])].sort((a, b) => a - b))}>Add Custom Window</button>
        <button onClick={() => { setWindows(data?.default_windows); setFeatureWindow(undefined); }}>Reset to Defaults</button>
      </div>
      <div className="control-row">
        {active.map((w) => (
          <label key={w}>
            <input type="checkbox" checked onChange={() => setWindows(active.filter((x) => x !== w))} /> Skew({w})
          </label>
        ))}
      </div>

      {yr && (
        <div className="control-row">
          <label>Metrics year start
            <input type="number" min={yr.min} max={yr.max} value={metricsYearStart ?? yr.min} onChange={(e) => setMetricsYearStart(Number(e.target.value))} />
          </label>
          <label>Metrics year end
            <input type="number" min={yr.min} max={yr.max} value={metricsYearEnd ?? yr.max} onChange={(e) => setMetricsYearEnd(Number(e.target.value))} />
          </label>
          <label>Strategy to feature
            <select value={data?.feature_window ?? ""} onChange={(e) => { setFeatureWindow(Number(e.target.value)); setFocusWindow(undefined); }}>
              {active.map((w) => <option key={w} value={w}>Skew({w})</option>)}
            </select>
          </label>
        </div>
      )}

      <div className="section-header">Performance Metrics</div>
      {isLoading && !data && <p>Loading…</p>}
      {error && <p className="error">{(error as Error).message}</p>}
      {data?.metrics && (
        <div className="metric-row">
          <MetricCard label="Gross Sharpe" value={data.metrics.gross} format={(v) => fmtSigned(v)} />
          <MetricCard label="Net Sharpe" value={data.metrics.net} format={(v) => fmtSigned(v)} />
          <MetricCard label={geometric ? "Ann Return (Net)" : "Ann PnL (Net)"} value={data.metrics.ann} format={(v) => fmtSignedComma(v)} unit={geometric ? " %" : ` ${data.unit_label}`} />
          <MetricCard label="Max DD (Net)" value={data.metrics.mdd} format={(v) => fmtSignedComma(v)} unit={geometric ? " %" : ` ${data.unit_label}`} />
          <MetricCard label="% Flat" value={data.metrics.flat_pct} format={(v) => v.toFixed(0)} unit="%" />
        </div>
      )}

      {data?.metrics && (
        <>
          <div className="metric-row">
            <MetricCard label="Gross IR (all days)" value={data.metrics.ir_gross ?? null} format={(v) => fmtSigned(v)} />
            <MetricCard label="Net IR (all days)" value={data.metrics.ir_net ?? null} format={(v) => fmtSigned(v)} />
            <MetricCard label="Ann Vol" value={data.metrics.vol ?? null} format={(v) => fmtSignedComma(v).replace("+", "")} unit={geometric ? " %" : ` ${data.unit_label}`} />
          </div>
          <p className="caption">
            Sharpe above = active days only (days in a position). IR = annual return / annual vol over every day of the window, flat days as zero:
            the figure the Final Research Dashboard shows per period. Signals are built on the full history and cut to the year range, as in the dashboard.
          </p>
        </>
      )}

      {data && (
        <>
          <div className="section-header">Gross Sharpe by Look-back Window</div>
          <p className="caption">
            Every window from 40 to 760 trading days in steps of 20, over the year range above. Signals use full history, so every window is
            warmed up at the start of the range.
          </p>
          {data.sweep_fig && <PlotlyChart fig={data.sweep_fig} height={320} />}
          {data.sweep_best && (
            <p className="caption">
              Best in range {metricsYearStart ?? yr?.min}-{metricsYearEnd ?? yr?.max}: {data.sweep_best.window} days, gross Sharpe{" "}
              {fmtSigned(data.sweep_best.sharpe)}.
            </p>
          )}

          <div className="section-header">Rolling Skewness ({data.feature_window}-day) of Daily Log Returns</div>
          <p className="caption">The signal is long where this line is below zero and short where it is above zero.</p>
          <PlotlyChart fig={data.rolling_skew_fig} height={300} />

          <div className="section-header">{geometric ? "Cumulative Return (Equity Curve, %)" : `Cumulative PnL (Equity Curve, ${data?.unit_label ?? ""})`}: Net of TC</div>
          <div className="control-row">
            <label>Equity year start <input type="number" value={equityYearStart ?? yr?.min ?? ""} onChange={(e) => setEquityYearStart(Number(e.target.value))} /></label>
            <label>Equity year end <input type="number" value={equityYearEnd ?? yr?.max ?? ""} onChange={(e) => setEquityYearEnd(Number(e.target.value))} /></label>
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
              <select value={data.focus_window} onChange={(e) => setFocusWindow(Number(e.target.value))}>
                {active.map((w) => <option key={w} value={w}>Skew({w})</option>)}
              </select>
            </label>
          </div>
          <PlotlyChart fig={data.signal_position_fig} height={500} />
        </>
      )}
    </div>
  );
}
