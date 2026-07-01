"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { label: "CLIENTS", href: "/admin", exact: true },
  { label: "APPROVALS", href: "/admin/approvals", exact: false },
];

export function NavLinks() {
  const pathname = usePathname();

  return (
    <div className="flex items-center gap-8">
      {links.map(({ label, href, exact }) => {
        const isActive = exact
          ? pathname === href || pathname.startsWith("/admin/clients")
          : pathname.startsWith(href);

        return (
          <Link
            key={label}
            href={href}
            className="font-mono text-[10px] tracking-[0.12em] uppercase transition-colors hover:text-[var(--white)]"
            style={{
              color: isActive ? "var(--white)" : "var(--faint)",
              textDecoration: "none",
            }}
          >
            {label}
          </Link>
        );
      })}
    </div>
  );
}
