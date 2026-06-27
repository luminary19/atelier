# -*- coding: utf-8 -*-
"""
atelier-data search - BM25 lookup over curated design datasets.

Derived from UI/UX Pro Max v2.5.0 (search.py), (c) 2024 Next Level Builder, MIT.
The design-system *generator* (design_system.py) was intentionally NOT adopted:
token output (raw hex, --color-* names) conflicts with atelier-foundations (OKLCH,
shadcn --primary). Use atelier-foundations to build the actual system.

Usage (Windows: use `python`, not `python3`):
  python search.py "<query>" [--domain <domain>] [--stack <stack>] [--max-results 3]

Domains: style, color, chart, landing, product, reasoning, ux, typography, react, google-fonts
Stacks:  react, nextjs, vue, shadcn, threejs

Keep --max-results small (<=5) and avoid --json for large domains: results inject
into context, and --json bypasses the per-field 300-char truncation.
"""

import argparse
import sys
import io
from core import CSV_CONFIG, AVAILABLE_STACKS, MAX_RESULTS, search, search_stack

# Force UTF-8 for stdout/stderr to handle emojis on Windows (cp1252 default)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def format_output(result):
    """Format results for Claude consumption (token-optimized)"""
    if "error" in result:
        return f"Error: {result['error']}"

    output = []
    if result.get("stack"):
        output.append(f"## atelier-data Stack Guidelines")
        output.append(f"**Stack:** {result['stack']} | **Query:** {result['query']}")
    else:
        output.append(f"## atelier-data Search Results")
        output.append(f"**Domain:** {result['domain']} | **Query:** {result['query']}")
    output.append(f"**Source:** {result['file']} | **Found:** {result['count']} results\n")

    for i, row in enumerate(result['results'], 1):
        output.append(f"### Result {i}")
        for key, value in row.items():
            value_str = str(value)
            if len(value_str) > 300:
                value_str = value_str[:300] + "..."
            output.append(f"- **{key}:** {value_str}")
        output.append("")

    return "\n".join(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="atelier-data search (BM25 over design datasets)")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--domain", "-d", choices=list(CSV_CONFIG.keys()), help="Search domain")
    parser.add_argument("--stack", "-s", choices=AVAILABLE_STACKS, help=f"Stack-specific search. Available: {', '.join(AVAILABLE_STACKS)}")
    parser.add_argument("--max-results", "-n", type=int, default=MAX_RESULTS, help="Max results (default: 3)")
    parser.add_argument("--json", action="store_true", help="Output as JSON (bypasses 300-char field truncation)")

    args = parser.parse_args()

    if args.stack:
        result = search_stack(args.query, args.stack, args.max_results)
    else:
        result = search(args.query, args.domain, args.max_results)

    if args.json:
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_output(result))
