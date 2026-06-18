# VV Client Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Next.js + Supabase dashboard at `app.victoryvelocity.ca` where clients view AI visibility scores and weekly reports, and the VV admin team manages clients and publishes reports.

**Architecture:** Next.js App Router on Vercel with Supabase for Postgres + Auth + RLS. The Python tracker agent pushes results to Supabase after each run. Admin edits draft reports and publishes them; clients see published reports and a live visibility dashboard. Design tokens are copied exactly from the VV landing page and report generator.

**Tech Stack:** Next.js 14+, TypeScript, Tailwind CSS, Supabase (Postgres, Auth, RLS), `@supabase/ssr`, `supabase-py`, Vitest

---

## File Map

### New: `dashboard/` (Next.js app)

```
dashboard/
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.ts
├── middleware.ts                    # Auth + role routing
├── .env.local.example              # Supabase env template
├── app/
│   ├── layout.tsx                  # Root: fonts, global styles
│   ├── globals.css                 # Design tokens from VV landing page + report generator
│   ├── page.tsx                    # Redirect to /login
│   ├── login/
│   │   ├── page.tsx                # Magic link form
│   │   └── callback/
│   │       └── route.ts            # Auth callback handler
│   ├── admin/
│   │   ├── layout.tsx              # Admin shell: nav, role gate
│   │   ├── page.tsx                # Client list
│   │   ├── clients/
│   │   │   └── [id]/
│   │   │       └── page.tsx        # Client detail
│   │   └── reports/
│   │       └── [id]/
│   │           └── page.tsx        # Report editor (two-pane)
│   └── dashboard/
│       ├── layout.tsx              # Client shell: nav, session gate
│       ├── page.tsx                # Visibility overview + report list
│       └── reports/
│           └── [id]/
│               └── page.tsx        # Report view + PDF
├── components/
│   ├── ui/
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Badge.tsx
│   │   ├── Input.tsx
│   │   └── SectionLabel.tsx
│   ├── charts/
│   │   └── SparklineChart.tsx
│   ├── report/
│   │   ├── ReportView.tsx          # Full report (shared by admin preview + client view)
│   │   ├── KPIGrid.tsx
│   │   ├── CompetitorTable.tsx
│   │   ├── QueryResultsTable.tsx
│   │   └── ReportHeader.tsx
│   ├── admin/
│   │   ├── ClientCard.tsx
│   │   ├── ReportEditor.tsx
│   │   └── InviteClientForm.tsx
│   └── dashboard/
│       ├── VisibilityOverview.tsx
│       ├── TrendChart.tsx
│       └── ReportList.tsx
├── lib/
│   ├── supabase/
│   │   ├── client.ts               # Browser client
│   │   ├── server.ts               # Server client (RSC + middleware)
│   │   └── admin.ts                # Service role client (admin actions)
│   ├── types.ts                    # DB types
│   └── utils.ts                    # Score color, formatting
└── __tests__/
    └── utils.test.ts               # Vitest tests for utility functions
```

### New: `supabase/migrations/001_initial_schema.sql`

### Modified:
- `agents/pyproject.toml` — add `supabase` dependency
- `agents/.env.example` — add `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- `agents/run.py` — add `--upload` flag
- `clients/childspot.json` — add `supabase_client_id`
- `.gitignore` — add `node_modules/`, `.env.local`, `.next/`

### New:
- `agents/src/upload.py` — Supabase upload module
- `agents/tests/test_upload.py` — upload tests

---

### Task 1: Next.js Project Scaffold + Design Tokens

**Files:**
- Create: `dashboard/` (via create-next-app)
- Create: `dashboard/app/globals.css`
- Modify: `dashboard/tailwind.config.ts`
- Modify: `dashboard/app/layout.tsx`
- Modify: `dashboard/app/page.tsx`
- Modify: `.gitignore`

- [ ] **Step 1: Create Next.js project**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
npx create-next-app@latest dashboard --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --no-turbopack
```

Accept defaults. This creates `dashboard/` with App Router, Tailwind, TypeScript.

- [ ] **Step 2: Install Supabase + Vitest dependencies**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard
npm install @supabase/supabase-js @supabase/ssr
npm install -D vitest @vitejs/plugin-react
```

- [ ] **Step 3: Add vitest config**

Create `dashboard/vitest.config.ts`:

```typescript
import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    environment: "node",
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});
```

Add to `dashboard/package.json` scripts:

```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 4: Write globals.css with exact VV design tokens**

Replace `dashboard/app/globals.css` with:

```css
@import "tailwindcss";

:root {
  /* ── Colors: VV Landing Page (globals.css) ── */
  --ink: #0e0e0f;
  --ink-soft: #141416;
  --ink-2: #19191c;
  --white: #f5f4f1;
  --paper: #f1ede4;
  --paper-ink: #17150f;
  --mute: rgba(245, 244, 241, 0.58);
  --faint: rgba(245, 244, 241, 0.36);
  --ghost: rgba(245, 244, 241, 0.13);
  --hair: rgba(245, 244, 241, 0.11);

  /* ── Accent/Status: VV Report Generator (styles.css) ── */
  --pos: #84d8ab;
  --neg: #e89aa0;
  --accent: #f5f4f1;

  /* ── Typography: VV Landing Page (layout.tsx) ── */
  --serif: "Newsreader", Georgia, serif;
  --sans: "Schibsted Grotesk", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, monospace;
  --display: "Cormorant Garamond", Georgia, "Times New Roman", serif;
}

*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html,
body {
  height: 100%;
  background: var(--ink);
  color: var(--white);
  font-family: var(--serif);
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

/* ── Scrollbars (from report generator) ── */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: var(--ghost);
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--faint);
}

/* ── Print CSS for PDF export ── */
@media print {
  @page {
    margin: 0;
  }
  html,
  body {
    height: auto;
    overflow: visible;
    background: var(--ink) !important;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }
  * {
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }
  .no-print {
    display: none !important;
  }
  .print-only {
    display: block !important;
  }
}
```

- [ ] **Step 5: Configure Tailwind with VV tokens**

Replace `dashboard/tailwind.config.ts`:

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "var(--ink)",
          soft: "var(--ink-soft)",
          2: "var(--ink-2)",
        },
        cream: "var(--white)",
        paper: {
          DEFAULT: "var(--paper)",
          ink: "var(--paper-ink)",
        },
        mute: "var(--mute)",
        faint: "var(--faint)",
        ghost: "var(--ghost)",
        hair: "var(--hair)",
        pos: "var(--pos)",
        neg: "var(--neg)",
        accent: "var(--accent)",
      },
      fontFamily: {
        serif: ["var(--serif)"],
        sans: ["var(--sans)"],
        mono: ["var(--mono)"],
        display: ["var(--display)"],
      },
      borderRadius: {
        card: "12px",
      },
      boxShadow: {
        card: "0 40px 90px -40px rgba(0,0,0,0.8)",
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 6: Update root layout with Google Fonts**

Replace `dashboard/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Victory Velocity — Client Dashboard",
  description: "AI visibility tracking and weekly performance reports.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin=""
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&family=Schibsted+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400;1,500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 7: Set root page to redirect to /login**

Replace `dashboard/app/page.tsx`:

```tsx
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/login");
}
```

- [ ] **Step 8: Create .env.local.example**

Create `dashboard/.env.local.example`:

```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

- [ ] **Step 9: Update .gitignore**

Append to root `.gitignore`:

```
# Dashboard
node_modules/
.next/
.env.local
```

- [ ] **Step 10: Verify build**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard
npm run build
```

Expected: Build succeeds.

- [ ] **Step 11: Commit**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
git add dashboard/ .gitignore
git commit -m "feat: scaffold Next.js dashboard with VV design tokens"
```

---

### Task 2: Supabase Schema

**Files:**
- Create: `supabase/migrations/001_initial_schema.sql`

**Prerequisites:** The user must create a Supabase project at https://supabase.com/dashboard and note their project URL, anon key, and service role key. These go into `dashboard/.env.local` and `agents/.env`.

- [ ] **Step 1: Write the SQL migration**

Create `supabase/migrations/001_initial_schema.sql`:

```sql
-- VV Client Dashboard — Initial Schema
-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor → New query)

-- ══════════════════════════════════════════════
-- Tables
-- ══════════════════════════════════════════════

create table public.clients (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  brand_name text not null,
  website_domain text default '',
  brand_variations jsonb default '[]'::jsonb,
  target_queries jsonb default '[]'::jsonb,
  competitors jsonb default '[]'::jsonb,
  created_at timestamptz default now()
);

create table public.client_users (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  client_id uuid references public.clients(id) on delete cascade,
  role text not null check (role in ('admin', 'client')),
  created_at timestamptz default now(),
  unique (user_id)
);

create table public.tracker_runs (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients(id) on delete cascade,
  ran_at timestamptz default now(),
  aggregate_mention_rate float,
  aggregate_citation_rate float,
  per_engine_scores jsonb default '{}'::jsonb,
  competitor_scores jsonb default '{}'::jsonb
);

create table public.tracker_results (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.tracker_runs(id) on delete cascade,
  query text not null,
  engine text not null,
  model text default '',
  brand_mentioned boolean default false,
  brand_cited boolean default false,
  citation_url text,
  competitor_mentions jsonb default '[]'::jsonb,
  response_text text default '',
  queried_at timestamptz default now()
);

create table public.reports (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients(id) on delete cascade,
  run_id uuid references public.tracker_runs(id) on delete set null,
  week_start date not null,
  status text not null default 'draft' check (status in ('draft', 'published')),
  exec_summary text default '',
  work_completed jsonb default '[]'::jsonb,
  priorities jsonb default '[]'::jsonb,
  highlights jsonb default '[]'::jsonb,
  blockers jsonb default '[]'::jsonb,
  notes text default '',
  search_console jsonb,
  published_at timestamptz,
  created_at timestamptz default now()
);

-- ══════════════════════════════════════════════
-- View: tracker_results without response_text (for client access)
-- ══════════════════════════════════════════════

create view public.tracker_results_client as
select
  id, run_id, query, engine, model,
  brand_mentioned, brand_cited, citation_url,
  competitor_mentions, queried_at
from public.tracker_results;

-- ══════════════════════════════════════════════
-- Indexes
-- ══════════════════════════════════════════════

create index idx_client_users_user_id on public.client_users(user_id);
create index idx_client_users_client_id on public.client_users(client_id);
create index idx_tracker_runs_client_id on public.tracker_runs(client_id);
create index idx_tracker_results_run_id on public.tracker_results(run_id);
create index idx_reports_client_id on public.reports(client_id);
create index idx_reports_status on public.reports(status);

-- ══════════════════════════════════════════════
-- Helper function: get the client_id for the current auth user
-- ══════════════════════════════════════════════

create or replace function public.get_my_client_id()
returns uuid
language sql
stable
security definer
as $$
  select client_id from public.client_users
  where user_id = auth.uid()
  limit 1;
$$;

create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
as $$
  select exists (
    select 1 from public.client_users
    where user_id = auth.uid() and role = 'admin'
  );
$$;

-- ══════════════════════════════════════════════
-- Row Level Security
-- ══════════════════════════════════════════════

alter table public.clients enable row level security;
alter table public.client_users enable row level security;
alter table public.tracker_runs enable row level security;
alter table public.tracker_results enable row level security;
alter table public.reports enable row level security;

-- clients
create policy "Admins can do everything with clients"
  on public.clients for all
  using (public.is_admin())
  with check (public.is_admin());

create policy "Clients can view their own client record"
  on public.clients for select
  using (id = public.get_my_client_id());

-- client_users
create policy "Admins can manage client_users"
  on public.client_users for all
  using (public.is_admin())
  with check (public.is_admin());

create policy "Users can view their own client_users row"
  on public.client_users for select
  using (user_id = auth.uid());

-- tracker_runs
create policy "Admins can manage tracker_runs"
  on public.tracker_runs for all
  using (public.is_admin())
  with check (public.is_admin());

create policy "Clients can view their own tracker_runs"
  on public.tracker_runs for select
  using (client_id = public.get_my_client_id());

-- tracker_results (admins only — clients use the view)
create policy "Admins can manage tracker_results"
  on public.tracker_results for all
  using (public.is_admin())
  with check (public.is_admin());

-- reports
create policy "Admins can manage reports"
  on public.reports for all
  using (public.is_admin())
  with check (public.is_admin());

create policy "Clients can view their own published reports"
  on public.reports for select
  using (
    status = 'published'
    and client_id = public.get_my_client_id()
  );

-- Grant access to the client view
grant select on public.tracker_results_client to authenticated;

-- RLS-like filter on the view (views don't support RLS directly,
-- so we use a security definer function for filtering in queries)
-- Client-side queries should always filter:
--   WHERE run_id IN (SELECT id FROM tracker_runs WHERE client_id = get_my_client_id())
```

