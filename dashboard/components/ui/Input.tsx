import { InputHTMLAttributes, TextareaHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export function Input({ label, className = "", ...props }: InputProps) {
  return (
    <div className="mb-3.5">
      {label && (
        <label className="block font-mono text-[11px] tracking-[0.12em] uppercase text-[var(--mute)] mb-1.5">
          {label}
        </label>
      )}
      <input
        className={`w-full bg-transparent border border-[var(--ghost)] text-[var(--white)] font-serif text-sm py-2 px-2.5 outline-none transition-colors focus:border-[rgba(245,244,241,0.42)] placeholder:text-[rgba(255,255,255,0.22)] ${className}`}
        {...props}
      />
    </div>
  );
}

interface TextareaProps
  extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
}

export function Textarea({
  label,
  className = "",
  ...props
}: TextareaProps) {
  return (
    <div className="mb-3.5">
      {label && (
        <label className="block font-mono text-[11px] tracking-[0.12em] uppercase text-[var(--mute)] mb-1.5">
          {label}
        </label>
      )}
      <textarea
        className={`w-full bg-transparent border border-[var(--ghost)] text-[var(--white)] font-serif text-sm py-2 px-2.5 outline-none transition-colors focus:border-[rgba(245,244,241,0.42)] placeholder:text-[rgba(255,255,255,0.22)] italic leading-relaxed min-h-[70px] resize-y ${className}`}
        {...props}
      />
    </div>
  );
}
