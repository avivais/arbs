#!/usr/bin/env python3
"""Render an immutable live-matching checkpoint report as standalone HTML."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.report.read_text(encoding="utf-8"))
    rows = []
    for match in data["matches"]:
        teams = " ↔ ".join(match["participants"])
        k, p = match["kalshi"], match["polymarket"]
        rows.append(f"""<tr><td>{html.escape(match['start_utc'])}</td><td><strong>{html.escape(teams)}</strong></td>
<td><a href="{html.escape(k['source_url'])}">{html.escape(k['event_id'])}</a></td>
<td><a href="{html.escape(p['source_url'])}">{html.escape(p['event_id'])}</a></td>
<td>{match['start_delta_seconds']}s</td><td><span class="review">{html.escape(match['decision'])}</span></td></tr>""")
    counts = data["counts"]
    document = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Arbs Live Cross-Venue Matches</title><style>
:root{{--bg:#09111f;--card:#111c2e;--text:#e8eef9;--muted:#9fb0c9;--line:#263650;--cyan:#5de4c7;--amber:#ffca6b}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif}}main{{max-width:1250px;margin:auto;padding:32px 18px}}
h1{{margin-bottom:4px}}.muted{{color:var(--muted)}}.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:24px 0}}.stat,.notice{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}}.number{{font-size:28px;font-weight:800;color:var(--cyan)}}
.notice{{border-left:4px solid var(--amber);margin:18px 0}}.wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:12px}}table{{width:100%;border-collapse:collapse;background:var(--card)}}th,td{{padding:12px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}}th{{position:sticky;top:0;background:#16243a}}a{{color:var(--cyan)}}.review{{color:#17120a;background:var(--amber);font-weight:800;padding:3px 8px;border-radius:999px}}code{{color:var(--cyan);overflow-wrap:anywhere}}
</style></head><body><main><h1>Live matched markets across venues</h1><p class="muted">Arbs read-only MLB checkpoint · captured {html.escape(data['generated_at'])}</p>
<div class="stats"><div class="stat"><div class="number">{counts['matched_events']}</div>matched events</div><div class="stat"><div class="number">{counts['kalshi_normalized_events']}</div>Kalshi events</div><div class="stat"><div class="number">{counts['polymarket_normalized_events']}</div>Polymarket events</div></div>
<div class="notice"><strong>Safety status: event identity matched, pricing disabled.</strong><br>Every row is <b>REVIEW</b>, not EXACT, because cancellation/postponement payout equivalence is not yet proven. No order or account action was performed.</div>
<div class="wrap"><table><thead><tr><th>Scheduled UTC</th><th>Participants</th><th>Kalshi event</th><th>Polymarket event</th><th>Start delta</th><th>Decision</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="muted">Audit report SHA-256: <code>{html.escape(data['report_sha256'])}</code></p></main></body></html>"""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(document, encoding="utf-8")
    print(f"rendered {len(rows)} matches to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
