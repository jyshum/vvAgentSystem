from unittest.mock import patch, MagicMock

import pytest
from src.improvement.pipeline import run_improvement_pipeline


class TestRunImprovementPipeline:
    @patch("src.improvement.pipeline._get_supabase")
    @patch("src.improvement.pipeline.run_crawlability_gate")
    @patch("src.improvement.pipeline.build_inventory")
    @patch("src.improvement.pipeline.match_queries_to_pages")
    @patch("src.improvement.pipeline.compute_structural_score")
    @patch("src.improvement.pipeline.generate_sonnet_quality")
    @patch("src.improvement.pipeline.check_competitive_gaps")
    @patch("src.improvement.pipeline.classify_actions")
    @patch("src.improvement.pipeline.generate_sonnet_specifics")
    @patch("src.improvement.pipeline.validate_json_ld")
    @patch("src.improvement.pipeline.qa_card")
    def test_returns_expected_state_keys(
        self, mock_qa, mock_validate, mock_sonnet, mock_classify,
        mock_gaps, mock_quality, mock_score, mock_match, mock_inv,
        mock_crawl, mock_sb,
    ):
        mock_qa.return_value = {"passed": True, "reason": ""}
        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "run-123"}])
        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_sb.return_value.table.return_value = mock_table

        mock_crawl.return_value = {"has_critical_blocker": False, "robots_txt": {"status": "pass"}}
        mock_inv.return_value = [
            {"url": "https://x.com/p1", "title": "Page 1", "h1": "H1", "first_paragraph": "text",
             "raw_html": "<html></html>", "last_modified": None, "word_count": 500,
             "outbound_link_count": 0, "has_faq_schema": False, "has_comparison_table": False, "schema_types": []},
        ]
        mock_match.return_value = [
            {"query": "q1", "query_id": "id1", "match_type": "matched",
             "matched_page_url": "https://x.com/p1", "similarity_score": 0.7, "bucket": "awareness"},
        ]
        mock_score.return_value = {"structural_score": 60, "check_results": {}, "schema_status": "missing", "schema_errors": []}
        mock_quality.return_value = {"specificity": 3, "completeness": 3, "answer_directness": 3, "summary": "OK"}
        mock_gaps.return_value = [{"query": "q1", "query_id": "id1", "competitive_gap": 0.2,
                                   "top_competitor": "CompA", "client_mention_rate": 0.3, "competitor_mention_rate": 0.5}]
        mock_classify.return_value = [{"action_type": "generate_schema", "page_url": "https://x.com/p1", "issue": "No schema"}]
        mock_sonnet.return_value = {"before_text": "", "after_text": "", "code_block": '{"@context":"https://schema.org","@type":"Organization","name":"X"}'}
        mock_validate.return_value = {"valid": True, "errors": []}

        state = {
            "client_id": "client-1",
            "client_config": {
                "website_domain": "x.com",
                "brand_name": "BrandX",
                "competitors": ["CompA"],
            },
            "tracker_results": [],
        }
        queries = [{"id": "id1", "prompt_text": "q1", "bucket": "awareness"}]

        result = run_improvement_pipeline(state, queries, competitive_gaps_data=[
            {"query": "q1", "client_mention_rate": 0.3, "competitor_data": [{"name": "CompA", "mention_rate": 0.5}]}
        ])

        assert "improvement_run_id" in result
        assert "crawlability_report" in result
        assert "page_inventory" in result
        assert "query_matches" in result
        assert "citation_scores" in result
        assert "action_cards" in result
        assert result["improvement_run_id"] == "run-123"

    @patch("src.improvement.pipeline._get_supabase")
    @patch("src.improvement.pipeline.run_crawlability_gate")
    @patch("src.improvement.pipeline.build_inventory")
    @patch("src.improvement.pipeline.match_queries_to_pages")
    @patch("src.improvement.pipeline.compute_structural_score")
    @patch("src.improvement.pipeline.generate_sonnet_quality")
    @patch("src.improvement.pipeline.check_competitive_gaps")
    @patch("src.improvement.pipeline.classify_actions")
    @patch("src.improvement.pipeline.generate_sonnet_specifics")
    @patch("src.improvement.pipeline.validate_json_ld")
    @patch("src.improvement.pipeline.qa_card")
    def test_improvement_run_insert_includes_thread_id(
        self, mock_qa, mock_validate, mock_sonnet, mock_classify,
        mock_gaps, mock_quality, mock_score, mock_match, mock_inv,
        mock_crawl, mock_sb,
    ):
        """improvement_runs insert must carry the pipeline thread_id so the
        approvals inbox and run-detail page can join back to the originating thread."""
        mock_qa.return_value = {"passed": True, "reason": ""}
        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "run-123"}])
        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_sb.return_value.table.return_value = mock_table

        mock_crawl.return_value = {"has_critical_blocker": False}
        mock_inv.return_value = []
        mock_match.return_value = []
        mock_gaps.return_value = []

        state = {"client_id": "client-1",
                 "client_config": {"website_domain": "x.com", "brand_name": "BrandX", "competitors": []},
                 "tracker_results": [],
                 "thread_id": "client-20260707-000000"}
        queries = []

        run_improvement_pipeline(state, queries, competitive_gaps_data=[])

        insert_calls = mock_table.insert.call_args_list
        run_insert_payload = insert_calls[0][0][0]
        assert run_insert_payload["thread_id"] == "client-20260707-000000"

    @patch("src.improvement.pipeline._get_supabase")
    @patch("src.improvement.pipeline.run_crawlability_gate")
    @patch("src.improvement.pipeline.build_inventory")
    @patch("src.improvement.pipeline.match_queries_to_pages")
    @patch("src.improvement.pipeline.compute_structural_score")
    @patch("src.improvement.pipeline.generate_sonnet_quality")
    @patch("src.improvement.pipeline.check_competitive_gaps")
    @patch("src.improvement.pipeline.classify_actions")
    @patch("src.improvement.pipeline.generate_sonnet_specifics")
    @patch("src.improvement.pipeline.validate_json_ld")
    @patch("src.improvement.pipeline.qa_card")
    def test_cards_get_db_ids_after_insert(
        self, mock_qa, mock_validate, mock_sonnet, mock_classify,
        mock_gaps, mock_quality, mock_score, mock_match, mock_inv,
        mock_crawl, mock_sb,
    ):
        mock_qa.return_value = {"passed": True, "reason": ""}
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

    @patch("src.improvement.pipeline._get_supabase")
    @patch("src.improvement.pipeline.run_crawlability_gate")
    @patch("src.improvement.pipeline.build_inventory")
    @patch("src.improvement.pipeline.match_queries_to_pages")
    @patch("src.improvement.pipeline.compute_structural_score")
    @patch("src.improvement.pipeline.generate_sonnet_quality")
    @patch("src.improvement.pipeline.check_competitive_gaps")
    @patch("src.improvement.pipeline.classify_actions")
    @patch("src.improvement.pipeline.generate_sonnet_specifics")
    @patch("src.improvement.pipeline.validate_json_ld")
    @patch("src.improvement.pipeline.qa_card")
    def test_multiple_queries_matching_one_page_produce_one_card_set(
        self, mock_qa, mock_validate, mock_sonnet, mock_classify,
        mock_gaps, mock_quality, mock_score, mock_match, mock_inv,
        mock_crawl, mock_sb,
    ):
        mock_qa.return_value = {"passed": True, "reason": ""}
        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "card-uuid-1"}])
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
            {"query": "q2", "query_id": "id2", "match_type": "matched",
             "matched_page_url": "https://x.com/p1", "similarity_score": 0.6, "bucket": "awareness"},
            {"query": "q3", "query_id": "id3", "match_type": "matched",
             "matched_page_url": "https://x.com/p1", "similarity_score": 0.55, "bucket": "awareness"},
        ]
        mock_score.return_value = {"structural_score": 60, "check_results": {}, "schema_status": "missing", "schema_errors": []}
        mock_quality.return_value = {"specificity": 3, "completeness": 3, "answer_directness": 3, "summary": "OK"}
        mock_gaps.return_value = [
            {"query": "q1", "query_id": "id1", "competitive_gap": 0.0, "top_competitor": None,
             "client_mention_rate": 0.5, "competitor_mention_rate": 0.0},
            {"query": "q2", "query_id": "id2", "competitive_gap": 0.4, "top_competitor": "CompA",
             "client_mention_rate": 0.1, "competitor_mention_rate": 0.5},
            {"query": "q3", "query_id": "id3", "competitive_gap": 0.0, "top_competitor": None,
             "client_mention_rate": 0.5, "competitor_mention_rate": 0.0},
        ]
        mock_classify.return_value = [{"action_type": "generate_schema", "page_url": "https://x.com/p1", "issue": "No schema"}]
        mock_sonnet.return_value = {"before_text": "", "after_text": "", "code_block": '{"@context":"https://schema.org","@type":"Organization","name":"X"}'}
        mock_validate.return_value = {"valid": True, "errors": []}

        state = {"client_id": "client-1",
                 "client_config": {"website_domain": "x.com", "brand_name": "BrandX", "competitors": []},
                 "tracker_results": []}
        queries = [
            {"id": "id1", "prompt_text": "q1", "bucket": "awareness"},
            {"id": "id2", "prompt_text": "q2", "bucket": "awareness"},
            {"id": "id3", "prompt_text": "q3", "bucket": "awareness"},
        ]

        result = run_improvement_pipeline(state, queries, competitive_gaps_data=[])

        # One automated card, not three — deduped by (page_url, action_type) —
        # plus one manual community-check card for the losing query (q2, gap>0).
        assert len(result["action_cards"]) == 2
        automated = [c for c in result["action_cards"] if c["track"] == "automated"][0]
        # The card carries the worst-gap query as its primary
        assert automated["query_id"] == "id2"
        assert automated["priority"] == 1
        assert automated["competitive_gap"] == 0.4
        # Sonnet specifics called once, not three times
        assert mock_sonnet.call_count == 1

        community = [c for c in result["action_cards"] if c["action_type"] == "community_check"][0]
        assert community["query_id"] == "id2"

    @patch("src.improvement.pipeline._get_supabase")
    @patch("src.improvement.pipeline.run_crawlability_gate")
    @patch("src.improvement.pipeline.build_inventory")
    @patch("src.improvement.pipeline.match_queries_to_pages")
    @patch("src.improvement.pipeline.compute_structural_score")
    @patch("src.improvement.pipeline.generate_sonnet_quality")
    @patch("src.improvement.pipeline.check_competitive_gaps")
    @patch("src.improvement.pipeline.classify_actions")
    @patch("src.improvement.pipeline.generate_sonnet_specifics")
    @patch("src.improvement.pipeline.validate_json_ld")
    @patch("src.improvement.pipeline.qa_card")
    def test_card_failing_qa_twice_is_dropped(
        self, mock_qa, mock_validate, mock_sonnet, mock_classify,
        mock_gaps, mock_quality, mock_score, mock_match, mock_inv,
        mock_crawl, mock_sb,
    ):
        mock_qa.return_value = {"passed": False, "reason": "generic"}
        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "run-123"}])
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
        mock_classify.return_value = [{"action_type": "generate_schema", "page_url": "https://x.com/p1", "issue": "No schema"}]
        mock_sonnet.return_value = {"before_text": "", "after_text": "", "code_block": '{"@context":"https://schema.org","@type":"Organization","name":"X"}'}
        mock_validate.return_value = {"valid": True, "errors": []}

        state = {"client_id": "client-1",
                 "client_config": {"website_domain": "x.com", "brand_name": "BrandX", "competitors": []},
                 "tracker_results": []}
        queries = [{"id": "id1", "prompt_text": "q1", "bucket": "awareness"}]

        result = run_improvement_pipeline(state, queries, competitive_gaps_data=[])

        assert result["action_cards"] == []
        assert mock_sonnet.call_count == 2   # original + one regeneration
        assert mock_qa.call_count == 2       # QA'd both attempts

    @patch("src.improvement.pipeline._get_supabase")
    @patch("src.improvement.pipeline.run_crawlability_gate")
    @patch("src.improvement.pipeline.build_inventory")
    @patch("src.improvement.pipeline.match_queries_to_pages")
    @patch("src.improvement.pipeline.compute_structural_score")
    @patch("src.improvement.pipeline.generate_sonnet_quality")
    @patch("src.improvement.pipeline.check_competitive_gaps")
    @patch("src.improvement.pipeline.classify_actions")
    @patch("src.improvement.pipeline.generate_sonnet_specifics")
    @patch("src.improvement.pipeline.validate_json_ld")
    @patch("src.improvement.pipeline.qa_card")
    def test_api_failure_marks_run_error_and_raises(
        self, mock_qa, mock_validate, mock_sonnet, mock_classify,
        mock_gaps, mock_quality, mock_score, mock_match, mock_inv,
        mock_crawl, mock_sb,
    ):
        from src.improvement.card_generator import CardGenerationError

        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "run-123"}])
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
        mock_quality.side_effect = CardGenerationError("card model call failed: 404 not_found_error")

        state = {"client_id": "client-1",
                 "client_config": {"website_domain": "x.com", "brand_name": "BrandX", "competitors": []},
                 "tracker_results": []}
        queries = [{"id": "id1", "prompt_text": "q1", "bucket": "awareness"}]

        import pytest
        with pytest.raises(CardGenerationError):
            run_improvement_pipeline(state, queries, competitive_gaps_data=[])

        error_updates = [
            c.args[0] for c in mock_table.update.call_args_list
            if c.args and c.args[0].get("status") == "error"
        ]
        assert error_updates, "improvement_runs was never marked as error"
        assert "404 not_found_error" in error_updates[0]["error_message"]

    @patch("src.improvement.pipeline._get_supabase")
    @patch("src.improvement.pipeline.run_crawlability_gate")
    @patch("src.improvement.pipeline.build_inventory")
    @patch("src.improvement.pipeline.match_queries_to_pages")
    @patch("src.improvement.pipeline.compute_structural_score")
    @patch("src.improvement.pipeline.generate_sonnet_quality")
    @patch("src.improvement.pipeline.check_competitive_gaps")
    @patch("src.improvement.pipeline.classify_actions")
    @patch("src.improvement.pipeline.generate_sonnet_specifics")
    @patch("src.improvement.pipeline.validate_json_ld")
    @patch("src.improvement.pipeline.qa_card")
    def test_card_passing_qa_on_retry_is_kept(
        self, mock_qa, mock_validate, mock_sonnet, mock_classify,
        mock_gaps, mock_quality, mock_score, mock_match, mock_inv,
        mock_crawl, mock_sb,
    ):
        mock_qa.side_effect = [
            {"passed": False, "reason": "generic"},
            {"passed": True, "reason": "ok"},
        ]
        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "card-uuid-1"}])
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
        mock_classify.return_value = [{"action_type": "generate_schema", "page_url": "https://x.com/p1", "issue": "No schema"}]
        mock_sonnet.return_value = {"before_text": "", "after_text": "", "code_block": '{"@context":"https://schema.org","@type":"Organization","name":"X"}'}
        mock_validate.return_value = {"valid": True, "errors": []}

        state = {"client_id": "client-1",
                 "client_config": {"website_domain": "x.com", "brand_name": "BrandX", "competitors": []},
                 "tracker_results": []}
        queries = [{"id": "id1", "prompt_text": "q1", "bucket": "awareness"}]

        result = run_improvement_pipeline(state, queries, competitive_gaps_data=[])

        assert len(result["action_cards"]) == 1
        assert mock_sonnet.call_count == 2

    @patch("src.improvement.pipeline._get_supabase")
    @patch("src.improvement.pipeline.run_crawlability_gate")
    @patch("src.improvement.pipeline.build_inventory")
    @patch("src.improvement.pipeline.match_queries_to_pages")
    @patch("src.improvement.pipeline.compute_structural_score")
    @patch("src.improvement.pipeline.generate_sonnet_quality")
    @patch("src.improvement.pipeline.check_competitive_gaps")
    @patch("src.improvement.pipeline.classify_actions")
    @patch("src.improvement.pipeline.generate_sonnet_specifics")
    @patch("src.improvement.pipeline.validate_json_ld")
    @patch("src.improvement.pipeline.qa_card")
    def test_card_auto_approved_after_three_clean_history_cycles(
        self, mock_qa, mock_validate, mock_sonnet, mock_classify,
        mock_gaps, mock_quality, mock_score, mock_match, mock_inv,
        mock_crawl, mock_sb,
    ):
        mock_qa.return_value = {"passed": True, "reason": ""}
        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "card-uuid-1"}])
        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
        history_rows = [
            {"action_type": "generate_schema", "status": "implemented", "run_id": "r1", "track": "automated"},
            {"action_type": "generate_schema", "status": "approved", "run_id": "r2", "track": "automated"},
            {"action_type": "generate_schema", "status": "implemented", "run_id": "r3", "track": "automated"},
        ]
        mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=history_rows)
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
        mock_classify.return_value = [{"action_type": "generate_schema", "page_url": "https://x.com/p1", "issue": "No schema"}]
        mock_sonnet.return_value = {"before_text": "", "after_text": "", "code_block": '{"@context":"https://schema.org","@type":"Organization","name":"X"}'}
        mock_validate.return_value = {"valid": True, "errors": []}

        state = {"client_id": "client-1",
                 "client_config": {"website_domain": "x.com", "brand_name": "BrandX", "competitors": []},
                 "tracker_results": []}
        queries = [{"id": "id1", "prompt_text": "q1", "bucket": "awareness"}]

        result = run_improvement_pipeline(state, queries, competitive_gaps_data=[])

        assert len(result["action_cards"]) == 1
        card = result["action_cards"][0]
        assert card["action_type"] == "generate_schema"
        assert card["status"] == "approved"
        assert card["auto_approved"] is True

    @patch("src.improvement.pipeline._get_supabase")
    @patch("src.improvement.pipeline.run_crawlability_gate")
    @patch("src.improvement.pipeline.build_inventory")
    @patch("src.improvement.pipeline.match_queries_to_pages")
    @patch("src.improvement.pipeline.compute_structural_score")
    @patch("src.improvement.pipeline.generate_sonnet_quality")
    @patch("src.improvement.pipeline.check_competitive_gaps")
    @patch("src.improvement.pipeline.classify_actions")
    @patch("src.improvement.pipeline.generate_sonnet_specifics")
    @patch("src.improvement.pipeline.validate_json_ld")
    @patch("src.improvement.pipeline.qa_card")
    def test_configured_allowlist_bounded_to_schema_safe_types(
        self, mock_qa, mock_validate, mock_sonnet, mock_classify,
        mock_gaps, mock_quality, mock_score, mock_match, mock_inv,
        mock_crawl, mock_sb,
    ):
        """Admin allowlist can never auto-approve content-changing types."""
        mock_qa.return_value = {"passed": True, "reason": ""}
        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "card-uuid-1"}, {"id": "card-uuid-2"}])
        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
        # No history — eligibility comes only from the configured allowlist
        mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
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
        mock_classify.return_value = [
            {"action_type": "add_faq_schema", "page_url": "https://x.com/p1", "issue": "No FAQ schema"},
            {"action_type": "restructure_intro", "page_url": "https://x.com/p1", "issue": "Weak intro"},
        ]
        mock_sonnet.return_value = {"before_text": "", "after_text": "", "code_block": '{"@context":"https://schema.org","@type":"FAQPage"}'}
        mock_validate.return_value = {"valid": True, "errors": []}

        state = {"client_id": "client-1",
                 "client_config": {"website_domain": "x.com", "brand_name": "BrandX", "competitors": [],
                                   # Misconfigured: admin included a content-changing type
                                   "auto_approve_action_types": ["restructure_intro", "add_faq_schema"]},
                 "tracker_results": []}
        queries = [{"id": "id1", "prompt_text": "q1", "bucket": "awareness"}]

        result = run_improvement_pipeline(state, queries, competitive_gaps_data=[])

        cards_by_type = {c["action_type"]: c for c in result["action_cards"]}
        # Schema-safe configured type still auto-approves
        assert cards_by_type["add_faq_schema"]["status"] == "approved"
        assert cards_by_type["add_faq_schema"]["auto_approved"] is True
        # Content-changing type is ignored despite being in the allowlist
        assert cards_by_type["restructure_intro"]["status"] == "pending"
        assert "auto_approved" not in cards_by_type["restructure_intro"]


