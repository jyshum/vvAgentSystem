# GSC Integration & Implementation Routing

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pull Google Search Console metrics into tracker runs and route approved action cards to the right implementation handler based on client CMS type (starting with copy/paste export).

**Architecture:** GSC module authenticates via service account JSON, queries the Search Console API for per-query metrics (clicks, impressions, CTR, position), and stores them alongside tracker runs. A new `gsc_site_url` field on the `clients` table maps each client to their GSC property. Implementation routing reads `cms_type` from the client config and dispatches approved cards to the appropriate handler — starting with copy/paste which generates a formatted summary page on the dashboard.

**Tech Stack:** google-api-python-client, google-auth (already installed), Supabase, Next.js

---

## File Structure

**Backend (agents/):**
- Create: `src/gsc.py` — GSC reader module (auth, query, per-query metrics)
- Modify: `src/graph/nodes.py` — add GSC node, update load_config to include gsc_site_url and cms_type
- Modify: `src/graph/state.py` — add gsc_metrics field
- Modify: `src/graph/pipeline.py` — wire GSC node after tracker node
- Modify: `server.py` — add audit_run_id to initial state (already done)

**Database:**
- Create: `supabase/migrations/004_gsc_and_implementation.sql` — add gsc columns to tracker_runs, gsc_site_url to clients

**Dashboard:**
- Modify: `dashboard/lib/types.ts` — add GSC fields to TrackerRun, add gsc_site_url to Client
- Modify: `dashboard/components/admin/RunRow.tsx` — show GSC metrics columns
- Modify: `dashboard/app/admin/clients/[id]/runs/page.tsx` — add GSC column headers
- Modify: `dashboard/components/admin/ConfigForm.tsx` — add GSC site URL field
- Create: `dashboard/app/admin/clients/[id]/export/[runId]/page.tsx` — copy/paste export page for approved cards
- Modify: `dashboard/app/admin/clients/[id]/audit/[runId]/page.tsx` — add "Export Changes" link

---

### Task 1: Gitignore and env setup for GSC credentials

**Files:**
- Modify: `.gitignore`
- Modify: `agents/.env`

- [ ] **Step 1: Add GSC credentials to .gitignore**

Add to the end of `/Users/jshum/Desktop/code-folders/vvAgentSystem/.gitignore`:
```
# GSC credentials
gsc-credentials.json
**/gsc-credentials.json
```

- [ ] **Step 2: Add GSC_CREDENTIALS_PATH to agents/.env**

Add to `agents/.env`:
```
GSC_CREDENTIALS_PATH=gsc-credentials.json
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore agents/.env
git commit -m "chore: add GSC credentials to gitignore and env"
```

---

### Task 2: GSC reader module

**Files:**
- Create: `agents/src/gsc.py`
- Test: `agents/tests/test_gsc.py`

- [ ] **Step 1: Write the test**

```python
# agents/tests/test_gsc.py
from unittest.mock import patch, MagicMock
from src.gsc import fetch_gsc_metrics


def test_fetch_gsc_metrics_returns_per_query_data():
    mock_response = {
        "rows": [
            {"keys": ["best daycare toronto"], "clicks": 15, "impressions": 200, "ctr": 0.075, "position": 4.2},
            {"keys": ["childcare ontario"], "clicks": 8, "impressions": 120, "ctr": 0.067, "position": 6.1},
        ]
    }

    with patch("src.gsc._get_service") as mock_svc:
        mock_svc.return_value.searchanalytics.return_value.query.return_value.execute.return_value = mock_response
        result = fetch_gsc_metrics("https://www.example.com/", days=28)

    assert len(result["queries"]) == 2
    assert result["queries"][0]["query"] == "best daycare toronto"
    assert result["queries"][0]["clicks"] == 15
    assert result["totals"]["clicks"] == 23
    assert result["totals"]["impressions"] == 320


def test_fetch_gsc_metrics_no_data():
    with patch("src.gsc._get_service") as mock_svc:
        mock_svc.return_value.searchanalytics.return_value.query.return_value.execute.return_value = {}
        result = fetch_gsc_metrics("https://www.example.com/", days=28)

    assert result["queries"] == []
    assert result["totals"]["clicks"] == 0


def test_fetch_gsc_metrics_no_credentials():
    with patch("src.gsc._get_service", side_effect=FileNotFoundError("no creds")):
        result = fetch_gsc_metrics("https://www.example.com/", days=28)

    assert result["queries"] == []
    assert result["error"] == "no creds"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents && ../.venv/bin/pytest tests/test_gsc.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.gsc'`

