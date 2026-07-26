interface ComingSoonPageProps {
  title: string;
  note?: string;
}

export default function ComingSoonPage({ title, note }: ComingSoonPageProps) {
  return (
    <div className="page">
      <h1>{title}</h1>
      <p className="tab-caption">{note ?? "Coming in a later build phase."}</p>
    </div>
  );
}
