from __future__ import annotations

import socket
import ssl
from datetime import datetime, timezone
from typing import Any


TLS_TIMEOUT_SECONDS = 10


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _name_pairs(entries: Any) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for group in entries or ():
        for key, value in group:
            pairs.setdefault(str(key), str(value))
    return pairs


def inspect_tls(host: str, port: int = 443, timeout: float = TLS_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Handshake with the default verifying context and record certificate facts.

    Never raises: verification and transport failures are recorded as evidence.
    """
    context = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as tls_sock:
                certificate = tls_sock.getpeercert() or {}
        return {
            "verified": True,
            "host": host,
            "subject": _name_pairs(certificate.get("subject")),
            "issuer": _name_pairs(certificate.get("issuer")),
            "not_before": certificate.get("notBefore"),
            "not_after": certificate.get("notAfter"),
            "subject_alt_names": [
                str(value)
                for kind, value in certificate.get("subjectAltName", ())
                if str(kind).lower() == "dns"
            ],
            "retrieved_at": _now(),
        }
    except ssl.SSLCertVerificationError as exc:
        return {
            "verified": False,
            "host": host,
            "error": f"certificate_verification: {exc.verify_message or exc}",
            "unreachable": False,
            "retrieved_at": _now(),
        }
    except Exception as exc:
        return {
            "verified": False,
            "host": host,
            "error": type(exc).__name__,
            "unreachable": True,
            "retrieved_at": _now(),
        }
