"use client";

import { useState } from "react";
import { TagInput } from "./TagInput";
import type { Client } from "@/lib/types";

export function ConfigForm({ client }: { client: Client }) {
  const [clientName, setClientName] = useState(client.name || "");
  const [brandName, setBrandName] = useState(client.brand_name || "");
  const [domain, setDomain] = useState(client.website_domain || "");
  const [variations, setVariations] = useState<string[]>(client.brand_variations || []);
  const [competitors, setCompetitors] = useState<string[]>(client.competitors || []);
  const [gscSiteUrl, setGscSiteUrl] = useState(client.gsc_site_url || "");
  const [sitePlatform, setSitePlatform] = useState(client.site_platform);
  const [implementationMode, setImplementationMode] = useState(client.implementation_mode);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setSaveError(null);
    // Saved via server route: browser-side updates are silently dropped by RLS
    // for ADMIN_EMAILS admins (no client_users row), showing a false "SAVED ✓".
    let errorMessage: string | null = null;
    try {
      const res = await fetch(`/api/admin/clients/${client.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: clientName,
          brand_name: brandName,
          website_domain: domain,
          brand_variations: variations,
          competitors: competitors,
          gsc_site_url: gscSiteUrl,
          site_platform: sitePlatform,
          implementation_mode: implementationMode,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        errorMessage = data?.error ?? `Save failed (${res.status})`;
      }
    } catch (e) {
      errorMessage = e instanceof Error ? e.message : "Network error";
    }
    setSaving(false);
    if (errorMessage) {
      setSaveError(errorMessage);
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
          Client Name
        </div>
        <input
          className="w-full font-mono text-[13px] py-2 outline-none transition-all"
          style={fieldBorderStyle}
          value={clientName}
          onChange={(e) => setClientName(e.target.value)}
          placeholder="Internal identifier"
        />
      </div>

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

      <div className="mb-6">
        <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-2" style={{ color: "var(--faint)" }}>
          GSC Property URL
        </div>
        <input
          className="w-full font-mono text-[12px] py-2 outline-none transition-all"
          style={fieldBorderStyle}
          value={gscSiteUrl}
          onChange={(e) => setGscSiteUrl(e.target.value)}
          placeholder="https://www.example.com/"
        />
        <div className="font-mono text-[8px] mt-1.5" style={{ color: "var(--faint)" }}>
          Must match exactly as shown in Google Search Console (including trailing slash)
        </div>
      </div>

      <div className="mb-6 mt-10 pt-8" style={{ borderTop: "1px solid var(--hair)" }}>
        <label
          htmlFor="site-platform"
          className="block font-mono text-[9px] tracking-[0.16em] uppercase mb-2"
          style={{ color: "var(--faint)" }}
        >
          Site platform
        </label>
        <select
          id="site-platform"
          className="w-full font-mono text-[12px] py-2 outline-none cursor-pointer"
          style={{ background: "transparent", borderBottom: "1px solid var(--hair)", color: "var(--white)" }}
          value={sitePlatform}
          onChange={(event) => setSitePlatform(event.target.value as Client["site_platform"])}
        >
          <option value="squarespace" style={{ background: "var(--ink)" }}>Squarespace</option>
          <option value="wordpress" style={{ background: "var(--ink)" }}>WordPress</option>
          <option value="webflow" style={{ background: "var(--ink)" }}>Webflow</option>
          <option value="shopify" style={{ background: "var(--ink)" }}>Shopify</option>
          <option value="repository" style={{ background: "var(--ink)" }}>Repository-managed</option>
          <option value="other" style={{ background: "var(--ink)" }}>Other</option>
        </select>
      </div>

      <TagInput
        label="Brand Variations"
        values={variations}
        onChange={setVariations}
        placeholder="Add variation and press Enter"
      />

      <TagInput
        label={`Competitors (${competitors.length})`}
        values={competitors}
        onChange={setCompetitors}
        placeholder="Add competitor and press Enter"
      />

      <div className="mb-6 mt-10 pt-8" style={{ borderTop: "1px solid var(--hair)" }}>
        <label
          htmlFor="implementation-mode"
          className="block font-mono text-[9px] tracking-[0.16em] uppercase mb-2"
          style={{ color: "var(--faint)" }}
        >
          Implementation mode
        </label>
        <select
          id="implementation-mode"
          className="w-full font-mono text-[12px] py-2 outline-none cursor-pointer"
          style={{ background: "transparent", borderBottom: "1px solid var(--hair)", color: "var(--white)" }}
          value={implementationMode}
          onChange={(event) => setImplementationMode(event.target.value as Client["implementation_mode"])}
        >
          <option value="copy_paste" style={{ background: "var(--ink)" }}>Copy and paste</option>
          <option value="guided" style={{ background: "var(--ink)" }}>Guided instructions</option>
          <option value="github_pr" style={{ background: "var(--ink)" }}>GitHub pull request</option>
          <option value="staged_api" style={{ background: "var(--ink)" }}>Staged API</option>
        </select>
      </div>

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
