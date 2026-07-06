from unittest.mock import patch, MagicMock
from src.improvement.pipeline import run_improvement_pipeline


class TestRunImprovementPipeline:
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
    @patch("src.improvement.pipeline.qa_card")
    def test_returns_expected_state_keys(
        self, mock_qa, mock_validate, mock_sonnet, mock_classify, mock_reddit,
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
        mock_reddit.return_value = []
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
    @patch("src.improvement.pipeline.run_reddit_scout")
    @patch("src.improvement.pipeline.classify_actions")
    @patch("src.improvement.pipeline.generate_sonnet_specifics")
    @patch("src.improvement.pipeline.validate_json_ld")
    @patch("src.improvement.pipeline.qa_card")
    def test_cards_get_db_ids_after_insert(
        self, mock_qa, mock_validate, mock_sonnet, mock_classify, mock_reddit,
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
    @patch("src.improvement.pipeline.qa_card")
    def test_multiple_queries_matching_one_page_produce_one_card_set(
        self, mock_qa, mock_validate, mock_sonnet, mock_classify, mock_reddit,
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
        mock_reddit.return_value = []
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

        # One card, not three — deduped by (page_url, action_type)
        assert len(result["action_cards"]) == 1
        card = result["action_cards"][0]
        # The card carries the worst-gap query as its primary
        assert card["query_id"] == "id2"
        assert card["priority"] == 1
        assert card["competitive_gap"] == 0.4
        # Sonnet specifics called once, not three times
        assert mock_sonnet.call_count == 1

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
    @patch("src.improvement.pipeline.qa_card")
    def test_card_failing_qa_twice_is_dropped(
        self, mock_qa, mock_validate, mock_sonnet, mock_classify, mock_reddit,
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
        mock_reddit.return_value = []
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
    @patch("src.improvement.pipeline.run_reddit_scout")
    @patch("src.improvement.pipeline.classify_actions")
    @patch("src.improvement.pipeline.generate_sonnet_specifics")
    @patch("src.improvement.pipeline.validate_json_ld")
    @patch("src.improvement.pipeline.qa_card")
    def test_card_passing_qa_on_retry_is_kept(
        self, mock_qa, mock_validate, mock_sonnet, mock_classify, mock_reddit,
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
        assert mock_sonnet.call_count == 2

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
    @patch("src.improvement.pipeline.qa_card")
    def test_card_auto_approved_after_three_clean_history_cycles(
        self, mock_qa, mock_validate, mock_sonnet, mock_classify, mock_reddit,
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
        card = result["action_cards"][0]
        assert card["action_type"] == "generate_schema"
        assert card["status"] == "approved"
        assert card["auto_approved"] is True
