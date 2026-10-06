import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  fetchCrossAssetMeta, fetchCrossCommodity, fetchCrossCorrelation, fetchCrossN,
  type EquityBlock,
} from "../lib/api";
import { fmtSigned } from "../lib/fmt";
import { useDebouncedValue } from "../lib/useDebouncedValue";
import CheckPills from "../components/CheckPills";
import MetricCard from "../components/MetricCard";
import PlotlyChart from "../components/PlotlyChart";
import YearRangeSlider from "../components/YearRangeSlider";

const CC_COMBINE_HELP =
  "Equal Weight: fixed equal split across the selected styles. Risk Parity: rolling Equal Risk " +
  "Contribution over the full covariance matrix (research/risk_parity.py). Dynamic Risk Parity: " +
  "inverse-EWMA-vol weighting (20-day vol / 60-day covariance half-lives, correlations shrunk 50% " +
  "toward zero), rescaled to match Equal Weight's own full-sample volatility (research/drp.py).";
const CN_COMBINE_HELP =
  "Equal Weight: fixed equal split across the selected asset classes' own EW portfolios. Dynamic " +
  "Risk Parity: inverse-EWMA-vol weighting across those same asset-class portfolios, rescaled to " +
  "match Equal Weight's own full-sample volatility (research/drp.py). No Risk Parity (ERC) option " +
  "at this level.";
const CORR_YEAR_HELP =
  "Restricts the correlation calculation to this sub-period -- a static recomputation over " +
  "whichever years you pick, not a rolling window. Compare different historical regimes (e.g. " +
  "2015-2020 vs 2020-2026) to see whether a correlation is stable or regime-dependent.";

