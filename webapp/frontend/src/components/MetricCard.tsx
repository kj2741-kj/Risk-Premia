interface MetricCardProps {
  label: string;
  value: number | null | undefined;
  format: (v: number) => string;
  unit?: string;
}

export default function MetricCard({ label, value, format, unit = "" }: MetricCardProps) {
  const display = value === null || value === undefined || Number.isNaN(value) ? "N/A" : format(value);
  return (
    <div className="metric-card">
      <h4>{label}</h4>
      <p className="value">
        {display}
        {value !== null && value !== undefined ? unit : ""}
      </p>
    </div>
  );
}