- [ ] **Step 3: Implement the GSC module**

```python
# agents/src/gsc.py
import os
from datetime import datetime, timedelta, timezone


_service = None


def _get_service():
    global _service
    if _service is None:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds_path = os.environ.get("GSC_CREDENTIALS_PATH", "gsc-credentials.json")
        creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
        )
        _service = build("searchconsole", "v1", credentials=creds)
    return _service


def fetch_gsc_metrics(site_url: str, days: int = 28) -> dict:
    try:
        service = _get_service()
    except Exception as e:
        print(f"  GSC credentials error: {e}")
        return {"queries": [], "totals": {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0}, "error": str(e)}

    end = datetime.now(timezone.utc).date() - timedelta(days=3)
    start = end - timedelta(days=days)

    try:
        response = service.searchanalytics().query(
            siteUrl=site_url,
            body={
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
                "dimensions": ["query"],
                "rowLimit": 100,
            },
        ).execute()
    except Exception as e:
        print(f"  GSC API error: {e}")
        return {"queries": [], "totals": {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0}, "error": str(e)}

    rows = response.get("rows", [])
    queries = [
        {
            "query": row["keys"][0],
            "clicks": row["clicks"],
            "impressions": row["impressions"],
            "ctr": round(row["ctr"], 4),
            "position": round(row["position"], 1),
        }
        for row in rows
    ]

    total_clicks = sum(r["clicks"] for r in queries)
    total_impressions = sum(r["impressions"] for r in queries)
    avg_ctr = round(total_clicks / total_impressions, 4) if total_impressions > 0 else 0
    avg_position = round(sum(r["position"] * r["impressions"] for r in queries) / total_impressions, 1) if total_impressions > 0 else 0

    return {
        "queries": queries,
        "totals": {
            "clicks": total_clicks,
            "impressions": total_impressions,
            "ctr": avg_ctr,
            "position": avg_position,
        },
    }
```

- [ ] **Step 4: Run tests**

Run: `cd agents && ../.venv/bin/pytest tests/test_gsc.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add agents/src/gsc.py agents/tests/test_gsc.py
git commit -m "feat: add GSC reader module with per-query metrics"
```

---

### Task 3: Database migration for GSC fields

**Files:**
- Create: `supabase/migrations/004_gsc_and_implementation.sql`

- [ ] **Step 1: Write the migration**

```sql
-- supabase/migrations/004_gsc_and_implementation.sql

-- GSC site URL on clients
alter table public.clients
  add column if not exists gsc_site_url text default '';

-- GSC metrics on tracker_runs
alter table public.tracker_runs
  add column if not exists gsc_clicks int default 0,
  add column if not exists gsc_impressions int default 0,
  add column if not exists gsc_ctr float default 0,
  add column if not exists gsc_position float default 0,
  add column if not exists gsc_top_queries jsonb default '[]'::jsonb;
```

- [ ] **Step 2: Commit**

```bash
git add supabase/migrations/004_gsc_and_implementation.sql
git commit -m "feat: add GSC columns to clients and tracker_runs"
```

Note: User must run this migration manually in the Supabase SQL editor.

---

### Task 4: Wire GSC into the pipeline

**Files:**
- Modify: `agents/src/graph/state.py`
- Modify: `agents/src/graph/nodes.py`
- Modify: `agents/src/graph/pipeline.py`

- [ ] **Step 1: Add gsc_metrics to GEOState**

In `agents/src/graph/state.py`, add after `tracker_scores: dict`:
```python
    gsc_metrics: dict
```

- [ ] **Step 2: Update load_config to include gsc_site_url**

In `agents/src/graph/nodes.py`, update the `load_config` function's config dict to include:
```python
        "gsc_site_url": row.get("gsc_site_url", ""),
        "cms_type": row.get("cms_type", "copy_paste"),
        "cms_config": row.get("cms_config", {}),
```

- [ ] **Step 3: Add run_gsc_node**

