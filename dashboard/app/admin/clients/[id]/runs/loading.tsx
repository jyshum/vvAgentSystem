export default function RunsLoading() {
  return (
    <div>
      <div
        className="flex items-center justify-between mb-9 p-6 animate-pulse"
        style={{ border: "1px solid var(--hair)" }}
      >
        <div>
          <div className="h-4 w-48 mb-2 rounded-none" style={{ background: "var(--hair)" }} />
          <div className="h-2 w-72 rounded-none" style={{ background: "var(--hair)" }} />
        </div>
        <div className="h-8 w-24 rounded-none" style={{ background: "var(--hair)" }} />
      </div>
      <div
        className="grid pb-2.5 border-b font-mono text-[8px] tracking-[0.14em] uppercase"
        style={{
          gridTemplateColumns: "1.5fr 1fr 1fr 80px 1fr 110px",
          gap: "16px",
          borderColor: "var(--hair)",
          color: "var(--faint)",
        }}
      >
        <span>DATE</span>
        <span>MENTION</span>
        <span>CITATION</span>
        <span>QUERIES</span>
        <span>STATUS</span>
        <span>REPORT</span>
      </div>
      {[...Array(4)].map((_, i) => (
        <div
          key={i}
          className="grid py-4 border-b animate-pulse"
          style={{
            gridTemplateColumns: "1.5fr 1fr 1fr 80px 1fr 110px",
            gap: "16px",
            borderColor: "var(--hair)",
          }}
        >
          {[...Array(6)].map((_, j) => (
            <div key={j} className="h-3 rounded-none" style={{ background: "var(--hair)" }} />
          ))}
        </div>
      ))}
    </div>
  );
}
