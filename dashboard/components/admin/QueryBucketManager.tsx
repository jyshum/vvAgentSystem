"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { BUCKET_DETAILS, BUCKET_LABELS } from "@/lib/intent-labels";
import type { Query } from "@/lib/types";

const BUCKETS: { key: Query["bucket"]; label: string; detail: string }[] = [
  { key: "consideration", label: BUCKET_LABELS.consideration, detail: BUCKET_DETAILS.consideration },
  { key: "awareness", label: BUCKET_LABELS.awareness, detail: BUCKET_DETAILS.awareness },
  { key: "branded", label: BUCKET_LABELS.branded, detail: BUCKET_DETAILS.branded },
];

export function QueryBucketManager({
  clientId,
  initialQueries,
}: {
  clientId: string;
  initialQueries: Query[];
}) {
  const router = useRouter();
  const [queries, setQueries] = useState(initialQueries);
  const [drafts, setDrafts] = useState<Record<Query["bucket"], string>>({
    awareness: "",
    consideration: "",
    branded: "",
  });
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [bulkText, setBulkText] = useState("");
  const [bulkBusy, setBulkBusy] = useState(false);

  const grouped = useMemo(() => {
    return BUCKETS.map((bucket) => ({
      ...bucket,
      queries: queries.filter((q) => q.bucket === bucket.key && q.status === "active"),
    }));
  }, [queries]);

  async function addQuery(bucket: Query["bucket"]) {
    const prompt = drafts[bucket].trim();
    if (!prompt) return;
    setError(null);
    setBusyId(bucket);
    const res = await fetch(`/api/admin/queries/${clientId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt_text: prompt, bucket, set_type: "core" }),
    });
    setBusyId(null);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      setError(body.error || "Could not add query");
      return;
    }
    const created = (await res.json()) as Query;
    setQueries((current) => [...current, created]);
    setDrafts((current) => ({ ...current, [bucket]: "" }));
    router.refresh();
  }

  async function bulkImport() {
    setError(null);
    let intents: unknown;
    try {
      intents = JSON.parse(bulkText);
    } catch {
      setError("Paste must be a valid JSON array of intents");
      return;
    }
    if (!Array.isArray(intents)) {
      setError("Expected a JSON array");
      return;
    }
    setBulkBusy(true);
    const res = await fetch(`/api/admin/queries/${clientId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intents }),
    });
    setBulkBusy(false);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      setError(body.error || "Bulk import failed");
      return;
    }
    const created = (await res.json()) as Query[];
    setQueries((current) => [...current, ...created]);
    setBulkText("");
    router.refresh();
  }

  async function moveQuery(query: Query, bucket: Query["bucket"]) {
    if (query.bucket === bucket) return;
    setError(null);
    setBusyId(query.id);
    const res = await fetch(`/api/admin/queries/query/${query.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bucket }),
    });
    setBusyId(null);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      setError(body.error || "Could not move query");
      return;
    }
    const updated = (await res.json()) as Query;
    setQueries((current) => current.map((q) => (q.id === updated.id ? updated : q)));
    router.refresh();
  }

  async function retireQuery(query: Query) {
    setError(null);
    setBusyId(query.id);
    const res = await fetch(`/api/admin/queries/query/${query.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "retired" }),
    });
    setBusyId(null);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      setError(body.error || "Could not retire query");
      return;
    }
    const updated = (await res.json()) as Query;
    setQueries((current) => current.map((q) => (q.id === updated.id ? updated : q)));
    router.refresh();
  }

  return (
    <div className="mb-10 mt-10 pt-8" style={{ borderTop: "1px solid var(--hair)" }}>
      <div className="flex items-end justify-between gap-4 mb-5">
        <div>
          <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-2" style={{ color: "var(--faint)" }}>
            Intent Set
          </div>
          <p className="font-serif text-[13px]" style={{ color: "var(--mute)" }}>
            Product Visibility and Content Authority intents are measured separately. Branded monitoring is deferred.
          </p>
        </div>
        <div className="font-mono text-[9px] tracking-[0.12em]" style={{ color: "var(--faint)" }}>
          {queries.filter((q) => q.status === "active").length} ACTIVE
        </div>
      </div>

      {error && (
        <div className="font-mono text-[9px] mb-4" style={{ color: "var(--neg)" }}>
          {error}
        </div>
      )}

      <details className="mb-5">
        <summary className="font-mono text-[9px] tracking-[0.14em] uppercase cursor-pointer" style={{ color: "var(--faint)" }}>
          Bulk import intents (paste JSON)
        </summary>
        <textarea
          value={bulkText}
          onChange={(e) => setBulkText(e.target.value)}
          placeholder='[{"prompt_text":"best daycare software","bucket":"consideration","paraphrases":["top childcare apps"]}]'
          className="w-full min-h-[120px] mt-3 resize-y bg-transparent font-mono text-[11px] leading-snug outline-none placeholder:opacity-40"
          style={{ color: "var(--white)", border: "1px solid var(--hair)", padding: "10px" }}
        />
        <button
          type="button"
          disabled={bulkBusy || !bulkText.trim()}
          onClick={bulkImport}
          className="mt-2 font-mono text-[9px] tracking-[0.14em] uppercase py-2.5 px-5 transition-opacity disabled:opacity-40"
          style={{ background: "var(--white)", color: "var(--ink)" }}
        >
          {bulkBusy ? "Importing" : "Import Intents"}
        </button>
      </details>

      <div className="grid grid-cols-1 lg:grid-cols-3" style={{ gap: 1, background: "var(--hair)", border: "1px solid var(--hair)" }}>
        {grouped.map((bucket) => (
          <section key={bucket.key} className="p-4" style={{ background: "var(--ink)" }}>
            <div className="flex items-baseline justify-between gap-3 mb-1">
              <h3 className="font-display text-[22px] font-light" style={{ color: "var(--white)" }}>
                {bucket.label}
              </h3>
              <span className="font-mono text-[9px]" style={{ color: "var(--faint)" }}>
                {bucket.queries.length}
              </span>
            </div>
            <p className="font-serif text-[12px] mb-4" style={{ color: "var(--mute)" }}>
              {bucket.detail}
            </p>

            <div className="flex flex-col gap-2 min-h-[160px]">
              {bucket.queries.map((query) => (
                <div key={query.id} className="group py-2.5" style={{ borderTop: "1px solid var(--hair)" }}>
                  <div className="font-serif text-[13px] leading-snug" style={{ color: "var(--white)" }}>
                    {query.prompt_text}
                  </div>
                  {query.paraphrases?.length > 0 && (
                    <div className="font-mono text-[8px] tracking-[0.08em] mt-1" style={{ color: "var(--faint)" }}>
                      {query.paraphrases.length + 1} WORDINGS
                    </div>
                  )}
                  <div className="flex items-center gap-2 mt-2">
                    <select
                      value={query.bucket}
                      disabled={busyId === query.id}
                      onChange={(e) => moveQuery(query, e.target.value as Query["bucket"])}
                      className="bg-transparent font-mono text-[9px] uppercase outline-none"
                      style={{ color: "var(--faint)" }}
                    >
                      {BUCKETS.map((b) => (
                        <option key={b.key} value={b.key} style={{ background: "var(--ink)" }}>
                          {b.label}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      disabled={busyId === query.id}
                      onClick={() => retireQuery(query)}
                      className="font-mono text-[9px] uppercase transition-colors disabled:opacity-50"
                      style={{ color: "var(--faint)" }}
                    >
                      Retire
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-4 pt-3" style={{ borderTop: "1px solid var(--hair)" }}>
              <textarea
                value={drafts[bucket.key]}
                onChange={(e) => setDrafts((current) => ({ ...current, [bucket.key]: e.target.value }))}
                placeholder={`Add ${bucket.label.toLowerCase()} prompt`}
                className="w-full min-h-[78px] resize-y bg-transparent font-serif text-[13px] leading-snug outline-none placeholder:opacity-40"
                style={{ color: "var(--white)" }}
              />
              <button
                type="button"
                disabled={busyId === bucket.key || !drafts[bucket.key].trim()}
                onClick={() => addQuery(bucket.key)}
                className="mt-2 w-full font-mono text-[9px] tracking-[0.14em] uppercase py-2.5 transition-opacity disabled:opacity-40"
                style={{ background: "var(--white)", color: "var(--ink)" }}
              >
                {busyId === bucket.key ? "Adding" : "Add Prompt"}
              </button>
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
