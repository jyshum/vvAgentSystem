export default function RunDetailLoading() {
  return (
    <div style={{ maxWidth: 960 }}>
      <div className="flex items-end justify-between mb-8 flex-wrap gap-4 animate-pulse">
        <div>
          <div className="h-10 w-72 mb-2 rounded-none" style={{ background: "var(--hair)" }} />
          <div className="h-2.5 w-40 rounded-none" style={{ background: "var(--hair)" }} />
        </div>
        <div className="h-10 w-32 rounded-none" style={{ background: "var(--hair)" }} />
      </div>
      <div className="grid grid-cols-4 mb-10 animate-pulse" style={{ gap: 1, background: "var(--hair)", border: "1px solid var(--hair)" }}>
        {[...Array(4)].map((_, i) => (
          <div key={i} className="py-5 px-5" style={{ background: "var(--ink)" }}>
            <div className="h-10 w-20 mb-2 rounded-none" style={{ background: "var(--hair)" }} />
            <div className="h-2 w-24 rounded-none" style={{ background: "var(--hair)" }} />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-4 gap-3 mt-12 animate-pulse">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="p-4 border" style={{ borderColor: "var(--hair)", minHeight: 120 }}>
            <div className="h-3 w-20 mb-4 rounded-none" style={{ background: "var(--hair)" }} />
            <div className="h-1 mb-3 rounded-none" style={{ background: "var(--hair)" }} />
            <div className="h-2 w-16 rounded-none" style={{ background: "var(--hair)" }} />
          </div>
        ))}
      </div>
    </div>
  );
}
