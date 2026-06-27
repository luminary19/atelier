# -*- coding: utf-8 -*-
"""
forge-data search — BM25 lookup over curated 3D production datasets.

Pure stdlib. No network calls. Windows: use `python`, not `python3`.

Usage:
  python search.py "<query>" [--domain <domain>] [-n 3] [--json]

Domains: tools, polycount, texel, format, material, gotchas

Keep -n small (<= 5). --json bypasses per-field 300-char truncation — use only
when the caller needs machine-parseable output.
"""

import sys
import io
import argparse
import json

# Force UTF-8 stdout/stderr on Windows (default is cp1252)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    from core import CSV_CONFIG, AVAILABLE_DOMAINS, MAX_RESULTS, search, detect_domain
except ImportError:
    # Allow running from a different cwd by adding scripts/ to path
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from core import CSV_CONFIG, AVAILABLE_DOMAINS, MAX_RESULTS, search, detect_domain


def format_output(result: dict) -> str:
    """Format results for Claude context consumption (token-optimized, 300-char field cap)."""
    if "error" in result:
        return f"[forge-data] Error: {result['error']}"

    lines = [
        "## forge-data Search Results",
        f"**Domain:** {result['domain']} | **Query:** {result['query']}",
        f"**Source:** {result['file']} | **Found:** {result['count']} results",
        "",
    ]
    for i, row in enumerate(result["results"], 1):
        lines.append(f"### Result {i}")
        for key, value in row.items():
            value_str = str(value)
            if len(value_str) > 300:
                value_str = value_str[:300] + "..."
            lines.append(f"- **{key}:** {value_str}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="forge-data search (BM25 over 3D production datasets). "
                    "Windows: use `python`, not `python3`."
    )
    parser.add_argument("query", help="Search query (e.g. 'mobile hero polycount')")
    parser.add_argument(
        "--domain", "-d",
        choices=AVAILABLE_DOMAINS,
        help=f"Search domain. Available: {', '.join(AVAILABLE_DOMAINS)}. "
             "Auto-detected if omitted.",
    )
    parser.add_argument(
        "--max-results", "-n",
        type=int,
        default=MAX_RESULTS,
        help=f"Max results to return (default: {MAX_RESULTS}). Keep <= 5.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON (bypasses per-field 300-char truncation).",
    )
    args = parser.parse_args()

    result = search(args.query, args.domain, args.max_results)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_output(result))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[forge-data] Unexpected error: {exc}", file=sys.stderr)
        sys.exit(0)  # advisory scripts always exit 0
