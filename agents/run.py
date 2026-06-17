import argparse
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.tracker import load_client_config, run_tracker
from src.output import write_csv, write_json, write_html, format_summary


def main():
    parser = argparse.ArgumentParser(description="GEO Tracker Agent")
    parser.add_argument("config", help="Path to client config JSON file")
    parser.add_argument(
        "--output-dir",
        default="../output",
        help="Directory for output files (default: ../output)",
    )
    args = parser.parse_args()

    config = load_client_config(args.config)
    client_name = config["client_name"]

    print(f"\n  GEO Tracker — {client_name}")
    print(f"  Queries: {len(config['target_queries'])}")
    print(f"  Brand: {config['brand_name']}")
    print()

    results, scores = run_tracker(config)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = client_name.lower().replace(" ", "_")

    csv_path = output_dir / f"{slug}_{timestamp}.csv"
    json_path = output_dir / f"{slug}_{timestamp}.json"
    html_path = output_dir / f"{slug}_{timestamp}.html"

    write_csv(results, csv_path)
    write_json(results, scores, client_name, json_path)
    write_html(results, scores, client_name, html_path)

    print(format_summary(scores, client_name))
    print(f"  HTML: {html_path}")
    print(f"  CSV:  {csv_path}")
    print(f"  JSON: {json_path}")


if __name__ == "__main__":
    main()
