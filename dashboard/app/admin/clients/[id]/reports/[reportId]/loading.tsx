export default function ReportEditorLoading() {
  return (
    <div
      style={{
        position: "fixed",
        top: "78px",
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 50,
        display: "flex",
        flexDirection: "column",
        background: "var(--ink)",
      }}
    >
      {/* Chrome bar skeleton */}
      <div
        style={{
          height: "48px",
          flexShrink: 0,
          padding: "0 24px",
          borderBottom: "1px solid var(--hair)",
          background: "rgba(14,14,15,0.7)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div className="h-2.5 w-48 rounded-none animate-pulse" style={{ background: "var(--hair)" }} />
        <div className="flex gap-2">
          <div className="h-7 w-24 rounded-none animate-pulse" style={{ background: "var(--hair)" }} />
          <div className="h-7 w-32 rounded-none animate-pulse" style={{ background: "var(--hair)" }} />
        </div>
      </div>

      {/* Body skeleton */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <div style={{ width: 380, flexShrink: 0, borderRight: "1px solid var(--hair)", padding: "28px 24px", background: "var(--ink-soft)" }}>
          {[...Array(5)].map((_, i) => (
            <div key={i} className="mb-6 animate-pulse">
              <div className="h-2 w-32 mb-3 rounded-none" style={{ background: "var(--hair)" }} />
              <div className="h-16 w-full rounded-none" style={{ background: "var(--hair)" }} />
            </div>
          ))}
        </div>
        <div style={{ flex: 1, background: "#080809" }} />
      </div>
    </div>
  );
}
