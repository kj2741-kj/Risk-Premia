interface YearRangeSliderProps {
  min: number;
  max: number;
  start: number;
  end: number;
  onChange: (start: number, end: number) => void;
  label?: string;
  help?: string;
}

/** Dual-handle year range, matching Streamlit's st.slider((a, b)) look: two stacked range inputs. */
export default function YearRangeSlider({ min, max, start, end, onChange, label = "Year range", help }: YearRangeSliderProps) {
  const span = Math.max(max - min, 1);
  const pct = (v: number) => ((v - min) / span) * 100;
  return (
    <div className="year-slider" title={help}>
      <div className="year-slider-label">{label}</div>
      <div className="year-slider-track">
        <div className="year-slider-fill" style={{ left: `${pct(start)}%`, width: `${pct(end) - pct(start)}%` }} />
        <input type="range" min={min} max={max} step={1} value={start}
          onChange={(e) => onChange(Math.min(Number(e.target.value), end), end)} />
        <input type="range" min={min} max={max} step={1} value={end}
          onChange={(e) => onChange(start, Math.max(Number(e.target.value), start))} />
      </div>
      <div className="year-slider-values">
        <span style={{ left: `${pct(start)}%` }}>{start}</span>
        <span style={{ left: `${pct(end)}%` }}>{end}</span>
      </div>
    </div>
  );
}
