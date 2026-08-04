"""Verify Phase 3 wiring: cross_commodity_dynamic's new "dynamic_risk_parity"
combine_method (alongside existing "equal_weight"/"risk_parity"), and
cross_n_portfolio's new "dynamic_risk_parity" option (alongside existing
"equal_weight"). Uses Metals+Precious (smallest two asset classes) for
speed. Also confirms cross_commodity_portfolio()/cross_pair_portfolios()
(the fixed, validated reference forms) still run unchanged."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "configs"))

import numpy as np

from cross_asset_engine import (cross_commodity_dynamic, cross_commodity_portfolio,
                                 cross_n_portfolio, cross_pair_portfolios)
from run_regime_table import _metrics

ACS = ("metals", "precious")


def show(label, series):
    m = _metrics(series)
    print(f"  {label:30s} ret={m['ret']:6.2f}%  vol={m['vol']:6.2f}%  "
          f"ir={m['ir']:6.3f}  mdd={m['mdd']:7.2f}%  n={len(series)}")


print("=== 1. cross_commodity_dynamic: equal_weight / risk_parity / dynamic_risk_parity ===\n")
for method in ("equal_weight", "risk_parity", "dynamic_risk_parity"):
    g, n = cross_commodity_dynamic(asset_classes=ACS, combine_method=method)
    print(f"-- combine_method={method} --")
    show("Portfolio", n["Portfolio"])
print()

print("=== 2. cross_n_portfolio: equal_weight / dynamic_risk_parity ===\n")
for method in ("equal_weight", "dynamic_risk_parity"):
    g, n = cross_n_portfolio(asset_classes=ACS, combine_method=method)
    print(f"-- combine_method={method} --")
    show("Portfolio", n["Portfolio"])
print()

print("=== 3. sanity assertions on DRP outputs ===")
_, n_cc_drp = cross_commodity_dynamic(asset_classes=ACS, combine_method="dynamic_risk_parity")
_, n_cn_drp = cross_n_portfolio(asset_classes=ACS, combine_method="dynamic_risk_parity")
for name, s in [("cross_commodity_dynamic DRP", n_cc_drp["Portfolio"]), ("cross_n_portfolio DRP", n_cn_drp["Portfolio"])]:
    s_clean = s.dropna()
    assert len(s) > 1000, f"{name}: suspiciously short ({len(s)})"
    assert len(s) - len(s_clean) <= 10, f"{name}: unexpectedly many NaN ({len(s) - len(s_clean)})"
    assert np.isfinite(s_clean).all(), f"{name}: non-finite values"
    assert s_clean.std() > 0, f"{name}: zero variance"
print("PASS\n")

print("=== 4. invalid combine_method raises cleanly ===")
try:
    cross_commodity_dynamic(asset_classes=ACS, combine_method="bogus")
    raise SystemExit("FAIL: expected ValueError")
except ValueError as e:
    print(f"  cross_commodity_dynamic: {e}")
try:
    cross_n_portfolio(asset_classes=ACS, combine_method="bogus")
    raise SystemExit("FAIL: expected ValueError")
except ValueError as e:
    print(f"  cross_n_portfolio: {e}")
print("PASS\n")

print("=== 5. fixed reference forms (cross_commodity_portfolio / cross_pair_portfolios) still run ===")
cc_ref = cross_commodity_portfolio()
print(f"  cross_commodity_portfolio() rows: {list(cc_ref.keys())}")
assert "EW PORT" in cc_ref and "Risk Parity" in cc_ref
cp_ref = cross_pair_portfolios()
print(f"  cross_pair_portfolios() rows: {list(cp_ref.keys())}")
assert len(cp_ref) == 4
print("PASS\n")

print("ALL CHECKS PASSED")
