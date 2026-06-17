import csv
import html
import json
from datetime import datetime, timezone
from pathlib import Path


CSV_FIELDS = [
    "query",
    "engine",
    "model",
    "brand_mentioned",
    "brand_cited",
    "citation_url",
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


def format_summary(scores: dict, client_name: str) -> str:
    lines = [
        f"\n{'='*50}",
        f"  GEO Visibility Report: {client_name}",
        f"{'='*50}",
    ]
    for engine, engine_scores in scores["per_engine"].items():
        mention = engine_scores["mention_rate"]
        citation = engine_scores["citation_rate"]
        lines.append(f"  {engine:<15} mention: {mention:>6.0%}   cited: {citation:>6.0%}")
    lines.append(f"{'─'*50}")
    agg_mention = scores["aggregate_mention_rate"]
    agg_citation = scores["aggregate_citation_rate"]
    lines.append(f"  {'AGGREGATE':<15} mention: {agg_mention:>6.0%}   cited: {agg_citation:>6.0%}")
    lines.append(f"{'='*50}")

    comp_scores = scores.get("competitor_scores", {})
    if comp_scores:
        lines.append(f"\n  {'Competitor Comparison':^48}")
        lines.append(f"{'─'*50}")
        lines.append(f"  {'Brand/Competitor':<30} {'Mention Rate':>16}")
        lines.append(f"{'─'*50}")
        lines.append(f"  {client_name:<30} {agg_mention:>15.0%}")
        for comp, cs in comp_scores.items():
            lines.append(f"  {comp:<30} {cs['mention_rate']:>15.0%}")
        lines.append(f"{'='*50}")

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


def _badge(mentioned: bool, cited: bool) -> str:
    if cited:
        return '<span class="badge cited">CITED</span>'
    if mentioned:
        return '<span class="badge mentioned">MENTIONED</span>'
    return '<span class="badge not-found">NOT FOUND</span>'


def write_html(
    results: list[dict],
    scores: dict,
    client_name: str,
    output_path: Path,
) -> None:
    agg_mention = scores["aggregate_mention_rate"]
    agg_citation = scores["aggregate_citation_rate"]
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
        color = _score_color(es["mention_rate"])
        engine_cards += f"""
        <div class="engine-card">
            <div class="engine-name">{html.escape(eng)}</div>
            <div class="engine-score" style="color:{color}">{es['mention_rate']:.0%}</div>
            <div class="engine-label">mention rate</div>
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
            badge = _badge(r["brand_mentioned"], r["brand_cited"])
            comps = ", ".join(r["competitor_mentions"]) if r["competitor_mentions"] else "none"
            resp = html.escape(r["response_text"])
            engine_blocks += f"""
                <details>
                    <summary>
                        <span class="engine-tag">{html.escape(r['engine'])}</span>
                        {badge}
                        <span class="competitors-tag">competitors: {html.escape(comps)}</span>
                    </summary>
                    <div class="response-text">{resp}</div>
                </details>"""

        query_sections += f"""
        <div class="query-section">
            <h3>{html.escape(query)}</h3>
            {engine_blocks}
        </div>"""

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
.badge.cited {{ background: #d1ecf1; color: #0c5460; }}
.badge.mentioned {{ background: #d4edda; color: #155724; }}
.badge.not-found {{ background: #f8d7da; color: #721c24; }}
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
        <div class="label">Aggregate Mention Rate</div>
        <div class="value" style="color:{_score_color(agg_mention)}">{agg_mention:.0%}</div>
        <div class="detail">across all engines &amp; queries</div>
    </div>
    <div class="score-card">
        <div class="label">Citation Rate</div>
        <div class="value" style="color:{_score_color(agg_citation)}">{agg_citation:.0%}</div>
        <div class="detail">linked to {html.escape(client_name)}'s website</div>
    </div>
    <div class="score-card">
        <div class="label">Queries Tracked</div>
        <div class="value" style="color:#1d1d1f">{len(queries)}</div>
        <div class="detail">across {len(per_engine)} engines</div>
    </div>
</div>

<div class="engines-row">{engine_cards}
</div>

{"" if not comp_scores else f'''
<div class="comp-section">
    <h2>Competitor Comparison</h2>
    <table class="comp-table">
        <thead><tr><th>Brand / Competitor</th><th>Mention Rate</th></tr></thead>
        <tbody>{comp_rows}
        </tbody>
    </table>
</div>
'''}

<h2 style="font-size:20px; margin-bottom:16px;">Query Results</h2>
{query_sections}

</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page)
