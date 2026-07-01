import csv
import html
import json
from datetime import datetime, timezone
from pathlib import Path


CSV_FIELDS = [
    "query",
    "engine",
    "model",
    "run_number",
    "brand_mentioned",
    "brand_cited",
    "citation_url",
    "mention_level",
    "mention_level_label",
    "competitor_mentions",
    "response_text",
    "timestamp",
]


def write_csv(results: list[dict], output_path: Path) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for r in results:
            row = {k: r.get(k, "") for k in CSV_FIELDS}
            if isinstance(row["competitor_mentions"], list):
                row["competitor_mentions"] = "; ".join(row["competitor_mentions"])
            writer.writerow(row)


def write_json(
    results: list[dict],
    scores: dict,
    client_name: str,
    output_path: Path,
) -> None:
    report = {
        "client_name": client_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "visibility_scores": scores,
        "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


LEVEL_LABELS = {
    0: "Not Mentioned",
    1: "Passing Mention",
    2: "Listed with Context",
    3: "Recommended",
    4: "Primary Recommendation",
}


def format_summary(scores: dict, client_name: str) -> str:
    lines = [
        f"\n{'='*60}",
        f"  GEO Visibility Report: {client_name}",
        f"{'='*60}",
    ]
    for engine, es in scores["per_engine"].items():
        mention = es["mention_rate"]
        avg_lvl = es.get("avg_mention_level", 0)
        citation = es.get("citation_rate", 0)
        lvl_label = LEVEL_LABELS.get(round(avg_lvl), "—")
        lines.append(
            f"  {engine:<15} mention: {mention:>6.0%}   "
            f"avg level: {avg_lvl:.1f} ({lvl_label})   "
            f"citation: {citation:>6.0%}"
        )
    lines.append(f"{'─'*60}")
    agg_mention = scores["aggregate_mention_rate"]
    agg_level = scores.get("aggregate_avg_mention_level", 0)
    lvl_label = LEVEL_LABELS.get(round(agg_level), "—")
    lines.append(
        f"  {'AGGREGATE':<15} mention: {agg_mention:>6.0%}   "
        f"avg level: {agg_level:.1f} ({lvl_label})"
    )
    lines.append(f"{'='*60}")

    comp_scores = scores.get("competitor_scores", {})
    if comp_scores:
        lines.append(f"\n  {'Competitor Comparison':^58}")
        lines.append(f"{'─'*60}")
        lines.append(f"  {'Brand/Competitor':<30} {'Mention Rate':>16}")
        lines.append(f"{'─'*60}")
        lines.append(f"  {client_name:<30} {agg_mention:>15.0%}")
        for comp, cs in comp_scores.items():
            lines.append(f"  {comp:<30} {cs['mention_rate']:>15.0%}")
        lines.append(f"{'='*60}")

    lines.append("")
    return "\n".join(lines)


def _score_color(rate: float) -> str:
    if rate == 0:
        return "#dc3545"
    if rate < 0.25:
        return "#fd7e14"
    if rate < 0.50:
        return "#ffc107"
    return "#28a745"


def _level_color(level: float) -> str:
    if level < 1:
        return "#dc3545"
    if level < 2:
        return "#fd7e14"
    if level < 3:
        return "#ffc107"
    return "#28a745"


def _level_badge(level: int, label: str) -> str:
    colors = {
        0: ("#f8d7da", "#721c24"),
        1: ("#fff3cd", "#856404"),
        2: ("#d4edda", "#155724"),
        3: ("#d1ecf1", "#0c5460"),
        4: ("#cce5ff", "#004085"),
    }
    bg, fg = colors.get(level, ("#e2e3e5", "#383d41"))
    display = label.replace("_", " ").title()
    return f'<span class="badge" style="background:{bg};color:{fg}">{display}</span>'


def write_html(
    results: list[dict],
    scores: dict,
    client_name: str,
    output_path: Path,
) -> None:
    agg_mention = scores["aggregate_mention_rate"]
    agg_level = scores.get("aggregate_avg_mention_level", 0)
    comp_scores = scores.get("competitor_scores", {})
    per_engine = scores["per_engine"]
    generated = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    queries = []
    seen = set()
    for r in results:
        if r["query"] not in seen:
            queries.append(r["query"])
            seen.add(r["query"])

    engine_cards = ""
    for eng, es in per_engine.items():
        m_color = _score_color(es["mention_rate"])
        l_color = _level_color(es.get("avg_mention_level", 0))
        c_rate = es.get("citation_rate", 0)
        engine_cards += f"""
        <div class="engine-card">
            <div class="engine-name">{html.escape(eng)}</div>
            <div class="engine-score" style="color:{m_color}">{es['mention_rate']:.0%}</div>
            <div class="engine-label">mention rate</div>
            <div style="font-size:18px;font-weight:600;color:{l_color};margin-top:4px">
                {es.get('avg_mention_level', 0):.1f}
            </div>
            <div class="engine-label">avg level</div>
            <div style="font-size:14px;color:#86868b;margin-top:4px">{c_rate:.0%} citation</div>
        </div>"""

    comp_rows = ""
    if comp_scores:
        brand_color = _score_color(agg_mention)
        comp_rows += f"""
            <tr class="brand-row">
                <td><strong>{html.escape(client_name)}</strong></td>
                <td><span style="color:{brand_color};font-weight:700">{agg_mention:.0%}</span></td>
            </tr>"""
        for comp, cs in sorted(comp_scores.items(), key=lambda x: -x[1]["mention_rate"]):
            c_color = _score_color(cs["mention_rate"])
            comp_rows += f"""
            <tr>
                <td>{html.escape(comp)}</td>
                <td><span style="color:{c_color};font-weight:700">{cs['mention_rate']:.0%}</span></td>
            </tr>"""

    query_sections = ""
    for query in queries:
        query_results = [r for r in results if r["query"] == query]
        engine_blocks = ""
        for r in query_results:
            level_badge = _level_badge(r.get("mention_level", 0), r.get("mention_level_label", "not_mentioned"))
            comps = ", ".join(r["competitor_mentions"]) if r["competitor_mentions"] else "none"
            resp = html.escape(r["response_text"])
            run_num = r.get("run_number", "")
            engine_blocks += f"""
                <details>
                    <summary>
                        <span class="engine-tag">{html.escape(r['engine'])}</span>
                        <span style="font-size:11px;color:#86868b">Run {run_num}</span>
                        {level_badge}
                        <span class="competitors-tag">competitors: {html.escape(comps)}</span>
                    </summary>
                    <div class="response-text">{resp}</div>
                </details>"""

        query_sections += f"""
        <div class="query-section">
            <h3>{html.escape(query)}</h3>
            {engine_blocks}
        </div>"""

    lvl_label = LEVEL_LABELS.get(round(agg_level), "—")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GEO Report: {html.escape(client_name)}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       max-width: 1100px; margin: 0 auto; padding: 24px; background: #f5f5f7; color: #1d1d1f; }}
h1 {{ font-size: 28px; margin-bottom: 4px; }}
.subtitle {{ color: #86868b; font-size: 14px; margin-bottom: 24px; }}
.dashboard {{ display: flex; gap: 20px; margin-bottom: 32px; flex-wrap: wrap; }}
.score-card {{ background: #fff; border-radius: 12px; padding: 24px; flex: 1; min-width: 200px;
               box-shadow: 0 1px 3px rgba(0,0,0,0.08); text-align: center; }}
.score-card .label {{ font-size: 13px; color: #86868b; text-transform: uppercase; letter-spacing: 0.5px; }}
.score-card .value {{ font-size: 48px; font-weight: 700; margin: 8px 0; }}
.score-card .detail {{ font-size: 13px; color: #86868b; }}
.engines-row {{ display: flex; gap: 12px; margin-bottom: 32px; flex-wrap: wrap; }}
.engine-card {{ background: #fff; border-radius: 10px; padding: 16px; flex: 1; min-width: 140px;
               box-shadow: 0 1px 3px rgba(0,0,0,0.08); text-align: center; }}
.engine-name {{ font-size: 13px; color: #86868b; text-transform: uppercase; letter-spacing: 0.5px; }}
.engine-score {{ font-size: 32px; font-weight: 700; margin: 4px 0; }}
.engine-label {{ font-size: 11px; color: #aeaeb2; }}
.comp-section {{ background: #fff; border-radius: 12px; padding: 24px; margin-bottom: 32px;
                 box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
.comp-section h2 {{ font-size: 18px; margin-bottom: 16px; }}
.comp-table {{ width: 100%; border-collapse: collapse; }}
.comp-table th {{ text-align: left; padding: 8px 12px; font-size: 12px; color: #86868b;
                  text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid #f0f0f0; }}
.comp-table td {{ padding: 10px 12px; border-bottom: 1px solid #f5f5f7; font-size: 15px; }}
.comp-table .brand-row td {{ background: #f0f7ff; }}
.query-section {{ background: #fff; border-radius: 12px; padding: 24px; margin-bottom: 16px;
                  box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
.query-section h3 {{ font-size: 16px; margin-bottom: 12px; color: #1d1d1f; }}
details {{ border: 1px solid #e5e5ea; border-radius: 8px; margin: 8px 0; }}
summary {{ padding: 10px 14px; cursor: pointer; display: flex; align-items: center; gap: 10px;
           font-size: 14px; background: #fafafa; border-radius: 8px; }}
summary:hover {{ background: #f0f0f0; }}
details[open] summary {{ border-bottom: 1px solid #e5e5ea; border-radius: 8px 8px 0 0; }}
.engine-tag {{ font-weight: 600; min-width: 90px; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px;
          font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }}
.competitors-tag {{ font-size: 12px; color: #86868b; margin-left: auto; }}
.response-text {{ padding: 16px; font-size: 14px; line-height: 1.7; white-space: pre-wrap;
                  word-wrap: break-word; max-height: 500px; overflow-y: auto; color: #333; }}
</style>
</head>
<body>

<h1>GEO Visibility Report: {html.escape(client_name)}</h1>
<div class="subtitle">Generated {generated}</div>

<div class="dashboard">
    <div class="score-card">
        <div class="label">Mention Rate</div>
        <div class="value" style="color:{_score_color(agg_mention)}">{agg_mention:.0%}</div>
        <div class="detail">across all engines &amp; queries</div>
    </div>
    <div class="score-card">
        <div class="label">Avg Mention Level</div>
        <div class="value" style="color:{_level_color(agg_level)}">{agg_level:.1f}</div>
        <div class="detail">{lvl_label}</div>
    </div>
    <div class="score-card">
        <div class="label">Queries Tracked</div>
        <div class="value" style="color:#1d1d1f">{len(queries)}</div>
        <div class="detail">across {len(per_engine)} engines &middot; 5 runs each</div>
    </div>
</div>

<div class="engines-row">{engine_cards}
</div>

{"" if not comp_scores else "COMP_SECTION_PLACEHOLDER"}

<h2 style="font-size:20px; margin-bottom:16px;">Query Results</h2>
{query_sections}

</body>
</html>"""

    # Handle competitor section separately to avoid nested f-string issues
    if comp_scores:
        comp_section = f"""
<div class="comp-section">
    <h2>Competitor Comparison</h2>
    <table class="comp-table">
        <thead><tr><th>Brand / Competitor</th><th>Mention Rate</th></tr></thead>
        <tbody>{comp_rows}
        </tbody>
    </table>
</div>
"""
        page = page.replace("COMP_SECTION_PLACEHOLDER", comp_section)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page)
