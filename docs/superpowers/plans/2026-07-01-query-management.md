# Phase 4: Query Management — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat `target_queries` array with a dedicated `queries` table supporting bucket classification, set types, and status lifecycle, with CRUD API endpoints and tracker integration.

**Architecture:** A new `queries` table stores each prompt as a managed entity. A migration populates it from existing `target_queries` data. The tracker pipeline's config-loading step switches to reading from the `queries` table. CRUD API endpoints enable admin management. The rest of the pipeline (tracker.py, upload.py) is unchanged.

**Tech Stack:** SQL migration (Supabase), Python (config loading), Next.js API routes (TypeScript), Supabase client

---

## File Structure

### Database (new)
- `supabase/migrations/007_queries.sql` — queries table + data migration

### Backend (modified)
- `agents/src/graph/nodes.py` — `load_config()` reads from queries table
- `agents/run.py` — `fetch_config_from_supabase()` reads from queries table

### Dashboard (new)
- `dashboard/app/api/admin/queries/[clientId]/route.ts` — GET + POST endpoints
- `dashboard/app/api/admin/queries/query/[queryId]/route.ts` — PATCH + DELETE endpoints

### Dashboard (modified)
- `dashboard/lib/types.ts` — add `Query` interface

---

### Task 1: Database Migration

**Files:**
- Create: `supabase/migrations/007_queries.sql`

- [ ] **Step 1: Write the migration SQL**

Create `supabase/migrations/007_queries.sql`:

```sql
-- 007_queries.sql
-- Phase 4: Query management

-- ══════════════════════════════════════════════
-- 1. Create queries table
-- ══════════════════════════════════════════════

create table public.queries (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients(id) on delete cascade,
  prompt_text text not null,
  slug text not null,
  bucket text not null default 'consideration' check (bucket in ('awareness', 'consideration', 'branded')),
  set_type text not null default 'core' check (set_type in ('core', 'discovery')),
  status text not null default 'active' check (status in ('active', 'retired')),
  version integer not null default 1,
  retired_at timestamptz,
  created_at timestamptz default now(),
  unique(client_id, slug)
);

create index idx_queries_client_id on public.queries(client_id);
create index idx_queries_status on public.queries(status);

-- RLS
alter table public.queries enable row level security;

create policy "Admins can manage queries"
  on public.queries for all
  using (public.is_admin())
  with check (public.is_admin());

create policy "Clients can view their own queries"
  on public.queries for select
  using (client_id = public.get_my_client_id());

-- ══════════════════════════════════════════════
-- 2. Migrate existing target_queries into queries table
-- ══════════════════════════════════════════════

-- For each client, insert their target_queries as active core consideration queries.
-- Slug is generated from prompt text: lowercase, non-alphanum → underscore, truncate 60, append _v1.
-- Uses ON CONFLICT to be idempotent.

insert into public.queries (client_id, prompt_text, slug, bucket, set_type, status, version)
select
  c.id as client_id,
  q.value::text as prompt_text,
  left(
    regexp_replace(lower(trim(both '"' from q.value::text)), '[^a-z0-9]+', '_', 'g'),
    60
  ) || '_v1' as slug,
  'consideration' as bucket,
  'core' as set_type,
  'active' as status,
  1 as version
from public.clients c,
     jsonb_array_elements(c.target_queries) as q
where jsonb_array_length(c.target_queries) > 0
on conflict (client_id, slug) do nothing;
```

- [ ] **Step 2: Commit**

```bash
git add supabase/migrations/007_queries.sql
git commit -m "feat: add queries table with data migration from target_queries"
```

---

### Task 2: Update Config Loading

**Files:**
- Modify: `agents/src/graph/nodes.py` (lines 5-21)
- Modify: `agents/run.py` (lines 15-30)

- [ ] **Step 1: Update `load_config()` in nodes.py**

In `agents/src/graph/nodes.py`, replace the `load_config` function (lines 5-21) with:

