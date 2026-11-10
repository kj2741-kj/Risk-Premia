p = "audit_v8.py"
s = open(p, encoding="utf-8").read()
def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80]); s = s.replace(a, b)
rep('"Energy including", "six buckets", "fifteen", "Soybean Oil") if s in main]', '"Energy including", "all six buckets", "six bucket portfolios", "six-bucket", "six products", "fifteen", "Soybean Oil, Coffee") if s in main]')
rep('keys_ = [NMAP.get(r[0], r[0].rstrip("*")) for r in prow]', 'keys_ = [NMAP.get(r[0].rstrip("*"), r[0].rstrip("*")) if r[0].rstrip("*") in NMAP else NMAP.get(r[0], r[0].rstrip("*")) for r in prow]')
open(p, "w", encoding="utf-8").write(s)
print("ok")
