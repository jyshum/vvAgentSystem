# Technical Audit Tranche 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put BudgetYourMD on one manual deterministic runtime, remove scheduling and legacy audit/card paths, reset all generated data safely, repair Foundation collection, and prove the resulting slice in development before any production baseline is created.

**Architecture:** Add the unified client fields before changing readers, then deploy a scheduler-free manual graph that writes tracker evidence and immutable technical-audit evidence only. Replace the profile-driven Foundation collector with a bounded site/platform collector, remove legacy tables and UI after a verified client-scoped reset, and validate with fixtures, a local Supabase demo run, and a non-persisting BudgetYourMD smoke run.

**Tech Stack:** Python 3.11, FastAPI, LangGraph, psycopg 3, httpx, BeautifulSoup, pytest, Next.js/React/TypeScript, Vitest, Supabase PostgreSQL, Railway.

## Global Constraints

- The approved normative rules remain in `docs/superpowers/specs/2026-07-14-deterministic-technical-audit-design.md`.
- The reset/runtime decisions remain in `docs/superpowers/specs/2026-07-15-technical-audit-reset-engine-first-design.md`.
- Runs are manual; no recurring job, inferred schedule, or automatic post-run schedule may exist.
- Preserve the BudgetYourMD client, brand inputs, competitors, GSC property, eight versioned queries, authentication users, administrator access, and credentials.
- Remove generated data, legacy matcher/scorer/card paths, and legacy fallback behavior.
- Do not create a production baseline in this tranche.
- Do not use a proprietary score, similarity result, or matcher output in technical decisions.
- Squarespace `llms.txt` absence is Not Applicable without a user-configured toggle.
- Missing descriptions on audited canonical indexable HTML pages are Review, never Fail.
- No audit result can publish or mutate a production site.
- Every network collector is bounded and records redirects, final URL, status, MIME type, retrieval time, fingerprint, truncation, and errors.
- Use TDD for every code task and commit each task independently.

---

## File Structure

### New files

- `supabase/migrations/016_unified_manual_client_config.sql` — additive platform/implementation fields and BudgetYourMD backfill.
- `supabase/migrations/017_remove_legacy_runtime.sql` — post-reset destructive schema cleanup.
- `agents/src/technical_audit/site.py` — domain identity, allowed-host, and platform applicability rules.
- `agents/src/technical_audit/collector.py` — bounded HTTP collection and page-scope construction.
- `agents/src/technical_audit/pipeline.py` — technical run persistence and community-opportunity summary without legacy cards.
- `agents/src/technical_audit/cli.py` — explicit persisted demo run and non-persisting smoke-run entry point.
- `agents/scripts/reset_client_data.py` — dry-run-first client export, transactional deletion, and verification.
- `agents/tests/test_unified_manual_config_migration.py` — migration contract.
- `agents/tests/test_reset_client_data.py` — reset selection, transaction, and preservation contract.
- `agents/tests/technical_audit/test_site.py` — host/platform rules.
- `agents/tests/technical_audit/test_collector.py` — redirects, bounds, truncation, and safe failures.
- `dashboard/__tests__/manual-client-config.test.tsx` — user-facing manual config contract.

### Modified files

- `agents/server.py` — manual run API only; no scheduler or approval resume endpoint.
- `agents/src/graph/pipeline.py` — load → tracker → GSC → technical pipeline → end.
- `agents/src/graph/nodes.py` — unified config and technical pipeline node only.
- `agents/src/graph/state.py` — visibility/technical/community state without matcher/card/implementation state.
- `agents/src/technical_audit/runner.py` — consume collected evidence and platform, not a hidden profile.
- `agents/src/technical_audit/checks/llms_txt.py` — platform-derived applicability.
- `agents/src/technical_audit/checks/metadata.py` — remove priority URL behavior.
- `agents/src/technical_audit/checks/canonical.py` — approved production host set from site identity.
- `agents/src/technical_audit/observations.py` — response provenance and bounded extraction.
- `agents/tests/test_server.py`, `agents/tests/test_pipeline.py`, `agents/tests/test_improvement_pipeline.py`, and `agents/tests/technical_audit/*` — new manual deterministic contracts.
- `agents/pyproject.toml` and `agents/requirements.txt` — remove APScheduler and legacy matcher dependency when unused.
- `dashboard/lib/types.ts` — unified client fields.
- `dashboard/components/admin/ConfigForm.tsx` — platform and implementation mode; no schedule/profile controls.
- `dashboard/app/api/admin/clients/[id]/route.ts` — unified writable fields.
- `dashboard/app/admin/clients/[id]/layout.tsx` — manual-only header.
- `dashboard/app/admin/page.tsx` and `dashboard/components/board/BoardRow.tsx` — no schedule or legacy-card queries/copy.
- `dashboard/app/admin/clients/[id]/queries/page.tsx` — visibility evidence only.
- `dashboard/app/admin/clients/[id]/runs/[runId]/page.tsx` — tracker plus technical evidence only.
- `dashboard/lib/client-tabs.ts` — remove Cards.
- `dashboard/lib/run-presentation.ts` and `dashboard/lib/improvement-types.ts` — one technical presentation.
- `supabase/schema.sql`, `PROJECT_STATE.md`, and `docs/technical-audit-operations.md` — canonical schema and current manual-only operations.

### Deleted files and surfaces

- `agents/src/technical_audit/rollout.py`
- `agents/src/improvement/matcher.py`
- `agents/src/improvement/scorer.py`
- `agents/src/improvement/gap_check.py`
- `agents/src/improvement/crawlability.py`
- `agents/src/improvement/card_generator.py`
- `agents/src/improvement/card_qa.py`
- `agents/src/improvement/auto_approve.py`
- `agents/src/improvement/verifier.py`
- `agents/src/improvement/pipeline.py` after its persistence responsibilities move
- `agents/src/implementors/`
- `agents/audit.py`, `agents/recommend.py`, `agents/implement.py`, and `agents/scout.py`
- `agents/src/auditor.py`, `agents/src/recommender.py`, `agents/src/reddit_scout.py`, `agents/src/parsers.py`, and `agents/src/scorers.py`
- legacy-only tests: `test_matcher.py`, `test_scorer.py`, `test_scorers.py`, `test_parsers.py`, `test_auditor.py`, `test_recommender.py`, `test_gap_check.py`, `test_crawlability.py`, `test_card_generator.py`, `test_card_qa.py`, `test_auto_approve.py`, `test_verifier.py`, `test_github_impl.py`, and implementation-only cases in `test_graph_nodes.py`
- `dashboard/lib/schedules.ts`
- `dashboard/app/api/runs/reload-schedules/route.ts`
- `dashboard/app/api/admin/approve/route.ts`
- `dashboard/app/admin/approvals/`
- `dashboard/app/admin/clients/[id]/cards/`
- `dashboard/app/mock-current/`
- `dashboard/components/approvals/`
- legacy Pages readers/components after their database tables are removed
- `dashboard/components/admin/HeatTable.tsx` card/waiting column and approval links
- `dashboard/components/runs/RunRail.tsx` card/approval/implementation segments
- `dashboard/components/admin/NavLinks.tsx` approval navigation entry
- `dashboard/__tests__/components/approval-cards.test.tsx` and `dashboard/__tests__/components/card-highlighter.test.tsx`

