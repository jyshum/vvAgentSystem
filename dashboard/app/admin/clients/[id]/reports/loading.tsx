export default function ReportsLoading() {
  return (
    <div>
      <div
        className="grid pb-2.5 border-b font-mono text-[8px] tracking-[0.14em] uppercase"
        style={{
          gridTemplateColumns: "1.5fr 1fr 1fr 1fr 120px",
          gap: "16px",
          borderColor: "var(--hair)",
          color: "var(--faint)",
        }}
      >
        <span>WEEK</span>
        <span>MENTION</span>
        <span>AVG LEVEL</span>
        <span>STATUS</span>
        <span>ACTIONS</span>
      </div>
      {[...Array(3)].map((_, i) => (
        <div
          key={i}
          className="grid py-4 border-b animate-pulse"
          style={{
            gridTemplateColumns: "1.5fr 1fr 1fr 1fr 120px",
            gap: "16px",
            borderColor: "var(--hair)",
          }}
        >
          {[...Array(5)].map((_, j) => (
            <div key={j} className="h-3 rounded-none" style={{ background: "var(--hair)" }} />
          ))}
        </div>
      ))}
    </div>
  );
}
