import { useCallback, useState } from "react";
import MomentumTab from "../components/MomentumTab";
import CarryTab from "../components/CarryTab";
import ValueTab from "../components/ValueTab";
import SkewnessTab from "../components/SkewnessTab";
import ComparisonTab from "../components/ComparisonTab";
import PortfolioTab from "../components/PortfolioTab";
import { setReturnBasis, type SeriesJson } from "../lib/api";
import { BasisContext } from "../lib/basis";

const TABS = ["Momentum", "Carry", "Value", "Skewness", "Comparison", "Portfolio"] as const;
type Tab = (typeof TABS)[number];

interface AssetClassPageProps {
  assetClass: string;
  label: string;
  products: string[];
  hidePortfolio?: boolean;
}

export default function AssetClassPage({ assetClass, label, products, hidePortfolio }: AssetClassPageProps) {
  const [product, setProduct] = useState(products[0]);
  const [geometric, setGeometric] = useState(true);   // Streamlit default: Geometric (% return)
  setReturnBasis(geometric);
  const [tab, setTab] = useState<Tab>("Momentum");
  const [groups, setGroups] = useState<Record<string, Record<string, SeriesJson>>>({
    Momentum: {}, Carry: {}, Value: {}, Skewness: {},
  });

  // Each tab fires several real pandas computations on mount. Mounting all
  // five at once (even hidden) means they all fire concurrently the moment
  // this page loads -- fine on a real machine, but on a resource-constrained
  // backend (single shared CPU core) that pile-up makes the tab you're
  // actually looking at slower, not faster. Mount a tab only the first time
  // it's opened, then keep it mounted (via display:none) so revisiting is
  // instant without re-fetching.
  const [visitedTabs, setVisitedTabs] = useState<Set<Tab>>(new Set(["Momentum"]));
  const selectTab = useCallback((t: Tab) => {
    setTab(t);
    setVisitedTabs((prev) => (prev.has(t) ? prev : new Set(prev).add(t)));
  }, []);

  // Product switches reset the cross-tab overlay -- Comparison shouldn't mix
  // positions computed for two different products.
  const changeProduct = useCallback((p: string) => {
    setProduct(p);
    setGroups({ Momentum: {}, Carry: {}, Value: {}, Skewness: {} });
  }, []);

  return (
    <BasisContext.Provider value={{ geometric, setGeometric }}>
    <div className="page">
      <h1>{label} Risk Premia</h1>
      <div className="control-row">
        <label>
          Product
          <select value={product} onChange={(e) => changeProduct(e.target.value)}>
            {products.map((p) => <option key={p}>{p}</option>)}
          </select>
        </label>
        <label title="Arithmetic: position x dollar change of F1_continuous, equity = cumulative sum, in the product's native unit. Geometric: position x ratio-adjusted daily log return, compounded (equity = exp(cumsum) - 1, in %), the same convention the Portfolio tab uses. Applies to Momentum, Carry, Value, Skewness and Comparison.">
          Return basis
          <span style={{ display: "flex", gap: 14, textTransform: "none" }}>
            <label style={{ flexDirection: "row", alignItems: "center", gap: 6, textTransform: "none" }}>
              <input type="radio" checked={!geometric} onChange={() => setGeometric(false)} /> Arithmetic ($ PnL)
            </label>
            <label style={{ flexDirection: "row", alignItems: "center", gap: 6, textTransform: "none" }}>
              <input type="radio" checked={geometric} onChange={() => setGeometric(true)} /> Geometric (% return)
            </label>
          </span>
        </label>
      </div>

      <div className="tabs">
        {TABS.filter((t) => !(hidePortfolio && t === "Portfolio")).map((t) => (
          <button key={t} className={t === tab ? "tab active" : "tab"} onClick={() => selectTab(t)}>
            {t}
          </button>
        ))}
      </div>

      {visitedTabs.has("Momentum") && (
        <div style={{ display: tab === "Momentum" ? "block" : "none" }}>
          <MomentumTab assetClass={assetClass} product={product}
            onPositionsChange={(p) => setGroups((g) => ({ ...g, Momentum: p }))} />
        </div>
      )}
      {visitedTabs.has("Carry") && (
        <div style={{ display: tab === "Carry" ? "block" : "none" }}>
          <CarryTab assetClass={assetClass} product={product}
            onPositionsChange={(p) => setGroups((g) => ({ ...g, Carry: p }))} />
        </div>
      )}
      {visitedTabs.has("Value") && (
        <div style={{ display: tab === "Value" ? "block" : "none" }}>
          <ValueTab assetClass={assetClass} product={product}
            onPositionsChange={(p) => setGroups((g) => ({ ...g, Value: p }))} />
        </div>
      )}
      {visitedTabs.has("Skewness") && (
        <div style={{ display: tab === "Skewness" ? "block" : "none" }}>
          <SkewnessTab assetClass={assetClass} product={product}
            onPositionsChange={(p) => setGroups((g) => ({ ...g, Skewness: p }))} />
        </div>
      )}
      {visitedTabs.has("Comparison") && (
        <div style={{ display: tab === "Comparison" ? "block" : "none" }}>
          <ComparisonTab assetClass={assetClass} product={product} groups={groups} />
        </div>
      )}
      {visitedTabs.has("Portfolio") && (
        <div style={{ display: tab === "Portfolio" ? "block" : "none" }}>
          <PortfolioTab assetClass={assetClass} />
        </div>
      )}
    </div>
    </BasisContext.Provider>
  );
}