/** Metric cards + equity chart + per-line table, matching hub/app.py::_render_equity_and_metrics. */
function EquityBlockView(props: {
  data: EquityBlock | undefined;
  loading: boolean;
  error: Error | null;
  yr: [number, number] | null;
  onYr: (a: number, b: number) => void;
  onFocus: (f: string) => void;
  hidden: string[];
  onHidden: (h: string[]) => void;
}) {
  const { data, loading, error, yr, onYr, onFocus, hidden, onHidden } = props;
  if (error) return <p className="error">{error.message}</p>;
  if (!data) return <div className="chart-loading">{loading ? "Computing (first load of each asset class can take a minute or two)…" : "No data."}</div>;
  if (data.warning) return <div className="warning-box">{data.warning}</div>;
  if (data.empty) return <div className="warning-box">No data for this selection.</div>;

  const shown = data.labels.filter((l) => !hidden.includes(l));
  const m = data.metrics;
  return (
    <>
      <div className="control-row" style={{ alignItems: "flex-start" }}>
        <label style={{ flex: "0 0 240px" }}>Strategy (for metric cards)
          <select value={data.focus} onChange={(e) => onFocus(e.target.value)}>
            {data.labels.map((l) => <option key={l}>{l}</option>)}
          </select>
        </label>
        <YearRangeSlider min={data.min_year} max={data.max_year}
          start={yr?.[0] ?? data.yr_start} end={yr?.[1] ?? data.yr_end} onChange={onYr} />
      </div>
      <CheckPills label="Lines shown on chart" options={data.labels} selected={shown}
        onChange={(sel) => onHidden(data.labels.filter((l) => !sel.includes(l)))} />

      <div className="metric-row">
        <MetricCard label="Gross Sharpe" value={m.gross} format={(v) => fmtSigned(v)} />
        <MetricCard label="Net Sharpe" value={m.net} format={(v) => fmtSigned(v)} />
        <MetricCard label="Ann Return (Net)" value={m.ann} format={(v) => fmtSigned(v)} unit="%" />
        <MetricCard label="Ann Vol" value={m.vol} format={(v) => v.toFixed(2)} unit="%" />
        <MetricCard label="Max DD (Net)" value={m.mdd} format={(v) => fmtSigned(v)} unit="%" />
      </div>

      <div className="section-header">Cumulative equity</div>
      <PlotlyChart fig={data.equity_fig} height={440} />
      {loading && <p className="caption">Updating…</p>}

      {data.table_rows.length > 0 && (
        <table className="stat-table">
          <thead><tr><th>Strategy</th><th>Return (%/yr)</th><th>Vol (%/yr)</th><th>IR</th></tr></thead>
          <tbody>
            {data.table_rows.map((r) => (
              <tr key={r.strategy}>
                <td>{r.strategy}</td>
                <td>{r.return != null ? fmtSigned(r.return) : "N/A"}</td>
                <td>{r.vol != null ? r.vol.toFixed(2) : "N/A"}</td>
                <td>{r.ir != null ? fmtSigned(r.ir, 3) : "N/A"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

export default function CrossAssetPage() {
  const { data: meta } = useQuery({ queryKey: ["crossasset-meta"], queryFn: fetchCrossAssetMeta, staleTime: Infinity });

  const [tcBps, setTcBps] = useState(5);

  // Cross-Commodity
  const [ccAssets, setCcAssets] = useState<string[] | null>(null);
  const [ccStyles, setCcStyles] = useState<string[] | null>(null);
  const [ccCombine, setCcCombine] = useState("Equal Weight");
  const [ccYr, setCcYr] = useState<[number, number] | null>(null);
  const [ccFocus, setCcFocus] = useState<string | undefined>();
  const [ccHidden, setCcHidden] = useState<string[]>([]);

  // Cross-Asset-Class
  const [cnAssets, setCnAssets] = useState<string[]>(["Metals", "Energy"]);
  const [cnCombine, setCnCombine] = useState("Equal Weight");
  const [cnYr, setCnYr] = useState<[number, number] | null>(null);
  const [cnFocus, setCnFocus] = useState<string | undefined>();
  const [cnHidden, setCnHidden] = useState<string[]>([]);

  // Correlation
  const [corrYr, setCorrYr] = useState<[number, number] | null>(null);
  const [corrHidden, setCorrHidden] = useState<string[]>([]);

  useEffect(() => {
    if (meta && ccAssets === null) setCcAssets(meta.asset_classes);
    if (meta && ccStyles === null) setCcStyles(meta.styles);
  }, [meta, ccAssets, ccStyles]);

  const ccParams = useDebouncedValue(
    { tcBps, assets: ccAssets ?? [], styles: ccStyles ?? [], combine: ccCombine,
      yrStart: ccYr?.[0], yrEnd: ccYr?.[1], focus: ccFocus, hidden: ccHidden }, 400);
  const cc = useQuery({
    queryKey: ["cc", ccParams], queryFn: () => fetchCrossCommodity(ccParams),
    enabled: ccParams.assets.length > 0 && ccParams.styles.length > 0, placeholderData: (p) => p,
  });

  const cnParams = useDebouncedValue(
    { tcBps, assets: cnAssets, combine: cnCombine, yrStart: cnYr?.[0], yrEnd: cnYr?.[1], focus: cnFocus, hidden: cnHidden }, 400);
  const cn = useQuery({
    queryKey: ["cn", cnParams], queryFn: () => fetchCrossN(cnParams), placeholderData: (p) => p,
  });

  const corrAll = useQuery({
    queryKey: ["corr-base", tcBps], queryFn: () => fetchCrossCorrelation({ tcBps }), placeholderData: (p) => p,
  });
  const corrStrategies = useMemo(
    () => (corrAll.data ? corrAll.data.strategy_labels.filter((l) => !corrHidden.includes(l)) : undefined),
    [corrAll.data, corrHidden]);
  const corrParams = useDebouncedValue({ tcBps, yrStart: corrYr?.[0], yrEnd: corrYr?.[1], strategies: corrStrategies }, 400);
  const corr = useQuery({
    queryKey: ["corr", corrParams], queryFn: () => fetchCrossCorrelation(corrParams),
    enabled: corrStrategies !== undefined, placeholderData: (p) => p,
  });

  const ccWarn = ccAssets !== null && ccAssets.length < 2 ? "Pick at least 2 asset classes." : null;

  return (
    <div className="page">
      <h1>🌐 Cross-Asset Portfolio</h1>
      <p className="tab-caption">
        Combining asset classes into one book (Research_Methodology.docx Section 9). Calendar alignment:
        intersection -- a date where any selected asset class isn't trading is dropped entirely, with a
        dropped date's move rolled into the next surviving date so no leg's real return is lost.
      </p>

      <div className="control-row">
        <label style={{ minWidth: 260 }} title="Applied at every level of this construction (product, asset-class, cross-asset). Default 5bps matches every other report in this project.">
          TC (bps, round-trip): {tcBps}
          <input type="range" min={0} max={20} step={1} value={tcBps} onChange={(e) => setTcBps(Number(e.target.value))} style={{ padding: 0 }} />
        </label>
      </div>

      <hr className="divider" />

      <div className="section-header">Cross-Commodity Portfolio</div>
      <p className="tab-caption">
        Each selected style is first equal-weighted across the selected asset classes into one
        cross-commodity series per style, then those style-level series are combined into one portfolio --
        a two-stage hierarchical construction (Methodology doc Section 9), not a single flat optimization
        over every underlying leg.
      </p>
      <div className="control-row" style={{ alignItems: "flex-start" }}>
        <div style={{ flex: "1 1 220px" }}>
          <CheckPills label="Asset classes" options={meta?.asset_classes ?? []} selected={ccAssets ?? []} onChange={setCcAssets} />
        </div>
        <div style={{ flex: "1 1 220px" }}>
          <CheckPills label="Styles" options={meta?.styles ?? []} selected={ccStyles ?? []} onChange={setCcStyles} />
        </div>
        <label title={CC_COMBINE_HELP}>Combine method
          <select value={ccCombine} onChange={(e) => setCcCombine(e.target.value)}>
            {(meta?.cc_combine_methods ?? ["Equal Weight"]).map((m) => <option key={m}>{m}</option>)}
          </select>
        </label>
      </div>
      {ccWarn ? <div className="warning-box">{ccWarn}</div>
        : ccStyles !== null && ccStyles.length === 0 ? <div className="warning-box">Pick at least 1 style.</div>
        : (
          <EquityBlockView data={cc.data} loading={cc.isFetching} error={cc.error as Error | null}
            yr={ccYr} onYr={(a, b) => setCcYr([a, b])} onFocus={setCcFocus}
            hidden={ccHidden} onHidden={setCcHidden} />
        )}

      <hr className="divider" />

      <div className="section-header">Cross-Asset-Class Portfolio</div>
      <p className="tab-caption">
        Combination of 1-4 asset classes' own Equal Weight portfolios (generalizes the 4 fixed Cross-Pairs
        shown on the static report to any 1-4 you pick). Pick just one to see that asset class's own EW
        Portfolio number on its own, matching its individual dashboard's Portfolio tab.
      </p>
      <div className="control-row" style={{ alignItems: "flex-start" }}>
        <div style={{ flex: "3 1 320px" }}>
          <CheckPills label="Asset classes (choose 1-4)" options={meta?.asset_classes ?? []} selected={cnAssets} onChange={setCnAssets} />
        </div>
        <label title={CN_COMBINE_HELP}>Combine method
          <select value={cnCombine} onChange={(e) => setCnCombine(e.target.value)}>
            {(meta?.cn_combine_methods ?? ["Equal Weight"]).map((m) => <option key={m}>{m}</option>)}
          </select>
        </label>
      </div>
      {cnAssets.length < 1 ? <div className="warning-box">Pick between 1 and 4 asset classes.</div> : (
        <EquityBlockView data={cn.data} loading={cn.isFetching} error={cn.error as Error | null}
          yr={cnYr} onYr={(a, b) => setCnYr([a, b])} onFocus={setCnFocus}
          hidden={cnHidden} onHidden={setCnHidden} />
      )}

      <hr className="divider" />

      <div className="section-header">Correlation vs Traditional Assets</div>
      <p className="tab-caption">
        How the Cross-Commodity Portfolio's strategy rows (Momentum/Carry/CarryMom/Value/EW PORT/Risk
        Parity/Dynamic Risk Parity) correlate with Equity (S&amp;P 500), Fixed Income (US Aggregate Bond), a
        broad passive Commodity Index (DBC), Gold as a distinct safe-haven, and a traditional 60/40
        stock-bond portfolio -- the standard "does this add value beyond simple beta, and does it diversify
        a traditional portfolio" questions for any systematic commodity strategy. Data: research/benchmarks.py
        (yfinance daily prices, cached locally).
      </p>
      {corrAll.data && (
        <>
          <div className="control-row" style={{ alignItems: "flex-start" }}>
            <YearRangeSlider min={corrAll.data.min_year} max={corrAll.data.max_year}
              start={corrYr?.[0] ?? corrAll.data.default_start} end={corrYr?.[1] ?? corrAll.data.max_year}
              onChange={(a, b) => setCorrYr([a, b])} help={CORR_YEAR_HELP} />
            <div style={{ flex: "1 1 260px" }}>
              <CheckPills label="Strategies shown" options={corrAll.data.strategy_labels}
                selected={corrAll.data.strategy_labels.filter((l) => !corrHidden.includes(l))}
                onChange={(sel) => setCorrHidden(corrAll.data!.strategy_labels.filter((l) => !sel.includes(l)))} />
            </div>
          </div>
          {corr.data?.warning ? <div className="warning-box">{corr.data.warning}</div>
            : <PlotlyChart fig={corr.data?.fig ?? null} height={380} />}
        </>
      )}
      {!corrAll.data && <div className="chart-loading">{corrAll.error ? (corrAll.error as Error).message : "Computing (first load can take a minute or two)…"}</div>}

      <hr className="divider" />
      <p className="caption">
        Engine: research/cross_asset_engine.py (new, isolated module -- does not modify common_engine.py,
        research/engine.py, research/risk_parity.py, or any of the 4 live asset-class dashboards).
        Signal-level Carry/Carry-Momentum combination across tenor pairs (Methodology doc Section 7), not
        the return-level construction used in an earlier static HTML report edit -- these numbers and those
        reports are not directly comparable until the reports are regenerated to match.
      </p>
    </div>
  );
}
