import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchComparison, type SeriesJson } from "../lib/api";
import { useDebouncedValue } from "../lib/useDebouncedValue";
import PlotlyChart from "./PlotlyChart";

const VOL_WINDOWS = ["21d (1mo)", "63d (1qtr)", "126d (6mo)", "252d (1yr)"];
const TC_OPTIONS = [0, 5, 10, 20];

interface ComparisonTabProps {
  assetClass: string;
  product: string;
  groups: Record<string, Record<string, SeriesJson>>;
}

export default function ComparisonTab({ assetClass, product, groups }: ComparisonTabProps) {
  const [volWindowLabel, setVolWindowLabel] = useState("63d (1qtr)");
  const [tcBps, setTcBps] = useState(5);
  const [chosen, setChosen] = useState<string[] | undefined>(undefined);
  const [showVolOverlay, setShowVolOverlay] = useState(false);
  const [rsBasis, setRsBasis] = useState<"net" | "gross">("net");
  const [equityYearStart, setEquityYearStart] = useState<number>();
  const [equityYearEnd, setEquityYearEnd] = useState<number>();

  const hasGroups = Object.values(groups).some((g) => Object.keys(g).length > 0);

  const params = useMemo(
    () => ({ groups, tcBps, volWindowLabel, chosen, showVolOverlay, rsBasis, equityYearStart, equityYearEnd }),
    [groups, tcBps, volWindowLabel, chosen, showVolOverlay, rsBasis, equityYearStart, equityYearEnd],
  );
  const debouncedParams = useDebouncedValue(params, 400);

  const { data, isLoading, error } = useQuery({
    queryKey: ["comparison", assetClass, product, debouncedParams],
    queryFn: () => fetchComparison(assetClass, product, debouncedParams),
    enabled: hasGroups,
    placeholderData: (prev) => prev,
  });

  if (!hasGroups) {
    return (
      <div className="tab-panel">
        <p className="tab-caption">
          Open the Momentum, Carry, and Value tabs above at least once — this tab overlays whatever strategies
          are currently active there.
        </p>
      </div>
    );
  }

  const options = data?.available_labels ?? [];
  const yr = data?.year_range;

  return (
    <div className="tab-panel">
      <p className="tab-caption">
        Overlays every strategy currently active in the Momentum, Carry, and Value tabs above.
      </p>

      <div className="section-header">Underlying Volatility — {product}</div>
      <div className="control-row">
        <label>Window
          <select value={volWindowLabel} onChange={(e) => setVolWindowLabel(e.target.value)}>
            {VOL_WINDOWS.map((w) => <option key={w}>{w}</option>)}
          </select>
        </label>
      </div>
      {isLoading && !data && <p>Loading…</p>}
      {error && <p className="error">{(error as Error).message}</p>}
      <PlotlyChart fig={data?.vol_fig ?? null} height={300} />

      <div className="section-header">Strategies to Compare</div>
      <div className="control-row">
        <label>Transaction Cost
          <select value={tcBps} onChange={(e) => setTcBps(Number(e.target.value))}>
            {TC_OPTIONS.map((bps) => <option key={bps} value={bps}>{bps === 0 ? "0 bps (Gross)" : `${bps} bps`}</option>)}
          </select>
        </label>
      </div>
      <div className="pill-row">
        {options.map((label) => {
          const active = !chosen || chosen.includes(label);
          return (
            <span className="pill" key={label} style={{ opacity: active ? 1 : 0.4 }}>
              {label}
              <button className="pill-remove" onClick={() => {
                const base = chosen ?? options;
                setChosen(active ? base.filter((l) => l !== label) : [...base, label]);
              }}>{active ? "×" : "+"}</button>
            </span>
          );
        })}
      </div>

      <div className="section-header">Cumulative PnL (Equity Curve) — Net of TC</div>
      <div className="control-row">
        <label>Equity year start <input type="number" value={equityYearStart ?? yr?.min ?? ""}
          onChange={(e) => setEquityYearStart(Number(e.target.value))} /></label>
        <label>Equity year end <input type="number" value={equityYearEnd ?? yr?.max ?? ""}
          onChange={(e) => setEquityYearEnd(Number(e.target.value))} /></label>
        <label><input type="checkbox" checked={showVolOverlay} onChange={(e) => setShowVolOverlay(e.target.checked)} /> Superimpose Volatility</label>
      </div>
      <PlotlyChart fig={data?.equity_curve_fig ?? null} height={380} />

      <div className="section-header">Rolling Sharpe (252-Day)</div>
      <div className="control-row">
        <label><input type="radio" checked={rsBasis === "gross"} onChange={() => setRsBasis("gross")} /> Gross</label>
        <label><input type="radio" checked={rsBasis === "net"} onChange={() => setRsBasis("net")} /> Net of TC</label>
      </div>
      <PlotlyChart fig={data?.rolling_sharpe_fig ?? null} height={320} />
    </div>
  );
}
