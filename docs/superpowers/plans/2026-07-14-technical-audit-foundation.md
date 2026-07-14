# Technical Audit Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a production-shaped technical-audit vertical slice with five evidence-backed statuses, deterministic `llms.txt`/title/description/canonical checks, persistence, pipeline integration, and a no-score checklist UI.

**Architecture:** A new `src.technical_audit` package owns immutable observations, versioned check definitions, deterministic evaluation, and persistence-shaped output. The existing inventory and improvement pipeline remain available for query matching and legacy history, while new runs invoke the audit runner and store results in additive Supabase tables. The dashboard selects the new audit by linked improvement run and renders status counts and grouped evidence without calculating a readiness score.

**Tech Stack:** Python 3.11, dataclasses/enums, BeautifulSoup 4, httpx, pytest, Supabase/Postgres, Next.js 16, React 19, TypeScript, Vitest.

## Global Constraints

- Statuses are exactly `pass`, `fail`, `review`, `unknown`, and `not_applicable`.
- Every result carries check ID/version, subject, evidence, applicability, scope, confidence, next action, and remediation ID.
- Deterministic checks make no LLM calls.
- New technical findings do not create `action_cards` or trigger implementation.
- No proprietary aggregate score is stored or rendered.
- Existing `page_citation_scores` and historical action cards remain readable as legacy data.
- When `TECHNICAL_AUDIT_V1_ENABLED=true`, the legacy structural scorer and its technical card generator do not execute; when false, the current path remains unchanged for rollback.
- Database changes are additive and safe for a shared database; do not drop or reinterpret legacy tables.
- All network-input types are explicit and unit tests do not call the public internet.
- The first slice audits the homepage and every page already present in the improvement inventory, bounded by `audit_max_pages`.
- Missing `llms.txt` is `not_applicable` unless `llms_txt_enabled` is true in the client audit profile.
- Title and description character counts are review triggers, never failures by themselves.
- A remediation draft or platform write path is outside this tranche; results expose only a catalogue identifier and next action.

## Delivery Roadmap

This plan proves the shared contract with four checks. Follow-on plans use the same registry/result model:

1. Protocol integrity: robots, sitemap, TLS/HTTPS, and structured-data integrity/coverage.
2. Site-wide integrity: broken links, image optimization, freshness, and existing source-support auditing.
3. Performance/integrations: CrUX, Lighthouse, Search Console, and Bing with explicit unknown/not-applicable outcomes.
4. Safe remediation: catalogue, drafts, stale-state guards, preview/approval/re-audit, and GitHub/WordPress/Webflow/Squarespace adapters.

## File Structure

### New agent files

- `agents/src/technical_audit/__init__.py` — public package exports.
- `agents/src/technical_audit/models.py` — enums and immutable observation/result contracts.
- `agents/src/technical_audit/observations.py` — URL normalization and deterministic HTML/head extraction.
- `agents/src/technical_audit/registry.py` — versioned check registration and duplicate protection.
- `agents/src/technical_audit/checks/llms_txt.py` — optional root-file evaluation.
- `agents/src/technical_audit/checks/metadata.py` — title and meta-description checks.
- `agents/src/technical_audit/checks/canonical.py` — canonical declaration checks.
- `agents/src/technical_audit/checks/__init__.py` — v1 registry assembly.
- `agents/src/technical_audit/runner.py` — executes page/site checks and builds run summary.

### New tests

- `agents/tests/technical_audit/test_models.py`
- `agents/tests/technical_audit/test_observations.py`
- `agents/tests/technical_audit/test_registry.py`
- `agents/tests/technical_audit/test_checks.py`
- `agents/tests/technical_audit/test_runner.py`

### Modified agent files

- `agents/src/improvement/pipeline.py` — invoke and persist the v1 audit without using it to create cards.
- `agents/src/graph/state.py` — expose `technical_audit_run_id` and summary.
- `agents/src/graph/nodes.py` — return empty audit state on a handled pipeline failure.
- `agents/tests/test_improvement_pipeline.py` — prove audit persistence and separation from cards.
- `agents/tests/test_graph_nodes.py` — verify state fallback.

### Database

- `supabase/migrations/014_technical_audit_foundation.sql` — additive run/observation/result/profile tables, constraints, indexes, and admin RLS.
- `supabase/schema.sql` — fold the additive tables into the canonical fresh-install schema without changing legacy history.

