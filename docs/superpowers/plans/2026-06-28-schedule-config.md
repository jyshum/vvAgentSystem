# Schedule Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let admins configure per-client pipeline schedule (day of week + frequency) from the dashboard, reload the scheduler when config changes, and show the next scheduled run.

**Architecture:** The `cycle_day` (int 0-6) and `cycle_frequency` (text: weekly/biweekly/monthly) columns already exist on the `clients` table. We add them to the Client type and ConfigForm, then add a `/api/reload-schedules` endpoint on the FastAPI server so the dashboard can tell the scheduler to pick up changes. The client layout header shows the next scheduled run time.

**Tech Stack:** Next.js, Supabase, FastAPI, APScheduler

---

## File Structure

**Dashboard:**
- Modify: `dashboard/lib/types.ts` — add `cycle_day` and `cycle_frequency` to Client
- Modify: `dashboard/components/admin/ConfigForm.tsx` — add schedule UI (day dropdown + frequency dropdown)
- Modify: `dashboard/app/admin/clients/[id]/layout.tsx` — show next scheduled run under domain

**Backend:**
- Modify: `agents/server.py` — add `POST /api/reload-schedules` endpoint, refactor `load_schedules` to support frequency

---

### Task 1: Add schedule fields to Client type and ConfigForm

**Files:**
- Modify: `dashboard/lib/types.ts`
- Modify: `dashboard/components/admin/ConfigForm.tsx`

- [ ] **Step 1: Add fields to Client interface**

In `dashboard/lib/types.ts`, add after `gsc_site_url: string;`:
```typescript
  cycle_frequency: string;
  cycle_day: number;
```

- [ ] **Step 2: Add schedule state to ConfigForm**

In `dashboard/components/admin/ConfigForm.tsx`, add after the `gscSiteUrl` state line (`const [gscSiteUrl, setGscSiteUrl] = useState(client.gsc_site_url || "");`):

```typescript
  const [cycleFrequency, setCycleFrequency] = useState(client.cycle_frequency || "weekly");
  const [cycleDay, setCycleDay] = useState(client.cycle_day ?? 1);
```

- [ ] **Step 3: Add schedule fields to the save function**

In `dashboard/components/admin/ConfigForm.tsx`, add to the `supabase.from("clients").update({...})` object, after `cms_config: cmsConfig,`:

```typescript
      cycle_frequency: cycleFrequency,
      cycle_day: cycleDay,
```

- [ ] **Step 4: Add schedule UI section**

In `dashboard/components/admin/ConfigForm.tsx`, add after the GSC Property URL `</div>` block and before the `<TagInput label="Brand Variations"` line:

```tsx
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
```

- [ ] **Step 5: Commit**

```bash
git add dashboard/lib/types.ts dashboard/components/admin/ConfigForm.tsx
git commit -m "feat: add pipeline schedule config to client form"
```

---

### Task 2: Add reload-schedules endpoint to FastAPI

**Files:**
- Modify: `agents/server.py`

- [ ] **Step 1: Refactor load_schedules to support frequency**

In `agents/server.py`, replace the `load_schedules()` function (lines 53-83) with:

```python
def load_schedules():
    try:
        from supabase import create_client
        sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
        result = sb.table("clients").select("id, cycle_frequency, cycle_day").execute()

        day_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}

        # Remove all existing cycle jobs
        for job in scheduler.get_jobs():
            if job.id.startswith("cycle-"):
                scheduler.remove_job(job.id)

        offset_minutes = 0

        for client in result.data:
            client_id = client["id"]
            frequency = client.get("cycle_frequency", "weekly")
            cycle_day = day_map.get(client.get("cycle_day", 1), "tue")

            if frequency == "monthly":
                trigger = CronTrigger(day="1", hour=2, minute=offset_minutes)
            elif frequency == "biweekly":
                trigger = CronTrigger(day_of_week=cycle_day, hour=2, minute=offset_minutes, week="*/2")
            else:
                trigger = CronTrigger(day_of_week=cycle_day, hour=2, minute=offset_minutes)

            scheduler.add_job(
                trigger_scheduled_run,
                trigger=trigger,
                args=[client_id],
                id=f"cycle-{client_id}",
                replace_existing=True,
            )
            label = f"{cycle_day} 02:{offset_minutes:02d}" if frequency != "monthly" else f"1st of month 02:{offset_minutes:02d}"
            print(f"  [Scheduler] Scheduled {client_id} ({frequency}) for {label}")
            offset_minutes += 15

    except Exception as e:
        print(f"  [Scheduler] Failed to load schedules: {e}")
```

