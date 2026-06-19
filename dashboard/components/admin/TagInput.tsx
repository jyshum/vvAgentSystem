"use client";

import { useState, KeyboardEvent } from "react";

interface TagInputProps {
  label: string;
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
}

export function TagInput({ label, values, onChange, placeholder }: TagInputProps) {
  const [input, setInput] = useState("");

  function add() {
    const trimmed = input.trim();
    if (trimmed && !values.includes(trimmed)) {
      onChange([...values, trimmed]);
    }
    setInput("");
  }

  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(); }
    if (e.key === "Backspace" && input === "" && values.length > 0) {
      onChange(values.slice(0, -1));
    }
  }

  return (
    <div className="mb-6">
      <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-2" style={{ color: "var(--faint)" }}>
        {label}
      </div>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {values.map((v) => (
          <span key={v} className="inline-flex items-center gap-1 font-mono text-[9px] tracking-[0.06em] py-1 px-2"
            style={{ color: "var(--mute)", border: "1px solid var(--ghost)" }}>
            {v}
            <button type="button" onClick={() => onChange(values.filter((x) => x !== v))}
              className="ml-0.5 hover:text-white transition-colors" style={{ color: "var(--faint)" }}>
              ×
            </button>
          </span>
        ))}
      </div>
      <input
        className="w-full font-mono text-[12px] tracking-[0.04em] bg-transparent border-b py-2 outline-none transition-colors placeholder:opacity-40"
        style={{ borderColor: "var(--hair)", color: "var(--white)" }}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={onKey}
        placeholder={placeholder || "Type and press Enter"}
      />
    </div>
  );
}