### Dashboard

- `dashboard/lib/technical-audit-types.ts` — typed audit contracts and status ordering.
- `dashboard/components/runs/TechnicalAuditChecklist.tsx` — status summary and section/result details.
- `dashboard/__tests__/components/technical-audit-checklist.test.tsx` — rendering and no-score assertions.
- `dashboard/app/admin/clients/[id]/runs/[runId]/page.tsx` — query and render the linked audit; label old readiness values as legacy only.

---

### Task 1: Define the immutable audit contract

**Files:**
- Create: `agents/src/technical_audit/__init__.py`
- Create: `agents/src/technical_audit/models.py`
- Create: `agents/tests/technical_audit/test_models.py`

**Interfaces:**
- Consumes: Python standard library only.
- Produces: `AuditStatus`, `Confidence`, `Observation`, `Applicability`, `NextAction`, `CheckResult`, and `AuditContext`, each with `to_dict()` where persistence needs JSON.

- [ ] **Step 1: Write failing contract tests**

```python
from dataclasses import FrozenInstanceError
import pytest

from src.technical_audit.models import (
    Applicability,
    AuditStatus,
    CheckResult,
    Confidence,
    NextAction,
)


def test_check_result_serializes_the_complete_resolution_contract():
    result = CheckResult(
        check_id="meta_title.present",
        check_version=1,
        section="meta_title",
        subject="https://example.com/",
        status=AuditStatus.FAIL,
        severity="high",
        summary="Title is missing",
        expected="One nonempty title",
        observed={"count": 0},
        evidence_refs=("page:https://example.com/",),
        scope={"sampled": False, "urls_checked": 1},
        applicability=Applicability(True, "HTML page is indexable"),
        confidence=Confidence.HIGH,
        next_action=NextAction("admin", "Add a truthful SEO title"),
        remediation_id="meta_title.add",
    )

    payload = result.to_dict()

    assert payload["status"] == "fail"
    assert payload["confidence"] == "high"
    assert payload["applicability"] == {"applies": True, "reason": "HTML page is indexable"}
    assert payload["next_action"]["owner"] == "admin"
    assert payload["evidence_refs"] == ["page:https://example.com/"]


def test_check_result_is_immutable():
    result = CheckResult.not_applicable(
        check_id="llms_txt.present",
        check_version=1,
        section="llms_txt",
        subject="https://example.com/llms.txt",
        reason="Client has not opted in",
    )
    with pytest.raises(FrozenInstanceError):
        result.status = AuditStatus.FAIL
```

- [ ] **Step 2: Run the model tests and verify RED**

Run: `cd agents && python3 -m pytest tests/technical_audit/test_models.py -q`

Expected: collection fails with `ModuleNotFoundError: No module named 'src.technical_audit'`.

- [ ] **Step 3: Implement the model contract**

Create frozen dataclasses and string enums. `CheckResult.__post_init__` must reject an empty `check_id`, nonpositive version, or a `not_applicable` result whose applicability says `applies=True`. `CheckResult.not_applicable(...)` must populate low severity, high confidence, empty evidence, owner `system`, instruction `No action required`, and no remediation ID. `to_dict()` must recursively convert enums, tuples, and dataclasses into JSON-compatible dictionaries/lists.

Use these exact enum values:

```python
class AuditStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    REVIEW = "review"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
```

`AuditContext` contains `client_id`, `domain`, `profile`, `pages`, `site_observations`, and `run_timestamp`. `Observation` contains `id`, `kind`, `subject`, `retrieved_at`, `fingerprint`, and `data`.

- [ ] **Step 4: Run the model tests and verify GREEN**

Run: `cd agents && python3 -m pytest tests/technical_audit/test_models.py -q`

Expected: `2 passed`.

- [ ] **Step 5: Commit the contract**

```bash
git add agents/src/technical_audit agents/tests/technical_audit/test_models.py
git commit -m "feat: define technical audit result contract"
```

### Task 2: Extract deterministic page observations

**Files:**
- Create: `agents/src/technical_audit/observations.py`
- Create: `agents/tests/technical_audit/test_observations.py`

**Interfaces:**
- Consumes: `Observation` from Task 1 and inventory dictionaries containing `url` and `raw_html`.
- Produces: `extract_page_observation(page: dict, retrieved_at: str) -> Observation` and `normalize_url(url: str) -> str`.

