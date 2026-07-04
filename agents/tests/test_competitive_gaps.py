# agents/tests/test_competitive_gaps.py
from src.tracker import compute_competitive_gaps


def _make_result(query, engine, competitor_mentions, brand_mentioned=False, mention_level=0, run_number=1):
    return {
        "query": query,
        "engine": engine,
        "model": "test-model",
        "response_text": "response",
        "brand_mentioned": brand_mentioned,
        "brand_cited": False,
        "citation_url": None,
        "mention_level": mention_level,
        "mention_level_label": {0: "not_mentioned", 1: "passing_mention", 2: "listed_with_context", 3: "recommended", 4: "primary_recommendation"}[mention_level],
        "competitor_mentions": competitor_mentions,
        "run_number": run_number,
        "timestamp": "2026-07-01T00:00:00Z",
    }


class TestComputeCompetitiveGaps:
    def test_single_query_single_engine(self):
        results = [
            _make_result("best tools", "chatgpt", ["CompA", "CompB"], brand_mentioned=True, mention_level=3, run_number=1),
            _make_result("best tools", "chatgpt", ["CompA"], brand_mentioned=True, mention_level=2, run_number=2),
            _make_result("best tools", "chatgpt", ["CompB"], brand_mentioned=False, mention_level=0, run_number=3),
            _make_result("best tools", "chatgpt", [], brand_mentioned=True, mention_level=1, run_number=4),
            _make_result("best tools", "chatgpt", ["CompA"], brand_mentioned=True, mention_level=3, run_number=5),
        ]
        competitors = ["CompA", "CompB"]
        gaps = compute_competitive_gaps(results, competitors)

        assert len(gaps) == 1
        gap = gaps[0]
        assert gap["query"] == "best tools"
        assert gap["client_mention_rate"] == 4 / 5
        assert gap["client_avg_mention_level"] == (3 + 2 + 1 + 3) / 4

        comp_map = {c["name"]: c for c in gap["competitor_data"]}
        assert comp_map["CompA"]["mention_rate"] == 3 / 5
        assert comp_map["CompA"]["per_engine"]["chatgpt"] == 3 / 5
        assert comp_map["CompB"]["mention_rate"] == 2 / 5
        assert comp_map["CompB"]["per_engine"]["chatgpt"] == 2 / 5

    def test_multi_engine_aggregation(self):
        results = [
            _make_result("q1", "chatgpt", ["CompA"], brand_mentioned=True, mention_level=3, run_number=1),
            _make_result("q1", "chatgpt", ["CompA"], brand_mentioned=False, mention_level=0, run_number=2),
            _make_result("q1", "perplexity", ["CompA"], brand_mentioned=True, mention_level=2, run_number=1),
            _make_result("q1", "perplexity", [], brand_mentioned=True, mention_level=1, run_number=2),
        ]
        competitors = ["CompA"]
        gaps = compute_competitive_gaps(results, competitors)

        assert len(gaps) == 1
        gap = gaps[0]
        assert gap["client_mention_rate"] == 3 / 4
        comp = gap["competitor_data"][0]
        assert comp["name"] == "CompA"
        assert comp["mention_rate"] == 3 / 4
        assert comp["per_engine"]["chatgpt"] == 2 / 2
        assert comp["per_engine"]["perplexity"] == 1 / 2

    def test_competitor_absent_from_query(self):
        results = [
            _make_result("q1", "chatgpt", [], brand_mentioned=True, mention_level=3, run_number=1),
            _make_result("q1", "chatgpt", [], brand_mentioned=True, mention_level=2, run_number=2),
        ]
        competitors = ["CompA"]
        gaps = compute_competitive_gaps(results, competitors)

        assert len(gaps) == 1
        comp = gaps[0]["competitor_data"][0]
        assert comp["name"] == "CompA"
        assert comp["mention_rate"] == 0

    def test_multiple_queries(self):
        results = [
            _make_result("q1", "chatgpt", ["CompA"], brand_mentioned=True, mention_level=3, run_number=1),
            _make_result("q1", "chatgpt", [], brand_mentioned=False, mention_level=0, run_number=2),
            _make_result("q2", "chatgpt", [], brand_mentioned=True, mention_level=2, run_number=1),
            _make_result("q2", "chatgpt", ["CompA"], brand_mentioned=False, mention_level=0, run_number=2),
        ]
        competitors = ["CompA"]
        gaps = compute_competitive_gaps(results, competitors)

        assert len(gaps) == 2
        gap_map = {g["query"]: g for g in gaps}
        assert gap_map["q1"]["client_mention_rate"] == 1 / 2
        assert gap_map["q1"]["competitor_data"][0]["mention_rate"] == 1 / 2
        assert gap_map["q2"]["client_mention_rate"] == 1 / 2
        assert gap_map["q2"]["competitor_data"][0]["mention_rate"] == 1 / 2

    def test_empty_results(self):
        gaps = compute_competitive_gaps([], ["CompA"])
        assert gaps == []

    def test_no_competitors_configured(self):
        results = [
            _make_result("q1", "chatgpt", [], brand_mentioned=True, mention_level=3, run_number=1),
        ]
        gaps = compute_competitive_gaps(results, [])
        assert len(gaps) == 1
        assert gaps[0]["competitor_data"] == []
