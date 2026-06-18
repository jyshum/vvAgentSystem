interface SectionLabelProps {
  children: React.ReactNode;
  action?: React.ReactNode;
}

export function SectionLabel({ children, action }: SectionLabelProps) {
  return (
    <div className="flex items-center justify-between gap-2.5 font-mono text-xs tracking-[0.14em] uppercase text-[var(--mute)] pb-[11px] border-b border-[var(--hair)] mb-6">
      <span>{children}</span>
      {action}
    </div>
  );
}
