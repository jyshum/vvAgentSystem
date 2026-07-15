from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
from typing import Any

from .checks import build_v1_registry
from .checks.llms_txt import UNSAFE_CONTENT
from .collector import CollectedSite, HttpEvidence
from .models import AuditContext, AuditStatus, Observation
from .observations import extract_page_observation
from .site import SiteIdentity


def _page_observation(evidence: HttpEvidence, identity: SiteIdentity | None = None) -> Observation:
    available = evidence.status_code == 200 and evidence.error is None
    return extract_page_observation(
        identity=identity,
        retrieved_at=evidence.retrieved_at,
        page={
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


def _http_evidence_observation(
    evidence: HttpEvidence,
    kind: str,
    *,
    body_excerpt_bytes: int = 2_000,
    extra: dict[str, Any] | None = None,
) -> Observation:
    data = asdict(evidence)
    data.pop("retrieved_at")
    data.pop("fingerprint")
    body = data.pop("body", "") or ""
    data["body"] = body[:body_excerpt_bytes]
    data["body_bytes"] = len(body.encode("utf-8"))
    if extra:
        data.update(extra)
    return Observation(
        id=f"{kind}:{evidence.request_url}",
        kind=kind,
        subject=evidence.final_url,
        retrieved_at=evidence.retrieved_at,
        fingerprint=evidence.fingerprint,
        data=data,
    )


def _sitemap_observation(evidence: HttpEvidence) -> Observation:
    from .evidence.sitemaps import parse_sitemap

    document = parse_sitemap(evidence.final_url, evidence.body)
    return _http_evidence_observation(
        evidence,
        "sitemap",
        body_excerpt_bytes=2_000,
        extra={
            "sitemap_kind": document.kind,
            "entries": [
                {"loc": entry.loc, "lastmod": entry.lastmod}
                for entry in document.entries
            ],
            "child_locs": list(document.child_locs),
            "parse_error": document.parse_error,
            "entries_truncated": document.entries_truncated,
        },
    )


def _tls_observation(tls: dict[str, Any], run_timestamp: str) -> Observation:
    retrieved_at = tls.get("retrieved_at") or run_timestamp
    return Observation(
        id=f"tls:{tls.get('host', 'unknown')}",
        kind="tls",
        subject=str(tls.get("host", "unknown")),
        retrieved_at=retrieved_at,
        fingerprint=sha256(
            json.dumps(
                {key: value for key, value in tls.items() if key != "retrieved_at"},
                sort_keys=True,
                default=str,
            ).encode("utf-8")
        ).hexdigest(),
        data={key: value for key, value in tls.items() if key != "retrieved_at"},
    )


def run_technical_audit(
    client_id: str,
    identity: SiteIdentity,
    collected: CollectedSite,
    enabled_check_sets: tuple[str, ...] = ("foundation",),
    integrations: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if identity != collected.identity:
        raise ValueError("collected evidence does not match the configured site identity")
    registry = build_v1_registry(enabled_check_sets)

    page_observations = tuple(
        _page_observation(page, collected.identity) for page in collected.pages
    )
    llms_observation = _llms_observation(collected.llms_txt)
    site_observations: dict[str, Any] = {"llms_txt": llms_observation}
    if collected.robots_txt is not None:
        site_observations["robots_txt"] = _http_evidence_observation(
            collected.robots_txt, "robots_txt", body_excerpt_bytes=16_000
        )
    if collected.sitemaps:
        site_observations["sitemaps"] = tuple(
            _sitemap_observation(document) for document in collected.sitemaps
        )
    if collected.tls is not None:
        site_observations["tls"] = _tls_observation(
            collected.tls, collected.homepage.retrieved_at
        )
    if collected.http_probe is not None:
        site_observations["http_probe"] = _http_evidence_observation(
            collected.http_probe, "http_probe", body_excerpt_bytes=500
        )
    if collected.external_probes:
        site_observations["external_probes"] = tuple(
            _http_evidence_observation(probe, "external_probe", body_excerpt_bytes=500)
            for probe in collected.external_probes
        )
    if collected.image_probes:
        site_observations["image_probes"] = tuple(
            _http_evidence_observation(probe, "image_probe", body_excerpt_bytes=0)
            for probe in collected.image_probes
        )

    context = AuditContext(
        client_id=client_id,
        domain=identity.configured_domain,
        site_identity=collected.identity,
        pages=page_observations,
        site_observations=site_observations,
        run_timestamp=collected.homepage.retrieved_at,
        integrations=integrations or {},
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
    for key, value in site_observations.items():
        if key == "llms_txt":
            continue
        items = value if isinstance(value, tuple) else (value,)
        observations.extend(item.to_dict() for item in items)
    return {
        "audit_version": 1,
        "scope": dict(collected.scope),
        "observations": observations,
        "results": [result.to_dict() for result in results],
        "summary": summary,
    }
