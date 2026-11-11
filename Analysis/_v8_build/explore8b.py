import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from facts3 import *
pd.set_option("display.width", 250)
W3 = ("p1", "p2", "p3")
f = lambda x: f"{x:+.2f}"
for v in ("ngl", "pen"):
    print("\n=====", v, MEMBERS[v])
    print("bucket sleeves IR full/p1/p2/p3 + stats")
    for k in SLEEVES + ["EW PORT", "Inverse Vol"]:
        s = st(v, k); print(f"  {k:12s} full {f(s['ir'])} ret {s['ret']:+.1f} vol {s['vol']:.1f} mdd {s['mdd']:.1f} | P {[f(x) for x in per(v, k)]}")
    print("4-sleeve (no Skewness) EW/IV:", f(st4(v, 'EW PORT')['ir']), f(st4(v, 'Inverse Vol')['ir']), [f(stats(PORT4[v][0], w)['ir']) for w in W3])
    print("products x sleeves IR (full) and P1/P2/P3")
    for (a, p) in MEMBERS[v]:
        row = {k: f(pst(a, p, k)['ir']) for k in SLEEVES}
        ew_p = ew_intersection([nets()[(a, p)][k] for k in SLEEVES])
        print(f"  {p:11s} {row} EW-of-5 {f(stats(ew_p)['ir'])}")
        for k in SLEEVES:
            print(f"        {k:9s} periods {[f(x) for x in pper(a, p, k)]}")
    print("skew legs (long% full, P3):", {p: (round(legs(a, p)['full']['long_pct']), round(legs(a, p)['p3']['long_pct'])) for a, p in MEMBERS[v]})
    # yearly log returns by bucket sleeve
    yl = pd.DataFrame({k: yearly_log(CS[v][k]) for k in SLEEVES}); print(yl.round(2).to_string())
    print("EW PORT yearly log", yearly_log(PORT[v][0]).round(2).to_dict())