- [ ] **Step 1: Write failing extraction tests**

```python
from src.technical_audit.observations import extract_page_observation


def test_extracts_all_head_declarations_without_semantic_judgment():
    page = {
        "url": "https://example.com/service",
        "raw_html": """<html><head>
          <title>Service | Example</title>
          <meta name="description" content="A precise service description.">
          <link rel="canonical" href="/service">
        </head><body><h1>Service</h1></body></html>""",
    }
    observation = extract_page_observation(page, "2026-07-14T10:00:00+00:00")

    assert observation.id == "page:https://example.com/service"
    assert observation.data["titles"] == ["Service | Example"]
    assert observation.data["meta_descriptions"] == ["A precise service description."]
    assert observation.data["canonicals"] == ["https://example.com/service"]
    assert observation.data["is_html"] is True
    assert len(observation.fingerprint) == 64


def test_preserves_duplicate_empty_declarations_for_checks_to_evaluate():
    page = {
        "url": "https://example.com/",
        "raw_html": '<html><head><title></title><title>Second</title><meta name="description" content=""></head></html>',
    }
    observation = extract_page_observation(page, "2026-07-14T10:00:00+00:00")

    assert observation.data["titles"] == ["", "Second"]
    assert observation.data["meta_descriptions"] == [""]
```

- [ ] **Step 2: Run and verify RED**

Run: `cd agents && python3 -m pytest tests/technical_audit/test_observations.py -q`

Expected: import fails because `observations.py` does not exist.

- [ ] **Step 3: Implement extraction**

Use BeautifulSoup to inspect only `<head>`. Preserve declaration count and trimmed values. Resolve canonical `href` values with `urljoin(page["url"], href)`. Calculate SHA-256 over UTF-8 `raw_html`. Treat a parsed HTML document as HTML unless the inventory supplies a non-HTML `content_type`. Store `url`, `titles`, `meta_descriptions`, `canonicals`, `robots_directives`, `h1_texts`, and `is_html` in `data`. URL normalization lowercases scheme/host, removes fragments, preserves path/query, and ensures an empty path becomes `/`.

- [ ] **Step 4: Run and verify GREEN**

Run: `cd agents && python3 -m pytest tests/technical_audit/test_observations.py -q`

Expected: `2 passed`.

- [ ] **Step 5: Commit observations**

```bash
git add agents/src/technical_audit/observations.py agents/tests/technical_audit/test_observations.py
git commit -m "feat: extract technical audit observations"
```

### Task 3: Add a versioned deterministic registry

**Files:**
- Create: `agents/src/technical_audit/registry.py`
- Create: `agents/tests/technical_audit/test_registry.py`

**Interfaces:**
- Consumes: `AuditContext` and `CheckResult`.
- Produces: `CheckDefinition`, `CheckRegistry.register()`, `CheckRegistry.definitions()`, and `CheckRegistry.run(context)`.

- [ ] **Step 1: Write failing registry tests**

```python
import pytest

from src.technical_audit.registry import CheckDefinition, CheckRegistry


def test_registry_rejects_duplicate_check_versions():
    registry = CheckRegistry()
    definition = CheckDefinition("meta_title.present", 1, "meta_title", "page", lambda context: [])
    registry.register(definition)

    with pytest.raises(ValueError, match="duplicate check version"):
        registry.register(definition)


def test_registry_runs_in_stable_id_version_order():
    calls = []
    registry = CheckRegistry()
    registry.register(CheckDefinition("z.check", 1, "z", "site", lambda context: calls.append("z") or []))
    registry.register(CheckDefinition("a.check", 2, "a", "site", lambda context: calls.append("a2") or []))
    registry.register(CheckDefinition("a.check", 1, "a", "site", lambda context: calls.append("a1") or []))

    assert registry.run(object()) == []
    assert calls == ["a1", "a2", "z"]
```

- [ ] **Step 2: Run and verify RED**

Run: `cd agents && python3 -m pytest tests/technical_audit/test_registry.py -q`

Expected: import fails because `registry.py` does not exist.

- [ ] **Step 3: Implement the registry**

`CheckDefinition` is frozen and contains `id`, `version`, `section`, `scope`, and an evaluator callable. Registry keys are `(id, version)`. `definitions()` returns a tuple sorted by ID then version. `run()` concatenates evaluator results and validates that every result's ID/version/section match its definition; a mismatch raises `ValueError` instead of persisting corrupt provenance.