---

### Task 1: Add the unified manual client configuration additively

**Files:**
- Create: `supabase/migrations/016_unified_manual_client_config.sql`
- Create: `agents/tests/test_unified_manual_config_migration.py`
- Modify: `supabase/schema.sql`

**Interfaces:**
- Produces: `clients.site_platform text` and `clients.implementation_mode text`.
- Preserves temporarily: `cms_type`, `cms_config`, `cycle_frequency`, and `cycle_day` until the scheduler-free application is deployed.
- BudgetYourMD backfill: `site_platform='squarespace'`, `implementation_mode='copy_paste'`.

- [ ] **Step 1: Write the migration contract test**

```python
from pathlib import Path


MIGRATION = Path(__file__).parents[2] / "supabase/migrations/016_unified_manual_client_config.sql"


def test_unified_config_is_additive_and_backfills_budgetyourmd():
    sql = MIGRATION.read_text()
    assert "add column if not exists site_platform" in sql.lower()
    assert "add column if not exists implementation_mode" in sql.lower()
    assert "website_domain = 'budgetyourmd.ca'" in sql.lower()
    assert "site_platform = 'squarespace'" in sql.lower()
    assert "implementation_mode = 'copy_paste'" in sql.lower()
    assert "drop column" not in sql.lower()
```

- [ ] **Step 2: Run the test and verify it fails because migration 016 does not exist**

Run: `cd agents && .venv/bin/python -m pytest tests/test_unified_manual_config_migration.py -q`

Expected: FAIL with `FileNotFoundError` for `016_unified_manual_client_config.sql`.

- [ ] **Step 3: Create the additive migration**

```sql
alter table public.clients
  add column if not exists site_platform text not null default 'unknown'
    check (site_platform in ('unknown', 'squarespace', 'wordpress', 'webflow', 'shopify', 'repository', 'other')),
  add column if not exists implementation_mode text not null default 'copy_paste'
    check (implementation_mode in ('copy_paste', 'guided', 'github_pr', 'staged_api'));

update public.clients
set site_platform = 'squarespace',
    implementation_mode = 'copy_paste'
where lower(website_domain) = 'budgetyourmd.ca';
```

Mirror these columns and constraints in `supabase/schema.sql` without removing the transitional columns yet.

- [ ] **Step 4: Run the migration test**

Run: `cd agents && .venv/bin/python -m pytest tests/test_unified_manual_config_migration.py -q`

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/016_unified_manual_client_config.sql supabase/schema.sql agents/tests/test_unified_manual_config_migration.py
git commit -m "feat: add unified manual client config"
```

---

### Task 2: Remove application scheduling before any reset

**Files:**
- Modify: `agents/server.py`
- Modify: `agents/tests/test_server.py`
- Modify: `agents/pyproject.toml`
- Modify: `agents/requirements.txt`

**Interfaces:**
- Keeps: authenticated `POST /api/run`, `GET /api/status/{thread_id}`, and `GET /health`.
- Removes: scheduler object, scheduler lifecycle, scheduled-run function, schedule endpoints, and post-run schedule activation.

- [ ] **Step 1: Replace scheduler tests with absence tests**

```python
def test_schedule_routes_do_not_exist():
    from server import app
    client = TestClient(app)
    headers = {"Authorization": "Bearer dev-key"}
    assert client.get("/api/schedules", headers=headers).status_code == 404
    assert client.post("/api/reload-schedules", headers=headers).status_code == 404


def test_manual_run_endpoint_still_requires_auth():
    from server import app
    client = TestClient(app)
    assert client.post("/api/run", json={"client_id": "client-1"}).status_code == 401
```

Delete the two existing schedule endpoint tests.

- [ ] **Step 2: Run the tests and verify the old routes still exist**

Run: `cd agents && .venv/bin/python -m pytest tests/test_server.py -q`

Expected: FAIL because `/api/schedules` and `/api/reload-schedules` return authenticated responses instead of 404.

- [ ] **Step 3: Remove scheduler code from `agents/server.py`**

Remove the APScheduler imports, `scheduler`, `trigger_scheduled_run`, `_add_client_schedule`, `load_schedules`, scheduler lifespan calls, `/api/reload-schedules`, `/api/schedules`, and the post-run `_add_client_schedule` block. Keep the lifespan only for tracing:

```python
@asynccontextmanager
async def lifespan(app):
    if os.environ.get("LANGCHAIN_TRACING_V2") == "true":
        print(
            "  [Tracing] LangSmith enabled — project: "
            f"{os.environ.get('LANGCHAIN_PROJECT', 'default')}"
        )
    yield
```

Remove `apscheduler>=3.10.0` from both dependency files.

- [ ] **Step 4: Prove scheduler symbols and dependency are gone**

Run:

```bash
rg -n "APScheduler|BackgroundScheduler|CronTrigger|load_schedules|cycle-" agents/server.py agents/pyproject.toml agents/requirements.txt
```

Expected: no matches.

- [ ] **Step 5: Run server tests**

Run: `cd agents && .venv/bin/python -m pytest tests/test_server.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add agents/server.py agents/tests/test_server.py agents/pyproject.toml agents/requirements.txt
git commit -m "refactor: remove automatic scheduling"
```

---

### Task 3: Make the dashboard configuration manual and unified

**Files:**
- Modify: `dashboard/lib/types.ts`
- Modify: `dashboard/components/admin/ConfigForm.tsx`
- Modify: `dashboard/app/api/admin/clients/[id]/route.ts`
- Modify: `dashboard/__tests__/client-config-save.test.ts`
- Create: `dashboard/__tests__/manual-client-config.test.tsx`
- Delete: `dashboard/lib/schedules.ts`
- Delete: `dashboard/app/api/runs/reload-schedules/route.ts`

**Interfaces:**
- `Client.site_platform`: platform selector.
- `Client.implementation_mode`: delivery selector.
- PATCH accepts these two fields and rejects schedule/profile fields by omission from `UPDATABLE_FIELDS`.

- [ ] **Step 1: Write failing API and form tests**

Add to `client-config-save.test.ts`:

```typescript
it("writes platform and implementation mode but ignores schedule fields", async () => {
  const res = await callPatch({
    site_platform: "squarespace",
    implementation_mode: "copy_paste",
    cycle_frequency: "weekly",
    cycle_day: 1,
  });
  expect(res.status).toBe(200);
  expect(clientsUpdate).toHaveBeenCalledWith({
    site_platform: "squarespace",
    implementation_mode: "copy_paste",
  });
});
```

Create `manual-client-config.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { ConfigForm } from "@/components/admin/ConfigForm";

