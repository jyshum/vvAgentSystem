from src.tracker import compute_scores


def _make_result(engine, mentioned, cited, mention_level, run_number):
    return {
        "query": "test query",
        "engine": engine,
        "model": "test-model",
        "response_text": "response",
        "brand_mentioned": mentioned,
        "brand_cited": cited,
        "citation_url": "https://example.com" if cited else None,
        "mention_level": mention_level,
        "mention_level_label": {0: "not_mentioned", 1: "passing_mention", 2: "listed_with_context", 3: "recommended", 4: "primary_recommendation"}[mention_level],
        "competitor_mentions": [],
        "run_number": run_number,
        "timestamp": "2026-07-01T00:00:00Z",
    }


class TestComputeScoresNewFormat:
    def test_mention_rate_across_runs(self):
        results = [
            _make_result("chatgpt", True, False, 3, 1),
            _make_result("chatgpt", True, False, 1, 2),
            _make_result("chatgpt", False, False, 0, 3),
            _make_result("chatgpt", True, False, 2, 4),
            _make_result("chatgpt", True, False, 3, 5),
        ]
        engines = {"chatgpt": {"query": None, "model": "test"}}
        scores = compute_scores(results, engines)
        assert scores["aggregate_mention_rate"] == 4 / 5

    def test_avg_mention_level_excludes_zeros(self):
        results = [
            _make_result("chatgpt", True, False, 3, 1),
            _make_result("chatgpt", True, False, 1, 2),
            _make_result("chatgpt", False, False, 0, 3),
            _make_result("chatgpt", True, False, 2, 4),
            _make_result("chatgpt", True, False, 3, 5),
        ]
        engines = {"chatgpt": {"query": None, "model": "test"}}
        scores = compute_scores(results, engines)
        assert scores["aggregate_avg_mention_level"] == (3 + 1 + 2 + 3) / 4

    def test_per_engine_citation_rate_based_on_mentioned_runs(self):
        results = [
            _make_result("chatgpt", True, True, 3, 1),
            _make_result("chatgpt", True, False, 2, 2),
            _make_result("chatgpt", False, False, 0, 3),
            _make_result("chatgpt", True, False, 1, 4),
            _make_result("chatgpt", True, True, 3, 5),
        ]
        engines = {"chatgpt": {"query": None, "model": "test"}}
        scores = compute_scores(results, engines)
        assert scores["per_engine"]["chatgpt"]["citation_rate"] == 2 / 4

    def test_per_engine_has_avg_mention_level(self):
        results = [
            _make_result("chatgpt", True, False, 3, 1),
            _make_result("chatgpt", True, False, 1, 2),
        ]
        engines = {"chatgpt": {"query": None, "model": "test"}}
        scores = compute_scores(results, engines)
        assert scores["per_engine"]["chatgpt"]["avg_mention_level"] == 2.0

    def test_no_mentions_produces_zero_avg_level(self):
        results = [
            _make_result("chatgpt", False, False, 0, 1),
            _make_result("chatgpt", False, False, 0, 2),
        ]
        engines = {"chatgpt": {"query": None, "model": "test"}}
        scores = compute_scores(results, engines)
        assert scores["aggregate_avg_mention_level"] == 0
        assert scores["per_engine"]["chatgpt"]["avg_mention_level"] == 0

    def test_competitor_scores_unchanged(self):
        results = [
            {**_make_result("chatgpt", True, False, 3, 1), "competitor_mentions": ["CompA"]},
            {**_make_result("chatgpt", False, False, 0, 2), "competitor_mentions": []},
        ]
        engines = {"chatgpt": {"query": None, "model": "test"}}
        scores = compute_scores(results, engines, competitors=["CompA"])
        assert scores["competitor_scores"]["CompA"]["mention_rate"] == 0.5
