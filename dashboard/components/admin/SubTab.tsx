"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function SubTab({ label, href }: { label: string; href: string }) {
  const pathname = usePathname();
  const isActive = pathname === href || pathname.startsWith(href + "/");

  return (
    <Link
      href={href}
      className="font-mono text-[9px] tracking-[0.16em] border-b-2 -mb-px transition-all duration-200 hover:text-[var(--mute)]"
      style={{
        padding: "13px 20px",
        color: isActive ? "var(--white)" : "var(--faint)",
        borderColor: isActive ? "var(--white)" : "transparent",
        display: "block",
      }}
    >
      {label}
    </Link>
  );
}
