import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchFundamental, fetchFundamentalBounds } from "../lib/api";
import { useDebouncedValue } from "../lib/useDebouncedValue";
import PlotlyChart from "../components/PlotlyChart";
import MetricCard from "../components/MetricCard";

const COMMODITIES = [
  { key: "copper", label: "Copper (LME)" },
  { key: "wti", label: "WTI Crude (NYMEX)" },
];

export default function FundamentalAnalysisPage() {
  const [commodity, setCommodity] = useState("copper");
  const [basisSource, setBasisSource] = useState<"f1f2" | "cash3m">("f1f2");
  const [start, setStart] = useState<string>();
  const [end, setEnd] = useState<string>();
  const [trailingWeeks, setTrailingWeeks] = useState(52);
  const [nwBandwidth, setNwBandwidth] = useState(52);
  const [fixedScale, setFixedScale] = useState(true);

  const { data: bounds } = useQuery({
    queryKey: ["fundamental-bounds", commodity, basisSource],
    queryFn: () => fetchFundamentalBounds(commodity, basisSource),
  });

  useEffect(() => {
    // Reset the regression window to the full available range whenever the
    // commodity or basis definition changes (their date ranges differ).
    setStart(undefined);
    setEnd(undefined);
  }, [commodity, basisSource]);

  const params = useMemo(
    () => ({ basisSource, start, end, trailingWeeks, nwBandwidth, fixedScale }),
    [basisSource, start, end, trailingWeeks, nwBandwidth, fixedScale],
  );
  const debouncedParams = useDebouncedValue(params, 400);

  const { data, isFetching, error } = useQuery({
    queryKey: ["fundamental", commodity, debouncedParams],
    queryFn: () => fetchFundamental(commodity, debouncedParams),
    placeholderData: (prev) => prev,
  });

  return (
    <div className="page">
      <h1>Fundamental Analysis: Inventory vs Basis</h1>
      <p className="tab-caption">
        A replication of Gorton, Hayashi &amp; Rouwenhorst (2013): the futures basis is fit on
        normalized inventory (I/I*, trailing 52-week average) using a cubic spline knotted at
        I/I*=1, with monthly seasonal dummies and Newey-West HAC standard errors, weekly frequency.
      </p>

      <div className="control-row">
        <label>Commodity
          <select value={commodity} onChange={(e) => setCommodity(e.target.value)}>
            {COMMODITIES.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
          </select>
        </label>
        {commodity === "copper" && (
          <label>Basis definition
            <select value={basisSource} onChange={(e) => setBasisSource(e.target.value as "f1f2" | "cash3m")}>
              <option value="f1f2">F1/F2 futures (Eq. 15)</option>
              <option value="cash3m">Cash vs 3-month forward</option>
            </select>
          </label>
        )}
        <label>Regression start
          <input type="date" min={bounds?.data_min} max={bounds?.data_max}
            value={start ?? bounds?.data_min ?? ""} onChange={(e) => setStart(e.target.value)} />
        </label>
        <label>Regression end
          <input type="date" min={bounds?.data_min} max={bounds?.data_max}
            value={end ?? bounds?.data_max ?? ""} onChange={(e) => setEnd(e.target.value)} />
        </label>
      </div>

      <details>
        <summary style={{ cursor: "pointer", color: "var(--text)", marginBottom: 8 }}>Advanced settings</summary>
        <div className="control-row">
          <label>I* trailing weeks <input type="number" min={4} max={156} value={trailingWeeks}
            onChange={(e) => setTrailingWeeks(Number(e.target.value))} /></label>
          <label>Newey-West bandwidth (weeks) <input type="number" min={4} max={156} value={nwBandwidth}
            onChange={(e) => setNwBandwidth(Number(e.target.value))} /></label>
          <label><input type="checkbox" checked={fixedScale} onChange={(e) => setFixedScale(e.target.checked)} /> Fixed axis scale</label>
        </div>
      </details>

      {isFetching && !data && <p>Loading…</p>}
      {error && <p className="error">{(error as Error).message}</p>}

      <PlotlyChart fig={data?.fig ?? null} height={600} />

      {data?.slopes && (
        <div className="metric-row">
          <MetricCard label="Slope at I/I*=1" value={data.slopes.slope_at_1} format={(v) => v.toFixed(2)} />
          <MetricCard label="Slope at I/I*=0.75" value={data.slopes["slope_at_0.75"]} format={(v) => v.toFixed(2)} />
          <MetricCard label="Convexity (diff)" value={data.slopes.diff} format={(v) => v.toFixed(2)} />
          <MetricCard label="R²" value={data.r2} format={(v) => v.toFixed(3)} />
        </div>
      )}
      {data && (
        <p className="caption">
          t = {data.slopes.t_at_1?.toFixed(2)} / {data.slopes["t_at_0.75"]?.toFixed(2)} / {data.slopes.t_diff?.toFixed(2)}
          {" "}(slope@1 / slope@0.75 / diff) &middot; {data.n_obs} weekly obs, {data.period_start} to {data.period_end}
        </p>
      )}
    </div>
  );
}
