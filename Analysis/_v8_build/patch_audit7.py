p = r"C:\Users\Kartavya\Desktop\NYU\Summer\Risk Premia\Analysis\_v8_build\audit_v8.py"
s = open(p, encoding="utf8").read()


def r(a, b, c=1):
    global s
    assert s.count(a) == c, (s.count(a), a[:90])
    s = s.replace(a, b)


r('LAB = {"Metals": "metals", "Petroleum": "petroleum", "Gas and Emissions": "pen", "NGL": "ngl", "Precious Metals": "precious", "Agriculture": "agri"}',
  'LAB = {"Metals": "metals", "Petroleum": "petroleum", "Gas and Emissions": "pen", "NGL": "ngl", "Precious Metals": "precious", "Agriculture": "agri", "US Power": "power"}')
r('re.match(r"Table A\\d+\\. US Power \\(Standalone\\): ", x)', 're.match(r"Table A\\d+\\. US Power: ", x)')
r("check(f\"C. fifteen-pair table == dataset ({len(rows) - 1} pairs, both constructions)\", mm == 0 and len(rows) == 16)", "check(f\"C. 21-pair table == dataset ({len(rows) - 1} pairs, both constructions)\", mm == 0 and len(rows) == 22)")
r('SHORT = {"Metals": "metals", "Petroleum": "petroleum", "Gas and Emissions": "pen", "NGL": "ngl", "Precious Metals": "precious", "Agriculture": "agri"}',
  'SHORT = {"Metals": "metals", "Petroleum": "petroleum", "Gas and Emissions": "pen", "NGL": "ngl", "Precious Metals": "precious", "Agriculture": "agri", "US Power": "power"}')
r('check(f"C. correlation-section pair table (EW PORT correlation and both IRs) == dataset ({len(corr_tab) - 1} pairs)", mm == 0 and len(corr_tab) == 16)',
  'check(f"C. correlation-section pair table (EW PORT correlation and both IRs) == dataset ({len(corr_tab) - 1} pairs)", mm == 0 and len(corr_tab) == 22)')
r('    b = LAB[r[0]]; mat = D["corr"]["within"][b]', '    b = LAB[r[0].split(" (from")[0]]; mat = D["corr"]["within"][b]')
r('check("G. fifteen pair series recomputed equal the dataset (both constructions)", bad_ == 0 and len(ps) == 15, f"{bad_} differ")', 'check("G. 21 pair series recomputed equal the dataset (both constructions)", bad_ == 0 and len(ps) == 21, f"{bad_} differ")')
r('check("F. the dataset has 27 products in six buckets"', 'check("F. the dataset has the seven-bucket book from 2015-01-07 and 27 products in the six research bucket tabs", D["meta"]["keys"][-1] == "power" and D["bystyle"]["common_first"] == "2015-01-07" and "7 January 2015" in text and "F. "', ) if False else None
open(p, "w", encoding="utf8").write(s)
print("ok")