- [ ] **Step 4: Run and verify GREEN**

Run: `cd agents && python3 -m pytest tests/technical_audit/test_registry.py -q`

Expected: `2 passed`.

- [ ] **Step 5: Commit the registry**

```bash
git add agents/src/technical_audit/registry.py agents/tests/technical_audit/test_registry.py
git commit -m "feat: add versioned technical check registry"
```

### Task 4: Implement the first four checklist sections

**Files:**
- Create: `agents/src/technical_audit/checks/__init__.py`
- Create: `agents/src/technical_audit/checks/llms_txt.py`
- Create: `agents/src/technical_audit/checks/metadata.py`
- Create: `agents/src/technical_audit/checks/canonical.py`
- Create: `agents/tests/technical_audit/test_checks.py`

**Interfaces:**
- Consumes: `AuditContext` page observations and `site_observations["llms_txt"]` with `status_code`, `content_type`, `body`, `final_url`, and `error`.
- Produces: `build_v1_registry() -> CheckRegistry` containing `llms_txt.integrity`, `meta_title.integrity`, `meta_description.integrity`, and `canonical.integrity`, all version 1.

- [ ] **Step 1: Write failing behavior tests**

Cover these exact outcomes in table-driven tests:

```python
def test_title_statuses(context_factory):
    assert status_for(context_factory(title=[]), "meta_title.integrity") == "fail"
    assert status_for(context_factory(title=["Accurate title"]), "meta_title.integrity") == "pass"
    assert status_for(context_factory(title=["A" * 101]), "meta_title.integrity") == "review"
    assert status_for(context_factory(title=["One", "Two"]), "meta_title.integrity") == "fail"


def test_description_statuses(context_factory):
    assert status_for(context_factory(description=[]), "meta_description.integrity") == "review"
    assert status_for(context_factory(description=["A useful description for this page."]), "meta_description.integrity") == "review"
    assert status_for(context_factory(description=["A" * 80]), "meta_description.integrity") == "pass"
    assert status_for(context_factory(description=["A" * 201]), "meta_description.integrity") == "review"
    assert status_for(context_factory(description=["One" * 20, "Two" * 20]), "meta_description.integrity") == "fail"


def test_canonical_statuses(context_factory):
    assert status_for(context_factory(canonical=[]), "canonical.integrity") == "review"
    assert status_for(context_factory(canonical=["https://example.com/page"]), "canonical.integrity") == "pass"
    assert status_for(context_factory(canonical=["http://staging.example.com/page"]), "canonical.integrity") == "fail"
    assert status_for(context_factory(canonical=["https://example.com/one", "https://example.com/two"]), "canonical.integrity") == "fail"


def test_llms_txt_is_optional_until_profile_enables_it(context_factory):
    disabled = context_factory(llms_enabled=False, llms_status=404, llms_body="")
    enabled = context_factory(llms_enabled=True, llms_status=404, llms_body="")

    assert status_for(disabled, "llms_txt.integrity") == "not_applicable"
    assert status_for(enabled, "llms_txt.integrity") == "fail"
```

The fixture helper constructs one page observation and returns `AuditContext`. For a non-indexable or non-HTML page, title/description/canonical checks return `not_applicable` with the precise reason. Description absence is `review` on priority pages and `not_applicable` on nonpriority pages. The short-description case above is `review` because it is below 50 characters.

- [ ] **Step 2: Run and verify RED**

Run: `cd agents && python3 -m pytest tests/technical_audit/test_checks.py -q`

Expected: imports fail because check modules do not exist.

- [ ] **Step 3: Implement the four evaluators**

Use only observation fields and profile data. Required decision tables:

| Check | Pass | Fail | Review | N/A | Unknown |
|---|---|---|---|---|---|
| `llms_txt.integrity` | Enabled/exists, text-like, nonempty, no staging/secret markers | Enabled but missing, HTML fallback, empty, or unsafe markers | Exists while disabled, or semantic description/links need review | Disabled and absent | Fetch error/403/429 |
| `meta_title.integrity` | One nonempty title ≤100 chars | Missing, empty, or multiple titles | One title >100 chars, or 65–100 chars when whitespace-token count exceeds 12 | Non-HTML/non-indexable | Observation missing |
| `meta_description.integrity` | One nonempty 50–200 char value | Multiple declarations | Missing on priority page, or one value outside 50–200 | Non-HTML/non-indexable, or missing on nonpriority page | Observation missing |
| `canonical.integrity` | One absolute HTTPS same-site canonical without fragment/staging marker | Multiple/conflicting, malformed, HTTP, staging, or unexpected cross-domain target | Missing declaration | Non-HTML/non-indexable | Observation missing |

