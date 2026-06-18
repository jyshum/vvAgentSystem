import { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "outline" | "solid";
}

export function Button({
  variant = "outline",
  className = "",
  children,
  ...props
}: ButtonProps) {
  const base =
    "font-sans text-[13px] font-semibold tracking-[0.06em] inline-flex items-center justify-center gap-[11px] py-[15px] px-[26px] cursor-pointer transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed";

  const variants = {
    outline:
      "bg-transparent border border-[var(--ghost)] text-[var(--white)] rounded-[2px] hover:bg-[var(--white)] hover:text-[var(--ink)] hover:border-[var(--white)]",
    solid:
      "bg-[var(--white)] text-[var(--ink)] border border-[var(--white)] rounded-[2px] hover:bg-transparent hover:text-[var(--white)] hover:border-[var(--ghost)]",
  };

  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}
