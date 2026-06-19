# Dashboard Frontend Overhaul — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up all missing admin pages (CONFIG, RUNS, RUN DETAIL, REPORTS, REPORT EDITOR/VIEW) in the existing Next.js 16 dashboard, add a Railway trigger API route, and update `agents/run.py` to fetch config from Supabase and write results back.

**Architecture:** The existing `/dashboard` Next.js app already has auth, design system, Supabase client/server helpers, types, and the `ReportEditor`/`ReportView` components. The work is: restructure the client detail route into a tabbed layout, create each missing sub-page, add one new API route to trigger Railway, and update the Python tracker's CLI to support `--client-id`.

**Tech Stack:** Next.js 16 (App Router), Tailwind CSS, Supabase SSR, Railway GraphQL API, Python 3 (agents/run.py)

---

## What Already Exists (do not rebuild)

- `dashboard/lib/supabase/` — client, server, admin, middleware helpers
- `dashboard/lib/types.ts` — `Client`, `TrackerRun`, `TrackerResult`, `Report`, `SearchConsoleMetrics`
- `dashboard/lib/utils.ts` — `scoreColor`, `formatRate`, `formatDelta`, `weekRangeLabel`
- `dashboard/app/globals.css` + `tailwind.config.ts` — full design system tokens
- `dashboard/components/admin/ReportEditor.tsx` — complete split-pane editor
- `dashboard/components/report/ReportView.tsx`, `KPIGrid.tsx`, `CompetitorTable.tsx`, `QueryResultsTable.tsx`, `ReportHeader.tsx`
- `dashboard/components/ui/` — `Card`, `Badge`, `Button`, `Input`, `SectionLabel`, `PrintButton`
- `dashboard/app/admin/layout.tsx` — nav + admin auth guard
- `dashboard/app/login/` — login page + callback

## What Gets Removed / Replaced

- `dashboard/app/admin/clients/[id]/page.tsx` — replaced by layout + redirect in Task 3
- `dashboard/components/admin/InviteClientForm.tsx` — no longer used (out of scope)
- `dashboard/app/admin/reports/[id]/page.tsx` — replace with redirect to new URL

---

## File Map

```
dashboard/
  app/
    admin/
      page.tsx                                    MODIFY (table format)
      clients/
        [id]/
          layout.tsx                              CREATE (sub-nav chrome)
          page.tsx                                REPLACE (redirect to /config)
          config/
            page.tsx                              CREATE
          runs/
            page.tsx                              CREATE
            [runId]/
              page.tsx                            CREATE
          reports/
            page.tsx                              CREATE
            [reportId]/
              page.tsx                            CREATE
              view/
                page.tsx                          CREATE
      reports/
        [id]/
          page.tsx                                REPLACE (redirect)
    api/
      runs/
        trigger/
          route.ts                                CREATE
  components/
    admin/
      ClientRow.tsx                               CREATE
      TagInput.tsx                                CREATE
      ConfigForm.tsx                              CREATE
      TriggerRunButton.tsx                        CREATE
      RunDetail.tsx                               CREATE
agents/
  run.py                                          MODIFY
```

---

## Task 1: Backend — update `agents/run.py` for `--client-id`

**Files:**
- Modify: `agents/run.py`

The tracker already has `run_tracker(config)` in `agents/src/tracker.py`. This task adds a `--client-id` flag that fetches config from Supabase instead of a local JSON file, and writes results back to Supabase after the run.

- [ ] **Step 1: Add `supabase-py` to the agents requirements if not present**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents
cat requirements.txt
```

If `supabase` is not listed, add it:
```
supabase>=2.0.0
```

Then install: `pip install -r requirements.txt`

- [ ] **Step 2: Read the existing `agents/run.py` to understand current structure**

```bash
cat /Users/jshum/Desktop/code-folders/vvAgentSystem/agents/run.py
```

Note the current `load_client_config(args.config)` call and how results/scores are handled after `run_tracker()`.

- [ ] **Step 3: Add `--client-id` flag and Supabase fetch to `run.py`**

Add at the top of `agents/run.py` (after existing imports):

```python
import os
from supabase import create_client

def fetch_config_from_supabase(client_id: str) -> dict:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(url, key)
    result = supabase.table("clients").select("*").eq("id", client_id).single().execute()
    row = result.data
    return {
        "brand_name": row["brand_name"],
        "website_domain": row["website_domain"],
        "brand_variations": row["brand_variations"] or [],
        "target_queries": row["target_queries"] or [],
        "competitors": row["competitors"] or [],
    }

def write_results_to_supabase(client_id: str, scores: dict, results: list) -> str:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(url, key)

    run_row = supabase.table("tracker_runs").insert({
        "client_id": client_id,
        "aggregate_mention_rate": scores.get("aggregate_mention_rate", 0),
        "aggregate_citation_rate": scores.get("aggregate_citation_rate", 0),
        "per_engine_scores": scores.get("per_engine_scores", {}),
        "competitor_scores": scores.get("competitor_scores", {}),
    }).execute()

    run_id = run_row.data[0]["id"]

    result_rows = [{
        "run_id": run_id,
        "query": r["query"],
        "engine": r["engine"],
        "model": r.get("model", ""),
        "brand_mentioned": r["brand_mentioned"],
        "brand_cited": r["brand_cited"],
        "citation_url": r.get("citation_url"),
        "competitor_mentions": r.get("competitor_mentions", []),
        "response_text": r.get("response_text", ""),
    } for r in results]

    supabase.table("tracker_results").insert(result_rows).execute()
    return run_id
```

- [ ] **Step 4: Update `main()` in `run.py` to handle both flags**

In the argument parser section, add alongside the existing `--config` arg:

```python
parser.add_argument("--client-id", help="Supabase client UUID (fetches config from DB)")
```

In the main execution block, replace the single `load_client_config(args.config)` call with:

```python
if args.client_id:
    config = fetch_config_from_supabase(args.client_id)
else:
    config = load_client_config(args.config)
```

After `results, scores = run_tracker(config)`, add:

```python
if args.client_id:
    run_id = write_results_to_supabase(args.client_id, scores, results)
    print(f"Results written to Supabase. Run ID: {run_id}")
```

- [ ] **Step 5: Test locally with ChildSpot's real client ID**

Set env vars and run:
```bash
export SUPABASE_URL="<from dashboard/.env.local>"
export SUPABASE_SERVICE_KEY="<service role key from Supabase dashboard>"
cd agents
python run.py --client-id 302eb603-3a0c-4429-bd8e-191ac30a965a
```

Expected: tracker runs, prints "Results written to Supabase. Run ID: <uuid>"

Verify in Supabase: `tracker_runs` has a new row, `tracker_results` has 31–32 new rows for that run.

- [ ] **Step 6: Commit**

```bash
git add agents/run.py
git commit -m "feat: add --client-id flag to run.py, fetch config from Supabase and write results back"
```

---

## Task 2: Railway trigger API route

**Files:**
- Create: `dashboard/app/api/runs/trigger/route.ts`

This route receives `{ clientId }`, calls the Railway GraphQL API to set `CLIENT_ID` as a service variable and trigger a redeploy, and returns the deployment ID.

Required env vars (add to `dashboard/.env.local` and Railway/Vercel):
```
RAILWAY_API_TOKEN=<from railway.app → Account Settings → Tokens>
RAILWAY_SERVICE_ID=<from Railway project → service → Settings → Service ID>
RAILWAY_ENVIRONMENT_ID=<from Railway project → environment settings>
```

- [ ] **Step 1: Create the route file**

```typescript
// dashboard/app/api/runs/trigger/route.ts
import { createClient } from "@/lib/supabase/server";
import { NextRequest, NextResponse } from "next/server";

