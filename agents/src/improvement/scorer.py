import json
import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup

FILLER_PATTERNS = re.compile(
    r"^(welcome|hello|hi |thanks for|thank you|we are (so )?glad|"
    r"let us |let's |in this (article|post|guide)|"
    r"are you looking|have you ever|do you want)",
    re.I
)

AUTHORITATIVE_TLDS = re.compile(r"\.(gov|edu|org|ac\.[a-z]{2})(/|$)")
CREDENTIAL_PATTERNS = re.compile(
    r"(ph\.?d|m\.?d|m\.?b\.?a|dr\.|prof\.|professor|"
    r"reviewed by|written by|author:|by [A-Z][a-z]+ [A-Z][a-z]+)",
    re.I
)

BASELINE_SCHEMA_TYPES = {"Organization", "WebSite", "BreadcrumbList"}
HIGH_VALUE_SCHEMA_TYPES = {"FAQPage", "HowTo", "Article", "NewsArticle", "BlogPosting", "Product"}


def check_answer_first(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body")
    if not body:
        return {"score": 0, "has_declarative_opening": False, "detail": "No body tag found"}

    for tag in body.find_all(["nav", "footer", "header", "aside", "script", "style"]):
        tag.decompose()

    paragraphs = [p.get_text(strip=True) for p in body.find_all("p") if len(p.get_text(strip=True)) > 20]
    if not paragraphs:
        return {"score": 0, "has_declarative_opening": False, "detail": "No paragraphs found"}

    first_text = paragraphs[0]
    first_words = " ".join(first_text.split()[:150])

    if first_text.strip().endswith("?"):
        return {"score": 0, "has_declarative_opening": False, "detail": "Opening is a question"}

    if FILLER_PATTERNS.match(first_text.strip()):
        return {"score": 0, "has_declarative_opening": False, "detail": "Opening uses filler/welcome language"}

    sentences = re.split(r'[.!]', first_words)
    declarative_sentences = [s.strip() for s in sentences if s.strip() and not s.strip().endswith("?")]

    if declarative_sentences and len(declarative_sentences[0].split()) >= 5:
        return {"score": 15, "has_declarative_opening": True, "detail": "Strong declarative opening"}

    return {"score": 0, "has_declarative_opening": False, "detail": "Opening lacks a clear declarative answer"}


def check_faq_schema(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if data.get("@type") == "FAQPage" and data.get("mainEntity"):
                qa_count = len(data["mainEntity"])
                return {"score": 10, "has_faq": True, "qa_count": qa_count, "detail": f"FAQPage schema with {qa_count} Q&A pair(s)"}
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass

    return {"score": 0, "has_faq": False, "qa_count": 0, "detail": "No FAQPage schema found"}


def check_comparison_tables(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    comparison_count = 0

    for table in tables:
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if len(headers) >= 3:
            comparison_count += 1

    if comparison_count > 0:
        return {"score": 10, "table_count": comparison_count, "detail": f"{comparison_count} comparison table(s) found"}
    return {"score": 0, "table_count": 0, "detail": "No comparison tables found"}


def check_lists(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["nav", "footer", "header"]):
        tag.decompose()

    ol_count = len(soup.find_all("ol"))
    ul_count = len(soup.find_all("ul"))
    total = ol_count + ul_count

    if total == 0:
        return {"score": 0, "list_count": 0, "detail": "No lists found"}
    elif total >= 3:
        return {"score": 10, "list_count": total, "detail": f"{total} lists found (ordered: {ol_count}, unordered: {ul_count})"}
    elif total >= 1:
        return {"score": 5, "list_count": total, "detail": f"{total} list(s) found"}
    return {"score": 0, "list_count": 0, "detail": "No lists found"}


def check_freshness(last_modified: str | None) -> dict:
    if not last_modified:
        return {"score": 0, "age_days": None, "detail": "No last-modified date available"}

    try:
        try:
            dt = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
        except ValueError:
            from dateutil import parser as dateutil_parser
            dt = dateutil_parser.parse(last_modified)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        age_days = (datetime.now(timezone.utc) - dt).days

        if age_days <= 90:
            return {"score": 10, "age_days": age_days, "detail": f"Content is {age_days} days old — fresh"}
        elif age_days <= 180:
            return {"score": 6, "age_days": age_days, "detail": f"Content is {age_days} days old — getting stale"}
        elif age_days <= 365:
            return {"score": 3, "age_days": age_days, "detail": f"Content is {age_days} days old — stale"}
        else:
            return {"score": 1, "age_days": age_days, "detail": f"Content is {age_days} days old — critically stale"}
    except Exception:
        return {"score": 0, "age_days": None, "detail": f"Could not parse date: {last_modified}"}


def check_word_count(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body")
    if not body:
        return {"score": 0, "word_count": 0, "h2_count": 0, "detail": "No body tag"}

    for tag in body.find_all(["nav", "footer", "header", "script", "style"]):
        tag.decompose()

    text = body.get_text(separator=" ", strip=True)
    word_count = len(text.split())
    h2_count = len(body.find_all("h2"))

    if word_count >= 2000 and h2_count >= 3:
        return {"score": 10, "word_count": word_count, "h2_count": h2_count, "detail": f"{word_count} words, {h2_count} H2 sections"}
    elif word_count >= 1000:
        return {"score": 6, "word_count": word_count, "h2_count": h2_count, "detail": f"{word_count} words — could be longer"}
    elif word_count >= 500:
        return {"score": 3, "word_count": word_count, "h2_count": h2_count, "detail": f"{word_count} words — thin content"}
    return {"score": 1, "word_count": word_count, "h2_count": h2_count, "detail": f"Only {word_count} words"}


def check_source_citations(html: str, client_domain: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["nav", "footer", "header"]):
        tag.decompose()

    external_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http") and client_domain not in href:
            external_links.append(href)

    authoritative = [l for l in external_links if AUTHORITATIVE_TLDS.search(l)]

    if len(external_links) >= 5:
        score = 7
    elif len(external_links) >= 3:
        score = 5
    elif len(external_links) >= 1:
        score = 2
    else:
        return {"score": 0, "external_count": 0, "authoritative_count": 0, "detail": "No external citations"}

    score += min(3, len(authoritative))

    return {
        "score": min(10, score),
        "external_count": len(external_links),
        "authoritative_count": len(authoritative),
        "detail": f"{len(external_links)} external links, {len(authoritative)} authoritative (.gov/.edu/.org)",
    }


def check_author_attribution(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)

    matches = CREDENTIAL_PATTERNS.findall(text)

    has_schema_author = False
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if "author" in data:
                has_schema_author = True
        except (json.JSONDecodeError, TypeError):
            pass

    if has_schema_author and matches:
        return {"score": 10, "has_author": True, "has_credentials": True, "detail": "Author with credentials and schema markup"}
    elif matches:
        return {"score": 7, "has_author": True, "has_credentials": True, "detail": f"Author attribution found: {matches[0]}"}
    elif has_schema_author:
        return {"score": 5, "has_author": True, "has_credentials": False, "detail": "Author in schema but no visible credentials"}
    return {"score": 0, "has_author": False, "has_credentials": False, "detail": "No author attribution found"}


def check_schema_validation(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script", type="application/ld+json")

    if not scripts:
        return {"score": 0, "schema_status": "missing", "schema_errors": [], "types_found": [], "detail": "No JSON-LD schema found"}

    types_found = set()
    errors = []
    has_malformed = False

    for script in scripts:
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            has_malformed = True
            errors.append("Malformed JSON-LD block — crawlers silently ignore this")
            continue

        if "@context" not in data:
            errors.append("JSON-LD block missing @context")

        schema_type = data.get("@type")
        if not schema_type:
            errors.append("JSON-LD block missing @type")
        else:
            if isinstance(schema_type, list):
                types_found.update(schema_type)
            else:
                types_found.add(schema_type)

    if has_malformed and not types_found:
        return {"score": 2, "schema_status": "broken", "schema_errors": errors, "types_found": list(types_found), "detail": "Schema exists but is broken"}

    if errors:
        score = max(3, 15 - len(errors) * 3)
        return {"score": score, "schema_status": "broken", "schema_errors": errors, "types_found": list(types_found), "detail": f"Schema has {len(errors)} error(s)"}

    has_baseline = BASELINE_SCHEMA_TYPES.issubset(types_found)
    has_high_value = bool(types_found & HIGH_VALUE_SCHEMA_TYPES)

    if has_baseline and has_high_value:
        return {"score": 15, "schema_status": "valid_complete", "schema_errors": [], "types_found": list(types_found), "detail": "Complete schema coverage"}
    elif has_baseline or has_high_value:
        return {"score": 10, "schema_status": "valid_incomplete", "schema_errors": [], "types_found": list(types_found), "detail": f"Schema present ({', '.join(types_found)}) but incomplete"}
    else:
        return {"score": 5, "schema_status": "valid_incomplete", "schema_errors": [], "types_found": list(types_found), "detail": "Schema types found but missing baseline coverage"}


def compute_structural_score(html: str, client_domain: str, last_modified: str | None) -> dict:
    checks = {
        "answer_first": check_answer_first(html),
        "faq_schema": check_faq_schema(html),
        "comparison_tables": check_comparison_tables(html),
        "lists": check_lists(html),
        "freshness": check_freshness(last_modified),
        "word_count": check_word_count(html),
        "source_citations": check_source_citations(html, client_domain),
        "author_attribution": check_author_attribution(html),
        "schema_validation": check_schema_validation(html),
    }

    total = sum(check["score"] for check in checks.values())

    schema_result = checks["schema_validation"]

    return {
        "structural_score": min(100, total),
        "check_results": checks,
        "schema_status": schema_result["schema_status"],
        "schema_errors": schema_result.get("schema_errors", []),
    }
