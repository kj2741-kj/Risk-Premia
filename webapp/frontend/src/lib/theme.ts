/**
 * Same hex values as common_shared.py's COLORS / METAL_COLORS, so the React
 * UI (nav accents, metric cards) reads as visually continuous with the
 * Plotly charts served by the backend (which use CHART_LAYOUT/COLORS
 * directly, unchanged, from the same Python source).
 */
export const COLORS = {
  primary: "#B87333",
  secondary: "#C9A84C",
  accent: "#3D8F8A",
  green: "#5BAD72",
  red: "#B85450",
  amber: "#C9A84C",
  orange: "#B87333",
  pink: "#A07898",
  slate: "#6A6460",
} as const;

export const METAL_COLORS: Record<string, string> = {
  Copper: "#B87333",
  Aluminium: "#9BAAB3",
  Zinc: "#7A8E9A",
  Nickel: "#A0A5A8",
  Lead: "#6B7073",
  Tin: "#9A9EA0",
  Gold: "#C9A84C",
  Silver: "#B0B8C0",
  Platinum: "#C8D0D8",
  Palladium: "#B8A898",
};
