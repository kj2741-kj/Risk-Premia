import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  fetchPortfolioReference, fetchPortfolioResults,
  type CustomPortfolioDef, type PortfolioLeg, type PortfolioSleeve, type ReferenceStrategy,
} from "../lib/api";
import { useDebouncedValue } from "../lib/useDebouncedValue";
import PlotlyChart from "./PlotlyChart";
import MetricCard from "./MetricCard";

type Family = "Momentum" | "Carry" | "CarryMom" | "Value";
const FAMILY_ORDER: Family[] = ["Momentum", "Carry", "CarryMom", "Value"];
const FAMILY_TITLE: Record<Family, string> = { Momentum: "Momentum", Carry: "Carry", CarryMom: "Carry-Momentum", Value: "Value" };
const DEFAULT_SHIFT_N: Record<Family, number> = { Momentum: 1, Carry: 1, CarryMom: 1, Value: 2 };
const COMBINE_METHODS = ["Equal Weight", "Inverse Vol", "Risk Parity (ERC, rolling)"];
const FAR_NEAR_OPTIONS = Array.from({ length: 15 }, (_, i) => `F${i + 1}`);
const CARRY_TYPES = ["V1 Level", "V2 Z-score", "V3 Carry-Momentum"] as const;

interface DraftSleeve {
  enabled: boolean;
  legs: PortfolioLeg[];
  shiftN: number;
  sharedTenor: boolean;
  sharedNear: string;
  sharedFar: string;
}

function blankSleeve(family: Family): DraftSleeve {
  return {
    enabled: false, legs: [], shiftN: DEFAULT_SHIFT_N[family],
    sharedTenor: true, sharedNear: "F1", sharedFar: "F3",
  };
}
function blankDraft(): Record<Family, DraftSleeve> {
  return { Momentum: blankSleeve("Momentum"), Carry: blankSleeve("Carry"), CarryMom: blankSleeve("CarryMom"), Value: blankSleeve("Value") };
}

function newLeg(family: Family, near: string, far: string): PortfolioLeg {
  if (family === "Momentum") return { fast: 5, slow: 60 };
  if (family === "Carry") return { type: "V1 Level", near, far, zwindow: 252, horizon: 20 };
  if (family === "CarryMom") return { near, far, horizon: 20 };
  return { contract: "F8", lookback: 1260, threshold: 0.10 };
}

interface PortfolioTabProps {
  assetClass: string;
}

