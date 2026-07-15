from __future__ import annotations

from urllib.parse import urlsplit

from ..models import AuditContext, AuditStatus, CheckResult
from ..observations import normalize_url
from ._common import build_result, unknown_result

_SECTION = "image_optimization"
_EXPECTED_INTEGRITY = "Content images load successfully as images over HTTPS"
_EXPECTED_ALT = (
    "Every content image carries an alt attribute; informative images describe"
    " content, decorative images declare alt=\"\""
)


def _filename(src: str) -> str:
    return urlsplit(src).path.rsplit("/", 1)[-1].lower()


def _alt_is_filename_like(alt: str, src: str) -> bool:
    lowered = alt.strip().lower()
    if not lowered:
        return False
    name = _filename(src)
    stem = name.rsplit(".", 1)[0]
    return lowered in {name, stem, src.lower()}


def _alt_is_stuffed(alt: str) -> bool:
    segments = [part.strip() for part in alt.split(",") if part.strip()]
    return len(segments) >= 4


def evaluate_image_integrity(context: AuditContext) -> list[CheckResult]:
    def _key(url: str) -> str:
        try:
            return normalize_url(url)
        except Exception:
            return url

    probes = {
        _key(probe.data.get("request_url") or ""): probe
        for probe in tuple(context.site_observations.get("image_probes") or ())
    }
    results = []
    for page in context.pages:
        data = page.data
        if not data.get("available", True):
            results.append(
                unknown_result(
                    check_id="images.integrity", section=_SECTION, subject=page.subject,
                    expected=_EXPECTED_INTEGRITY,
                    observed={"status_code": data.get("status_code")},
                    evidence_refs=(page.id,),
                    applicability_reason="Audited page retrieval was attempted",
                    instruction="Retry the page request or inspect host access controls",
                )
            )
            continue
        images = data.get("images", [])
        if not data.get("is_html", False) or not images:
            results.append(
                CheckResult.not_applicable(
                    check_id="images.integrity", check_version=1, section=_SECTION,
                    subject=page.subject, reason="Page has no content images",
                )
            )
            continue

        failures, unknowns, checked = [], [], 0
        refs = [page.id]
        for image in images:
            probe = probes.get(_key(image["src"]))
            if probe is None:
                continue
            checked += 1
            refs.append(probe.id)
            probe_data = probe.data
            status_code = int(probe_data.get("status_code") or 0)
            mime = (probe_data.get("content_type") or "").split(";", 1)[0].strip().lower()
            if image["src"].lower().startswith("http://"):
                failures.append({"src": image["src"], "defect": "served over plain HTTP"})
            elif status_code in {404, 410} or status_code >= 500 or probe_data.get("error"):
                failures.append({
                    "src": image["src"],
                    "defect": f"status {status_code}" if status_code else str(probe_data.get("error"))[:200],
                })
            elif mime and not mime.startswith("image/"):
                failures.append({"src": image["src"], "defect": f"non-image response ({mime})"})
            elif status_code in {403, 429}:
                unknowns.append({"src": image["src"], "status": status_code})
        scope = {
            "sampled": True,
            "images_found": len(images),
            "urls_checked": checked,
        }
        observed = {
            "failures": failures[:25],
            "blocked": unknowns[:25],
            "byte_measurement": "recorded as evidence only; no fixed byte or format rule",
        }
        common = {
            "check_id": "images.integrity", "section": _SECTION, "subject": page.subject,
            "expected": _EXPECTED_INTEGRITY, "observed": observed,
            "evidence_refs": tuple(refs[:30]),
            "applicability_reason": "The page displays content images",
            "scope": scope,
        }
        if failures:
            results.append(
                build_result(
                    **common, status=AuditStatus.FAIL, severity="medium",
                    summary="Images fail to load or are served insecurely",
                    instruction=(
                        "Re-upload or correct each listed image through the platform's"
                        " image manager; keep platform-native responsive delivery"
                    ),
                    remediation_id="images.repair",
                )
            )
        elif unknowns or checked == 0:
            results.append(
                unknown_result(
                    check_id="images.integrity", section=_SECTION, subject=page.subject,
                    expected=_EXPECTED_INTEGRITY, observed=observed,
                    evidence_refs=tuple(refs[:30]),
                    applicability_reason="The page displays content images",
                    instruction=(
                        "Retry blocked image requests or extend probing; sampled images"
                        " were not all verifiable"
                    ),
                    scope=scope,
                )
            )
        else:
            results.append(
                build_result(
                    **common, status=AuditStatus.PASS, severity="low",
                    summary="Sampled images load successfully over HTTPS",
                    instruction="No action required",
                )
            )
    return results


def evaluate_alt_text(context: AuditContext) -> list[CheckResult]:
    results = []
    for page in context.pages:
        data = page.data
        if not data.get("available", True):
            results.append(
                unknown_result(
                    check_id="images.alt_text", section=_SECTION, subject=page.subject,
                    expected=_EXPECTED_ALT,
                    observed={"status_code": data.get("status_code")},
                    evidence_refs=(page.id,),
                    applicability_reason="Audited page retrieval was attempted",
                    instruction="Retry the page request or inspect host access controls",
                )
            )
            continue
        images = data.get("images", [])
        if not data.get("is_html", False) or not images:
            results.append(
                CheckResult.not_applicable(
                    check_id="images.alt_text", check_version=1, section=_SECTION,
                    subject=page.subject, reason="Page has no content images",
                )
            )
            continue

        missing, reviews = [], []
        for image in images:
            alt = image.get("alt")
            if alt is None:
                missing.append({"src": image["src"], "defect": "missing alt attribute"})
            elif alt == "" and image.get("in_link"):
                reviews.append({
                    "src": image["src"],
                    "question": "Linked image has empty alt; confirm the link purpose is conveyed elsewhere",
                })
            elif alt and _alt_is_filename_like(alt, image["src"]):
                reviews.append({
                    "src": image["src"],
                    "question": f"Alt text '{alt[:80]}' looks like a filename; describe the image or use alt=\"\" if decorative",
                })
            elif alt and _alt_is_stuffed(alt):
                reviews.append({
                    "src": image["src"],
                    "question": "Alt text looks like a keyword list; describe the image instead",
                })
        observed = {"missing": missing[:25], "reviews": reviews[:25], "images": len(images)}
        common = {
            "check_id": "images.alt_text", "section": _SECTION, "subject": page.subject,
            "expected": _EXPECTED_ALT, "observed": observed, "evidence_refs": (page.id,),
            "applicability_reason": "The page displays content images",
            "scope": {"sampled": False, "urls_checked": len(images)},
        }
        if missing:
            results.append(
                build_result(
                    **common, status=AuditStatus.FAIL, severity="medium",
                    summary="Content images are missing alt attributes",
                    instruction=(
                        "Add meaningful alt text for informative images and alt=\"\" for"
                        " decorative images through the editor's image settings"
                    ),
                    remediation_id="images.add_alt_text",
                )
            )
        elif reviews:
            results.append(
                build_result(
                    **common, status=AuditStatus.REVIEW, severity="low",
                    summary="Some alt text needs a bounded judgment call",
                    instruction="Answer the listed questions; image purpose is contextual",
                )
            )
        else:
            results.append(
                build_result(
                    **common, status=AuditStatus.PASS, severity="low",
                    summary="Every image declares an appropriate alt state",
                    instruction="No action required",
                )
            )
    return results
