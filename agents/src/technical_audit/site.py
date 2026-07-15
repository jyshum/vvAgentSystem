from __future__ import annotations

from dataclasses import dataclass, replace
from ipaddress import ip_address
from urllib.parse import urlsplit


@dataclass(frozen=True)
class SiteIdentity:
    configured_domain: str
    platform: str
    allowed_hosts: frozenset[str]

    @classmethod
    def from_domain(cls, domain: str, platform: str) -> "SiteIdentity":
        raw = domain.strip()
        parsed = urlsplit(raw if "://" in raw else f"//{raw}")
        host = (parsed.hostname or "").lower().rstrip(".")
        try:
            port = parsed.port
        except ValueError as exc:
            raise ValueError(
                "domain must be a public hostname on the standard HTTPS port"
            ) from exc
        is_ip_literal = False
        try:
            ip_address(host)
            is_ip_literal = True
        except ValueError:
            pass
        if (
            not host
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or parsed.username is not None
            or parsed.password is not None
            or port not in {None, 443}
            or is_ip_literal
            or host == "localhost"
            or host.endswith((".localhost", ".local", ".internal"))
        ):
            raise ValueError(
                "domain must be a public hostname on the standard HTTPS port"
            )
        bare = host.removeprefix("www.")
        return cls(
            configured_domain=host,
            platform=platform.strip().lower(),
            allowed_hosts=frozenset({bare, f"www.{bare}"}),
        )

    def with_final_homepage(self, url: str) -> "SiteIdentity":
        parts = urlsplit(url)
        host = (parts.hostname or "").lower().rstrip(".")
        if not self.allows(url):
            raise ValueError("final homepage must be an allowed same-site HTTPS URL")
        return replace(self, allowed_hosts=frozenset({*self.allowed_hosts, host}))

    def allows(self, url: str) -> bool:
        try:
            parts = urlsplit(url)
            return (
                parts.scheme.lower() == "https"
                and (parts.hostname or "").lower().rstrip(".") in self.allowed_hosts
                and parts.port in {None, 443}
                and parts.username is None
                and parts.password is None
            )
        except ValueError:
            return False