Do not fetch canonical targets in this tranche; the result's expected text must state that target-health validation belongs to the protocol-integrity plan. Use remediation IDs `llms_txt.correct`, `meta_title.correct`, `meta_description.correct`, and `canonical.correct` only for fail/review results.

- [ ] **Step 4: Run and verify GREEN**

Run: `cd agents && python3 -m pytest tests/technical_audit/test_checks.py -q`

Expected: all parameterized cases pass.

- [ ] **Step 5: Commit the checks**

```bash
git add agents/src/technical_audit/checks agents/tests/technical_audit/test_checks.py
git commit -m "feat: add initial deterministic audit checks"
```

### Task 5: Run and summarize an audit without scoring

**Files:**
- Create: `agents/src/technical_audit/runner.py`
- Create: `agents/tests/technical_audit/test_runner.py`

**Interfaces:**
- Consumes: `run_technical_audit(client_id: str, domain: str, inventory: list[dict], profile: dict, fetcher: Callable) -> dict`.
- Produces: `{"audit_version": 1, "observations": list[dict], "results": list[dict], "summary": dict}`.

- [ ] **Step 1: Write a failing end-to-end runner test**

```python
def test_runner_returns_counts_and_never_a_score():
    inventory = [{
        "url": "https://example.com/",
        "raw_html": '<html><head><title>Example</title><meta name="description" content="' + ("A" * 80) + '"><link rel="canonical" href="https://example.com/"></head><body></body></html>',
    }]

    report = run_technical_audit(
        client_id="client-1",
        domain="example.com",
        inventory=inventory,
        profile={"llms_txt_enabled": False, "priority_urls": ["https://example.com/"]},
        fetcher=lambda url: {"status_code": 404, "content_type": "text/plain", "body": "", "final_url": url, "error": None},
    )

    assert report["audit_version"] == 1
    assert report["summary"] == {"pass": 3, "fail": 0, "review": 0, "unknown": 0, "not_applicable": 1, "total": 4}
    assert "score" not in report
    assert all("score" not in result for result in report["results"])
```

- [ ] **Step 2: Run and verify RED**

Run: `cd agents && python3 -m pytest tests/technical_audit/test_runner.py -q`

Expected: import fails because `runner.py` does not exist.

- [ ] **Step 3: Implement the runner**

Extract one page observation per inventory row, fetch only `https://{domain}/llms.txt`, build `AuditContext`, execute `build_v1_registry()`, and count statuses from the returned results. The injected fetcher makes network behavior testable. The production default uses `httpx.get(timeout=10, follow_redirects=True)` and returns a structured error rather than raising. Ensure homepage is included in inventory by adding a fetched homepage observation only when the existing inventory omitted both `https://domain` and `https://domain/`.

- [ ] **Step 4: Run and verify GREEN**

Run: `cd agents && python3 -m pytest tests/technical_audit/test_runner.py -q`

Expected: runner tests pass.

- [ ] **Step 5: Run the entire new package suite**

Run: `cd agents && python3 -m pytest tests/technical_audit -q`

Expected: all technical-audit tests pass with no warnings.

- [ ] **Step 6: Commit the runner**

```bash
git add agents/src/technical_audit/runner.py agents/tests/technical_audit/test_runner.py
git commit -m "feat: run unscored technical audits"
```

### Task 6: Add additive persistence and client audit profiles

**Files:**
- Create: `supabase/migrations/014_technical_audit_foundation.sql`
- Modify: `supabase/schema.sql`

**Interfaces:**
- Consumes: `clients`, `improvement_runs`, and `pipeline_runs` IDs.
- Produces: `client_site_profiles`, `technical_audit_runs`, `technical_audit_observations`, and `technical_audit_results`.

- [ ] **Step 1: Write the additive migration**

The migration creates:

