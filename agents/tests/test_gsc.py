from unittest.mock import patch, MagicMock
from src.gsc import fetch_gsc_metrics


def test_fetch_gsc_metrics_returns_per_query_data():
    mock_response = {
        "rows": [
            {"keys": ["best daycare toronto"], "clicks": 15, "impressions": 200, "ctr": 0.075, "position": 4.2},
            {"keys": ["childcare ontario"], "clicks": 8, "impressions": 120, "ctr": 0.067, "position": 6.1},
        ]
    }

    with patch("src.gsc._get_service") as mock_svc:
        mock_svc.return_value.searchanalytics.return_value.query.return_value.execute.return_value = mock_response
        result = fetch_gsc_metrics("https://www.example.com/", days=28)

    assert len(result["queries"]) == 2
    assert result["queries"][0]["query"] == "best daycare toronto"
    assert result["queries"][0]["clicks"] == 15
    assert result["totals"]["clicks"] == 23
    assert result["totals"]["impressions"] == 320


def test_fetch_gsc_metrics_no_data():
    with patch("src.gsc._get_service") as mock_svc:
        mock_svc.return_value.searchanalytics.return_value.query.return_value.execute.return_value = {}
        result = fetch_gsc_metrics("https://www.example.com/", days=28)

    assert result["queries"] == []
    assert result["totals"]["clicks"] == 0


def test_fetch_gsc_metrics_no_credentials():
    with patch("src.gsc._get_service", side_effect=FileNotFoundError("no creds")):
        result = fetch_gsc_metrics("https://www.example.com/", days=28)

    assert result["queries"] == []
    assert result["error"] == "no creds"
