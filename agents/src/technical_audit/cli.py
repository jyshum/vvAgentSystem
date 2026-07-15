from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .collector import Fetcher, collect_site
from .evidence.performance import collect_integrations
from .pipeline import DEFAULT_CHECK_SETS, run_technical_pipeline
from .runner import run_technical_audit
from .site import SiteIdentity


MAX_ARTIFACT_BYTES = 2_000_000


def _parse_check_sets(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return DEFAULT_CHECK_SETS
    return tuple(name.strip() for name in raw.split(",") if name.strip())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic technical audits")
    commands = parser.add_subparsers(dest="command", required=True)

    smoke = commands.add_parser("smoke", help="collect without database persistence")
    smoke.add_argument("--domain", required=True)
    smoke.add_argument("--platform", required=True)
    smoke.add_argument("--output", type=Path, required=True)
    smoke.add_argument(
        "--check-sets",
        default=None,
        help="comma-separated check sets (default: all four)",
    )

    persisted = commands.add_parser("run", help="persist an audit for a configured client")
    persisted.add_argument("--client-id", required=True)
    persisted.add_argument(
        "--check-sets",
        default=None,
        help="comma-separated check sets (default: all four)",
    )
    return parser


def _write_report(path: Path, report: dict) -> None:
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True).encode(
        "utf-8"
    )
    if len(payload) > MAX_ARTIFACT_BYTES:
        raise ValueError("technical audit artifact exceeded its byte limit")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_bytes(payload)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _load_persisted_context(client_id: str) -> tuple[dict, list[dict], list[dict]]:
    from os import environ

    from supabase import create_client

    sb = create_client(environ["SUPABASE_URL"], environ["SUPABASE_SERVICE_KEY"])
    client_response = (
        sb.table("clients")
        .select(
            "id,brand_name,website_domain,brand_variations,competitors,"
            "gsc_site_url,site_platform,implementation_mode"
        )
        .eq("id", client_id)
        .maybe_single()
        .execute()
    )
    if not client_response.data:
        raise ValueError("configured client was not found")
    client = client_response.data

    queries_response = (
        sb.table("queries")
        .select("id,prompt_text,paraphrases,bucket,set_type,slug,version")
        .eq("client_id", client_id)
        .eq("status", "active")
        .order("bucket")
        .order("created_at")
        .execute()
    )
    queries = queries_response.data or []

    latest_response = (
        sb.table("tracker_runs")
        .select("id")
        .eq("client_id", client_id)
        .order("ran_at", desc=True)
        .limit(1)
        .execute()
    )
    competitive_gaps: list[dict] = []
    if latest_response.data:
        gaps_response = (
            sb.table("competitive_gaps")
            .select("*")
            .eq("run_id", latest_response.data[0]["id"])
            .execute()
        )
        competitive_gaps = gaps_response.data or []

    state = {
        "client_id": client_id,
        "thread_id": None,
        "client_config": {
            "brand_name": client["brand_name"],
            "website_domain": client["website_domain"],
            "site_platform": client.get("site_platform") or "other",
            "implementation_mode": client.get("implementation_mode") or "copy_paste",
            "brand_variations": client.get("brand_variations") or [],
            "competitors": client.get("competitors") or [],
            "gsc_site_url": client.get("gsc_site_url") or "",
            "target_queries": queries,
        },
    }
    return state, queries, competitive_gaps


def _smoke(args: argparse.Namespace, fetcher: Fetcher | None) -> int:
    check_sets = _parse_check_sets(args.check_sets)
    identity = SiteIdentity.from_domain(args.domain, args.platform)
    collected = collect_site(identity, fetcher=fetcher)
    integrations = None
    if "performance" in check_sets and fetcher is None:
        # Smoke has no configured GSC property; keys drive real API calls only
        # when present, otherwise checks become explicit unknowns.
        integrations = collect_integrations(collected, "")
    report = run_technical_audit(
        "smoke", identity, collected,
        enabled_check_sets=check_sets, integrations=integrations,
    )
    _write_report(args.output, report)
    return 0 if report["summary"].get("total", 0) else 1


def _run(args: argparse.Namespace) -> int:
    state, queries, competitive_gaps = _load_persisted_context(args.client_id)
    result = run_technical_pipeline(
        state, queries, competitive_gaps, check_sets=_parse_check_sets(args.check_sets)
    )
    summary = {
        "improvement_run_id": result.get("improvement_run_id"),
        "technical_audit_run_id": result.get("technical_audit_run_id"),
        "technical_audit_summary": result.get("technical_audit_summary", {}),
        "technical_audit_error": bool(result.get("technical_audit_error")),
    }
    print(json.dumps(summary, sort_keys=True))
    return 1 if result.get("error") or result.get("technical_audit_error") else 0


def main(argv: Sequence[str] | None = None, *, fetcher: Fetcher | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "smoke":
            return _smoke(args, fetcher)
        return _run(args)
    except Exception as exc:
        print(f"technical audit failed ({type(exc).__name__})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