```sql
create table public.client_site_profiles (
  client_id uuid primary key references public.clients(id) on delete cascade,
  audit_version integer not null default 1 check (audit_version > 0),
  llms_txt_enabled boolean not null default false,
  priority_urls text[] not null default '{}',
  platform text not null default 'unknown'
    check (platform in ('unknown', 'github', 'wordpress', 'webflow', 'squarespace', 'other')),
  integration_state jsonb not null default '{}'::jsonb,
  verified_facts jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table public.technical_audit_runs (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients(id) on delete cascade,
  improvement_run_id uuid references public.improvement_runs(id) on delete set null,
  pipeline_run_id uuid references public.pipeline_runs(id) on delete set null,
  audit_version integer not null check (audit_version > 0),
  status text not null default 'running' check (status in ('running', 'completed', 'error')),
  scope jsonb not null default '{}'::jsonb,
  summary jsonb not null default '{}'::jsonb,
  error_message text,
  started_at timestamptz not null default now(),
  completed_at timestamptz
);

create table public.technical_audit_results (
  id uuid primary key default gen_random_uuid(),
  audit_run_id uuid not null references public.technical_audit_runs(id) on delete cascade,
  check_id text not null,
  check_version integer not null check (check_version > 0),
  section text not null,
  subject text not null,
  status text not null check (status in ('pass', 'fail', 'review', 'unknown', 'not_applicable')),
  severity text not null,
  summary text not null,
  expected text not null,
  observed jsonb not null default '{}'::jsonb,
  evidence_refs text[] not null default '{}',
  scope jsonb not null default '{}'::jsonb,
  applicability jsonb not null,
  confidence text not null check (confidence in ('high', 'medium', 'low')),
  next_action jsonb not null,
  remediation_id text,
  lifecycle_state text not null default 'new'
    check (lifecycle_state in ('new', 'continuing', 'changed', 'resolved', 'regressed')),
  created_at timestamptz not null default now(),
  unique (audit_run_id, check_id, check_version, subject)
);
```

Between the run and result tables, create `technical_audit_observations` with a UUID primary key, `audit_run_id` cascade foreign key, stable `observation_ref`, kind, subject, retrieval timestamp, SHA-256 fingerprint, bounded JSON data, and `unique (audit_run_id, observation_ref)`. Result `evidence_refs` values address `observation_ref` within the same run.

Add indexes for run/client, result run/status/section, enable RLS, grant admin management using the existing `is_admin()` function, and grant authenticated client users select access only where `client_id = get_my_client_id()`. Do not add client write policies.

- [ ] **Step 2: Fold the same tables into the consolidated schema**

Add drop statements in dependency order, table definitions after `improvement_runs`, indexes, RLS enablement, and policies matching the migration. Preserve every legacy table and comment that old readiness rows remain historical.

- [ ] **Step 3: Validate migration syntax and destructive-operation absence**

Run:

```bash
rg -n "drop table|truncate|delete from|alter table .* drop" supabase/migrations/014_technical_audit_foundation.sql
git diff --check
```

Expected: the first command returns no matches and `git diff --check` exits 0.

- [ ] **Step 4: Commit persistence**

```bash
git add supabase/migrations/014_technical_audit_foundation.sql supabase/schema.sql
git commit -m "feat: persist versioned technical audits"
```

### Task 7: Integrate the audit into improvement runs without generating cards

**Files:**
- Modify: `agents/src/improvement/pipeline.py`
- Modify: `agents/src/graph/state.py`
- Modify: `agents/src/graph/nodes.py`
- Modify: `agents/tests/test_improvement_pipeline.py`
- Modify: `agents/tests/test_graph_nodes.py`

**Interfaces:**
- Consumes: `run_technical_audit(...)` and Supabase tables from Task 6.
- Produces: `technical_audit_run_id` and `technical_audit_summary` in pipeline/state output.

- [ ] **Step 1: Add a failing pipeline separation test**

Patch `src.improvement.pipeline.run_technical_audit` to return one failing title result and summary. Assert:

```python
monkeypatch.setenv("TECHNICAL_AUDIT_V1_ENABLED", "true")

assert result["technical_audit_run_id"] == "audit-run-1"
assert result["technical_audit_summary"]["fail"] == 1
assert not any(card.get("pillar") == "meta_title" for card in result["action_cards"])
mock_score.assert_not_called()
mock_quality.assert_not_called()
mock_classify.assert_not_called()
mock_sonnet.assert_not_called()

inserted_tables = [call.args[0] for call in mock_sb.return_value.table.call_args_list]
assert "technical_audit_runs" in inserted_tables
assert "technical_audit_results" in inserted_tables
```

