import { Link } from "react-router-dom";
import MetricCard from "../components/MetricCard";

const DASHBOARD_LINKS = [
  { to: "/metals", name: "Metals", desc: "LME Copper, Aluminium, Lead, and Zinc. Momentum, Carry, and Value strategies." },
  { to: "/energy", name: "Energy", desc: "WTI, Brent, RBOB, Heating Oil, Nat Gas. Momentum, Carry, Value." },
  { to: "/precious", name: "Precious Metals", desc: "Gold, Silver, Copper (CME), Platinum, Palladium. Momentum, Carry, Value." },
  { to: "/ngl", name: "NGL / Refined", desc: "Ethane, Propane, Butane, Isobutane. Momentum, Carry, Value." },
];

export default function HomePage() {
  return (
    <div className="page">
      <h1>Risk Premia</h1>
      <p className="tab-caption">
        Systematic Momentum, Carry, and Value risk premia across LME metals, energy, precious metals,
        and refined products, developed as supervised research with Prof. Ilia Bouchouev.
      </p>

      <div className="section-header">What This Project Is</div>
      <p className="tab-caption">
        This project is a systematic framework that decomposes commodity futures returns into three
        economically distinct, near-uncorrelated risk premia: <strong>Momentum</strong> (trend persistence),{" "}
        <strong>Carry</strong> (curve shape and roll yield), and <strong>Value</strong> (mean-reversion to a
        long-run anchor), combined into an equal-weight portfolio. The central result from the metals pilot
        on Copper and Aluminium is that three orthogonal sleeves of similar stand-alone Sharpe ratio combine
        into a portfolio whose risk-adjusted return materially exceeds any single sleeve, while roughly
        halving drawdown.
      </p>
      <p className="tab-caption">
        The framework was first validated on LME Copper and Aluminium, then extended, using the same three
        strategies in a deliberately simplified form (no CTA-paper trend, no structural anchors, no
        walk-forward out-of-sample testing yet), to oil and energy, precious metals, and refined NGL products.
      </p>

      <div className="section-header">Methodology (Same Convention Across Every Asset Class)</div>
      <div className="metric-row">
        <MetricCard label="PnL Basis" value={1} format={() => "F1_continuous"} />
        <MetricCard label="Sharpe Convention" value={1} format={() => "Active-Day"} />
        <MetricCard label="Transaction Costs" value={1} format={() => "On F1_raw"} />
      </div>
      <p className="tab-caption">
        Ratio back-adjusted continuous front-month series. Signals read raw prices (F1_raw); PnL always
        realises on F1_continuous. Sharpe is annualised mean and standard deviation of daily returns, scaled
        by the square root of 252 and computed over days the strategy actually holds a position, so flat
        days do not dilute the ratio. Round-trip cost = |&Delta;position| &times; (bps/10000/2) &times; F1_raw,
        charged at every position change on the real traded price, not the adjusted series.
      </p>
      <p className="tab-caption">
        Execution timing follows two conventions: <strong>Same-Day</strong>, where position(t) = signal(t&minus;1),
        and <strong>Lag-1</strong>, where position(t) = signal(t&minus;2), one additional day of delay with no
        look-ahead bias in either case. Which convention performs better is strategy-specific and is re-checked
        for every asset class rather than assumed.
      </p>

      <div className="section-header">Conclusion</div>
      <p className="tab-caption">
        The diversification thesis holds on every metal tested to date: combining three economically distinct
        premia consistently outperforms any single sleeve on a risk-adjusted basis, with materially lower
        drawdown. Optimal parameters are asset-specific rather than a single template; each new product is
        assigned its own momentum speed, carry variant, and value anchor, selected from its own data using the
        same methodology throughout. The framework has since been extended to genuinely different asset
        classes, including energy and refined products, to test whether the same three-premia structure holds
        outside metals.
      </p>

      <div className="section-header">Explore the Dashboards</div>
      <p className="tab-caption">
        Each asset class below has its own Momentum, Carry, Value, Comparison, and Portfolio tabs.
      </p>
      <div className="control-row" style={{ flexWrap: "wrap" }}>
        {DASHBOARD_LINKS.map((d) => (
          <div key={d.to} style={{ flex: "1 1 220px", border: "1px solid var(--panel-border)", borderRadius: 4, padding: 14 }}>
            <strong style={{ display: "block", marginBottom: 6 }}>{d.name}</strong>
            <Link to={d.to} className="nav-link" style={{ padding: 0, display: "inline-block", marginBottom: 8 }}>
              Open {d.name} &rarr;
            </Link>
            <p className="tab-caption" style={{ margin: 0 }}>{d.desc}</p>
          </div>
        ))}
      </div>

      <p className="caption" style={{ marginTop: 24 }}>
        Data sources: LME futures curves (F1-F27), NYMEX, ICE, and COMEX futures curves, and LME Cash and
        3-Month prices. This is a research prototype for academic purposes; all backtests are in-sample
        unless otherwise stated, and nothing here constitutes investment advice.
      </p>
    </div>
  );
}
