import httpx


def apply_webflow_change(card: dict, cms_config: dict) -> dict:
    api_token = cms_config.get("api_token", "")
    site_id = cms_config.get("site_id", "")

    if not api_token or not site_id:
        return {"status": "error", "error": "Webflow API token or site ID not configured"}

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "accept-version": "2.0.0",
    }

    page_url = card.get("page_url", "")
    slug = page_url.rstrip("/").split("/")[-1] or "index"

    try:
        resp = httpx.get(
            f"https://api.webflow.com/v2/sites/{site_id}/pages",
            headers=headers,
            timeout=15,
        )
        if resp.status_code != 200:
            return {"status": "error", "error": f"Webflow API returned {resp.status_code}: {resp.text[:200]}"}

        pages = resp.json().get("pages", [])
        matched_page = None
        for page in pages:
            if page.get("slug") == slug or page.get("title", "").lower().replace(" ", "-") == slug:
                matched_page = page
                break

        if not matched_page:
            return {"status": "error", "error": f"Could not find Webflow page matching slug '{slug}'"}

        page_id = matched_page["id"]

        update_data = {}
        if card.get("code_block"):
            current_head = matched_page.get("seo", {}).get("customHeadCode", "")
            schema_tag = f'<script type="application/ld+json">\n{card["code_block"]}\n</script>'
            update_data["seo"] = {"customHeadCode": (current_head + "\n" + schema_tag).strip()}

        if update_data:
            resp = httpx.patch(
                f"https://api.webflow.com/v2/sites/{site_id}/pages/{page_id}",
                headers=headers,
                json=update_data,
                timeout=15,
            )
            if resp.status_code not in (200, 201):
                return {"status": "error", "error": f"Webflow page update returned {resp.status_code}: {resp.text[:200]}"}

        staging_domain = cms_config.get("staging_domain", f"{site_id}.webflow.io")
        staging_url = f"https://{staging_domain}/{slug}" if slug != "index" else f"https://{staging_domain}/"

        return {
            "status": "implemented",
            "preview_url": staging_url,
            "webflow_page_id": page_id,
            "note": "Change applied to staging only — NOT published to production",
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}