In `agents/src/graph/nodes.py`, add after `run_tracker_node`:
```python
def run_gsc_node(state: GEOState) -> dict:
    gsc_site_url = state["client_config"].get("gsc_site_url", "")
    if not gsc_site_url:
        print("  GSC: no site URL configured, skipping")
        return {"gsc_metrics": {}}

    from src.gsc import fetch_gsc_metrics
    try:
        metrics = fetch_gsc_metrics(gsc_site_url)
        if metrics.get("error"):
            print(f"  GSC: {metrics['error']}")
        else:
            print(f"  GSC: {metrics['totals']['clicks']} clicks, {metrics['totals']['impressions']} impressions")

        # Save GSC data to the tracker_run row
        sb = _get_supabase()
        # Find the most recent tracker_run for this client to update
        latest = sb.table("tracker_runs") \
            .select("id") \
            .eq("client_id", state["client_id"]) \
            .order("ran_at", desc=True) \
            .limit(1) \
            .execute()

        if latest.data:
            sb.table("tracker_runs").update({
                "gsc_clicks": metrics["totals"]["clicks"],
                "gsc_impressions": metrics["totals"]["impressions"],
                "gsc_ctr": metrics["totals"]["ctr"],
                "gsc_position": metrics["totals"]["position"],
                "gsc_top_queries": metrics["queries"][:20],
            }).eq("id", latest.data[0]["id"]).execute()

        return {"gsc_metrics": metrics}
    except Exception as e:
        print(f"  GSC failed: {e}")
        return {"gsc_metrics": {}}
```

- [ ] **Step 4: Wire GSC node into pipeline**

In `agents/src/graph/pipeline.py`, the GSC node should run after the tracker node. In the `build_graph()` function, add `run_gsc_node` as an import and add an edge from `run_tracker` to `run_gsc` (or run it in parallel — depends on existing graph structure). Read the current pipeline.py to determine the exact wiring needed. The GSC node should only run when `run_type` is `"full"` or `"tracker_only"`.

- [ ] **Step 5: Update initial state in server.py**

In both `_run_graph_background` and `trigger_scheduled_run` in `agents/server.py`, add to the initial state dict:
```python
                "gsc_metrics": {},
```

- [ ] **Step 6: Commit**

```bash
git add agents/src/graph/state.py agents/src/graph/nodes.py agents/src/graph/pipeline.py agents/server.py
git commit -m "feat: wire GSC metrics into LangGraph pipeline"
```

---

### Task 5: GSC site URL in the config form

**Files:**
- Modify: `dashboard/components/admin/ConfigForm.tsx`
- Modify: `dashboard/lib/types.ts`

- [ ] **Step 1: Add gsc_site_url to Client type**

In `dashboard/lib/types.ts`, add after `cms_config`:
```typescript
  gsc_site_url: string;
```

- [ ] **Step 2: Add GSC field to ConfigForm**

In `dashboard/components/admin/ConfigForm.tsx`:

Add state:
```typescript
const [gscSiteUrl, setGscSiteUrl] = useState(client.gsc_site_url || "");
```

Add to the save function's update object:
```typescript
      gsc_site_url: gscSiteUrl,
```

Add field UI after the Website Domain field (before Brand Variations):
```tsx
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
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/components/admin/ConfigForm.tsx dashboard/lib/types.ts
git commit -m "feat: add GSC site URL to client config form"
```

---

### Task 6: Show GSC metrics on runs page

**Files:**
- Modify: `dashboard/lib/types.ts`
- Modify: `dashboard/app/admin/clients/[id]/runs/page.tsx`
- Modify: `dashboard/components/admin/RunRow.tsx`

- [ ] **Step 1: Add GSC fields to TrackerRun type**

In `dashboard/lib/types.ts`, add to the `TrackerRun` interface:
```typescript
  gsc_clicks: number;
  gsc_impressions: number;
  gsc_ctr: number;
  gsc_position: number;
  gsc_top_queries: { query: string; clicks: number; impressions: number; ctr: number; position: number }[];
```

- [ ] **Step 2: Update runs page header**

In `dashboard/app/admin/clients/[id]/runs/page.tsx`, change the grid columns and headers:

Change `gridTemplateColumns` from `"1.5fr 1fr 1fr 80px 1fr 190px"` to `"1.5fr 0.8fr 0.8fr 0.7fr 0.7fr 80px 150px"` in both the header div and the `RunRow` component props expectation.

