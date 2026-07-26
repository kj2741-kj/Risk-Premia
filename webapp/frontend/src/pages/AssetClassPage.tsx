import { useCallback, useState } from "react";
import MomentumTab from "../components/MomentumTab";
import CarryTab from "../components/CarryTab";
import ValueTab from "../components/ValueTab";
import ComparisonTab from "../components/ComparisonTab";
import type { SeriesJson } from "../lib/api";

const TABS = ["Momentum", "Carry", "Value", "Comparison", "Portfolio"] as const;
type Tab = (typeof TABS)[number];

interface AssetClassPageProps {
  assetClass: string;
  label: string;
  products: string[];
}

export default function AssetClassPage({ assetClass, label, products }: AssetClassPageProps) {
  const [product, setProduct] = useState(products[0]);
  const [tab, setTab] = useState<Tab>("Momentum");
  const [groups, setGroups] = useState<Record<string, Record<string, SeriesJson>>>({
    Momentum: {}, Carry: {}, Value: {},
  });

  // Product switches reset the cross-tab overlay -- Comparison shouldn't mix
  // positions computed for two different products.
  const changeProduct = useCallback((p: string) => {
    setProduct(p);
    setGroups({ Momentum: {}, Carry: {}, Value: {} });
  }, []);

  return (
    <div className="page">
      <h1>{label} Risk Premia</h1>
      <div className="control-row">
        <label>
          Product
          <select value={product} onChange={(e) => changeProduct(e.target.value)}>
            {products.map((p) => <option key={p}>{p}</option>)}
          </select>
        </label>
      </div>

      <div className="tabs">
        {TABS.map((t) => (
          <button key={t} className={t === tab ? "tab active" : "tab"} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>

      <div style={{ display: tab === "Momentum" ? "block" : "none" }}>
        <MomentumTab assetClass={assetClass} product={product}
          onPositionsChange={(p) => setGroups((g) => ({ ...g, Momentum: p }))} />
      </div>
      <div style={{ display: tab === "Carry" ? "block" : "none" }}>
        <CarryTab assetClass={assetClass} product={product}
          onPositionsChange={(p) => setGroups((g) => ({ ...g, Carry: p }))} />
      </div>
      <div style={{ display: tab === "Value" ? "block" : "none" }}>
        <ValueTab assetClass={assetClass} product={product}
          onPositionsChange={(p) => setGroups((g) => ({ ...g, Value: p }))} />
      </div>
      <div style={{ display: tab === "Comparison" ? "block" : "none" }}>
        <ComparisonTab assetClass={assetClass} product={product} groups={groups} />
      </div>
      {tab === "Portfolio" && (
        <div className="tab-panel">
          <p className="tab-caption">Portfolio tab — coming in Phase 5 (project plan Checkpoint 2).</p>
        </div>
      )}
    </div>
  );
}
