#!/usr/bin/env python3
"""Render source-backed review pages. Optional documentation dependency: Markdown."""
from pathlib import Path
import html
import markdown

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('validation-verdict', 'matching-independent-review', 'settlement-eligibility-review')
STYLE = '''body{margin:0;background:#101827;color:#e6edf7;font:16px/1.65 system-ui,sans-serif}main{max-width:1000px;margin:auto;padding:36px 22px}h1{font-size:clamp(26px,5vw,40px);line-height:1.2}h2{margin-top:2em;color:#91d8d0}a{color:#8fc7ff;overflow-wrap:anywhere}code{overflow-wrap:anywhere;font-size:.88em}table{display:block;overflow-x:auto;border-collapse:collapse;width:100%;margin:22px 0}td,th{padding:12px;text-align:left;border:1px solid #344257;min-width:110px}th{background:#1f2d42}p,li{overflow-wrap:anywhere}nav{display:flex;gap:20px;flex-wrap:wrap}strong{color:white}footer{margin-top:40px;border-top:1px solid #344257;padding-top:18px;color:#a9b6c9}@media print{body{background:white;color:black}h2,strong{color:black}a{color:#135}main{max-width:none}table{display:table;font-size:11px}}'''
for name in NAMES:
    source = (ROOT / f'docs/{name}.md').read_text()
    title = source.splitlines()[0].removeprefix('# ')
    body = markdown.markdown(source, extensions=['tables', 'fenced_code'])
    for linked in NAMES:
        body = body.replace(f'href="{linked}.md"', f'href="{linked}.html"')
    page = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(title)}</title><style>{STYLE}</style></head><body><main><nav><a href="validation-verdict.html">Verdict</a><a href="matching-independent-review.html">Identity review</a><a href="settlement-eligibility-review.html">Settlement review</a><a href="rolling-plan.html">Project plan</a></nav>{body}<footer>Read-only technical evidence · no trading or eligibility promotion · <a href="{name}.md">Markdown source</a></footer></main></body></html>\n'
    (ROOT / f'docs/{name}.html').write_text(page)
    print(f'Rendered docs/{name}.html')
