def aggregate_prompt_scores(prompt_scores: list[dict], runs: list[dict]) -> list[dict]:
    by_run_query: dict[str, dict[str, list[dict]]] = {}
    for ps in prompt_scores:
        rid = ps["run_id"]
        q = ps["query"]
        by_run_query.setdefault(rid, {}).setdefault(q, []).append(ps)

    result = []
    for run in runs:
        rid = run["id"]
        queries = {}
        for query, scores in by_run_query.get(rid, {}).items():
            n = len(scores)
            avg_rate = sum(s["mention_rate"] for s in scores) / n if n > 0 else 0

            total_weight = sum(s["mention_rate"] for s in scores)
            if total_weight > 0:
                avg_level = round(
                    sum(s["avg_mention_level"] * s["mention_rate"] for s in scores) / total_weight,
                    10,
                )
            else:
                avg_level = 0

            queries[query] = {
                "mention_rate": avg_rate,
                "avg_mention_level": avg_level,
            }

        result.append({
            "run_id": rid,
            "ran_at": run["ran_at"],
            "queries": queries,
        })

    return result


def _classify(rates: list[float], levels: list[float]) -> str:
    n = len(rates)

    if all(r == 0 for r in rates):
        return "absent"

    if n >= 3 and all(r >= 0.7 for r in rates):
        level_range = max(levels) - min(levels)
        if level_range <= 0.5:
            return "locked_in"

    if n >= 3:
        rate_diffs = [rates[i + 1] - rates[i] for i in range(n - 1)]
        signs = [1 if d > 0 else (-1 if d < 0 else 0) for d in rate_diffs]
        nonzero_signs = [s for s in signs if s != 0]
        if len(set(nonzero_signs)) > 1:
            return "volatile"

    if n >= 2:
        rate_delta = rates[-1] - rates[0]
        level_delta = levels[-1] - levels[0]

        rate_gaining = rate_delta >= 0.1
        rate_declining = rate_delta <= -0.1
        level_gaining = level_delta >= 0.5
        level_declining = level_delta <= -0.5

        if rate_gaining or (not rate_declining and level_gaining):
            return "gaining"

        if rate_declining or (not rate_gaining and level_declining):
            return "declining"

    return "volatile"


def compute_prompt_stability(runs_data: list[dict]) -> list[dict]:
    if not runs_data:
        return []

    all_queries: set[str] = set()
    for run in runs_data:
        all_queries.update(run["queries"].keys())

    result = []
    for query in sorted(all_queries):
        rates = []
        levels = []
        trend = []

        for run in runs_data:
            q_data = run["queries"].get(query, {"mention_rate": 0, "avg_mention_level": 0})
            rates.append(q_data["mention_rate"])
            levels.append(q_data["avg_mention_level"])
            trend.append({
                "run_id": run["run_id"],
                "ran_at": run["ran_at"],
                "mention_rate": q_data["mention_rate"],
                "avg_mention_level": q_data["avg_mention_level"],
            })

        stability_class = _classify(rates, levels)

        result.append({
            "query": query,
            "stability_class": stability_class,
            "current_mention_rate": rates[-1],
            "current_avg_level": levels[-1],
            "trend": trend,
        })

    return result