def _chainable_table(data=None):
    table = MagicMock()
    for method in ("select", "eq", "order", "limit", "maybe_single", "single", "insert", "update"):
        getattr(table, method).return_value = table
    table.execute.return_value = MagicMock(data=[] if data is None else data)
    return table


def test_v1_audit_persists_evidence_without_running_legacy_technical_cards(monkeypatch):
    monkeypatch.setenv("TECHNICAL_AUDIT_V1_ENABLED", "true")
    monkeypatch.setenv("TECHNICAL_AUDIT_INTERNAL_CLIENT_IDS", "client-1")
    monkeypatch.setenv("TECHNICAL_AUDIT_CHECK_SETS", "foundation")
    tables = {
        "improvement_runs": _chainable_table([{"id": "improvement-run-1"}]),
        "page_inventory": _chainable_table(),
        "client_site_profiles": _chainable_table({
            "client_id": "client-1",
            "llms_txt_enabled": False,
            "priority_urls": ["https://x.com/p1"],
        }),
        "pipeline_runs": _chainable_table({"id": "pipeline-run-1"}),
        "technical_audit_runs": _chainable_table([{"id": "audit-run-1"}]),
        "technical_audit_observations": _chainable_table(),
        "technical_audit_results": _chainable_table(),
        "action_cards": _chainable_table(),
    }
    sb = MagicMock()
    sb.table.side_effect = lambda name: tables[name]
    inventory = [{
        "url": "https://x.com/p1",
        "title": "Page 1",
        "h1": "H1",
        "first_paragraph": "text",
        "raw_html": "<html><head><title>Page</title></head></html>",
        "last_modified": None,
        "word_count": 1,
        "outbound_link_count": 0,
        "has_faq_schema": False,
        "has_comparison_table": False,
        "schema_types": [],
    }]
    audit_report = {
        "audit_version": 1,
        "observations": [{
            "id": "page:https://x.com/p1",
            "kind": "page",
            "subject": "https://x.com/p1",
            "retrieved_at": "2026-07-14T10:00:00+00:00",
            "fingerprint": "a" * 64,
            "data": {"titles": []},
        }],
        "results": [{
            "check_id": "meta_title.integrity",
            "check_version": 1,
            "section": "meta_title",
            "subject": "https://x.com/p1",
            "status": "fail",
            "severity": "high",
            "summary": "Title is missing",
            "expected": "One title",
            "observed": {"count": 0},
            "evidence_refs": ["page:https://x.com/p1"],
            "scope": {"sampled": False, "urls_checked": 1},
            "applicability": {"applies": True, "reason": "HTML page"},
            "confidence": "high",
            "next_action": {"owner": "admin", "instruction": "Add a title"},
            "remediation_id": "meta_title.correct",
        }],
        "summary": {
            "pass": 0,
            "fail": 1,
            "review": 0,
            "unknown": 0,
            "not_applicable": 0,
            "total": 1,
        },
    }

    queries = [{"id": "id1", "prompt_text": "q1", "bucket": "awareness"}]
    tracker_gaps = [
        {
            "query": f"query-{number}",
            "query_id": f"query-{number}",
            "bucket": "awareness",
            "client_mention_rate": 0.1,
            "competitor_data": [{"name": "Competitor", "mention_rate": gap}],
        }
        for number, gap in [(4, 0.6), (1, 0.9), (7, 0.3), (2, 0.8), (6, 0.4), (3, 0.7), (5, 0.5)]
    ]

    with patch("src.improvement.pipeline._get_supabase", return_value=sb), \
         patch("src.improvement.pipeline.run_crawlability_gate", return_value={
             "has_critical_blocker": True,
             "robots_txt": {"status": "fail", "detail": "blocked"},
         }), \
         patch("src.improvement.pipeline.build_crawlability_card") as mock_crawlability_card, \
         patch("src.improvement.pipeline.build_inventory", return_value=inventory), \
         patch("src.improvement.pipeline.match_queries_to_pages") as mock_match, \
         patch("src.improvement.pipeline.check_competitive_gaps") as mock_gap_check, \
         patch("src.improvement.pipeline.compute_structural_score") as mock_score, \
         patch("src.improvement.pipeline.generate_sonnet_quality") as mock_quality, \
         patch("src.improvement.pipeline.classify_actions") as mock_classify, \
         patch("src.improvement.pipeline.generate_sonnet_specifics") as mock_sonnet, \
         patch("src.improvement.pipeline.build_content_brief") as mock_brief, \
         patch("src.improvement.pipeline.run_technical_audit", return_value=audit_report, create=True):
        mock_match.return_value = []
        mock_gap_check.return_value = []
        result = run_improvement_pipeline(
            {
                "client_id": "client-1",
                "thread_id": "thread-1",
                "client_config": {
                    "website_domain": "x.com",
                    "brand_name": "BrandX",
                    "competitors": [],
                },
            },
            queries,
            tracker_gaps,
        )

    assert result["technical_audit_run_id"] == "audit-run-1"
    assert result["technical_audit_summary"]["fail"] == 1
    assert result["query_matches"] == []
    assert result["citation_scores"] == []
    improvement_run_insert = tables["improvement_runs"].insert.call_args.args[0]
    assert improvement_run_insert["run_mode"] == "technical_v1"
    assert improvement_run_insert["effective_check_sets"] == ["foundation"]
    assert len(result["competitive_gap_data"]) == 5
    assert [card["action_type"] for card in result["action_cards"]] == [
        "community_check"
    ] * 5
    assert all(card["track"] == "manual" for card in result["action_cards"])
    mock_match.assert_not_called()
    mock_gap_check.assert_not_called()
    mock_score.assert_not_called()
    mock_quality.assert_not_called()
    mock_classify.assert_not_called()
    mock_sonnet.assert_not_called()
    mock_brief.assert_not_called()
    mock_crawlability_card.assert_not_called()
    assert "query_page_matches" not in [call.args[0] for call in sb.table.call_args_list]
    assert "page_citation_scores" not in [call.args[0] for call in sb.table.call_args_list]
    tables["technical_audit_observations"].insert.assert_called_once()
    tables["technical_audit_results"].insert.assert_called_once()
    assert tables["technical_audit_runs"].insert.call_args.args[0]["scope"] == {
        "inventory_pages": 1,
        "check_sets": ["foundation"],
    }
    completed_audit_run = next(
        call.args[0]
        for call in tables["technical_audit_runs"].update.call_args_list
        if call.args[0]["status"] == "completed"
    )
    assert completed_audit_run["scope"] == {
        "inventory_pages": 1,
        "observations": 1,
        "check_sets": ["foundation"],
    }
    completed_improvement_run = tables["improvement_runs"].update.call_args.args[0]
    assert completed_improvement_run["queries_matched"] == 0
    assert completed_improvement_run["content_gaps_found"] == 0
    assert completed_improvement_run["competitive_gaps_found"] == 7
    assert completed_improvement_run["cards_generated"] == 5


