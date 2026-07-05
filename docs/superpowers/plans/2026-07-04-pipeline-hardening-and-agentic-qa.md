# Pipeline Hardening + Agentic QA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the broken approval→implementation seam and observability gaps in the improvement pipeline, then add three agentic capabilities: card QA self-review, policy-based auto-approve, and post-implementation verification.

**Architecture:** All work is in the Python backend (`agents/`) plus one SQL migration. Tasks 1–7 fix seams found in the 2026-07-04 review (card IDs never attached, in-memory checkpointer, dead `/api/schedules`, duplicate cards, raw-HTML-to-Sonnet, missing crawlability cards, gutted `improvement_only` runs). Tasks 8–11 add the agentic layer: a Haiku QA pass that regenerates-or-drops bad cards before they surface, an auto-approve policy that skips human review for proven-safe action types, and a verifier that re-fetches pages after publishing to confirm changes are live.

**Tech Stack:** Python 3.11+, LangGraph 1.x (`PostgresSaver` from `langgraph-checkpoint-postgres` — already in pyproject.toml), Supabase (Postgres + PostgREST), Anthropic SDK (Sonnet for generation, Haiku for QA), httpx, BeautifulSoup, pytest.

**Conventions:** Tests live in `agents/tests/`, use `unittest.mock.patch` on the module under test's imports (see `tests/test_improvement_pipeline.py` for the Supabase mock pattern). Run all commands from `agents/` using `.venv/bin/python -m pytest`. Models are hardcoded string ids, matching existing code.

---

## File Structure

**New files:**

| File | Responsibility |
|---|---|
| `supabase/migrations/009_agentic_qa.sql` | `auto_approved` + `verification` columns on action_cards; `auto_approve_action_types` on clients |
| `agents/src/improvement/card_qa.py` | Card QA: programmatic before_text grounding check + Haiku specificity review |
| `agents/src/improvement/auto_approve.py` | Auto-approve eligibility from card history + policy application |
| `agents/src/improvement/verifier.py` | Post-implementation page re-fetch and change verification |
| `agents/tests/test_card_qa.py` | Tests for card_qa |
| `agents/tests/test_auto_approve.py` | Tests for auto_approve |
| `agents/tests/test_verifier.py` | Tests for verifier |

**Modified files:**

| File | Changes |
|---|---|
| `agents/src/improvement/pipeline.py` | Attach DB ids after insert; dedupe Step 6 by page; body-text to Sonnet; crawlability card; QA loop; auto-approve application |
| `agents/src/improvement/scorer.py` | Add `extract_body_text()` helper |
| `agents/src/improvement/card_generator.py` | Add `build_crawlability_card()` |
| `agents/src/graph/nodes.py` | Always fetch competitive gaps; auto-approve config in `load_config`; verification in `run_implementation_node` |
| `agents/src/graph/pipeline.py` | Conditional edge: skip `await_approval` when nothing pending |
| `agents/server.py` | Fix `/api/schedules` column name; Postgres checkpointer |
| `agents/tests/test_improvement_pipeline.py` | Update mocks for new pipeline calls; new tests for id-attach + dedupe |
| `agents/tests/test_server.py` | Update schedules test if it asserts `created_at` |
| `agents/tests/test_graph_nodes.py` | Update for gap-fetch and verification changes |

---

### Task 1: Attach DB ids to inserted action cards

The pipeline inserts cards but discards the returned rows, so state cards have no `id` and `run_implementation_node` can never match approved ids. Capture the insert response and merge ids back.

**Files:**
- Modify: `agents/src/improvement/pipeline.py` (the `action_cards` insert, currently ~line 232-241)
- Test: `agents/tests/test_improvement_pipeline.py`

- [ ] **Step 1: Write the failing test**

Add to `agents/tests/test_improvement_pipeline.py`, inside `TestRunImprovementPipeline` (copy the decorator stack and mock setup from `test_returns_expected_state_keys` — same 11 patches):

```python
    @patch("src.improvement.pipeline._get_supabase")
    @patch("src.improvement.pipeline.run_crawlability_gate")
    @patch("src.improvement.pipeline.build_inventory")
    @patch("src.improvement.pipeline.match_queries_to_pages")
    @patch("src.improvement.pipeline.compute_structural_score")
    @patch("src.improvement.pipeline.generate_sonnet_quality")
    @patch("src.improvement.pipeline.check_competitive_gaps")
    @patch("src.improvement.pipeline.run_reddit_scout")
    @patch("src.improvement.pipeline.classify_actions")
    @patch("src.improvement.pipeline.generate_sonnet_specifics")
    @patch("src.improvement.pipeline.validate_json_ld")
    def test_cards_get_db_ids_after_insert(
        self, mock_validate, mock_sonnet, mock_classify, mock_reddit,
        mock_gaps, mock_quality, mock_score, mock_match, mock_inv,
        mock_crawl, mock_sb,
    ):
        mock_table = MagicMock()
        # insert() returns run row first, then card rows with generated ids
        mock_table.insert.return_value.execute.side_effect = [
            MagicMock(data=[{"id": "run-123"}]),      # improvement_runs insert
            MagicMock(data=[{"id": "row-inv"}]),      # page_inventory insert
            MagicMock(data=[{"id": "row-match"}]),    # query_page_matches insert
            MagicMock(data=[{"id": "row-score"}]),    # page_citation_scores insert
            MagicMock(data=[{"id": "card-uuid-1"}]),  # action_cards insert
        ]
        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_sb.return_value.table.return_value = mock_table

        mock_crawl.return_value = {"has_critical_blocker": False}
        mock_inv.return_value = [
            {"url": "https://x.com/p1", "title": "Page 1", "h1": "H1", "first_paragraph": "text",
             "raw_html": "<html><body><p>content here</p></body></html>", "last_modified": None,
             "word_count": 500, "outbound_link_count": 0, "has_faq_schema": False,
             "has_comparison_table": False, "schema_types": []},
        ]
        mock_match.return_value = [
            {"query": "q1", "query_id": "id1", "match_type": "matched",
             "matched_page_url": "https://x.com/p1", "similarity_score": 0.7, "bucket": "awareness"},
        ]
        mock_score.return_value = {"structural_score": 60, "check_results": {}, "schema_status": "missing", "schema_errors": []}
        mock_quality.return_value = {"specificity": 3, "completeness": 3, "answer_directness": 3, "summary": "OK"}
        mock_gaps.return_value = [{"query": "q1", "query_id": "id1", "competitive_gap": 0.0,
                                   "top_competitor": None, "client_mention_rate": 0.3, "competitor_mention_rate": 0.0}]
        mock_reddit.return_value = []
        mock_classify.return_value = [{"action_type": "generate_schema", "page_url": "https://x.com/p1", "issue": "No schema"}]
        mock_sonnet.return_value = {"before_text": "", "after_text": "", "code_block": '{"@context":"https://schema.org","@type":"Organization","name":"X"}'}
        mock_validate.return_value = {"valid": True, "errors": []}

        state = {"client_id": "client-1",
                 "client_config": {"website_domain": "x.com", "brand_name": "BrandX", "competitors": []},
                 "tracker_results": []}
        queries = [{"id": "id1", "prompt_text": "q1", "bucket": "awareness"}]

        result = run_improvement_pipeline(state, queries, competitive_gaps_data=[])

        assert len(result["action_cards"]) == 1
        assert result["action_cards"][0]["id"] == "card-uuid-1"
```

