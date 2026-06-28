import httpx
import base64
from urllib.parse import urlparse


def _auth_header(username: str, app_password: str) -> str:
    creds = base64.b64encode(f"{username}:{app_password}".encode()).decode()
    return f"Basic {creds}"


def _find_page_or_post(wp_url: str, auth: str, page_url: str) -> tuple[str, int, str] | None:
    """Find the WP post/page that matches the given URL. Returns (type, id, content)."""
    parsed = urlparse(page_url)
    slug = parsed.path.strip("/").split("/")[-1] or ""

    headers = {"Authorization": auth}

    for post_type in ["pages", "posts"]:
        try:
            params = {"slug": slug, "_fields": "id,content,slug"} if slug else {"_fields": "id,content,slug", "per_page": 5}
            resp = httpx.get(f"{wp_url}/wp-json/wp/v2/{post_type}", params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                items = resp.json()
                if items:
                    item = items[0]
                    return (post_type, item["id"], item["content"]["rendered"])
        except Exception as e:
            print(f"    WP search {post_type} failed: {e}")

    if not slug:
        try:
            resp = httpx.get(f"{wp_url}/wp-json/wp/v2/pages", params={"_fields": "id,content,slug", "per_page": 1}, headers=headers, timeout=15)
            if resp.status_code == 200:
                items = resp.json()
                if items:
                    return ("pages", items[0]["id"], items[0]["content"]["rendered"])
        except Exception:
            pass

    return None


def apply_wordpress_change(card: dict, cms_config: dict) -> dict:
    wp_url = cms_config.get("wp_url", "").rstrip("/")
    username = cms_config.get("wp_username", "admin")
    app_password = cms_config.get("app_password", "")

    if not wp_url or not app_password:
        return {"status": "error", "error": "WordPress URL or app password not configured"}

    auth = _auth_header(username, app_password)

    result = _find_page_or_post(wp_url, auth, card["page_url"])
    if not result:
        return {"status": "error", "error": f"Could not find WP page/post matching {card['page_url']}"}

    post_type, post_id, current_content = result

    if card.get("before_text") and card["before_text"] in current_content:
        new_content = current_content.replace(card["before_text"], card["after_text"], 1)
    elif card.get("code_block"):
        new_content = current_content + f'\n<script type="application/ld+json">\n{card["code_block"]}\n</script>'
    elif card.get("after_text"):
        new_content = current_content + f"\n\n{card['after_text']}"
    else:
        return {"status": "error", "error": "No before_text, after_text, or code_block to apply"}

    try:
        resp = httpx.post(
            f"{wp_url}/wp-json/wp/v2/{post_type}/{post_id}",
            headers={"Authorization": auth, "Content-Type": "application/json"},
            json={"content": new_content},
            timeout=15,
        )
        if resp.status_code in (200, 201):
            return {"status": "implemented", "wp_post_id": post_id, "wp_post_type": post_type}
        else:
            return {"status": "error", "error": f"WP API returned {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
