import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchCarry, fetchCarryHeatmap, type CarryVariant, type SeriesJson } from "../lib/api";
import { useDebouncedValue } from "../lib/useDebouncedValue";
import PlotlyChart from "./PlotlyChart";
import MetricCard from "./MetricCard";

const TC_OPTIONS = [0, 5, 10, 20];
const TIMING_OPTIONS = [
  { label: "Same Day (Shift-0)", shiftN: 0 },
  { label: "Lag-1 (Shift-1)", shiftN: 1 },
  { label: "Lag-2 (Shift-2)", shiftN: 2 },
];

function variantLabel(v: CarryVariant): string {
  if (v.type === "V1") return `V1 (${v.near}-${v.far})`;
  if (v.type === "V2") return `V2 (win=${v.window})`;
  return `V3 (N=${v.horizon})`;
}

interface CarryTabProps {
  assetClass: string;
  product: string;
  onPositionsChange?: (positions: Record<string, SeriesJson>) => void;
}

export default function CarryTab({ assetClass, product, onPositionsChange }: CarryTabProps) {
  const [tcBps, setTcBps] = useState(5);
  const [shiftN, setShiftN] = useState(1);
  // Starts empty rather than hardcoded F1-F2 -- the correct default V1 pair
  // is asset-specific (e.g. NGL uses F4-F15), so we let the first server
  // response (which already resolves this via config_registry) tell us
  // what to seed, instead of guessing and always overriding the server.
  const [variants, setVariants] = useState<CarryVariant[]>([]);

  const [addType, setAddType] = useState<"V1" | "V2" | "V3">("V1");
  const [addNear, setAddNear] = useState("F1");
  const [addFar, setAddFar] = useState("F2");
  const [addWindow, setAddWindow] = useState(252);
  const [addHorizon, setAddHorizon] = useState(20);

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
    setVariants([]);
    setFeatureLabel("");
    setFocusLabel("");
  }, [assetClass, product]);

  const params = useMemo(
    () => ({
      tcBps, shiftN, variants,
      featureVariant: variants.find((v) => variantLabel(v) === featureLabel),
      focusVariant: variants.find((v) => variantLabel(v) === focusLabel),
      metricsYearStart, metricsYearEnd, equityYearStart, equityYearEnd, rsBasis,
    }),
    [tcBps, shiftN, variants, featureLabel, focusLabel, metricsYearStart, metricsYearEnd,
     equityYearStart, equityYearEnd, rsBasis],
  );
  const debouncedParams = useDebouncedValue(params, 400);

  const { data, isLoading, error } = useQuery({
    queryKey: ["carry", assetClass, product, debouncedParams],
    queryFn: () => fetchCarry(assetClass, product, debouncedParams),
    placeholderData: (prev) => prev,
  });

  useEffect(() => {
    if (data?.positions) onPositionsChange?.(data.positions);
    if (data && !seeded) {
      const seed: CarryVariant[] = [
        { type: "V1", near: data.near_default, far: data.far_default },
        { type: "V2", window: 252 },
        { type: "V3", horizon: 20 },
      ];
      setVariants(seed);
      setFeatureLabel(data.feature_label ?? variantLabel(seed[0]));
      setFocusLabel(data.focus_label ?? variantLabel(seed[0]));
      setAddNear(data.near_default);
      setAddFar(data.far_default);
      setSeeded(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  const [hmDays, setHmDays] = useState<string>("N/A");
  const [hmMode, setHmMode] = useState<"Momentum" | "Zscore">("Momentum");
  const [hmYearStart, setHmYearStart] = useState<number>();
  const [hmYearEnd, setHmYearEnd] = useState<number>();
  const [hmCommitted, setHmCommitted] = useState({
    tcBps, shiftN, days: undefined as number | undefined, mode: undefined as "Momentum" | "Zscore" | undefined,
    yearStart: hmYearStart, yearEnd: hmYearEnd,
  });
  const heatmapQuery = useQuery({
    queryKey: ["carry-heatmap", assetClass, product, hmCommitted],
    queryFn: () => fetchCarryHeatmap(assetClass, product, hmCommitted),
  });

  function addVariant() {
    let v: CarryVariant;
    if (addType === "V1") v = { type: "V1", near: addNear, far: addFar };
    else if (addType === "V2") v = { type: "V2", window: addWindow };
    else v = { type: "V3", horizon: addHorizon };
    if (!variants.some((x) => variantLabel(x) === variantLabel(v))) setVariants([...variants, v]);
  }
  function removeVariant(v: CarryVariant) {
    setVariants(variants.filter((x) => variantLabel(x) !== variantLabel(v)));
  }

  const yr = data?.year_range;
  const contracts = data?.contracts ?? [];

  return (
    <div className="tab-panel">
      <p className="tab-caption">Term structure carry: long in backwardation, short in contango.</p>

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

      <div className="section-header">Add a Carry Variant</div>
      <div className="control-row">
        <label>Variant
          <select value={addType} onChange={(e) => setAddType(e.target.value as "V1" | "V2" | "V3")}>
            <option value="V1">V1 Level (Roll Yield / Long Slope)</option>
            <option value="V2">V2 Z-score</option>
            <option value="V3">V3 Carry-Momentum</option>
          </select>
        </label>
        {addType === "V1" && (
          <>
            <label>Near
              <select value={addNear} onChange={(e) => setAddNear(e.target.value)}>
                {contracts.map((c) => <option key={c}>{c}</option>)}
              </select>
            </label>
            <label>Far
              <select value={addFar} onChange={(e) => setAddFar(e.target.value)}>
                {contracts.filter((c) => c !== addNear).map((c) => <option key={c}>{c}</option>)}
              </select>
            </label>
          </>
        )}
        {addType === "V2" && (
          <label>Window (days)
            <select value={addWindow} onChange={(e) => setAddWindow(Number(e.target.value))}>
              {[126, 252, 504].map((w) => <option key={w} value={w}>{w}</option>)}
            </select>
          </label>
        )}
        {addType === "V3" && (
          <label>Horizon (days)
            <select value={addHorizon} onChange={(e) => setAddHorizon(Number(e.target.value))}>
              {[5, 10, 20, 60].map((h) => <option key={h} value={h}>{h}</option>)}
            </select>
          </label>
        )}
        <button onClick={addVariant}>Add</button>
      </div>
      <div className="pill-row">
        {variants.map((v) => (
          <span className="pill" key={variantLabel(v)}>
            {variantLabel(v)}
            <button className="pill-remove" onClick={() => removeVariant(v)}>×</button>
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
              {variants.map((v) => <option key={variantLabel(v)}>{variantLabel(v)}</option>)}
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

      <div className="section-header">Sharpe Heatmap — Contract Pair × Carry Signal</div>
      <div className="control-row">
        <label>Horizon (days) <input type="text" value={hmDays} onChange={(e) => setHmDays(e.target.value)} /></label>
        {hmDays.trim().toUpperCase() !== "N/A" && !Number.isNaN(Number(hmDays)) && (
          <label>Interpret as
            <select value={hmMode} onChange={(e) => setHmMode(e.target.value as "Momentum" | "Zscore")}>
              <option value="Momentum">V3 Carry-Momentum</option>
              <option value="Zscore">V2 Z-score</option>
            </select>
          </label>
        )}
        <label>Year start <input type="number" value={hmYearStart ?? yr?.min ?? ""}
          onChange={(e) => setHmYearStart(Number(e.target.value))} /></label>
        <label>Year end <input type="number" value={hmYearEnd ?? yr?.max ?? ""}
          onChange={(e) => setHmYearEnd(Number(e.target.value))} /></label>
        <button onClick={() => {
          const clean = hmDays.trim().toUpperCase();
          const parsed = clean === "N/A" || clean === "" ? undefined : Number(hmDays);
          setHmCommitted({
            tcBps, shiftN,
            days: parsed && parsed > 0 ? parsed : undefined,
            mode: parsed && parsed > 0 ? hmMode : undefined,
            yearStart: hmYearStart, yearEnd: hmYearEnd,
          });
        }}>
          Recompute Heatmap
        </button>
      </div>
      {heatmapQuery.isFetching && <p>Computing heatmap…</p>}
      {heatmapQuery.data && (
        <>
          <PlotlyChart fig={heatmapQuery.data.fig} height={560} />
          {heatmapQuery.data.best && (
            <p className="caption">
              Best: ({heatmapQuery.data.best.near}, {heatmapQuery.data.best.far}) gross Sharpe{" "}
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
                {variants.map((v) => <option key={variantLabel(v)}>{variantLabel(v)}</option>)}
              </select>
            </label>
          </div>
          <PlotlyChart fig={data.signal_position_fig} height={500} />
        </>
      )}
    </div>
  );
}
