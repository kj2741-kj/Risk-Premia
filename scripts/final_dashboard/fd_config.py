"""Shared settings of the v3 research-dashboard pipeline (2026-10-31): which data folder / cutoff a run uses, and the bucket definitions.
A run is identified by a TAG:
  "0930": data/Prices_0930 (29-Oct pull merged into the 24-Sep history, every sheet cut at 2026-09-30)  -> outputs/final_dashboard_0930, Analysis/*_0930.html
  "1029": data/Prices_1029_merged (the same merge, nothing cut: prices to 2026-10-29, LME and NGL to 10-28) -> outputs/final_dashboard_1029, Analysis/*_1029.html
compute_products_v3.py takes the tag from RP_PRICES_DIR (it refuses any other folder); every later script takes it from the env var FD_TAG (default "0930", so the
committed 0930 pages stay reproducible) and checks it against outputs/final_dashboard_<tag>/run_info.json."""
import json
import os
from pathlib import Path

TAGS = {
    "0930": dict(prices_dir="Prices_0930", cutoff="2026-09-30", long="30 September 2026", short="30 September",
                 data_line="Prices run through 2026-09-30 for all six buckets (the 29-Oct Bloomberg pull extends the 24-Sep file; every sheet is cut at 30 September).",
                 change_line="<b>Data:</b> the 29-Oct Bloomberg pull is merged into the 24-Sep history (overlap identical) and cut at 30 September 2026, seven trading days later than the previous version (23 September). P1 and P2 results of the unchanged buckets are identical to the previous version; Full and P3 differ only by those seven days.",
                 last_txt="30 September 2026 (the last price date)"),
    "1029": dict(prices_dir="Prices_1029_merged", cutoff="2026-10-29", long="29 October 2026", short="29 October",
                 data_line="Prices run through 2026-10-29 for all six buckets (LME and NGL through 2026-10-28): the 29-Oct Bloomberg pull merged into the 24-Sep history, nothing cut.",
                 change_line="<b>Data:</b> the 29-Oct Bloomberg pull is merged into the 24-Sep history (overlap identical) and used in full: prices through 29 October 2026 (LME and NGL through 28 October), about 26 trading days beyond the 23 September data of the previous version. The 30-September cut of the same dashboard is Final_Research_Dashboard_2012_0930.html.",
                 last_txt="29 October 2026 (the last price date; LME and NGL end on 28 October)"),
}

# bucket key -> (label, [(asset-class module, product), ...]); the module is where the product's config and series live
BUCKETS = {
    "metals": ("Metals", [("metals", p) for p in ["Copper", "Aluminium", "Lead", "Zinc"]]),
    "petroleum": ("Petroleum", [("energy", p) for p in ["WTI", "Brent", "RBOB", "HeatingOil"]]),
    "pen": ("Power, Emissions and Nat Gas", [("energy", "NatGas"), ("emissions", "TTF"), ("emissions", "EUA")]),
    "ngl": ("NGL", [("ngl", p) for p in ["Ethane", "Propane", "Butane", "Isobutane"]]),
    "precious": ("Precious", [("precious", p) for p in ["Gold", "Silver", "Platinum", "Palladium"]]),
    "agri": ("Agriculture", [("agri", p) for p in ["Corn", "Wheat", "Soybean", "SoybeanOil", "Coffee", "Sugar"]]),
}
PAGE_CSS = """body{font-family:Calibri,Arial,sans-serif;margin:0;background:#fff;color:#1f2d3d}@media(prefers-color-scheme:dark){body{background:#12171d;color:#dfe5ec}th{background:#222b35!important}td,th{border-color:#333d49!important}}
.wrap{max-width:1100px;margin:0 auto;padding:20px 16px}h1{font-size:24px;margin:0 0 4px}h2{font-size:17px;margin:26px 0 4px}.note{color:#667;font-size:13px;margin:2px 0 8px}
.ts{overflow-x:auto}table{border-collapse:collapse;font-size:12.5px;width:100%}th,td{border:1px solid #d5dbe2;padding:4px 8px;text-align:right;white-space:nowrap}th{background:#e8ecf0}
td:first-child,th:first-child{text-align:left}.pos{color:#0a7d3c;font-weight:600}.neg{color:#b3261e;font-weight:600}"""
STYLES = ("Momentum", "Carry", "CarryMom", "Value", "Skewness")


def tag_from_prices_dir() -> str:
    d = os.environ.get("RP_PRICES_DIR")
    for t, c in TAGS.items():
        if c["prices_dir"] == d:
            return t
    raise SystemExit(f"RP_PRICES_DIR must be one of {[c['prices_dir'] for c in TAGS.values()]}, got {d!r}")


def current_tag() -> str:
    t = os.environ.get("FD_TAG", "0930")
    if t not in TAGS:
        raise SystemExit(f"FD_TAG must be one of {list(TAGS)}, got {t!r}")
    return t


def out_dir(tag: str) -> Path:
    return Path(f"outputs/final_dashboard_{tag}")


def check_run(tag: str) -> dict:
    info = json.load(open(out_dir(tag) / "run_info.json"))
    assert info["tag"] == tag, f"outputs/final_dashboard_{tag} was built with tag {info['tag']}"
    return info