const RAILWAY_API = "https://backboard.railway.app/graphql/v2";

async function railwayGraphQL(query: string, variables: Record<string, unknown>) {
  const res = await fetch(RAILWAY_API, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${process.env.RAILWAY_API_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query, variables }),
  });
  const json = await res.json();
  if (json.errors) throw new Error(json.errors[0].message);
  return json.data;
}

export async function POST(req: NextRequest) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { clientId } = await req.json();
  if (!clientId) return NextResponse.json({ error: "clientId required" }, { status: 400 });

  // Verify client exists
  const { data: client } = await supabase.from("clients").select("id").eq("id", clientId).single();
  if (!client) return NextResponse.json({ error: "Client not found" }, { status: 404 });

  // Set CLIENT_ID variable on Railway service
  await railwayGraphQL(`
    mutation variableUpsert($input: VariableUpsertInput!) {
      variableUpsert(input: $input)
    }
  `, {
    input: {
      serviceId: process.env.RAILWAY_SERVICE_ID,
      environmentId: process.env.RAILWAY_ENVIRONMENT_ID,
      name: "CLIENT_ID",
      value: clientId,
    },
  });

  // Trigger redeployment
  const data = await railwayGraphQL(`
    mutation serviceInstanceRedeploy($serviceId: String!, $environmentId: String!) {
      serviceInstanceRedeploy(serviceId: $serviceId, environmentId: $environmentId)
    }
  `, {
    serviceId: process.env.RAILWAY_SERVICE_ID!,
    environmentId: process.env.RAILWAY_ENVIRONMENT_ID!,
  });

  return NextResponse.json({ ok: true, data });
}
```

- [ ] **Step 2: Write a unit test for the auth guard**

```typescript
// dashboard/__tests__/api/runs/trigger.test.ts
import { POST } from "@/app/api/runs/trigger/route";
import { NextRequest } from "next/server";

// Mock supabase
jest.mock("@/lib/supabase/server", () => ({
  createClient: jest.fn().mockResolvedValue({
    auth: { getUser: jest.fn().mockResolvedValue({ data: { user: null } }) },
  }),
}));

test("returns 401 when not authenticated", async () => {
  const req = new NextRequest("http://localhost/api/runs/trigger", {
    method: "POST",
    body: JSON.stringify({ clientId: "abc" }),
  });
  const res = await POST(req);
  expect(res.status).toBe(401);
});
```

Run: `cd dashboard && npx vitest run __tests__/api/runs/trigger.test.ts`

- [ ] **Step 3: Commit**

```bash
git add dashboard/app/api/runs/trigger/route.ts dashboard/__tests__/api/runs/trigger.test.ts
git commit -m "feat: add /api/runs/trigger route to trigger Railway tracker deployment"
```

---

## Task 3: Update clients list to table format

**Files:**
- Create: `dashboard/components/admin/ClientRow.tsx`
- Modify: `dashboard/app/admin/page.tsx`

- [ ] **Step 1: Create `ClientRow.tsx`**

```typescript
// dashboard/components/admin/ClientRow.tsx
import Link from "next/link";
import { scoreColor, formatRate, formatDelta } from "@/lib/utils";
import type { Client, TrackerRun, Report } from "@/lib/types";

interface ClientRowProps {
  client: Client;
  latestRun: TrackerRun | null;
  previousRun: TrackerRun | null;
  latestReport: Report | null;
}

