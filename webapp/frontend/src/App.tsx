import { NavLink, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage";
import AssetClassPage from "./pages/AssetClassPage";
import ComingSoonPage from "./pages/ComingSoonPage";

const NAV = [
  { to: "/", label: "Overview", end: true },
  { to: "/metals", label: "Metals" },
  { to: "/energy", label: "Energy" },
  { to: "/precious", label: "Precious Metals" },
  { to: "/ngl", label: "NGL / Refined" },
  { to: "/fundamental-analysis", label: "Fundamental Analysis" },
];

export default function App() {
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
            <AssetClassPage assetClass="metals" label="Metals" products={["Copper", "Aluminium", "Lead", "Zinc"]} />
          } />
          <Route path="/energy" element={
            <AssetClassPage assetClass="energy" label="Energy"
              products={["WTI Crude", "Brent Crude", "RBOB Gasoline", "Heating Oil", "Nat Gas", "Singapore Gasoil", "Fuel Oil"]} />
          } />
          <Route path="/precious" element={
            <AssetClassPage assetClass="precious" label="Precious Metals"
              products={["Gold", "Silver", "Copper (CME)", "Platinum", "Palladium"]} />
          } />
          <Route path="/ngl" element={
            <AssetClassPage assetClass="ngl" label="NGL / Refined"
              products={["Ethane", "Propane", "Butane", "Isobutane", "Ethylene", "Propylene"]} />
          } />
          <Route path="/fundamental-analysis" element={
            <ComingSoonPage title="Fundamental Analysis" note="GHR inventory-vs-basis spline tab, added in Phase 6." />
          } />
        </Routes>
      </main>
    </div>
  );
}