it("shows site platform and no scheduler controls", () => {
  render(<ConfigForm client={{
    id: "c1", name: "Christian", brand_name: "BudgetYourMD",
    website_domain: "budgetyourmd.ca", brand_variations: [], target_queries: [],
    competitors: [], gsc_site_url: "https://www.budgetyourmd.ca/",
    site_platform: "squarespace", implementation_mode: "copy_paste",
    created_at: "2026-07-15T00:00:00Z",
  }} />);
  expect(screen.getByLabelText("Site platform")).toHaveValue("squarespace");
  expect(screen.queryByText("Pipeline Schedule")).toBeNull();
  expect(screen.queryByText("Frequency")).toBeNull();
});
```

- [ ] **Step 2: Run the tests and verify they fail on the old contract**

Run: `cd dashboard && npm test -- __tests__/client-config-save.test.ts __tests__/manual-client-config.test.tsx`

Expected: FAIL because the new fields are absent and schedule controls still render.

- [ ] **Step 3: Update the client type and PATCH allowlist**

Replace the legacy config fields in `Client` with:

```typescript
site_platform: "unknown" | "squarespace" | "wordpress" | "webflow" | "shopify" | "repository" | "other";
implementation_mode: "copy_paste" | "guided" | "github_pr" | "staged_api";
gsc_site_url: string;
```

The API allowlist becomes:

```typescript
const UPDATABLE_FIELDS = [
  "name", "brand_name", "website_domain", "brand_variations", "competitors",
  "gsc_site_url", "site_platform", "implementation_mode",
] as const;
```

- [ ] **Step 4: Replace the schedule/CMS sections in `ConfigForm`**

Use labelled selects so the test and browser accessibility contract are stable:

```tsx
<label htmlFor="site-platform">Site platform</label>
<select id="site-platform" value={sitePlatform} onChange={(event) => setSitePlatform(event.target.value)}>
  <option value="squarespace">Squarespace</option>
  <option value="wordpress">WordPress</option>
  <option value="webflow">Webflow</option>
  <option value="shopify">Shopify</option>
  <option value="repository">Repository-managed</option>
  <option value="other">Other</option>
</select>

<label htmlFor="implementation-mode">Implementation mode</label>
<select id="implementation-mode" value={implementationMode} onChange={(event) => setImplementationMode(event.target.value)}>
  <option value="copy_paste">Copy and paste</option>
  <option value="guided">Guided instructions</option>
  <option value="github_pr">GitHub pull request</option>
  <option value="staged_api">Staged API</option>
</select>
```

The save body includes `site_platform` and `implementation_mode` and makes no reload-schedules request.

- [ ] **Step 5: Delete schedule helpers and run tests**

```bash
git rm dashboard/lib/schedules.ts dashboard/app/api/runs/reload-schedules/route.ts
cd dashboard
npm test -- __tests__/client-config-save.test.ts __tests__/manual-client-config.test.tsx
```

Expected: both test files pass.

- [ ] **Step 6: Commit**

```bash
git add dashboard/lib/types.ts dashboard/components/admin/ConfigForm.tsx dashboard/app/api/admin/clients/'[id]'/route.ts dashboard/__tests__
git commit -m "feat: unify manual client configuration"
```

---

### Task 4: Replace the approval graph with one manual evidence graph

**Files:**
- Modify: `agents/src/graph/pipeline.py`
- Modify: `agents/src/graph/nodes.py`
- Modify: `agents/src/graph/state.py`
- Modify: `agents/server.py`
- Modify: `agents/tests/test_pipeline.py`
- Modify: `agents/tests/test_server.py`
- Create: `agents/src/technical_audit/pipeline.py`
- Delete: `agents/src/improvement/pipeline.py`

**Interfaces:**
- Graph sequence: `load_config → run_tracker → run_gsc → run_technical_pipeline → END`.
- `run_type='tracker_only'` still ends after GSC.
- `run_type='full'` and `run_type='technical_only'` run technical evidence; `technical_only` skips tracker/GSC.
- `run_technical_pipeline(state, queries, competitive_gaps) -> dict` returns technical IDs/summary/results, community opportunities, and errors; it never returns action cards.

- [ ] **Step 1: Replace graph topology tests**

```python
def test_build_graph_has_only_manual_evidence_nodes():
    graph = build_graph()
    nodes = set(graph.get_graph().nodes)
    assert {"load_config", "run_tracker", "run_gsc", "run_technical_pipeline"} <= nodes
    assert "await_approval" not in nodes
    assert "run_implementation" not in nodes


def test_full_run_ends_after_technical_pipeline():
    from langgraph.graph import END
    from src.graph.pipeline import route_after_gsc
    assert route_after_gsc({"run_type": "full"}) == "run_technical_pipeline"
    assert route_after_gsc({"run_type": "tracker_only"}) == END
```

Add a server test asserting authenticated `POST /api/approve` returns 404.

- [ ] **Step 2: Run the tests and verify the old approval nodes fail the contract**

Run: `cd agents && .venv/bin/python -m pytest tests/test_pipeline.py tests/test_server.py -q`

Expected: FAIL because approval/implementation nodes and `/api/approve` still exist.

- [ ] **Step 3: Replace `GEOState` with evidence-only state**

```python
class GEOState(TypedDict):
    client_id: str
    client_config: dict
    tracker_results: list[dict]
    tracker_scores: dict
    gsc_metrics: dict
    competitive_gaps: list[dict]
    run_type: str
    thread_id: str
    improvement_run_id: str | None
    technical_audit_run_id: str | None
    technical_audit_summary: dict
    technical_audit_results: list[dict]
    technical_audit_error: str | None
    community_opportunities: list[dict]
    error: str | None
