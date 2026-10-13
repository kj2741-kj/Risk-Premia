"""Apply the external-fact corrections found by the internet verification pass (2026-10-13) to the asset-class text modules. Run once, after the agent that owns those modules has finished.
Each replacement asserts that the old text is present exactly once. Sources: EIA Today in Energy 64724 (propane exports first above 2 million b/d in November 2024) and 68244 (April 2026 record 2.1 million b/d);
Harbor Aluminum and MetalCharts (aluminium record about $4,073 in March 2022; the 7 March day is not confirmed); Erbakir, Discovery Alert, Bloomberg, Investing News, Tacto (copper peak 9 to 10 September 2026, sources differ by contract and time);
EIA Today in Energy 9490 (Henry Hub 2012: high, not record, storage); Barchart and Reuters (arabica record about $4.30 in February 2025 on the most active contract; no source found for a $4.38 record on 23 October 2025)."""
import os, re, sys
S = os.path.dirname(os.path.abspath(__file__))
EDITS = {
    "text_ngl.py": [("passed 2 million b/d for the first time in April 2026, at a record 2.1 million b/d (EIA)",
                     "reached a record 2.1 million b/d in April 2026 (EIA; exports first topped 2 million b/d in November 2024)")],
    "text_metals.py": [("about $4,073 on 7 March", "about $4,073 in March"),
                       ("about $14,875 on 10 September", "about $14,800 to $14,875 on 9 to 10 September")],
    "text_energy.py": [("record storage", "high storage")],
    "text_agri.py": [("(market sources put the record for the most active contract at about $4.30 that month and the later all-time high at $4.38 on 23 October 2025)",
                      "(our series is the front-month, March, contract; the most active contract set its record at about $4.30 that month)")],
}
for fn, pairs in EDITS.items():
    p = os.path.join(S, fn); s = open(p, encoding="utf8").read()
    for old, new in pairs:
        n = s.count(old)
        if n != 1:
            print(f"SKIP {fn}: {n} matches for: {old[:70]}"); continue
        s = s.replace(old, new); print(f"OK   {fn}: {old[:60]}")
    open(p, "w", encoding="utf8").write(s)
