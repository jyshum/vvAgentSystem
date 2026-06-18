from unittest.mock import MagicMock, patch
import pytest
from src.upload import upload_run


@pytest.fixture
def sample_results():
    return [
        {
            "query": "best childcare finder",
            "engine": "chatgpt",
            "model": "gpt-4o-mini",
            "response_text": "Here are some options...",
            "brand_mentioned": False,
            "brand_cited": False,
            "citation_url": "",
            "competitor_mentions": ["Care.com"],
            "timestamp": "2026-06-17T12:00:00+00:00",
        },
    ]


@pytest.fixture
def sample_scores():
    return {
        "per_engine": {"chatgpt": {"mention_rate": 0.0, "citation_rate": 0.0}},
        "aggregate_mention_rate": 0.0,
        "aggregate_citation_rate": 0.0,
        "competitor_scores": {"Care.com": {"mention_rate": 1.0}},
    }


@patch("src.upload.create_client")
def test_upload_run_creates_run_and_results(mock_create, sample_results, sample_scores):
    mock_client = MagicMock()
    mock_create.return_value = mock_client

    mock_table = MagicMock()
    mock_client.from_.return_value = mock_table
    mock_insert = MagicMock()
    mock_table.insert.return_value = mock_insert
    mock_execute = MagicMock()
    mock_insert.execute.return_value = mock_execute
    mock_execute.data = [{"id": "run-uuid-123"}]

    mock_select = MagicMock()
    mock_insert.select.return_value = mock_select
    mock_select.single.return_value = MagicMock()
    mock_select.single.return_value.execute.return_value = MagicMock(
        data={"id": "run-uuid-123"}
    )

    run_id = upload_run("client-uuid", sample_results, sample_scores)

    assert run_id == "run-uuid-123"
    assert mock_client.from_.call_count >= 2


@patch("src.upload.create_client")
def test_upload_run_returns_none_without_env(mock_create):
    mock_create.side_effect = Exception("No env vars")
    run_id = upload_run("client-uuid", [], {})
    assert run_id is None