```

- [ ] **Step 4: Replace graph construction**

```python
def build_graph(checkpointer=None):
    graph = StateGraph(GEOState)
    graph.add_node("load_config", load_config)
    graph.add_node("run_tracker", run_tracker_node)
    graph.add_node("run_gsc", run_gsc_node)
    graph.add_node("run_technical_pipeline", run_technical_pipeline_node)
    graph.set_entry_point("load_config")
    graph.add_conditional_edges("load_config", route_after_config, {
        "run_tracker": "run_tracker",
        "run_technical_pipeline": "run_technical_pipeline",
    })
    graph.add_edge("run_tracker", "run_gsc")
    graph.add_conditional_edges("run_gsc", route_after_gsc, {
        END: END,
        "run_technical_pipeline": "run_technical_pipeline",
    })
    graph.add_edge("run_technical_pipeline", END)
    return graph.compile(checkpointer=checkpointer or MemorySaver())
```

`route_after_config` sends `technical_only` to `run_technical_pipeline`; all other types go to tracker. Remove `await_approval`, `run_implementation_node`, `ApproveRequest`, `/api/approve`, and every `Command` import.

- [ ] **Step 5: Move deterministic persistence into `technical_audit/pipeline.py`**

Move `_run_and_persist_technical_audit` out of the legacy improvement module. The public function starts one `improvement_runs` row, executes `run_technical_audit`, persists observations/results, selects community opportunities directly, and returns:

```python
return {
    "improvement_run_id": improvement_run_id,
    "technical_audit_run_id": audit_run_id,
    "technical_audit_summary": report["summary"],
    "technical_audit_results": report["results"],
    "technical_audit_error": None,
    "community_opportunities": [item.to_gap_dict() for item in selection.opportunities],
}
```

It must not import matcher, scorer, crawlability, card generation, QA, auto-approval, validators, or implementors.

- [ ] **Step 6: Delete the legacy improvement pipeline and run tests**

```bash
git rm agents/src/improvement/pipeline.py
cd agents
.venv/bin/python -m pytest tests/test_pipeline.py tests/test_server.py tests/test_improvement_pipeline.py -q
```

Update `test_improvement_pipeline.py` imports and fixtures to test `src.technical_audit.pipeline`; remove matcher/scorer/card assertions. Expected: all selected tests pass.

- [ ] **Step 7: Commit**

```bash
git add agents/server.py agents/src/graph agents/src/technical_audit/pipeline.py agents/tests
git commit -m "refactor: use one manual evidence graph"
```

---

### Task 5: Remove legacy code and frontend readers

**Files:**
- Delete the legacy agent/dashboard files listed in File Structure.
- Modify: `dashboard/lib/client-tabs.ts`
- Modify: `dashboard/app/admin/page.tsx`
- Modify: `dashboard/components/board/BoardRow.tsx`
- Modify: `dashboard/app/admin/clients/[id]/layout.tsx`
- Modify: `dashboard/app/admin/clients/[id]/queries/page.tsx`
- Modify: `dashboard/app/admin/clients/[id]/runs/[runId]/page.tsx`
- Modify: `dashboard/lib/run-presentation.ts`
- Modify: `dashboard/lib/improvement-types.ts`
- Modify: dashboard tests that assert legacy/scheduled/card behavior.

**Interfaces:**
- Primary navigation: Overview, Queries, Runs, Config, Reports.
- Run detail: visibility evidence, technical audit evidence, and measured community-opportunity count only.
- Board first-run copy: `first manual run pending`.

- [ ] **Step 1: Write failing navigation and copy tests**

Update `dashboard/__tests__/client-tabs.test.ts`:

```typescript
expect(clientTabs("c1").map((tab) => tab.label)).toEqual([
  "OVERVIEW", "QUERIES", "RUNS", "CONFIG", "REPORTS",
]);
```

Update the BoardRow component test to assert `first manual run pending` and reject `scheduled`.

- [ ] **Step 2: Run the focused tests and verify old surfaces remain**

Run: `cd dashboard && npm test -- __tests__/client-tabs.test.ts __tests__/components/smoke.test.tsx __tests__/run-presentation.test.ts`

Expected: FAIL on Cards/schedule/legacy presentation assertions.

- [ ] **Step 3: Remove legacy agent modules**

```bash
git rm agents/src/improvement/matcher.py agents/src/improvement/scorer.py agents/src/improvement/gap_check.py agents/src/improvement/crawlability.py agents/src/improvement/card_generator.py agents/src/improvement/card_qa.py agents/src/improvement/auto_approve.py agents/src/improvement/verifier.py
git rm -r agents/src/implementors
git rm agents/audit.py agents/recommend.py agents/implement.py agents/scout.py
git rm agents/src/auditor.py agents/src/recommender.py agents/src/reddit_scout.py agents/src/parsers.py agents/src/scorers.py
git rm agents/tests/test_matcher.py agents/tests/test_scorer.py agents/tests/test_scorers.py agents/tests/test_parsers.py agents/tests/test_auditor.py agents/tests/test_recommender.py agents/tests/test_gap_check.py agents/tests/test_crawlability.py agents/tests/test_card_generator.py agents/tests/test_card_qa.py agents/tests/test_auto_approve.py agents/tests/test_verifier.py agents/tests/test_github_impl.py
```

Delete implementation-only cases from `agents/tests/test_graph_nodes.py`. Rewrite `agents/tests/test_community_check.py` to import and assert `select_community_opportunities` directly; it must not build an action card. Remove `sentence-transformers>=3.0.0` from `agents/pyproject.toml`; no remaining runtime imports it. Run `rg -n "matcher|structural_score|citation-readiness|await_approval|run_implementation|auto_approve" agents/src agents/server.py` and delete every remaining active-runtime reference. Expected afterward: no matches outside comments describing prohibited behavior.

- [ ] **Step 4: Remove legacy dashboard routes/components**

```bash
git rm -r dashboard/app/admin/approvals dashboard/app/admin/clients/'[id]'/cards dashboard/components/approvals
git rm -r dashboard/app/admin/clients/'[id]'/pages dashboard/components/pages-tab
git rm -r dashboard/app/mock-current
git rm dashboard/app/api/admin/approve/route.ts
git rm dashboard/__tests__/components/approval-cards.test.tsx dashboard/__tests__/components/card-highlighter.test.tsx
```

Delete the hidden Pages route and `dashboard/components/pages-tab/` because migration 017 removes its storage. Remove the APPROVALS entry from `NavLinks`; remove card/waiting cells and links from `HeatTable`; replace `RunRail` segments with `MEASURE`, `COLLECT`, `AUDIT`, `COMPLETE`. Remove action-card and schedule queries from Board, Queries, client layout, runs list, and run detail. Remove legacy matching/readiness/crawlability tiles and the legacy/technical presentation branch. Keep `TechnicalAuditChecklist` as the only technical evidence component.

- [ ] **Step 5: Remove Cards navigation and use manual copy**

`clientTabs` returns only the five approved tabs. `BoardRow` renders:

```tsx
<div className="font-serif italic text-[13px]" style={{ color: "var(--mute)" }}>
  first manual run pending
