"""Writes data/Prices_0924/NGL_Futures_Updated_labels_corrected.xlsx: same data as NGL_Futures_Updated.xlsx (24-Sep pull), sheet names and
titles corrected to the verified product labels (same names the July file used, so the repo's NGL config works unchanged with this file)."""
import openpyxl
SRC="data/Prices_0924/NGL_Futures_Updated.xlsx"; DST="data/Prices_0924/NGL_Futures_Updated_labels_corrected.xlsx"
RENAME={"Propane Argus Far East C3":"Ethane Argus","Butane Argus C4":"Propane Argus","Ethane Argus":"Butane Argus",
        "Propane C3 CIF ARA":"Ethylene Argus","Isobutane Argus":"Isobutane Argus","Propylene Argus":"Propylene Argus"}
wb=openpyxl.load_workbook(SRC)
tmp={}
for ws in wb.worksheets:
    if ws.title in RENAME:
        tmp[ws.title]=ws; ws.title="__tmp__"+ws.title       # avoid name collisions while swapping
for old,ws in tmp.items():
    new=RENAME[old]; ws.title=new
    a1=ws["A1"].value
    if isinstance(a1,str) and a1.startswith(old):
        ws["A1"].value=new+a1[len(old):]
rd=wb["README"]
rows=[["NGL / Refined Products - Futures Curves (LABELS CORRECTED)",None],[None,None],["Generated","2026-09-24 14:45 (source: NGL_Futures_Updated.xlsx)"],["Start Date","20050101"],["End Date","20260923"],["Fields","PX_LAST"],["Timeout/ticker","12s + skip after 3 empties"],[None,None],
 ["CAP","Ethane Argus                   F1-F27"],["BAP","Propane Argus                  F1-F27"],["DAE","Butane Argus                   F1-F27"],["IBD","Isobutane Argus                F1-F27"],["PCW","Ethylene Argus                 F1-F27"],["PGP","Propylene Argus                F1-F27"],[None,None],
 ["CORRECTION NOTE",None],
 [None,"2026-10-11: the 2026-09-24 pull labelled the sheets CAP='Propane Argus Far East C3', BAP='Butane Argus C4', DAE='Ethane Argus', PCW='Propane C3 CIF ARA' (cyclically shifted). The price data are identical to the 2026-07 file under the July (verified) labels; sheet names and titles are corrected here, data untouched."],
 [None,"Verification against independent prices: BAP matches EIA Mont Belvieu propane spot (FRED DPROPANEMBTX, 2010-2026): median ratio 1.003, level correlation 0.995, 5-day change correlation 0.90, 2012 vs 2011 average -31% (EIA propane -32%). CAP is ethane: 2012 vs 2011 -47% (EIA ethane -48%), 24c/gal on 19-Dec-2012 (reported 25c), 13c on 16-Mar-2020 (reported 12.9c). DAE is normal butane (about 1.2x propane). IBD isobutane (about 1.3x). PCW is ethylene: 8.1 c/lb on 3-Apr-2020 (reported record low 8 c/lb). See outputs/final_dashboard/ngl_label_check.py."]]
for r in list(rd.iter_rows()):
    for c in r: c.value=None
for i,row in enumerate(rows,1):
    for j,v in enumerate(row,1): rd.cell(i,j).value=v
wb.save(DST); print("saved",DST)
