p = "audit_v8.py"
s = open(p, encoding="utf-8").read()


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:80])
    s = s.replace(a, b)


rep('BK = D["meta"]["keys"]                      # metals, petroleum, pen, ngl, precious, agri', 'BK = D["meta"]["keys"]                      # metals, petroleum, pen, ngl, precious, agri, softs')
rep('"Precious Metals": "precious", "Agriculture": "agri"}\nfails = []', '"Precious Metals": "precious", "Agriculture": "agri", "Softs": "softs"}\nfails = []')
rep('PN = {"Heating Oil": "HeatingOil", "Soybean Oil": "SoybeanOil", "Henry Hub": "NatGas", "UK Gas": "UKGas"}', 'PN = {"Heating Oil": "HeatingOil", "Soybean Oil": "SoybeanOil", "Henry Hub": "NatGas", "UK Gas": "UKGas", "Live Cattle": "LiveCattle", "Natural Gasoline": "NatGasoline"}')
rep('(Metals|Petroleum|Gas and Emissions|Precious Metals|NGL|Agriculture): (.+)', '(Metals|Petroleum|Gas and Emissions|Precious Metals|NGL|Agriculture|Softs): (.+)')
rep('# B. appendix tables of the six buckets', '# B. appendix tables of the seven buckets')
rep('not mism and cells == 298, f"{len(mism)}: {mism[:4]}")      # 303 before Isobutane was removed (five sleeve cells of its column)', 'not mism and cells == 341, f"{len(mism)}: {mism[:4]}")      # 7 buckets x 28 period cells + 29 products x 5 sleeves (298 for six buckets and 26 products)')
rep('check(f"C. fifteen-pair table == dataset ({len(rows) - 1} pairs, both constructions)", mm == 0 and len(rows) == 16)', 'check(f"C. twenty-one-pair table == dataset ({len(rows) - 1} pairs, both constructions)", mm == 0 and len(rows) == 22)')
rep('"Precious Metals": "precious", "Agriculture": "agri"}\nmm = 0\nfor r in corr_tab[1:]:', '"Precious Metals": "precious", "Agriculture": "agri", "Softs": "softs"}\nmm = 0\nfor r in corr_tab[1:]:')
rep('== dataset ({len(corr_tab) - 1} pairs)", mm == 0 and len(corr_tab) == 16)', '== dataset ({len(corr_tab) - 1} pairs)", mm == 0 and len(corr_tab) == 22)')
rep('check(f"D. Skewness correlation table correlations (six buckets) == dataset', 'check(f"D. Skewness correlation table correlations (seven buckets) == dataset')
rep('"Energy including") if s in main]', '"Energy including", "six buckets", "fifteen", "Soybean Oil") if s in main]')
rep('check(f"G. class statistics of all six buckets recomputed', 'check(f"G. class statistics of all seven buckets recomputed')
rep('check("G. fifteen pair series recomputed equal the dataset (both constructions)", bad_ == 0 and len(ps) == 15, f"{bad_} differ")', 'check("G. twenty-one pair series recomputed equal the dataset (both constructions)", bad_ == 0 and len(ps) == 21, f"{bad_} differ")')
rep('"SoybeanOil", "MISO OffPeak\\u2021"', '"SoybeanOil", "Live Cattle": "LiveCattle", "Natural Gasoline": "NatGasoline", "MISO OffPeak\\u2021"')
rep('badl == 0 and len(prow) == 33, f"{badl} differ")', 'badl == 0 and len(prow) == 36, f"{badl} differ")')
rep('# F. 26 products named in the buckets (27 before Isobutane was removed); sleeves\ncheck("F. the dataset has 26 products in six buckets", sum(len(D["tabs"][b]["products"]) for b in BK) == 26)', '# F. 29 products named in the seven buckets (26 in six buckets before the 10 November 2026 split and Natural Gasoline)\ncheck("F. the dataset has 29 products in seven buckets", sum(len(D["tabs"][b]["products"]) for b in BK) == 29)')
open(p, "w", encoding="utf-8").write(s)
print("audit patched")
