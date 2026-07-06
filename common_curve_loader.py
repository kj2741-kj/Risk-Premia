"""
common_curve_loader.py
========================
Loaders for full futures-curve data (F1..F27), needed by the Carry and
Value tabs (Momentum only needs F1_raw/F1_continuous, from
rolling_continuous.get_metal_rolling_f1).

Two formats exist in this project:
  - load_curve_legacy_multiheader(): the original "Metals Futures Curve.csv"
    format (multi-row headers, Price/Volume/Open-Interest blocks per
    contract) -- ported verbatim from the Stage 1 dashboard's proven parser.
  - load_curve_simple(): the newer data/06-30/*.xlsx format used for
    Energy/Precious Metals/NGL (title row, then a plain Date,F1,F2,...
    header row, no Volume/OI columns).
"""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st


# ═══════════════════════════════════════════════════════════════
# LEGACY (Metals Futures Curve.csv) -- multi-row header, Price/Volume/OI
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def load_curve_legacy_multiheader(filepath: str) -> dict:
    """One sheet per metal, multi-row headers. Returns {sheet_name: {'raw': df, 'prices': df}}."""
    with open(filepath, "rb") as f:
        raw_bytes = f.read()
    xls = pd.ExcelFile(io.BytesIO(raw_bytes)) if raw_bytes[:4] == b"PK\x03\x04" else None
    if xls is None:
        # plain CSV fallback
        for encoding in ["utf-8", "latin-1", "cp1252", "iso-8859-1", "utf-16"]:
            try:
                df = pd.read_csv(io.BytesIO(raw_bytes), encoding=encoding)
                if not df.empty:
                    return {"Sheet1": _parse_single_curve_df(df)}
            except Exception:
                continue
        return {}
    return _parse_curve_excel(xls)


def _parse_curve_excel(xls: pd.ExcelFile) -> dict:
    data = {}
    for sheet in xls.sheet_names:
        try:
            df_raw = pd.read_excel(xls, sheet_name=sheet, header=None, nrows=5)
            header_rows = []
            for i in range(min(4, len(df_raw))):
                row_vals = [str(v).strip().lower() for v in df_raw.iloc[i].values if pd.notna(v)]
                if any(kw in " ".join(row_vals) for kw in ["date", "f1", "f2", "price", "volume"]):
                    header_rows.append(i)
            if len(header_rows) >= 2:
                df = pd.read_excel(xls, sheet_name=sheet, header=header_rows)
            elif len(header_rows) == 1:
                df = pd.read_excel(xls, sheet_name=sheet, header=header_rows[0])
            else:
                df = pd.read_excel(xls, sheet_name=sheet, header=[0, 1, 2])
        except Exception:
            try:
                df = pd.read_excel(xls, sheet_name=sheet, header=[0, 1])
            except Exception:
                df = pd.read_excel(xls, sheet_name=sheet)
        data[sheet] = _parse_single_curve_df(df)
    return data


def _parse_single_curve_df(df: pd.DataFrame) -> dict:
    if isinstance(df.columns, pd.MultiIndex):
        new_cols = []
        for col_tuple in df.columns:
            parts = [str(p).strip() for p in col_tuple
                     if pd.notna(p) and "Unnamed" not in str(p) and str(p).strip()]
            new_cols.append("_".join(parts) if parts else str(col_tuple))
        df.columns = new_cols
    df.columns = [str(c).strip() for c in df.columns]

    date_col = [c for c in df.columns if "date" in c.lower()]
    if date_col:
        df = df.rename(columns={date_col[0]: "Date"})
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])
        df = df.set_index("Date").sort_index()

    prices = {}
    for col in df.columns:
        col_lower = col.lower().replace(" ", "_")
        for i in range(1, 28):
            patterns = [f"f{i}_price", f"F{i}_Price", f"F{i}_price"]
            if any(p.lower() in col_lower for p in patterns):
                prices[f"F{i}"] = pd.to_numeric(df[col], errors="coerce")
                break
            elif col_lower.startswith(f"f{i}_") and "price" in col_lower:
                prices[f"F{i}"] = pd.to_numeric(df[col], errors="coerce")
                break

    return {"raw": df, "prices": pd.DataFrame(prices, index=df.index) if prices else pd.DataFrame()}


# ═══════════════════════════════════════════════════════════════
# SIMPLE (data/06-30/*.xlsx) -- title row, then Date,F1,F2,... header
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def load_curve_simple(filepath: str, sheet_name: str) -> pd.DataFrame:
    """Load one product's F1..F27 curve from the newer single-header-row format.
    Returns a DataFrame indexed by Date with columns F1, F2, ..."""
    raw = pd.read_excel(filepath, sheet_name=sheet_name, header=None)
    header_row_idx = 1  # row 0 = title, row 1 = 'Date','F1','F2',...
    cols = raw.iloc[header_row_idx].tolist()
    df = raw.iloc[header_row_idx + 1:].copy()
    df.columns = cols
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).set_index("Date").sort_index()
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df
