from __future__ import annotations

from datetime import datetime, timezone

from ..evidence.structured_data import parse_jsonld
from ..models import AuditContext, AuditStatus, CheckResult
from ._common import build_result, unknown_result

_SECTION = "freshness"
_EXPECTED = (
    "Declared dates are valid, non-future, and ordered"
    " (dateModified >= datePublished); no universal freshness deadline applies"
)

_EDITORIAL_TYPES = {"Article", "BlogPosting", "NewsArticle"}


def _parse_date(value: str) -> datetime | None:
    candidate = value.strip()
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def evaluate_freshness(context: AuditContext) -> list[CheckResult]:
    run_at = datetime.fromisoformat(context.run_timestamp)
    results = []
    for page in context.pages:
        data = page.data
        if not data.get("available", True):
            results.append(
                unknown_result(
                    check_id="freshness.dates", section=_SECTION, subject=page.subject,
                    expected=_EXPECTED,
                    observed={"status_code": data.get("status_code")},
                    evidence_refs=(page.id,),
                    applicability_reason="Audited page retrieval was attempted",
                    instruction="Retry the page request or inspect host access controls",
                )
            )
            continue

        entities, _ = parse_jsonld(data.get("jsonld_blocks", []))
        schema_dates: dict[str, str] = {}
        expired_events = []
        is_editorial = False
        for entity in entities:
            raw_types = entity.get("@type")
            types = {raw_types} if isinstance(raw_types, str) else set(raw_types or [])
            if types & _EDITORIAL_TYPES:
                is_editorial = True
                for key in ("datePublished", "dateModified"):
                    if isinstance(entity.get(key), str):
                        schema_dates.setdefault(key, entity[key])
            if "Event" in types and isinstance(entity.get("endDate"), str):
                end = _parse_date(entity["endDate"])
                if end is not None and end < run_at:
                    expired_events.append(entity["endDate"])

        meta_dates = data.get("meta_dates") or {}
        visible_dates = data.get("visible_dates") or []
        published = schema_dates.get("datePublished") or meta_dates.get("published")
        modified = schema_dates.get("dateModified") or meta_dates.get("modified")
        has_date_signals = bool(published or modified or visible_dates)

        if not data.get("is_html", False) or (not is_editorial and not has_date_signals):
            results.append(
                CheckResult.not_applicable(
                    check_id="freshness.dates", check_version=1, section=_SECTION,
                    subject=page.subject,
                    reason="Timeless/utility page with no declared date signals",
                )
            )
            continue

        defects, reviews = [], []
        parsed_dates: dict[str, datetime] = {}
        for label, value in (("published", published), ("modified", modified)):
            if not value:
                continue
            parsed = _parse_date(value)
            if parsed is None:
                defects.append({"date": value, "defect": f"unparseable {label} date"})
            elif parsed > run_at:
                defects.append({"date": value, "defect": f"future-dated {label} date"})
            else:
                parsed_dates[label] = parsed
        for value in visible_dates:
            parsed = _parse_date(value)
            if parsed is not None and parsed > run_at:
                defects.append({"date": value, "defect": "future-dated visible date"})
        if (
            "published" in parsed_dates
            and "modified" in parsed_dates
            and parsed_dates["modified"] < parsed_dates["published"]
        ):
            defects.append({
                "date": f"{modified} < {published}",
                "defect": "dateModified precedes datePublished",
            })
        if expired_events:
            reviews.append({
                "dates": expired_events[:5],
                "question": "Event end dates are in the past; confirm the page should still present them",
            })

        observed = {
            "published": published,
            "modified": modified,
            "visible_dates": visible_dates[:5],
            "defects": defects[:10],
            "reviews": reviews,
            "change_verification": "unknown_baseline",
        }
        common = {
            "check_id": "freshness.dates", "section": _SECTION, "subject": page.subject,
            "expected": _EXPECTED, "observed": observed, "evidence_refs": (page.id,),
            "applicability_reason": "The page declares date signals or is editorial",
            "scope": {"sampled": False, "urls_checked": 1},
        }
        if defects:
            results.append(
                build_result(
                    **common, status=AuditStatus.FAIL, severity="medium",
                    summary="Declared dates are invalid, future-dated, or misordered",
                    instruction=(
                        "Correct the listed dates at their source; never change a date"
                        " without a meaningful content update"
                    ),
                    remediation_id="freshness.correct_dates",
                )
            )
        elif reviews:
            results.append(
                build_result(
                    **common, status=AuditStatus.REVIEW, severity="low",
                    summary="Date evidence suggests possible staleness",
                    instruction="Answer the listed staleness questions",
                )
            )
        else:
            results.append(
                build_result(
                    **common, status=AuditStatus.PASS, severity="low",
                    summary="Declared dates are valid and consistent",
                    instruction="No action required",
                )
            )
    return results