export function ClientRow({ client, latestRun, previousRun, latestReport }: ClientRowProps) {
  const mentionDelta = latestRun && previousRun
    ? formatDelta(latestRun.aggregate_mention_rate, previousRun.aggregate_mention_rate)
    : null;

  const isStale = latestRun
    ? (Date.now() - new Date(latestRun.ran_at).getTime()) > 7 * 24 * 60 * 60 * 1000
    : true;

  return (
    <Link
      href={`/admin/clients/${client.id}/runs`}
      className="grid items-center py-5 px-4 border-b transition-all duration-200 group"
      style={{
        gridTemplateColumns: "2fr 1fr 1fr 1.4fr 1fr",
        gap: "16px",
        borderColor: "var(--hair)",
      }}
    >
      {/* Client name + domain */}
      <div className="group-hover:pl-3 transition-all duration-200">
        <div className="font-serif text-[18px]" style={{ color: "var(--white)" }}>
          {client.name}
        </div>
        <div className="font-mono text-[9px] tracking-[0.08em] mt-0.5" style={{ color: "var(--faint)" }}>
          {client.website_domain}
        </div>
      </div>

      {/* Mention rate */}
      <div>
        {latestRun ? (
          <>
            <div className="font-display text-[26px] font-light leading-none"
              style={{ color: scoreColor(latestRun.aggregate_mention_rate) }}>
              {formatRate(latestRun.aggregate_mention_rate)}
            </div>
            {mentionDelta && (
              <div className="font-mono text-[8px] mt-1" style={{
                color: mentionDelta.direction === "up" ? "var(--pos)"
                  : mentionDelta.direction === "down" ? "var(--neg)"
                  : "var(--faint)"
              }}>
                {mentionDelta.text}
              </div>
            )}
          </>
        ) : (
          <span className="font-mono text-[11px]" style={{ color: "var(--faint)" }}>—</span>
        )}
      </div>

      {/* Citation rate */}
      <div>
        {latestRun ? (
          <div className="font-display text-[26px] font-light leading-none"
            style={{ color: scoreColor(latestRun.aggregate_citation_rate) }}>
            {formatRate(latestRun.aggregate_citation_rate)}
          </div>
        ) : (
          <span className="font-mono text-[11px]" style={{ color: "var(--faint)" }}>—</span>
        )}
      </div>

      {/* Last run */}
      <div>
        {latestRun ? (
          <>
            <div className="font-mono text-[10px] tracking-[0.06em]" style={{ color: "var(--mute)" }}>
              {new Date(latestRun.ran_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
            </div>
            <div className="inline-flex items-center gap-1.5 mt-1.5 font-mono text-[8px] tracking-[0.1em] px-1.5 py-0.5 rounded-sm"
              style={isStale
                ? { background: "rgba(232,154,160,0.08)", color: "var(--neg)", border: "1px solid rgba(232,154,160,0.18)" }
                : { background: "rgba(132,216,171,0.1)", color: "var(--pos)", border: "1px solid rgba(132,216,171,0.2)" }
              }>
              <span className="w-1 h-1 rounded-full bg-current inline-block" />
              {isStale ? "STALE" : "CURRENT"}
            </div>
          </>
        ) : (
          <span className="font-mono text-[10px]" style={{ color: "var(--faint)" }}>No runs yet</span>
        )}
      </div>

      {/* Latest report */}
      <div>
        {latestReport ? (
          <span className="font-mono text-[9px] tracking-[0.1em] py-1.5 px-3 transition-colors"
            style={{ color: "var(--faint)", border: "1px solid var(--ghost)" }}
            onClick={(e) => { e.preventDefault(); window.location.href = `/admin/clients/${client.id}/reports/${latestReport.id}/view`; }}>
            VIEW ↗
          </span>
        ) : (
          <span className="font-mono text-[9px]" style={{ color: "var(--faint)", opacity: 0.4 }}>no report yet</span>
        )}
      </div>
    </Link>
  );
}
```

- [ ] **Step 2: Update `app/admin/page.tsx` to table layout**

Replace the entire return block with:

```typescript
// dashboard/app/admin/page.tsx
import { createClient } from "@/lib/supabase/server";
import { ClientRow } from "@/components/admin/ClientRow";
import type { Client, TrackerRun, Report } from "@/lib/types";

export default async function AdminPage() {
  const supabase = await createClient();

  const { data: clients } = await supabase
    .from("clients")
    .select("*")
    .order("created_at", { ascending: true });

  const allClients = (clients as Client[]) || [];

  const clientsWithData = await Promise.all(
    allClients.map(async (client) => {
      const { data: runs } = await supabase
        .from("tracker_runs")
        .select("*")
        .eq("client_id", client.id)
        .order("ran_at", { ascending: false })
        .limit(2);

      const { data: reports } = await supabase
        .from("reports")
        .select("*")
        .eq("client_id", client.id)
        .order("created_at", { ascending: false })
        .limit(1);

      const allRuns = (runs as TrackerRun[]) || [];
      return {
        client,
        latestRun: allRuns[0] || null,
        previousRun: allRuns[1] || null,
        latestReport: ((reports as Report[]) || [])[0] || null,
      };
    })
  );

  return (
    <>
      <div className="flex items-end justify-between mb-10">
        <div>
          <h1 className="font-display text-[clamp(34px,4.4vw,58px)] font-light leading-[1.02] tracking-[-0.01em]"
            style={{ color: "var(--white)" }}>
            Clients
          </h1>
          <p className="font-serif italic text-base mt-1" style={{ color: "var(--mute)" }}>
            {allClients.length} active account{allClients.length !== 1 ? "s" : ""}
          </p>
        </div>
      </div>

      {/* Table header */}
      <div className="grid px-4 pb-3 border-b" style={{
        gridTemplateColumns: "2fr 1fr 1fr 1.4fr 1fr",
        gap: "16px",
        borderColor: "var(--hair)"
      }}>
        {["CLIENT", "MENTION", "CITATION", "LAST RUN", "REPORT"].map((h) => (
          <div key={h} className="font-mono text-[8px] tracking-[0.18em]" style={{ color: "var(--faint)" }}>
            {h}
          </div>
        ))}
      </div>

      {allClients.length === 0 ? (
        <p className="font-serif italic text-base py-10" style={{ color: "var(--mute)" }}>
          No clients yet.
        </p>
      ) : (
        clientsWithData.map(({ client, latestRun, previousRun, latestReport }) => (
          <ClientRow
            key={client.id}
            client={client}
            latestRun={latestRun}
            previousRun={previousRun}
            latestReport={latestReport}
          />
        ))
      )}
    </>
  );
}
```

- [ ] **Step 3: Verify visually**

```bash
cd dashboard && npm run dev
```

Open `http://localhost:3000/admin`. Confirm table format with column headers, client rows, and hover indent.

- [ ] **Step 4: Commit**

```bash
git add dashboard/components/admin/ClientRow.tsx dashboard/app/admin/page.tsx
git commit -m "feat: update clients list to editorial table format"
```

---

## Task 4: Client detail — shared layout with sub-nav tabs

**Files:**
- Create: `dashboard/app/admin/clients/[id]/layout.tsx`
- Replace: `dashboard/app/admin/clients/[id]/page.tsx` (redirect to /config)

- [ ] **Step 1: Create the shared client layout**

```typescript
// dashboard/app/admin/clients/[id]/layout.tsx
import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import Link from "next/link";
import type { Client } from "@/lib/types";

export default async function ClientLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();

  const { data: client } = await supabase
    .from("clients")
    .select("id, name, website_domain")
    .eq("id", id)
    .single();

  if (!client) notFound();
  const c = client as Pick<Client, "id" | "name" | "website_domain">;

  const tabs = [
    { label: "CONFIG", href: `/admin/clients/${id}/config` },
    { label: "RUNS", href: `/admin/clients/${id}/runs` },
    { label: "REPORTS", href: `/admin/clients/${id}/reports` },
  ];

  return (
    <div>
      {/* Breadcrumb */}
      <Link
        href="/admin"
        className="font-mono text-[11px] tracking-[0.16em] uppercase inline-block mb-6 transition-colors hover:text-[var(--mute)]"
        style={{ color: "var(--faint)" }}
      >
        ← Clients
      </Link>

      {/* Client header */}
      <div className="mb-6">
        <h1 className="font-display text-[clamp(34px,4.8vw,60px)] font-light leading-[1.02] tracking-[-0.02em]"
          style={{ color: "var(--white)" }}>
          {c.name}
        </h1>
        <div className="font-mono text-[10px] tracking-[0.1em] uppercase mt-1" style={{ color: "var(--faint)" }}>
          {c.website_domain}
        </div>
      </div>

      {/* Sub-nav */}
      <div className="flex gap-0 mb-10 border-b" style={{ borderColor: "var(--hair)" }}>
        {tabs.map((tab) => (
          <SubTab key={tab.label} label={tab.label} href={tab.href} />
        ))}
      </div>

      {children}
    </div>
  );
}

// Client component to detect active tab
// Note: usePathname requires "use client" — use a separate component
import { SubTab } from "@/components/admin/SubTab";
```

- [ ] **Step 2: Create `components/admin/SubTab.tsx`**

```typescript
// dashboard/components/admin/SubTab.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function SubTab({ label, href }: { label: string; href: string }) {
  const pathname = usePathname();
  const isActive = pathname.startsWith(href);

  return (
    <Link
      href={href}
      className="font-mono text-[9px] tracking-[0.16em] pb-3 px-1 mr-8 border-b-2 transition-all duration-200"
      style={{
        color: isActive ? "var(--white)" : "var(--faint)",
        borderColor: isActive ? "var(--white)" : "transparent",
      }}
    >
      {label}
    </Link>
  );
}
```

- [ ] **Step 3: Update the import in layout.tsx**

The layout.tsx above already imports `SubTab`. Make sure the import is at the top of the file (not inside the function):

```typescript
import { SubTab } from "@/components/admin/SubTab";
```

Remove the comment-style import at the bottom if you followed Step 1 exactly.

- [ ] **Step 4: Replace `page.tsx` with redirect**

```typescript
// dashboard/app/admin/clients/[id]/page.tsx
import { redirect } from "next/navigation";

export default async function ClientDetailRoot({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/admin/clients/${id}/config`);
}
```

- [ ] **Step 5: Redirect old report editor route**

```typescript
// dashboard/app/admin/reports/[id]/page.tsx
// Replace entire file content:
import { createClient } from "@/lib/supabase/server";
import { redirect, notFound } from "next/navigation";