def test_v1_flag_disabled_preserves_legacy_route_without_audit_writes(monkeypatch):
    monkeypatch.setenv("TECHNICAL_AUDIT_V1_ENABLED", "false")
    monkeypatch.setenv("TECHNICAL_AUDIT_CHECK_SETS", "unsupported")
    tables = {
        "improvement_runs": _chainable_table([{"id": "improvement-run-1"}]),
        "action_cards": _chainable_table(),
    }
    sb = MagicMock()
    sb.table.side_effect = lambda name: tables[name]

    with patch("src.improvement.pipeline._get_supabase", return_value=sb), \
         patch("src.improvement.pipeline.run_crawlability_gate", return_value={"has_critical_blocker": False}), \
         patch("src.improvement.pipeline.build_inventory", return_value=[]), \
         patch("src.improvement.pipeline.match_queries_to_pages", return_value=[]) as mock_match, \
         patch("src.improvement.pipeline.check_competitive_gaps", return_value=[]) as mock_gap_check, \
         patch("src.improvement.pipeline.run_technical_audit") as mock_audit:
        result = run_improvement_pipeline(
            {
                "client_id": "client-1",
                "client_config": {
                    "website_domain": "x.com",
                    "brand_name": "BrandX",
                    "competitors": [],
                },
            },
            [],
            [],
        )

    assert result["technical_audit_run_id"] is None
    assert result["technical_audit_summary"] == {}
    improvement_run_insert = tables["improvement_runs"].insert.call_args.args[0]
    assert improvement_run_insert["run_mode"] == "legacy"
    assert improvement_run_insert["effective_check_sets"] == []
    mock_match.assert_called_once()
    mock_gap_check.assert_called_once()
    mock_audit.assert_not_called()
    assert "technical_audit_runs" not in [call.args[0] for call in sb.table.call_args_list]