</div>
```

- [ ] **Step 6: Run static reference checks and dashboard tests**

Run:

```bash
rg -n "from\(\"action_cards\"\)|fetchSchedules|next scheduled|legacy readiness|query_page_matches|page_citation_scores|/admin/approvals" dashboard --glob '!node_modules'
cd dashboard
npm test
npm run build
```

Expected: the reference scan has no active-code matches; all tests and the production build pass.

- [ ] **Step 7: Commit**

```bash
git add agents dashboard
git commit -m "refactor: remove legacy audit and card surfaces"
```

---

### Task 6: Repair Foundation collection and remove the hidden profile

**Files:**
- Create: `agents/src/technical_audit/site.py`
- Create: `agents/src/technical_audit/collector.py`
- Create: `agents/tests/technical_audit/test_site.py`
- Create: `agents/tests/technical_audit/test_collector.py`
- Modify: `agents/src/technical_audit/runner.py`
- Modify: `agents/src/technical_audit/observations.py`
- Modify: `agents/src/technical_audit/checks/llms_txt.py`
- Modify: `agents/src/technical_audit/checks/metadata.py`
- Modify: `agents/src/technical_audit/checks/canonical.py`
- Modify: `agents/tests/technical_audit/test_runner.py`
- Modify: `agents/tests/technical_audit/test_checks.py`
- Delete: `agents/src/technical_audit/rollout.py`
- Delete: `agents/tests/technical_audit/test_rollout.py`

**Interfaces:**
- `SiteIdentity.from_domain(domain, platform) -> SiteIdentity`.
- `collect_foundation(identity, max_pages=20, fetcher=None) -> CollectedSite`.
- `run_technical_audit(client_id, identity, collected, enabled_check_sets=('foundation',)) -> dict`.

`CollectedSite` is defined in `collector.py` as:

```python
@dataclass(frozen=True)
class CollectedSite:
    identity: SiteIdentity
    homepage: HttpEvidence
    pages: tuple[HttpEvidence, ...]
    llms_txt: HttpEvidence
    scope: dict[str, Any]
```

- [ ] **Step 1: Write redirect/host/platform tests**

```python
def test_bare_and_www_hosts_are_same_site():
    identity = SiteIdentity.from_domain("budgetyourmd.ca", "squarespace")
    identity = identity.with_final_homepage("https://www.budgetyourmd.ca/")
    assert identity.allows("https://budgetyourmd.ca/")
    assert identity.allows("https://www.budgetyourmd.ca/")


def test_squarespace_missing_llms_txt_is_not_applicable():
    context = foundation_context(platform="squarespace", llms_status=404, llms_body="")
    assert status(context, "llms_txt.integrity") == "not_applicable"


def test_missing_description_on_any_audited_indexable_page_is_review():
    context = foundation_context(description=[])
    assert status(context, "meta_description.integrity") == "review"
```

- [ ] **Step 2: Write bounded collector tests**

Use a fake fetcher whose bare homepage returns a 301 to `www`, whose `www` homepage returns HTML plus sitemap/nav links, and whose 21st page would exceed the cap. Assert:

```python
assert collected.homepage.final_url == "https://www.budgetyourmd.ca/"
assert len(collected.pages) <= 20
assert collected.pages[0].redirect_chain == (
    "https://budgetyourmd.ca/", "https://www.budgetyourmd.ca/",
)
assert collected.scope["truncated"] is True
```

- [ ] **Step 3: Run the new tests and verify imports fail**

Run: `cd agents && .venv/bin/python -m pytest tests/technical_audit/test_site.py tests/technical_audit/test_collector.py -q`

Expected: FAIL because `site.py` and `collector.py` do not exist.

- [ ] **Step 4: Implement `SiteIdentity`**

```python
@dataclass(frozen=True)
class SiteIdentity:
    configured_domain: str
    platform: str
    allowed_hosts: frozenset[str]

    @classmethod
    def from_domain(cls, domain: str, platform: str) -> "SiteIdentity":
        host = domain.strip().lower().removeprefix("https://").removeprefix("http://").strip("/")
        bare = host.removeprefix("www.")
        return cls(host, platform, frozenset({bare, f"www.{bare}"}))

    def with_final_homepage(self, url: str) -> "SiteIdentity":
        host = (urlsplit(url).hostname or "").lower()
        return replace(self, allowed_hosts=frozenset({*self.allowed_hosts, host}))

    def allows(self, url: str) -> bool:
        parts = urlsplit(url)
        return parts.scheme == "https" and (parts.hostname or "").lower() in self.allowed_hosts
```

- [ ] **Step 5: Implement bounded collection**

The collector uses `httpx.Client(follow_redirects=True, timeout=10)` with a 512,000-byte body cap, at most five redirects, same-site HTTPS validation on every hop, and at most 20 HTML pages. It returns immutable page/site observations with redirect history and scope. A blocked page remains an unavailable observation rather than being skipped.

The fetch result contract is:

```python
@dataclass(frozen=True)
class HttpEvidence:
    request_url: str
    final_url: str
    redirect_chain: tuple[str, ...]
    status_code: int
    content_type: str
    body: str
    body_truncated: bool
    error: str | None
