from src.stability import aggregate_prompt_scores, compute_prompt_stability


class TestAggregatePromptScores:
    def test_single_run_single_engine(self):
        prompt_scores = [
            {"run_id": "r1", "query": "best tools", "llm": "chatgpt", "mention_rate": 0.8, "avg_mention_level": 2.5},
        ]
        runs = [{"id": "r1", "ran_at": "2026-07-01T00:00:00Z"}]
        result = aggregate_prompt_scores(prompt_scores, runs)

        assert len(result) == 1
        assert result[0]["run_id"] == "r1"
        assert result[0]["queries"]["best tools"]["mention_rate"] == 0.8
        assert result[0]["queries"]["best tools"]["avg_mention_level"] == 2.5

    def test_multi_engine_averaging(self):
        prompt_scores = [
            {"run_id": "r1", "query": "best tools", "llm": "chatgpt", "mention_rate": 0.8, "avg_mention_level": 3.0},
            {"run_id": "r1", "query": "best tools", "llm": "perplexity", "mention_rate": 0.6, "avg_mention_level": 2.0},
            {"run_id": "r1", "query": "best tools", "llm": "claude", "mention_rate": 1.0, "avg_mention_level": 4.0},
            {"run_id": "r1", "query": "best tools", "llm": "gemini", "mention_rate": 0.4, "avg_mention_level": 1.0},
        ]
        runs = [{"id": "r1", "ran_at": "2026-07-01T00:00:00Z"}]
        result = aggregate_prompt_scores(prompt_scores, runs)

        assert len(result) == 1
        q = result[0]["queries"]["best tools"]
        assert q["mention_rate"] == (0.8 + 0.6 + 1.0 + 0.4) / 4
        # Weighted avg level: (3.0*0.8 + 2.0*0.6 + 4.0*1.0 + 1.0*0.4) / (0.8+0.6+1.0+0.4)
        expected_level = (3.0 * 0.8 + 2.0 * 0.6 + 4.0 * 1.0 + 1.0 * 0.4) / (0.8 + 0.6 + 1.0 + 0.4)
        assert abs(q["avg_mention_level"] - expected_level) < 0.001

    def test_multi_run_ordering(self):
        prompt_scores = [
            {"run_id": "r1", "query": "q1", "llm": "chatgpt", "mention_rate": 0.2, "avg_mention_level": 1.0},
            {"run_id": "r2", "query": "q1", "llm": "chatgpt", "mention_rate": 0.5, "avg_mention_level": 2.0},
            {"run_id": "r3", "query": "q1", "llm": "chatgpt", "mention_rate": 0.8, "avg_mention_level": 3.0},
        ]
        runs = [
            {"id": "r1", "ran_at": "2026-06-29T00:00:00Z"},
            {"id": "r2", "ran_at": "2026-06-30T00:00:00Z"},
            {"id": "r3", "ran_at": "2026-07-01T00:00:00Z"},
        ]
        result = aggregate_prompt_scores(prompt_scores, runs)

        assert len(result) == 3
        assert result[0]["run_id"] == "r1"
        assert result[2]["run_id"] == "r3"

    def test_zero_mention_rate_level_ignored(self):
        prompt_scores = [
            {"run_id": "r1", "query": "q1", "llm": "chatgpt", "mention_rate": 0.0, "avg_mention_level": 0.0},
            {"run_id": "r1", "query": "q1", "llm": "perplexity", "mention_rate": 0.8, "avg_mention_level": 3.0},
        ]
        runs = [{"id": "r1", "ran_at": "2026-07-01T00:00:00Z"}]
        result = aggregate_prompt_scores(prompt_scores, runs)

        q = result[0]["queries"]["q1"]
        assert q["mention_rate"] == (0.0 + 0.8) / 2
        # Weighted: only perplexity contributes (chatgpt has 0 rate)
        assert q["avg_mention_level"] == 3.0


