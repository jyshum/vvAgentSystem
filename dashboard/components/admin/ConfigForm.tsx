"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { TagInput } from "./TagInput";
import type { Client } from "@/lib/types";

export function ConfigForm({ client }: { client: Client }) {
  const [clientName, setClientName] = useState(client.name || "");
  const [brandName, setBrandName] = useState(client.brand_name || "");
  const [domain, setDomain] = useState(client.website_domain || "");
  const [variations, setVariations] = useState<string[]>(client.brand_variations || []);
  const [queries, setQueries] = useState<string[]>(client.target_queries || []);
  const [competitors, setCompetitors] = useState<string[]>(client.competitors || []);
  const [gscSiteUrl, setGscSiteUrl] = useState(client.gsc_site_url || "");
  const [cmsType, setCmsType] = useState(client.cms_type || "copy_paste");
  const [cmsConfig, setCmsConfig] = useState<Record<string, string>>(client.cms_config || {});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  function updateCmsField(key: string, value: string) {
    setCmsConfig(prev => ({ ...prev, [key]: value }));
  }

  async function save() {
    setSaving(true);
    setSaveError(null);
    const supabase = createClient();
    const { error } = await supabase.from("clients").update({
      name: clientName,
      brand_name: brandName,
      website_domain: domain,
      brand_variations: variations,
      target_queries: queries,
      competitors: competitors,
      gsc_site_url: gscSiteUrl,
      cms_type: cmsType,
      cms_config: cmsConfig,
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

      {/* CMS Integration */}
      <div className="mb-6 mt-10 pt-8" style={{ borderTop: "1px solid var(--hair)" }}>
        <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-4" style={{ color: "var(--faint)" }}>
          Implementation Method
        </div>
        <select
          className="w-full font-mono text-[12px] py-2 outline-none cursor-pointer"
          style={{ background: "transparent", borderBottom: "1px solid var(--hair)", color: "var(--white)" }}
          value={cmsType}
          onChange={(e) => setCmsType(e.target.value)}
        >
          <option value="copy_paste" style={{ background: "var(--ink)" }}>Copy & Paste</option>
          <option value="github" style={{ background: "var(--ink)" }}>GitHub PR</option>
          <option value="wordpress" style={{ background: "var(--ink)" }}>WordPress API</option>
          <option value="webflow" style={{ background: "var(--ink)" }}>Webflow API</option>
        </select>
        <div className="font-mono text-[8px] mt-1.5" style={{ color: "var(--faint)" }}>
          {cmsType === "copy_paste" && "Approved changes exported as text — no setup needed"}
          {cmsType === "github" && "Auto-creates PRs with content changes"}
          {cmsType === "wordpress" && "Pushes changes via WordPress REST API"}
          {cmsType === "webflow" && "Pushes changes via Webflow CMS API"}
        </div>
      </div>

      {cmsType === "github" && (
        <div className="space-y-4 mb-6">
          <div>
            <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-2" style={{ color: "var(--faint)" }}>
              Repository
            </div>
            <input
              className="w-full font-mono text-[12px] py-2 outline-none"
              style={{ background: "transparent", borderBottom: "1px solid var(--hair)", color: "var(--white)" }}
              value={cmsConfig.repo || ""}
              onChange={(e) => updateCmsField("repo", e.target.value)}
              placeholder="owner/repo"
            />
          </div>
          <div>
            <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-2" style={{ color: "var(--faint)" }}>
              Branch
            </div>
            <input
              className="w-full font-mono text-[12px] py-2 outline-none"
              style={{ background: "transparent", borderBottom: "1px solid var(--hair)", color: "var(--white)" }}
              value={cmsConfig.branch || ""}
              onChange={(e) => updateCmsField("branch", e.target.value)}
              placeholder="main"
            />
          </div>
          <div>
            <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-2" style={{ color: "var(--faint)" }}>
              GitHub Token
            </div>
            <input
              type="password"
              className="w-full font-mono text-[12px] py-2 outline-none"
              style={{ background: "transparent", borderBottom: "1px solid var(--hair)", color: "var(--white)" }}
              value={cmsConfig.token || ""}
              onChange={(e) => updateCmsField("token", e.target.value)}
              placeholder="ghp_..."
            />
          </div>
        </div>
      )}

      {cmsType === "wordpress" && (
        <div className="space-y-4 mb-6">
          <div>
            <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-2" style={{ color: "var(--faint)" }}>
              WordPress URL
            </div>
            <input
              className="w-full font-mono text-[12px] py-2 outline-none"
              style={{ background: "transparent", borderBottom: "1px solid var(--hair)", color: "var(--white)" }}
              value={cmsConfig.wp_url || ""}
              onChange={(e) => updateCmsField("wp_url", e.target.value)}
              placeholder="https://example.com/wp-json"
            />
          </div>
          <div>
            <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-2" style={{ color: "var(--faint)" }}>
              App Password
            </div>
            <input
              type="password"
              className="w-full font-mono text-[12px] py-2 outline-none"
              style={{ background: "transparent", borderBottom: "1px solid var(--hair)", color: "var(--white)" }}
              value={cmsConfig.app_password || ""}
              onChange={(e) => updateCmsField("app_password", e.target.value)}
              placeholder="WordPress application password"
            />
          </div>
        </div>
      )}

      {cmsType === "webflow" && (
        <div className="space-y-4 mb-6">
          <div>
            <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-2" style={{ color: "var(--faint)" }}>
              API Token
            </div>
            <input
              type="password"
              className="w-full font-mono text-[12px] py-2 outline-none"
              style={{ background: "transparent", borderBottom: "1px solid var(--hair)", color: "var(--white)" }}
              value={cmsConfig.api_token || ""}
              onChange={(e) => updateCmsField("api_token", e.target.value)}
              placeholder="Webflow API token"
            />
          </div>
          <div>
            <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-2" style={{ color: "var(--faint)" }}>
              Site ID
            </div>
            <input
              className="w-full font-mono text-[12px] py-2 outline-none"
              style={{ background: "transparent", borderBottom: "1px solid var(--hair)", color: "var(--white)" }}
              value={cmsConfig.site_id || ""}
              onChange={(e) => updateCmsField("site_id", e.target.value)}
              placeholder="Webflow site ID"
            />
          </div>
        </div>
      )}

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