```

- [ ] **Step 6: Remove profile-driven rules**

`AuditContext` receives `site_identity` instead of `profile`. `llms.txt` uses `context.site_identity.platform`; absent content is Not Applicable, present content is checked. Meta description no longer reads `priority_urls`. Canonical uses `site_identity.allowed_hosts`.

Remove `client_site_profiles` lookup from the persistence pipeline. Load `site_platform` and `implementation_mode` from `clients` in `load_config`.

- [ ] **Step 7: Remove rollout flags and run Foundation tests**

```bash
git rm agents/src/technical_audit/rollout.py agents/tests/technical_audit/test_rollout.py
cd agents
.venv/bin/python -m pytest tests/technical_audit tests/test_improvement_pipeline.py -q
```

Expected: all selected tests pass, including the bare-domain/`www` case.

- [ ] **Step 8: Commit**

```bash
git add agents/src/technical_audit agents/src/graph/nodes.py agents/tests
git commit -m "fix: collect trustworthy Foundation evidence"
```

---

### Task 7: Build the dry-run-first transactional reset utility

**Files:**
- Create: `agents/scripts/reset_client_data.py`
- Create: `agents/tests/test_reset_client_data.py`
- Modify: `.gitignore`

**Interfaces:**
- Required environment: `SUPABASE_DB_URL`.
- Required arguments: `--client-id`, `--backup-dir`.
- Mutation gate: `--execute --confirm-client-id` must exactly match `--client-id`.
- Output: `manifest.json`, one JSON file per preserved/generated table, and a final verification report.

- [ ] **Step 1: Write safety tests**

```python
def test_execute_requires_matching_confirmation(tmp_path):
    with pytest.raises(SystemExit, match="confirmation"):
        parse_args([
            "--client-id", "03cfae03-7d1d-484f-94aa-f1e576ed299a",
            "--backup-dir", str(tmp_path), "--execute",
            "--confirm-client-id", "wrong",
        ])


def test_delete_order_is_foreign_key_safe():
    assert DELETE_ORDER == (
        "technical_audit_runs", "improvement_runs", "reports",
        "tracker_runs", "pipeline_runs",
    )


def test_preserved_tables_are_never_deleted():
    sql = "\n".join(DELETE_SQL.values()).lower()
    assert "delete from public.clients" not in sql
    assert "delete from public.queries" not in sql
    assert "delete from public.client_users" not in sql
```

- [ ] **Step 2: Run tests and verify the reset module is missing**

Run: `cd agents && .venv/bin/python -m pytest tests/test_reset_client_data.py -q`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement exact deletion ownership**

```python
DELETE_ORDER = (
    "technical_audit_runs", "improvement_runs", "reports",
    "tracker_runs", "pipeline_runs",
)

DELETE_SQL = {
    "technical_audit_runs": "delete from public.technical_audit_runs where client_id = %(client_id)s",
    "improvement_runs": "delete from public.improvement_runs where client_id = %(client_id)s",
    "reports": "delete from public.reports where client_id = %(client_id)s",
    "tracker_runs": "delete from public.tracker_runs where client_id = %(client_id)s",
    "pipeline_runs": "delete from public.pipeline_runs where client_id = %(client_id)s",
}
```

The backup queries include direct tables plus child joins for tracker results, prompt scores, competitive gaps, technical observations/results, page inventory, matches, readiness scores, and action cards. Serialize UUIDs and timestamps with `json.dumps(..., default=str)`.

- [ ] **Step 4: Implement transaction and preservation verification**

Before deletion, capture canonical JSON for `clients`, `queries`, `client_users`, and matching `auth.users`. Within one psycopg transaction, execute the five parent deletions, query every generated-table count, compare preserved rows byte-for-byte, and raise before commit on any mismatch. Dry-run performs the same exports/counts without opening a write transaction.

Add `.artifacts/client-resets/` to `.gitignore`.

- [ ] **Step 5: Run reset tests**

Run: `cd agents && .venv/bin/python -m pytest tests/test_reset_client_data.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add .gitignore agents/scripts/reset_client_data.py agents/tests/test_reset_client_data.py
git commit -m "feat: add verified client reset utility"
```

---

### Task 8: Add the post-reset schema cleanup

**Files:**
- Create: `supabase/migrations/017_remove_legacy_runtime.sql`
- Modify: `agents/tests/test_unified_manual_config_migration.py`
- Modify: `supabase/schema.sql`

**Interfaces:**
- Drops legacy generated tables after reset: `action_cards`, `page_citation_scores`, `query_page_matches`, `page_inventory`, `client_site_profiles`.
- Removes client schedule/legacy implementation fields.
- Simplifies `pipeline_runs.status` to `running|completed|error`.
- Simplifies `improvement_runs` to technical/community execution metadata.

- [ ] **Step 1: Write the cleanup migration contract**

```python
def test_cleanup_drops_only_approved_legacy_contracts():
    sql = (Path(__file__).parents[2] / "supabase/migrations/017_remove_legacy_runtime.sql").read_text().lower()
    for table in ("action_cards", "page_citation_scores", "query_page_matches", "page_inventory", "client_site_profiles"):
        assert f"drop table if exists public.{table}" in sql
    for column in ("cycle_frequency", "cycle_day", "cms_type", "cms_config", "auto_approve_action_types"):
        assert f"drop column if exists {column}" in sql
    assert "drop table public.tracker_runs" not in sql
    assert "drop table public.queries" not in sql
    assert "drop table public.technical_audit_runs" not in sql
```

- [ ] **Step 2: Run the migration test and verify migration 017 is missing**

Run: `cd agents && .venv/bin/python -m pytest tests/test_unified_manual_config_migration.py -q`

Expected: FAIL with `FileNotFoundError`.

- [ ] **Step 3: Create migration 017**

```sql
drop table if exists public.action_cards cascade;
drop table if exists public.page_citation_scores cascade;
drop table if exists public.query_page_matches cascade;
drop table if exists public.page_inventory cascade;
drop table if exists public.client_site_profiles cascade;

drop trigger if exists improvement_runs_route_controls_immutable on public.improvement_runs;
drop function if exists public.prevent_improvement_run_route_mutation();

alter table public.clients
  drop column if exists cycle_frequency,
  drop column if exists cycle_day,
  drop column if exists cms_type,
  drop column if exists cms_config,
  drop column if exists auto_approve_action_types;

alter table public.improvement_runs
  drop column if exists crawlability_report,
  drop column if exists pages_inventoried,
  drop column if exists queries_matched,
  drop column if exists content_gaps_found,
  drop column if exists cards_generated,
  drop column if exists run_mode,
  drop column if exists effective_check_sets;

alter table public.pipeline_runs drop constraint if exists pipeline_runs_status_check;
alter table public.pipeline_runs
  add constraint pipeline_runs_status_check check (status in ('running', 'completed', 'error'));
```

Mirror the final schema in `supabase/schema.sql`.

- [ ] **Step 4: Run migration tests and schema reference scans**

Run:

```bash
cd agents
.venv/bin/python -m pytest tests/test_unified_manual_config_migration.py tests/test_improvement_run_migration.py -q
cd ..
rg -n "client_site_profiles|action_cards|query_page_matches|page_citation_scores|cycle_frequency|cycle_day" agents dashboard --glob '!node_modules'
```

Expected: migration tests pass; active-code reference scan is empty.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/017_remove_legacy_runtime.sql supabase/schema.sql agents/tests
git commit -m "refactor: remove legacy runtime schema"
```

