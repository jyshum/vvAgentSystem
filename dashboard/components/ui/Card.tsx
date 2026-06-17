import { HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  elevated?: boolean;
}

export function Card({
  elevated = false,
  className = "",
  children,
  ...props
}: CardProps) {
  const base = elevated
    ? "bg-[var(--ink-2)] border border-[var(--hair)] rounded-card shadow-card overflow-hidden"
    : "bg-[var(--ink-soft)] border border-[var(--hair)] rounded-card overflow-hidden";

  return (
    <div className={`${base} ${className}`} {...props}>
      {children}
    </div>
  );
}
