import csv
import json
from pathlib import Path

from src.output import write_csv, write_json, format_summary


SAMPLE_RESULTS = [
    {
        "query": "best childcare finder in Ontario",
        "engine": "chatgpt",
        "model": "gpt-4o-mini",
        "response_text": "ChildSpot is a great platform for finding childcare.",
        "brand_mentioned": True,
        "brand_cited": False,
        "citation_url": None,
        "competitor_mentions": ["OneList Ontario"],
        "timestamp": "2026-06-17T10:00:00",
    },
    {
        "query": "best childcare finder in Ontario",
        "engine": "perplexity",
        "model": "sonar",
        "response_text": "Government resources are your best bet for childcare.",
        "brand_mentioned": False,
        "brand_cited": False,
        "citation_url": None,
        "competitor_mentions": [],
        "timestamp": "2026-06-17T10:00:01",
    },
]

SAMPLE_SCORES = {
    "per_engine": {
        "chatgpt": {"mention_rate": 1.0, "citation_rate": 0.0},
        "perplexity": {"mention_rate": 0.0, "citation_rate": 0.0},
    },
    "aggregate_mention_rate": 0.5,
    "aggregate_citation_rate": 0.0,
}


class TestWriteCsv:
    def test_creates_csv_with_correct_headers(self, tmp_path):
        path = tmp_path / "test.csv"
        write_csv(SAMPLE_RESULTS, path)
        with open(path) as f:
            reader = csv.DictReader(f)
            assert "query" in reader.fieldnames
            assert "engine" in reader.fieldnames
            assert "response_text" in reader.fieldnames
            assert "brand_mentioned" in reader.fieldnames

    def test_csv_has_correct_row_count(self, tmp_path):
        path = tmp_path / "test.csv"
        write_csv(SAMPLE_RESULTS, path)
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2

    def test_csv_preserves_full_response_text(self, tmp_path):
        path = tmp_path / "test.csv"
        write_csv(SAMPLE_RESULTS, path)
        with open(path) as f:
            reader = csv.DictReader(f)
            row = next(reader)
        assert row["response_text"] == "ChildSpot is a great platform for finding childcare."

    def test_csv_competitor_mentions_joined(self, tmp_path):
        path = tmp_path / "test.csv"
        write_csv(SAMPLE_RESULTS, path)
        with open(path) as f:
            reader = csv.DictReader(f)
            row = next(reader)
        assert row["competitor_mentions"] == "OneList Ontario"


class TestWriteJson:
    def test_creates_valid_json(self, tmp_path):
        path = tmp_path / "test.json"
        write_json(SAMPLE_RESULTS, SAMPLE_SCORES, "ChildSpot", path)
        data = json.loads(path.read_text())
        assert "results" in data
        assert "visibility_scores" in data
        assert "client_name" in data

    def test_json_contains_all_results(self, tmp_path):
        path = tmp_path / "test.json"
        write_json(SAMPLE_RESULTS, SAMPLE_SCORES, "ChildSpot", path)
        data = json.loads(path.read_text())
        assert len(data["results"]) == 2

    def test_json_contains_scores(self, tmp_path):
        path = tmp_path / "test.json"
        write_json(SAMPLE_RESULTS, SAMPLE_SCORES, "ChildSpot", path)
        data = json.loads(path.read_text())
        assert data["visibility_scores"]["aggregate_mention_rate"] == 0.5


class TestFormatSummary:
    def test_summary_contains_engine_scores(self):
        text = format_summary(SAMPLE_SCORES, "ChildSpot")
        assert "chatgpt" in text.lower()
        assert "perplexity" in text.lower()

    def test_summary_contains_aggregate(self):
        text = format_summary(SAMPLE_SCORES, "ChildSpot")
        assert "50" in text or "0.5" in text