Add a graph-node test asserting the handled error fallback contains `technical_audit_run_id: None` and an empty `technical_audit_summary`.

- [ ] **Step 2: Run and verify RED**

Run: `cd agents && python3 -m pytest tests/test_improvement_pipeline.py tests/test_graph_nodes.py -q`

Expected: assertions fail because the pipeline has no technical-audit fields or calls.

- [ ] **Step 3: Integrate the runner and persistence**

After inventory and before legacy scoring/card generation:

1. Load `client_site_profiles` with `.eq("client_id", client_id).maybe_single()` behavior; use `{}` if absent.
2. Insert a `technical_audit_runs` row linked to the improvement run and current pipeline thread's `pipeline_runs` row when available.
3. Call `run_technical_audit` with inventory/profile.
4. Insert each bounded observation and each result with `audit_run_id`; update the audit run to completed with scope and summary.
5. On audit-only failure, mark that audit run `error`, include the error in pipeline output, and continue the existing query/content path. Do not fabricate unknown results for a runner crash.
6. Return audit ID/summary/results in memory, but never pass them to `classify_actions` or `generate_sonnet_specifics`.

Guard the new path with:

```python
technical_audit_enabled = os.environ.get("TECHNICAL_AUDIT_V1_ENABLED", "false").lower() == "true"
```

When enabled, do not call `compute_structural_score`, `generate_sonnet_quality`, `classify_actions`, or `generate_sonnet_specifics`, and do not write `page_citation_scores` or technical `action_cards`. Continue query matching, competitive-gap calculation, content-gap cards, and community-check cards because those are independent of the technical audit. When disabled, preserve the current legacy path exactly as a rollback route. Add the new state fields in both paths.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `cd agents && python3 -m pytest tests/test_improvement_pipeline.py tests/test_graph_nodes.py -q`

Expected: all focused tests pass.

- [ ] **Step 5: Run the complete agent suite**

Run: `cd agents && python3 -m pytest -q`

Expected: all tests pass. If pre-existing baseline failures recur, compare against the recorded worktree baseline and do not conceal them.

- [ ] **Step 6: Commit pipeline integration**

```bash
git add agents/src/improvement/pipeline.py agents/src/graph/state.py agents/src/graph/nodes.py agents/tests/test_improvement_pipeline.py agents/tests/test_graph_nodes.py
git commit -m "feat: attach technical checklist to improvement runs"
```

### Task 8: Render the no-score checklist in the dashboard

**Files:**
- Create: `dashboard/lib/technical-audit-types.ts`
- Create: `dashboard/components/runs/TechnicalAuditChecklist.tsx`
- Create: `dashboard/__tests__/components/technical-audit-checklist.test.tsx`
- Modify: `dashboard/app/admin/clients/[id]/runs/[runId]/page.tsx`

**Interfaces:**
- Consumes: `TechnicalAuditRun` and `TechnicalAuditResult[]` selected by `improvement_run_id`.
- Produces: `<TechnicalAuditChecklist run={run} results={results} />`.

- [ ] **Step 1: Write failing component tests**