---

### Task 9: Add an explicit audit CLI for smoke and demo validation

**Files:**
- Create: `agents/src/technical_audit/cli.py`
- Create: `agents/tests/technical_audit/test_cli.py`
- Modify: `agents/pyproject.toml`

**Interfaces:**
- Non-persisting: `python -m src.technical_audit.cli smoke --domain budgetyourmd.ca --platform squarespace --output PATH`.
- Persisting demo: `python -m src.technical_audit.cli run --client-id UUID`.
- The smoke command never initializes Supabase and writes bounded JSON only to the requested local artifact path.

- [ ] **Step 1: Write CLI isolation tests**

```python
def test_smoke_does_not_request_database(monkeypatch, tmp_path):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    output = tmp_path / "smoke.json"
    def fetcher(url):
        return HttpEvidence(
            request_url=url, final_url=url, redirect_chain=(url,), status_code=404,
            content_type="text/plain", body="", body_truncated=False, error=None,
        )
    result = main(["smoke", "--domain", "example.com", "--platform", "other", "--output", str(output)], fetcher=fetcher)
    assert result == 0
    assert output.exists()
    assert json.loads(output.read_text())["summary"]["total"] >= 4
```

- [ ] **Step 2: Run the test and verify the CLI module is missing**

Run: `cd agents && .venv/bin/python -m pytest tests/technical_audit/test_cli.py -q`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `smoke` and `run` subcommands**

`smoke` constructs `SiteIdentity`, collects Foundation evidence, runs the registry, redacts/bounds artifacts, and writes JSON. `run` loads the client through Supabase and calls `run_technical_pipeline` with persistence. Both return nonzero when collection produces a run Error; check-level Unknown remains a valid report.

- [ ] **Step 4: Run CLI tests**

Run: `cd agents && .venv/bin/python -m pytest tests/technical_audit/test_cli.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add agents/src/technical_audit/cli.py agents/tests/technical_audit/test_cli.py agents/pyproject.toml
git commit -m "feat: add explicit technical audit CLI"
```

---

### Task 10: Verify code, deploy manual runtime, and replace Railway checkpoints

**Files:**
- Modify after verification: `PROJECT_STATE.md`
- Modify after verification: `docs/technical-audit-operations.md`

**Interfaces:**
- Railway project: current linked `vv-geo-production` project, `production` environment.
- Application service remains available; in-process scheduling is absent.
- New database service name: `checkpoints-v2`.

- [ ] **Step 1: Run complete local verification before deployment**

```bash
cd agents
.venv/bin/python -m pytest -q
cd ../dashboard
npm test
npm run build
```

Expected: every command exits 0.

- [ ] **Step 2: Apply additive migration 016 only**

```bash
test -n "$SUPABASE_DB_URL"
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f supabase/migrations/016_unified_manual_client_config.sql
```

Verify:

```sql
select website_domain, site_platform, implementation_mode
from public.clients
where id = '03cfae03-7d1d-484f-94aa-f1e576ed299a';
```

Expected row: `budgetyourmd.ca | squarespace | copy_paste`.

- [ ] **Step 3: Provision and wire a fresh Railway checkpoint store**

```bash
RAILWAY_CALLER=skill:use-railway@1.3.5 railway add --database postgres --json
```

Rename the returned service to `checkpoints-v2`, then set the agent service `DATABASE_URL` to `${{checkpoints-v2.DATABASE_URL}}` using a Railway reference variable. Do not expose either URL in logs.

- [ ] **Step 4: Deploy the scheduler-free agent and verify terminal success**

```bash
RAILWAY_CALLER=skill:use-railway@1.3.5 railway up --detach -m "Deploy manual deterministic runtime"
RAILWAY_CALLER=skill:use-railway@1.3.5 railway deployment list --json
```

Poll until the newest application deployment is `SUCCESS`. A queued deployment is not success.

- [ ] **Step 5: Verify no recurrence remains**

```bash
RAILWAY_CALLER=skill:use-railway@1.3.5 railway environment config --json
RAILWAY_CALLER=skill:use-railway@1.3.5 railway logs --service vv-tracker --lines 200 --json
```

Expected: `cronSchedule` is null, logs contain no `[Scheduler]`, the health endpoint returns 200, and authenticated `/api/schedules` returns 404.

- [ ] **Step 6: Update operations documentation and commit**

Document that migrations 014–016 are applied, runs are manual, scheduling is removed, production baseline remains absent, and reset/017 are the next gate.

```bash
git add PROJECT_STATE.md docs/technical-audit-operations.md
git commit -m "docs: mark runtime manual before reset"
```

---

### Task 11: Execute and verify the BudgetYourMD reset, then apply cleanup migration 017

**Files:**
- Runtime artifact only: `.artifacts/client-resets/budgetyourmd-2026-07-15/`

**Interfaces:**
- Client ID: `03cfae03-7d1d-484f-94aa-f1e576ed299a`.
- The reset script is dry-run-first and uses one Supabase transaction for deletion.
- Production baseline remains absent after this task.

- [ ] **Step 1: Capture dry-run export and counts**

```bash
cd agents
test -n "$SUPABASE_DB_URL"
.venv/bin/python scripts/reset_client_data.py \
  --client-id 03cfae03-7d1d-484f-94aa-f1e576ed299a \
  --backup-dir ../.artifacts/client-resets/budgetyourmd-2026-07-15
```

Expected: exit 0, manifest lists the preserved client/eight queries/access, and generated row counts are nonzero only in known generated tables.

- [ ] **Step 2: Review the manifest mechanically**

```bash
jq '{client: .preserved.clients, query_count: (.preserved.queries | length), generated_counts: .generated_counts}' ../.artifacts/client-resets/budgetyourmd-2026-07-15/manifest.json
```

Expected: one BudgetYourMD client, eight queries, and no credentials or secret values in the manifest.

- [ ] **Step 3: Execute the transactional reset**

```bash
.venv/bin/python scripts/reset_client_data.py \
  --client-id 03cfae03-7d1d-484f-94aa-f1e576ed299a \
  --backup-dir ../.artifacts/client-resets/budgetyourmd-2026-07-15 \
  --execute \
  --confirm-client-id 03cfae03-7d1d-484f-94aa-f1e576ed299a
```

Expected: exit 0; post-delete generated counts are zero; preserved-row fingerprints equal the dry-run manifest.

- [ ] **Step 4: Apply migration 017 after the successful reset**