export default async function OldReportRoute({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();
  const { data: report } = await supabase
    .from("reports")
    .select("id, client_id")
    .eq("id", id)
    .single();
  if (!report) notFound();
  redirect(`/admin/clients/${report.client_id}/reports/${id}`);
}
```

- [ ] **Step 6: Commit**

```bash
git add "dashboard/app/admin/clients/[id]/layout.tsx" "dashboard/app/admin/clients/[id]/page.tsx" dashboard/components/admin/SubTab.tsx "dashboard/app/admin/reports/[id]/page.tsx"
git commit -m "feat: add tabbed client detail layout (CONFIG / RUNS / REPORTS)"
```

---

## Task 5: Config page

**Files:**
- Create: `dashboard/components/admin/TagInput.tsx`
- Create: `dashboard/components/admin/ConfigForm.tsx`
- Create: `dashboard/app/admin/clients/[id]/config/page.tsx`

- [ ] **Step 1: Create `TagInput.tsx`**

```typescript
// dashboard/components/admin/TagInput.tsx
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
        className="w-full font-mono text-[12px] tracking-[0.04em] bg-transparent border-b py-2 outline-none transition-colors focus:border-[var(--mute)] placeholder:text-[var(--faint)]"
        style={{ borderColor: "var(--hair)", color: "var(--white)" }}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={onKey}
        onBlur={add}
        placeholder={placeholder || "Type and press Enter"}
      />
    </div>
  );
}
```

- [ ] **Step 2: Create `ConfigForm.tsx`**

```typescript
// dashboard/components/admin/ConfigForm.tsx
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

  async function save() {
    setSaving(true);
    const supabase = createClient();
    await supabase.from("clients").update({
      brand_name: brandName,
      website_domain: domain,
      brand_variations: variations,
      target_queries: queries,
      competitors: competitors,
    }).eq("id", client.id);
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  const fieldStyle = {
    background: "transparent",
    borderBottom: "1px solid var(--hair)",
    color: "var(--white)",
  };

  return (
    <div className="max-w-2xl">
      <div className="mb-6">
        <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-2" style={{ color: "var(--faint)" }}>
          Brand Name
        </div>
        <input
          className="w-full font-serif text-[16px] py-2 outline-none focus:border-b-[var(--mute)] transition-colors"
          style={fieldStyle}
          value={brandName}
          onChange={(e) => setBrandName(e.target.value)}
        />
      </div>

      <div className="mb-6">
        <div className="font-mono text-[9px] tracking-[0.16em] uppercase mb-2" style={{ color: "var(--faint)" }}>
          Website Domain
        </div>
        <input
          className="w-full font-mono text-[12px] py-2 outline-none transition-colors"
          style={fieldStyle}
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
    </div>
  );
}
```

- [ ] **Step 3: Create the config page**

```typescript
// dashboard/app/admin/clients/[id]/config/page.tsx
import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import { ConfigForm } from "@/components/admin/ConfigForm";
import type { Client } from "@/lib/types";

export default async function ConfigPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();

  const { data: client } = await supabase
    .from("clients")
    .select("*")
    .eq("id", id)
    .single();

  if (!client) notFound();

  return <ConfigForm client={client as Client} />;
}
```

- [ ] **Step 4: Verify — navigate to `/admin/clients/<id>/config`, edit a tag, click SAVE, refresh to confirm it persisted**

- [ ] **Step 5: Commit**

```bash
git add dashboard/components/admin/TagInput.tsx dashboard/components/admin/ConfigForm.tsx "dashboard/app/admin/clients/[id]/config/page.tsx"
git commit -m "feat: add config page with tag inputs for queries, competitors, brand variations"
```

---

## Task 6: Runs list + trigger button

**Files:**
- Create: `dashboard/components/admin/TriggerRunButton.tsx`
- Create: `dashboard/app/admin/clients/[id]/runs/page.tsx`

- [ ] **Step 1: Create `TriggerRunButton.tsx`**

```typescript
// dashboard/components/admin/TriggerRunButton.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function TriggerRunButton({ clientId }: { clientId: string }) {
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");
  const router = useRouter();

  async function trigger() {
    setState("loading");
    try {
      const res = await fetch("/api/runs/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clientId }),
      });
      if (!res.ok) throw new Error();
      setState("done");
      setTimeout(() => {
        setState("idle");
        router.refresh();
      }, 3000);
    } catch {
      setState("error");
      setTimeout(() => setState("idle"), 3000);
    }
  }

  const labels = {
    idle: "RUN TRACKER →",
    loading: "TRIGGERING…",
    done: "TRIGGERED ✓",
    error: "ERROR — RETRY",
  };

  const colors = {
    idle: { background: "transparent", color: "var(--white)", border: "1px solid var(--ghost)" },
    loading: { background: "transparent", color: "var(--faint)", border: "1px solid var(--hair)" },
    done: { background: "rgba(132,216,171,0.1)", color: "var(--pos)", border: "1px solid rgba(132,216,171,0.3)" },
    error: { background: "rgba(232,154,160,0.08)", color: "var(--neg)", border: "1px solid rgba(232,154,160,0.2)" },
  };

  return (
    <button
      onClick={trigger}
      disabled={state === "loading"}
      className="font-mono text-[9px] tracking-[0.14em] uppercase py-3 px-5 transition-all duration-200"
      style={colors[state]}
    >
      {labels[state]}
    </button>
  );
}
```

- [ ] **Step 2: Create the runs page**

```typescript
// dashboard/app/admin/clients/[id]/runs/page.tsx
import { createClient } from "@/lib/supabase/server";
import Link from "next/link";
import { TriggerRunButton } from "@/components/admin/TriggerRunButton";
import { scoreColor, formatRate } from "@/lib/utils";
import type { TrackerRun, Report } from "@/lib/types";

