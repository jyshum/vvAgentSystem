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
    def test_returns_expected_state_keys(
        self, mock_validate, mock_sonnet, mock_classify, mock_reddit,
        mock_gaps, mock_quality, mock_score, mock_match, mock_inv,
        mock_crawl, mock_sb,
    ):
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
