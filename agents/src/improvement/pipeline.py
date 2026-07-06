import os
from datetime import datetime, timezone

from src.improvement.crawlability import run_crawlability_gate
from src.improvement.inventory import build_inventory
from src.improvement.matcher import match_queries_to_pages
from src.improvement.scorer import compute_structural_score, extract_body_text
from src.improvement.gap_check import check_competitive_gaps
from src.improvement.reddit_scout import run_reddit_scout
from src.improvement.card_generator import (
    classify_actions,
    build_content_brief,
    build_crawlability_card,
    build_reddit_card,
    generate_sonnet_specifics,
    generate_sonnet_quality,
    prioritize_cards,
)
from src.improvement.validators import validate_json_ld


def _get_supabase():
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def run_improvement_pipeline(
    state: dict,
    queries: list[dict],
    competitive_gaps_data: list[dict] | None = None,
) -> dict:
    config = state["client_config"]
    domain = config["website_domain"]
    client_id = state["client_id"]
    brand_name = config.get("brand_name", "")
    competitors = config.get("competitors", [])

    sb = _get_supabase()

    run_resp = sb.table("improvement_runs").insert({
        "client_id": client_id,
        "status": "running",
    }).execute()
    run_id = run_resp.data[0]["id"]

    try:
        print("  Step 1: Crawlability gate...")
        crawl_report = run_crawlability_gate(domain)

        print("  Step 2: Site inventory...")
        inventory = build_inventory(domain, max_pages=config.get("audit_max_pages", 20))

        if inventory:
            inv_rows = [{
                "run_id": run_id,
                "url": p["url"],
                "title": p["title"],
                "h1": p["h1"],
                "first_paragraph": p["first_paragraph"],
                "schema_types": p["schema_types"],
                "word_count": p["word_count"],
                "last_modified": p.get("last_modified"),
                "outbound_link_count": p["outbound_link_count"],
                "has_faq_schema": p["has_faq_schema"],
                "has_comparison_table": p["has_comparison_table"],
            } for p in inventory]
            sb.table("page_inventory").insert(inv_rows).execute()

        print("  Step 3: Query-page matching...")
        query_dicts = [{"query": q["prompt_text"], "query_id": q["id"], "bucket": q.get("bucket", "")} for q in queries]
        matches = match_queries_to_pages(inventory, query_dicts)

        if matches:
            match_rows = [{
                "run_id": run_id,
                "query_id": m["query_id"],
                "query_text": m["query"],
                "match_type": m["match_type"],
                "matched_page_url": m.get("matched_page_url"),
                "similarity_score": m["similarity_score"],
                "bucket": m.get("bucket"),
            } for m in matches]
            sb.table("query_page_matches").insert(match_rows).execute()

        print("  Step 4: Citation-readiness scoring...")
        matched_pages = {m["matched_page_url"] for m in matches if m["match_type"] == "matched" and m["matched_page_url"]}
        page_by_url = {p["url"]: p for p in inventory}

        citation_scores = []
        for page_url in matched_pages:
            page = page_by_url.get(page_url)
            if not page:
                continue

            score_result = compute_structural_score(
                page.get("raw_html", ""),
                domain,
                page.get("last_modified"),
            )

            matched_queries = [m["query"] for m in matches if m["matched_page_url"] == page_url]
            query_text = matched_queries[0] if matched_queries else ""
            page_text = extract_body_text(page.get("raw_html", ""))
            sonnet_quality = generate_sonnet_quality(
                page_text,
                query_text,
                score_result["check_results"],
            )

            score_entry = {
                "url": page_url,
                **score_result,
                "sonnet_quality": sonnet_quality,
            }
            citation_scores.append(score_entry)

            sb.table("page_citation_scores").insert({
                "run_id": run_id,
                "page_url": page_url,
                "structural_score": score_result["structural_score"],
                "check_results": score_result["check_results"],
                "sonnet_quality": sonnet_quality,
                "schema_status": score_result["schema_status"],
                "schema_errors": score_result.get("schema_errors", []),
            }).execute()

        print("  Step 5: Competitive gap check...")
        gap_results = check_competitive_gaps(matches, competitive_gaps_data or [])

        print("  Step 5b: Reddit scout...")
        gap_queries = [g for g in gap_results if g["competitive_gap"] > 0]
        reddit_data = run_reddit_scout(gap_queries, brand_name, competitors) if gap_queries else []

        print("  Step 6: Generating action cards...")
        all_cards = []

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

        score_by_url = {s["url"]: s for s in citation_scores}

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

        for match in matches:
            if match["match_type"] != "content_gap":
                continue

            gap_info = next((g for g in gap_results if g["query"] == match["query"]), None)
            if gap_info and gap_info["competitive_gap"] > 0:
                brief = build_content_brief(
                    query=match["query"],
                    query_id=match["query_id"],
                    competitive_gap=gap_info["competitive_gap"],
                    top_competitor=gap_info["top_competitor"],
                )
                brief["run_id"] = run_id
                brief["client_id"] = client_id
                brief["pillar"] = "content_gap"
                brief["score"] = 0
                brief["before_text"] = ""
                brief["after_text"] = ""
                brief["code_block"] = ""
                brief["validation_passed"] = True
                all_cards.append(brief)

        reddit_by_query = {r["query"]: r for r in reddit_data}
        for gap in gap_queries:
            scout = reddit_by_query.get(gap["query"])
            if scout and scout["threads_found"] > 0:
                reddit_card = build_reddit_card(gap["query"], scout)
                reddit_card["run_id"] = run_id
                reddit_card["client_id"] = client_id
                reddit_card["query_id"] = gap.get("query_id")
                reddit_card["pillar"] = "reddit"
                reddit_card["score"] = 0
                reddit_card["before_text"] = ""
                reddit_card["after_text"] = ""
                reddit_card["code_block"] = ""
                reddit_card["validation_passed"] = True
                all_cards.append(reddit_card)

        all_cards = prioritize_cards(all_cards)

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
            if len(inserted_rows) != len(all_cards):
                print(f"  Warning: inserted {len(inserted_rows)} card rows but generated {len(all_cards)} cards — some cards will lack ids")
            # Assumes PostgREST returns inserted rows in submission order,
            # so positional zip pairing attaches the right id to each card.
            for card, row in zip(all_cards, inserted_rows):
                card["id"] = row.get("id")

        content_gaps = sum(1 for m in matches if m["match_type"] == "content_gap")
        comp_gaps = sum(1 for g in gap_results if g["competitive_gap"] > 0)

        sb.table("improvement_runs").update({
            "status": "completed",
            "crawlability_report": crawl_report,
            "pages_inventoried": len(inventory),
            "queries_matched": sum(1 for m in matches if m["match_type"] == "matched"),
            "content_gaps_found": content_gaps,
            "competitive_gaps_found": comp_gaps,
            "cards_generated": len(all_cards),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", run_id).execute()

        print(f"  Pipeline complete: {len(inventory)} pages, {len(matches)} matches, {len(all_cards)} cards")

        return {
            "improvement_run_id": run_id,
            "crawlability_report": crawl_report,
            "page_inventory": [{k: v for k, v in p.items() if k != "raw_html"} for p in inventory],
            "query_matches": matches,
            "citation_scores": citation_scores,
            "competitive_gap_data": gap_results,
            "reddit_scout_data": reddit_data,
            "action_cards": all_cards,
        }

    except Exception as e:
        sb.table("improvement_runs").update({
            "status": "error",
            "error_message": str(e)[:500],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", run_id).execute()
        raise
