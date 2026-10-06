// Number formatters matching the Streamlit dashboards' Python format specs exactly.

/** Python "{:+.Nf}" */
export function fmtSigned(v: number, digits = 2): string {
  const s = v.toFixed(digits);
  return v >= 0 && !s.startsWith("-") ? `+${s}` : s;
}

/** Python "{:+,.2f}" */
export function fmtSignedComma(v: number, digits = 2): string {
  const body = Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  return v < 0 ? `-${body}` : `+${body}`;
}