- [ ] **Step 2: Add the reload endpoint**

In `agents/server.py`, add after the `/api/status/{thread_id}` endpoint:

```python
@app.post("/api/reload-schedules")
async def reload_schedules(authorization: str | None = Header(None)):
    verify_auth(authorization)
    load_schedules()
    jobs = [{"id": j.id, "next_run": j.next_run_time.isoformat() if j.next_run_time else None} for j in scheduler.get_jobs() if j.id.startswith("cycle-")]
    return {"status": "reloaded", "jobs": jobs}
```

- [ ] **Step 3: Commit**

```bash
git add agents/server.py
git commit -m "feat: add reload-schedules endpoint and frequency support"
```

---

### Task 3: Show next scheduled run in client header and trigger reload on save

**Files:**
- Modify: `dashboard/app/admin/clients/[id]/layout.tsx`
- Modify: `dashboard/components/admin/ConfigForm.tsx`

- [ ] **Step 1: Show schedule info in client layout header**

In `dashboard/app/admin/clients/[id]/layout.tsx`, update the client select query to include schedule fields:

Change:
```typescript
    supabase
      .from("clients")
      .select("id, name, website_domain")
      .eq("id", id)
      .single(),
```

To:
```typescript
    supabase
      .from("clients")
      .select("id, name, website_domain, cycle_frequency, cycle_day")
      .eq("id", id)
      .single(),
```

Update the type cast:
```typescript
  const c = client as Pick<Client, "id" | "name" | "website_domain" | "cycle_frequency" | "cycle_day">;
```

Add a schedule label under the domain text:
```tsx
          <div
            className="font-mono text-[10px] tracking-[0.1em] mt-1.5"
            style={{ color: "var(--faint)" }}
          >
            {c.website_domain}
          </div>
          <div
            className="font-mono text-[8px] tracking-[0.06em] mt-1"
            style={{ color: "var(--faint)", opacity: 0.7 }}
          >
            {c.cycle_frequency === "monthly" ? "Monthly" : c.cycle_frequency === "biweekly" ? "Bi-weekly" : "Weekly"} · {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][c.cycle_day ?? 1]} 2:00 AM UTC
          </div>
```

- [ ] **Step 2: Trigger reload-schedules after save**

In `dashboard/components/admin/ConfigForm.tsx`, add after `setSaved(true);` (inside the `save()` function, after the successful Supabase update):

```typescript
    // Tell the agent server to reload schedules
    try {
      await fetch("/api/runs/reload-schedules", { method: "POST" });
    } catch {}
```

- [ ] **Step 3: Create the reload-schedules proxy route**

Create `dashboard/app/api/runs/reload-schedules/route.ts`:

```typescript
import { NextResponse } from "next/server";

const LANGGRAPH_API = process.env.LANGGRAPH_API_URL;
const LANGGRAPH_KEY = process.env.LANGGRAPH_API_KEY;

export async function POST() {
  if (!LANGGRAPH_API || !LANGGRAPH_KEY) {
    return NextResponse.json({ error: "Agent API not configured" }, { status: 503 });
  }

  try {
    const res = await fetch(`${LANGGRAPH_API}/api/reload-schedules`, {
      method: "POST",
      headers: { "Authorization": `Bearer ${LANGGRAPH_KEY}` },
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ error: "Could not reach agent server" }, { status: 502 });
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add dashboard/app/admin/clients/\[id\]/layout.tsx dashboard/components/admin/ConfigForm.tsx dashboard/app/api/runs/reload-schedules/route.ts
git commit -m "feat: show schedule in header, reload scheduler on config save"
```

---

## Self-Review

**Spec coverage:** Schedule UI with day + frequency, reload endpoint, schedule display in header — all covered.

**Placeholder scan:** No TBD/TODO. All code blocks complete.

**Type consistency:** `cycle_frequency: string` and `cycle_day: number` used consistently across types.ts, ConfigForm state, save object, layout query, and server.py. Day mapping uses 0=Mon through 6=Sun consistently in both frontend selects and backend `day_map`.
