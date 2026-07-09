import os
from collections import defaultdict
from datetime import datetime, timezone


def create_client():
    from supabase import create_client as sb_create

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")
    return sb_create(url, key)


def upload_run(
    client_id: str,
    results: list[dict],
    scores: dict,
    competitive_gaps: list[dict] | None = None,
) -> str | None:
    try:
        sb = create_client()
    except Exception as e:
        print(f"  Supabase upload skipped: {e}")
        return None

    try:
        run_row = {
            "client_id": client_id,
            "ran_at": datetime.now(timezone.utc).isoformat(),
            "aggregate_mention_rate": scores.get("aggregate_mention_rate", 0),
            "non_branded_mention_rate": scores.get("non_branded_mention_rate", scores.get("aggregate_mention_rate", 0)),
            "aggregate_avg_mention_level": scores.get("aggregate_avg_mention_level", 0),
            "bucket_scores": scores.get("bucket_scores", {}),
            "per_engine_scores": scores.get("per_engine", {}),
            "competitor_scores": scores.get("competitor_scores", {}),
        }

        run_resp = sb.from_("tracker_runs").insert(run_row).execute()
        run_id = run_resp.data[0]["id"]

        result_rows = []
        for r in results:
            result_rows.append({
                "run_id": run_id,
                "query": r["query"],
                "query_id": r.get("query_id"),
                "bucket": r.get("bucket", "consideration"),
                "engine": r["engine"],
                "model": r.get("model", ""),
                "brand_mentioned": r.get("brand_mentioned", False),
                "brand_cited": r.get("brand_cited", False),
                "citation_url": r.get("citation_url", ""),
                "competitor_mentions": r.get("competitor_mentions", []),
                "response_text": r.get("response_text", ""),
                "queried_at": r.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "run_number": r.get("run_number"),
                "mention_level": r.get("mention_level", 0),
                "mention_level_label": r.get("mention_level_label", "not_mentioned"),
            })

        if result_rows:
            sb.from_("tracker_results").insert(result_rows).execute()

        prompt_scores = _compute_prompt_scores(client_id, run_id, results)
        if prompt_scores:
            sb.from_("prompt_scores").insert(prompt_scores).execute()

        gap_rows = _build_competitive_gap_rows(client_id, run_id, competitive_gaps or [])
        if gap_rows:
            sb.from_("competitive_gaps").insert(gap_rows).execute()

        print(f"  Uploaded to Supabase: run {run_id} ({len(result_rows)} results, {len(prompt_scores)} prompt scores, {len(gap_rows)} gaps)")
        return run_id

    except Exception as e:
        print(f"  Supabase upload failed: {e}")
        return None


def _compute_prompt_scores(client_id: str, run_id: str, results: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for r in results:
        groups[(r["query"], r["engine"])].append(r)

    scores = []
    for (query, engine), runs in groups.items():
        total = len(runs)
        mentions = [r for r in runs if r.get("brand_mentioned")]
        mention_count = len(mentions)

        mention_rate = mention_count / total if total > 0 else 0
        avg_level = (
            sum(r.get("mention_level", 0) for r in mentions) / mention_count
            if mention_count > 0 else 0
        )
        citation_rate = (
            sum(1 for r in mentions if r.get("brand_cited")) / mention_count
            if mention_count > 0 else 0
        )

        scores.append({
            "run_id": run_id,
            "client_id": client_id,
            "query_id": runs[0].get("query_id"),
            "query": query,
            "bucket": runs[0].get("bucket", "consideration"),
            "llm": engine,
            "mention_rate": mention_rate,
            "avg_mention_level": avg_level,
            "citation_rate": citation_rate,
        })

    return scores


def _build_competitive_gap_rows(client_id: str, run_id: str, gaps: list[dict]) -> list[dict]:
    rows = []
    for gap in gaps:
        rows.append({
            "run_id": run_id,
            "client_id": client_id,
            "query_id": gap.get("query_id"),
            "query": gap["query"],
            "bucket": gap.get("bucket", "consideration"),
            "client_mention_rate": gap["client_mention_rate"],
            "client_avg_mention_level": gap["client_avg_mention_level"],
            "competitor_data": gap["competitor_data"],
        })
    return rows
