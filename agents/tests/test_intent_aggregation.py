from unittest.mock import patch

from src.tracker import run_tracker


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
