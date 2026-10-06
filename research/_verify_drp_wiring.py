"""Verify Phase 2 wiring (research/cross_asset_engine.py's new combine_method
param on asset_class_four_row and asset_class_ew_portfolio) against real
data: (1) equal_weight path still runs and produces sane numbers (structural
regression check -- the branch itself is untouched code, just moved under an
if), (2) dynamic_risk_parity runs end-to-end at both the product level and
the style level, (3) the two layers combine independently in all 4
permutations, (4) DRP's combined series is finite/sane and its metrics are
in a plausible range relative to EW's own."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "configs"))

from cross_asset_engine import asset_class_ew_portfolio, asset_class_four_row
from run_regime_table import _metrics

AC = "metals"  # smallest/fastest asset class (4 products), good for a wiring smoke test


def show(label, series):
    # _metrics() (research/run_regime_table.py) already returns ret/vol/mdd
    # pre-scaled to percent -- do not multiply by 100 again here.
    m = _metrics(series)
    print(f"  {label:45s} ret={m['ret']:6.2f}%  vol={m['vol']:6.2f}%  "
          f"ir={m['ir']:6.3f}  mdd={m['mdd']:7.2f}%  n={len(series)}")


print(f"=== Asset class: {AC} ===\n")

print("--- 1. Product-level EW, Style-level EW (baseline, must match pre-Phase-2 behavior) ---")
g4_ew, n4_ew = asset_class_four_row(AC, combine_method="equal_weight")
g_ew_ew, n_ew_ew = asset_class_ew_portfolio(g4_ew, n4_ew, combine_method="equal_weight")
for style in n4_ew:
    show(style, n4_ew[style])
show("EW Portfolio (product=EW, style=EW)", n_ew_ew)
print()

print("--- 2. Product-level DRP, Style-level EW ---")
g4_drp, n4_drp = asset_class_four_row(AC, combine_method="dynamic_risk_parity")
g_drp_ew, n_drp_ew = asset_class_ew_portfolio(g4_drp, n4_drp, combine_method="equal_weight")
for style in n4_drp:
    show(style, n4_drp[style])
show("Portfolio (product=DRP, style=EW)", n_drp_ew)
print()

print("--- 3. Product-level EW, Style-level DRP ---")
g_ew_drp, n_ew_drp = asset_class_ew_portfolio(g4_ew, n4_ew, combine_method="dynamic_risk_parity")
show("Portfolio (product=EW, style=DRP)", n_ew_drp)
print()

print("--- 4. Product-level DRP, Style-level DRP (both layers) ---")
g_drp_drp, n_drp_drp = asset_class_ew_portfolio(g4_drp, n4_drp, combine_method="dynamic_risk_parity")
show("Portfolio (product=DRP, style=DRP)", n_drp_drp)
print()

print("--- 5. sanity assertions ---")
import numpy as np
for name, s in [("EW/EW", n_ew_ew), ("DRP/EW", n_drp_ew), ("EW/DRP", n_ew_drp), ("DRP/DRP", n_drp_drp)]:
    s_clean = s.dropna()  # a couple of leading NaN is expected/documented (combine_cross_asset's
                           # cumsum-diff first-row artifact) -- same convention _metrics() itself uses
    assert len(s) > 1000, f"{name}: suspiciously short series ({len(s)})"
    assert len(s) - len(s_clean) <= 5, f"{name}: unexpectedly many NaN ({len(s) - len(s_clean)})"
    assert np.isfinite(s_clean).all(), f"{name}: non-finite values present after dropping leading NaN"
    assert s_clean.std() > 0, f"{name}: zero variance -- something collapsed"
print("PASS: all 4 permutations produced finite (post-dropna), non-degenerate series\n")

print("--- 6. invalid combine_method raises cleanly ---")
try:
    asset_class_four_row(AC, combine_method="bogus")
    raise SystemExit("FAIL: expected ValueError")
except ValueError as e:
    print(f"  asset_class_four_row: {e}")
try:
    asset_class_ew_portfolio(g4_ew, n4_ew, combine_method="bogus")
    raise SystemExit("FAIL: expected ValueError")
except ValueError as e:
    print(f"  asset_class_ew_portfolio: {e}")
print("PASS\n")

print("ALL CHECKS PASSED")
