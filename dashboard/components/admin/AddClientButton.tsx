"use client";

import { useState } from "react";
import { AddClientModal } from "./AddClientModal";

export function AddClientButton() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="font-mono text-[10px] tracking-[0.14em] py-3 px-6 transition-all duration-200 hover:bg-[var(--white)] hover:text-[var(--ink)]"
        style={{ border: "1px solid var(--ghost)", background: "transparent", color: "var(--white)", cursor: "pointer" }}
      >
        + ADD CLIENT
      </button>
      {open && <AddClientModal onClose={() => setOpen(false)} />}
    </>
  );
}
