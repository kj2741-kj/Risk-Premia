import { useState } from "react";
import { reportUrl } from "../lib/api";

const REPORTS = [
  { slug: "final-research-dashboard-2012", label: "Final Research Dashboard (2012 start)" },
  { slug: "commodity-rankings", label: "Commodity Rankings" },
];

export default function ResearchPage() {
  const [slug, setSlug] = useState(REPORTS[0].slug);

  return (
    <div>
      <h1>Research</h1>
      <div className="nav-links" style={{ marginBottom: 12 }}>
        {REPORTS.map((r) => (
          <button
            key={r.slug}
            className={r.slug === slug ? "nav-link active" : "nav-link"}
            onClick={() => setSlug(r.slug)}
          >
            {r.label}
          </button>
        ))}
        <a className="nav-link" href={reportUrl(slug)} target="_blank" rel="noreferrer">
          Open full page
        </a>
      </div>
      <iframe
        key={slug}
        title={slug}
        src={reportUrl(slug)}
        style={{ width: "100%", height: "calc(100vh - 190px)", border: "1px solid #d5dbe2", borderRadius: 6 }}
      />
    </div>
  );
}