```bash
cd ..
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f supabase/migrations/017_remove_legacy_runtime.sql
```

Expected: exit 0.

- [ ] **Step 5: Verify final production configuration and emptiness**

Run read-only SQL proving:

```sql
select count(*) from public.clients where id = '03cfae03-7d1d-484f-94aa-f1e576ed299a';
select count(*) from public.queries where client_id = '03cfae03-7d1d-484f-94aa-f1e576ed299a';
select count(*) from public.tracker_runs where client_id = '03cfae03-7d1d-484f-94aa-f1e576ed299a';
select count(*) from public.pipeline_runs where client_id = '03cfae03-7d1d-484f-94aa-f1e576ed299a';
select count(*) from public.improvement_runs where client_id = '03cfae03-7d1d-484f-94aa-f1e576ed299a';
select count(*) from public.technical_audit_runs where client_id = '03cfae03-7d1d-484f-94aa-f1e576ed299a';
```

Expected counts: `1, 8, 0, 0, 0, 0`.

- [ ] **Step 6: Delete the old Railway checkpoint service**

First verify `checkpoints-v2` accepted a test checkpoint through the deployed agent. Then resolve the old Postgres service ID from `railway service list --json`, confirm it is not referenced by any variable, and delete that service. Read back service/variable configuration and confirm only `checkpoints-v2` supplies `DATABASE_URL`.

- [ ] **Step 7: Record reset completion without committing artifacts**

Update `PROJECT_STATE.md` and `docs/technical-audit-operations.md` with reset verification counts and the statement that no production baseline exists. Do not add `.artifacts/`.

```bash
git add PROJECT_STATE.md docs/technical-audit-operations.md
git commit -m "docs: record verified BudgetYourMD reset"
```

---

### Task 12: Validate Foundation with a development database and non-persisting live smoke run

**Files:**
- Modify: `PROJECT_STATE.md`
- Modify: `docs/technical-audit-operations.md`
- Runtime artifacts only: `.artifacts/technical-audit/`

**Interfaces:**
- Development persistence uses local Supabase, never production.
- BudgetYourMD smoke uses the public website but writes no database rows.
- Promotion gate produces evidence for the next Protocol plan; it does not create a production baseline.

- [ ] **Step 1: Start and migrate local Supabase**

```bash
supabase start
supabase db reset
```

Expected: local services healthy and migrations 001–017 applied.

- [ ] **Step 2: Seed a demo client and deterministic queries**

Insert one `example.com` client with `site_platform='other'`, `implementation_mode='copy_paste'`, plus one active consideration query. Use fixed IDs so persistence assertions are repeatable:

```bash
LOCAL_DB_URL=$(supabase status -o json | jq -r '.DB_URL')
psql "$LOCAL_DB_URL" -v ON_ERROR_STOP=1 <<'SQL'
insert into public.clients (
  id, name, brand_name, website_domain, brand_variations, target_queries,
  competitors, gsc_site_url, site_platform, implementation_mode
) values (
  '11111111-1111-1111-1111-111111111111',
  'Demo', 'Example', 'example.com', '[]'::jsonb, '[]'::jsonb,
  '[]'::jsonb, '', 'other', 'copy_paste'
);

insert into public.queries (
  id, client_id, prompt_text, paraphrases, slug, bucket, set_type, status, version
) values (
  '22222222-2222-2222-2222-222222222222',
  '11111111-1111-1111-1111-111111111111',
  'example query', '["example paraphrase"]'::jsonb,
  'example_query_v1', 'consideration', 'core', 'active', 1
);
SQL
```

- [ ] **Step 3: Run the full targeted automated suite**

```bash
cd agents
.venv/bin/python -m pytest tests/technical_audit tests/test_pipeline.py tests/test_server.py tests/test_reset_client_data.py -q
cd ../dashboard
npm test -- __tests__/components/technical-audit-checklist.test.tsx __tests__/components/run-technical-audit-evidence.test.tsx __tests__/run-presentation.test.ts __tests__/manual-client-config.test.tsx
npm run build
```

Expected: all commands exit 0.

- [ ] **Step 4: Run a persisted demo audit against the local database**

Point `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` to local Supabase and run:

```bash
cd ../agents
.venv/bin/python -m src.technical_audit.cli run --client-id 11111111-1111-1111-1111-111111111111
```

Expected: one completed technical audit, bounded observations, Foundation results, and no matcher/readiness/card tables in the schema.

- [ ] **Step 5: Run the non-persisting BudgetYourMD smoke audit**

```bash
mkdir -p ../.artifacts/technical-audit
.venv/bin/python -m src.technical_audit.cli smoke \
  --domain budgetyourmd.ca \
  --platform squarespace \
  --output ../.artifacts/technical-audit/budgetyourmd-foundation-smoke.json
```

Expected:

- the homepage resolves from `budgetyourmd.ca` to `www.budgetyourmd.ca`;
- the live `www` canonical is accepted;
- absent Squarespace `llms.txt` is Not Applicable;
- every result has evidence/applicability/scope/next action;
- no production Supabase rows are created.

- [ ] **Step 6: Verify production remains empty**

Repeat the six production count queries from Task 11 Step 5. Expected: `1, 8, 0, 0, 0, 0`.

- [ ] **Step 7: Document the validation evidence and commit**

Record exact test counts, local audit result counts, smoke statuses, redirect/canonical evidence, and production-zero verification. State that Protocol is the next plan and production baseline remains unauthorized.

```bash
git add PROJECT_STATE.md docs/technical-audit-operations.md
git commit -m "docs: validate manual Foundation tranche"
```

---

## Final Tranche Verification

- [ ] Run `git status --short` and confirm only intentional changes exist.
- [ ] Run `cd agents && .venv/bin/python -m pytest -q` and record the exact pass/fail count.
- [ ] Run `cd dashboard && npm test && npm run build` and record exact results.
- [ ] Confirm Railway has no cron, scheduler log, schedule endpoint, or schedule variable.
- [ ] Confirm production has one preserved client, eight preserved queries, preserved auth/access, and zero generated runs.
- [ ] Confirm the old Railway checkpoint service is deleted and `checkpoints-v2` is the only checkpoint reference.
- [ ] Confirm no production baseline or production technical-audit result was created.
- [ ] Request code review over `6fbe8eb..HEAD` and resolve every important finding.
- [ ] Use verification-before-completion before declaring Tranche 0 complete.

The next document after this plan is a separate Protocol check-set implementation plan. Do not begin Protocol work until this tranche's development/staging evidence and production reset state are reviewed.