export default function PortfolioTab({ assetClass }: PortfolioTabProps) {
  const { data: refData } = useQuery({
    queryKey: ["portfolio-reference", assetClass],
    queryFn: () => fetchPortfolioReference(assetClass),
    staleTime: Infinity,
  });
  const strategies: ReferenceStrategy[] = refData?.strategies ?? [];

  // ── Live controls (debounced, not gated behind Refresh Results -- matches
  // the Streamlit tab, where tc_bps/combine_method/vol_window/return_tilt
  // sit OUTSIDE the st.form and recompute immediately). ──────────────────
  const [tcBps, setTcBps] = useState(5);
  const [combineMethod, setCombineMethod] = useState("Equal Weight");
  const [volWindow, setVolWindow] = useState(63);
  const [returnTilt, setReturnTilt] = useState(0);

  // ── Draft builder ───────────────────────────────────────────────────────
  const [draft, setDraft] = useState<Record<Family, DraftSleeve>>(blankDraft());
  const [portfolios, setPortfolios] = useState<CustomPortfolioDef[]>([]);
  const [portfolioCounter, setPortfolioCounter] = useState(1);

  function referenceSeedFor(family: Family): { legs: PortfolioLeg[]; shiftN: number } | null {
    const ref = strategies.find((s) => s.family === family);
    if (!ref) return null;
    return { legs: ref.legs, shiftN: ref.shift_n };
  }

  function toggleFamily(family: Family) {
    setDraft((d) => {
      const sleeve = d[family];
      if (sleeve.enabled) {
        return { ...d, [family]: blankSleeve(family) };
      }
      const seed = referenceSeedFor(family);
      const legs = seed?.legs ?? [newLeg(family, "F1", "F3")];
      const shiftN = seed?.shiftN ?? DEFAULT_SHIFT_N[family];
      const sharedNear = (family === "Carry" || family === "CarryMom") ? (legs[0]?.near ?? "F1") : "F1";
      const sharedFar = (family === "Carry" || family === "CarryMom") ? (legs[0]?.far ?? "F3") : "F3";
      return { ...d, [family]: { enabled: true, legs, shiftN, sharedTenor: true, sharedNear, sharedFar } };
    });
  }

  function updateSleeve(family: Family, patch: Partial<DraftSleeve>) {
    setDraft((d) => ({ ...d, [family]: { ...d[family], ...patch } }));
  }
  function updateLeg(family: Family, index: number, patch: PortfolioLeg) {
    setDraft((d) => {
      const legs = d[family].legs.slice();
      legs[index] = { ...legs[index], ...patch };
      return { ...d, [family]: { ...d[family], legs } };
    });
  }
  function removeLeg(family: Family, index: number) {
    setDraft((d) => ({ ...d, [family]: { ...d[family], legs: d[family].legs.filter((_, i) => i !== index) } }));
  }
  function addLeg(family: Family) {
    setDraft((d) => {
      const sleeve = d[family];
      const leg = newLeg(family, sleeve.sharedNear, sleeve.sharedFar);
      return { ...d, [family]: { ...sleeve, legs: [...sleeve.legs, leg] } };
    });
  }

  function addPortfolio() {
    const sleeves: PortfolioSleeve[] = [];
    for (const family of FAMILY_ORDER) {
      const sleeve = draft[family];
      if (!sleeve.enabled || sleeve.legs.length === 0) continue;
      const legs = sleeve.legs.map((leg) => {
        if ((family === "Carry" || family === "CarryMom") && sleeve.sharedTenor) {
          return { ...leg, near: sleeve.sharedNear, far: sleeve.sharedFar };
        }
        return leg;
      });
      sleeves.push({ family, legs, shift_n: sleeve.shiftN, combine_method: "equal_weight" });
    }
    if (sleeves.length === 0) return;
    setPortfolios((p) => [...p, { label: `Portfolio ${portfolioCounter}`, sleeves }]);
    setPortfolioCounter((n) => n + 1);
    setDraft(blankDraft());
  }
  function removePortfolio(label: string) {
    setPortfolios((p) => p.filter((x) => x.label !== label));
  }

  // ── Results section: batched behind "Refresh Results" for year range /
  // metric strategy / shown list (matches the st.form in the original tab).
  // tc_bps/combine_method/vol_window/return_tilt/portfolios are live. ─────
  const liveParams = useMemo(
    () => ({ tcBps, combineMethod, volWindow, returnTilt, customPortfolios: portfolios }),
    [tcBps, combineMethod, volWindow, returnTilt, portfolios],
  );
  const debouncedLive = useDebouncedValue(liveParams, 400);

  const [applied, setApplied] = useState<{ yrStart?: number; yrEnd?: number; metricStrategy?: string; shown?: string[] }>({});
  const [pendingYrStart, setPendingYrStart] = useState<number>();
  const [pendingYrEnd, setPendingYrEnd] = useState<number>();
  const [pendingMetricStrategy, setPendingMetricStrategy] = useState<string>();
  const [pendingShownExcluded, setPendingShownExcluded] = useState<string[]>([]);

  const queryParams = useMemo(() => ({ ...debouncedLive, ...applied }), [debouncedLive, applied]);

  const { data, isFetching, error } = useQuery({
    queryKey: ["portfolio-results", assetClass, queryParams],
    queryFn: () => fetchPortfolioResults(assetClass, queryParams),
    placeholderData: (prev) => prev,
  });

  const metricLabels = data?.metric_labels ?? [];

  useEffect(() => {
    // Seed the results controls once labels first arrive, and whenever the
    // previously-selected metric strategy disappears (e.g. its portfolio
    // was removed).
    if (metricLabels.length === 0) return;
    if (pendingMetricStrategy === undefined || !metricLabels.includes(pendingMetricStrategy)) {
      setPendingMetricStrategy(metricLabels[metricLabels.length - 1]);
    }
    if (data && pendingYrStart === undefined) setPendingYrStart(data.min_year);
    if (data && pendingYrEnd === undefined) setPendingYrEnd(data.max_year);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [metricLabels.join(","), data?.min_year, data?.max_year]);

  function refreshResults() {
    setApplied({
      yrStart: pendingYrStart, yrEnd: pendingYrEnd,
      metricStrategy: pendingMetricStrategy,
      shown: metricLabels.filter((l) => !pendingShownExcluded.includes(l)),
    });
  }

  return (
    <div className="tab-panel">
      <p className="tab-caption">
        Log-return methodology (research/engine.py), not the dollar-PnL convention used by
        Momentum/Carry/Value/Comparison above -- figures here will not reconcile exactly with those tabs.
      </p>
      {data && (
        <p className="caption">
          Common data window across all products: {data.common_start} to {data.common_end}.
        </p>
      )}

      <div className="control-row">
        <label>Transaction cost (bps, round-trip)
          <input type="number" min={0} max={50} value={tcBps} onChange={(e) => setTcBps(Number(e.target.value))} />
        </label>
        <label>Combine strategies via
          <select value={combineMethod} onChange={(e) => setCombineMethod(e.target.value)}>
            {COMBINE_METHODS.map((m) => <option key={m}>{m}</option>)}
          </select>
        </label>
        {combineMethod === "Inverse Vol" && (
          <label>Inverse-vol lookback (days)
            <input type="number" min={5} max={252} value={volWindow} onChange={(e) => setVolWindow(Number(e.target.value))} />
          </label>
        )}
        {combineMethod === "Risk Parity (ERC, rolling)" && (
          <label>Return tilt (0-1)
            <input type="number" min={0} max={1} step={0.05} value={returnTilt} onChange={(e) => setReturnTilt(Number(e.target.value))} />
          </label>
        )}
      </div>

      <div className="section-header">Reference Strategies</div>
      <p className="tab-caption">The officially reported parameter set for this asset class -- read-only.</p>
      {strategies.map((s) => (
        <details key={s.id} style={{ marginBottom: 6 }}>
          <summary style={{ cursor: "pointer", color: "var(--text)" }}>{s.label}</summary>
          <ul>
            {s.legs_desc.map((d, i) => <li key={i} className="tab-caption">{d}</li>)}
          </ul>
          <p className="caption">Execution lag (shift_n): {s.shift_n} | Combine legs via: Equal Weight</p>
        </details>
      ))}

      <div className="section-header">Portfolio Construction</div>
      <p className="tab-caption">
        Switch on whichever strategy families belong in this portfolio. Each pre-fills with its
        reference parameters -- edit to customize, or leave as-is.
      </p>
      {FAMILY_ORDER.map((family) => {
        const sleeve = draft[family];
        return (
          <div key={family} className="control-row" style={{ display: "block", border: "1px solid var(--panel-border)", borderRadius: 4, padding: 12, marginBottom: 10 }}>
            <label style={{ display: "flex", flexDirection: "row", alignItems: "center", gap: 8, textTransform: "none" }}>
              <input type="checkbox" checked={sleeve.enabled} onChange={() => toggleFamily(family)} />
              Include {FAMILY_TITLE[family]}
            </label>
            {sleeve.enabled && (
              <div style={{ marginTop: 10 }}>
                {(family === "Carry" || family === "CarryMom") && (
                  <div className="control-row">
                    <label>
                      <input type="checkbox" checked={sleeve.sharedTenor}
                        onChange={(e) => updateSleeve(family, { sharedTenor: e.target.checked })} /> Shared tenor pair
                    </label>
                    {sleeve.sharedTenor && (
                      <>
                        <label>Near
                          <select value={sleeve.sharedNear} onChange={(e) => updateSleeve(family, { sharedNear: e.target.value })}>
                            {FAR_NEAR_OPTIONS.map((c) => <option key={c}>{c}</option>)}
                          </select>
                        </label>
                        <label>Far
                          <select value={sleeve.sharedFar} onChange={(e) => updateSleeve(family, { sharedFar: e.target.value })}>
                            {FAR_NEAR_OPTIONS.map((c) => <option key={c}>{c}</option>)}
                          </select>
                        </label>
                      </>
                    )}
                  </div>
                )}
                {sleeve.legs.map((leg, i) => (
                  <div className="control-row" key={i}>
                    {family === "Momentum" && (
                      <>
                        <label>Fast MA <input type="number" min={1} max={500} value={leg.fast ?? 5}
                          onChange={(e) => updateLeg(family, i, { fast: Number(e.target.value) })} /></label>
                        <label>Slow MA <input type="number" min={2} max={500} value={leg.slow ?? 60}
                          onChange={(e) => updateLeg(family, i, { slow: Number(e.target.value) })} /></label>
                      </>
                    )}
                    {family === "Carry" && (
                      <>
                        <label>Type
                          <select value={leg.type ?? "V1 Level"} onChange={(e) => updateLeg(family, i, { type: e.target.value as PortfolioLeg["type"] })}>
                            {CARRY_TYPES.map((t) => <option key={t}>{t}</option>)}
                          </select>
                        </label>
                        {!sleeve.sharedTenor && (
                          <>
                            <label>Near
                              <select value={leg.near ?? "F1"} onChange={(e) => updateLeg(family, i, { near: e.target.value })}>
                                {FAR_NEAR_OPTIONS.map((c) => <option key={c}>{c}</option>)}
                              </select>
                            </label>
                            <label>Far
                              <select value={leg.far ?? "F3"} onChange={(e) => updateLeg(family, i, { far: e.target.value })}>
                                {FAR_NEAR_OPTIONS.map((c) => <option key={c}>{c}</option>)}
                              </select>
                            </label>
                          </>
                        )}
                        {leg.type === "V2 Z-score" && (
                          <label>Z-Window <input type="number" min={20} max={756} value={leg.zwindow ?? 252}
                            onChange={(e) => updateLeg(family, i, { zwindow: Number(e.target.value) })} /></label>
                        )}
                        {leg.type === "V3 Carry-Momentum" && (
                          <label>Horizon <input type="number" min={1} max={252} value={leg.horizon ?? 20}
                            onChange={(e) => updateLeg(family, i, { horizon: Number(e.target.value) })} /></label>
                        )}
                      </>
                    )}
                    {family === "CarryMom" && (
                      <>
                        {!sleeve.sharedTenor && (
                          <>
                            <label>Near
                              <select value={leg.near ?? "F1"} onChange={(e) => updateLeg(family, i, { near: e.target.value })}>
                                {FAR_NEAR_OPTIONS.map((c) => <option key={c}>{c}</option>)}
                              </select>
                            </label>
                            <label>Far
                              <select value={leg.far ?? "F3"} onChange={(e) => updateLeg(family, i, { far: e.target.value })}>
                                {FAR_NEAR_OPTIONS.map((c) => <option key={c}>{c}</option>)}
                              </select>
                            </label>
                          </>
                        )}
                        <label>Horizon <input type="number" min={1} max={252} value={leg.horizon ?? 20}
                          onChange={(e) => updateLeg(family, i, { horizon: Number(e.target.value) })} /></label>
                      </>
                    )}
                    {family === "Value" && (
                      <>
                        <label>Contract
                          <select value={leg.contract ?? "F8"} onChange={(e) => updateLeg(family, i, { contract: e.target.value })}>
                            {FAR_NEAR_OPTIONS.map((c) => <option key={c}>{c}</option>)}
                          </select>
                        </label>
                        <label>Lookback (days) <input type="number" min={20} max={2520} value={leg.lookback ?? 1260}
                          onChange={(e) => updateLeg(family, i, { lookback: Number(e.target.value) })} /></label>
                        <label>Threshold <input type="number" min={0} max={1} step={0.01} value={leg.threshold ?? 0.10}
                          onChange={(e) => updateLeg(family, i, { threshold: Number(e.target.value) })} /></label>
                      </>
                    )}
                    <button onClick={() => removeLeg(family, i)}>Remove</button>
                  </div>
                ))}
                <div className="control-row">
                  <button onClick={() => addLeg(family)}>Add leg</button>
                  <label>Execution lag (shift_n) <input type="number" min={0} max={5} value={sleeve.shiftN}
                    onChange={(e) => updateSleeve(family, { shiftN: Number(e.target.value) })} /></label>
                </div>
              </div>
            )}
          </div>
        );
      })}
      <button onClick={addPortfolio} style={{ marginBottom: 20 }}>Add Portfolio</button>

      {portfolios.length > 0 && (
        <>
          <div className="section-header">Your Portfolios</div>
          {portfolios.map((p) => (
            <div className="control-row" key={p.label}>
              <span>{p.label} -- {p.sleeves.map((s) => FAMILY_TITLE[s.family]).join(" + ")}</span>
              <button onClick={() => removePortfolio(p.label)}>Remove</button>
            </div>
          ))}
        </>
      )}

      <div className="section-header">Year Range, Performance Metrics, and Cumulative Equity</div>
      <p className="tab-caption">Adjust the controls below, then click Refresh Results.</p>
      <div className="control-row">
        <label>Year start <input type="number" value={pendingYrStart ?? ""} onChange={(e) => setPendingYrStart(Number(e.target.value))} /></label>
        <label>Year end <input type="number" value={pendingYrEnd ?? ""} onChange={(e) => setPendingYrEnd(Number(e.target.value))} /></label>
        <label>Strategy (for metric cards)
          <select value={pendingMetricStrategy ?? ""} onChange={(e) => setPendingMetricStrategy(e.target.value)}>
            {metricLabels.map((l) => <option key={l}>{l}</option>)}
          </select>
        </label>
        <button onClick={refreshResults}>Refresh Results</button>
      </div>
      <div className="pill-row">
        {metricLabels.map((l) => {
          const shown = !pendingShownExcluded.includes(l);
          return (
            <span className="pill" key={l} style={{ opacity: shown ? 1 : 0.4 }}>
              {l}
              <button className="pill-remove" onClick={() =>
                setPendingShownExcluded((ex) => shown ? [...ex, l] : ex.filter((x) => x !== l))
              }>{shown ? "×" : "+"}</button>
            </span>
          );
        })}
      </div>

      {isFetching && <p>Computing…</p>}
      {error && <p className="error">{(error as Error).message}</p>}

      {data?.metrics && (
        <div className="metric-row">
          <MetricCard label="Gross Sharpe" value={data.metrics.gross} format={(v) => v.toFixed(2)} />
          <MetricCard label="Net Sharpe" value={data.metrics.net} format={(v) => v.toFixed(2)} />
          <MetricCard label="Ann Return (Net)" value={data.metrics.ann} format={(v) => v.toFixed(2)} unit="%" />
          <MetricCard label="Ann Vol" value={data.metrics.vol} format={(v) => v.toFixed(2)} unit="%" />
          <MetricCard label="Max DD (Net)" value={data.metrics.mdd} format={(v) => v.toFixed(2)} unit="%" />
        </div>
      )}
      <p className="caption">
        Vol replaces "% Flat" here -- once returns are equal-weighted across products, "active day" no
        longer has one well-defined meaning.
      </p>

      <PlotlyChart fig={data?.equity_fig ?? null} height={460} />

      {data && data.table_rows.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
          <thead>
            <tr style={{ textAlign: "left", color: "var(--text-muted)", fontSize: "0.78rem", textTransform: "uppercase" }}>
              <th>Strategy</th><th>Return (%/yr)</th><th>Vol (%/yr)</th><th>IR</th>
            </tr>
          </thead>
          <tbody>
            {data.table_rows.map((r) => (
              <tr key={r.strategy} style={{ borderTop: "1px solid var(--panel-border)" }}>
                <td>{r.strategy}</td>
                <td>{r.return?.toFixed(2) ?? "N/A"}</td>
                <td>{r.vol?.toFixed(2) ?? "N/A"}</td>
                <td>{r.ir?.toFixed(3) ?? "N/A"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
