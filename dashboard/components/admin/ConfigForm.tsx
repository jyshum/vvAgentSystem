"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { TagInput } from "./TagInput";
import type { Client } from "@/lib/types";

export function ConfigForm({ client }: { client: Client }) {
  const [brandName, setBrandName] = useState(client.brand_name || "");
  const [domain, setDomain] = useState(client.website_domain || "");
  const [variations, setVariations] = useState<string[]>(client.brand_variations || []);
  const [queries, setQueries] = useState<string[]>(client.target_queries || []);
  const [competitors, setCompetitors] = useState<string[]>(client.competitors || []);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setSaveError(null);
    const supabase = createClient();
    const { error } = await supabase.from("clients").update({
      brand_name: brandName,
      website_domain: domain,
      brand_variations: variations,
      target_queries: queries,
      competitors: competitors,
    }).eq("id", client.id);
    setSaving(false);
    if (error) {
      setSaveError(error.message);
      return;
    }
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  const fieldBorderStyle = {
    background: "transparent",
    borderBottom: "1px solid var(--hair)",
    color: "var(--white)",
  };

  return (
    <div style={{ maxWidth: 640 }}>
      <div className="mb-6">
        <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-2" style={{ color: "var(--faint)" }}>
          Brand Name
        </div>
        <input
          className="w-full font-serif text-[16px] py-2 outline-none transition-all"
          style={fieldBorderStyle}
          value={brandName}
          onChange={(e) => setBrandName(e.target.value)}
        />
      </div>

      <div className="mb-6">
        <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-2" style={{ color: "var(--faint)" }}>
          Website Domain
        </div>
        <input
          className="w-full font-mono text-[12px] py-2 outline-none transition-all"
          style={fieldBorderStyle}
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
          placeholder="example.com"
        />
      </div>

      <TagInput
        label="Brand Variations"
        values={variations}
        onChange={setVariations}
        placeholder="Add variation and press Enter"
      />

      <TagInput
        label={`Target Queries (${queries.length})`}
        values={queries}
        onChange={setQueries}
        placeholder="Add query and press Enter"
      />

      <TagInput
        label={`Competitors (${competitors.length})`}
        values={competitors}
        onChange={setCompetitors}
        placeholder="Add competitor and press Enter"
      />

      <button
        onClick={save}
        disabled={saving}
        className="font-mono text-[9px] tracking-[0.14em] uppercase py-3 px-6 transition-all duration-200 disabled:opacity-40"
        style={{
          background: saved ? "var(--pos)" : "var(--white)",
          color: "var(--ink)",
        }}
      >
        {saving ? "SAVING…" : saved ? "SAVED ✓" : "SAVE CONFIG"}
      </button>
      {saveError && (
        <p className="font-mono text-[9px] mt-3" style={{ color: "var(--neg)" }}>
          Save failed: {saveError}
        </p>
      )}
    </div>
  );
}
