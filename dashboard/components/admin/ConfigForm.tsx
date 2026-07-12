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
  const [cycleFrequency, setCycleFrequency] = useState(client.cycle_frequency || "weekly");
  const [cycleDay, setCycleDay] = useState(client.cycle_day ?? 1);
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
          cms_type: cmsType,
          cms_config: cmsConfig,
          cycle_frequency: cycleFrequency,
          cycle_day: cycleDay,
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
    // Tell the agent server to reload schedules
    try {
      await fetch("/api/runs/reload-schedules", { method: "POST" });
    } catch {}
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

      {/* Schedule */}
      <div className="mb-6 mt-10 pt-8" style={{ borderTop: "1px solid var(--hair)" }}>
        <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-4" style={{ color: "var(--faint)" }}>
          Pipeline Schedule
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-2" style={{ color: "var(--faint)" }}>
              Frequency
            </div>
            <select
              className="w-full font-mono text-[12px] py-2 outline-none cursor-pointer"
              style={{ background: "transparent", borderBottom: "1px solid var(--hair)", color: "var(--white)" }}
              value={cycleFrequency}
              onChange={(e) => setCycleFrequency(e.target.value)}
            >
              <option value="weekly" style={{ background: "var(--ink)" }}>Weekly</option>
              <option value="biweekly" style={{ background: "var(--ink)" }}>Bi-weekly</option>
              <option value="monthly" style={{ background: "var(--ink)" }}>Monthly</option>
            </select>
          </div>
          <div>
            <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-2" style={{ color: "var(--faint)" }}>
              Day
            </div>
            <select
              className="w-full font-mono text-[12px] py-2 outline-none cursor-pointer"
              style={{ background: "transparent", borderBottom: "1px solid var(--hair)", color: "var(--white)" }}
              value={cycleDay}
              onChange={(e) => setCycleDay(Number(e.target.value))}
            >
              <option value={0} style={{ background: "var(--ink)" }}>Monday</option>
              <option value={1} style={{ background: "var(--ink)" }}>Tuesday</option>
              <option value={2} style={{ background: "var(--ink)" }}>Wednesday</option>
              <option value={3} style={{ background: "var(--ink)" }}>Thursday</option>
              <option value={4} style={{ background: "var(--ink)" }}>Friday</option>
              <option value={5} style={{ background: "var(--ink)" }}>Saturday</option>
              <option value={6} style={{ background: "var(--ink)" }}>Sunday</option>
            </select>
          </div>
        </div>
        <div className="font-mono text-[8px] mt-2" style={{ color: "var(--faint)" }}>
          Full pipeline runs automatically at 2:00 AM UTC on the selected day
        </div>
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
          <option value="shopify" style={{ background: "var(--ink)" }}>Shopify API</option>
          <option value="webflow" style={{ background: "var(--ink)" }}>Webflow CMS (manual)</option>
        </select>
        <div className="font-mono text-[8px] mt-1.5" style={{ color: "var(--faint)" }}>
          {cmsType === "copy_paste" && "Approved changes exported as text — no setup needed"}
          {cmsType === "github" && "Auto-creates PRs with content changes"}
          {cmsType === "wordpress" && "Pushes changes directly via WordPress REST API"}
          {cmsType === "shopify" && "Pushes changes directly via Shopify Admin API"}
          {cmsType === "webflow" && "Webflow static pages can't be updated via API — uses copy & paste export"}
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
              Content Path
            </div>
            <input
              className="w-full font-mono text-[12px] py-2 outline-none"
              style={{ background: "transparent", borderBottom: "1px solid var(--hair)", color: "var(--white)" }}
              value={cmsConfig.content_path || ""}
              onChange={(e) => updateCmsField("content_path", e.target.value)}
              placeholder="src/content/pages/index.html"
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
              placeholder="https://example.com"
            />
            <div className="font-mono text-[8px] mt-1" style={{ color: "var(--faint)" }}>
              Base URL without /wp-json
            </div>
          </div>
          <div>
            <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-2" style={{ color: "var(--faint)" }}>
              Username
            </div>
            <input
              className="w-full font-mono text-[12px] py-2 outline-none"
              style={{ background: "transparent", borderBottom: "1px solid var(--hair)", color: "var(--white)" }}
              value={cmsConfig.wp_username || ""}
              onChange={(e) => updateCmsField("wp_username", e.target.value)}
              placeholder="admin"
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
            <div className="font-mono text-[8px] mt-1" style={{ color: "var(--faint)" }}>
              Generate in WordPress → Users → Application Passwords
            </div>
          </div>
        </div>
      )}

      {cmsType === "shopify" && (
        <div className="space-y-4 mb-6">
          <div>
            <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-2" style={{ color: "var(--faint)" }}>
              Shop Domain
            </div>
            <input
              className="w-full font-mono text-[12px] py-2 outline-none"
              style={{ background: "transparent", borderBottom: "1px solid var(--hair)", color: "var(--white)" }}
              value={cmsConfig.shop_domain || ""}
              onChange={(e) => updateCmsField("shop_domain", e.target.value)}
              placeholder="your-store.myshopify.com"
            />
          </div>
          <div>
            <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-2" style={{ color: "var(--faint)" }}>
              Admin API Token
            </div>
            <input
              type="password"
              className="w-full font-mono text-[12px] py-2 outline-none"
              style={{ background: "transparent", borderBottom: "1px solid var(--hair)", color: "var(--white)" }}
              value={cmsConfig.api_token || ""}
              onChange={(e) => updateCmsField("api_token", e.target.value)}
              placeholder="shpat_..."
            />
            <div className="font-mono text-[8px] mt-1" style={{ color: "var(--faint)" }}>
              Create a custom app in Shopify Admin → Settings → Apps → Develop apps
            </div>
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
