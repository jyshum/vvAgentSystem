import httpx
from urllib.parse import urlparse


def _find_resource(shop_url: str, headers: dict, page_url: str) -> tuple[str, int, str] | None:
    """Find the Shopify page, article, or product matching the URL. Returns (type, id, body_html)."""
    parsed = urlparse(page_url)
    path = parsed.path.strip("/")

    for resource_type, api_path in [("pages", "pages"), ("articles", "blogs/articles"), ("products", "products")]:
        try:
            resp = httpx.get(
                f"{shop_url}/admin/api/2024-01/{api_path}.json",
                headers=headers,
                params={"limit": 50, "fields": "id,handle,body_html"},
                timeout=15,
            )
            if resp.status_code != 200:
                continue

            items = resp.json().get(resource_type, [])
            for item in items:
                if item.get("handle") and item["handle"] in path:
                    return (resource_type, item["id"], item.get("body_html", ""))

        except Exception as e:
            print(f"    Shopify search {resource_type} failed: {e}")

    return None


def apply_shopify_change(card: dict, cms_config: dict) -> dict:
    shop_domain = cms_config.get("shop_domain", "").rstrip("/")
    api_token = cms_config.get("api_token", "")

    if not shop_domain or not api_token:
        return {"status": "error", "error": "Shopify shop domain or API token not configured"}

    shop_url = f"https://{shop_domain}" if not shop_domain.startswith("http") else shop_domain
    headers = {"X-Shopify-Access-Token": api_token, "Content-Type": "application/json"}

    result = _find_resource(shop_url, headers, card["page_url"])
    if not result:
        return {"status": "error", "error": f"Could not find Shopify resource matching {card['page_url']}"}

    resource_type, resource_id, current_html = result
    singular = resource_type.rstrip("s")

    if card.get("before_text") and card["before_text"] in current_html:
        new_html = current_html.replace(card["before_text"], card["after_text"], 1)
    elif card.get("code_block"):
        new_html = current_html + f'\n<script type="application/ld+json">\n{card["code_block"]}\n</script>'
    elif card.get("after_text"):
        new_html = current_html + f"\n\n{card['after_text']}"
    else:
        return {"status": "error", "error": "No before_text, after_text, or code_block to apply"}

    api_path = "pages" if resource_type == "pages" else "products" if resource_type == "products" else "blogs/articles"

    try:
        resp = httpx.put(
            f"{shop_url}/admin/api/2024-01/{api_path}/{resource_id}.json",
            headers=headers,
            json={singular: {"id": resource_id, "body_html": new_html}},
            timeout=15,
        )
        if resp.status_code == 200:
            return {"status": "implemented", "shopify_id": resource_id, "shopify_type": resource_type}
        else:
            return {"status": "error", "error": f"Shopify API returned {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
