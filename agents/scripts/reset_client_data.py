#!/usr/bin/env python3
"""Export and, with explicit confirmation, reset one client's generated data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from uuid import UUID

import psycopg
from psycopg.rows import dict_row


PRESERVED_TABLES = (
    "clients",
    "client_site_profiles",
    "queries",
    "client_users",
    "auth_users",
)

GENERATED_TABLES = (
    "technical_audit_observations",
    "technical_audit_results",
    "technical_audit_runs",
    "page_inventory",
    "query_page_matches",
    "page_citation_scores",
    "action_cards",
    "improvement_runs",
    "reports",
    "tracker_results",
    "prompt_scores",
    "competitive_gaps",
    "tracker_runs",
    "pipeline_runs",
)

DELETE_ORDER = (
    "technical_audit_runs",
    "improvement_runs",
    "reports",
    "tracker_runs",
    "pipeline_runs",
)

DELETE_SQL = {
    "technical_audit_runs": (
        "delete from public.technical_audit_runs "
        "where client_id = %(client_id)s"
    ),
    "improvement_runs": (
        "delete from public.improvement_runs where client_id = %(client_id)s"
    ),
    "reports": "delete from public.reports where client_id = %(client_id)s",
    "tracker_runs": (
        "delete from public.tracker_runs where client_id = %(client_id)s"
    ),
    "pipeline_runs": (
        "delete from public.pipeline_runs where client_id = %(client_id)s"
    ),
}

BACKUP_SQL = {
    "clients": (
        "select clients.* from public.clients as clients "
        "where clients.id = %(client_id)s order by clients.id"
    ),
    "client_site_profiles": (
        "select client_site_profiles.* "
        "from public.client_site_profiles as client_site_profiles "
        "where client_site_profiles.client_id = %(client_id)s "
        "order by client_site_profiles.client_id"
    ),
    "queries": (
        "select queries.* from public.queries as queries "
        "where queries.client_id = %(client_id)s order by queries.id"
    ),
    "client_users": (
        "select client_users.* from public.client_users as client_users "
        "where client_users.client_id = %(client_id)s order by client_users.id"
    ),
    # Deliberately explicit: auth.users contains password hashes and token columns.
    "auth_users": (
        "select auth_users.id, auth_users.instance_id, auth_users.aud, "
        "auth_users.role, auth_users.email, auth_users.phone, "
        "auth_users.email_confirmed_at, auth_users.phone_confirmed_at, "
        "auth_users.last_sign_in_at, auth_users.created_at, "
        "auth_users.updated_at, auth_users.banned_until "
        "from auth.users as auth_users "
        "join public.client_users as client_users "
        "on client_users.user_id = auth_users.id "
        "where client_users.client_id = %(client_id)s order by auth_users.id"
    ),
    "technical_audit_observations": (
        "select technical_audit_observations.* "
        "from public.technical_audit_observations as technical_audit_observations "
        "join public.technical_audit_runs as technical_audit_runs "
        "on technical_audit_runs.id = technical_audit_observations.audit_run_id "
        "where technical_audit_runs.client_id = %(client_id)s "
        "order by technical_audit_observations.id"
    ),
    "technical_audit_results": (
        "select technical_audit_results.* "
        "from public.technical_audit_results as technical_audit_results "
        "join public.technical_audit_runs as technical_audit_runs "
        "on technical_audit_runs.id = technical_audit_results.audit_run_id "
        "where technical_audit_runs.client_id = %(client_id)s "
        "order by technical_audit_results.id"
    ),
    "technical_audit_runs": (
        "select technical_audit_runs.* "
        "from public.technical_audit_runs as technical_audit_runs "
        "where technical_audit_runs.client_id = %(client_id)s "
        "order by technical_audit_runs.id"
    ),
    "page_inventory": (
        "select page_inventory.* from public.page_inventory as page_inventory "
        "join public.improvement_runs as improvement_runs "
        "on improvement_runs.id = page_inventory.run_id "
        "where improvement_runs.client_id = %(client_id)s "
        "order by page_inventory.id"
    ),
    "query_page_matches": (
        "select query_page_matches.* "
        "from public.query_page_matches as query_page_matches "
        "join public.improvement_runs as improvement_runs "
        "on improvement_runs.id = query_page_matches.run_id "
        "where improvement_runs.client_id = %(client_id)s "
        "order by query_page_matches.id"
    ),
    "page_citation_scores": (
        "select page_citation_scores.* "
        "from public.page_citation_scores as page_citation_scores "
        "join public.improvement_runs as improvement_runs "
        "on improvement_runs.id = page_citation_scores.run_id "
        "where improvement_runs.client_id = %(client_id)s "
        "order by page_citation_scores.id"
    ),
    "action_cards": (
        "select action_cards.* from public.action_cards as action_cards "
        "join public.improvement_runs as improvement_runs "
        "on improvement_runs.id = action_cards.run_id "
        "where improvement_runs.client_id = %(client_id)s "
        "order by action_cards.id"
    ),
    "improvement_runs": (
        "select improvement_runs.* "
        "from public.improvement_runs as improvement_runs "
        "where improvement_runs.client_id = %(client_id)s "
        "order by improvement_runs.id"
    ),
    "reports": (
        "select reports.* from public.reports as reports "
        "where reports.client_id = %(client_id)s order by reports.id"
    ),
    "tracker_results": (
        "select tracker_results.* "
        "from public.tracker_results as tracker_results "
        "join public.tracker_runs as tracker_runs "
        "on tracker_runs.id = tracker_results.run_id "
        "where tracker_runs.client_id = %(client_id)s "
        "order by tracker_results.id"
    ),
    "prompt_scores": (
        "select prompt_scores.* from public.prompt_scores as prompt_scores "
        "join public.tracker_runs as tracker_runs "
        "on tracker_runs.id = prompt_scores.run_id "
        "where tracker_runs.client_id = %(client_id)s "
        "order by prompt_scores.id"
    ),
    "competitive_gaps": (
        "select competitive_gaps.* "
        "from public.competitive_gaps as competitive_gaps "
        "join public.tracker_runs as tracker_runs "
        "on tracker_runs.id = competitive_gaps.run_id "
        "where tracker_runs.client_id = %(client_id)s "
        "order by competitive_gaps.id"
    ),
    "tracker_runs": (
        "select tracker_runs.* from public.tracker_runs as tracker_runs "
        "where tracker_runs.client_id = %(client_id)s order by tracker_runs.id"
    ),
    "pipeline_runs": (
        "select pipeline_runs.* from public.pipeline_runs as pipeline_runs "
        "where pipeline_runs.client_id = %(client_id)s order by pipeline_runs.id"
    ),
}

# Verification-only: the database hashes the complete auth row so password,
# token, and metadata values never cross the database boundary.
AUTH_VERIFICATION_SQL = (
    "select auth_users.id, "
    "encode(extensions.digest("
    "convert_to(to_jsonb(auth_users)::text, 'UTF8'), 'sha256'"
    "), 'hex') as row_fingerprint "
    "from auth.users as auth_users "
    "join public.client_users as client_users "
    "on client_users.user_id = auth_users.id "
    "where client_users.client_id = %(client_id)s "
    "order by auth_users.id"
)

_SENSITIVE_KEY_WORDS = frozenset(
    {
        "authorization",
        "authorizations",
        "cookie",
        "cookies",
        "credential",
        "credentials",
        "dsn",
        "key",
        "keys",
        "passwd",
        "password",
        "pwd",
        "secret",
        "secrets",
        "token",
        "tokens",
    }
)
_SENSITIVE_COMPACT_KEYS = frozenset(
    {
        "apikey",
        "authorizationheader",
        "clientsecret",
        "connectionstring",
        "databaseurl",
        "privatekey",
        "serviceaccountkey",
    }
)
_CREDENTIAL_URL_RE = re.compile(
    r"(?i)\b[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@"
)
_AUTHORIZATION_VALUE_RE = re.compile(
    r"(?i)^\s*(?:authorization\s*:\s*)?"
    r"(?:basic|bearer|digest|token)\s+\S+"
)
_DSN_SECRET_RE = re.compile(
    r"(?i)(?:^|[^a-z0-9_])(?:password|passwd|pwd|token|secret)\s*="
)
_COOKIE_VALUE_RE = re.compile(
    r"(?i)(?:(?:^|;\s*)(?:session(?:id)?|auth|jwt|sid|token|cookie)"
    r"[a-z0-9_.-]*=[^;\s]+|^[^;\s=]+=[^;]+;\s*"
    r"(?:path|domain|expires|max-age|samesite|secure|httponly)\b)"
)


def _is_sensitive_key(key: Any) -> bool:
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(key))
    words = {part for part in re.split(r"[^a-z0-9]+", name.lower()) if part}
    compact = re.sub(r"[^a-z0-9]", "", name.lower())
    return bool(words & _SENSITIVE_KEY_WORDS) or compact in _SENSITIVE_COMPACT_KEYS


def _is_sensitive_string(value: str) -> bool:
    return bool(
        _CREDENTIAL_URL_RE.search(value)
        or _AUTHORIZATION_VALUE_RE.search(value)
        or _DSN_SECRET_RE.search(value)
        or _COOKIE_VALUE_RE.search(value)
    )


class ResetVerificationError(RuntimeError):
    """Raised inside the write transaction when reset verification fails."""


def _uuid(value: str) -> str:
    try:
        return str(UUID(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("client ID must be a UUID") from exc


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export and optionally reset one client's generated rows."
    )
    parser.add_argument("--client-id", required=True, type=_uuid)
    parser.add_argument("--backup-dir", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-client-id")
    args = parser.parse_args(argv)
    if args.execute and args.confirm_client_id != args.client_id:
        raise SystemExit(
            "execution confirmation must exactly match --client-id"
        )
    return args


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        default=str,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _redact(value: Any, *, parent_key: str = "") -> Any:
    if parent_key == "cms_config" and value:
        return "[REDACTED]"
    if isinstance(value, Mapping):
        redacted = {}
        for key, child in value.items():
            normalized = str(key).lower()
            if _is_sensitive_key(key):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact(child, parent_key=normalized)
        return redacted
    if isinstance(value, list):
        return [_redact(child, parent_key=parent_key) for child in value]
    if isinstance(value, tuple):
        return [_redact(child, parent_key=parent_key) for child in value]
    if isinstance(value, str) and _is_sensitive_string(value):
        return "[REDACTED]"
    return value


def _safe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _redact(deepcopy(rows))


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json(value) + b"\n")


def _write_failure_report(path: Path, report: dict[str, Any]) -> None:
    try:
        _write_json(path, _redact(report))
    except Exception:
        # The original failure must remain primary; reporting is best effort.
        pass


def _fetch_rows(connection: Any, table: str, client_id: str) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(BACKUP_SQL[table], {"client_id": client_id})
        return list(cursor.fetchall())


def _fetch_complete_auth_fingerprints(
    connection: Any, client_id: str
) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(AUTH_VERIFICATION_SQL, {"client_id": client_id})
        return list(cursor.fetchall())


def _capture(connection: Any, client_id: str) -> dict[str, list[dict[str, Any]]]:
    return {
        table: _fetch_rows(connection, table, client_id)
        for table in PRESERVED_TABLES + GENERATED_TABLES
    }


def _validate_client_selection(
    snapshot: dict[str, list[dict[str, Any]]],
) -> None:
    if len(snapshot["clients"]) != 1:
        raise ResetVerificationError(
            "reset selection must resolve to exactly one client"
        )


def _export_snapshot(
    backup_dir: Path,
    client_id: str,
    execute: bool,
    snapshot: dict[str, list[dict[str, Any]]],
    auth_complete_fingerprints: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, bytes]]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    safe_snapshot = {table: _safe_rows(rows) for table, rows in snapshot.items()}
    for table, rows in safe_snapshot.items():
        _write_json(backup_dir / f"{table}.json", rows)

    preserved_bytes = {
        table: canonical_json(snapshot[table]) for table in PRESERVED_TABLES
    }
    manifest = {
        "format_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "client_id": client_id,
        "mode": "execute" if execute else "dry_run",
        "preserved": {
            table: safe_snapshot[table] for table in PRESERVED_TABLES
        },
        "preserved_fingerprints": {
            table: _fingerprint(snapshot[table]) for table in PRESERVED_TABLES
        },
        "auth_users_complete_fingerprints": auth_complete_fingerprints,
        "generated_counts": {
            table: len(snapshot[table]) for table in GENERATED_TABLES
        },
        "table_files": {
            table: f"{table}.json"
            for table in PRESERVED_TABLES + GENERATED_TABLES
        },
    }
    _write_json(backup_dir / "manifest.json", manifest)
    return manifest, preserved_bytes


def _load_reviewed_manifest(backup_dir: Path, client_id: str) -> dict[str, Any]:
    path = backup_dir / "manifest.json"
    try:
        manifest = json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        raise ResetVerificationError(
            "a valid reviewed dry-run manifest is required before execute"
        ) from exc
    required = {
        "client_id",
        "mode",
        "preserved_fingerprints",
        "auth_users_complete_fingerprints",
    }
    if (
        not isinstance(manifest, dict)
        or not required.issubset(manifest)
        or manifest["client_id"] != client_id
        or manifest["mode"] != "dry_run"
    ):
        raise ResetVerificationError(
            "reviewed dry-run manifest does not match this client"
        )
    return manifest


def _verify_reviewed_snapshot(
    reviewed: dict[str, Any],
    snapshot: dict[str, list[dict[str, Any]]],
    auth_complete_fingerprints: list[dict[str, Any]],
) -> None:
    current = {
        table: _fingerprint(snapshot[table]) for table in PRESERVED_TABLES
    }
    if current != reviewed["preserved_fingerprints"]:
        raise ResetVerificationError(
            "preserved rows differ from the reviewed dry-run manifest"
        )
    if (
        auth_complete_fingerprints
        != reviewed["auth_users_complete_fingerprints"]
    ):
        raise ResetVerificationError(
            "auth_users differ from the reviewed dry-run manifest"
        )


def _delete_generated(connection: Any, client_id: str) -> None:
    for table in DELETE_ORDER:
        with connection.cursor() as cursor:
            cursor.execute(DELETE_SQL[table], {"client_id": client_id})


def _verify_empty(connection: Any, client_id: str) -> dict[str, int]:
    counts = {
        table: len(_fetch_rows(connection, table, client_id))
        for table in GENERATED_TABLES
    }
    nonempty = {table: count for table, count in counts.items() if count}
    if nonempty:
        details = ", ".join(
            f"{table}={count}" for table, count in nonempty.items()
        )
        raise ResetVerificationError(
            f"generated rows remain after deletion: {details}"
        )
    return counts


def _verify_preserved(
    connection: Any,
    client_id: str,
    before: dict[str, bytes],
    auth_before: list[dict[str, Any]],
) -> dict[str, str]:
    after_fingerprints = {}
    for table in PRESERVED_TABLES:
        rows = _fetch_rows(connection, table, client_id)
        serialized = canonical_json(rows)
        if serialized != before[table]:
            raise ResetVerificationError(
                f"preserved table changed during reset: {table}"
            )
        after_fingerprints[table] = _fingerprint(rows)
    auth_after = _fetch_complete_auth_fingerprints(connection, client_id)
    if auth_after != auth_before:
        raise ResetVerificationError(
            "preserved table changed during reset: auth_users complete row"
        )
    return after_fingerprints


def run_reset(
    args: argparse.Namespace,
    *,
    db_url: str,
    connect: Callable[..., Any] = psycopg.connect,
) -> dict[str, Any]:
    """Run a dry-run export or a confirmed transactional client reset."""
    backup_dir = Path(args.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "format_version": 1,
        "client_id": args.client_id,
        "mode": "execute" if args.execute else "dry_run",
    }
    ready_to_commit = False

    try:
        reviewed_manifest = (
            _load_reviewed_manifest(backup_dir, args.client_id)
            if args.execute
            else None
        )
        with connect(
            db_url,
            autocommit=not args.execute,
            row_factory=dict_row,
        ) as connection:
            if not args.execute:
                snapshot = _capture(connection, args.client_id)
                _validate_client_selection(snapshot)
                auth_fingerprints = _fetch_complete_auth_fingerprints(
                    connection, args.client_id
                )
                manifest, _ = _export_snapshot(
                    backup_dir,
                    args.client_id,
                    False,
                    snapshot,
                    auth_fingerprints,
                )
                report.update(
                    {
                        "status": "dry_run_complete",
                        "deletion_performed": False,
                        "before_generated_counts": manifest["generated_counts"],
                        "after_generated_counts": None,
                        "preservation_verified": False,
                    }
                )
            else:
                with connection.transaction():
                    snapshot = _capture(connection, args.client_id)
                    _validate_client_selection(snapshot)
                    auth_before = _fetch_complete_auth_fingerprints(
                        connection, args.client_id
                    )
                    _verify_reviewed_snapshot(
                        reviewed_manifest,
                        snapshot,
                        auth_before,
                    )
                    manifest, preserved_bytes = _export_snapshot(
                        backup_dir / "execute",
                        args.client_id,
                        True,
                        snapshot,
                        auth_before,
                    )
                    _delete_generated(connection, args.client_id)
                    after_counts = _verify_empty(connection, args.client_id)
                    after_fingerprints = _verify_preserved(
                        connection,
                        args.client_id,
                        preserved_bytes,
                        auth_before,
                    )
                    report.update(
                        {
                            "status": "verified",
                            "deletion_performed": True,
                            "before_generated_counts": manifest[
                                "generated_counts"
                            ],
                            "after_generated_counts": after_counts,
                            "before_preserved_fingerprints": manifest[
                                "preserved_fingerprints"
                            ],
                            "after_preserved_fingerprints": after_fingerprints,
                            "preservation_verified": True,
                        }
                    )
                    ready_to_commit = True
    except ResetVerificationError as exc:
        report.update(
            {
                "status": "rolled_back" if args.execute else "validation_failed",
                "deletion_performed": False,
                "preservation_verified": False,
                "error": str(exc),
            }
        )
        _write_failure_report(backup_dir / "verification.json", report)
        raise
    except Exception:
        report.update(
            {
                "status": "failed",
                "deletion_performed": False,
                "preservation_verified": False,
                "transaction_state": (
                    "commit_unconfirmed"
                    if ready_to_commit
                    else "rolled_back_or_not_started"
                ),
                "error": "reset operation failed; exception details omitted",
            }
        )
        _write_failure_report(backup_dir / "verification.json", report)
        raise

    _write_json(backup_dir / "verification.json", report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("SUPABASE_DB_URL is required")
    report = run_reset(args, db_url=db_url)
    print(json.dumps(report, default=str, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
