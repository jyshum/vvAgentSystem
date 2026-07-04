"""Tests for agents/src/improvement/gap_check.py — Competitive Gap Check (Step 5)."""

import pytest
from src.improvement.gap_check import compute_gap_for_query, check_competitive_gaps


# ---------------------------------------------------------------------------
# compute_gap_for_query
# ---------------------------------------------------------------------------

class TestComputeGapForQuery:
    def test_competitor_winning(self):
        """CompA at 0.8, CompB at 0.6, client at 0.4 → gap 0.4, top CompA."""
        gap_data = {
            "query": "best project management tool",
            "client_mention_rate": 0.4,
            "competitor_data": [
                {"name": "CompA", "mention_rate": 0.8},
                {"name": "CompB", "mention_rate": 0.6},
            ],
        }
        result = compute_gap_for_query(gap_data)

        assert result["query"] == "best project management tool"
        assert result["competitive_gap"] == round(0.8 - 0.4, 4)
        assert result["top_competitor"] == "CompA"
        assert result["client_mention_rate"] == 0.4
        assert result["competitor_mention_rate"] == 0.8

    def test_client_winning(self):
        """Client at 0.9, CompA at 0.3 → gap negative, client winning."""
        gap_data = {
            "query": "top crm software",
            "client_mention_rate": 0.9,
            "competitor_data": [
                {"name": "CompA", "mention_rate": 0.3},
            ],
        }
        result = compute_gap_for_query(gap_data)

        assert result["competitive_gap"] == round(0.3 - 0.9, 4)
        assert result["competitive_gap"] < 0
        assert result["top_competitor"] == "CompA"
        assert result["client_mention_rate"] == 0.9
        assert result["competitor_mention_rate"] == 0.3

    def test_equal_rates(self):
        """Client and competitor both at 0.5 → gap 0.0."""
        gap_data = {
            "query": "email marketing platform",
            "client_mention_rate": 0.5,
            "competitor_data": [
                {"name": "CompA", "mention_rate": 0.5},
            ],
        }
        result = compute_gap_for_query(gap_data)

        assert result["competitive_gap"] == 0.0
        assert result["top_competitor"] == "CompA"

    def test_no_competitors(self):
        """Empty competitor list → gap 0.0, top_competitor None."""
        gap_data = {
            "query": "solo query",
            "client_mention_rate": 0.7,
            "competitor_data": [],
        }
        result = compute_gap_for_query(gap_data)

        assert result["competitive_gap"] == 0.0
        assert result["top_competitor"] is None
        assert result["client_mention_rate"] == 0.7
        assert result["competitor_mention_rate"] == 0.0

    def test_result_rounded_to_4_decimals(self):
        """Gap is rounded to 4 decimal places."""
        gap_data = {
            "query": "rounding test",
            "client_mention_rate": 1 / 3,
            "competitor_data": [
                {"name": "Comp", "mention_rate": 2 / 3},
            ],
        }
        result = compute_gap_for_query(gap_data)

        assert result["competitive_gap"] == round(2 / 3 - 1 / 3, 4)


# ---------------------------------------------------------------------------
# check_competitive_gaps
# ---------------------------------------------------------------------------

class TestCheckCompetitiveGaps:
    def _make_match(self, query, query_id="q1", match_type="direct", url=None):
        return {
            "query": query,
            "query_id": query_id,
            "match_type": match_type,
            "matched_page_url": url,
        }

    def _make_gap_data(self, query, client_rate, competitors):
        return {
            "query": query,
            "client_mention_rate": client_rate,
            "competitor_data": competitors,
        }

    def test_filters_to_matches_only(self):
        """Returns results only for queries in the matches list, not all gap_data."""
        matches = [
            self._make_match("query A", query_id="q1"),
        ]
        gap_data_list = [
            self._make_gap_data("query A", 0.4, [{"name": "CompA", "mention_rate": 0.8}]),
            self._make_gap_data("query B", 0.2, [{"name": "CompB", "mention_rate": 0.9}]),
        ]

        results = check_competitive_gaps(matches, gap_data_list)

        assert len(results) == 1
        assert results[0]["query"] == "query A"

    def test_query_id_added_to_results(self):
        """Each result includes the query_id from the match."""
        matches = [
            self._make_match("query A", query_id="abc-123"),
        ]
        gap_data_list = [
            self._make_gap_data("query A", 0.5, [{"name": "CompA", "mention_rate": 0.7}]),
        ]

        results = check_competitive_gaps(matches, gap_data_list)

        assert results[0]["query_id"] == "abc-123"

    def test_empty_gap_data_returns_zeros(self):
        """If gap_data_list is empty, all matches get zero-gap results."""
        matches = [
            self._make_match("query A", query_id="q1"),
            self._make_match("query B", query_id="q2"),
        ]

        results = check_competitive_gaps(matches, [])

        assert len(results) == 2
        for r in results:
            assert r["competitive_gap"] == 0.0
            assert r["top_competitor"] is None

    def test_missing_gap_data_for_query_returns_zero(self):
        """A query in matches that has no corresponding gap_data gets zeros."""
        matches = [
            self._make_match("unknown query", query_id="q99"),
        ]
        gap_data_list = [
            self._make_gap_data("other query", 0.5, [{"name": "CompA", "mention_rate": 0.8}]),
        ]

        results = check_competitive_gaps(matches, gap_data_list)

        assert len(results) == 1
        assert results[0]["competitive_gap"] == 0.0
        assert results[0]["query_id"] == "q99"

    def test_multiple_matches_correct_gaps(self):
        """Each match is paired with the right gap_data."""
        matches = [
            self._make_match("query A", query_id="q1"),
            self._make_match("query B", query_id="q2"),
        ]
        gap_data_list = [
            self._make_gap_data("query A", 0.4, [{"name": "CompA", "mention_rate": 0.8}]),
            self._make_gap_data("query B", 0.9, [{"name": "CompB", "mention_rate": 0.3}]),
        ]

        results = check_competitive_gaps(matches, gap_data_list)

        assert len(results) == 2
        result_by_query = {r["query"]: r for r in results}

        assert result_by_query["query A"]["competitive_gap"] == round(0.8 - 0.4, 4)
        assert result_by_query["query B"]["competitive_gap"] == round(0.3 - 0.9, 4)
