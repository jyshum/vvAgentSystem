from unittest.mock import patch

from src.upload import _compute_prompt_scores
from src.tracker import compute_competitive_gaps, compute_scores, run_tracker


def _fake_engines():
    # Two engines; each returns a canned string containing the wording so we can
    # assert which wordings were fired.
    def make(name):
        return {"model": f"{name}-model", "query": lambda w, n=name: f"[{n}] answer to: {w}"}
    return {"chatgpt": make("chatgpt"), "claude": make("claude")}


def test_run_tracker_fires_canonical_plus_paraphrases_and_skips_branded():
    config = {
        "target_queries": [
            {"id": "i1", "prompt_text": "best daycare software", "bucket": "awareness",
             "paraphrases": ["top childcare apps", "daycare management tools"]},
            {"id": "i2", "prompt_text": "brightwheel reviews", "bucket": "branded",
             "paraphrases": ["is brightwheel good"]},
        ],
        "brand_variations": ["Acme"],
        "website_domain": "acme.com",
        "competitors": [],
        "runs_per_paraphrase": 1,
    }
    with patch("src.tracker.load_engines", return_value=_fake_engines()):
        results, scores = run_tracker(config)

    # Awareness intent: (1 canonical + 2 paraphrases) x 2 engines = 6 samples
    awareness = [r for r in results if r["query_id"] == "i1"]
    assert len(awareness) == 6
    fired_wordings = {r["query"] for r in awareness}
    assert fired_wordings == {"best daycare software", "top childcare apps", "daycare management tools"}
    # every awareness sample carries the canonical + bucket
    assert all(r["intent_prompt"] == "best daycare software" for r in awareness)
    assert all(r["bucket"] == "awareness" for r in awareness)
    # branded intent is NOT fired at all
    assert [r for r in results if r["query_id"] == "i2"] == []


def _sample(query_id, bucket, engine, mentioned, level=0, cited=False, comps=None):
    return {
        "query_id": query_id, "intent_prompt": query_id, "query": query_id,
        "bucket": bucket, "engine": engine,
        "brand_mentioned": mentioned, "brand_cited": cited, "mention_level": level,
        "competitor_mentions": comps or [],
    }


def test_compute_scores_intent_level_and_non_branded():
    engines = {"chatgpt": {}, "claude": {}}
    results = [
        # intent A (awareness): 4 samples, 2 mentioned (levels 2 and 4), 1 of them cited
        _sample("A", "awareness", "chatgpt", True, level=2, cited=True),
        _sample("A", "awareness", "chatgpt", False),
        _sample("A", "awareness", "claude", True, level=4, cited=False),
        _sample("A", "awareness", "claude", False),
        # intent B (consideration): 2 samples, both mentioned (levels 1,3), none cited
        _sample("B", "consideration", "chatgpt", True, level=1),
        _sample("B", "consideration", "claude", True, level=3),
        # intent C (branded): must be ignored entirely
        _sample("C", "branded", "chatgpt", True, level=4, cited=True),
    ]
    s = compute_scores(results, engines, competitors=[])

    # A mention_rate = 2/4 = 0.5 ; B = 2/2 = 1.0 ; headline = mean(0.5, 1.0) = 0.75
    assert s["aggregate_mention_rate"] == 0.75
    assert s["non_branded_mention_rate"] == 0.75
    # avg level pooled over mentioned non-branded samples: levels [2,4,1,3] -> 2.5
    assert s["aggregate_avg_mention_level"] == 2.5
    # citation pooled: 1 cited of 4 mentioned = 0.25
    assert s["aggregate_citation_rate"] == 0.25
    # buckets
    assert s["bucket_scores"]["awareness"]["mention_rate"] == 0.5
    assert s["bucket_scores"]["consideration"]["mention_rate"] == 1.0
    assert s["bucket_scores"]["awareness"]["intent_count"] == 1
    # branded bucket present but contributes nothing to headline
    assert s["bucket_scores"]["branded"]["intent_count"] == 1
    # per-engine excludes branded; chatgpt sees A(1/2) and B(1/1) -> mean = 0.75
    assert s["per_engine"]["chatgpt"]["mention_rate"] == 0.75


def test_compute_scores_competitors_non_branded_only():
    engines = {"chatgpt": {}}
    results = [
        _sample("A", "awareness", "chatgpt", False, comps=["KinderCare"]),
        _sample("A", "awareness", "chatgpt", False, comps=[]),
        _sample("C", "branded", "chatgpt", True, comps=["KinderCare"]),  # ignored
    ]
    s = compute_scores(results, engines, competitors=["KinderCare"])
    # 1 of 2 non-branded samples mention KinderCare
    assert s["competitor_scores"]["KinderCare"]["mention_rate"] == 0.5


def test_compute_scores_empty():
    s = compute_scores([], {"chatgpt": {}}, competitors=[])
    assert s["aggregate_mention_rate"] == 0
    assert s["bucket_scores"]["awareness"]["intent_count"] == 0


def test_prompt_scores_keyed_by_intent():
    results = [
        {"query_id": "i1", "intent_prompt": "best daycare software", "query": "best daycare software",
         "bucket": "awareness", "engine": "chatgpt", "brand_mentioned": True, "brand_cited": True, "mention_level": 3},
        {"query_id": "i1", "intent_prompt": "best daycare software", "query": "top childcare apps",
         "bucket": "awareness", "engine": "chatgpt", "brand_mentioned": False, "brand_cited": False, "mention_level": 0},
    ]
    rows = _compute_prompt_scores("client-1", "run-1", results)
    assert len(rows) == 1
    row = rows[0]
    assert row["query_id"] == "i1"
    assert row["query"] == "best daycare software"
    assert row["bucket"] == "awareness"
    assert row["llm"] == "chatgpt"
    assert row["mention_rate"] == 0.5
    assert row["citation_rate"] == 1.0


def test_prompt_scores_legacy_rows_keep_query_id_null():
    results = [
        {"intent_prompt": "legacy query", "query": "legacy query",
         "bucket": "consideration", "engine": "chatgpt", "brand_mentioned": True,
         "brand_cited": False, "mention_level": 2},
        {"intent_prompt": "legacy query", "query": "legacy query rephrased",
         "bucket": "consideration", "engine": "chatgpt", "brand_mentioned": False,
         "brand_cited": False, "mention_level": 0},
    ]
    rows = _compute_prompt_scores("client-1", "run-1", results)
    assert len(rows) == 1
    row = rows[0]
    assert row["query_id"] is None
    assert row["query"] == "legacy query"
    assert row["mention_rate"] == 0.5


def test_competitive_gaps_grouped_by_intent():
    results = [
        {"query_id": "i1", "intent_prompt": "best daycare software", "query": "best daycare software",
         "bucket": "consideration", "engine": "chatgpt", "brand_mentioned": True, "mention_level": 2,
         "competitor_mentions": ["KinderCare"]},
        {"query_id": "i1", "intent_prompt": "best daycare software", "query": "top childcare apps",
         "bucket": "consideration", "engine": "chatgpt", "brand_mentioned": False, "mention_level": 0,
         "competitor_mentions": ["KinderCare"]},
    ]
    gaps = compute_competitive_gaps(results, ["KinderCare"])
    assert len(gaps) == 1
    g = gaps[0]
    assert g["query"] == "best daycare software"
    assert g["query_id"] == "i1"
    assert g["bucket"] == "consideration"
    assert g["client_mention_rate"] == 0.5
    assert g["competitor_data"][0]["name"] == "KinderCare"
    assert g["competitor_data"][0]["mention_rate"] == 1.0
