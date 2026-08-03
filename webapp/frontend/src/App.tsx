import { useEffect } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage";
import AssetClassPage from "./pages/AssetClassPage";
import FundamentalAnalysisPage from "./pages/FundamentalAnalysisPage";
import { warmBackend } from "./lib/api";

const NAV = [
  { to: "/", label: "Overview", end: true },
  { to: "/metals", label: "Metals" },
  { to: "/energy", label: "Energy" },
  { to: "/precious", label: "Precious Metals" },
  { to: "/ngl", label: "NGL / Refined" },
  { to: "/fundamental-analysis", label: "Fundamental Analysis" },
];

export default function App() {
  useEffect(() => {
    warmBackend();
  }, []);

  return (
    <div className="app-shell">
      <nav className="top-nav">
        <span className="brand">Risk Premia</span>
        <div className="nav-links">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
              {n.label}
            </NavLink>
          ))}
          <span className="nav-link disabled" title="Not built yet — see project roadmap">
            Cross-Asset Portfolio (Coming Soon)
          </span>
        </div>
      </nav>

      <main className="content">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/metals" element={
            <AssetClassPage key="metals" assetClass="metals" label="Metals" products={["Copper", "Aluminium", "Lead", "Zinc"]} />
          } />
          <Route path="/energy" element={
            <AssetClassPage key="energy" assetClass="energy" label="Energy"
              products={["WTI Crude", "Brent Crude", "RBOB Gasoline", "Heating Oil", "Nat Gas"]} />
          } />
          <Route path="/precious" element={
            <AssetClassPage key="precious" assetClass="precious" label="Precious Metals"
              products={["Gold", "Silver", "Copper (CME)", "Platinum", "Palladium"]} />
          } />
          <Route path="/ngl" element={
            <AssetClassPage key="ngl" assetClass="ngl" label="NGL / Refined"
              products={["Ethane", "Propane", "Butane", "Isobutane"]} />
          } />
          <Route path="/fundamental-analysis" element={<FundamentalAnalysisPage />} />
        </Routes>
      </main>
    </div>
  );
}
