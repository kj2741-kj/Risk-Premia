interface CheckPillsProps {
  label: string;
  options: string[];
  selected: string[];
  onChange: (next: string[]) => void;
  help?: string;
}

/** Multiselect equivalent (st.multiselect): every option shown, click to toggle in/out. */
export default function CheckPills({ label, options, selected, onChange, help }: CheckPillsProps) {
  return (
    <div style={{ marginBottom: 12 }} title={help}>
      <div className="pill-label">{label}</div>
      <div className="pill-row" style={{ marginBottom: 0 }}>
        {options.map((o) => {
          const on = selected.includes(o);
          return (
            <span className="pill" key={o} style={{ opacity: on ? 1 : 0.4 }}>
              {o}
              <button className="pill-remove"
                onClick={() => onChange(on ? selected.filter((x) => x !== o) : options.filter((x) => x === o || selected.includes(x)))}>
                {on ? "×" : "+"}
              </button>
            </span>
          );
        })}
      </div>
    </div>
  );
}
