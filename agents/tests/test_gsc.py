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


def test_get_service_uses_env_json_when_no_file(monkeypatch, tmp_path):
    """Railway has no gsc-credentials.json file — creds must load from
    GOOGLE_SERVICE_ACCOUNT_JSON env var."""
    import src.gsc as gsc

    gsc._service = None
    monkeypatch.chdir(tmp_path)  # no credentials file here
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", '{"client_email": "svc@x.iam"}')

    with patch("google.oauth2.service_account.Credentials") as mock_creds, \
         patch("googleapiclient.discovery.build"):
        gsc._get_service()
        mock_creds.from_service_account_info.assert_called_once()
        info = mock_creds.from_service_account_info.call_args.args[0]
        assert info == {"client_email": "svc@x.iam"}

    gsc._service = None


def test_get_service_prefers_file_when_present(monkeypatch, tmp_path):
    import src.gsc as gsc

    gsc._service = None
    creds_file = tmp_path / "gsc-credentials.json"
    creds_file.write_text('{"client_email": "file@x.iam"}')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", '{"client_email": "env@x.iam"}')

    with patch("google.oauth2.service_account.Credentials") as mock_creds, \
         patch("googleapiclient.discovery.build"):
        gsc._get_service()
        mock_creds.from_service_account_file.assert_called_once()

    gsc._service = None