Change headers array from `["CLIENT", "MENTION", "CITATION", "LAST RUN", ""]` to `["DATE", "MENTION", "CITATION", "GSC CLICKS", "GSC POS", "QUERIES", "ACTIONS"]`.

- [ ] **Step 3: Update RunRow component**

In `dashboard/components/admin/RunRow.tsx`:

Update `gridTemplateColumns` to `"1.5fr 0.8fr 0.8fr 0.7fr 0.7fr 80px 150px"`.

Add GSC columns after the Citation column:
```tsx
      {/* GSC Clicks */}
      <div>
        <div className="font-display font-light text-[22px] leading-none"
          style={{ color: run.gsc_clicks > 0 ? "var(--white)" : "var(--faint)" }}>
          {run.gsc_clicks > 0 ? run.gsc_clicks : "—"}
        </div>
      </div>

      {/* GSC Position */}
      <div>
        <div className="font-display font-light text-[22px] leading-none"
          style={{ color: run.gsc_position > 0 && run.gsc_position <= 10 ? "var(--pos)" : run.gsc_position > 10 ? "var(--yellow, #facc15)" : "var(--faint)" }}>
          {run.gsc_position > 0 ? run.gsc_position.toFixed(1) : "—"}
        </div>
      </div>
```

Remove the STATUS column (it's redundant — the data presence already indicates success).

- [ ] **Step 4: Commit**

```bash
git add dashboard/lib/types.ts dashboard/app/admin/clients/\[id\]/runs/page.tsx dashboard/components/admin/RunRow.tsx
git commit -m "feat: show GSC clicks and position on runs page"
```

---

### Task 7: Copy/paste export page for approved cards

**Files:**
- Create: `dashboard/app/admin/clients/[id]/export/[runId]/page.tsx`
- Modify: `dashboard/app/admin/clients/[id]/audit/[runId]/page.tsx`

- [ ] **Step 1: Create the export page**

```tsx
// dashboard/app/admin/clients/[id]/export/[runId]/page.tsx
export const dynamic = "force-dynamic";

import { createAdminClient } from "@/lib/supabase/admin";
import { notFound } from "next/navigation";
import Link from "next/link";

export default async function ExportPage({
  params,
}: {
  params: Promise<{ id: string; runId: string }>;
}) {
  const { id, runId } = await params;
  const supabase = createAdminClient();

  const [{ data: client }, { data: run }, { data: cards }] = await Promise.all([
    supabase.from("clients").select("brand_name, website_domain").eq("id", id).single(),
    supabase.from("audit_runs").select("ran_at, site_score").eq("id", runId).single(),
    supabase
      .from("action_cards")
      .select("*")
      .eq("run_id", runId)
      .in("status", ["approved", "implemented"])
      .order("page_url"),
  ]);

  if (!run || !client) notFound();

  const allCards = cards || [];
  const grouped: Record<string, typeof allCards> = {};
  for (const card of allCards) {
    const url = card.page_url;
    if (!grouped[url]) grouped[url] = [];
    grouped[url].push(card);
  }

  return (
    <div style={{ maxWidth: 800 }}>
      <Link
        href={`/admin/clients/${id}/audit/${runId}`}
        className="inline-block font-mono text-[10px] tracking-[0.1em] uppercase mb-6 transition-colors hover:text-[var(--white)]"
        style={{ color: "var(--faint)", textDecoration: "none" }}
      >
        &larr; Back to Audit
      </Link>

      <div className="mb-8">
        <h1 className="font-display text-[36px] font-light leading-tight mb-2" style={{ color: "var(--white)" }}>
          Implementation Guide
        </h1>
        <div className="font-mono text-[9px] tracking-[0.1em]" style={{ color: "var(--faint)" }}>
          {client.brand_name} · {new Date(run.ran_at).toLocaleDateString("en-CA", { year: "numeric", month: "short", day: "numeric" })} · {allCards.length} change{allCards.length !== 1 ? "s" : ""}
        </div>
      </div>

      {allCards.length === 0 ? (
        <p className="font-serif italic" style={{ color: "var(--mute)" }}>
          No approved cards for this audit run. Go back and approve some action cards first.
        </p>
      ) : (
        Object.entries(grouped).map(([url, pageCards]) => (
          <div key={url} className="mb-10">
            <div className="mb-4 pb-2" style={{ borderBottom: "1px solid var(--hair)" }}>
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-[11px] transition-colors hover:text-[var(--white)]"
                style={{ color: "var(--mute)", textDecoration: "none" }}
              >
                {url} ↗
              </a>
            </div>

            <div className="space-y-6">
              {pageCards.map((card) => (
                <div key={card.id} className="pl-4" style={{ borderLeft: "2px solid var(--hair)" }}>
                  <div className="font-mono text-[8px] tracking-[0.14em] uppercase mb-2" style={{ color: "var(--faint)" }}>
                    {card.pillar} · Score: {card.score}/100
                  </div>

                  <p className="font-serif text-[13px] mb-3" style={{ color: "var(--white)" }}>
                    {card.issue}
                  </p>

                  {card.before_text && (
                    <div className="mb-3">
                      <div className="font-mono text-[8px] tracking-[0.1em] uppercase mb-1" style={{ color: "var(--neg)" }}>
                        Find this text:
                      </div>
                      <pre className="font-mono text-[11px] p-3 whitespace-pre-wrap leading-relaxed" style={{ background: "rgba(232,154,160,0.05)", color: "var(--mute)", border: "1px solid rgba(232,154,160,0.15)" }}>
                        {card.before_text}
                      </pre>
                    </div>
                  )}

                  {card.after_text && (
                    <div className="mb-3">
                      <div className="font-mono text-[8px] tracking-[0.1em] uppercase mb-1" style={{ color: "var(--pos)" }}>
                        Replace with:
                      </div>
                      <pre className="font-mono text-[11px] p-3 whitespace-pre-wrap leading-relaxed" style={{ background: "rgba(132,216,171,0.05)", color: "var(--mute)", border: "1px solid rgba(132,216,171,0.15)" }}>
                        {card.after_text}
                      </pre>
                    </div>
                  )}

                  {card.code_block && (
                    <div className="mb-3">
                      <div className="font-mono text-[8px] tracking-[0.1em] uppercase mb-1" style={{ color: "var(--blue, #60a5fa)" }}>
                        Add this code:
                      </div>
                      <pre className="font-mono text-[11px] p-3 whitespace-pre-wrap leading-relaxed" style={{ background: "rgba(96,165,250,0.05)", color: "var(--mute)", border: "1px solid rgba(96,165,250,0.15)" }}>
                        {card.code_block}
                      </pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add export link to audit run detail page**

In `dashboard/app/admin/clients/[id]/audit/[runId]/page.tsx`, add an "Export Changes" link next to the "Back to Audit Runs" link at the top:

```tsx
      <div className="flex items-center justify-between">
        <Link
          href={`/admin/clients/${id}/audit`}
          className="inline-block font-mono text-[10px] tracking-[0.1em] uppercase transition-colors hover:text-[var(--white)]"
          style={{ color: "var(--faint)", textDecoration: "none" }}
        >
          &larr; Back to Audit Runs
        </Link>
        {allCards.length > 0 && (
          <Link
            href={`/admin/clients/${id}/export/${runId}`}
            className="font-mono text-[10px] tracking-[0.14em] uppercase py-2.5 px-5 transition-all duration-200 hover:opacity-80"
            style={{ background: "var(--white)", color: "var(--ink)", textDecoration: "none" }}
          >
            EXPORT CHANGES
          </Link>
        )}
      </div>
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/app/admin/clients/\[id\]/export/\[runId\]/page.tsx dashboard/app/admin/clients/\[id\]/audit/\[runId\]/page.tsx
git commit -m "feat: add copy/paste export page for approved action cards"
```

---

## Self-Review

**Spec coverage:** ✅ GSC reader, pipeline integration, dashboard display, config form, export page, migration — all covered.

**Placeholder scan:** ✅ No TBD/TODO. All code blocks complete. Pipeline wiring in Task 4 Step 4 references reading the existing pipeline.py which the implementer will need to do — this is intentional since graph wiring depends on the exact current structure.

**Type consistency:** ✅ `fetch_gsc_metrics` returns `{"queries": [...], "totals": {...}}` consistently. `gsc_site_url` used everywhere. TrackerRun GSC fields match migration column names.
