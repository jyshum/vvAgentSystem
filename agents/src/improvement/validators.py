import json
import re
import httpx

REQUIRED_FIELDS_BY_TYPE = {
    "FAQPage": ["mainEntity"],
    "Organization": ["name"],
    "WebSite": ["name", "url"],
    "Article": ["headline"],
    "BlogPosting": ["headline"],
    "NewsArticle": ["headline"],
    "HowTo": ["name", "step"],
    "BreadcrumbList": ["itemListElement"],
    "Product": ["name"],
    "LocalBusiness": ["name"],
}


def validate_json_ld(json_ld_str: str) -> dict:
    errors = []

    if not json_ld_str or not json_ld_str.strip():
        return {"valid": False, "errors": ["Empty JSON-LD string"]}

    try:
        data = json.loads(json_ld_str)
    except json.JSONDecodeError as e:
        return {"valid": False, "errors": [f"JSON parse error: {e}"]}

    if not isinstance(data, dict):
        return {"valid": False, "errors": ["JSON-LD must be an object"]}

    if "@context" not in data:
        errors.append("Missing @context — must be 'https://schema.org'")

    schema_type = data.get("@type")
    if not schema_type:
        errors.append("Missing @type — every JSON-LD block needs a schema.org type")

    if schema_type and schema_type in REQUIRED_FIELDS_BY_TYPE:
        for field in REQUIRED_FIELDS_BY_TYPE[schema_type]:
            if field not in data:
                errors.append(f"Missing required field '{field}' for @type '{schema_type}'")

    if errors:
        return {"valid": False, "errors": errors}

    return {"valid": True, "errors": []}


def validate_html_fragment(html: str) -> dict:
    errors = []

    if not html or not html.strip():
        return {"valid": False, "errors": ["Empty HTML fragment"]}

    if re.search(r'<script\b', html, re.I):
        errors.append("HTML contains <script> tag — potential XSS risk")

    if re.search(r'\bon\w+\s*=', html, re.I):
        errors.append("HTML contains inline event handlers — potential XSS risk")

    if errors:
        return {"valid": False, "errors": errors}

    return {"valid": True, "errors": []}


def check_link_alive(url: str, timeout: int = 5) -> dict:
    try:
        resp = httpx.head(url, timeout=timeout, follow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0 (compatible; VV-LinkCheck/1.0)"})
        alive = resp.status_code < 400
        return {"alive": alive, "status_code": resp.status_code, "url": url}
    except Exception as e:
        return {"alive": False, "status_code": 0, "url": url, "error": str(e)}
