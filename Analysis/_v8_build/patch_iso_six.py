import re


def edit(path, pairs):
    s = open(path, encoding="utf8").read()
    for a, b in pairs:
        assert s.count(a) == 1, (path, s.count(a), a[:90])
        s = s.replace(a, b)
    open(path, "w", encoding="utf8").write(s); print("edited", path)


edit("rp.py", [('"ngl": ["Ethane", "Propane", "Butane", "Isobutane"], "precious"', '"ngl": ["Ethane", "Propane", "Butane"], "precious"')])

edit("build_v8.py", [
    ('assert [c.text for c in t13.rows[0].cells[1:]] == ["Ethane", "Propane", "Butane", "Isobutane"]\nadd_column(t13, "Naphtha", [""] * 5)', 'assert [c.text for c in t13.rows[0].cells[1:]] == ["Ethane", "Propane", "Butane", "Isobutane"]\ndelete_column(t13, 4)      # Isobutane is removed from every output (2026-11-09)\nadd_column(t13, "Naphtha", [""] * 5)'),
    ('("NGL", ["Propane", "Butane", "Ethane", "Naphtha", "Isobutane"])', '("NGL", ["Propane", "Butane", "Ethane", "Naphtha"])'),
    ('chk(len(allp) == 34, "34 liquidity products")', 'chk(len(allp) == 33, "33 liquidity products")'),
    ('(34 Products, Six Buckets and US Power)', '(33 Products, Six Buckets and US Power)'),
    ('_lab = "Results across 34 products."', '_lab = "Results across 33 products."'),
    ('"The table covers 34 products: the 27 of the six buckets,', '"The table covers 33 products: the 26 of the six buckets,'),
    ('assert "34 products" in nt and "Bloomberg series" in nt', 'assert "33 products" in nt and "Bloomberg series" in nt'),
    ('nt = nt.replace("EUA and TTF are converted from EUR at 1.1300",', 'nt = nt.replace("Isobutane printed on only 13% of days with a median daily volume of zero, which is what its very low x reflects. ", "")\nnt = nt.replace("EUA and TTF are converted from EUR at 1.1300",'),
    ("NGL has five products, with Naphtha added to the four Mont Belvieu products.", "NGL has four products (Ethane, Propane, Butane and Naphtha): Naphtha is added to the three Mont Belvieu products, and Isobutane, the least liquid product in the data set, is removed from every bucket, pair, correlation and table."),
    ("the liquidity section and table (34 products, with UK Gas, Naphtha and the US Power series)", "the liquidity section and table (33 products, with UK Gas, Naphtha and the US Power series)"),
    ("Version note (v8, 6 November 2026)", "Version note (v8, 10 November 2026)"),
    ('"v8 (6 November 2026) VERIFICATION_PLACEHOLDER"', '"v8 (10 November 2026) VERIFICATION_PLACEHOLDER"'),
    ('assert [c.text for c in tpi.rows[0].cells[1:]] == ["Ethane", "Propane", "Butane", "Isobutane", "Naphtha"]\n', 'assert [c.text for c in tpi.rows[0].cells[1:]] == ["Ethane", "Propane", "Butane", "Naphtha"]      # the NGL product table the Power table is cloned from has four products since Isobutane was removed\nadd_column(tpi, "", [""] * 5)      # the five Power series need five columns\n'),
])

# text_front8: the liquidity paragraph as rewritten for the 33-product table (taken from the committed version), and the NGL wording
head = open(r"C:\Users\Kartavya\AppData\Local\Temp\claude\acfa373b4c66489b\2d9f3014-23bd-44e2-ba96-1a4367c5782d\scratchpad\text_front8_head.py", encoding="utf8").read()
hi = head.index("def liquidity_paragraph():"); hj = head.index("    return s\n", hi) + len("    return s\n")
new_fn = head[hi:hj]
s = open("text_front8.py", encoding="utf8").read()
i = s.index("def liquidity_paragraph():"); j = s.index("    return s\n", i) + len("    return s\n")
s = s[:i] + new_fn + s[j:]
a = "Naphtha, added as the fifth product in v8, lifts the Equal Weight IR from {I(ew_4p['ir'])} (the four Mont Belvieu products)"
assert s.count(a) == 1
s = s.replace(a, "Naphtha, added as the fourth product in v8, lifts the Equal Weight IR from {I(ew_4p['ir'])} (the three Mont Belvieu products)")
open("text_front8.py", "w", encoding="utf8").write(s); print("edited text_front8.py")

edit("audit_v8.py", [
    ('badl == 0 and len(prow) == 34, f"{badl} differ")', 'badl == 0 and len(prow) == 33, f"{badl} differ")'),
    ('# F. 27 products named in the buckets; sleeves', '# F. 26 products named in the buckets (27 before Isobutane was removed); sleeves'),
    ('check("F. the dataset has 27 products in six buckets", sum(len(D["tabs"][b]["products"]) for b in BK) == 27)', 'check("F. the dataset has 26 products in six buckets", sum(len(D["tabs"][b]["products"]) for b in BK) == 26)'),
])
# the CHK_SOFT trial mode of facts.chk (collects every failing claim in one pass; never used for the final build)
s = open("facts.py", encoding="utf8").read()
a = 'def chk(cond, msg):\n    if not cond:\n        raise AssertionError("CLAIM FAILED: " + msg)\n'
assert s.count(a) == 1
s = s.replace(a, 'SOFT_FAILS = []\n\n\ndef chk(cond, msg):\n    if not cond:\n        if os.environ.get("CHK_SOFT"):      # trial build only\n            SOFT_FAILS.append(msg); return\n        raise AssertionError("CLAIM FAILED: " + msg)\n')
if not re.search(r"^import os|^import .*\bos\b", s, re.M): s = "import os\n" + s
open("facts.py", "w", encoding="utf8").write(s); print("edited facts.py")
b = open("build_v8.py", encoding="utf8").read()
if "SOFT_FAILS" not in b:
    b += "\nimport facts as _f\nif _f.SOFT_FAILS:\n    print(\"TRIAL BUILD: failing claims:\"); [print(\"  -\", m) for m in _f.SOFT_FAILS]\n"
    open("build_v8.py", "w", encoding="utf8").write(b); print("trial print added to build_v8.py")
