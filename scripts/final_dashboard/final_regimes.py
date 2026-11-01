"""Regime windows used by the Final Research Dashboard pipeline only (analyze_v2.py, analyze_twopair.py, build_final_dashboard_v2.py).
Decided 2026-10-12: three regimes. Dates do not overlap (R2 ends 31 Dec 2021, R3 starts 1 Jan 2022). research/regimes.py (four regimes,
used by run_regime_table.py and the Streamlit apps) is left unchanged. REPORT_START is still imported from there."""
REGIMES = [("R1_2011_2016", "2011-01-01", "2016-12-31"),
           ("R2_2017_2021", "2017-01-01", "2021-12-31"),
           ("R3_2022_2026", "2022-01-01", "2026-12-31")]
LABELS = {"r1": "2011-2016", "r2": "2017-2021", "r3": "2022-2026"}
