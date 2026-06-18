"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function SubTab({ label, href }: { label: string; href: string }) {
  const pathname = usePathname();
  const isActive = pathname.startsWith(href);

  return (
    <Link
      href={href}
      className="font-mono text-[9px] tracking-[0.16em] pb-3 px-1 mr-8 border-b-2 transition-all duration-200"
      style={{
        color: isActive ? "var(--white)" : "var(--faint)",
        borderColor: isActive ? "var(--white)" : "transparent",
      }}
    >
      {label}
    </Link>
  );
}