Note: `side_effect` ordering assumes inserts happen in pipeline order (run → inventory → matches → scores → cards). If Tasks 4–6 later add calls, the executor adjusts the side_effect list — the assertion is what matters.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents && .venv/bin/python -m pytest tests/test_improvement_pipeline.py::TestRunImprovementPipeline::test_cards_get_db_ids_after_insert -v`
Expected: FAIL — `KeyError: 'id'` (cards have no id key).

- [ ] **Step 3: Implement**

In `agents/src/improvement/pipeline.py`, replace the card insert block:

```python
        if all_cards:
            card_rows = []
            for c in all_cards:
                row = {k: v for k, v in c.items()}
                if "brief" in row and not isinstance(row["brief"], (dict, type(None))):
                    del row["brief"]
                if "reddit_data" in row and not isinstance(row["reddit_data"], (dict, type(None))):
                    del row["reddit_data"]
                card_rows.append(row)
            insert_resp = sb.table("action_cards").insert(card_rows).execute()
            inserted_rows = insert_resp.data or []
            for card, row in zip(all_cards, inserted_rows):
                card["id"] = row.get("id")
```

- [ ] **Step 4: Run the full pipeline test file**

Run: `cd agents && .venv/bin/python -m pytest tests/test_improvement_pipeline.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/src/improvement/pipeline.py agents/tests/test_improvement_pipeline.py
git commit -m "fix: attach DB ids to action cards so approval can find them"
```

---

### Task 2: Fix /api/schedules column name

`pipeline_runs` has `started_at` (migration 003), not `created_at`. The endpoint 500s on first call.

**Files:**
- Modify: `agents/server.py:296-320` (the `get_schedules` handler)
- Test: `agents/tests/test_server.py`

- [ ] **Step 1: Check existing server test pattern, write the failing test**

Read `agents/tests/test_server.py` first and reuse its client/auth fixture pattern. Add:

```python
def test_schedules_uses_started_at(monkeypatch):
    """The schedules endpoint must query pipeline_runs by started_at (created_at doesn't exist)."""
    import server as server_mod

    captured = {}

    class FakeQuery:
        def __init__(self, table):
            self.table = table
        def select(self, cols):
            captured[self.table] = cols
            return self
        def order(self, col, desc=False):
            captured[self.table + "_order"] = col
            return self
        def execute(self):
            return type("R", (), {"data": []})()

    class FakeSB:
        def table(self, name):
            return FakeQuery(name)

    monkeypatch.setattr(server_mod, "_get_supabase", lambda: FakeSB())

    from fastapi.testclient import TestClient
    client = TestClient(server_mod.app)
    resp = client.get("/api/schedules", headers={"Authorization": "Bearer dev-key"})

    assert resp.status_code == 200
    assert "started_at" in captured["pipeline_runs"]
    assert captured["pipeline_runs_order"] == "started_at"
```

(If `test_server.py` already has a shared auth-header constant or app fixture, use those instead of the literals above.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents && .venv/bin/python -m pytest tests/test_server.py::test_schedules_uses_started_at -v`
Expected: FAIL — captured column string contains `created_at`.

- [ ] **Step 3: Implement**

In `agents/server.py` `get_schedules`, change:

```python
    runs_resp = sb.table("pipeline_runs").select("client_id, status, started_at").order("started_at", desc=True).execute()
```

and below, in the schedule dict:

```python
            "last_run_at": last_run["started_at"] if last_run else None,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agents && .venv/bin/python -m pytest tests/test_server.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/server.py agents/tests/test_server.py
git commit -m "fix: /api/schedules queried nonexistent created_at column"
```

---

### Task 3: Durable checkpointer (PostgresSaver)

