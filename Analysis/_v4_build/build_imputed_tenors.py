"""Build the imputed-tenor dataset for the only two tenors with a missing-price window inside the 2012 sample that a Carry long pair depends on.
Same-grade fill, missing cells only (observed prices are never changed):
  Heating Oil F13, 2012-04-02 to 2012-04-27 (19 trading days): F13 = F12 + s, s = mean of (F13 - F12) over March 2012 (the month before the gap), in cents/gal.
      In April 2012 F13 is the May 2013 contract, the first month with the ULSD grade (CME notice of April 2012); no premium is added because the only
      evidence for it comes from after the gap (look-ahead).
  Isobutane F14, 2013-03-01 to 2013-03-20 (14 trading days): F14 = F13 + s, s = mean of (F14 - F13) over February 2013 (= 0.0 exactly, F14 repeats F13 on every day), $/gal.
Output: data/Imputed_Tenors/imputed_tenors_ho_isobutane.csv with the agreed schema. Run from anywhere; paths are relative to the repository root."""
import os, sys, importlib
import numpy as np, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [os.path.join(ROOT, p) for p in ("research", os.path.join("research", "configs"), "scripts")]
OUT_DIR = os.path.join(ROOT, "data", "Imputed_Tenors")
os.makedirs(OUT_DIR, exist_ok=True)

SPECS = [  # product label, config module, product key, leg 1, leg 2, neighbour tenor, gap window, spread-estimation window, unit
    ("HEATING_OIL", "energy", "HeatingOil", "F1", "F13", "F12", ("2012-04-02", "2012-04-27"), ("2012-03-01", "2012-03-31"), "cents/gal"),
    ("ISOBUTANE", "ngl", "Isobutane", "F2", "F14", "F13", ("2013-03-01", "2013-03-20"), ("2013-02-01", "2013-02-28"), "$/gal"),
]
frames, log = [], []
for label, mod, prod, leg1, leg2, nb, (g0, g1), (e0, e1), unit in SPECS:
    c = importlib.import_module(mod).load_curve(prod)
    s = float((c[leg2] - c[nb]).loc[e0:e1].dropna().mean())
    n_est = int((c[leg2] - c[nb]).loc[e0:e1].dropna().shape[0])
    gap = c.loc[g0:g1]
    miss = gap[gap[leg2].isna()]
    assert len(miss) == len(gap), "every day in the window must be a missing cell (nothing observed is overwritten)"
    assert miss[leg1].notna().all() and miss[nb].notna().all()
    imputed = miss[nb] + s
    df = pd.DataFrame({"date": miss.index.strftime("%Y-%m-%d"), "product": label, "leg_1_tenor": leg1, "leg_1_price": miss[leg1].values,
                       "leg_2_tenor": leg2, "leg_2_price_imputed": imputed.values,
                       "carry_spread_value": (miss[leg1] - imputed).values, "adjustment_applied": s, "flag_imputed": True})
    frames.append(df)
    # outside the window nothing is touched: the series equals the source everywhere else
    log.append(f"{label}: {len(df)} cells, {df.date.iloc[0]} to {df.date.iloc[-1]}; {leg2} = {nb} {s:+.5f} {unit} (mean of {n_est} days {e0} to {e1})")
out = pd.concat(frames, ignore_index=True)
path = os.path.join(OUT_DIR, "imputed_tenors_ho_isobutane.csv")
out.to_csv(path, index=False, float_format="%.6f")
print("\n".join(log)); print("rows", len(out), "->", path)