def test_v1_non_allowlisted_client_preserves_legacy_route_without_audit_writes(monkeypatch):
    monkeypatch.setenv("TECHNICAL_AUDIT_V1_ENABLED", "true")
    monkeypatch.setenv("TECHNICAL_AUDIT_INTERNAL_CLIENT_IDS", "client-2")
    monkeypatch.setenv("TECHNICAL_AUDIT_CHECK_SETS", "unsupported")
    tables = {
        "improvement_runs": _chainable_table([{"id": "improvement-run-1"}]),
        "page_inventory": _chainable_table(),
        "query_page_matches": _chainable_table(),
        "action_cards": _chainable_table(),
    }
    sb = MagicMock()
    sb.table.side_effect = lambda name: tables[name]
    inventory = [{
        "url": "https://x.com/p1",
        "title": "Page 1",
        "h1": "H1",
        "first_paragraph": "text",
        "raw_html": "<html></html>",
        "last_modified": None,
        "word_count": 1,
        "outbound_link_count": 0,
        "has_faq_schema": False,
        "has_comparison_table": False,
        "schema_types": [],
    }]
    legacy_matches = [{
        "query": "query-1",
        "query_id": "query-1",
        "match_type": "content_gap",
        "matched_page_url": None,
        "similarity_score": 0.0,
        "bucket": "awareness",
    }]
    legacy_gaps = [{
        "query": "query-1",
        "query_id": "query-1",
        "competitive_gap": 0.4,
        "top_competitor": "Competitor",
        "client_mention_rate": 0.1,
        "competitor_mention_rate": 0.5,
    }]

    with patch("src.improvement.pipeline._get_supabase", return_value=sb), \
         patch("src.improvement.pipeline.run_crawlability_gate", return_value={"has_critical_blocker": False}), \
         patch("src.improvement.pipeline.build_inventory", return_value=inventory), \
         patch("src.improvement.pipeline.match_queries_to_pages", return_value=legacy_matches) as mock_match, \
         patch("src.improvement.pipeline.check_competitive_gaps", return_value=legacy_gaps) as mock_gap_check, \
         patch("src.improvement.pipeline.run_technical_audit") as mock_audit:
        result = run_improvement_pipeline(
            {
                "client_id": "client-1",
                "client_config": {
                    "website_domain": "x.com",
                    "brand_name": "BrandX",
                    "competitors": [],
                },
            },
            [{"id": "query-1", "prompt_text": "query-1", "bucket": "awareness"}],
            [],
        )

    mock_match.assert_called_once()
    mock_gap_check.assert_called_once()
    mock_audit.assert_not_called()
    assert result["query_matches"] == legacy_matches
    assert result["competitive_gap_data"] == legacy_gaps
    improvement_run_insert = tables["improvement_runs"].insert.call_args.args[0]
    assert improvement_run_insert["run_mode"] == "legacy"
    assert improvement_run_insert["effective_check_sets"] == []
    assert "technical_audit_runs" not in [call.args[0] for call in sb.table.call_args_list]


