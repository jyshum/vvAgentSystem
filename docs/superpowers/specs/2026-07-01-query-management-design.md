# Phase 4: Query Management — Backend Design Spec

> **Scope:** Backend only. Frontend deferred until all backend phases (2-5) are complete, then built in one unified pass.

## Goal

Replace the flat `target_queries` string array on the clients table with a dedicated `queries` table. Each query has metadata (bucket, set_type, status, version) enabling organized tracking and future query lifecycle management. CRUD API endpoints let the admin interface manage queries.

## Architecture

A new `queries` table stores each tracked prompt as a managed entity with classification metadata. The tracker pipeline reads active queries from this table instead of the client config's `target_queries` array. The rest of the pipeline (tracker.py, upload.py, nodes.py) is unchanged — it still receives `target_queries` as a list of strings in the config dict. Only the config-loading step changes.

A migration script populates the `queries` table from existing `target_queries` data. After migration, the tracker reads exclusively from the `queries` table — `target_queries` on the client row becomes unused but stays for backwards compatibility.

## What Changes

### 1. Database: `queries` table

```sql
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
```

Indexes on `client_id` and `status`. RLS: admin full access, client read own.

**Slug generation:** Convert prompt_text to lowercase, replace non-alphanumeric characters with underscores, truncate to 60 chars, append `_v1`. Example: `"Best budgeting tools for med students"` → `"best_budgeting_tools_for_med_students_v1"`.

### 2. Data migration

A SQL function or migration step that, for each client with non-empty `target_queries`, inserts rows into the `queries` table:
- `prompt_text` = each query string
- `slug` = auto-generated from prompt text
- `bucket` = `'consideration'` (safe default)
- `set_type` = `'core'`
- `status` = `'active'`
- `version` = 1

This runs once. Idempotent — skips queries where a matching `(client_id, slug)` already exists.

### 3. Backend: Config loading

**`agents/src/graph/nodes.py` — `load_config()`:**

Replace reading `target_queries` from the client row with a query to the `queries` table:

```python
queries_resp = sb.table("queries").select("prompt_text").eq("client_id", state["client_id"]).eq("status", "active").execute()
config["target_queries"] = [q["prompt_text"] for q in queries_resp.data]
```

**`agents/run.py`:**

Same change — read from `queries` table instead of `row["target_queries"]`.

The rest of the pipeline (tracker.py, upload.py) is unchanged. It receives `target_queries` as a list of strings in the config dict, same as before.

### 4. Dashboard: CRUD API

**`GET /api/admin/queries/[clientId]`**
- Returns all queries for a client, ordered by created_at
- Response: `Query[]`

**`POST /api/admin/queries/[clientId]`**
- Body: `{ prompt_text: string, bucket?: string, set_type?: string }`
- Auto-generates slug from prompt_text
- Returns created query
- Response: `Query`

**`PATCH /api/admin/queries/[queryId]`**
- Body: `{ bucket?: string, set_type?: string, status?: string }`
- When status changes to `'retired'`, sets `retired_at` to now
- Returns updated query

**`DELETE /api/admin/queries/[queryId]`**
- Hard delete for cleanup
- Returns 204

All endpoints admin-only (same auth pattern as existing admin routes).

### 5. Dashboard: Types

Add `Query` interface to `dashboard/lib/types.ts`:

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

## What's NOT Included

- **No validation pipeline** — automated 3-5 run testing of candidate queries is a future enhancement
- **No promotion workflow** — discovery → core promotion deferred
- **No version auto-increment** — editing prompt_text is a manual process; version stays at 1 for now
- **No frontend components** — deferred to unified frontend pass
- **No changes to tracker.py, upload.py, or detection.py** — they receive queries as strings, unchanged

## Cost Impact

Zero. No additional API calls. Config loading adds one lightweight Supabase query per run.

## Dependencies

- No dependency on Phases 2 or 3
- Phase 1 (multi-run scoring) must be complete — done