`MemorySaver` loses paused approval threads on every restart/deploy. `langgraph-checkpoint-postgres` is already declared in `agents/pyproject.toml` — wire it up, gated on a `DATABASE_URL` env var (Supabase's direct Postgres connection string), with MemorySaver fallback for local dev.

**Files:**
- Modify: `agents/server.py` (graph construction, top of file)
- Test: `agents/tests/test_server.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_checkpointer_returns_none_without_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    import server as server_mod
    assert server_mod._build_checkpointer() is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents && .venv/bin/python -m pytest tests/test_server.py::test_build_checkpointer_returns_none_without_database_url -v`
Expected: FAIL — `AttributeError: module 'server' has no attribute '_build_checkpointer'`.

- [ ] **Step 3: Implement**

In `agents/server.py`, replace `graph = build_graph()` with:

```python
def _build_checkpointer():
    """Postgres-backed checkpointer so paused approval threads survive restarts.

    Requires DATABASE_URL (Supabase direct connection string, port 5432).
    Returns None when unset — build_graph falls back to MemorySaver (local dev).
    """
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        return None
    from psycopg_pool import ConnectionPool
    from langgraph.checkpoint.postgres import PostgresSaver
    pool = ConnectionPool(db_url, kwargs={"autocommit": True, "prepare_threshold": 0}, open=True)
    saver = PostgresSaver(pool)
    saver.setup()
    print("  [Checkpointer] PostgresSaver enabled")
    return saver


graph = build_graph(checkpointer=_build_checkpointer())
```

Notes for the engineer:
- `saver.setup()` creates LangGraph's checkpoint tables on first run — idempotent.
- `psycopg_pool` and `psycopg` come in as dependencies of `langgraph-checkpoint-postgres`; verify with `.venv/bin/python -c "import psycopg_pool"`.
- Use Supabase's **session-mode** connection string (port 5432, not the 6543 transaction pooler) — PostgresSaver needs prepared statements disabled either way, hence `prepare_threshold: 0`.
- Deployment step (manual, not code): set `DATABASE_URL` on Railway.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agents && .venv/bin/python -m pytest tests/test_server.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/server.py agents/tests/test_server.py
git commit -m "feat: Postgres checkpointer so pending approvals survive restarts"
```

---

### Task 4: Feed Sonnet body text, not raw HTML

`generate_sonnet_quality` and `generate_sonnet_specifics` currently receive `raw_html[:3000]` — mostly `<head>` boilerplate. Add an `extract_body_text()` helper and use it in the pipeline.

**Files:**
- Modify: `agents/src/improvement/scorer.py` (add helper at module level)
- Modify: `agents/src/improvement/pipeline.py` (Step 4 and Step 6 call sites)
- Test: `agents/tests/test_scorer.py`

- [ ] **Step 1: Write the failing test**

Add to `agents/tests/test_scorer.py`:

```python
from src.improvement.scorer import extract_body_text


class TestExtractBodyText:
    def test_strips_head_nav_and_scripts(self):
        html = """<html><head><title>T</title><style>.x{color:red}</style>
        <script>var a=1;</script></head>
        <body><nav>Menu Home About</nav>
        <p>Actual visible content about widgets.</p>
        <footer>Copyright</footer></body></html>"""
        text = extract_body_text(html)
        assert "Actual visible content about widgets." in text
        assert "var a=1" not in text
        assert "color:red" not in text
        assert "Menu Home About" not in text
        assert "Copyright" not in text

    def test_respects_max_chars(self):
        html = "<html><body><p>" + ("word " * 2000) + "</p></body></html>"
        assert len(extract_body_text(html, max_chars=500)) <= 500

    def test_empty_html_returns_empty_string(self):
        assert extract_body_text("") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents && .venv/bin/python -m pytest tests/test_scorer.py::TestExtractBodyText -v`
Expected: FAIL — `ImportError: cannot import name 'extract_body_text'`.

- [ ] **Step 3: Implement**

Add to `agents/src/improvement/scorer.py` (after the constants, before `check_answer_first`):

```python
def extract_body_text(html: str, max_chars: int = 3000) -> str:
    """Visible body text for LLM input — strips chrome, scripts, and styles."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body") or soup
    for tag in body.find_all(["nav", "footer", "header", "aside", "script", "style"]):
        tag.decompose()
    text = " ".join(body.get_text(separator=" ").split())
    return text[:max_chars]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agents && .venv/bin/python -m pytest tests/test_scorer.py -v`
Expected: all PASS.

- [ ] **Step 5: Use it in the pipeline**

In `agents/src/improvement/pipeline.py`:

Add import:
```python
from src.improvement.scorer import compute_structural_score, extract_body_text
```
(replacing the existing `compute_structural_score` import line)

In Step 4, replace the `sonnet_quality` call's first argument:
```python
            page_text = extract_body_text(page.get("raw_html", ""))
            sonnet_quality = generate_sonnet_quality(
                page_text,
                query_text,
                score_result["check_results"],
            )
```

In Step 6, replace the `generate_sonnet_specifics` first argument `page.get("raw_html", "")[:3000]` with:
```python
                page_text = extract_body_text(page.get("raw_html", ""))
                specifics = generate_sonnet_specifics(
                    page_text,
                    match["query"],
                    action["action_type"],
                    action["issue"],
                    gap_text,
                )
```
(Compute `page_text` once per page, above the `for action in actions:` loop, not per action.)

- [ ] **Step 6: Run the full suite and commit**

Run: `cd agents && .venv/bin/python -m pytest tests/ -q`
Expected: all PASS.

```bash
git add agents/src/improvement/scorer.py agents/src/improvement/pipeline.py agents/tests/test_scorer.py
git commit -m "fix: feed Sonnet extracted body text instead of raw HTML head boilerplate"
```

---

### Task 5: Dedupe action cards by (page, action_type)

Step 6 loops over matches, so a page matched by 3 queries gets 3 identical card sets (3× Sonnet cost, card spam). Group matches by page, pick the worst-gap query as primary, and generate one card set per page.

**Files:**
- Modify: `agents/src/improvement/pipeline.py` (Step 6, the first `for match in matches:` loop)
- Test: `agents/tests/test_improvement_pipeline.py`

- [ ] **Step 1: Write the failing test**

Add to `TestRunImprovementPipeline` (same decorator stack as Task 1's test):

```python
    def test_multiple_queries_matching_one_page_produce_one_card_set(
        self, mock_validate, mock_sonnet, mock_classify, mock_reddit,
        mock_gaps, mock_quality, mock_score, mock_match, mock_inv,
        mock_crawl, mock_sb,
    ):
        # setup identical to test_cards_get_db_ids_after_insert, EXCEPT:
        mock_match.return_value = [
            {"query": "q1", "query_id": "id1", "match_type": "matched",
             "matched_page_url": "https://x.com/p1", "similarity_score": 0.7, "bucket": "awareness"},
            {"query": "q2", "query_id": "id2", "match_type": "matched",
             "matched_page_url": "https://x.com/p1", "similarity_score": 0.6, "bucket": "awareness"},
            {"query": "q3", "query_id": "id3", "match_type": "matched",
             "matched_page_url": "https://x.com/p1", "similarity_score": 0.55, "bucket": "awareness"},
        ]
        mock_gaps.return_value = [
            {"query": "q1", "query_id": "id1", "competitive_gap": 0.0, "top_competitor": None,
             "client_mention_rate": 0.5, "competitor_mention_rate": 0.0},
            {"query": "q2", "query_id": "id2", "competitive_gap": 0.4, "top_competitor": "CompA",
             "client_mention_rate": 0.1, "competitor_mention_rate": 0.5},
            {"query": "q3", "query_id": "id3", "competitive_gap": 0.0, "top_competitor": None,
             "client_mention_rate": 0.5, "competitor_mention_rate": 0.0},
        ]
        # ... (rest of mocks identical to Task 1's test — one page, one classify action)

        result = run_improvement_pipeline(state, queries, competitive_gaps_data=[])

        # One card, not three — deduped by (page_url, action_type)
        assert len(result["action_cards"]) == 1
        card = result["action_cards"][0]
        # The card carries the worst-gap query as its primary
        assert card["query_id"] == "id2"
        assert card["priority"] == 1
        assert card["competitive_gap"] == 0.4
        # Sonnet specifics called once, not three times
        assert mock_sonnet.call_count == 1
```

(The executor writes out the full mock setup by copying Task 1's test body; `queries` becomes three entries with ids id1/id2/id3.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents && .venv/bin/python -m pytest tests/test_improvement_pipeline.py::TestRunImprovementPipeline::test_multiple_queries_matching_one_page_produce_one_card_set -v`
Expected: FAIL — 3 cards generated, `mock_sonnet.call_count == 3`.

- [ ] **Step 3: Implement**

In `agents/src/improvement/pipeline.py` Step 6, replace the first loop (`for match in matches:` ... automated cards) with:

```python
        gap_by_query = {g["query"]: g for g in gap_results}

        matches_by_page: dict[str, list[dict]] = {}
        for m in matches:
            if m["match_type"] == "matched" and m["matched_page_url"]:
                matches_by_page.setdefault(m["matched_page_url"], []).append(m)

        for page_url, page_matches in matches_by_page.items():
            score = score_by_url.get(page_url)
            if not score:
                continue

            def _gap_value(m: dict) -> float:
                g = gap_by_query.get(m["query"])
                return g["competitive_gap"] if g else 0.0

            primary = max(page_matches, key=_gap_value)
            gap_info = gap_by_query.get(primary["query"])
            has_gap = bool(gap_info and gap_info["competitive_gap"] > 0)

            actions = classify_actions(score, page_url)
            page = page_by_url.get(page_url, {})
            page_text = extract_body_text(page.get("raw_html", ""))

            for action in actions:
                gap_text = f"Competitor {gap_info['top_competitor']} has {gap_info['competitive_gap']:.0%} advantage" if has_gap and gap_info else "No competitive gap"

                specifics = generate_sonnet_specifics(
                    page_text,
                    primary["query"],
                    action["action_type"],
                    action["issue"],
                    gap_text,
                )

                validation_passed = True
                if action["action_type"] in ("generate_schema", "fix_schema", "add_faq_schema") and specifics.get("code_block"):
                    validation = validate_json_ld(specifics["code_block"])
                    validation_passed = validation["valid"]
                    if not validation_passed:
                        print(f"    Schema validation failed for {action['action_type']}: {validation['errors']}")
                        continue

                card = {
                    "run_id": run_id,
                    "client_id": client_id,
                    "query_id": primary.get("query_id"),
                    "page_url": page_url,
                    "pillar": action["action_type"],
                    "action_type": action["action_type"],
                    "track": "automated",
                    "priority": 1 if has_gap else 3,
                    "competitive_gap": gap_info["competitive_gap"] if gap_info else None,
                    "structural_score": score["structural_score"],
                    "score": score["structural_score"],
                    "issue": action["issue"],
                    "before_text": specifics.get("before_text", ""),
                    "after_text": specifics.get("after_text", ""),
                    "code_block": specifics.get("code_block", ""),
                    "validation_passed": validation_passed,
                    "status": "pending",
                    "cms_action": "copy_paste",
                }
                all_cards.append(card)
```

This subsumes Task 4's Step 6 call-site change — if Task 4 already edited that loop, this replaces it wholesale.

- [ ] **Step 4: Run the full pipeline test file**

Run: `cd agents && .venv/bin/python -m pytest tests/test_improvement_pipeline.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/src/improvement/pipeline.py agents/tests/test_improvement_pipeline.py
git commit -m "fix: dedupe action cards by page — one card set per page, not per query match"
```

---

### Task 6: Crawlability blockers become a priority-0 card

The spec's gate behavior (a critical blocker generates a high-priority card) was never implemented — blockers are buried in a jsonb column. Add `build_crawlability_card()` and emit it in the pipeline.

**Files:**
- Modify: `agents/src/improvement/card_generator.py`
- Modify: `agents/src/improvement/pipeline.py` (Step 6, before the automated-card loop)
- Test: `agents/tests/test_card_generator.py`

- [ ] **Step 1: Write the failing test**

Add to `agents/tests/test_card_generator.py`:

```python
from src.improvement.card_generator import build_crawlability_card


class TestBuildCrawlabilityCard:
    def test_lists_failing_critical_checks(self):
        report = {
            "robots_txt": {"status": "fail", "detail": "GPTBot disallowed in robots.txt"},
            "js_rendering": {"status": "pass"},
            "cdn_blocks": {"status": "fail", "detail": "403 for GPTBot user agent"},
            "has_critical_blocker": True,
        }
        card = build_crawlability_card(report, "example.com")
        assert card["action_type"] == "fix_crawlability"
        assert card["track"] == "manual"
        assert card["priority"] == 0
        assert card["status"] == "pending"
        assert card["page_url"] == "https://example.com"
        assert "GPTBot disallowed" in card["issue"]
        assert "403 for GPTBot" in card["issue"]

    def test_check_without_detail_falls_back_to_check_name(self):
        report = {
            "robots_txt": {"status": "fail"},
            "js_rendering": {"status": "pass"},
            "cdn_blocks": {"status": "pass"},
            "has_critical_blocker": True,
        }
        card = build_crawlability_card(report, "example.com")
        assert "robots_txt" in card["issue"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents && .venv/bin/python -m pytest tests/test_card_generator.py::TestBuildCrawlabilityCard -v`
Expected: FAIL — `ImportError: cannot import name 'build_crawlability_card'`.

- [ ] **Step 3: Implement**

Add to `agents/src/improvement/card_generator.py` (after `build_reddit_card`):

```python
CRITICAL_CRAWL_CHECKS = ("robots_txt", "js_rendering", "cdn_blocks")


def build_crawlability_card(crawl_report: dict, domain: str) -> dict:
    failing = [
        name for name in CRITICAL_CRAWL_CHECKS
        if crawl_report.get(name, {}).get("status") == "fail"
    ]
    details = "; ".join(
        crawl_report[name].get("detail") or name for name in failing
    )
    return {
        "page_url": f"https://{domain}",
        "action_type": "fix_crawlability",
        "track": "manual",
        "priority": 0,
        "competitive_gap": None,
        "issue": f"AI crawlers cannot access the site — every other action is blocked until fixed: {details}",
        "status": "pending",
        "cms_action": "none",
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agents && .venv/bin/python -m pytest tests/test_card_generator.py -v`
Expected: all PASS.

- [ ] **Step 5: Emit it in the pipeline**

In `agents/src/improvement/pipeline.py`:

Add `build_crawlability_card` to the `card_generator` import list.

At the start of Step 6 (right after `all_cards = []`):

```python
        if crawl_report.get("has_critical_blocker"):
            crawl_card = build_crawlability_card(crawl_report, domain)
            crawl_card["run_id"] = run_id
            crawl_card["client_id"] = client_id
            crawl_card["pillar"] = "crawlability"
            crawl_card["score"] = 0
            crawl_card["before_text"] = ""
            crawl_card["after_text"] = ""
            crawl_card["code_block"] = ""
            crawl_card["validation_passed"] = True
            all_cards.append(crawl_card)
```

`prioritize_cards` sorts ascending by priority, so priority 0 lands on top — no change needed there.

- [ ] **Step 6: Run full suite and commit**

Run: `cd agents && .venv/bin/python -m pytest tests/ -q`
Expected: all PASS.

```bash
git add agents/src/improvement/card_generator.py agents/src/improvement/pipeline.py agents/tests/test_card_generator.py
git commit -m "feat: surface critical crawlability blockers as priority-0 action cards"
```

---

### Task 7: Always fetch competitive gaps (fix improvement_only runs)

`run_improvement_pipeline_node` only loads gaps when `state["tracker_results"]` is non-empty, so `improvement_only` runs get no priorities, no briefs, no Reddit scout. The gaps live in the DB from the last tracker run — fetch them unconditionally.

**Files:**
- Modify: `agents/src/graph/nodes.py:127-141` (`run_improvement_pipeline_node`)
- Test: `agents/tests/test_graph_nodes.py`

- [ ] **Step 1: Write the failing test**

Read `agents/tests/test_graph_nodes.py` first and match its mocking style. Add:

```python
@patch("src.graph.nodes._get_supabase")
def test_improvement_node_fetches_gaps_without_tracker_results(mock_sb):
    """improvement_only runs (no tracker_results in state) must still load stored gaps."""
    mock_table = MagicMock()
    # queries select
    mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    # tracker_runs latest + competitive_gaps
    mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[{"id": "trun-1"}])
    mock_table.select.return_value.eq.return_value.execute.return_value = \
        MagicMock(data=[{"query": "q1", "client_mention_rate": 0.1, "competitor_data": []}])
    mock_sb.return_value.table.return_value = mock_table

    from src.graph.nodes import run_improvement_pipeline_node

    with patch("src.improvement.pipeline.run_improvement_pipeline") as mock_run:
        mock_run.return_value = {"improvement_run_id": "r1", "action_cards": []}
        state = {"client_id": "c1", "client_config": {"website_domain": "x.com"},
                 "tracker_results": []}   # improvement_only: tracker never ran
        run_improvement_pipeline_node(state)

        # Third positional arg = competitive_gaps, must be the stored rows, not []
        passed_gaps = mock_run.call_args[0][2]
        assert passed_gaps == [{"query": "q1", "client_mention_rate": 0.1, "competitor_data": []}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents && .venv/bin/python -m pytest tests/test_graph_nodes.py::test_improvement_node_fetches_gaps_without_tracker_results -v`
Expected: FAIL — `passed_gaps == []`.

- [ ] **Step 3: Implement**

In `agents/src/graph/nodes.py`, `run_improvement_pipeline_node`, delete the `if state.get("tracker_results"):` guard so the gap fetch always runs:

```python
    competitive_gaps = []
    latest_run = sb.table("tracker_runs") \
        .select("id") \
        .eq("client_id", state["client_id"]) \
        .order("ran_at", desc=True) \
        .limit(1) \
        .execute()
    if latest_run.data:
        run_id = latest_run.data[0]["id"]
        gaps_resp = sb.table("competitive_gaps") \
            .select("*") \
            .eq("run_id", run_id) \
            .execute()
        competitive_gaps = gaps_resp.data or []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agents && .venv/bin/python -m pytest tests/test_graph_nodes.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/src/graph/nodes.py agents/tests/test_graph_nodes.py
git commit -m "fix: improvement_only runs now load stored competitive gaps"
```

---

### Task 8: Migration 009 — agentic QA columns

**Files:**
- Create: `supabase/migrations/009_agentic_qa.sql`

- [ ] **Step 1: Write the migration**

```sql
-- 009_agentic_qa.sql
-- Columns for card QA, policy-based auto-approve, and post-implementation verification.

alter table public.action_cards
    add column if not exists auto_approved boolean default false,
    add column if not exists verification jsonb;

-- Per-client override/allowlist: action types the admin has explicitly cleared
-- for auto-approval (in addition to history-earned eligibility).
alter table public.clients
    add column if not exists auto_approve_action_types text[] default '{}';

create index if not exists idx_action_cards_auto_approved
    on public.action_cards(auto_approved) where auto_approved = true;
```

- [ ] **Step 2: Verify SQL is well-formed**

Run: `psql --version >/dev/null 2>&1 && echo ok` — if psql is unavailable locally, eyeball-check only; the migration is applied via the Supabase dashboard/CLI at deploy time like migrations 001–008 (follow whatever process was used for `008_improvement_pipeline.sql`).

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/009_agentic_qa.sql
git commit -m "feat: migration for auto-approve and verification columns"
```

---

### Task 9: Card QA self-review loop

Before a card surfaces: (a) programmatic grounding check — `before_text` must actually appear on the page; (b) Haiku judgment — is `after_text` specific to this page/query or generic filler? On failure, regenerate once; if it fails again, drop the card. Reduces human review load per card.

**Files:**
- Create: `agents/src/improvement/card_qa.py`
- Create: `agents/tests/test_card_qa.py`
- Modify: `agents/src/improvement/pipeline.py` (Step 6 automated-card loop)
- Modify: `agents/tests/test_improvement_pipeline.py` (patch `qa_card` in existing tests)

- [ ] **Step 1: Write the failing tests**

Create `agents/tests/test_card_qa.py`:

```python
from unittest.mock import patch
from src.improvement.card_qa import check_grounding, qa_card


class TestCheckGrounding:
    def test_before_text_present_on_page_passes(self):
        page_text = "Our widget service costs $50 per month and includes support."
        result = check_grounding("costs $50 per month", page_text)
        assert result["passed"] is True

    def test_before_text_absent_fails(self):
        result = check_grounding("this sentence is not on the page", "totally different page content here")
        assert result["passed"] is False
        assert "not found" in result["reason"].lower()

    def test_whitespace_and_case_normalized(self):
        page_text = "Our   Widget\nService costs $50."
        result = check_grounding("our widget service", page_text)
        assert result["passed"] is True

    def test_empty_or_none_before_text_skips_check(self):
        assert check_grounding("", "anything")["passed"] is True
        assert check_grounding("none", "anything")["passed"] is True


class TestQaCard:
    @patch("src.improvement.card_qa.haiku_review")
    def test_passes_when_grounded_and_haiku_approves(self, mock_haiku):
        mock_haiku.return_value = {"verdict": "pass", "reason": "specific"}
        card = {"action_type": "restructure_intro", "before_text": "old intro text",
                "after_text": "New specific intro answering the query.", "code_block": ""}
        result = qa_card(card, "page containing the old intro text somewhere")
        assert result["passed"] is True

    @patch("src.improvement.card_qa.haiku_review")
    def test_fails_on_ungrounded_before_text_without_calling_haiku(self, mock_haiku):
        card = {"action_type": "restructure_intro", "before_text": "hallucinated quote",
                "after_text": "whatever", "code_block": ""}
        result = qa_card(card, "page text that does not contain that quote")
        assert result["passed"] is False
        mock_haiku.assert_not_called()

    @patch("src.improvement.card_qa.haiku_review")
    def test_fails_when_haiku_rejects(self, mock_haiku):
        mock_haiku.return_value = {"verdict": "fail", "reason": "generic boilerplate"}
        card = {"action_type": "add_faq_schema", "before_text": "",
                "after_text": "", "code_block": '{"@type":"FAQPage"}'}
        result = qa_card(card, "any page text")
        assert result["passed"] is False
        assert "generic boilerplate" in result["reason"]

    @patch("src.improvement.card_qa.haiku_review")
    def test_fails_when_card_has_no_content_at_all(self, mock_haiku):
        card = {"action_type": "restructure_intro", "before_text": "",
                "after_text": "", "code_block": ""}
        result = qa_card(card, "page text")
        assert result["passed"] is False
        mock_haiku.assert_not_called()

    @patch("src.improvement.card_qa.haiku_review")
    def test_haiku_error_passes_open(self, mock_haiku):
        """QA is a filter, not a gate — if Haiku errors, let the card through to human review."""
        mock_haiku.return_value = {"verdict": "error", "reason": "api down"}
        card = {"action_type": "restructure_intro", "before_text": "",
                "after_text": "Some replacement text.", "code_block": ""}
        result = qa_card(card, "page text")
        assert result["passed"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd agents && .venv/bin/python -m pytest tests/test_card_qa.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.improvement.card_qa'`.

- [ ] **Step 3: Implement**

Create `agents/src/improvement/card_qa.py`:

```python
"""Card QA self-review — cheap validation pass before a card surfaces.

Two checks:
1. Grounding (free, programmatic): before_text must actually appear on the page.
2. Haiku judgment (~1 cheap call per card): is after_text specific to this
   page, or generic filler that could apply to any site?

Fail-open on API errors: QA reduces human review load, it must never block
the pipeline. A card that can't be QA'd goes to human review as normal.
"""

import os
import json
import re
import anthropic

HAIKU_MODEL = "claude-haiku-4-5-20251001"

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def check_grounding(before_text: str, page_text: str) -> dict:
    """Verify before_text is an actual quote from the page (whitespace/case-insensitive)."""
    if not before_text or before_text.strip().lower() == "none":
        return {"passed": True, "reason": "no before_text to check"}
    if _normalize(before_text) in _normalize(page_text):
        return {"passed": True, "reason": "before_text found on page"}
    return {"passed": False, "reason": "before_text not found on page — likely hallucinated"}


def haiku_review(card: dict) -> dict:
    """Ask Haiku whether the proposed change is specific and usable.

    Returns {"verdict": "pass" | "fail" | "error", "reason": str}.
    """
    prompt = f"""You are reviewing a proposed website change before it goes to a human approver.

ACTION TYPE: {card.get('action_type', '')}
PROPOSED REPLACEMENT TEXT:
{card.get('after_text', '')[:1500]}

PROPOSED CODE BLOCK:
{card.get('code_block', '')[:1500]}

Reject the change if ANY of these hold:
- The replacement text is generic filler that could apply to any website
- It contains placeholder tokens like [Brand], [X]%, TODO, lorem, "your company"
- It makes up specific statistics or facts with no plausible source
- It is empty or just restates the problem instead of fixing it

Return ONLY valid JSON: {{"verdict": "pass" or "fail", "reason": "one sentence"}}"""

    try:
        response = _get_client().messages.create(
            model=HAIKU_MODEL,
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                return {"verdict": "error", "reason": "unparseable Haiku response"}
            data = json.loads(match.group())
        verdict = data.get("verdict", "error")
        if verdict not in ("pass", "fail"):
            verdict = "error"
        return {"verdict": verdict, "reason": data.get("reason", "")}
    except Exception as e:
        print(f"  Card QA: Haiku review failed: {e}")
        return {"verdict": "error", "reason": str(e)}


def qa_card(card: dict, page_text: str) -> dict:
    """Full QA pass. Returns {"passed": bool, "reason": str}."""
    if not card.get("after_text") and not card.get("code_block"):
        return {"passed": False, "reason": "card has no replacement content"}

    grounding = check_grounding(card.get("before_text", ""), page_text)
    if not grounding["passed"]:
        return {"passed": False, "reason": grounding["reason"]}

    review = haiku_review(card)
    if review["verdict"] == "fail":
        return {"passed": False, "reason": review["reason"]}

    # pass or error → fail-open
    return {"passed": True, "reason": review["reason"]}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents && .venv/bin/python -m pytest tests/test_card_qa.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit the module**

```bash
git add agents/src/improvement/card_qa.py agents/tests/test_card_qa.py
git commit -m "feat: card QA module — grounding check + Haiku specificity review"
```

- [ ] **Step 6: Write the failing integration test**

Add to `TestRunImprovementPipeline` in `agents/tests/test_improvement_pipeline.py` (same decorator stack as Task 1's test, **plus** `@patch("src.improvement.pipeline.qa_card")` as the innermost decorator, so it becomes the first parameter):

```python
    def test_card_failing_qa_twice_is_dropped(
        self, mock_qa, mock_validate, mock_sonnet, mock_classify, mock_reddit,
        mock_gaps, mock_quality, mock_score, mock_match, mock_inv,
        mock_crawl, mock_sb,
    ):
        # setup identical to test_cards_get_db_ids_after_insert, plus:
        mock_qa.return_value = {"passed": False, "reason": "generic"}

        result = run_improvement_pipeline(state, queries, competitive_gaps_data=[])

        assert result["action_cards"] == []
        assert mock_sonnet.call_count == 2   # original + one regeneration
        assert mock_qa.call_count == 2       # QA'd both attempts

    def test_card_passing_qa_on_retry_is_kept(
        self, mock_qa, mock_validate, mock_sonnet, mock_classify, mock_reddit,
        mock_gaps, mock_quality, mock_score, mock_match, mock_inv,
        mock_crawl, mock_sb,
    ):
        mock_qa.side_effect = [
            {"passed": False, "reason": "generic"},
            {"passed": True, "reason": "ok"},
        ]

        result = run_improvement_pipeline(state, queries, competitive_gaps_data=[])

        assert len(result["action_cards"]) == 1
        assert mock_sonnet.call_count == 2
```

Also add `@patch("src.improvement.pipeline.qa_card")` (returning `{"passed": True, "reason": ""}`) to the **existing** tests in this class so they keep passing once the pipeline calls QA.

- [ ] **Step 7: Run to verify failure**

Run: `cd agents && .venv/bin/python -m pytest tests/test_improvement_pipeline.py -v`
Expected: new tests FAIL (`AttributeError` — pipeline has no `qa_card` to patch).

- [ ] **Step 8: Integrate into the pipeline**

In `agents/src/improvement/pipeline.py`:

Add import:
```python
from src.improvement.card_qa import qa_card
```

In the Step 6 automated-card loop (as restructured in Task 5), wrap generation in a QA-retry. Replace the block from `specifics = generate_sonnet_specifics(...)` through the validation check with:

```python
                specifics = None
                for attempt in range(2):
                    candidate = generate_sonnet_specifics(
                        page_text,
                        primary["query"],
                        action["action_type"],
                        action["issue"],
                        gap_text,
                    )
                    qa = qa_card(
                        {**candidate, "action_type": action["action_type"]},
                        page_text,
                    )
                    if qa["passed"]:
                        specifics = candidate
                        break
                    print(f"    QA failed ({action['action_type']}, attempt {attempt + 1}): {qa['reason']}")

                if specifics is None:
                    continue  # dropped — regeneration didn't fix it

                validation_passed = True
                if action["action_type"] in ("generate_schema", "fix_schema", "add_faq_schema") and specifics.get("code_block"):
                    validation = validate_json_ld(specifics["code_block"])
                    validation_passed = validation["valid"]
                    if not validation_passed:
                        print(f"    Schema validation failed for {action['action_type']}: {validation['errors']}")
                        continue
```

- [ ] **Step 9: Run full suite and commit**

Run: `cd agents && .venv/bin/python -m pytest tests/ -q`
Expected: all PASS.

```bash
git add agents/src/improvement/pipeline.py agents/tests/test_improvement_pipeline.py
git commit -m "feat: QA loop — regenerate once then drop cards that fail grounding/specificity"
```

---

### Task 10: Policy-based auto-approve

Schema-only changes that pass programmatic JSON-LD validation are near-zero-risk. A client earns auto-approval for an action type after `min_cycles` improvement runs in which every card of that type was approved/implemented and none rejected — or the admin sets it explicitly via `clients.auto_approve_action_types`. Auto-approved cards skip human review; if nothing is left pending, the graph skips `await_approval` entirely.

**Files:**
- Create: `agents/src/improvement/auto_approve.py`
- Create: `agents/tests/test_auto_approve.py`
- Modify: `agents/src/improvement/pipeline.py` (apply policy before insert)
- Modify: `agents/src/graph/nodes.py` (`load_config` passes the config column; `run_implementation_node` implements auto-approved cards)
- Modify: `agents/src/graph/pipeline.py` (conditional edge after improvement node)
- Test: `agents/tests/test_improvement_pipeline.py`, `agents/tests/test_graph_nodes.py`

- [ ] **Step 1: Write the failing tests**

Create `agents/tests/test_auto_approve.py`:

```python
from src.improvement.auto_approve import compute_eligible_action_types, apply_auto_approve


def _card(action_type, status, run_id, track="automated"):
    return {"action_type": action_type, "status": status, "run_id": run_id, "track": track}


class TestComputeEligibleActionTypes:
    def test_three_clean_cycles_earn_eligibility(self):
        history = [
            _card("add_faq_schema", "implemented", "r1"),
            _card("add_faq_schema", "approved", "r2"),
            _card("add_faq_schema", "implemented", "r3"),
        ]
        assert "add_faq_schema" in compute_eligible_action_types(history, min_cycles=3)

    def test_two_cycles_not_enough(self):
        history = [
            _card("add_faq_schema", "implemented", "r1"),
            _card("add_faq_schema", "implemented", "r2"),
        ]
        assert compute_eligible_action_types(history, min_cycles=3) == set()

    def test_any_rejection_ever_blocks_eligibility(self):
        history = [
            _card("fix_schema", "implemented", "r1"),
            _card("fix_schema", "rejected", "r2"),
            _card("fix_schema", "implemented", "r3"),
            _card("fix_schema", "implemented", "r4"),
        ]
        assert "fix_schema" not in compute_eligible_action_types(history, min_cycles=3)

    def test_pending_cards_do_not_count_as_clean_cycles(self):
        history = [
            _card("add_faq_schema", "implemented", "r1"),
            _card("add_faq_schema", "pending", "r2"),
            _card("add_faq_schema", "implemented", "r3"),
        ]
        assert "add_faq_schema" not in compute_eligible_action_types(history, min_cycles=3)

    def test_content_action_types_never_eligible_from_history(self):
        history = [_card("restructure_intro", "implemented", f"r{i}") for i in range(10)]
        assert "restructure_intro" not in compute_eligible_action_types(history, min_cycles=3)


class TestApplyAutoApprove:
    def test_eligible_valid_automated_card_gets_auto_approved(self):
        cards = [{"action_type": "add_faq_schema", "track": "automated",
                  "validation_passed": True, "status": "pending"}]
        n = apply_auto_approve(cards, {"add_faq_schema"})
        assert n == 1
        assert cards[0]["status"] == "approved"
        assert cards[0]["auto_approved"] is True

    def test_ineligible_type_stays_pending(self):
        cards = [{"action_type": "restructure_intro", "track": "automated",
                  "validation_passed": True, "status": "pending"}]
        assert apply_auto_approve(cards, {"add_faq_schema"}) == 0
        assert cards[0]["status"] == "pending"

    def test_failed_validation_never_auto_approved(self):
        cards = [{"action_type": "add_faq_schema", "track": "automated",
                  "validation_passed": False, "status": "pending"}]
        assert apply_auto_approve(cards, {"add_faq_schema"}) == 0

    def test_manual_track_never_auto_approved(self):
        cards = [{"action_type": "add_faq_schema", "track": "manual",
                  "validation_passed": True, "status": "pending"}]
        assert apply_auto_approve(cards, {"add_faq_schema"}) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd agents && .venv/bin/python -m pytest tests/test_auto_approve.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Create `agents/src/improvement/auto_approve.py`:

```python
"""Policy-based auto-approve for proven-safe action types.

Schema-only changes validated programmatically (JSON-LD parse + required
fields) carry near-zero risk. A client earns auto-approval for an action type
after `min_cycles` runs where every card of that type was approved or
implemented and none was ever rejected. Admins can also grant types explicitly
via clients.auto_approve_action_types.

Content-changing action types (intro rewrites, citations, freshness) are never
auto-approved from history — humans review anything that changes visible copy.
"""

from collections import defaultdict

# Only structurally-validatable, non-content action types can ever earn auto-approval.
HISTORY_ELIGIBLE_TYPES = {"add_faq_schema", "fix_schema", "generate_schema"}

RESOLVED_STATUSES = {"approved", "implemented"}


def compute_eligible_action_types(card_history: list[dict], min_cycles: int = 3) -> set[str]:
    """Earned eligibility from past automated cards for one client.

    A run counts as clean for an action type when every card of that type in
    the run resolved to approved/implemented. Any rejection ever disqualifies
    the type outright.
    """
    by_type_run: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    rejected_types: set[str] = set()

    for card in card_history:
        action_type = card.get("action_type", "")
        if action_type not in HISTORY_ELIGIBLE_TYPES:
            continue
        if card.get("track") != "automated":
            continue
        status = card.get("status", "")
        if status == "rejected":
            rejected_types.add(action_type)
        by_type_run[action_type][card.get("run_id", "")].append(status)

    eligible = set()
    for action_type, runs in by_type_run.items():
        if action_type in rejected_types:
            continue
        clean_runs = sum(
            1 for statuses in runs.values()
            if statuses and all(s in RESOLVED_STATUSES for s in statuses)
        )
        if clean_runs >= min_cycles:
            eligible.add(action_type)
    return eligible


def apply_auto_approve(cards: list[dict], eligible_types: set[str]) -> int:
    """Mark eligible cards approved in place. Returns count auto-approved."""
    count = 0
    for card in cards:
        if (
            card.get("track") == "automated"
            and card.get("action_type") in eligible_types
            and card.get("validation_passed")
            and card.get("status") == "pending"
        ):
            card["status"] = "approved"
            card["auto_approved"] = True
            count += 1
    return count
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents && .venv/bin/python -m pytest tests/test_auto_approve.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit the module**

```bash
git add agents/src/improvement/auto_approve.py agents/tests/test_auto_approve.py
git commit -m "feat: auto-approve policy — history-earned eligibility for schema-only actions"
```

- [ ] **Step 6: Integrate into pipeline + config**

In `agents/src/graph/nodes.py`, `load_config`, add to the `config` dict:

```python
        "auto_approve_action_types": row.get("auto_approve_action_types") or [],
```

In `agents/src/improvement/pipeline.py`:

Add import:
```python
from src.improvement.auto_approve import compute_eligible_action_types, apply_auto_approve
```

After `all_cards = prioritize_cards(all_cards)` and before the insert block:

```python
        history_resp = sb.table("action_cards") \
            .select("action_type, status, run_id, track") \
            .eq("client_id", client_id) \
            .execute()
        earned = compute_eligible_action_types(history_resp.data or [])
        configured = set(config.get("auto_approve_action_types") or [])
        eligible = earned | configured
        if eligible:
            n_auto = apply_auto_approve(all_cards, eligible)
            if n_auto:
                print(f"  Auto-approved {n_auto} card(s) — eligible types: {sorted(eligible)}")
```

Update existing pipeline tests: the extra `select().eq().execute()` on `action_cards` needs the generic mock chain — add to each test's setup:

```python
        mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
```

- [ ] **Step 7: Graph edge — skip approval when nothing is pending**

In `agents/src/graph/pipeline.py`, add after `route_after_gsc`:

```python
def route_after_improvement(state: GEOState) -> str:
    pending = [c for c in state.get("action_cards", []) if c.get("status") == "pending"]
    if pending:
        return "await_approval"
    return "run_implementation"
```

Replace `graph.add_edge("run_improvement_pipeline", "await_approval")` with:

```python
    graph.add_conditional_edges("run_improvement_pipeline", route_after_improvement, {
        "await_approval": "await_approval",
        "run_implementation": "run_implementation",
    })
```

In `agents/src/graph/nodes.py`, `run_implementation_node`, change the approval filter so auto-approved cards implement without human ids:

```python
    approved_ids = set(state.get("approved_card_ids") or [])
    for card in state["action_cards"]:
        card_id = card.get("id", "")
        if not (card.get("auto_approved") or card_id in approved_ids):
            continue
```

- [ ] **Step 8: Write graph-level test**

Add to `agents/tests/test_graph_nodes.py` (or a suitable existing graph test file — check `test_pipeline.py` for where routing tests live and match):

```python
def test_route_after_improvement_skips_approval_when_all_auto_approved():
    from src.graph.pipeline import route_after_improvement
    state = {"action_cards": [
        {"status": "approved", "auto_approved": True},
        {"status": "approved", "auto_approved": True},
    ]}
    assert route_after_improvement(state) == "run_implementation"


def test_route_after_improvement_awaits_when_pending_cards_exist():
    from src.graph.pipeline import route_after_improvement
    state = {"action_cards": [
        {"status": "approved", "auto_approved": True},
        {"status": "pending"},
    ]}
    assert route_after_improvement(state) == "await_approval"


def test_route_after_improvement_awaits_when_no_cards():
    """Zero cards → still pause; a silent full-auto run with nothing to show should not implement."""
    from src.graph.pipeline import route_after_improvement
    assert route_after_improvement({"action_cards": []}) == "await_approval"
```

Note the third test's intent: an empty card list routes to `await_approval` (pending list is empty, but so is everything). Adjust `route_after_improvement` accordingly:

```python
def route_after_improvement(state: GEOState) -> str:
    cards = state.get("action_cards", [])
    pending = [c for c in cards if c.get("status") == "pending"]
    auto_approved = [c for c in cards if c.get("auto_approved")]
    if auto_approved and not pending:
        return "run_implementation"
    return "await_approval"
```

- [ ] **Step 9: Run full suite and commit**

Run: `cd agents && .venv/bin/python -m pytest tests/ -q`
Expected: all PASS.

```bash
git add agents/src/graph/pipeline.py agents/src/graph/nodes.py agents/src/improvement/pipeline.py agents/tests/
git commit -m "feat: wire auto-approve into pipeline — skip human gate when everything auto-approved"
```

---

### Task 11: Post-implementation verification

After a card is actually published (`status == "implemented"`), re-fetch the page and confirm: the page still renders (200, has body+title), and the change is present (JSON-LD `@type` for schema cards, `after_text` substring for content cards). Result stored on the card's `verification` jsonb column. Closes the "did it actually go live?" trust gap.

**Files:**
- Create: `agents/src/improvement/verifier.py`
- Create: `agents/tests/test_verifier.py`
- Modify: `agents/src/graph/nodes.py` (`run_implementation_node`)
- Test: `agents/tests/test_graph_nodes.py`

- [ ] **Step 1: Write the failing tests**

Create `agents/tests/test_verifier.py`:

```python
from unittest.mock import patch, MagicMock
from src.improvement.verifier import verify_implementation


def _mock_response(status=200, html="<html><head><title>T</title></head><body><p>hello</p></body></html>"):
    resp = MagicMock()
    resp.status_code = status
    resp.text = html
    return resp


class TestVerifyImplementation:
    @patch("src.improvement.verifier.httpx.get")
    def test_schema_card_verified_when_type_present(self, mock_get):
        html = ('<html><head><title>T</title></head><body><p>x</p>'
                '<script type="application/ld+json">'
                '{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}'
                '</script></body></html>')
        mock_get.return_value = _mock_response(html=html)
        card = {"page_url": "https://x.com/p1", "action_type": "add_faq_schema",
                "code_block": '{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}',
                "after_text": ""}
        result = verify_implementation(card)
        assert result["verified"] is True
        assert result["checks"]["page_renders"] is True
        assert result["checks"]["change_present"] is True

    @patch("src.improvement.verifier.httpx.get")
    def test_schema_card_fails_when_type_absent(self, mock_get):
        mock_get.return_value = _mock_response()
        card = {"page_url": "https://x.com/p1", "action_type": "add_faq_schema",
                "code_block": '{"@type":"FAQPage"}', "after_text": ""}
        result = verify_implementation(card)
        assert result["verified"] is False
        assert result["checks"]["change_present"] is False

    @patch("src.improvement.verifier.httpx.get")
    def test_content_card_verified_by_after_text_substring(self, mock_get):
        mock_get.return_value = _mock_response(
            html="<html><head><title>T</title></head><body><p>Widgets cost $50 per month, including support.</p></body></html>")
        card = {"page_url": "https://x.com/p1", "action_type": "restructure_intro",
                "code_block": "", "after_text": "Widgets cost $50 per month"}
        result = verify_implementation(card)
        assert result["verified"] is True

    @patch("src.improvement.verifier.httpx.get")
    def test_http_error_reports_unverified_with_error(self, mock_get):
        mock_get.side_effect = Exception("connection refused")
        card = {"page_url": "https://x.com/p1", "action_type": "restructure_intro",
                "code_block": "", "after_text": "anything"}
        result = verify_implementation(card)
        assert result["verified"] is False
        assert "connection refused" in result["error"]

    @patch("src.improvement.verifier.httpx.get")
    def test_broken_page_fails_render_check(self, mock_get):
        mock_get.return_value = _mock_response(status=500, html="Internal Server Error")
        card = {"page_url": "https://x.com/p1", "action_type": "restructure_intro",
                "code_block": "", "after_text": "anything"}
        result = verify_implementation(card)
        assert result["verified"] is False
        assert result["checks"]["page_renders"] is False

    def test_card_without_page_url_is_skipped(self):
        card = {"page_url": None, "action_type": "content_brief", "code_block": "", "after_text": ""}
        result = verify_implementation(card)
        assert result["verified"] is False
        assert result["skipped"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd agents && .venv/bin/python -m pytest tests/test_verifier.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Create `agents/src/improvement/verifier.py`:

```python
"""Post-implementation verification — re-fetch the page after publishing and
confirm the change is live and nothing broke.

Checks:
- page_renders: HTTP < 400, response has <body> and <title>
- change_present: schema cards → a JSON-LD block with the card's @type exists;
  content cards → after_text (first 200 chars, normalized) appears in page text

The result is advisory: it's stored on the card for the dashboard, it never
rolls anything back on its own.
"""

import json
import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (compatible; VV-Verify/1.0)"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _extract_schema_types(soup: BeautifulSoup) -> set[str]:
    types: set[str] = set()
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        blocks = data if isinstance(data, list) else [data]
        for block in blocks:
            if not isinstance(block, dict):
                continue
            t = block.get("@type")
            if isinstance(t, list):
                types.update(t)
            elif t:
                types.add(t)
    return types


def verify_implementation(card: dict, timeout: float = 15.0) -> dict:
    """Verify one implemented card against the live page."""
    result = {
        "verified": False,
        "skipped": False,
        "checks": {"page_renders": False, "change_present": False},
        "error": None,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    url = card.get("page_url")
    if not url:
        result["skipped"] = True
        result["error"] = "card has no page_url"
        return result

    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True,
                         headers={"User-Agent": USER_AGENT})
    except Exception as e:
        result["error"] = str(e)
        return result

    soup = BeautifulSoup(resp.text, "html.parser")
    renders = resp.status_code < 400 and soup.find("body") is not None and soup.find("title") is not None
    result["checks"]["page_renders"] = renders

    change_present = False
    code_block = card.get("code_block") or ""
    after_text = card.get("after_text") or ""

    if code_block:
        try:
            expected = json.loads(code_block)
            expected_type = expected.get("@type") if isinstance(expected, dict) else None
        except json.JSONDecodeError:
            expected_type = None
        if expected_type:
            live_types = _extract_schema_types(soup)
            if isinstance(expected_type, list):
                change_present = any(t in live_types for t in expected_type)
            else:
                change_present = expected_type in live_types
    elif after_text:
        page_text = _normalize(soup.get_text(separator=" "))
        change_present = _normalize(after_text)[:200] in page_text

    result["checks"]["change_present"] = change_present
    result["verified"] = renders and change_present
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents && .venv/bin/python -m pytest tests/test_verifier.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit the module**

```bash
git add agents/src/improvement/verifier.py agents/tests/test_verifier.py
git commit -m "feat: post-implementation verifier — confirm changes are live on the page"
```

- [ ] **Step 6: Integrate into run_implementation_node**

In `agents/src/graph/nodes.py`, inside `run_implementation_node`'s per-card try block, after the status update:

```python
            result = route_card(card, cms_type, cms_config)
            result["card_id"] = card_id

            new_status = "implemented" if result.get("status") == "implemented" else "approved"

            verification = None
            if result.get("status") == "implemented":
                from src.improvement.verifier import verify_implementation
                verification = verify_implementation(card)
                result["verification"] = verification
                if verification["verified"]:
                    print(f"    Verified live: {card.get('page_url')}")
                else:
                    print(f"    NOT verified: {verification.get('error') or verification['checks']}")

            update_fields = {"status": new_status}
            if verification is not None:
                update_fields["verification"] = verification
            sb.table("action_cards").update(update_fields).eq("id", card_id).execute()
```

(This replaces the existing `sb.table("action_cards").update({"status": new_status})...` line.)

Note: `copy_paste` and draft-based flows return `status: "approved"`, not `"implemented"` — verification correctly only runs for actually-published changes.

- [ ] **Step 7: Write the failing node test, then verify**

Add to `agents/tests/test_graph_nodes.py`:

```python
@patch("src.improvement.verifier.verify_implementation")
@patch("src.implementors.router.route_card")
@patch("src.graph.nodes._get_supabase")
def test_implementation_node_verifies_implemented_cards(mock_sb, mock_route, mock_verify):
    mock_table = MagicMock()
    mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
    mock_sb.return_value.table.return_value = mock_table

    mock_route.return_value = {"status": "implemented"}
    mock_verify.return_value = {"verified": True, "skipped": False,
                                "checks": {"page_renders": True, "change_present": True},
                                "error": None, "checked_at": "2026-07-04T00:00:00Z"}

    from src.graph.nodes import run_implementation_node
    state = {
        "client_config": {"cms_type": "wordpress", "cms_config": {}},
        "action_cards": [{"id": "card-1", "page_url": "https://x.com/p1",
                          "action_type": "add_faq_schema", "code_block": "{}", "after_text": ""}],
        "approved_card_ids": ["card-1"],
    }
    result = run_implementation_node(state)

    mock_verify.assert_called_once()
    assert result["implementation_results"][0]["verification"]["verified"] is True
    # verification persisted to the card row
    update_payload = mock_table.update.call_args[0][0]
    assert "verification" in update_payload
```

Run: `cd agents && .venv/bin/python -m pytest tests/test_graph_nodes.py -v`
Expected: all PASS (if the test was written before Step 6, it fails first with `mock_verify.assert_called_once()` — either order is fine as long as failure was observed before implementation).

- [ ] **Step 8: Run the entire suite one final time and commit**

Run: `cd agents && .venv/bin/python -m pytest tests/ -q`
Expected: all PASS (230 original + ~25 new).

```bash
git add agents/src/graph/nodes.py agents/tests/test_graph_nodes.py
git commit -m "feat: verify implemented cards against the live page, persist result"
```

---

## Deployment checklist (manual, after merge)

1. Apply `supabase/migrations/009_agentic_qa.sql` via Supabase (same process as 008).
2. Set `DATABASE_URL` on Railway (Supabase session-mode connection string, port 5432) to activate the Postgres checkpointer.
3. Confirm Railway's start command runs `uvicorn server:app` — `Procfile`/`nixpacks.toml` currently point at the old `run.py` CLI worker.
4. First cycle after deploy: watch for `[Checkpointer] PostgresSaver enabled` and `Auto-approved N card(s)` log lines.

## Out of scope (separate plans)

- Frontend rebuild (approvals inbox with per-run grouping — fixes the `pipelineRuns[0]` wrong-thread bug — funnel view, ops board): next plan, after this backend work lands.
- Rejected-card persistence (dashboard sends only approvals): belongs to the frontend plan since the fix spans `ApprovalsClient` and the approve route.
- Preview-before-approval (spec Step 7 draft/staging flow), LangSmith `@traceable` step instrumentation, Reddit scout SERP API: deferred, tracked in the deferred-features list.
