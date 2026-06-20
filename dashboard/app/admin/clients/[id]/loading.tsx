export default function ClientLoading() {
  return (
    <div className="animate-pulse">
      <div className="pb-3.5 border-b mb-8" style={{ borderColor: "var(--hair)" }}>
        <div className="h-2 w-32 rounded-none" style={{ background: "var(--hair)" }} />
      </div>
      <div className="pt-8 mb-8">
        <div className="h-12 w-64 mb-2 rounded-none" style={{ background: "var(--hair)" }} />
        <div className="h-2.5 w-36 rounded-none" style={{ background: "var(--hair)" }} />
      </div>
      <div className="flex gap-0 mt-5 border-b mb-10" style={{ borderColor: "var(--hair)" }}>
        {["CONFIG", "RUNS", "REPORTS"].map((t) => (
          <div key={t} className="py-3 px-5 mr-1">
            <div className="h-2 w-14 rounded-none" style={{ background: "var(--hair)" }} />
          </div>
        ))}
      </div>
    </div>
  );
}
