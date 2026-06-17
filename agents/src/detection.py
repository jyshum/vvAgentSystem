import re


def detect_brand(
    response_text: str,
    brand_variations: list[str],
    website_domain: str,
) -> dict:
    text_lower = response_text.lower()
    domain_lower = website_domain.lower()

    brand_mentioned = any(v.lower() in text_lower for v in brand_variations)

    citation_url = None
    brand_cited = False

    if domain_lower in text_lower:
        brand_cited = True
        brand_mentioned = True
        urls = re.findall(r"https?://[^\s\)\]\"'>]+", response_text)
        for url in urls:
            if domain_lower in url.lower():
                citation_url = url
                break
        if citation_url is None:
            citation_url = f"https://{website_domain}"

    return {
        "brand_mentioned": brand_mentioned,
        "brand_cited": brand_cited,
        "citation_url": citation_url,
    }


def detect_competitors(
    response_text: str,
    competitors: list[str],
) -> list[str]:
    text_lower = response_text.lower()
    return [c for c in competitors if c.lower() in text_lower]