```python
def load_config(state: GEOState) -> dict:
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    result = sb.table("clients").select("*").eq("id", state["client_id"]).single().execute()
    row = result.data

    queries_resp = sb.table("queries").select("prompt_text").eq("client_id", state["client_id"]).eq("status", "active").execute()
    target_queries = [q["prompt_text"] for q in queries_resp.data] if queries_resp.data else []

    config = {
        "client_name": row["brand_name"],
        "brand_name": row["brand_name"],
        "website_domain": row["website_domain"],
        "brand_variations": row["brand_variations"] or [],
        "target_queries": target_queries,
        "competitors": row["competitors"] or [],
        "gsc_site_url": row.get("gsc_site_url", ""),
        "cms_type": row.get("cms_type", "copy_paste"),
        "cms_config": row.get("cms_config", {}),
    }
    return {"client_config": config}
```

- [ ] **Step 2: Update `fetch_config_from_supabase()` in run.py**

In `agents/run.py`, replace the `fetch_config_from_supabase` function (lines 15-30) with:

```python
def fetch_config_from_supabase(client_id: str) -> dict:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment")
    supabase = create_client(url, key)
    result = supabase.table("clients").select("*").eq("id", client_id).single().execute()
    row = result.data

    queries_resp = supabase.table("queries").select("prompt_text").eq("client_id", client_id).eq("status", "active").execute()
    target_queries = [q["prompt_text"] for q in queries_resp.data] if queries_resp.data else []

    return {
        "client_name": row["brand_name"],
        "brand_name": row["brand_name"],
        "website_domain": row["website_domain"],
        "brand_variations": row["brand_variations"] or [],
        "target_queries": target_queries,
        "competitors": row["competitors"] or [],
    }
```

- [ ] **Step 3: Commit**

```bash
git add agents/src/graph/nodes.py agents/run.py
git commit -m "feat: load target_queries from queries table instead of client config"
```

---

### Task 3: CRUD API — List and Create

**Files:**
- Create: `dashboard/app/api/admin/queries/[clientId]/route.ts`

- [ ] **Step 1: Create the GET + POST endpoint**

Create `dashboard/app/api/admin/queries/[clientId]/route.ts`:

```typescript
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

function generateSlug(text: string): string {
  return (
    text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_|_$/g, "")
      .slice(0, 60) + "_v1"
  );
}

async function checkAdmin(supabase: Awaited<ReturnType<typeof createClient>>) {
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;

  const { data: clientUser } = await supabase
    .from("client_users")
    .select("role")
    .eq("user_id", user.id)
    .single();

  return clientUser?.role === "admin" ? user : null;
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ clientId: string }> }
) {
  const { clientId } = await params;
  const supabase = await createClient();
  const user = await checkAdmin(supabase);
  if (!user) return Response.json({ error: "Forbidden" }, { status: 403 });

  const admin = createAdminClient();
  const { data, error } = await admin
    .from("queries")
    .select("*")
    .eq("client_id", clientId)
    .order("created_at", { ascending: true });

  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json(data);
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ clientId: string }> }
) {
  const { clientId } = await params;
  const supabase = await createClient();
  const user = await checkAdmin(supabase);
  if (!user) return Response.json({ error: "Forbidden" }, { status: 403 });

  const body = await request.json();
  const { prompt_text, bucket, set_type } = body;

  if (!prompt_text || typeof prompt_text !== "string" || !prompt_text.trim()) {
    return Response.json({ error: "prompt_text is required" }, { status: 400 });
  }

  const slug = generateSlug(prompt_text);

  const admin = createAdminClient();
  const { data, error } = await admin
    .from("queries")
    .insert({
      client_id: clientId,
      prompt_text: prompt_text.trim(),
      slug,
      bucket: bucket || "consideration",
      set_type: set_type || "core",
    })
    .select()
    .single();

  if (error) {
    if (error.code === "23505") {
      return Response.json({ error: "A query with this slug already exists" }, { status: 409 });
    }
    return Response.json({ error: error.message }, { status: 500 });
  }

  return Response.json(data, { status: 201 });
}
```

