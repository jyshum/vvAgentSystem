interface BadgeProps {
  variant: "cited" | "mentioned" | "not-found" | "draft" | "published";
  children: React.ReactNode;
}

export function Badge({ variant, children }: BadgeProps) {
  const base =
    "font-mono text-[8px] tracking-[0.1em] uppercase py-[4px] px-[9px] inline-block whitespace-nowrap";

  const variants: Record<string, string> = {
    cited: "text-[var(--ink)] bg-[var(--pos)]",
    mentioned: "text-[var(--ink)] bg-[var(--pos)]",
    "not-found": "text-[var(--mute)] border border-[rgba(245,244,241,0.42)]",
    draft: "text-[var(--mute)] border border-[rgba(245,244,241,0.42)]",
    published: "text-[var(--ink)] bg-[var(--pos)]",
  };

  return (
    <span className={`${base} ${variants[variant] || ""}`}>
      {children}
    </span>
  );
}