- [ ] **Step 2: Commit**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
git add supabase/
git commit -m "feat: Supabase schema with RLS policies and client view"
```

---

### Task 3: Supabase Client Libraries + TypeScript Types

**Files:**
- Create: `dashboard/lib/supabase/client.ts`
- Create: `dashboard/lib/supabase/server.ts`
- Create: `dashboard/lib/supabase/admin.ts`
- Create: `dashboard/lib/types.ts`

- [ ] **Step 1: Create browser Supabase client**

Create `dashboard/lib/supabase/client.ts`:

```typescript
import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
```

- [ ] **Step 2: Create server Supabase client**

Create `dashboard/lib/supabase/server.ts`:

```typescript
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          } catch {
            // Called from Server Component — ignore
          }
        },
      },
    }
  );
}
```

- [ ] **Step 3: Create admin (service role) client**

Create `dashboard/lib/supabase/admin.ts`:

```typescript
import { createClient as createSupabaseClient } from "@supabase/supabase-js";

export function createAdminClient() {
  return createSupabaseClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } }
  );
}
```

- [ ] **Step 4: Create TypeScript types**

Create `dashboard/lib/types.ts`:

```typescript
export interface Client {
  id: string;
  name: string;
  brand_name: string;
  website_domain: string;
  brand_variations: string[];
  target_queries: string[];
  competitors: string[];
  created_at: string;
}

export interface ClientUser {
  id: string;
  user_id: string;
  client_id: string | null;
  role: "admin" | "client";
  created_at: string;
}

export interface TrackerRun {
  id: string;
  client_id: string;
  ran_at: string;
  aggregate_mention_rate: number;
  aggregate_citation_rate: number;
  per_engine_scores: Record<
    string,
    { mention_rate: number; citation_rate: number }
  >;
  competitor_scores: Record<string, { mention_rate: number }>;
}

export interface TrackerResult {
  id: string;
  run_id: string;
  query: string;
  engine: string;
  model: string;
  brand_mentioned: boolean;
  brand_cited: boolean;
  citation_url: string | null;
  competitor_mentions: string[];
  response_text: string;
  queried_at: string;
}

export interface TrackerResultClient {
  id: string;
  run_id: string;
  query: string;
  engine: string;
  model: string;
  brand_mentioned: boolean;
  brand_cited: boolean;
  citation_url: string | null;
  competitor_mentions: string[];
  queried_at: string;
}

export interface Report {
  id: string;
  client_id: string;
  run_id: string | null;
  week_start: string;
  status: "draft" | "published";
  exec_summary: string;
  work_completed: { text: string; done: boolean }[];
  priorities: { text: string }[];
  highlights: { text: string }[];
  blockers: { text: string }[];
  notes: string;
  search_console: SearchConsoleMetrics | null;
  published_at: string | null;
  created_at: string;
}

export interface SearchConsoleMetrics {
  impressions: { week: number | null; baseline: number | null };
  clicks: { week: number | null; baseline: number | null };
  ctr: { week: number | null; baseline: number | null };
  position: { week: number | null; baseline: number | null };
}

export interface ReportWithRun extends Report {
  tracker_run: TrackerRun | null;
}
```

- [ ] **Step 5: Verify build**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard
npm run build
```

Expected: Build succeeds.

- [ ] **Step 6: Commit**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
git add dashboard/lib/
git commit -m "feat: Supabase client libraries and TypeScript types"
```

---

### Task 4: Auth Middleware + Login Page

**Files:**
- Create: `dashboard/middleware.ts`
- Create: `dashboard/lib/supabase/middleware.ts`
- Create: `dashboard/app/login/page.tsx`
- Create: `dashboard/app/login/callback/route.ts`

- [ ] **Step 1: Create Supabase middleware helper**

Create `dashboard/lib/supabase/middleware.ts`:

```typescript
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            request.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  const path = request.nextUrl.pathname;

  // Public routes
  if (path === "/login" || path.startsWith("/login/")) {
    if (user) {
      // Logged in — redirect to appropriate dashboard
      const { data: clientUser } = await supabase
        .from("client_users")
        .select("role")
        .eq("user_id", user.id)
        .single();

      const dest =
        clientUser?.role === "admin" ? "/admin" : "/dashboard";
      return NextResponse.redirect(new URL(dest, request.url));
    }
    return supabaseResponse;
  }

  // Protected routes — must be logged in
  if (!user) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Role-based access
  const { data: clientUser } = await supabase
    .from("client_users")
    .select("role")
    .eq("user_id", user.id)
    .single();

  if (!clientUser) {
    // User exists in auth but has no client_users row
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (path.startsWith("/admin") && clientUser.role !== "admin") {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  if (path.startsWith("/dashboard") && clientUser.role !== "client") {
    return NextResponse.redirect(new URL("/admin", request.url));
  }

  return supabaseResponse;
}
```

- [ ] **Step 2: Create Next.js middleware**

Create `dashboard/middleware.ts`:

```typescript
import { type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

export async function middleware(request: NextRequest) {
  return await updateSession(request);
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
```

- [ ] **Step 3: Create auth callback route**

Create `dashboard/app/login/callback/route.ts`:

```typescript
import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);

    if (!error) {
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (user) {
        const { data: clientUser } = await supabase
          .from("client_users")
          .select("role")
          .eq("user_id", user.id)
          .single();

        const dest =
          clientUser?.role === "admin" ? "/admin" : "/dashboard";
        return NextResponse.redirect(`${origin}${dest}`);
      }
    }
  }

  return NextResponse.redirect(`${origin}/login?error=auth`);
}
```

- [ ] **Step 4: Create login page**

Create `dashboard/app/login/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    const supabase = createClient();
    const { error: authError } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/login/callback`,
      },
    });

    setLoading(false);
    if (authError) {
      setError("Something went wrong. Please try again.");
    } else {
      setSent(true);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6"
         style={{ background: "var(--ink)" }}>
      <div className="w-full max-w-[400px]">
        {/* Brand */}
        <div className="text-center mb-16">
          <h1 className="font-serif text-[21px] tracking-[0.01em]"
              style={{ color: "var(--white)" }}>
            Victory Velocity
          </h1>
          <p className="font-mono text-[10px] tracking-[0.2em] uppercase mt-2"
             style={{ color: "var(--faint)" }}>
            Client Dashboard
          </p>
        </div>

        {sent ? (
          <div className="text-center">
            <p className="font-serif text-lg italic"
               style={{ color: "var(--mute)" }}>
              Check your email for a login link.
            </p>
            <p className="font-mono text-[10px] tracking-[0.1em] uppercase mt-4"
               style={{ color: "var(--faint)" }}>
              Sent to {email}
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <label className="block font-mono text-[11px] tracking-[0.12em] uppercase mb-2"
                   style={{ color: "var(--mute)" }}>
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              required
              className="w-full bg-transparent font-serif text-sm px-3 py-2.5 outline-none transition-colors"
              style={{
                border: "1px solid var(--ghost)",
                color: "var(--white)",
              }}
              onFocus={(e) =>
                (e.target.style.borderColor = "rgba(245,244,241,0.42)")
              }
              onBlur={(e) =>
                (e.target.style.borderColor = "var(--ghost)")
              }
            />

            {error && (
              <p className="font-mono text-[10px] tracking-[0.1em] mt-2"
                 style={{ color: "var(--neg)" }}>
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-6 font-sans text-[13px] font-semibold tracking-[0.06em] inline-flex items-center justify-center py-[15px] px-[26px] cursor-pointer transition-all duration-300"
              style={{
                background: "var(--white)",
                color: "var(--ink)",
                border: "1px solid var(--white)",
                borderRadius: "2px",
                opacity: loading ? 0.6 : 1,
              }}
            >
              {loading ? "Sending…" : "Send Magic Link"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Verify build**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard
npm run build
```

Expected: Build succeeds.

- [ ] **Step 6: Commit**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
git add dashboard/middleware.ts dashboard/lib/supabase/middleware.ts dashboard/app/login/
git commit -m "feat: auth middleware with role routing and magic link login"
```

---

### Task 5: Utility Functions (TDD)

**Files:**
- Create: `dashboard/lib/utils.ts`
- Create: `dashboard/__tests__/utils.test.ts`

- [ ] **Step 1: Write failing tests**

Create `dashboard/__tests__/utils.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import {
  scoreColor,
  formatRate,
  formatDelta,
  weekRangeLabel,
  scoreLevel,
} from "@/lib/utils";

describe("scoreColor", () => {
  it("returns neg for 0", () => {
    expect(scoreColor(0)).toBe("var(--neg)");
  });
  it("returns orange for low rates", () => {
    expect(scoreColor(0.1)).toBe("#fd7e14");
  });
  it("returns yellow for mid rates", () => {
    expect(scoreColor(0.3)).toBe("#ffc107");
  });
  it("returns pos for high rates", () => {
    expect(scoreColor(0.6)).toBe("var(--pos)");
  });
});

describe("scoreLevel", () => {
  it("returns 'zero' for 0", () => {
    expect(scoreLevel(0)).toBe("zero");
  });
  it("returns 'low' for <25%", () => {
    expect(scoreLevel(0.15)).toBe("low");
  });
  it("returns 'mid' for <50%", () => {
    expect(scoreLevel(0.4)).toBe("mid");
  });
  it("returns 'high' for >=50%", () => {
    expect(scoreLevel(0.75)).toBe("high");
  });
});

describe("formatRate", () => {
  it("formats 0.05 as 5%", () => {
    expect(formatRate(0.05)).toBe("5%");
  });
  it("formats 0 as 0%", () => {
    expect(formatRate(0)).toBe("0%");
  });
  it("formats 1 as 100%", () => {
    expect(formatRate(1)).toBe("100%");
  });
  it("formats 0.253 as 25%", () => {
    expect(formatRate(0.253)).toBe("25%");
  });
});

describe("formatDelta", () => {
  it("returns positive delta with arrow", () => {
    expect(formatDelta(0.1, 0.05)).toEqual({
      text: "+5pp",
      direction: "up",
    });
  });
  it("returns negative delta with arrow", () => {
    expect(formatDelta(0.05, 0.1)).toEqual({
      text: "-5pp",
      direction: "down",
    });
  });
  it("returns flat for no change", () => {
    expect(formatDelta(0.1, 0.1)).toEqual({
      text: "±0pp",
      direction: "flat",
    });
  });
  it("returns null when no previous value", () => {
    expect(formatDelta(0.1, null)).toBeNull();
  });
});

