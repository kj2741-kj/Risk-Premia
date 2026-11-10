"""One-off patch (2026-11-10): the research dashboard's liquidity statements follow the CME plus ICE liquidity file (scripts/liquidity_ngl_ice_1110.py)."""
p = "scripts/final_dashboard/build_final_dashboard_v3.py"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:100])
    s = s.replace(a, b)


rep('''_liq = {r["product"]: r for r in csv.DictReader(open(R / "Analysis/Liquidity_Cal2025_results.csv", encoding="utf8"))}''',
    '''_liq = {r["product"]: r for r in csv.DictReader(open(R / "Analysis/Liquidity_Cal2025_results.csv", encoding="utf8"))}
# Isobutane (hidden from every output on 2026-11-09): its liquidity figures follow the CME plus ICE file (the earlier CME-only figures were about 10 lots a day and 156 days)
ISO_TXT = (f"its 12-month strip averaged about {float(_liq['Isobutane']['adv_strip']):.0f} lots a day on CME and ICE together in Calendar 2025, it printed on {float(_liq['Isobutane']['share_days_print']) * 100:.0f}% of days, "
           f"and a USD 1 million one-sigma position equals about {float(_liq['Isobutane']['L_strip']):.0f} days of its risk turnover.")''')
rep("because it is the least liquid product in the data set: its 12-month strip averaged about 10 lots a day in Calendar 2025 and printed on 13% of days. Agriculture =", "because it is the least liquid product in the data set: \" + ISO_TXT + \" Agriculture =")
rep("NGL volume is the CME half only.", "NGL volume is CME plus ICE for Ethane, Propane, Butane, Isobutane and Natural Gasoline (the ICE contracts are in the 10 November 2026 download); Naphtha is one Bloomberg series that is not split by exchange.")
open(p, "w", encoding="utf-8").write(s)
print("patched build_final_dashboard_v3.py")
