from src.technical_audit.models import AuditContext, Observation
from src.technical_audit.site import SiteIdentity


IDENTITY = SiteIdentity.from_domain("example.com", "other")
RUN_AT = "2026-07-15T12:00:00+00:00"


def page_observation(url="https://example.com/", **overrides):
    data = {
        "url": url,
        "request_url": url,
        "final_url": url,
        "redirect_chain": [url],
        "available": True,
        "status_code": 200,
        "content_type": "text/html",
        "body_truncated": False,
        "fetch_error": None,
        "titles": ["Example"],
        "meta_descriptions": ["An example page description that is long enough."],
        "canonicals": [url],
        "robots_directives": [],
        "h1_texts": ["Example"],
        "is_html": True,
        "links": [],
        "images": [],
        "active_mixed_candidates": [],
        "jsonld_blocks": [],
        "has_microdata": False,
        "has_rdfa": False,
        "visible_dates": [],
        "meta_dates": {"published": None, "modified": None},
    }
    data.update(overrides)
    return Observation(
        id=f"page:{url}",
        kind="page",
        subject=url,
        retrieved_at=RUN_AT,
        fingerprint="a" * 64,
        data=data,
    )


def site_observation(kind, subject, **data):
    return Observation(
        id=f"{kind}:{subject}",
        kind=kind,
        subject=subject,
        retrieved_at=RUN_AT,
        fingerprint="b" * 64,
        data=data,
    )


def robots_observation(*, status=200, body="User-agent: *\nAllow: /\n",
                       content_type="text/plain", error=None):
    return site_observation(
        "robots_txt",
        "https://example.com/robots.txt",
        request_url="https://example.com/robots.txt",
        final_url="https://example.com/robots.txt",
        status_code=status,
        content_type=content_type,
        body=body,
        error=error,
    )


def sitemap_observation(url="https://example.com/sitemap.xml", *, status=200,
                        kind="urlset", entries=(), child_locs=(), parse_error=None,
                        entries_truncated=False, error=None, content_type="application/xml"):
    return site_observation(
        "sitemap",
        url,
        request_url=url,
        final_url=url,
        status_code=status,
        content_type=content_type,
        error=error,
        sitemap_kind=kind,
        entries=[dict(entry) for entry in entries],
        child_locs=list(child_locs),
        parse_error=parse_error,
        entries_truncated=entries_truncated,
    )


def make_context(pages=None, site_observations=None, integrations=None,
                 identity=IDENTITY):
    pages = tuple(pages) if pages is not None else (page_observation(),)
    return AuditContext(
        client_id="client-1",
        domain=identity.configured_domain,
        site_identity=identity,
        pages=pages,
        site_observations=site_observations or {},
        run_timestamp=RUN_AT,
        integrations=integrations or {},
    )