class TestComputePromptStability:
    def test_absent(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0, "avg_mention_level": 0}}},
            {"run_id": "r2", "ran_at": "t2", "queries": {"q1": {"mention_rate": 0, "avg_mention_level": 0}}},
            {"run_id": "r3", "ran_at": "t3", "queries": {"q1": {"mention_rate": 0, "avg_mention_level": 0}}},
        ]
        result = compute_prompt_stability(runs_data)
        assert len(result) == 1
        assert result[0]["query"] == "q1"
        assert result[0]["stability_class"] == "absent"

    def test_locked_in(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0.8, "avg_mention_level": 2.5}}},
            {"run_id": "r2", "ran_at": "t2", "queries": {"q1": {"mention_rate": 0.75, "avg_mention_level": 2.7}}},
            {"run_id": "r3", "ran_at": "t3", "queries": {"q1": {"mention_rate": 0.9, "avg_mention_level": 2.8}}},
        ]
        result = compute_prompt_stability(runs_data)
        assert result[0]["stability_class"] == "locked_in"

    def test_gaining_by_rate(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0.3, "avg_mention_level": 1.5}}},
            {"run_id": "r2", "ran_at": "t2", "queries": {"q1": {"mention_rate": 0.4, "avg_mention_level": 1.5}}},
            {"run_id": "r3", "ran_at": "t3", "queries": {"q1": {"mention_rate": 0.5, "avg_mention_level": 1.5}}},
        ]
        result = compute_prompt_stability(runs_data)
        assert result[0]["stability_class"] == "gaining"

    def test_gaining_by_level(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0.6, "avg_mention_level": 1.5}}},
            {"run_id": "r2", "ran_at": "t2", "queries": {"q1": {"mention_rate": 0.6, "avg_mention_level": 2.0}}},
            {"run_id": "r3", "ran_at": "t3", "queries": {"q1": {"mention_rate": 0.6, "avg_mention_level": 2.5}}},
        ]
        result = compute_prompt_stability(runs_data)
        assert result[0]["stability_class"] == "gaining"

    def test_declining_by_rate(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0.8, "avg_mention_level": 2.5}}},
            {"run_id": "r2", "ran_at": "t2", "queries": {"q1": {"mention_rate": 0.6, "avg_mention_level": 2.5}}},
            {"run_id": "r3", "ran_at": "t3", "queries": {"q1": {"mention_rate": 0.5, "avg_mention_level": 2.5}}},
        ]
        result = compute_prompt_stability(runs_data)
        assert result[0]["stability_class"] == "declining"

    def test_volatile(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0.8, "avg_mention_level": 3.0}}},
            {"run_id": "r2", "ran_at": "t2", "queries": {"q1": {"mention_rate": 0.2, "avg_mention_level": 1.0}}},
            {"run_id": "r3", "ran_at": "t3", "queries": {"q1": {"mention_rate": 0.7, "avg_mention_level": 2.5}}},
        ]
        result = compute_prompt_stability(runs_data)
        assert result[0]["stability_class"] == "volatile"

    def test_rate_wins_tiebreak(self):
        # Rate gaining (+0.2), level declining (-0.6) -> gaining (rate wins)
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0.4, "avg_mention_level": 3.0}}},
            {"run_id": "r2", "ran_at": "t2", "queries": {"q1": {"mention_rate": 0.5, "avg_mention_level": 2.5}}},
            {"run_id": "r3", "ran_at": "t3", "queries": {"q1": {"mention_rate": 0.6, "avg_mention_level": 2.4}}},
        ]
        result = compute_prompt_stability(runs_data)
        assert result[0]["stability_class"] == "gaining"

    def test_single_run_absent(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0, "avg_mention_level": 0}}},
        ]
        result = compute_prompt_stability(runs_data)
        assert result[0]["stability_class"] == "absent"

    def test_single_run_volatile(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0.5, "avg_mention_level": 2.0}}},
        ]
        result = compute_prompt_stability(runs_data)
        assert result[0]["stability_class"] == "volatile"

    def test_multiple_queries(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {
                "q1": {"mention_rate": 0.8, "avg_mention_level": 3.0},
                "q2": {"mention_rate": 0, "avg_mention_level": 0},
            }},
            {"run_id": "r2", "ran_at": "t2", "queries": {
                "q1": {"mention_rate": 0.85, "avg_mention_level": 3.1},
                "q2": {"mention_rate": 0, "avg_mention_level": 0},
            }},
            {"run_id": "r3", "ran_at": "t3", "queries": {
                "q1": {"mention_rate": 0.9, "avg_mention_level": 3.2},
                "q2": {"mention_rate": 0, "avg_mention_level": 0},
            }},
        ]
        result = compute_prompt_stability(runs_data)
        stability_map = {r["query"]: r["stability_class"] for r in result}
        assert stability_map["q1"] == "locked_in"
        assert stability_map["q2"] == "absent"

    def test_query_missing_from_earlier_run(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0.5, "avg_mention_level": 2.0}}},
            {"run_id": "r2", "ran_at": "t2", "queries": {
                "q1": {"mention_rate": 0.6, "avg_mention_level": 2.5},
                "q2": {"mention_rate": 0.8, "avg_mention_level": 3.0},
            }},
            {"run_id": "r3", "ran_at": "t3", "queries": {
                "q1": {"mention_rate": 0.7, "avg_mention_level": 3.0},
                "q2": {"mention_rate": 0.9, "avg_mention_level": 3.5},
            }},
        ]
        result = compute_prompt_stability(runs_data)
        stability_map = {r["query"]: r for r in result}
        assert "q1" in stability_map
        assert "q2" in stability_map
        # q2 only has 2 runs of data — treat missing run as 0/0
        assert stability_map["q2"]["stability_class"] == "gaining"

    def test_output_shape(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0.8, "avg_mention_level": 2.5}}},
            {"run_id": "r2", "ran_at": "t2", "queries": {"q1": {"mention_rate": 0.8, "avg_mention_level": 2.6}}},
            {"run_id": "r3", "ran_at": "t3", "queries": {"q1": {"mention_rate": 0.8, "avg_mention_level": 2.7}}},
        ]
        result = compute_prompt_stability(runs_data)
        item = result[0]
        assert "query" in item
        assert "stability_class" in item
        assert "current_mention_rate" in item
        assert "current_avg_level" in item
        assert "trend" in item
        assert len(item["trend"]) == 3
        assert "run_id" in item["trend"][0]
        assert "ran_at" in item["trend"][0]
        assert "mention_rate" in item["trend"][0]
        assert "avg_mention_level" in item["trend"][0]

    def test_empty_runs(self):
        result = compute_prompt_stability([])
        assert result == []