- [ ] **Step 2: Commit**

```bash
git add "dashboard/app/api/admin/queries/[clientId]/route.ts"
git commit -m "feat: add queries list and create API endpoints"
```

---

### Task 4: CRUD API — Update and Delete

**Files:**
- Create: `dashboard/app/api/admin/queries/query/[queryId]/route.ts`

- [ ] **Step 1: Create the PATCH + DELETE endpoint**

Create `dashboard/app/api/admin/queries/query/[queryId]/route.ts`:

```typescript
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

async function checkAdmin(supabase: Awaited<ReturnType<typeof createClient>>) {
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;

  const { data: clientUser } = await supabase
    .from("client_users")
    .select("role")
    .eq("user_id", user.id)
    .single();

  return clientUser?.role === "admin" ? user : null;
}

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ queryId: string }> }
) {
  const { queryId } = await params;
  const supabase = await createClient();
  const user = await checkAdmin(supabase);
  if (!user) return Response.json({ error: "Forbidden" }, { status: 403 });

  const body = await request.json();
  const updates: Record<string, unknown> = {};

  if (body.bucket !== undefined) updates.bucket = body.bucket;
  if (body.set_type !== undefined) updates.set_type = body.set_type;
  if (body.status !== undefined) {
    updates.status = body.status;
    if (body.status === "retired") {
      updates.retired_at = new Date().toISOString();
    }
  }

  if (Object.keys(updates).length === 0) {
    return Response.json({ error: "No valid fields to update" }, { status: 400 });
  }

  const admin = createAdminClient();
  const { data, error } = await admin
    .from("queries")
    .update(updates)
    .eq("id", queryId)
    .select()
    .single();

  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json(data);
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ queryId: string }> }
) {
  const { queryId } = await params;
  const supabase = await createClient();
  const user = await checkAdmin(supabase);
  if (!user) return Response.json({ error: "Forbidden" }, { status: 403 });

  const admin = createAdminClient();
  const { error } = await admin.from("queries").delete().eq("id", queryId);

  if (error) return Response.json({ error: error.message }, { status: 500 });
  return new Response(null, { status: 204 });
}
```

- [ ] **Step 2: Commit**

```bash
git add "dashboard/app/api/admin/queries/query/[queryId]/route.ts"
git commit -m "feat: add queries update and delete API endpoints"
```

---

### Task 5: Frontend Types

**Files:**
- Modify: `dashboard/lib/types.ts`

- [ ] **Step 1: Add Query interface**

Add this interface after `PromptStability` in `dashboard/lib/types.ts`:

```typescript
export interface Query {
  id: string;
  client_id: string;
  prompt_text: string;
  slug: string;
  bucket: "awareness" | "consideration" | "branded";
  set_type: "core" | "discovery";
  status: "active" | "retired";
  version: number;
  retired_at: string | null;
  created_at: string;
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/lib/types.ts
git commit -m "feat: add Query type"
```

---

### Task 6: Integration Verification

**Files:** None (verification only)

- [ ] **Step 1: Build frontend**

Run: `cd /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard && npx next build`
Expected: Build succeeds with no TypeScript errors. New routes `/api/admin/queries/[clientId]` and `/api/admin/queries/query/[queryId]` visible in output.

- [ ] **Step 2: Verify all query management references**

Run: `grep -rn "queries\|Query" --include="*.ts" --include="*.tsx" /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard/app/api/admin/queries /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard/lib/types.ts | grep -v node_modules`
Expected: References only in the files created/modified by this plan.

- [ ] **Step 3: Verify backend config loading changes**

Run: `grep -n "queries" /Users/jshum/Desktop/code-folders/vvAgentSystem/agents/src/graph/nodes.py /Users/jshum/Desktop/code-folders/vvAgentSystem/agents/run.py`
Expected: Both files reference the `queries` table in their config loading functions.

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: integration fixes from Phase 4 verification"
```
