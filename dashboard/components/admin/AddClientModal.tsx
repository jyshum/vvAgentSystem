"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { TagInput } from "./TagInput";

export function AddClientModal({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [name, setName] = useState("");
  const [brandName, setBrandName] = useState("");
  const [domain, setDomain] = useState("");
  const [brandVariations, setBrandVariations] = useState<string[]>([]);
  const [awarenessPrompts, setAwarenessPrompts] = useState<string[]>([]);
  const [considerationPrompts, setConsiderationPrompts] = useState<string[]>([]);
  const [brandedPrompts, setBrandedPrompts] = useState<string[]>([]);
  const [competitors, setCompetitors] = useState<string[]>([]);

  // Close on Escape
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !domain.trim()) {
      setError("Name and domain are required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const res = await fetch("/api/admin/clients", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          brand_name: brandName.trim() || name.trim(),
          website_domain: domain.trim(),
          brand_variations: brandVariations,
          query_buckets: {
            awareness: awarenessPrompts,
            consideration: considerationPrompts,
            branded: brandedPrompts,
          },
          competitors,
        }),
      });
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(msg || "Failed to create client.");
      }
      router.refresh();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-end"
      style={{ background: "rgba(14,14,15,0.7)", backdropFilter: "blur(4px)" }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="h-full overflow-y-auto flex flex-col"
        style={{ width: 540, background: "var(--ink)", borderLeft: "1px solid var(--hair)" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-8 py-6 border-b" style={{ borderColor: "var(--hair)" }}>
          <div>
            <div className="font-display text-[28px] font-light" style={{ color: "var(--white)" }}>
              Add Client
            </div>
            <div className="font-mono text-[9px] tracking-[0.12em] mt-1" style={{ color: "var(--faint)" }}>
              NEW ACCOUNT
            </div>
          </div>
          <button
            onClick={onClose}
            className="font-mono text-[11px] transition-colors hover:text-white"
            style={{ color: "var(--faint)", background: "none", border: "none", cursor: "pointer" }}
          >
            ✕
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-0 px-8 py-7 flex-1">

          {/* Name */}
          <div className="mb-5">
            <label className="block font-mono text-[9px] tracking-[0.14em] uppercase mb-1.5" style={{ color: "var(--faint)" }}>
              Client Name <span style={{ color: "var(--neg)" }}>*</span>
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="ChildSpot"
              required
              className="w-full font-serif text-[15px] bg-transparent px-3 py-2.5 outline-none transition-colors"
              style={{ border: "1px solid var(--hair)", color: "var(--white)" }}
              onFocus={(e) => (e.target.style.borderColor = "var(--ghost)")}
              onBlur={(e) => (e.target.style.borderColor = "var(--hair)")}
            />
          </div>

          {/* Brand name */}
          <div className="mb-5">
            <label className="block font-mono text-[9px] tracking-[0.14em] uppercase mb-1.5" style={{ color: "var(--faint)" }}>
              Brand Name <span style={{ color: "var(--faint)", opacity: 0.5 }}>(if different)</span>
            </label>
            <input
              value={brandName}
              onChange={(e) => setBrandName(e.target.value)}
              placeholder="Same as client name"
              className="w-full font-serif text-[15px] bg-transparent px-3 py-2.5 outline-none transition-colors"
              style={{ border: "1px solid var(--hair)", color: "var(--white)" }}
              onFocus={(e) => (e.target.style.borderColor = "var(--ghost)")}
              onBlur={(e) => (e.target.style.borderColor = "var(--hair)")}
            />
          </div>

          {/* Domain */}
          <div className="mb-6">
            <label className="block font-mono text-[9px] tracking-[0.14em] uppercase mb-1.5" style={{ color: "var(--faint)" }}>
              Website Domain <span style={{ color: "var(--neg)" }}>*</span>
            </label>
            <input
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="childspotapp.com"
              required
              className="w-full font-mono text-[12px] bg-transparent px-3 py-2.5 outline-none transition-colors"
              style={{ border: "1px solid var(--hair)", color: "var(--white)" }}
              onFocus={(e) => (e.target.style.borderColor = "var(--ghost)")}
              onBlur={(e) => (e.target.style.borderColor = "var(--hair)")}
            />
          </div>

          <div className="border-t mb-6" style={{ borderColor: "var(--hair)" }} />

          <TagInput
            label="Brand Variations"
            values={brandVariations}
            onChange={setBrandVariations}
            placeholder="e.g. Child Spot, childspotapp"
          />

          <TagInput
            label={`Awareness Prompts (${awarenessPrompts.length})`}
            values={awarenessPrompts}
            onChange={setAwarenessPrompts}
            placeholder="e.g. how to budget as a medical student"
          />

          <TagInput
            label={`Consideration Prompts (${considerationPrompts.length})`}
            values={considerationPrompts}
            onChange={setConsiderationPrompts}
            placeholder="e.g. best budgeting tools for medical students"
          />

          <TagInput
            label={`Branded Prompts - Deferred (${brandedPrompts.length})`}
            values={brandedPrompts}
            onChange={setBrandedPrompts}
            placeholder="not measured in current runs"
          />

          <TagInput
            label="Competitors"
            values={competitors}
            onChange={setCompetitors}
            placeholder="e.g. KinderPage, Wee Watch"
          />

          {error && (
            <p className="font-mono text-[9px] mb-4" style={{ color: "var(--neg)" }}>{error}</p>
          )}

          {/* Actions */}
          <div className="flex gap-3 mt-auto pt-6 border-t" style={{ borderColor: "var(--hair)" }}>
            <button
              type="button"
              onClick={onClose}
              className="font-mono text-[9px] tracking-[0.14em] uppercase px-5 py-3 transition-all duration-200 hover:text-white"
              style={{ color: "var(--faint)", border: "1px solid var(--hair)", background: "transparent", cursor: "pointer" }}
            >
              CANCEL
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 font-mono text-[9px] tracking-[0.14em] uppercase px-5 py-3 transition-all duration-200"
              style={{
                background: saving ? "var(--faint)" : "var(--white)",
                color: "var(--ink)",
                border: "1px solid var(--white)",
                cursor: saving ? "not-allowed" : "pointer",
                opacity: saving ? 0.7 : 1,
              }}
            >
              {saving ? "CREATING…" : "CREATE CLIENT"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