describe("weekRangeLabel", () => {
  it("formats a week range", () => {
    const label = weekRangeLabel("2026-06-15");
    expect(label).toContain("June 15");
    expect(label).toContain("21");
  });
  it("returns empty string for null", () => {
    expect(weekRangeLabel(null)).toBe("");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard
npx vitest run
```

Expected: All tests FAIL (module not found).

- [ ] **Step 3: Implement utility functions**

Create `dashboard/lib/utils.ts`:

```typescript
export function scoreColor(rate: number): string {
  if (rate === 0) return "var(--neg)";
  if (rate < 0.25) return "#fd7e14";
  if (rate < 0.5) return "#ffc107";
  return "var(--pos)";
}

export function scoreLevel(
  rate: number
): "zero" | "low" | "mid" | "high" {
  if (rate === 0) return "zero";
  if (rate < 0.25) return "low";
  if (rate < 0.5) return "mid";
  return "high";
}

export function formatRate(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}

export function formatDelta(
  current: number,
  previous: number | null
): { text: string; direction: "up" | "down" | "flat" } | null {
  if (previous === null || previous === undefined) return null;
  const diff = Math.round((current - previous) * 100);
  if (diff > 0)
    return { text: `+${diff}pp`, direction: "up" };
  if (diff < 0)
    return { text: `${diff}pp`, direction: "down" };
  return { text: "±0pp", direction: "flat" };
}

export function weekRangeLabel(weekStart: string | null): string {
  if (!weekStart) return "";
  const start = new Date(weekStart + "T00:00:00");
  if (isNaN(start.getTime())) return "";
  const end = new Date(start);
  end.setDate(end.getDate() + 6);

  const sameMonth =
    start.getMonth() === end.getMonth() &&
    start.getFullYear() === end.getFullYear();

  const startStr = start.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
  });
  const endStr = end.toLocaleDateString(
    "en-US",
    sameMonth ? { day: "numeric" } : { month: "long", day: "numeric" }
  );

  return `${startStr} – ${endStr}, ${end.getFullYear()}`;
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard
npx vitest run
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
git add dashboard/lib/utils.ts dashboard/__tests__/ dashboard/vitest.config.ts
git commit -m "feat: utility functions for score colors and formatting"
```

---

### Task 6: UI Components

**Files:**
- Create: `dashboard/components/ui/Button.tsx`
- Create: `dashboard/components/ui/Card.tsx`
- Create: `dashboard/components/ui/Badge.tsx`
- Create: `dashboard/components/ui/Input.tsx`
- Create: `dashboard/components/ui/SectionLabel.tsx`

- [ ] **Step 1: Create Button component**

Create `dashboard/components/ui/Button.tsx`:

```tsx
import { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "outline" | "solid";
}

export function Button({
  variant = "outline",
  className = "",
  children,
  ...props
}: ButtonProps) {
  const base =
    "font-sans text-[13px] font-semibold tracking-[0.06em] inline-flex items-center justify-center gap-[11px] py-[15px] px-[26px] cursor-pointer transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed";

  const variants = {
    outline:
      "bg-transparent border border-[var(--ghost)] text-[var(--white)] rounded-[2px] hover:bg-[var(--white)] hover:text-[var(--ink)] hover:border-[var(--white)]",
    solid:
      "bg-[var(--white)] text-[var(--ink)] border border-[var(--white)] rounded-[2px] hover:bg-transparent hover:text-[var(--white)] hover:border-[var(--ghost)]",
  };

  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}
```

- [ ] **Step 2: Create Card component**

Create `dashboard/components/ui/Card.tsx`:

```tsx
import { HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  elevated?: boolean;
}

export function Card({
  elevated = false,
  className = "",
  children,
  ...props
}: CardProps) {
  const base = elevated
    ? "bg-[var(--ink-2)] border border-[var(--hair)] rounded-card shadow-card overflow-hidden"
    : "bg-[var(--ink-soft)] border border-[var(--hair)] rounded-card overflow-hidden";

  return (
    <div className={`${base} ${className}`} {...props}>
      {children}
    </div>
  );
}
```

- [ ] **Step 3: Create Badge component**

Create `dashboard/components/ui/Badge.tsx`:

```tsx
interface BadgeProps {
  variant: "cited" | "mentioned" | "not-found" | "draft" | "published";
  children: React.ReactNode;
}

export function Badge({ variant, children }: BadgeProps) {
  const base =
    "font-mono text-[8px] tracking-[0.1em] uppercase py-[4px] px-[9px] inline-block whitespace-nowrap";

  const variants: Record<string, string> = {
    cited: "text-[var(--ink)] bg-[var(--pos)]",
    mentioned: "text-[var(--ink)] bg-[var(--pos)]",
    "not-found": "text-[var(--mute)] border border-[rgba(245,244,241,0.42)]",
    draft: "text-[var(--mute)] border border-[rgba(245,244,241,0.42)]",
    published: "text-[var(--ink)] bg-[var(--pos)]",
  };

  return (
    <span className={`${base} ${variants[variant] || ""}`}>
      {children}
    </span>
  );
}
```

- [ ] **Step 4: Create Input component**

Create `dashboard/components/ui/Input.tsx`:

```tsx
import { InputHTMLAttributes, TextareaHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export function Input({ label, className = "", ...props }: InputProps) {
  return (
    <div className="mb-3.5">
      {label && (
        <label className="block font-mono text-[11px] tracking-[0.12em] uppercase text-[var(--mute)] mb-1.5">
          {label}
        </label>
      )}
      <input
        className={`w-full bg-transparent border border-[var(--ghost)] text-[var(--white)] font-serif text-sm py-2 px-2.5 outline-none transition-colors focus:border-[rgba(245,244,241,0.42)] placeholder:text-[rgba(255,255,255,0.22)] ${className}`}
        {...props}
      />
    </div>
  );
}

interface TextareaProps
  extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
}

export function Textarea({
  label,
  className = "",
  ...props
}: TextareaProps) {
  return (
    <div className="mb-3.5">
      {label && (
        <label className="block font-mono text-[11px] tracking-[0.12em] uppercase text-[var(--mute)] mb-1.5">
          {label}
        </label>
      )}
      <textarea
        className={`w-full bg-transparent border border-[var(--ghost)] text-[var(--white)] font-serif text-sm py-2 px-2.5 outline-none transition-colors focus:border-[rgba(245,244,241,0.42)] placeholder:text-[rgba(255,255,255,0.22)] italic leading-relaxed min-h-[70px] resize-y ${className}`}
        {...props}
      />
    </div>
  );
}
```

- [ ] **Step 5: Create SectionLabel component**

Create `dashboard/components/ui/SectionLabel.tsx`:

```tsx
interface SectionLabelProps {
  children: React.ReactNode;
  action?: React.ReactNode;
}

export function SectionLabel({ children, action }: SectionLabelProps) {
  return (
    <div className="flex items-center justify-between gap-2.5 font-mono text-xs tracking-[0.14em] uppercase text-[var(--mute)] pb-[11px] border-b border-[var(--hair)] mb-6">
      <span>{children}</span>
      {action}
    </div>
  );
}
```

- [ ] **Step 6: Verify build**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard
npm run build
```

Expected: Build succeeds.

- [ ] **Step 7: Commit**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
git add dashboard/components/ui/
git commit -m "feat: UI component library matching VV design system"
```

---

### Task 7: SparklineChart Component

**Files:**
- Create: `dashboard/components/charts/SparklineChart.tsx`

- [ ] **Step 1: Create SparklineChart**

Port from the report generator's `sparklineSVG` function. Create `dashboard/components/charts/SparklineChart.tsx`:

```tsx
interface SparklineChartProps {
  values: (number | null)[];
  direction?: "up" | "down" | "flat" | "none";
  width?: number;
  height?: number;
}

export function SparklineChart({
  values,
  direction = "none",
  width = 160,
  height = 30,
}: SparklineChartProps) {
  const pts = values.filter(
    (v): v is number => v !== null && !isNaN(v)
  );
  const pad = 3;

  if (pts.length < 2) {
    return (
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        className="w-full"
        style={{ height }}
      >
        <text
          x="0"
          y={height - 9}
          className="font-mono text-[8px] tracking-[0.1em]"
          fill="var(--faint)"
        >
          needs 2+ data points
        </text>
      </svg>
    );
  }

  const min = Math.min(...pts);
  const max = Math.max(...pts);
  const range = max - min || 1;
  const stepX = (width - pad * 2) / (pts.length - 1);

  const coords = pts.map((v, i) => {
    const t = (v - min) / range;
    return [pad + i * stepX, pad + (1 - t) * (height - pad * 2)] as const;
  });

  const line = coords
    .map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`)
    .join(" ");

  const last = coords[coords.length - 1];
  const area =
    `M${coords[0][0].toFixed(1)} ${(height - pad).toFixed(1)} ` +
    coords
      .map(([x, y]) => `L${x.toFixed(1)} ${y.toFixed(1)}`)
      .join(" ") +
    ` L${last[0].toFixed(1)} ${(height - pad).toFixed(1)} Z`;

  const strokeColor =
    direction === "up"
      ? "var(--pos)"
      : direction === "down"
        ? "var(--neg)"
        : "rgba(245,244,241,0.5)";

  const fillColor =
    direction === "up"
      ? "var(--pos)"
      : direction === "down"
        ? "var(--neg)"
        : "rgba(245,244,241,0.5)";

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className="w-full"
      style={{ height }}
    >
      <path d={area} fill={fillColor} opacity={0.16} />
      <path
        d={line}
        fill="none"
        stroke={strokeColor}
        strokeWidth={1.5}
        vectorEffect="non-scaling-stroke"
      />
      <circle
        cx={last[0].toFixed(1)}
        cy={last[1].toFixed(1)}
        r={2.2}
        fill="var(--white)"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard
npm run build
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
git add dashboard/components/charts/
git commit -m "feat: SparklineChart component ported from report generator"
```

---

### Task 8: Report Components

**Files:**
- Create: `dashboard/components/report/ReportHeader.tsx`
- Create: `dashboard/components/report/KPIGrid.tsx`
- Create: `dashboard/components/report/CompetitorTable.tsx`
- Create: `dashboard/components/report/QueryResultsTable.tsx`

- [ ] **Step 1: Create ReportHeader**

Create `dashboard/components/report/ReportHeader.tsx`:

```tsx
import { weekRangeLabel } from "@/lib/utils";

interface ReportHeaderProps {
  clientName: string;
  weekStart: string;
  domain?: string;
  preparedBy?: string;
}

export function ReportHeader({
  clientName,
  weekStart,
  domain,
  preparedBy = "Victory Velocity",
}: ReportHeaderProps) {
  return (
    <header className="mb-[18px]">
      <div className="flex items-center justify-between gap-4 mb-12">
        <div
          className="font-serif text-xs tracking-[0.1em] ml-auto"
          style={{ color: "var(--mute)" }}
        >
          Victory Velocity
        </div>
      </div>

      <div
        className="font-mono text-xs tracking-[0.16em] uppercase mb-3"
        style={{ color: "var(--mute)" }}
      >
        GEO &middot; Weekly Performance Report
      </div>

      <h1
        className="font-display font-light text-[72px] leading-[0.96] tracking-[-0.015em] mb-4 break-words"
        style={{ color: "var(--white)" }}
      >
        {clientName}
      </h1>

      <div
        className="font-serif italic font-light text-[21px]"
        style={{ color: "var(--mute)" }}
      >
        {weekRangeLabel(weekStart)}
      </div>

      <div
        className="font-mono text-[10px] tracking-[0.1em] uppercase mt-3"
        style={{ color: "var(--faint)" }}
      >
        {domain && `${domain} · `}Prepared by {preparedBy}
      </div>
    </header>
  );
}
```

- [ ] **Step 2: Create KPIGrid**

Create `dashboard/components/report/KPIGrid.tsx`:

```tsx
import { scoreColor, formatRate } from "@/lib/utils";
import { SparklineChart } from "@/components/charts/SparklineChart";
import type { TrackerRun } from "@/lib/types";

interface KPIGridProps {
  run: TrackerRun;
  previousRuns?: TrackerRun[];
}

export function KPIGrid({ run, previousRuns = [] }: KPIGridProps) {
  const engines = Object.entries(run.per_engine_scores);

  return (
    <div className="mt-[50px]">
      <h2
        className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
        style={{ color: "var(--mute)" }}
      >
        AI Visibility Scores
      </h2>

      {/* Aggregate cards */}
      <div className="grid grid-cols-2 gap-px bg-[var(--hair)] border border-[var(--hair)] mb-6">
        <ScoreCard
          label="Mention Rate"
          value={run.aggregate_mention_rate}
          history={previousRuns.map((r) => r.aggregate_mention_rate)}
        />
        <ScoreCard
          label="Citation Rate"
          value={run.aggregate_citation_rate}
          history={previousRuns.map((r) => r.aggregate_citation_rate)}
        />
      </div>

      {/* Per-engine cards */}
      <div
        className="grid gap-px bg-[var(--hair)] border border-[var(--hair)]"
        style={{ gridTemplateColumns: `repeat(${engines.length}, 1fr)` }}
      >
        {engines.map(([engine, scores]) => (
          <div
            key={engine}
            className="p-5 flex flex-col"
            style={{ background: "var(--ink-2)", minHeight: "120px" }}
          >
            <div
              className="font-mono text-[11px] tracking-[0.12em] uppercase mb-3"
              style={{ color: "var(--mute)" }}
            >
              {engine}
            </div>
            <div
              className="font-serif font-light text-[32px] leading-none mb-1"
              style={{ color: scoreColor(scores.mention_rate) }}
            >
              {formatRate(scores.mention_rate)}
            </div>
            <div
              className="font-mono text-[9px] tracking-[0.1em] uppercase"
              style={{ color: "var(--faint)" }}
            >
              mention rate
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ScoreCard({
  label,
  value,
  history,
}: {
  label: string;
  value: number;
  history: number[];
}) {
  const allValues = [...history, value];
  const prev = history.length > 0 ? history[history.length - 1] : null;
  const delta =
    prev !== null ? Math.round((value - prev) * 100) : null;
  const direction =
    delta === null
      ? ("none" as const)
      : delta > 0
        ? ("up" as const)
        : delta < 0
          ? ("down" as const)
          : ("flat" as const);

  return (
    <div
      className="p-5 flex flex-col"
      style={{ background: "var(--ink-2)", minHeight: "132px" }}
    >
      <div
        className="font-mono text-[11px] tracking-[0.12em] uppercase mb-3"
        style={{ color: "var(--mute)" }}
      >
        {label}
      </div>
      <div
        className="font-serif font-light text-[40px] leading-none mb-2"
        style={{ color: scoreColor(value) }}
      >
        {formatRate(value)}
      </div>
      <div
        className="font-mono text-[10px] tracking-[0.04em]"
        style={{ color: "var(--mute)" }}
      >
        {delta !== null && (
          <>
            <span
              className="font-bold"
              style={{
                color:
                  direction === "up"
                    ? "var(--pos)"
                    : direction === "down"
                      ? "var(--neg)"
                      : "var(--mute)",
              }}
            >
              {direction === "up" ? "▲" : direction === "down" ? "▼" : "■"}
            </span>{" "}
            <span>{Math.abs(delta)}pp vs last week</span>
          </>
        )}
      </div>
      <div className="mt-auto pt-3">
        <SparklineChart values={allValues} direction={direction} />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create CompetitorTable**

Create `dashboard/components/report/CompetitorTable.tsx`:

```tsx
import { scoreColor, formatRate } from "@/lib/utils";
import type { TrackerRun } from "@/lib/types";

interface CompetitorTableProps {
  run: TrackerRun;
  brandName: string;
}

export function CompetitorTable({ run, brandName }: CompetitorTableProps) {
  const competitors = Object.entries(run.competitor_scores).sort(
    ([, a], [, b]) => b.mention_rate - a.mention_rate
  );

  if (competitors.length === 0) return null;

  return (
    <div className="mt-[50px]">
      <h2
        className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
        style={{ color: "var(--mute)" }}
      >
        Competitor Comparison
      </h2>

      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th
              className="font-mono text-[10px] tracking-[0.12em] uppercase text-left py-0 pr-3.5 pb-2.5 border-b border-[var(--hair)]"
              style={{ color: "var(--mute)" }}
            >
              Brand / Competitor
            </th>
            <th
              className="font-mono text-[10px] tracking-[0.12em] uppercase text-left py-0 pb-2.5 border-b border-[var(--hair)]"
              style={{ color: "var(--mute)" }}
            >
              Mention Rate
            </th>
          </tr>
        </thead>
        <tbody>
          {/* Brand row (highlighted) */}
          <tr style={{ background: "rgba(245,244,241,0.04)" }}>
            <td
              className="font-serif text-base py-2.5 pr-3.5 border-b border-[var(--hair)]"
              style={{ color: "var(--white)" }}
            >
              <strong>{brandName}</strong>
            </td>
            <td className="py-2.5 border-b border-[var(--hair)]">
              <span
                className="font-bold"
                style={{
                  color: scoreColor(run.aggregate_mention_rate),
                }}
              >
                {formatRate(run.aggregate_mention_rate)}
              </span>
            </td>
          </tr>
          {/* Competitor rows */}
          {competitors.map(([name, scores]) => (
            <tr key={name}>
              <td
                className="font-serif text-base py-2.5 pr-3.5 border-b border-[var(--hair)]"
                style={{ color: "var(--white)" }}
              >
                {name}
              </td>
              <td className="py-2.5 border-b border-[var(--hair)]">
                <span
                  className="font-bold"
                  style={{ color: scoreColor(scores.mention_rate) }}
                >
                  {formatRate(scores.mention_rate)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 4: Create QueryResultsTable**

Create `dashboard/components/report/QueryResultsTable.tsx`:

```tsx
import { Badge } from "@/components/ui/Badge";
import type { TrackerResultClient } from "@/lib/types";

interface QueryResultsTableProps {
  results: TrackerResultClient[];
}

export function QueryResultsTable({ results }: QueryResultsTableProps) {
  return (
    <div className="mt-[50px]">
      <h2
        className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
        style={{ color: "var(--mute)" }}
      >
        GEO Query Results
      </h2>

      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th
              className="font-mono text-[10px] tracking-[0.12em] uppercase text-left py-0 pr-3.5 pb-2.5 border-b border-[var(--hair)]"
              style={{ color: "var(--mute)", width: "42%" }}
            >
              Query
            </th>
            <th
              className="font-mono text-[10px] tracking-[0.12em] uppercase text-left py-0 pr-3.5 pb-2.5 border-b border-[var(--hair)]"
              style={{ color: "var(--mute)", width: "16%" }}
            >
              Engine
            </th>
            <th
              className="font-mono text-[10px] tracking-[0.12em] uppercase text-left py-0 pb-2.5 border-b border-[var(--hair)]"
              style={{ color: "var(--mute)", width: "14%" }}
            >
              Status
            </th>
          </tr>
        </thead>
        <tbody>
          {results.map((r) => (
            <tr key={r.id}>
              <td
                className="font-serif italic text-lg py-[13px] pr-3.5 border-b border-[var(--hair)] align-top leading-snug"
                style={{ color: "var(--white)" }}
              >
                {r.query}
              </td>
              <td
                className="font-mono text-[10px] tracking-[0.08em] uppercase py-[13px] pr-3.5 border-b border-[var(--hair)] align-top"
                style={{ color: "var(--faint)" }}
              >
                {r.engine}
              </td>
              <td className="py-[13px] border-b border-[var(--hair)] align-top">
                {r.brand_cited ? (
                  <Badge variant="cited">Cited</Badge>
                ) : r.brand_mentioned ? (
                  <Badge variant="mentioned">Mentioned</Badge>
                ) : (
                  <Badge variant="not-found">Not Found</Badge>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 5: Verify build**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard
npm run build
```

Expected: Build succeeds.

- [ ] **Step 6: Commit**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
git add dashboard/components/report/
git commit -m "feat: report components — KPI grid, competitor table, query results"
```

---

### Task 9: ReportView (Full Report Renderer)

**Files:**
- Create: `dashboard/components/report/ReportView.tsx`

- [ ] **Step 1: Create ReportView**

This is the shared report renderer used by both admin preview and client report page. Create `dashboard/components/report/ReportView.tsx`:

```tsx
import { ReportHeader } from "./ReportHeader";
import { KPIGrid } from "./KPIGrid";
import { CompetitorTable } from "./CompetitorTable";
import { QueryResultsTable } from "./QueryResultsTable";
import type {
  Report,
  TrackerRun,
  TrackerResultClient,
} from "@/lib/types";
import { weekRangeLabel } from "@/lib/utils";

interface ReportViewProps {
  report: Report;
  run: TrackerRun | null;
  results: TrackerResultClient[];
  clientName: string;
  brandName: string;
  domain?: string;
  previousRuns?: TrackerRun[];
}

export function ReportView({
  report,
  run,
  results,
  clientName,
  brandName,
  domain,
  previousRuns = [],
}: ReportViewProps) {
  const checkSvg = (
    <svg
      width="9"
      height="9"
      viewBox="0 0 9 9"
      fill="none"
      aria-hidden="true"
    >
      <polyline
        points="1,4.5 3.5,7 8,1.5"
        stroke="var(--ink)"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );

  return (
    <div
      className="max-w-[860px] mx-auto py-[70px] px-[76px]"
      style={{
        background: "var(--ink-2)",
        color: "var(--white)",
        fontFamily: "var(--display)",
      }}
    >
      <ReportHeader
        clientName={clientName}
        weekStart={report.week_start}
        domain={domain}
      />

      {/* Executive Summary */}
      {report.exec_summary && (
        <div className="mt-[50px]">
          <h2
            className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
            style={{ color: "var(--mute)" }}
          >
            Executive Summary
          </h2>
          <p
            className="font-display font-light text-[22px] leading-[1.5] italic"
            style={{ color: "rgba(245,244,241,0.82)" }}
          >
            {report.exec_summary}
          </p>
        </div>
      )}

      {/* AI Visibility Scores */}
      {run && <KPIGrid run={run} previousRuns={previousRuns} />}

      {/* Competitor Comparison */}
      {run && <CompetitorTable run={run} brandName={brandName} />}

      {/* Query Results */}
      {results.length > 0 && <QueryResultsTable results={results} />}

      {/* Search Console Metrics */}
      {report.search_console && (
        <div className="mt-[50px]">
          <h2
            className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
            style={{ color: "var(--mute)" }}
          >
            Search Performance
          </h2>
          <div className="grid grid-cols-4 gap-px bg-[var(--hair)] border border-[var(--hair)]">
            {(
              [
                ["Impressions", report.search_console.impressions, 0],
                ["Clicks", report.search_console.clicks, 0],
                ["Avg. CTR", report.search_console.ctr, 2, "%"],
                ["Avg. Position", report.search_console.position, 1],
              ] as const
            ).map(([label, data, dp, suffix]) => (
              <div
                key={label}
                className="p-5 flex flex-col"
                style={{ background: "var(--ink-2)" }}
              >
                <div
                  className="font-mono text-[11px] tracking-[0.12em] uppercase mb-3"
                  style={{ color: "var(--mute)" }}
                >
                  {label}
                </div>
                <div
                  className="font-display font-light text-[40px] leading-none"
                  style={{ color: "var(--white)" }}
                >
                  {data?.week != null
                    ? `${data.week.toLocaleString("en-US", { minimumFractionDigits: dp as number, maximumFractionDigits: dp as number })}${suffix || ""}`
                    : "—"}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Highlights */}
      {report.highlights.filter((h) => h.text.trim()).length > 0 && (
        <div className="mt-[50px]">
          <h2
            className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
            style={{ color: "var(--mute)" }}
          >
            Highlights / Wins
          </h2>
          <ul className="list-none">
            {report.highlights
              .filter((h) => h.text.trim())
              .map((h, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3.5 py-3 border-b border-[var(--hair)] font-display text-base leading-snug"
                  style={{ color: "var(--white)" }}
                >
                  <span style={{ color: "var(--accent)" }}>—</span>
                  <span>{h.text}</span>
                </li>
              ))}
          </ul>
        </div>
      )}

      {/* Work Completed */}
      {report.work_completed.filter((w) => w.text.trim()).length > 0 && (
        <div className="mt-[50px]">
          <h2
            className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
            style={{ color: "var(--mute)" }}
          >
            Work Completed This Week
          </h2>
          <ul className="list-none">
            {report.work_completed
              .filter((w) => w.text.trim())
              .map((w, i) => (
                <li
                  key={i}
                  className={`flex items-start gap-3.5 py-3 border-b border-[var(--hair)] font-display text-base leading-snug ${w.done ? "opacity-60" : ""}`}
                  style={{ color: "var(--white)" }}
                >
                  <span
                    className="w-[15px] h-[15px] min-w-[15px] mt-0.5 flex items-center justify-center shrink-0"
                    style={{
                      border: w.done
                        ? "none"
                        : "1px solid rgba(245,244,241,0.42)",
                      background: w.done ? "var(--white)" : "transparent",
                    }}
                  >
                    {w.done && checkSvg}
                  </span>
                  <span>{w.text}</span>
                </li>
              ))}
          </ul>
        </div>
      )}

      {/* Priorities */}
      {report.priorities.filter((p) => p.text.trim()).length > 0 && (
        <div className="mt-[50px]">
          <h2
            className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
            style={{ color: "var(--mute)" }}
          >
            Next Week Priorities
          </h2>
          <ul className="list-none">
            {report.priorities
              .filter((p) => p.text.trim())
              .map((p, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3.5 py-3 border-b border-[var(--hair)] font-display text-base leading-snug"
                  style={{ color: "var(--white)" }}
                >
                  <span
                    className="font-mono text-[9px] tracking-[0.1em] shrink-0 min-w-[20px] pt-1"
                    style={{ color: "var(--accent)" }}
                  >
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span>{p.text}</span>
                </li>
              ))}
          </ul>
        </div>
      )}

      {/* Blockers */}
      {report.blockers.filter((b) => b.text.trim()).length > 0 && (
        <div className="mt-[50px]">
          <h2
            className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
            style={{ color: "var(--mute)" }}
          >
            Blockers / Risks
          </h2>
          <ul className="list-none">
            {report.blockers
              .filter((b) => b.text.trim())
              .map((b, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3.5 py-3 border-b border-[var(--hair)] font-display text-base leading-snug"
                  style={{ color: "var(--white)" }}
                >
                  <span style={{ color: "var(--neg)" }}>—</span>
                  <span>{b.text}</span>
                </li>
              ))}
          </ul>
        </div>
      )}

      {/* Notes */}
      {report.notes && (
        <div className="mt-[50px]">
          <h2
            className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
            style={{ color: "var(--mute)" }}
          >
            Notes &amp; Observations
          </h2>
          <p
            className="font-display italic font-light text-base leading-[1.7]"
            style={{ color: "var(--mute)" }}
          >
            {report.notes}
          </p>
        </div>
      )}

      {/* Footer */}
      <footer
        className="mt-16 pt-4 border-t border-[var(--hair)] flex justify-between gap-3 flex-wrap font-mono text-[9px] tracking-[0.14em] uppercase"
        style={{ color: "var(--faint)" }}
      >
        <span>
          Prepared by Victory Velocity &middot;{" "}
          {domain || "victoryvelocity.ca"}
        </span>
        <span>{weekRangeLabel(report.week_start)}</span>
      </footer>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard
npm run build
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
git add dashboard/components/report/ReportView.tsx
git commit -m "feat: full ReportView renderer matching VV report generator style"
```

---

### Task 10: Client Dashboard (Layout + Overview + Report List)

**Files:**
- Create: `dashboard/app/dashboard/layout.tsx`
- Create: `dashboard/app/dashboard/page.tsx`
- Create: `dashboard/components/dashboard/VisibilityOverview.tsx`
- Create: `dashboard/components/dashboard/TrendChart.tsx`
- Create: `dashboard/components/dashboard/ReportList.tsx`

- [ ] **Step 1: Create client dashboard layout**

Create `dashboard/app/dashboard/layout.tsx`:

```tsx
import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import Link from "next/link";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  const { data: clientUser } = await supabase
    .from("client_users")
    .select("role, client_id")
    .eq("user_id", user.id)
    .single();

  if (!clientUser || clientUser.role !== "client") redirect("/admin");

  const { data: client } = await supabase
    .from("clients")
    .select("name")
    .eq("id", clientUser.client_id)
    .single();

  return (
    <div className="min-h-screen" style={{ background: "var(--ink)" }}>
      {/* Nav — from landing page .nav */}
      <nav
        className="no-print h-[78px] flex items-center justify-between px-14"
        style={{
          background: "rgba(14,14,15,0.82)",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid var(--hair)",
        }}
      >
        <span
          className="font-serif text-[21px] tracking-[0.01em]"
          style={{ color: "var(--white)" }}
        >
          Victory Velocity
        </span>

        <div className="flex items-center gap-[30px]">
          <Link
            href="/dashboard"
            className="font-sans text-[12.5px] font-medium tracking-[0.08em] transition-colors hover:text-[var(--white)]"
            style={{ color: "var(--mute)" }}
          >
            Dashboard
          </Link>
          <span
            className="font-mono text-[10px] tracking-[0.1em] uppercase"
            style={{ color: "var(--faint)" }}
          >
            {client?.name}
          </span>
          <form action="/api/auth/signout" method="POST">
            <button
              type="submit"
              className="font-sans text-[12.5px] font-medium tracking-[0.08em] transition-colors bg-transparent border-none cursor-pointer hover:text-[var(--white)]"
              style={{ color: "var(--faint)" }}
            >
              Sign Out
            </button>
          </form>
        </div>
      </nav>

      <main className="max-w-[1280px] mx-auto px-14 py-12">
        {children}
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Create sign-out API route**

Create `dashboard/app/api/auth/signout/route.ts`:

```typescript
import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";

export async function POST() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/login");
}
```

- [ ] **Step 3: Create VisibilityOverview component**

Create `dashboard/components/dashboard/VisibilityOverview.tsx`:

```tsx
import { Card } from "@/components/ui/Card";
import { scoreColor, formatRate, formatDelta } from "@/lib/utils";
import type { TrackerRun } from "@/lib/types";

interface VisibilityOverviewProps {
  latestRun: TrackerRun | null;
  previousRun: TrackerRun | null;
  totalReports: number;
}

export function VisibilityOverview({
  latestRun,
  previousRun,
  totalReports,
}: VisibilityOverviewProps) {
  const mentionRate = latestRun?.aggregate_mention_rate ?? 0;
  const citationRate = latestRun?.aggregate_citation_rate ?? 0;
  const engineCount = latestRun
    ? Object.keys(latestRun.per_engine_scores).length
    : 0;

  const mentionDelta = formatDelta(
    mentionRate,
    previousRun?.aggregate_mention_rate ?? null
  );
  const citationDelta = formatDelta(
    citationRate,
    previousRun?.aggregate_citation_rate ?? null
  );

  const cards = [
    {
      label: "Overall Visibility",
      value: formatRate(mentionRate),
      color: scoreColor(mentionRate),
      delta: mentionDelta,
    },
    {
      label: "Citation Rate",
      value: formatRate(citationRate),
      color: scoreColor(citationRate),
      delta: citationDelta,
    },
    {
      label: "Engines Tracked",
      value: String(engineCount),
      color: "var(--white)",
      delta: null,
    },
    {
      label: "Reports Available",
      value: String(totalReports),
      color: "var(--white)",
      delta: null,
    },
  ];

  return (
    <div className="grid grid-cols-4 gap-4 mb-10">
      {cards.map((card) => (
        <Card key={card.label} elevated className="p-6 text-center">
          <div
            className="font-mono text-[10.5px] tracking-[0.2em] uppercase mb-2"
            style={{ color: "var(--mute)" }}
          >
            {card.label}
          </div>
          <div
            className="font-serif text-[56px] leading-none my-2"
            style={{ color: card.color }}
          >
            {card.value}
          </div>
          {card.delta && (
            <div
              className="font-mono text-[10px] tracking-[0.04em]"
              style={{
                color:
                  card.delta.direction === "up"
                    ? "var(--pos)"
                    : card.delta.direction === "down"
                      ? "var(--neg)"
                      : "var(--mute)",
              }}
            >
              {card.delta.direction === "up"
                ? "▲"
                : card.delta.direction === "down"
                  ? "▼"
                  : "■"}{" "}
              {card.delta.text} vs last week
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Create TrendChart component**

Create `dashboard/components/dashboard/TrendChart.tsx`:

```tsx
import { Card } from "@/components/ui/Card";
import { formatRate } from "@/lib/utils";
import type { TrackerRun } from "@/lib/types";

interface TrendChartProps {
  runs: TrackerRun[];
}

export function TrendChart({ runs }: TrendChartProps) {
  if (runs.length < 2) return null;

  const sorted = [...runs].sort(
    (a, b) => new Date(a.ran_at).getTime() - new Date(b.ran_at).getTime()
  );

  const values = sorted.map((r) => r.aggregate_mention_rate);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 0.01;

  const W = 800;
  const H = 200;
  const pad = 30;
  const stepX = (W - pad * 2) / (values.length - 1);

  const coords = values.map((v, i) => {
    const t = (v - min) / range;
    return [pad + i * stepX, pad + (1 - t) * (H - pad * 2)] as const;
  });

  const line = coords
    .map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`)
    .join(" ");

  const last = coords[coords.length - 1];

  return (
    <Card elevated className="p-6 mb-10">
      <div
        className="font-mono text-[11px] tracking-[0.12em] uppercase mb-4"
        style={{ color: "var(--mute)" }}
      >
        Visibility Trend
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 200 }}>
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((t) => {
          const y = pad + (1 - t) * (H - pad * 2);
          const val = min + t * range;
          return (
            <g key={t}>
              <line
                x1={pad}
                x2={W - pad}
                y1={y}
                y2={y}
                stroke="var(--hair)"
                strokeWidth={1}
              />
              <text
                x={pad - 8}
                y={y + 3}
                textAnchor="end"
                className="font-mono"
                style={{ fontSize: 9, fill: "var(--faint)" }}
              >
                {formatRate(val)}
              </text>
            </g>
          );
        })}

        {/* Line */}
        <path
          d={line}
          fill="none"
          stroke="var(--pos)"
          strokeWidth={2}
          vectorEffect="non-scaling-stroke"
        />

        {/* Dot on latest */}
        <circle
          cx={last[0]}
          cy={last[1]}
          r={4}
          fill="var(--white)"
          vectorEffect="non-scaling-stroke"
        />

        {/* Week labels */}
        {sorted.map((r, i) => {
          const x = pad + i * stepX;
          const date = new Date(r.ran_at);
          const label = date.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
          });
          return (
            <text
              key={r.id}
              x={x}
              y={H - 5}
              textAnchor="middle"
              className="font-mono"
              style={{ fontSize: 9, fill: "var(--faint)" }}
            >
              {label}
            </text>
          );
        })}
      </svg>
    </Card>
  );
}
```

- [ ] **Step 5: Create ReportList component**

Create `dashboard/components/dashboard/ReportList.tsx`:

```tsx
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { formatRate, weekRangeLabel, scoreColor } from "@/lib/utils";
import type { Report, TrackerRun } from "@/lib/types";

interface ReportListProps {
  reports: (Report & { tracker_run: TrackerRun | null })[];
}

export function ReportList({ reports }: ReportListProps) {
  if (reports.length === 0) {
    return (
      <div
        className="font-mono text-[10px] tracking-[0.08em] uppercase py-6"
        style={{ color: "var(--faint)" }}
      >
        No reports published yet.
      </div>
    );
  }

  return (
    <div>
      <div
        className="font-mono text-xs tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-0"
        style={{ color: "var(--mute)" }}
      >
        Weekly Reports
      </div>

      {reports.map((report) => {
        const rate = report.tracker_run?.aggregate_mention_rate;
        return (
          <Link
            key={report.id}
            href={`/dashboard/reports/${report.id}`}
            className="flex items-center gap-3.5 py-[13px] border-b border-[var(--hair)] transition-all duration-300 hover:pl-3.5"
            style={{ color: "var(--white)" }}
          >
            <span className="font-serif italic text-lg flex-1">
              {weekRangeLabel(report.week_start)}
            </span>

            {rate != null && (
              <span
                className="font-mono text-[10px] tracking-[0.1em] font-bold"
                style={{ color: scoreColor(rate) }}
              >
                {formatRate(rate)}
              </span>
            )}

            <span
              className="font-mono text-[10px] tracking-[0.16em] uppercase w-24 text-right"
              style={{ color: "var(--faint)" }}
            >
              {report.published_at
                ? new Date(report.published_at).toLocaleDateString(
                    "en-US",
                    { month: "short", day: "numeric" }
                  )
                : ""}
            </span>

            <span
              className="font-sans text-[12.5px] font-medium tracking-[0.08em] transition-colors"
              style={{ color: "var(--faint)" }}
            >
              View →
            </span>
          </Link>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 6: Create client dashboard page**

Create `dashboard/app/dashboard/page.tsx`:

```tsx
import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { VisibilityOverview } from "@/components/dashboard/VisibilityOverview";
import { TrendChart } from "@/components/dashboard/TrendChart";
import { ReportList } from "@/components/dashboard/ReportList";
import type { TrackerRun, Report } from "@/lib/types";

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  const { data: clientUser } = await supabase
    .from("client_users")
    .select("client_id")
    .eq("user_id", user.id)
    .single();

  if (!clientUser?.client_id) redirect("/login");

  const clientId = clientUser.client_id;

  // Fetch client info
  const { data: client } = await supabase
    .from("clients")
    .select("*")
    .eq("id", clientId)
    .single();

  // Fetch all tracker runs (sorted newest first)
  const { data: runs } = await supabase
    .from("tracker_runs")
    .select("*")
    .eq("client_id", clientId)
    .order("ran_at", { ascending: false });

  // Fetch published reports with linked tracker run
  const { data: reports } = await supabase
    .from("reports")
    .select("*, tracker_run:tracker_runs(*)")
    .eq("client_id", clientId)
    .eq("status", "published")
    .order("week_start", { ascending: false });

  const allRuns = (runs as TrackerRun[]) || [];
  const latestRun = allRuns[0] || null;
  const previousRun = allRuns[1] || null;
  const allReports = (reports as (Report & { tracker_run: TrackerRun | null })[]) || [];

  return (
    <>
      <h1
        className="font-serif text-[clamp(34px,4.4vw,58px)] font-normal leading-[1.02] tracking-[-0.02em] mb-10"
        style={{ color: "var(--white)" }}
      >
        {client?.brand_name || client?.name || "Dashboard"}
      </h1>

      <VisibilityOverview
        latestRun={latestRun}
        previousRun={previousRun}
        totalReports={allReports.length}
      />

      <TrendChart runs={allRuns} />

      <ReportList reports={allReports} />
    </>
  );
}
```

- [ ] **Step 7: Verify build**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard
npm run build
```

Expected: Build succeeds (pages won't render without Supabase, but compilation should pass).

- [ ] **Step 8: Commit**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
git add dashboard/app/dashboard/ dashboard/app/api/ dashboard/components/dashboard/
git commit -m "feat: client dashboard with visibility overview, trend chart, report list"
```

---

### Task 11: Client Report Page + Print CSS

**Files:**
- Create: `dashboard/app/dashboard/reports/[id]/page.tsx`

- [ ] **Step 1: Create client report page**

Create `dashboard/app/dashboard/reports/[id]/page.tsx`:

```tsx
import { createClient } from "@/lib/supabase/server";
import { redirect, notFound } from "next/navigation";
import { ReportView } from "@/components/report/ReportView";
import type { TrackerRun, TrackerResultClient } from "@/lib/types";

export default async function ClientReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  // Fetch report (RLS ensures only published + own client)
  const { data: report } = await supabase
    .from("reports")
    .select("*")
    .eq("id", id)
    .single();

  if (!report) notFound();

  // Fetch client
  const { data: client } = await supabase
    .from("clients")
    .select("*")
    .eq("id", report.client_id)
    .single();

  if (!client) notFound();

  // Fetch tracker run if linked
  let run: TrackerRun | null = null;
  let results: TrackerResultClient[] = [];
  let previousRuns: TrackerRun[] = [];

  if (report.run_id) {
    const { data: runData } = await supabase
      .from("tracker_runs")
      .select("*")
      .eq("id", report.run_id)
      .single();

    run = runData as TrackerRun | null;

    // Fetch results (client view — no response_text)
    const { data: resultsData } = await supabase
      .from("tracker_results_client")
      .select("*")
      .eq("run_id", report.run_id);

    results = (resultsData as TrackerResultClient[]) || [];

    // Fetch previous runs for sparklines
    if (run) {
      const { data: prevRuns } = await supabase
        .from("tracker_runs")
        .select("*")
        .eq("client_id", report.client_id)
        .lt("ran_at", run.ran_at)
        .order("ran_at", { ascending: false })
        .limit(7);

      previousRuns = ((prevRuns as TrackerRun[]) || []).reverse();
    }
  }

  return (
    <>
      {/* Print button */}
      <div className="no-print mb-6 flex justify-end">
        <button
          onClick={() => {}}
          className="font-mono text-[10px] tracking-[0.15em] uppercase py-2.5 px-6 cursor-pointer transition-opacity hover:opacity-85"
          style={{
            background: "var(--white)",
            color: "var(--ink)",
            border: "none",
          }}
        >
          Export PDF
        </button>
      </div>

      <ReportView
        report={report}
        run={run}
        results={results}
        clientName={client.name}
        brandName={client.brand_name}
        domain={client.website_domain}
        previousRuns={previousRuns}
      />
    </>
  );
}
```

Note: The "Export PDF" button uses `window.print()`. Since this is a Server Component, we need a small client wrapper for the button. Replace the button with a client component:

Create `dashboard/components/ui/PrintButton.tsx`:

```tsx
"use client";

export function PrintButton() {
  return (
    <button
      onClick={() => window.print()}
      className="font-mono text-[10px] tracking-[0.15em] uppercase py-2.5 px-6 cursor-pointer transition-opacity hover:opacity-85"
      style={{
        background: "var(--white)",
        color: "var(--ink)",
        border: "none",
      }}
    >
      Export PDF
    </button>
  );
}
```

Then update the report page to import `PrintButton` and replace the inline button:

```tsx
import { PrintButton } from "@/components/ui/PrintButton";

// In the JSX, replace the button with:
<div className="no-print mb-6 flex justify-end">
  <PrintButton />
</div>
```

- [ ] **Step 2: Verify build**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard
npm run build
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
git add dashboard/app/dashboard/reports/ dashboard/components/ui/PrintButton.tsx
git commit -m "feat: client report page with PDF export via browser print"
```

---

### Task 12: Admin Layout + Client List

**Files:**
- Create: `dashboard/app/admin/layout.tsx`
- Create: `dashboard/app/admin/page.tsx`
- Create: `dashboard/components/admin/ClientCard.tsx`

- [ ] **Step 1: Create admin layout**

Create `dashboard/app/admin/layout.tsx`:

```tsx
import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import Link from "next/link";

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  const { data: clientUser } = await supabase
    .from("client_users")
    .select("role")
    .eq("user_id", user.id)
    .single();

  if (!clientUser || clientUser.role !== "admin") redirect("/dashboard");

  return (
    <div className="min-h-screen" style={{ background: "var(--ink)" }}>
      {/* Nav */}
      <nav
        className="no-print h-[78px] flex items-center justify-between px-14"
        style={{
          background: "rgba(14,14,15,0.82)",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid var(--hair)",
        }}
      >
        <div className="flex items-center gap-3">
          <span
            className="font-serif text-[21px] tracking-[0.01em]"
            style={{ color: "var(--white)" }}
          >
            Victory Velocity
          </span>
          <span
            className="font-mono text-[8px] tracking-[0.2em] uppercase py-[3px] px-[7px]"
            style={{
              color: "var(--mute)",
              border: "1px solid var(--ghost)",
            }}
          >
            Admin
          </span>
        </div>

        <div className="flex items-center gap-[30px]">
          <Link
            href="/admin"
            className="font-sans text-[12.5px] font-medium tracking-[0.08em] transition-colors hover:text-[var(--white)]"
            style={{ color: "var(--mute)" }}
          >
            Clients
          </Link>
          <form action="/api/auth/signout" method="POST">
            <button
              type="submit"
              className="font-sans text-[12.5px] font-medium tracking-[0.08em] transition-colors bg-transparent border-none cursor-pointer hover:text-[var(--white)]"
              style={{ color: "var(--faint)" }}
            >
              Sign Out
            </button>
          </form>
        </div>
      </nav>

      <main className="max-w-[1280px] mx-auto px-14 py-12">
        {children}
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Create ClientCard component**

Create `dashboard/components/admin/ClientCard.tsx`:

```tsx
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { scoreColor, formatRate } from "@/lib/utils";
import type { Client, TrackerRun, Report } from "@/lib/types";

interface ClientCardProps {
  client: Client;
  latestRun: TrackerRun | null;
  latestReport: Report | null;
}

export function ClientCard({
  client,
  latestRun,
  latestReport,
}: ClientCardProps) {
  const rate = latestRun?.aggregate_mention_rate;

  return (
    <Card elevated className="p-6">
      <h3
        className="font-serif text-[28px] font-normal tracking-[-0.02em] mb-1"
        style={{ color: "var(--white)" }}
      >
        {client.name}
      </h3>

      <div
        className="font-mono text-[11px] tracking-[0.1em] uppercase mb-4"
        style={{ color: "var(--faint)" }}
      >
        {client.website_domain || "no domain"}
      </div>

      {rate != null && (
        <div className="mb-2">
          <span
            className="font-serif text-[40px] font-light leading-none"
            style={{ color: scoreColor(rate) }}
          >
            {formatRate(rate)}
          </span>
          <span
            className="font-mono text-[9px] tracking-[0.1em] uppercase ml-2"
            style={{ color: "var(--faint)" }}
          >
            visibility
          </span>
        </div>
      )}

      <div
        className="font-mono text-[10px] tracking-[0.08em] mb-4"
        style={{ color: "var(--faint)" }}
      >
        {latestRun
          ? `Last run: ${new Date(latestRun.ran_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}`
          : "No runs yet"}
      </div>

      <div className="flex items-center gap-2 mb-4">
        {latestReport ? (
          <Badge variant={latestReport.status === "published" ? "published" : "draft"}>
            {latestReport.status}
          </Badge>
        ) : (
          <span
            className="font-mono text-[8px] tracking-[0.1em] uppercase"
            style={{ color: "var(--faint)" }}
          >
            No report
          </span>
        )}
      </div>

      <div className="flex gap-2">
        <Link
          href={`/admin/clients/${client.id}`}
          className="font-sans text-[13px] font-semibold tracking-[0.06em] inline-flex items-center py-[11px] px-[20px] transition-all duration-300 border rounded-[2px]"
          style={{
            borderColor: "var(--ghost)",
            color: "var(--white)",
          }}
        >
          View
        </Link>
      </div>
    </Card>
  );
}
```

- [ ] **Step 3: Create admin home page**

Create `dashboard/app/admin/page.tsx`:

```tsx
import { createClient } from "@/lib/supabase/server";
import { ClientCard } from "@/components/admin/ClientCard";
import { Button } from "@/components/ui/Button";
import Link from "next/link";
import type { Client, TrackerRun, Report } from "@/lib/types";

export default async function AdminPage() {
  const supabase = await createClient();

  const { data: clients } = await supabase
    .from("clients")
    .select("*")
    .order("created_at", { ascending: true });

  const allClients = (clients as Client[]) || [];

  // Fetch latest run and report for each client
  const clientsWithData = await Promise.all(
    allClients.map(async (client) => {
      const { data: runs } = await supabase
        .from("tracker_runs")
        .select("*")
        .eq("client_id", client.id)
        .order("ran_at", { ascending: false })
        .limit(1);

      const { data: reports } = await supabase
        .from("reports")
        .select("*")
        .eq("client_id", client.id)
        .order("created_at", { ascending: false })
        .limit(1);

      return {
        client,
        latestRun: (runs?.[0] as TrackerRun) || null,
        latestReport: (reports?.[0] as Report) || null,
      };
    })
  );

  return (
    <>
      <div className="flex items-center justify-between mb-10">
        <h1
          className="font-serif text-[clamp(34px,4.4vw,58px)] font-normal leading-[1.02] tracking-[-0.02em]"
          style={{ color: "var(--white)" }}
        >
          Clients
        </h1>
      </div>

      {clientsWithData.length === 0 ? (
        <p
          className="font-serif text-lg italic"
          style={{ color: "var(--mute)" }}
        >
          No clients yet. Create one in Supabase or use the tracker upload.
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {clientsWithData.map(({ client, latestRun, latestReport }) => (
            <ClientCard
              key={client.id}
              client={client}
              latestRun={latestRun}
              latestReport={latestReport}
            />
          ))}
        </div>
      )}
    </>
  );
}
```

- [ ] **Step 4: Verify build**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard
npm run build
```

Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
git add dashboard/app/admin/ dashboard/components/admin/ClientCard.tsx
git commit -m "feat: admin layout and client list page"
```

---

### Task 13: Admin Client Detail

**Files:**
- Create: `dashboard/app/admin/clients/[id]/page.tsx`
- Create: `dashboard/components/admin/InviteClientForm.tsx`

- [ ] **Step 1: Create InviteClientForm**

Create `dashboard/components/admin/InviteClientForm.tsx`:

```tsx
"use client";

import { useState } from "react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

interface InviteClientFormProps {
  clientId: string;
}

export function InviteClientForm({ clientId }: InviteClientFormProps) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    setStatus("sending");

    const res = await fetch("/api/admin/invite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, clientId }),
    });

    if (res.ok) {
      setStatus("sent");
      setEmail("");
    } else {
      setStatus("error");
    }
  }

  return (
    <form onSubmit={handleInvite} className="flex items-end gap-3">
      <div className="flex-1">
        <Input
          label="Invite client user"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="client@company.com"
          required
        />
      </div>
      <Button
        type="submit"
        variant="solid"
        disabled={status === "sending"}
        className="mb-3.5 py-[11px] px-[20px] text-[12px]"
      >
        {status === "sending" ? "Sending…" : status === "sent" ? "Sent!" : "Invite"}
      </Button>
    </form>
  );
}
```

- [ ] **Step 2: Create invite API route**

Create `dashboard/app/api/admin/invite/route.ts`:

```typescript
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { NextResponse } from "next/server";

export async function POST(request: Request) {
  // Verify caller is admin
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { data: clientUser } = await supabase
    .from("client_users")
    .select("role")
    .eq("user_id", user.id)
    .single();

  if (clientUser?.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  const { email, clientId } = await request.json();
  if (!email || !clientId) {
    return NextResponse.json(
      { error: "Missing email or clientId" },
      { status: 400 }
    );
  }

  const admin = createAdminClient();

  // Invite user via Supabase Auth
  const { data: inviteData, error: inviteError } =
    await admin.auth.admin.inviteUserByEmail(email, {
      redirectTo: `${request.headers.get("origin")}/login/callback`,
    });

  if (inviteError) {
    return NextResponse.json(
      { error: inviteError.message },
      { status: 500 }
    );
  }

  // Create client_users row
  if (inviteData.user) {
    await admin.from("client_users").insert({
      user_id: inviteData.user.id,
      client_id: clientId,
      role: "client",
    });
  }

  return NextResponse.json({ success: true });
}
```

- [ ] **Step 3: Create client detail page**

Create `dashboard/app/admin/clients/[id]/page.tsx`:

```tsx
import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { SectionLabel } from "@/components/ui/SectionLabel";
import { InviteClientForm } from "@/components/admin/InviteClientForm";
import { formatRate, scoreColor, weekRangeLabel } from "@/lib/utils";
import type { Client, TrackerRun, Report } from "@/lib/types";

export default async function AdminClientDetailPage({
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

  // Tracker runs
  const { data: runs } = await supabase
    .from("tracker_runs")
    .select("*")
    .eq("client_id", id)
    .order("ran_at", { ascending: false });

  // Reports
  const { data: reports } = await supabase
    .from("reports")
    .select("*")
    .eq("client_id", id)
    .order("created_at", { ascending: false });

  // Linked users
  const { data: users } = await supabase
    .from("client_users")
    .select("id, user_id, role, created_at")
    .eq("client_id", id);

  const allRuns = (runs as TrackerRun[]) || [];
  const allReports = (reports as Report[]) || [];

  return (
    <>
      <Link
        href="/admin"
        className="font-mono text-[11px] tracking-[0.16em] uppercase inline-block mb-10 transition-colors hover:text-[var(--mute)]"
        style={{ color: "var(--faint)" }}
      >
        ← Clients
      </Link>

      <h1
        className="font-serif text-[clamp(36px,5.2vw,64px)] font-normal leading-[1.04] tracking-[-0.025em] mb-2"
        style={{ color: "var(--white)" }}
      >
        {(client as Client).name}
      </h1>

      <div
        className="font-mono text-[11px] tracking-[0.1em] uppercase mb-10"
        style={{ color: "var(--faint)" }}
      >
        {(client as Client).website_domain || "No domain set"}
      </div>

      {/* Client Config */}
      <Card elevated className="p-6 mb-8">
        <SectionLabel>Client Configuration</SectionLabel>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div
              className="font-mono text-[10px] tracking-[0.1em] uppercase mb-1"
              style={{ color: "var(--faint)" }}
            >
              Brand
            </div>
            <div className="font-serif text-base" style={{ color: "var(--white)" }}>
              {(client as Client).brand_name}
            </div>
          </div>
          <div>
            <div
              className="font-mono text-[10px] tracking-[0.1em] uppercase mb-1"
              style={{ color: "var(--faint)" }}
            >
              Variations
            </div>
            <div className="flex flex-wrap gap-1">
              {((client as Client).brand_variations || []).map((v: string) => (
                <span
                  key={v}
                  className="font-mono text-[9px] tracking-[0.08em] py-0.5 px-2"
                  style={{
                    color: "var(--mute)",
                    border: "1px solid var(--ghost)",
                  }}
                >
                  {v}
                </span>
              ))}
            </div>
          </div>
          <div>
            <div
              className="font-mono text-[10px] tracking-[0.1em] uppercase mb-1"
              style={{ color: "var(--faint)" }}
            >
              Queries ({((client as Client).target_queries || []).length})
            </div>
            <ul className="list-none">
              {((client as Client).target_queries || []).map((q: string) => (
                <li
                  key={q}
                  className="font-serif italic text-sm py-0.5"
                  style={{ color: "var(--mute)" }}
                >
                  {q}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div
              className="font-mono text-[10px] tracking-[0.1em] uppercase mb-1"
              style={{ color: "var(--faint)" }}
            >
              Competitors ({((client as Client).competitors || []).length})
            </div>
            <div className="flex flex-wrap gap-1">
              {((client as Client).competitors || []).map((c: string) => (
                <span
                  key={c}
                  className="font-mono text-[9px] tracking-[0.08em] py-0.5 px-2"
                  style={{
                    color: "var(--mute)",
                    border: "1px solid var(--ghost)",
                  }}
                >
                  {c}
                </span>
              ))}
            </div>
          </div>
        </div>
      </Card>

      {/* User Management */}
      <Card elevated className="p-6 mb-8">
        <SectionLabel>Linked Users</SectionLabel>
        {(users || []).length > 0 ? (
          <div className="mb-4">
            {(users || []).map((u) => (
              <div
                key={u.id}
                className="flex items-center gap-3 py-2 border-b border-[var(--hair)]"
              >
                <span
                  className="font-mono text-[10px] tracking-[0.08em]"
                  style={{ color: "var(--mute)" }}
                >
                  {u.user_id}
                </span>
                <Badge variant={u.role === "admin" ? "published" : "draft"}>
                  {u.role}
                </Badge>
              </div>
            ))}
          </div>
        ) : (
          <p
            className="font-mono text-[10px] tracking-[0.08em] uppercase mb-4"
            style={{ color: "var(--faint)" }}
          >
            No users linked yet.
          </p>
        )}
        <InviteClientForm clientId={id} />
      </Card>

      {/* Tracker Run History */}
      <Card elevated className="p-6 mb-8">
        <SectionLabel>Tracker Run History</SectionLabel>
        {allRuns.length === 0 ? (
          <p
            className="font-mono text-[10px] tracking-[0.08em] uppercase"
            style={{ color: "var(--faint)" }}
          >
            No tracker runs yet. Run the tracker with --upload.
          </p>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <th
                  className="font-mono text-[10px] tracking-[0.12em] uppercase text-left pb-2.5 border-b border-[var(--hair)]"
                  style={{ color: "var(--mute)" }}
                >
                  Date
                </th>
                <th
                  className="font-mono text-[10px] tracking-[0.12em] uppercase text-left pb-2.5 border-b border-[var(--hair)]"
                  style={{ color: "var(--mute)" }}
                >
                  Mention
                </th>
                <th
                  className="font-mono text-[10px] tracking-[0.12em] uppercase text-left pb-2.5 border-b border-[var(--hair)]"
                  style={{ color: "var(--mute)" }}
                >
                  Citation
                </th>
                <th className="pb-2.5 border-b border-[var(--hair)]"></th>
              </tr>
            </thead>
            <tbody>
              {allRuns.map((run) => {
                const hasReport = allReports.some(
                  (r) => r.run_id === run.id
                );
                return (
                  <tr key={run.id}>
                    <td
                      className="font-mono text-[11px] tracking-[0.08em] py-3 border-b border-[var(--hair)]"
                      style={{ color: "var(--mute)" }}
                    >
                      {new Date(run.ran_at).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                        hour: "numeric",
                        minute: "2-digit",
                      })}
                    </td>
                    <td className="py-3 border-b border-[var(--hair)]">
                      <span
                        className="font-bold"
                        style={{
                          color: scoreColor(run.aggregate_mention_rate),
                        }}
                      >
                        {formatRate(run.aggregate_mention_rate)}
                      </span>
                    </td>
                    <td className="py-3 border-b border-[var(--hair)]">
                      <span
                        className="font-bold"
                        style={{
                          color: scoreColor(run.aggregate_citation_rate),
                        }}
                      >
                        {formatRate(run.aggregate_citation_rate)}
                      </span>
                    </td>
                    <td className="py-3 border-b border-[var(--hair)] text-right">
                      {hasReport ? (
                        <span
                          className="font-mono text-[9px] tracking-[0.1em] uppercase"
                          style={{ color: "var(--faint)" }}
                        >
                          Report exists
                        </span>
                      ) : (
                        <Link
                          href={`/api/admin/create-report?runId=${run.id}&clientId=${run.client_id}`}
                          className="font-mono text-[9px] tracking-[0.1em] uppercase py-1 px-2 transition-colors"
                          style={{
                            color: "var(--white)",
                            border: "1px solid var(--ghost)",
                          }}
                        >
                          Create Report
                        </Link>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>

      {/* Reports */}
      <Card elevated className="p-6">
        <SectionLabel>Reports</SectionLabel>
        {allReports.length === 0 ? (
          <p
            className="font-mono text-[10px] tracking-[0.08em] uppercase"
            style={{ color: "var(--faint)" }}
          >
            No reports yet.
          </p>
        ) : (
          <div>
            {allReports.map((report) => (
              <Link
                key={report.id}
                href={`/admin/reports/${report.id}`}
                className="flex items-center gap-3.5 py-3 border-b border-[var(--hair)] transition-all duration-300 hover:pl-3.5"
                style={{ color: "var(--white)" }}
              >
                <span className="font-serif italic text-base flex-1">
                  {weekRangeLabel(report.week_start)}
                </span>
                <Badge
                  variant={
                    report.status === "published" ? "published" : "draft"
                  }
                >
                  {report.status}
                </Badge>
              </Link>
            ))}
          </div>
        )}
      </Card>
    </>
  );
}
```

- [ ] **Step 4: Create create-report API route**

Create `dashboard/app/api/admin/create-report/route.ts`:

```typescript
import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const runId = searchParams.get("runId");
  const clientId = searchParams.get("clientId");

  if (!runId || !clientId) {
    return new Response("Missing params", { status: 400 });
  }

  const supabase = await createClient();

  // Verify admin
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return new Response("Unauthorized", { status: 401 });

  const { data: clientUser } = await supabase
    .from("client_users")
    .select("role")
    .eq("user_id", user.id)
    .single();

  if (clientUser?.role !== "admin") {
    return new Response("Forbidden", { status: 403 });
  }

  // Get run date for week_start
  const { data: run } = await supabase
    .from("tracker_runs")
    .select("ran_at")
    .eq("id", runId)
    .single();

  if (!run) return new Response("Run not found", { status: 404 });

  const ranDate = new Date(run.ran_at);
  const day = ranDate.getDay();
  const monday = new Date(ranDate);
  monday.setDate(ranDate.getDate() - ((day + 6) % 7));
  const weekStart = monday.toISOString().split("T")[0];

  const { data: report, error } = await supabase
    .from("reports")
    .insert({
      client_id: clientId,
      run_id: runId,
      week_start: weekStart,
      status: "draft",
    })
    .select()
    .single();

  if (error) {
    return new Response(error.message, { status: 500 });
  }

  redirect(`/admin/reports/${report.id}`);
}
```

- [ ] **Step 5: Verify build**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard
npm run build
```

Expected: Build succeeds.

- [ ] **Step 6: Commit**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
git add dashboard/app/admin/clients/ dashboard/app/api/admin/ dashboard/components/admin/InviteClientForm.tsx
git commit -m "feat: admin client detail with run history, user management, report creation"
```

---

### Task 14: Admin Report Editor

**Files:**
- Create: `dashboard/app/admin/reports/[id]/page.tsx`
- Create: `dashboard/components/admin/ReportEditor.tsx`

- [ ] **Step 1: Create ReportEditor component**

Create `dashboard/components/admin/ReportEditor.tsx`:

```tsx
"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { Input, Textarea } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { SectionLabel } from "@/components/ui/SectionLabel";
import { ReportView } from "@/components/report/ReportView";
import type {
  Report,
  TrackerRun,
  TrackerResultClient,
  Client,
} from "@/lib/types";

interface ReportEditorProps {
  initialReport: Report;
  run: TrackerRun | null;
  results: TrackerResultClient[];
  client: Client;
  previousRuns: TrackerRun[];
}

export function ReportEditor({
  initialReport,
  run,
  results,
  client,
  previousRuns,
}: ReportEditorProps) {
  const [report, setReport] = useState<Report>(initialReport);
  const [saving, setSaving] = useState(false);

  function update(partial: Partial<Report>) {
    setReport((prev) => ({ ...prev, ...partial }));
  }

  async function save(newStatus?: "draft" | "published") {
    setSaving(true);
    const supabase = createClient();

    const updates: Record<string, unknown> = {
      exec_summary: report.exec_summary,
      work_completed: report.work_completed,
      priorities: report.priorities,
      highlights: report.highlights,
      blockers: report.blockers,
      notes: report.notes,
      search_console: report.search_console,
    };

    if (newStatus) {
      updates.status = newStatus;
      if (newStatus === "published") updates.published_at = new Date().toISOString();
      else updates.published_at = null;
    }

    await supabase.from("reports").update(updates).eq("id", report.id);

    if (newStatus) update({ status: newStatus, published_at: updates.published_at as string | null });
    setSaving(false);
  }

  function addListItem(field: "work_completed" | "priorities" | "highlights" | "blockers") {
    const arr = [...(report[field] as { text: string }[])];
    if (field === "work_completed") {
      (arr as { text: string; done: boolean }[]).push({ text: "", done: false });
    } else {
      arr.push({ text: "" });
    }
    update({ [field]: arr });
  }

  function updateListItem(field: string, index: number, value: string) {
    const arr = [...(report[field as keyof Report] as { text: string }[])];
    arr[index] = { ...arr[index], text: value };
    update({ [field]: arr });
  }

  function removeListItem(field: string, index: number) {
    const arr = [...(report[field as keyof Report] as { text: string }[])];
    arr.splice(index, 1);
    update({ [field]: arr });
  }

  return (
    <div className="flex gap-0 min-h-[calc(100vh-78px-48px)]">
      {/* Left pane — Editor (420px, matching report generator) */}
      <aside
        className="w-[420px] shrink-0 overflow-y-auto py-8 px-6"
        style={{
          background: "var(--ink-soft)",
          borderRight: "1px solid var(--hair)",
        }}
      >
        {/* Status + actions */}
        <div className="flex items-center gap-2 mb-6">
          <span
            className="font-mono text-[8px] tracking-[0.1em] uppercase py-[4px] px-[9px]"
            style={{
              color:
                report.status === "published"
                  ? "var(--ink)"
                  : "var(--mute)",
              background:
                report.status === "published"
                  ? "var(--pos)"
                  : "transparent",
              border:
                report.status !== "published"
                  ? "1px solid rgba(245,244,241,0.42)"
                  : "none",
            }}
          >
            {report.status}
          </span>
          <div className="ml-auto flex gap-2">
            <Button
              variant="outline"
              onClick={() => save()}
              disabled={saving}
              className="py-[8px] px-[16px] text-[11px]"
            >
              {saving ? "Saving…" : "Save"}
            </Button>
            {report.status === "draft" ? (
              <Button
                variant="solid"
                onClick={() => save("published")}
                disabled={saving}
                className="py-[8px] px-[16px] text-[11px]"
              >
                Publish
              </Button>
            ) : (
              <Button
                variant="outline"
                onClick={() => save("draft")}
                disabled={saving}
                className="py-[8px] px-[16px] text-[11px]"
              >
                Unpublish
              </Button>
            )}
          </div>
        </div>

        {/* Executive Summary */}
        <SectionLabel>Executive Summary</SectionLabel>
        <Textarea
          value={report.exec_summary}
          onChange={(e) => update({ exec_summary: e.target.value })}
          placeholder="One short paragraph: the headline story of the week…"
          rows={4}
        />

        {/* Highlights */}
        <SectionLabel>Highlights / Wins</SectionLabel>
        {report.highlights.map((h, i) => (
          <div key={i} className="flex items-center gap-2 mb-2">
            <input
              type="text"
              value={h.text}
              onChange={(e) => updateListItem("highlights", i, e.target.value)}
              placeholder="Win or highlight…"
              className="flex-1 bg-transparent border border-[var(--ghost)] text-[var(--white)] font-serif text-sm py-1.5 px-2 outline-none focus:border-[rgba(245,244,241,0.42)]"
            />
            <button
              onClick={() => removeListItem("highlights", i)}
              className="text-[var(--faint)] hover:text-[var(--neg)] bg-transparent border-none cursor-pointer text-sm"
            >
              ×
            </button>
          </div>
        ))}
        <button
          onClick={() => addListItem("highlights")}
          className="font-mono text-[9px] tracking-[0.15em] uppercase py-[7px] px-4 mt-1 mb-6 cursor-pointer transition-colors bg-transparent text-[var(--mute)] border border-[var(--ghost)] hover:text-[var(--white)] hover:border-[rgba(245,244,241,0.42)]"
        >
          + Add Highlight
        </button>

        {/* Work Completed */}
        <SectionLabel>Work Completed</SectionLabel>
        {report.work_completed.map((w, i) => (
          <div key={i} className="flex items-center gap-2 mb-2">
            <input
              type="checkbox"
              checked={w.done}
              onChange={(e) => {
                const arr = [...report.work_completed];
                arr[i] = { ...arr[i], done: e.target.checked };
                update({ work_completed: arr });
              }}
              className="w-4 h-4 shrink-0 cursor-pointer accent-[var(--white)]"
            />
            <input
              type="text"
              value={w.text}
              onChange={(e) => updateListItem("work_completed", i, e.target.value)}
              placeholder="Task description…"
              className="flex-1 bg-transparent border border-[var(--ghost)] text-[var(--white)] font-serif text-sm py-1.5 px-2 outline-none focus:border-[rgba(245,244,241,0.42)]"
            />
            <button
              onClick={() => removeListItem("work_completed", i)}
              className="text-[var(--faint)] hover:text-[var(--neg)] bg-transparent border-none cursor-pointer text-sm"
            >
              ×
            </button>
          </div>
        ))}
        <button
          onClick={() => addListItem("work_completed")}
          className="font-mono text-[9px] tracking-[0.15em] uppercase py-[7px] px-4 mt-1 mb-6 cursor-pointer transition-colors bg-transparent text-[var(--mute)] border border-[var(--ghost)] hover:text-[var(--white)] hover:border-[rgba(245,244,241,0.42)]"
        >
          + Add Item
        </button>

        {/* Priorities */}
        <SectionLabel>Next Week Priorities</SectionLabel>
        {report.priorities.map((p, i) => (
          <div key={i} className="flex items-center gap-2 mb-2">
            <span
              className="font-mono text-[9px] tracking-[0.1em] shrink-0 min-w-[20px] text-center"
              style={{ color: "var(--faint)" }}
            >
              {String(i + 1).padStart(2, "0")}
            </span>
            <input
              type="text"
              value={p.text}
              onChange={(e) => updateListItem("priorities", i, e.target.value)}
              placeholder="Priority…"
              className="flex-1 bg-transparent border border-[var(--ghost)] text-[var(--white)] font-serif text-sm py-1.5 px-2 outline-none focus:border-[rgba(245,244,241,0.42)]"
            />
            <button
              onClick={() => removeListItem("priorities", i)}
              className="text-[var(--faint)] hover:text-[var(--neg)] bg-transparent border-none cursor-pointer text-sm"
            >
              ×
            </button>
          </div>
        ))}
        <button
          onClick={() => addListItem("priorities")}
          className="font-mono text-[9px] tracking-[0.15em] uppercase py-[7px] px-4 mt-1 mb-6 cursor-pointer transition-colors bg-transparent text-[var(--mute)] border border-[var(--ghost)] hover:text-[var(--white)] hover:border-[rgba(245,244,241,0.42)]"
        >
          + Add Priority
        </button>

        {/* Blockers */}
        <SectionLabel>Blockers / Risks</SectionLabel>
        {report.blockers.map((b, i) => (
          <div key={i} className="flex items-center gap-2 mb-2">
            <input
              type="text"
              value={b.text}
              onChange={(e) => updateListItem("blockers", i, e.target.value)}
              placeholder="Blocker or risk…"
              className="flex-1 bg-transparent border border-[var(--ghost)] text-[var(--white)] font-serif text-sm py-1.5 px-2 outline-none focus:border-[rgba(245,244,241,0.42)]"
            />
            <button
              onClick={() => removeListItem("blockers", i)}
              className="text-[var(--faint)] hover:text-[var(--neg)] bg-transparent border-none cursor-pointer text-sm"
            >
              ×
            </button>
          </div>
        ))}
        <button
          onClick={() => addListItem("blockers")}
          className="font-mono text-[9px] tracking-[0.15em] uppercase py-[7px] px-4 mt-1 mb-6 cursor-pointer transition-colors bg-transparent text-[var(--mute)] border border-[var(--ghost)] hover:text-[var(--white)] hover:border-[rgba(245,244,241,0.42)]"
        >
          + Add Blocker
        </button>

        {/* Notes */}
        <SectionLabel>Notes / Observations</SectionLabel>
        <Textarea
          value={report.notes}
          onChange={(e) => update({ notes: e.target.value })}
          placeholder="Optional observations…"
          rows={5}
        />
      </aside>

      {/* Right pane — Live Preview */}
      <div
        className="flex-1 overflow-y-auto py-10"
        style={{ background: "#0e0e0e" }}
      >
        <ReportView
          report={report}
          run={run}
          results={results}
          clientName={client.name}
          brandName={client.brand_name}
          domain={client.website_domain}
          previousRuns={previousRuns}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create admin report editor page**

Create `dashboard/app/admin/reports/[id]/page.tsx`:

```tsx
import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import { ReportEditor } from "@/components/admin/ReportEditor";
import type {
  Report,
  TrackerRun,
  TrackerResultClient,
  Client,
} from "@/lib/types";

export default async function AdminReportEditorPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();

  const { data: report } = await supabase
    .from("reports")
    .select("*")
    .eq("id", id)
    .single();

  if (!report) notFound();

  const { data: client } = await supabase
    .from("clients")
    .select("*")
    .eq("id", report.client_id)
    .single();

  if (!client) notFound();

  let run: TrackerRun | null = null;
  let results: TrackerResultClient[] = [];
  let previousRuns: TrackerRun[] = [];

  if (report.run_id) {
    const { data: runData } = await supabase
      .from("tracker_runs")
      .select("*")
      .eq("id", report.run_id)
      .single();

    run = runData as TrackerRun | null;

    const { data: resultsData } = await supabase
      .from("tracker_results_client")
      .select("*")
      .eq("run_id", report.run_id);

    results = (resultsData as TrackerResultClient[]) || [];

    if (run) {
      const { data: prevRuns } = await supabase
        .from("tracker_runs")
        .select("*")
        .eq("client_id", report.client_id)
        .lt("ran_at", run.ran_at)
        .order("ran_at", { ascending: false })
        .limit(7);

      previousRuns = ((prevRuns as TrackerRun[]) || []).reverse();
    }
  }

  return (
    <ReportEditor
      initialReport={report as Report}
      run={run}
      results={results}
      client={client as Client}
      previousRuns={previousRuns}
    />
  );
}
```

- [ ] **Step 3: Verify build**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard
npm run build
```

Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
git add dashboard/app/admin/reports/ dashboard/components/admin/ReportEditor.tsx
git commit -m "feat: admin report editor with two-pane layout and live preview"
```

---

### Task 15: Tracker Supabase Upload (Python, TDD)

**Files:**
- Create: `agents/src/upload.py`
- Create: `agents/tests/test_upload.py`
- Modify: `agents/pyproject.toml`
- Modify: `agents/.env.example`
- Modify: `agents/run.py`
- Modify: `clients/childspot.json`

- [ ] **Step 1: Add supabase dependency**

In `agents/pyproject.toml`, add `"supabase>=2.0.0"` to the dependencies list:

```toml
[project]
name = "geo-tracker"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "openai>=1.82.0",
    "anthropic>=0.52.0",
    "google-genai>=1.14.0",
    "python-dotenv>=1.0.0",
    "supabase>=2.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0"]
```

- [ ] **Step 2: Install the dependency**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents
source .venv/bin/activate
pip install -e ".[dev]"
```

- [ ] **Step 3: Update .env.example**

Append to `agents/.env.example`:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
```

- [ ] **Step 4: Write failing tests for upload**

Create `agents/tests/test_upload.py`:

```python
from unittest.mock import MagicMock, patch
import pytest
from src.upload import upload_run


@pytest.fixture
def sample_results():
    return [
        {
            "query": "best childcare finder",
            "engine": "chatgpt",
            "model": "gpt-4o-mini",
            "response_text": "Here are some options...",
            "brand_mentioned": False,
            "brand_cited": False,
            "citation_url": "",
            "competitor_mentions": ["Care.com"],
            "timestamp": "2026-06-17T12:00:00+00:00",
        },
    ]


@pytest.fixture
def sample_scores():
    return {
        "per_engine": {"chatgpt": {"mention_rate": 0.0, "citation_rate": 0.0}},
        "aggregate_mention_rate": 0.0,
        "aggregate_citation_rate": 0.0,
        "competitor_scores": {"Care.com": {"mention_rate": 1.0}},
    }


@patch("src.upload.create_client")
def test_upload_run_creates_run_and_results(mock_create, sample_results, sample_scores):
    mock_client = MagicMock()
    mock_create.return_value = mock_client

    # Mock the chained calls: .from().insert().execute()
    mock_table = MagicMock()
    mock_client.from_.return_value = mock_table
    mock_insert = MagicMock()
    mock_table.insert.return_value = mock_insert
    mock_execute = MagicMock()
    mock_insert.execute.return_value = mock_execute
    mock_execute.data = [{"id": "run-uuid-123"}]

    # Mock select for the run insert
    mock_select = MagicMock()
    mock_insert.select.return_value = mock_select
    mock_select.single.return_value = MagicMock()
    mock_select.single.return_value.execute.return_value = MagicMock(
        data={"id": "run-uuid-123"}
    )

    run_id = upload_run("client-uuid", sample_results, sample_scores)

    assert run_id == "run-uuid-123"
    assert mock_client.from_.call_count >= 2  # tracker_runs + tracker_results


@patch("src.upload.create_client")
def test_upload_run_returns_none_without_env(mock_create):
    mock_create.side_effect = Exception("No env vars")
    run_id = upload_run("client-uuid", [], {})
    assert run_id is None
```

- [ ] **Step 5: Run tests to verify they fail**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents
python -m pytest tests/test_upload.py -v
```

Expected: FAIL (module not found).

- [ ] **Step 6: Implement upload module**

Create `agents/src/upload.py`:

```python
import os
from datetime import datetime, timezone


def create_client():
    from supabase import create_client as sb_create

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")
    return sb_create(url, key)


def upload_run(
    client_id: str,
    results: list[dict],
    scores: dict,
) -> str | None:
    try:
        sb = create_client()
    except Exception as e:
        print(f"  Supabase upload skipped: {e}")
        return None

    try:
        run_row = {
            "client_id": client_id,
            "ran_at": datetime.now(timezone.utc).isoformat(),
            "aggregate_mention_rate": scores.get("aggregate_mention_rate", 0),
            "aggregate_citation_rate": scores.get("aggregate_citation_rate", 0),
            "per_engine_scores": scores.get("per_engine", {}),
            "competitor_scores": scores.get("competitor_scores", {}),
        }

        run_resp = sb.from_("tracker_runs").insert(run_row).select().single().execute()
        run_id = run_resp.data["id"]

        result_rows = []
        for r in results:
            result_rows.append({
                "run_id": run_id,
                "query": r["query"],
                "engine": r["engine"],
                "model": r.get("model", ""),
                "brand_mentioned": r.get("brand_mentioned", False),
                "brand_cited": r.get("brand_cited", False),
                "citation_url": r.get("citation_url", ""),
                "competitor_mentions": r.get("competitor_mentions", []),
                "response_text": r.get("response_text", ""),
                "queried_at": r.get("timestamp", datetime.now(timezone.utc).isoformat()),
            })

        if result_rows:
            sb.from_("tracker_results").insert(result_rows).execute()

        print(f"  Uploaded to Supabase: run {run_id} ({len(result_rows)} results)")
        return run_id

    except Exception as e:
        print(f"  Supabase upload failed: {e}")
        return None
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents
python -m pytest tests/test_upload.py -v
```

Expected: All tests PASS.

- [ ] **Step 8: Add --upload flag to run.py**

Modify `agents/run.py` to add upload functionality. Add the `--upload` argument and call `upload_run` after writing local files:

```python
import argparse
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.tracker import load_client_config, run_tracker
from src.output import write_csv, write_json, write_html, format_summary


def main():
    parser = argparse.ArgumentParser(description="GEO Tracker Agent")
    parser.add_argument("config", help="Path to client config JSON file")
    parser.add_argument(
        "--output-dir",
        default="../output",
        help="Directory for output files (default: ../output)",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload results to Supabase after run",
    )
    args = parser.parse_args()

    config = load_client_config(args.config)
    client_name = config["client_name"]

    print(f"\n  GEO Tracker — {client_name}")
    print(f"  Queries: {len(config['target_queries'])}")
    print(f"  Brand: {config['brand_name']}")
    print()

    results, scores = run_tracker(config)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%b-%d-%Y_%I-%M%p").lower()
    slug = client_name.lower().replace(" ", "_")

    csv_path = output_dir / f"{slug}_{timestamp}.csv"
    json_path = output_dir / f"{slug}_{timestamp}.json"
    html_path = output_dir / f"{slug}_{timestamp}.html"

    write_csv(results, csv_path)
    write_json(results, scores, client_name, json_path)
    write_html(results, scores, client_name, html_path)

    print(format_summary(scores, client_name))
    print(f"  HTML: {html_path}")
    print(f"  CSV:  {csv_path}")
    print(f"  JSON: {json_path}")

    if args.upload:
        supabase_client_id = config.get("supabase_client_id")
        if not supabase_client_id:
            print("\n  ⚠ No supabase_client_id in config — skipping upload")
        else:
            from src.upload import upload_run

            print()
            upload_run(supabase_client_id, results, scores)


if __name__ == "__main__":
    main()
```

- [ ] **Step 9: Add supabase_client_id to childspot.json**

Update `clients/childspot.json` to add the `supabase_client_id` field (to be filled in after creating the client in Supabase):

```json
{
  "client_name": "ChildSpot",
  "brand_name": "ChildSpot",
  "brand_variations": ["ChildSpot", "Child Spot", "childspot.ca"],
  "website_domain": "childspot.ca",
  "supabase_client_id": "",
  "target_queries": [
    "best childcare finder in Ontario",
    "how to find daycare near me Ontario",
    "childcare waitlist Ontario",
    "Ontario childcare registry",
    "find licensed daycare Ontario"
  ],
  "competitors": [
    "Wee Watch",
    "KinderPage",
    "Daycare Radar",
    "Care.com",
    "RateYourDaycare",
    "OneList Ontario",
    "HiMama"
  ]
}
```

- [ ] **Step 10: Run all tests**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents
python -m pytest tests/ -v
```

Expected: All tests PASS (detection, output, and upload tests).

- [ ] **Step 11: Commit**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
git add agents/src/upload.py agents/tests/test_upload.py agents/pyproject.toml agents/.env.example agents/run.py clients/childspot.json
git commit -m "feat: Supabase upload module with --upload flag for tracker"
```
