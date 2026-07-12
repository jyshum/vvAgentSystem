import os
from datetime import datetime, timedelta, timezone


_service = None


def _get_service():
    global _service
    if _service is None:
        import json

        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        scopes = ["https://www.googleapis.com/auth/webmasters.readonly"]
        creds_path = os.environ.get("GSC_CREDENTIALS_PATH", "gsc-credentials.json")
        if os.path.exists(creds_path):
            creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
        else:
            # Deployed environments (Railway) have no credentials file — the
            # service-account JSON is provided via env instead.
            raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
            if not raw:
                raise FileNotFoundError(
                    f"No GSC credentials: {creds_path} missing and GOOGLE_SERVICE_ACCOUNT_JSON unset"
                )
            creds = service_account.Credentials.from_service_account_info(json.loads(raw), scopes=scopes)
        _service = build("searchconsole", "v1", credentials=creds)
    return _service


def fetch_gsc_metrics(site_url: str, days: int = 28) -> dict:
    try:
        service = _get_service()
    except Exception as e:
        print(f"  GSC credentials error: {e}")
        return {"queries": [], "totals": {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0}, "error": str(e)}

    end = datetime.now(timezone.utc).date() - timedelta(days=3)
    start = end - timedelta(days=days)

    try:
        response = service.searchanalytics().query(
            siteUrl=site_url,
            body={
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
                "dimensions": ["query"],
                "rowLimit": 100,
            },
        ).execute()
    except Exception as e:
        print(f"  GSC API error: {e}")
        return {"queries": [], "totals": {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0}, "error": str(e)}

    rows = response.get("rows", [])
    queries = [
        {
            "query": row["keys"][0],
            "clicks": row["clicks"],
            "impressions": row["impressions"],
            "ctr": round(row["ctr"], 4),
            "position": round(row["position"], 1),
        }
        for row in rows
    ]

    total_clicks = sum(r["clicks"] for r in queries)
    total_impressions = sum(r["impressions"] for r in queries)
    avg_ctr = round(total_clicks / total_impressions, 4) if total_impressions > 0 else 0
    avg_position = round(sum(r["position"] * r["impressions"] for r in queries) / total_impressions, 1) if total_impressions > 0 else 0

    return {
        "queries": queries,
        "totals": {
            "clicks": total_clicks,
            "impressions": total_impressions,
            "ctr": avg_ctr,
            "position": avg_position,
        },
    }
