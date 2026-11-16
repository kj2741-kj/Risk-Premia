"""Before / after the product-level netting (2026-11-15), 0930 basis, Full window from 2012 (and periods for the books).
Before = outputs/final_dashboard_0930_pre_netting/final_v3.json and the Classical JSON as committed (git HEAD~ of the netting commit, read from git);
after = the rebuilt outputs. Run from the repo root:  python scripts/final_dashboard/compare_netting.py [<git ref of the pre-netting Classical JSON>]"""
import json
import subprocess
import sys

import pandas as pd

ref = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
old = json.load(open("outputs/final_dashboard_0930_pre_netting/final_v3.json"))
new = json.load(open("outputs/final_dashboard_0930/final_v3.json"))
row = lambda W, w, n: next(r for r in W[w] if r["name"] == n)
pd.set_option("display.width", 250)

print("=== 1. Bucket portfolios, Full 2012-2026 (strategy rows unchanged by construction) ===")
t = []
for k, tab in new["tabs"].items():
    for n in ("EW PORT", "Inverse Vol"):
        a, b = row(old["tabs"][k]["windows"], "full", n), row(tab["windows"], "full", n)
        t.append(dict(bucket=tab["label"], row=n, ir_before=a["ir"], ir_after=b["ir"], d_ir=round(b["ir"] - a["ir"], 3), ret_before=a["ret"], ret_after=b["ret"], vol_after=b["vol"], mdd_before=a["mdd"], mdd_after=b["mdd"]))
    for n in ("Momentum", "Carry", "CarryMom", "Value", "Skewness"):
        assert row(old["tabs"][k]["windows"], "full", n) == row(tab["windows"], "full", n), (k, n)
print(pd.DataFrame(t).to_string(index=False))

print("\n=== 2. Product EW PORT (5 strategies of one product), Full ===")
t = []
for pk, d in new["products"].items():
    a, b = old["products"][pk]["EW PORT"]["full"], d["EW PORT"]["full"]
    t.append(dict(product=pk.split("|")[1], ir_before=a["ir"], ir_after=b["ir"], d_ir=round(b["ir"] - a["ir"], 3), ret_before=a["ret"], ret_after=b["ret"]))
print(pd.DataFrame(t).sort_values("d_ir", ascending=False).to_string(index=False))

print("\n=== 3. Seven-bucket book and By Style, IR by period ===")
t = []
for sec in ("combined", "bystyle"):
    for r in new[sec]["windows"]["full"]:
        if r["name"].startswith("Reference") or r["name"] in ("Momentum", "Carry", "CarryMom", "Value", "Skewness"):
            continue
        d = dict(book=sec, row=r["name"])
        for w in ("full", "p1", "p2", "p3", "y26"):
            d[w + "_before"] = row(old[sec]["windows"], w, r["name"])["ir"]
            d[w + "_after"] = row(new[sec]["windows"], w, r["name"])["ir"]
        d["mdd_before"], d["mdd_after"] = row(old[sec]["windows"], "full", r["name"])["mdd"], r["mdd"]
        t.append(d)
print(pd.DataFrame(t).to_string(index=False))

print("\n=== 4. Cross-pairs (EW), Full IR: best five after ===")
t = [dict(pair=r["name"], ir_before=row(old["crosspair"]["EW"], "full", r["name"])["ir"], ir_after=r["ir"]) for r in new["crosspair"]["EW"]["full"]]
print(pd.DataFrame(t).sort_values("ir_after", ascending=False).head(5).to_string(index=False))
d = pd.DataFrame(t); print("mean change in cross-pair EW IR:", round((d.ir_after - d.ir_before).mean(), 3))

print("\n=== 5. Classical and Classical + New gen Energy, Full ===")
for key in ("classical", "classical_ng"):
    o = json.loads(subprocess.run(["git", "show", f"{ref}:Analysis/_classical_build/{key}_0930.json"], capture_output=True, text=True).stdout)
    n = json.load(open(f"Analysis/_classical_build/{key}_0930.json"))
    t = []
    for r in n["windows"]["full"]:
        if r["name"].startswith("Reference") or r["name"].startswith("By Style: ") and r["name"][10:] in ("Momentum", "Carry", "CarryMom", "Value", "Skewness"):
            continue
        a = row(o["windows"], "full", r["name"])
        t.append(dict(row=r["name"], ir_before=a["ir"], ir_after=r["ir"], d_ir=round(r["ir"] - a["ir"], 3), mdd_before=a["mdd"], mdd_after=r["mdd"]))
    print(n["label"]); print(pd.DataFrame(t).to_string(index=False))
