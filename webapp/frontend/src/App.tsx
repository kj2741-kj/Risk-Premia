import { useEffect } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage";
import AssetClassPage from "./pages/AssetClassPage";
import FundamentalAnalysisPage from "./pages/FundamentalAnalysisPage";
import CrossAssetPage from "./pages/CrossAssetPage";
import ResearchPage from "./pages/ResearchPage";
import { warmBackend } from "./lib/api";

const NAV = [
  { to: "/", label: "Overview", end: true },
  { to: "/metals", label: "Metals" },
  { to: "/petroleum", label: "Petroleum" },
  { to: "/pen", label: "Power, Emissions & Nat Gas" },
  { to: "/ngl", label: "NGL" },
  { to: "/precious", label: "Precious Metals" },
  { to: "/agri", label: "Agriculture" },
  { to: "/fundamental-analysis", label: "Fundamental Analysis" },
  { to: "/cross-asset", label: "Cross-Asset Portfolio" },
  { to: "/research", label: "Research" },
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
        </div>
      </nav>

      <main className="content">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/metals" element={
            <AssetClassPage key="metals" assetClass="metals" label="Metals" products={["Copper", "Aluminium", "Lead", "Zinc"]} />
          } />
          <Route path="/petroleum" element={
            <AssetClassPage key="petroleum" assetClass="petroleum" label="Petroleum"
              products={["WTI Crude", "Brent Crude", "RBOB Gasoline", "Heating Oil"]} />
          } />
          <Route path="/pen" element={
            <AssetClassPage key="pen" assetClass="pen" label="Power, Emissions & Nat Gas"
              products={["Nat Gas Henry Hub", "TTF Natural Gas", "EUA Carbon"]} />
          } />
          <Route path="/ngl" element={
            <AssetClassPage key="ngl" assetClass="ngl" label="NGL"
              products={["Ethane", "Propane", "Butane", "Isobutane"]} />
          } />
          <Route path="/precious" element={
            <AssetClassPage key="precious" assetClass="precious" label="Precious Metals"
              products={["Gold", "Silver", "Platinum", "Palladium"]} />
          } />
          <Route path="/agri" element={
            <AssetClassPage key="agri" assetClass="agri" label="Agriculture"
              products={["Corn", "Wheat", "Soybean", "Soybean Oil", "Coffee", "Sugar No.11"]} />
          } />
          <Route path="/fundamental-analysis" element={<FundamentalAnalysisPage />} />
          <Route path="/cross-asset" element={<CrossAssetPage />} />
          <Route path="/research" element={<ResearchPage />} />
        </Routes>
      </main>
    </div>
  );
}