```tsx
it("shows five status counts and no readiness score", () => {
  render(<TechnicalAuditChecklist run={runFixture} results={resultFixtures} />);

  expect(screen.getByText("Technical audit")).toBeInTheDocument();
  expect(screen.getByText("1 pass")).toBeInTheDocument();
  expect(screen.getByText("1 review")).toBeInTheDocument();
  expect(screen.getByText("1 unknown")).toBeInTheDocument();
  expect(screen.getByText("1 not applicable")).toBeInTheDocument();
  expect(screen.queryByText(/readiness/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/\/100/)).not.toBeInTheDocument();
});

it("shows the resolution contract for a non-pass result", () => {
  render(<TechnicalAuditChecklist run={runFixture} results={resultFixtures} />);
  fireEvent.click(screen.getByText("Canonical declaration is missing"));

  expect(screen.getByText("Expected")).toBeInTheDocument();
  expect(screen.getByText("Why this applies")).toBeInTheDocument();
  expect(screen.getByText("Next action")).toBeInTheDocument();
  expect(screen.getByText("Add a canonical through the site's authoritative SEO setting")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run and verify RED**

Run: `cd dashboard && npm test -- __tests__/components/technical-audit-checklist.test.tsx`

Expected: import fails because the component does not exist.

- [ ] **Step 3: Implement typed status presentation**

Define the status union exactly as the database constraint. Export labels/order/colors from the type module. Render one compact summary row and results grouped by section in `<details>` elements. Each row shows status, summary, subject, scope, expected, observed JSON in a `<pre>`, applicability reason, confidence, owner, and next action. Collapse `pass` and `not_applicable` groups initially; keep `fail`, `review`, and `unknown` open. Do not render a score, percentage, “clear/blocked” shortcut, approve/reject controls, or implementation button.

- [ ] **Step 4: Integrate the run page**

Query `technical_audit_runs` by `improvement_run_id`, then query `technical_audit_results` by audit run ID ordered by section/check ID/subject. Replace the current readiness tile for new audit runs with status counts and render the checklist below the evidence tiles. When no new audit exists but `page_citation_scores` do, label that tile `LEGACY READINESS` and preserve historical rendering. Update the funnel copy for new runs to say `{total} technical checks · {fail} failures · {review} reviews · {unknown} unknown` instead of “pages scored.”

- [ ] **Step 5: Run component tests and verify GREEN**

Run: `cd dashboard && npm test -- __tests__/components/technical-audit-checklist.test.tsx`

Expected: component tests pass.

- [ ] **Step 6: Run dashboard verification**

Run:

```bash
cd dashboard
npm test
npm run lint
npm run build
```

Expected: tests, lint, type checking, and production build pass.

- [ ] **Step 7: Commit the dashboard slice**

```bash
git add dashboard/lib/technical-audit-types.ts dashboard/components/runs/TechnicalAuditChecklist.tsx dashboard/__tests__/components/technical-audit-checklist.test.tsx dashboard/app/admin/clients/'[id]'/runs/'[runId]'/page.tsx
git commit -m "feat: show evidence-backed technical checklist"
```

### Task 9: Verify the vertical slice and update operator documentation

**Files:**
- Create: `docs/technical-audit-operations.md`
- Modify: `PROJECT_STATE.md`

**Interfaces:**
- Consumes: implemented audit runner, database model, and checklist UI.
- Produces: operator instructions for statuses, profiles, rollout, failure handling, and rollback flag use.

- [ ] **Step 1: Write operator documentation**

Document:

- the five statuses and what the founders do for each;
- how `llms_txt_enabled` and `priority_urls` affect applicability;
- that audit failures do not create implementation cards;
- how to identify legacy versus v1 runs;
- how to apply migration 014 to a development/staging Supabase project;
- how to verify counts and inspect evidence;
- how to disable invocation with `TECHNICAL_AUDIT_V1_ENABLED=false` while retaining stored results;
- that production database migration and production rollout require separate approval.

Update `PROJECT_STATE.md` with the feature branch name, migration number, new test commands, and the current rollout state `development only`.

- [ ] **Step 2: Verify the rollback route explicitly**

Run the two focused Task 7 tests that set `TECHNICAL_AUDIT_V1_ENABLED=true` and `false`. The enabled test must assert that the four legacy scoring/card mocks have zero calls. The disabled test must assert that no `technical_audit_runs` insert occurs and the existing legacy structural-card fixture still passes.

- [ ] **Step 3: Run final verification**

Run:

```bash
cd agents && python3 -m pytest -q
cd ../dashboard && npm test && npm run lint && npm run build
cd .. && git diff --check && git status --short
```

Expected: all tests/build checks pass; `git diff --check` is clean; status contains only the intended documentation or is clean after commit.

- [ ] **Step 4: Commit operations documentation and flag**

```bash
git add docs/technical-audit-operations.md PROJECT_STATE.md
git commit -m "docs: add technical audit rollout controls"
```

- [ ] **Step 5: Review against acceptance criteria**

Confirm from tests and rendered output:

1. No new result or UI field contains a proprietary score.
2. All five statuses are representable and explained.
3. Four check definitions are versioned and deterministic.
4. Missing integrations/applicability are not reported as failures.
5. New findings do not enter `action_cards`.
6. Legacy runs remain readable.
7. The feature defaults off and can run in development/staging without changing production behavior.
8. No platform write, source generation, date mutation, or auto-publish path exists in this tranche.
