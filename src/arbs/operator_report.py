"""Create a read-only operator report from an integrity-checked replay artifact."""
from __future__ import annotations

import argparse
import html
from pathlib import Path

from arbs.replay import load_match_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = load_match_report(args.report)
    rows = []
    for m in report["matches"]:
        reasons = ", ".join(m["review_reasons"])
        rows.append(f"<tr><td>{html.escape(m['start_utc'])}</td><td>{' ↔ '.join(m['participants'])}</td>"
                    f"<td><a href='{html.escape(m['kalshi']['source_url'])}'>Kalshi</a></td>"
                    f"<td><a href='{html.escape(m['polymarket']['source_url'])}'>Polymarket</a></td>"
                    f"<td>{html.escape(m['decision'])}</td><td>{html.escape(reasons)}</td><td>disabled</td></tr>")
    content = f"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width'>
<title>Arbs operator review</title><style>body{{font:14px system-ui;background:#09111f;color:#e7eef9;margin:2rem}}table{{border-collapse:collapse;width:100%}}td,th{{padding:.6rem;border-bottom:1px solid #334155;text-align:left}}a{{color:#67e8f9}}.safe{{padding:1rem;background:#3f1d2e;border-radius:8px}}</style></head><body>
<h1>Read-only operator review</h1><p class=safe><b>Mutation disabled.</b> Event matches are REVIEW; pricing and trading are disabled. Captured {html.escape(report['generated_at'])}.</p>
<table><thead><tr><th>UTC</th><th>Participants</th><th>Sources</th><th></th><th>Decision</th><th>Reasons</th><th>Opportunity</th></tr></thead><tbody>{''.join(rows)}</tbody></table></body></html>"""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(f"rendered {len(rows)} read-only decisions")
    return 0


if __name__ == "__main__": raise SystemExit(main())