export default async function RunsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();

  const { data: runs } = await supabase
    .from("tracker_runs")
    .select("*")
    .eq("client_id", id)
    .order("ran_at", { ascending: false });

  const { data: reports } = await supabase
    .from("reports")
    .select("id, run_id")
    .eq("client_id", id);

  const allRuns = (runs as TrackerRun[]) || [];
  const reportedRunIds = new Set((reports || []).map((r) => r.run_id).filter(Boolean));

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div className="font-mono text-[8px] tracking-[0.18em] uppercase" style={{ color: "var(--faint)" }}>
          {allRuns.length} run{allRuns.length !== 1 ? "s" : ""}
        </div>
        <TriggerRunButton clientId={id} />
      </div>

      {allRuns.length === 0 ? (
        <p className="font-serif italic" style={{ color: "var(--mute)" }}>
          No runs yet. Click RUN TRACKER to start the first one.
        </p>
      ) : (
        <>
          {/* Table header */}
          <div className="grid pb-3 border-b font-mono text-[8px] tracking-[0.18em] uppercase"
            style={{ gridTemplateColumns: "1.6fr 1fr 1fr 1fr auto", gap: "16px", borderColor: "var(--hair)", color: "var(--faint)" }}>
            <span>DATE</span><span>MENTION</span><span>CITATION</span><span>STATUS</span><span></span>
          </div>

          {allRuns.map((run) => (
            <div key={run.id}
              className="grid items-center py-4 border-b transition-all duration-200 group"
              style={{ gridTemplateColumns: "1.6fr 1fr 1fr 1fr auto", gap: "16px", borderColor: "var(--hair)" }}>
              <Link href={`/admin/clients/${id}/runs/${run.id}`}
                className="font-mono text-[11px] tracking-[0.06em] group-hover:pl-2 transition-all duration-200"
                style={{ color: "var(--mute)" }}>
                {new Date(run.ran_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" })}
              </Link>
              <span className="font-display text-[22px] font-light" style={{ color: scoreColor(run.aggregate_mention_rate) }}>
                {formatRate(run.aggregate_mention_rate)}
              </span>
              <span className="font-display text-[22px] font-light" style={{ color: scoreColor(run.aggregate_citation_rate) }}>
                {formatRate(run.aggregate_citation_rate)}
              </span>
              <span className="font-mono text-[8px] tracking-[0.1em]" style={{ color: reportedRunIds.has(run.id) ? "var(--faint)" : "var(--mute)" }}>
                {reportedRunIds.has(run.id) ? "report exists" : "no report"}
              </span>
              <div className="flex gap-2">
                <Link href={`/admin/clients/${id}/runs/${run.id}`}
                  className="font-mono text-[8px] tracking-[0.1em] uppercase py-1.5 px-3 transition-all duration-200 hover:text-white"
                  style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}>
                  VIEW
                </Link>
                {!reportedRunIds.has(run.id) && (
                  <Link href={`/api/admin/create-report?runId=${run.id}&clientId=${id}`}
                    className="font-mono text-[8px] tracking-[0.1em] uppercase py-1.5 px-3 transition-all duration-200 hover:text-white"
                    style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}>
                    → MAKE REPORT
                  </Link>
                )}
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify — navigate to `/admin/clients/<id>/runs`, confirm runs table, trigger button visible**

- [ ] **Step 4: Commit**

```bash
git add dashboard/components/admin/TriggerRunButton.tsx "dashboard/app/admin/clients/[id]/runs/page.tsx"
git commit -m "feat: add runs list page with Railway trigger button"
```

---

## Task 7: Run detail page

**Files:**
- Create: `dashboard/components/admin/RunDetail.tsx`
- Create: `dashboard/app/admin/clients/[id]/runs/[runId]/page.tsx`

This is the most complex page. It shows KPIs, per-engine bars, competitor SoV, citation URLs, and all query results with expandable AI excerpts. The data comes from `tracker_runs` (aggregate) + `tracker_results` (per query×engine).

- [ ] **Step 1: Create `RunDetail.tsx`**

```typescript
// dashboard/components/admin/RunDetail.tsx
"use client";

import { useState } from "react";
import Link from "next/link";
import { scoreColor, formatRate } from "@/lib/utils";
import type { TrackerRun, TrackerResult, Client } from "@/lib/types";

interface RunDetailProps {
  run: TrackerRun;
  results: TrackerResult[];
  client: Client;
  clientId: string;
}

const ENGINES = ["chatgpt", "perplexity", "claude", "gemini"];
const ENGINES_DISPLAY: Record<string, string> = {
  chatgpt: "CHATGPT", perplexity: "PERPLEXITY", claude: "CLAUDE", gemini: "GEMINI",
};

function Badge({ mentioned, cited }: { mentioned: boolean; cited: boolean }) {
  if (cited) return (
    <span className="font-mono text-[8px] tracking-[0.1em] py-0.5 px-2"
      style={{ color: "var(--pos)", border: "1px solid rgba(132,216,171,0.3)", background: "rgba(132,216,171,0.08)" }}>
      CITED
    </span>
  );
  if (mentioned) return (
    <span className="font-mono text-[8px] tracking-[0.1em] py-0.5 px-2"
      style={{ color: "var(--mute)", border: "1px solid var(--ghost)" }}>
      MENTIONED
    </span>
  );
  return (
    <span className="font-mono text-[8px] tracking-[0.1em]" style={{ color: "var(--faint)" }}>
      — not found
    </span>
  );
}

function ExcerptRow({ result }: { result: TrackerResult }) {
  const [open, setOpen] = useState(false);
  const snippet = result.response_text?.slice(0, 280);

  return (
    <div className="flex gap-4 py-3 border-b" style={{ borderColor: "var(--hair)" }}>
      <span className="font-mono text-[9px] tracking-[0.1em] w-24 shrink-0 pt-0.5" style={{ color: "var(--mute)" }}>
        {ENGINES_DISPLAY[result.engine] || result.engine.toUpperCase()}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3 mb-1">
          <Badge mentioned={result.brand_mentioned} cited={result.brand_cited} />
          {result.citation_url && (
            <span className="font-mono text-[8px] tracking-[0.06em]" style={{ color: "var(--pos)" }}>
              ↗ {result.citation_url}
            </span>
          )}
        </div>
        {(result.brand_mentioned || result.brand_cited) && result.response_text && (
          <div>
            <p className="font-mono text-[10px] leading-relaxed" style={{ color: "var(--mute)" }}>
              {open ? result.response_text : `${snippet}${result.response_text.length > 280 ? "…" : ""}`}
            </p>
            {result.response_text.length > 280 && (
              <button onClick={() => setOpen(!open)}
                className="font-mono text-[8px] tracking-[0.1em] uppercase mt-1 transition-colors hover:text-white"
                style={{ color: "var(--faint)" }}>
                {open ? "↑ collapse" : "··· read full"}
              </button>
            )}
          </div>
        )}
        {result.competitor_mentions && result.competitor_mentions.length > 0 && (
          <p className="font-mono text-[8px] mt-1" style={{ color: "var(--faint)" }}>
            competitors: {result.competitor_mentions.join(", ")}
          </p>
        )}
      </div>
    </div>
  );
}

export function RunDetail({ run, results, client, clientId }: RunDetailProps) {
  const [showAll, setShowAll] = useState(false);

  // Group results by query
  const queries = Array.from(new Set(results.map((r) => r.query)));
  const byQuery = (q: string) => results.filter((r) => r.query === q);

  // Per-engine stats
  const engineStats = ENGINES.map((eng) => {
    const engineResults = results.filter((r) => r.engine === eng);
    return {
      engine: eng,
      total: engineResults.length,
      cited: engineResults.filter((r) => r.brand_cited).length,
      mentioned: engineResults.filter((r) => r.brand_mentioned && !r.brand_cited).length,
      notFound: engineResults.filter((r) => !r.brand_mentioned).length,
    };
  });

  // Competitor SoV
  const compCounts: Record<string, number> = {};
  results.forEach((r) => {
    (r.competitor_mentions || []).forEach((c) => {
      compCounts[c] = (compCounts[c] || 0) + 1;
    });
  });
  const competitors = Object.entries(compCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 7);
  const maxCompMentions = competitors[0]?.[1] || 1;

  // Citation URLs
  const citationUrls: Record<string, string[]> = {};
  results.filter((r) => r.brand_cited && r.citation_url).forEach((r) => {
    const url = r.citation_url!;
    if (!citationUrls[url]) citationUrls[url] = [];
    citationUrls[url].push(ENGINES_DISPLAY[r.engine] || r.engine);
  });

  const INITIAL_QUERY_COUNT = 3;
  const visibleQueries = showAll ? queries : queries.slice(0, INITIAL_QUERY_COUNT);

  return (
    <div style={{ maxWidth: 960, margin: "0 auto" }}>
      {/* Header */}
      <div className="flex items-end justify-between mb-8">
        <div>
          <h2 className="font-display text-[36px] font-light">
            {new Date(run.ran_at).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
          </h2>
          <p className="font-mono text-[9px] tracking-[0.1em] mt-1.5" style={{ color: "var(--faint)" }}>
            {new Date(run.ran_at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })} · {results.length} responses
          </p>
        </div>
        <Link
          href={`/api/admin/create-report?runId=${run.id}&clientId=${clientId}`}
          className="font-mono text-[9px] tracking-[0.14em] uppercase py-3 px-5 transition-all duration-200 hover:bg-white hover:text-[var(--ink)]"
          style={{ color: "var(--white)", border: "1px solid var(--ghost)" }}
        >
          → MAKE REPORT
        </Link>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-4 border mb-10" style={{ borderColor: "var(--hair)", gap: 1, background: "var(--hair)" }}>
        {[
          { n: formatRate(run.aggregate_mention_rate), l: "MENTION RATE", color: scoreColor(run.aggregate_mention_rate) },
          { n: formatRate(run.aggregate_citation_rate), l: "CITATION RATE", color: scoreColor(run.aggregate_citation_rate) },
          { n: String(results.length), l: "RESPONSES", color: "var(--mute)" },
          { n: String(results.filter((r) => r.brand_cited).length), l: "CITATIONS", color: "var(--mute)" },
        ].map(({ n, l, color }) => (
          <div key={l} className="py-4 px-5" style={{ background: "var(--ink)" }}>
            <div className="font-display text-[38px] font-light leading-none mb-1.5" style={{ color }}>{n}</div>
            <div className="font-mono text-[8px] tracking-[0.14em]" style={{ color: "var(--faint)" }}>{l}</div>
          </div>
        ))}
      </div>

      {/* Per-engine breakdown */}
      <div className="font-mono text-[8px] tracking-[0.18em] uppercase mb-4" style={{ color: "var(--faint)" }}>
        PER-ENGINE BREAKDOWN
      </div>
      <div className="grid grid-cols-4 gap-3 mb-10">
        {engineStats.map(({ engine, total, cited, mentioned, notFound }) => {
          const citedPct = total ? (cited / total) * 100 : 0;
          const mentionedPct = total ? (mentioned / total) * 100 : 0;
          const notFoundPct = total ? (notFound / total) * 100 : 0;
          return (
            <div key={engine} className="p-4 border" style={{ borderColor: "var(--hair)" }}>
              <div className="font-mono text-[9px] tracking-[0.14em] mb-3" style={{ color: "var(--mute)" }}>
                {ENGINES_DISPLAY[engine]}
              </div>
              {/* Stacked bar */}
              <div className="flex h-1 rounded-sm overflow-hidden mb-3">
                <div style={{ width: `${citedPct}%`, background: "var(--pos)" }} />
                <div style={{ width: `${mentionedPct}%`, background: "rgba(132,216,171,0.35)" }} />
                <div style={{ width: `${notFoundPct}%`, background: "var(--hair)" }} />
              </div>
              <div className="flex flex-col gap-1.5">
                {[
                  { label: "CITED", val: cited, color: "var(--pos)" },
                  { label: "MENTIONED", val: mentioned, color: "var(--mute)" },
                  { label: "NOT FOUND", val: notFound, color: "var(--faint)" },
                ].map(({ label, val, color }) => (
                  <div key={label} className="flex justify-between">
                    <span className="font-mono text-[8px]" style={{ color }}>● {label}</span>
                    <span className="font-mono text-[9px]" style={{ color: val > 0 ? "var(--white)" : "var(--faint)" }}>
                      {val} / {total}
                    </span>
                  </div>
                ))}
              </div>
              {total < 8 && (
                <div className="font-mono text-[7px] mt-2 opacity-60" style={{ color: "var(--faint)" }}>
                  skipped {8 - total} query
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Competitor SoV */}
      {competitors.length > 0 && (
        <>
          <div className="font-mono text-[8px] tracking-[0.18em] uppercase mb-4" style={{ color: "var(--faint)" }}>
            COMPETITOR SHARE OF VOICE
          </div>
          <table className="w-full border-collapse mb-10">
            <thead>
              <tr className="border-b" style={{ borderColor: "var(--hair)" }}>
                {["BRAND", "APPEARANCES", "RATE"].map((h) => (
                  <th key={h} className="font-mono text-[8px] tracking-[0.12em] uppercase pb-2.5 text-left" style={{ color: "var(--faint)" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {/* Brand row first */}
              <tr className="border-b" style={{ borderColor: "var(--hair)" }}>
                <td className="py-3 font-serif text-sm" style={{ color: "var(--pos)" }}>{client.brand_name}</td>
                <td className="py-3">
                  <div className="h-0.5 bg-[var(--pos)]" style={{ width: `${(run.aggregate_mention_rate / 1) * 200}px`, maxWidth: "200px" }} />
                </td>
                <td className="py-3 font-mono text-[10px]" style={{ color: "var(--pos)" }}>
                  {formatRate(run.aggregate_mention_rate)}
                </td>
              </tr>
              {competitors.map(([name, count]) => (
                <tr key={name} className="border-b" style={{ borderColor: "var(--hair)" }}>
                  <td className="py-3 font-serif text-sm" style={{ color: "var(--mute)" }}>{name}</td>
                  <td className="py-3">
                    <div className="h-0.5" style={{
                      width: `${(count / maxCompMentions) * 200 * 0.7}px`,
                      maxWidth: "200px",
                      background: "var(--ghost)"
                    }} />
                  </td>
                  <td className="py-3 font-mono text-[10px]" style={{ color: "var(--faint)" }}>
                    {Math.round((count / results.length) * 100)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {/* Citation URLs */}
      <div className="font-mono text-[8px] tracking-[0.18em] uppercase mb-4" style={{ color: "var(--faint)" }}>
        CITATION URLS DISCOVERED
      </div>
      {Object.keys(citationUrls).length === 0 ? (
        <p className="font-mono text-[9px] pb-8" style={{ color: "var(--faint)" }}>
          No URLs cited this run.
        </p>
      ) : (
        <div className="mb-8">
          {Object.entries(citationUrls).map(([url, engines]) => (
            <div key={url} className="flex items-center gap-4 py-3 border-b" style={{ borderColor: "var(--hair)" }}>
              <span className="font-mono text-[10px] tracking-[0.04em]" style={{ color: "var(--white)" }}>{url}</span>
              <span className="font-mono text-[8px]" style={{ color: "var(--faint)" }}>{engines.join(" · ")}</span>
              <span className="font-mono text-[8px] ml-auto" style={{ color: "var(--faint)" }}>{engines.length} citation{engines.length !== 1 ? "s" : ""}</span>
            </div>
          ))}
        </div>
      )}

      {/* Query results */}
      <div className="flex items-center justify-between mb-4">
        <div className="font-mono text-[8px] tracking-[0.18em] uppercase" style={{ color: "var(--faint)" }}>
          QUERY RESULTS <span className="ml-2 opacity-50">{queries.length} queries · {results.length} responses</span>
        </div>
      </div>

      {visibleQueries.map((query) => (
        <div key={query} className="mb-6 pb-6 border-b" style={{ borderColor: "var(--hair)" }}>
          <div className="font-serif italic text-base mb-2" style={{ color: "var(--mute)" }}>
            "{query}"
          </div>
          {byQuery(query).every((r) => !r.brand_mentioned) && (
            <div className="font-mono text-[8px] tracking-[0.08em] mb-1" style={{ color: "var(--neg)" }}>
              Zero mentions — content gap
            </div>
          )}
          {byQuery(query).map((result) => (
            <ExcerptRow key={result.id} result={result} />
          ))}
        </div>
      ))}

      {queries.length > INITIAL_QUERY_COUNT && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="w-full font-mono text-[9px] tracking-[0.14em] uppercase py-4 transition-all duration-200 hover:text-white"
          style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}
        >
          {showAll
            ? "COLLAPSE QUERIES ↑"
            : `SHOW ${queries.length - INITIAL_QUERY_COUNT} MORE QUERIES ↓`}
        </button>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create the run detail page**

```typescript
// dashboard/app/admin/clients/[id]/runs/[runId]/page.tsx
import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import { RunDetail } from "@/components/admin/RunDetail";
import type { TrackerRun, TrackerResult, Client } from "@/lib/types";

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string; runId: string }>;
}) {
  const { id, runId } = await params;
  const supabase = await createClient();

  const [{ data: run }, { data: results }, { data: client }] = await Promise.all([
    supabase.from("tracker_runs").select("*").eq("id", runId).single(),
    supabase.from("tracker_results").select("*").eq("run_id", runId).order("queried_at"),
    supabase.from("clients").select("*").eq("id", id).single(),
  ]);

  if (!run || !client) notFound();

  return (
    <RunDetail
      run={run as TrackerRun}
      results={(results as TrackerResult[]) || []}
      client={client as Client}
      clientId={id}
    />
  );
}
```

- [ ] **Step 3: Verify — open a run, confirm all sections render, expand a query excerpt, test "SHOW MORE QUERIES"**

- [ ] **Step 4: Commit**

```bash
git add dashboard/components/admin/RunDetail.tsx "dashboard/app/admin/clients/[id]/runs/[runId]/page.tsx"
git commit -m "feat: add run detail page with per-engine breakdown, competitor SoV, and expandable query results"
```

---

## Task 8: Reports list page

**Files:**
- Create: `dashboard/app/admin/clients/[id]/reports/page.tsx`

- [ ] **Step 1: Create the reports list page**

```typescript
// dashboard/app/admin/clients/[id]/reports/page.tsx
import { createClient } from "@/lib/supabase/server";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { weekRangeLabel } from "@/lib/utils";
import type { Report } from "@/lib/types";

export default async function ReportsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();

  const { data: reports } = await supabase
    .from("reports")
    .select("*")
    .eq("client_id", id)
    .order("created_at", { ascending: false });

  const allReports = (reports as Report[]) || [];

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div className="font-mono text-[8px] tracking-[0.18em] uppercase" style={{ color: "var(--faint)" }}>
          {allReports.length} report{allReports.length !== 1 ? "s" : ""}
        </div>
        {/* Blank report creation — links to create-report with no runId */}
        <Link
          href={`/api/admin/create-report?clientId=${id}`}
          className="font-mono text-[9px] tracking-[0.14em] uppercase py-3 px-5 transition-all duration-200 hover:text-white"
          style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}
        >
          + NEW BLANK REPORT
        </Link>
      </div>

      {allReports.length === 0 ? (
        <p className="font-serif italic" style={{ color: "var(--mute)" }}>
          No reports yet. Go to RUNS to create a report from a tracker run.
        </p>
      ) : (
        <>
          <div className="grid pb-3 border-b font-mono text-[8px] tracking-[0.18em] uppercase"
            style={{ gridTemplateColumns: "1fr auto auto", gap: "24px", borderColor: "var(--hair)", color: "var(--faint)" }}>
            <span>WEEK</span><span>STATUS</span><span></span>
          </div>

          {allReports.map((report) => (
            <div key={report.id} className="grid items-center py-4 border-b group"
              style={{ gridTemplateColumns: "1fr auto auto", gap: "24px", borderColor: "var(--hair)" }}>
              <Link
                href={`/admin/clients/${id}/reports/${report.id}`}
                className="font-serif italic text-base group-hover:pl-3 transition-all duration-200"
                style={{ color: "var(--white)" }}
              >
                {weekRangeLabel(report.week_start) || "Untitled report"}
              </Link>
              <Badge variant={report.status === "published" ? "published" : "draft"}>
                {report.status}
              </Badge>
              <div className="flex gap-2">
                <Link href={`/admin/clients/${id}/reports/${report.id}`}
                  className="font-mono text-[8px] tracking-[0.1em] uppercase py-1.5 px-3 transition-colors hover:text-white"
                  style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}>
                  EDIT
                </Link>
                <Link href={`/admin/clients/${id}/reports/${report.id}/view`}
                  className="font-mono text-[8px] tracking-[0.1em] uppercase py-1.5 px-3 transition-colors hover:text-white"
                  style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}>
                  VIEW ↗
                </Link>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Update `app/api/admin/create-report/route.ts` to support blank reports (no `runId`)**

Read the existing file first:
```bash
cat "dashboard/app/api/admin/create-report/route.ts"
```

Ensure it handles the case where `runId` is absent (blank report):

```typescript
// If runId is missing, create report without run association
const runId = searchParams.get("runId") || null;
const clientId = searchParams.get("clientId");
```

And the insert should use `run_id: runId` (null if blank).

After creating, redirect to `/admin/clients/${clientId}/reports/${newReport.id}` instead of the old `/admin/reports/${newReport.id}`.

- [ ] **Step 3: Verify — navigate to REPORTS tab, create a blank report, confirm redirect to editor**

- [ ] **Step 4: Commit**

```bash
git add "dashboard/app/admin/clients/[id]/reports/page.tsx" "dashboard/app/api/admin/create-report/route.ts"
git commit -m "feat: add reports list page and update create-report redirect to new URL"
```

---

## Task 9: Report editor and view pages

**Files:**
- Create: `dashboard/app/admin/clients/[id]/reports/[reportId]/page.tsx`
- Create: `dashboard/app/admin/clients/[id]/reports/[reportId]/view/page.tsx`

The `ReportEditor` and `ReportView` components already exist. These pages just fetch data and wire them up.

- [ ] **Step 1: Create the report editor page**

```typescript
// dashboard/app/admin/clients/[id]/reports/[reportId]/page.tsx
import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import { ReportEditor } from "@/components/admin/ReportEditor";
import type { Report, TrackerRun, TrackerResultClient, Client } from "@/lib/types";

export default async function ReportEditorPage({
  params,
}: {
  params: Promise<{ id: string; reportId: string }>;
}) {
  const { id, reportId } = await params;
  const supabase = await createClient();

  const { data: report } = await supabase
    .from("reports")
    .select("*")
    .eq("id", reportId)
    .eq("client_id", id)
    .single();

  if (!report) notFound();
  const typedReport = report as Report;

  const [{ data: client }, runData, resultsData] = await Promise.all([
    supabase.from("clients").select("*").eq("id", id).single(),
    typedReport.run_id
      ? supabase.from("tracker_runs").select("*").eq("id", typedReport.run_id).single()
      : { data: null },
    typedReport.run_id
      ? supabase.from("tracker_results")
          .select("id, run_id, query, engine, model, brand_mentioned, brand_cited, citation_url, competitor_mentions, queried_at")
          .eq("run_id", typedReport.run_id)
      : { data: [] },
  ]);

  const { data: previousRuns } = await supabase
    .from("tracker_runs")
    .select("*")
    .eq("client_id", id)
    .order("ran_at", { ascending: false })
    .limit(5);

  if (!client) notFound();

  return (
    <ReportEditor
      initialReport={typedReport}
      run={(runData?.data as TrackerRun) || null}
      results={(resultsData?.data as TrackerResultClient[]) || []}
      client={client as Client}
      previousRuns={(previousRuns as TrackerRun[]) || []}
    />
  );
}
```

- [ ] **Step 2: Create the report view (PDF) page**

```typescript
// dashboard/app/admin/clients/[id]/reports/[reportId]/view/page.tsx
import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import Link from "next/link";
import { ReportView } from "@/components/report/ReportView";
import { PrintButton } from "@/components/ui/PrintButton";
import type { ReportWithRun, Client } from "@/lib/types";

export default async function ReportViewPage({
  params,
}: {
  params: Promise<{ id: string; reportId: string }>;
}) {
  const { id, reportId } = await params;
  const supabase = await createClient();

  const { data: report } = await supabase
    .from("reports")
    .select("*, tracker_run:tracker_runs(*)")
    .eq("id", reportId)
    .eq("client_id", id)
    .single();

  if (!report) notFound();

  const { data: client } = await supabase
    .from("clients")
    .select("*")
    .eq("id", id)
    .single();

  if (!client) notFound();

  return (
    <div style={{ background: "#080809", minHeight: "calc(100vh - 78px)" }}>
      {/* Top bar */}
      <div className="no-print flex items-center justify-between px-6 h-12 border-b"
        style={{ background: "rgba(14,14,15,0.7)", borderColor: "var(--hair)" }}>
        <Link href={`/admin/clients/${id}/reports`}
          className="font-mono text-[9px] tracking-[0.12em] transition-colors hover:text-white"
          style={{ color: "var(--faint)" }}>
          ← Reports
        </Link>
        <div className="flex gap-2">
          <Link href={`/admin/clients/${id}/reports/${reportId}`}
            className="font-mono text-[9px] tracking-[0.1em] uppercase py-1.5 px-4 transition-colors hover:text-white"
            style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}>
            EDIT
          </Link>
          <PrintButton />
        </div>
      </div>

      {/* Paper */}
      <div className="px-6 py-10">
        <ReportView report={report as ReportWithRun} client={client as Client} />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify — open a report from the list, confirm editor loads with correct data, click VIEW to see clean paper view, test PRINT button**

- [ ] **Step 4: Commit**

```bash
git add "dashboard/app/admin/clients/[id]/reports/[reportId]/page.tsx" "dashboard/app/admin/clients/[id]/reports/[reportId]/view/page.tsx"
git commit -m "feat: add report editor and read-only view pages"
```

---

## Task 10: Final wiring — deploy to Vercel

- [ ] **Step 1: Add missing env vars to Vercel**

In the Vercel dashboard for this project, add:
```
RAILWAY_API_TOKEN=<token>
RAILWAY_SERVICE_ID=<service id>
RAILWAY_ENVIRONMENT_ID=<environment id>
```

`SUPABASE_URL` and `SUPABASE_ANON_KEY` should already be set from the initial deploy.

- [ ] **Step 2: Push and deploy**

```bash
git push origin master
```

Monitor Vercel build. Fix any TypeScript errors before continuing.

- [ ] **Step 3: Smoke test production**

1. Log in at `/login`
2. `/admin` — client list shows ChildSpot with real mention/citation rates
3. Click ChildSpot → redirects to CONFIG tab, all fields populated
4. RUNS tab → run history table, RUN TRACKER button visible
5. Click a run → run detail page loads with per-engine breakdown and query results
6. REPORTS tab → reports list, EDIT/VIEW actions work
7. Open a report editor — SAVE DRAFT works, PUBLISH works
8. VIEW → clean paper document, PRINT button triggers browser print dialog

- [ ] **Step 4: Set up Railway service**

In Railway:
1. Create a new service pointing to the `agents/` directory
2. Set start command: `python run.py --client-id $CLIENT_ID`
3. Add env vars: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `PERPLEXITY_API_KEY`
4. Note the Service ID and Environment ID for the Vercel env vars

---

## Self-Review Checklist

- [x] **Spec: Admin-only** — no client portal, no invite system referenced
- [x] **Spec: Railway trigger** — Task 2 covers the `/api/runs/trigger` route
- [x] **Spec: Separate pages** — CONFIG/RUNS/REPORTS are distinct routes with shared layout
- [x] **Spec: Runs ≠ Reports** — "→ MAKE REPORT" is always a manual click; no auto-promotion
- [x] **Spec: Run detail** — Task 7 covers KPIs, per-engine, SoV, citation URLs, query results with show-more
- [x] **Spec: Report editor** — uses existing ReportEditor component, wired in Task 9
- [x] **Spec: Infrastructure gap** — Task 1 fixes `run.py` to accept `--client-id` and write to Supabase
- [x] **Spec: Design system** — uses existing Tailwind tokens and CSS vars throughout
- [x] **Types consistent** — `TrackerRun`, `TrackerResult`, `Client`, `Report` used consistently from `lib/types.ts`
- [x] **No placeholders** — every step has concrete code or commands
