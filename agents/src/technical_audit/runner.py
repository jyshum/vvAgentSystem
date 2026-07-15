from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from typing import Any

from .checks import build_v1_registry
from .checks.llms_txt import UNSAFE_CONTENT
from .collector import CollectedSite, HttpEvidence
from .models import AuditContext, AuditStatus, Observation
from .observations import extract_page_observation
from .site import SiteIdentity


def _page_observation(evidence: HttpEvidence) -> Observation:
    available = evidence.status_code == 200 and evidence.error is None
    return extract_page_observation(
        {
            "url": evidence.final_url,
            "request_url": evidence.request_url,
            "final_url": evidence.final_url,
            "redirect_chain": evidence.redirect_chain,
            "raw_html": evidence.body if available else "",
            "content_type": evidence.content_type,
            "available": available,
            "status_code": evidence.status_code,
            "fetch_error": evidence.error,
            "body_truncated": evidence.body_truncated,
            "fingerprint": evidence.fingerprint,
        },
        evidence.retrieved_at,
    )


def _llms_observation(evidence: HttpEvidence) -> Observation:
    data = asdict(evidence)
    data.pop("retrieved_at")
    data.pop("fingerprint")
    return Observation(
        id=f"site:{evidence.request_url}",
        kind="llms_txt",
        subject=evidence.final_url,
        retrieved_at=evidence.retrieved_at,
        fingerprint=evidence.fingerprint,
        data=data,
    )


def run_technical_audit(
    client_id: str,
    identity: SiteIdentity,
    collected: CollectedSite,
    enabled_check_sets: tuple[str, ...] = ("foundation",),
) -> dict[str, Any]:
    if identity != collected.identity:
        raise ValueError("collected evidence does not match the configured site identity")
    registry = build_v1_registry(enabled_check_sets)

    page_observations = tuple(_page_observation(page) for page in collected.pages)
    llms_observation = _llms_observation(collected.llms_txt)
    context = AuditContext(
        client_id=client_id,
        domain=identity.configured_domain,
        site_identity=collected.identity,
        pages=page_observations,
        site_observations={"llms_txt": llms_observation},
        run_timestamp=collected.homepage.retrieved_at,
    )
    results = registry.run(context)
    counts = Counter(result.status.value for result in results)
    summary = {status.value: counts.get(status.value, 0) for status in AuditStatus}
    summary["total"] = len(results)

    observations = [observation.to_dict() for observation in page_observations]
    persisted_llms = llms_observation.to_dict()
    persisted_llms["data"] = {
        key: value
        for key, value in persisted_llms["data"].items()
        if key != "body"
    }
    llms_body = collected.llms_txt.body
    unsafe_content = bool(UNSAFE_CONTENT.search(llms_body))
    persisted_llms["data"]["body_excerpt"] = (
        "[REDACTED: unsafe content detected]"
        if unsafe_content
        else llms_body[:4_000]
    )
    persisted_llms["data"]["unsafe_content_detected"] = unsafe_content
    persisted_llms["data"]["body_bytes"] = len(llms_body.encode("utf-8"))
    observations.append(persisted_llms)
    return {
        "audit_version": 1,
        "scope": dict(collected.scope),
        "observations": observations,
        "results": [result.to_dict() for result in results],
        "summary": summary,
    }
