import { Suspense, lazy } from "react";
import type { PlotlyFigure } from "../lib/api";

// Lazy + code-split behind the cartesian-only Plotly build (not the full
// ~3.5MB plotly.js) so the initial route (/) never pays for Plotly at all --
// the chunk only loads once a user opens a tab that actually renders a chart.
const Plot = lazy(async () => {
  const [{ default: createPlotlyComponent }, plotlyModule] = await Promise.all([
    import("react-plotly.js/factory"),
    import("plotly.js-cartesian-dist"),
  ]);
  const Plotly = (plotlyModule as { default?: unknown }).default ?? plotlyModule;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return { default: createPlotlyComponent(Plotly as any) };
});

interface PlotlyChartProps {
  fig: PlotlyFigure | null;
  plotConfig?: Record<string, unknown>;
  height?: number;
  emptyMessage?: string;
}

export default function PlotlyChart({ fig, plotConfig, height, emptyMessage }: PlotlyChartProps) {
  if (!fig) {
    return <div className="chart-empty">{emptyMessage ?? "Not enough data to render this chart."}</div>;
  }
  return (
    <Suspense fallback={<div className="chart-loading">Loading chart…</div>}>
      <Plot
        data={fig.data as never}
        layout={{ ...fig.layout, autosize: true, ...(height ? { height } : {}) } as never}
        config={{ displaylogo: false, responsive: true, ...plotConfig }}
        style={{ width: "100%" }}
        useResizeHandler
      />
    </Suspense>
  );
}