@pytest.mark.parametrize(
    ("check_sets", "message"),
    [
        ("unsupported", "Unavailable technical audit check set"),
        ("", "At least one technical audit check set is required"),
    ],
)
def test_v1_active_client_rejects_invalid_check_sets_before_pipeline_work(
    monkeypatch, check_sets, message
):
    monkeypatch.setenv("TECHNICAL_AUDIT_V1_ENABLED", "true")
    monkeypatch.setenv("TECHNICAL_AUDIT_INTERNAL_CLIENT_IDS", "client-1")
    monkeypatch.setenv("TECHNICAL_AUDIT_CHECK_SETS", check_sets)

    with patch("src.improvement.pipeline._get_supabase") as mock_supabase:
        with pytest.raises(ValueError, match=message):
            run_improvement_pipeline(
                {
                    "client_id": "client-1",
                    "client_config": {
                        "website_domain": "x.com",
                        "brand_name": "BrandX",
                        "competitors": [],
                    },
                },
                [],
                [],
            )

    mock_supabase.assert_not_called()


def test_v1_audit_initialization_failure_does_not_abort_query_pipeline(monkeypatch):
    monkeypatch.setenv("TECHNICAL_AUDIT_V1_ENABLED", "true")
    monkeypatch.setenv("TECHNICAL_AUDIT_INTERNAL_CLIENT_IDS", "client-1")
    monkeypatch.setenv("TECHNICAL_AUDIT_CHECK_SETS", "foundation")
    tables = {
        "improvement_runs": _chainable_table([{"id": "improvement-run-1"}]),
        "action_cards": _chainable_table(),
    }
    sb = MagicMock()
    sb.table.side_effect = lambda name: tables[name]

    with patch("src.improvement.pipeline._get_supabase", return_value=sb), \
         patch("src.improvement.pipeline.run_crawlability_gate", return_value={"has_critical_blocker": False}), \
         patch("src.improvement.pipeline.build_inventory", return_value=[]), \
         patch("src.improvement.pipeline.match_queries_to_pages") as mock_match, \
         patch("src.improvement.pipeline.check_competitive_gaps") as mock_gap_check, \
         patch("src.improvement.pipeline.compute_structural_score") as mock_score, \
         patch("src.improvement.pipeline.build_content_brief") as mock_brief, \
         patch("src.improvement.pipeline.generate_sonnet_specifics") as mock_sonnet, \
         patch(
             "src.improvement.pipeline._run_and_persist_technical_audit",
             side_effect=RuntimeError("audit tables unavailable"),
         ):
        mock_match.return_value = []
        mock_gap_check.return_value = []
        result = run_improvement_pipeline(
            {
                "client_id": "client-1",
                "client_config": {
                    "website_domain": "x.com",
                    "brand_name": "BrandX",
                    "competitors": [],
                },
            },
            [],
            [],
        )

    assert result["improvement_run_id"] == "improvement-run-1"
    assert result["technical_audit_run_id"] is None
    assert result["technical_audit_error"] == "audit tables unavailable"
    mock_match.assert_not_called()
    mock_gap_check.assert_not_called()
    mock_score.assert_not_called()
    mock_brief.assert_not_called()
    mock_sonnet.assert_not_called()
