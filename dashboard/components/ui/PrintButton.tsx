"use client";

export function PrintButton() {
  return (
    <button
      onClick={() => window.print()}
      className="font-mono text-[10px] tracking-[0.15em] uppercase py-2.5 px-6 cursor-pointer transition-opacity hover:opacity-85"
      style={{
        background: "var(--white)",
        color: "var(--ink)",
        border: "none",
      }}
    >
      Export PDF
    </button>
  );
}
