interface BadgeProps {
  variant:
    | "cited"
    | "mentioned"
    | "not-found"
    | "draft"
    | "published"
    | "cited-paper"
    | "mentioned-paper"
    | "not-found-paper";
  children: React.ReactNode;
}

export function Badge({ variant, children }: BadgeProps) {
  const base =
    "font-mono text-[8px] tracking-[0.1em] uppercase py-[4px] px-[9px] inline-block whitespace-nowrap";

  const variants: Record<string, string> = {
    // dark-mode variants
    cited: "text-[var(--ink)] bg-[var(--pos)]",
    mentioned: "text-[var(--ink)] bg-[var(--pos)]",
    "not-found": "text-[var(--mute)] border border-[rgba(245,244,241,0.42)]",
    draft: "text-[var(--mute)] border border-[rgba(245,244,241,0.42)]",
    published: "text-[var(--ink)] bg-[var(--pos)]",
    // paper-mode variants
    "cited-paper":
      "text-[var(--pos-paper)] bg-[rgba(45,122,82,0.1)] border border-[rgba(45,122,82,0.22)]",
    "mentioned-paper":
      "text-[var(--pos-paper)] bg-[rgba(45,122,82,0.07)] border border-[rgba(45,122,82,0.15)]",
    "not-found-paper":
      "text-[var(--p-mute)] bg-[rgba(23,21,15,0.04)] border border-[var(--p-ghost)]",
  };

  return (
    <span className={`${base} ${variants[variant] || ""}`}>
      {children}
    </span>
  );
}
