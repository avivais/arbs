#!/usr/bin/env python3
"""Render and validate the Arbs rolling plan from its canonical JSON source."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/rolling-plan.json"
MARKDOWN = ROOT / "docs/ROLLING_PLAN.md"
HTML = ROOT / "docs/rolling-plan.html"
STATUSES = {"done", "in_progress", "next", "blocked", "deferred"}
LABELS = {"done":"Done", "in_progress":"In progress", "next":"Next", "blocked":"Blocked", "deferred":"Deferred"}


def load() -> dict[str, Any]:
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def tasks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [task | {"phase_id": phase["id"], "phase_name": phase["name"]}
            for phase in plan["phases"] for task in phase["tasks"]]


def validate(plan: dict[str, Any]) -> None:
    required = {"schema_version", "plan_id", "project", "last_verified", "source_of_truth", "mission", "current_focus", "next_action", "phases"}
    missing = required - plan.keys()
    if missing:
        raise ValueError(f"missing root fields: {sorted(missing)}")
    all_tasks = tasks(plan)
    ids = [item["id"] for item in all_tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("task IDs must be unique")
    bad = [(item["id"], item["status"]) for item in all_tasks if item["status"] not in STATUSES]
    if bad:
        raise ValueError(f"invalid task statuses: {bad}")
    active = [item["id"] for item in all_tasks if item["status"] == "in_progress"]
    if len(active) != 1:
        raise ValueError(f"exactly one task must be in_progress, found {active}")
    if not plan["next_action"].startswith(active[0]):
        raise ValueError("next_action must identify the sole in-progress task")
    for item in all_tasks:
        if not item.get("acceptance"):
            raise ValueError(f"{item['id']} lacks acceptance criteria")
        if item["status"] == "done" and not item.get("evidence"):
            raise ValueError(f"completed task {item['id']} lacks evidence")
    canonical = plan["source_of_truth"].get("canonical")
    if canonical != "docs/rolling-plan.json":
        raise ValueError("canonical source path changed unexpectedly")


def counts(plan: dict[str, Any]) -> Counter[str]:
    return Counter(item["status"] for item in tasks(plan))


def render_markdown(plan: dict[str, Any]) -> str:
    all_tasks, c = tasks(plan), counts(plan)
    done, total = c["done"], len(all_tasks)
    lines = [
        f"# {plan['project']} — Rolling Plan", "",
        f"> **Canonical source:** [`docs/rolling-plan.json`](rolling-plan.json) · **Last verified:** {plan['last_verified']}",
        "> Edit the JSON first, run `python3 scripts/render_rolling_plan.py`, validate, and commit all generated views together.", "",
        "## Live status", "",
        f"- **Progress:** {done}/{total} tasks source-verified complete ({done * 100 // total}%)",
        f"- **Current focus:** {plan['current_focus']}",
        f"- **Next action:** `{plan['next_action']}`", "",
        "| Done | In progress | Next | Blocked | Deferred |", "|---:|---:|---:|---:|---:|",
        f"| {c['done']} | {c['in_progress']} | {c['next']} | {c['blocked']} | {c['deferred']} |", "",
        "## Mission", "", plan["mission"], "", "## Operating rules", ""
    ]
    lines += [f"{i}. {rule}" for i, rule in enumerate(plan["operating_rules"], 1)]
    lines += ["", "## Milestones", "", "| ID | Milestone | Status | Exit gate |", "|---|---|---|---|"]
    lines += [f"| `{m['id']}` | {m['name']} | **{LABELS[m['status']]}** | {m['exit']} |" for m in plan["milestones"]]
    lines += ["", "## Delivery phases", ""]
    for phase in plan["phases"]:
        pc = Counter(t["status"] for t in phase["tasks"])
        lines += [f"### {phase['id']} — {phase['name']}", "", f"**Status:** {LABELS[phase['status']]} · **Progress:** {pc['done']}/{len(phase['tasks'])}", "", phase["objective"], ""]
        for item in phase["tasks"]:
            mark = "x" if item["status"] == "done" else " "
            lines += [f"- [{mark}] **{item['id']} — {item['title']}** `[{LABELS[item['status']]}]`", f"  - **Acceptance:** {item['acceptance']}"]
            if item.get("blocker"):
                lines += [f"  - **Blocker:** {item['blocker']}"]
            if item.get("evidence"):
                lines += ["  - **Evidence:** " + "; ".join(f"`{x}`" if "/" in x or ":" in x else x for x in item["evidence"])]
        lines.append("")
    lines += ["## Decisions", "", "| ID | Date | Decision | Why |", "|---|---|---|---|"]
    lines += [f"| `{d['id']}` | {d['date']} | {d['decision']} | {d['reason']} |" for d in plan["decisions"]]
    lines += ["", "## Risk register", "", "| ID | Severity | Risk | Mitigation |", "|---|---|---|---|"]
    lines += [f"| `{r['id']}` | **{r['severity'].upper()}** | {r['risk']} | {r['mitigation']} |" for r in plan["risks"]]
    lines += ["", "## Change log", ""] + [f"- **{x['date']}** — {x['change']}" for x in plan["change_log"]]
    lines += ["", "---", "", "The HTML view adds navigation and browser-local working checkboxes. Those local selections are not shared evidence and never change this source-verified plan.", ""]
    return "\n".join(lines)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_html(plan: dict[str, Any]) -> str:
    all_tasks, c = tasks(plan), counts(plan)
    total, done = len(all_tasks), c["done"]
    phase_nav, phase_html = [], []
    for phase in plan["phases"]:
        pc = Counter(t["status"] for t in phase["tasks"])
        phase_nav.append(f'<a href="#{esc(phase["id"])}"><span>{esc(phase["id"])}</span>{esc(phase["name"])}<b>{pc["done"]}/{len(phase["tasks"])}</b></a>')
        cards = []
        for item in phase["tasks"]:
            evidence = "".join(f"<li><code>{esc(x)}</code></li>" for x in item.get("evidence", [])) or "<li>Not yet produced.</li>"
            blocker = f'<p class="blocker"><strong>Blocker:</strong> {esc(item["blocker"])}</p>' if item.get("blocker") else ""
            checked = " checked" if item["status"] == "done" else ""
            auth = "true" if item["status"] == "done" else "false"
            cards.append(f'''<article class="task" data-status="{esc(item['status'])}" data-task="{esc(item['id'])}">
<label class="task-head"><input type="checkbox" data-id="{esc(item['id'])}" data-authoritative="{auth}"{checked}><span class="task-id">{esc(item['id'])}</span><span class="task-title">{esc(item['title'])}</span><span class="badge {esc(item['status'])}">{esc(LABELS[item['status']])}</span></label>
<div class="task-body"><p><strong>Acceptance:</strong> {esc(item['acceptance'])}</p>{blocker}<details><summary>Evidence</summary><ul>{evidence}</ul></details></div></article>''')
        phase_html.append(f'''<section id="{esc(phase['id'])}" class="phase" data-phase="{esc(phase['id'])}">
<header class="phase-head"><div><span class="kicker">{esc(phase['id'])} · {esc(LABELS[phase['status']])}</span><h2>{esc(phase['name'])}</h2><p>{esc(phase['objective'])}</p></div><div class="phase-progress"><strong>{pc['done']}/{len(phase['tasks'])}</strong><span>verified</span></div><button class="collapse" aria-expanded="true" aria-label="Collapse phase">−</button></header><div class="task-list">{''.join(cards)}</div></section>''')
    milestones = "".join(f'<tr><td><code>{esc(m["id"])}</code></td><td>{esc(m["name"])}</td><td><span class="badge {esc(m["status"])}">{esc(LABELS[m["status"]])}</span></td><td>{esc(m["exit"])}</td></tr>' for m in plan["milestones"])
    decisions = "".join(f'<tr><td><code>{esc(d["id"])}</code></td><td>{esc(d["date"])}</td><td>{esc(d["decision"])}</td><td>{esc(d["reason"])}</td></tr>' for d in plan["decisions"])
    risks = "".join(f'<article class="risk {esc(r["severity"])}"><div><span>{esc(r["severity"].upper())}</span><code>{esc(r["id"])}</code></div><h3>{esc(r["risk"])}</h3><p>{esc(r["mitigation"])}</p></article>' for r in plan["risks"])
    rules = "".join(f"<li>{esc(x)}</li>" for x in plan["operating_rules"])
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()[:12]
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Arbs Rolling Plan — Live Project Status</title>
<style>
:root{{--bg:#f4f1e8;--paper:#fffdf8;--ink:#14231c;--muted:#66736b;--green:#156044;--mint:#dbece3;--amber:#a45b13;--red:#a33c35;--blue:#225c84;--line:#d7d5ca;--shadow:0 12px 35px #163b2710}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 Inter,ui-sans-serif,system-ui,sans-serif}}a{{color:inherit}}.hero{{background:linear-gradient(125deg,#0d3025,#176b4d 65%,#2a8b64);color:white;padding:62px 28px}}.hero-inner{{max-width:1220px;margin:auto}}.eyebrow,.kicker{{font-size:11px;font-weight:850;letter-spacing:.13em;text-transform:uppercase}}h1{{max-width:950px;margin:8px 0 14px;font:700 clamp(37px,6vw,72px)/1.02 Georgia,serif}}.hero p{{max-width:850px;font-size:18px;opacity:.88}}.hero-meta{{display:flex;flex-wrap:wrap;gap:8px;margin-top:22px}}.hero-meta span{{padding:6px 11px;border:1px solid #ffffff45;border-radius:99px;background:#ffffff12}}.toolbar{{position:sticky;top:0;z-index:5;display:flex;gap:10px;align-items:center;padding:11px max(18px,calc((100vw - 1220px)/2));background:#fffdf8f2;border-bottom:1px solid var(--line);backdrop-filter:blur(10px)}}.toolbar input[type=search]{{min-width:180px;flex:1;padding:10px 13px;border:1px solid var(--line);border-radius:8px;background:white}}button,.filter{{border:1px solid var(--line);background:white;border-radius:8px;padding:9px 11px;font-weight:700;cursor:pointer}}.layout{{display:grid;grid-template-columns:245px minmax(0,1fr);gap:28px;max-width:1280px;margin:0 auto;padding:28px}}.rail{{position:sticky;top:74px;align-self:start;max-height:calc(100vh - 92px);overflow:auto}}.rail h2{{font:700 20px Georgia,serif}}.rail a{{display:grid;grid-template-columns:33px 1fr auto;gap:6px;padding:9px 6px;border-bottom:1px solid var(--line);text-decoration:none;font-size:13px}}.rail a span,.rail a b{{color:var(--green)}}main{{min-width:0}}.notice,.overview,.phase,.table-card,.risk{{background:var(--paper);border:1px solid var(--line);border-radius:13px;box-shadow:var(--shadow)}}.notice{{border-left:5px solid var(--amber);padding:14px 18px;margin-bottom:17px}}.overview{{padding:22px;margin-bottom:22px}}.status-grid{{display:grid;grid-template-columns:repeat(5,minmax(90px,1fr));gap:9px}}.stat{{padding:13px;background:#f5f3eb;border-radius:9px}}.stat strong{{display:block;font-size:25px}}.progress-track{{height:9px;background:#e4e2d9;border-radius:10px;overflow:hidden;margin:16px 0 7px}}.progress-track i{{display:block;height:100%;width:{done*100/total:.2f}%;background:var(--green)}}.phase{{margin:22px 0;overflow:hidden;scroll-margin-top:75px}}.phase-head{{display:grid;grid-template-columns:1fr auto auto;gap:18px;align-items:center;padding:22px;background:#f9f7f0;border-bottom:1px solid var(--line)}}.phase-head h2{{font:700 29px Georgia,serif;margin:3px 0}}.phase-head p{{margin:0;color:var(--muted)}}.phase-progress{{text-align:center}}.phase-progress strong{{display:block;font-size:24px}}.phase-progress span{{font-size:11px;text-transform:uppercase;color:var(--muted)}}.collapse{{font-size:20px}}.task-list{{padding:8px 20px 17px}}.task{{padding:14px 0;border-bottom:1px solid var(--line)}}.task:last-child{{border:0}}.task-head{{display:grid;grid-template-columns:22px 62px 1fr auto;gap:9px;align-items:start;cursor:pointer}}.task-head input{{width:17px;height:17px;margin-top:3px;accent-color:var(--green)}}.task-id{{font-weight:850;color:var(--green)}}.task-title{{font-weight:760;font-size:16px}}.task-body{{padding-left:93px;color:#35433c}}.task-body p{{margin:7px 0}}details summary{{cursor:pointer;font-weight:700}}code{{font:12px ui-monospace,SFMono-Regular,monospace;color:#154d39;background:#e7eee9;border-radius:4px;padding:2px 5px;overflow-wrap:anywhere}}.badge{{display:inline-block;padding:3px 8px;border-radius:99px;font-size:11px;font-weight:850;white-space:nowrap}}.badge.done{{color:#14583f;background:#d8ebdf}}.badge.in_progress{{color:#684000;background:#ffe4a8}}.badge.next{{color:#204f73;background:#dcecf7}}.badge.blocked{{color:#812b27;background:#f7dcda}}.badge.deferred{{color:#565b58;background:#e5e6e5}}.table-card{{padding:20px;margin:22px 0;overflow-x:auto;scroll-margin-top:75px}}.table-card h2{{font:700 29px Georgia,serif}}table{{width:100%;border-collapse:collapse;min-width:720px}}th,td{{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid var(--line)}}th{{color:var(--green);font-size:12px;text-transform:uppercase}}.risk-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:12px}}.risk{{padding:16px;border-top:4px solid var(--amber)}}.risk.critical{{border-top-color:var(--red)}}.risk.high{{border-top-color:var(--amber)}}.risk h3{{font-size:16px}}.risk div{{display:flex;justify-content:space-between;font-size:11px;font-weight:850}}.footer{{max-width:1220px;margin:25px auto;padding:25px;color:var(--muted);text-align:center}}.hidden{{display:none!important}}body.incomplete .task[data-status=done]{{display:none}}.phase.collapsed .task-list{{display:none}}@media(max-width:850px){{.layout{{display:block;padding:17px}}.rail{{position:static;max-height:none;margin-bottom:20px}}.status-grid{{grid-template-columns:repeat(2,1fr)}}.phase-head{{grid-template-columns:1fr auto}}.phase-progress{{display:none}}.task-head{{grid-template-columns:22px 55px 1fr}}.badge{{grid-column:3}}.task-body{{padding-left:86px}}.toolbar{{flex-wrap:wrap}}}}@media(max-width:520px){{.hero{{padding:42px 18px}}.task-head{{grid-template-columns:22px 1fr}}.task-id{{grid-column:2}}.task-title,.badge{{grid-column:2}}.task-body{{padding-left:31px}}}}@media print{{.toolbar,.rail,.collapse{{display:none}}.layout{{display:block;padding:0}}.phase{{break-inside:avoid;box-shadow:none}}body{{background:white}}}}
</style></head><body>
<header class="hero"><div class="hero-inner"><div class="eyebrow">Single source of truth · Rolling delivery plan</div><h1>Arbs: from raw markets to verified opportunities</h1><p>{esc(plan['mission'])}</p><div class="hero-meta"><span>Verified {esc(plan['last_verified'])}</span><span>Canonical plan v{esc(plan['schema_version'])}</span><span>Source {source_hash}</span><span>Read-only phase</span></div></div></header>
<div class="toolbar"><input id="search" type="search" placeholder="Search tasks, gates, evidence…" aria-label="Search plan"><button id="incomplete">Incomplete only</button><button id="expand">Expand all</button><button onclick="window.print()">Print / PDF</button><button id="reset">Reset local checks</button></div>
<div class="layout"><aside class="rail"><h2>Delivery map</h2>{''.join(phase_nav)}<a href="#decisions"><span>•</span>Decisions</a><a href="#risks"><span>•</span>Risks</a><p><small><strong>Shared status</strong> comes only from the committed canonical JSON. Checkbox changes on this page stay in this browser.</small></p></aside><main>
<div class="notice"><strong>Current focus:</strong> {esc(plan['current_focus'])}<br><strong>Next:</strong> {esc(plan['next_action'])}</div>
<section class="overview"><h2>Live status</h2><div class="status-grid"><div class="stat"><strong>{done}</strong>done</div><div class="stat"><strong>{c['in_progress']}</strong>in progress</div><div class="stat"><strong>{c['next']}</strong>next</div><div class="stat"><strong>{c['blocked']}</strong>blocked</div><div class="stat"><strong>{c['deferred']}</strong>deferred</div></div><div class="progress-track"><i></i></div><p><strong>{done}/{total}</strong> source-verified complete · <span id="working">{done}/{total}</span> with browser-local working checks</p><details><summary>Operating rules</summary><ol>{rules}</ol></details></section>
<section class="table-card"><h2>Milestones</h2><table><thead><tr><th>ID</th><th>Milestone</th><th>Status</th><th>Exit gate</th></tr></thead><tbody>{milestones}</tbody></table></section>
{''.join(phase_html)}
<section id="decisions" class="table-card"><h2>Decisions</h2><table><thead><tr><th>ID</th><th>Date</th><th>Decision</th><th>Why</th></tr></thead><tbody>{decisions}</tbody></table></section>
<section id="risks" class="table-card"><h2>Risk register</h2><div class="risk-grid">{risks}</div></section>
</main></div><footer class="footer">Generated from <code>docs/rolling-plan.json</code>. Do not edit this HTML directly. Local checks are private working notes, not shared completion evidence.</footer>
<script>
const KEY='arbs-plan-local-v1'; const boxes=[...document.querySelectorAll('.task input[type=checkbox]')];
function saved(){{try{{return JSON.parse(localStorage.getItem(KEY)||'{{}}')}}catch{{return {{}}}}}}
function update(){{const n=boxes.filter(x=>x.checked).length;document.querySelector('#working').textContent=`${{n}}/${{boxes.length}}`;}}
const state=saved(); boxes.forEach(b=>{{if(b.dataset.authoritative==='false'&&state[b.dataset.id])b.checked=true;b.addEventListener('change',()=>{{if(b.dataset.authoritative==='true')b.checked=true;const s=saved();if(b.checked)s[b.dataset.id]=true;else delete s[b.dataset.id];localStorage.setItem(KEY,JSON.stringify(s));update();}})}});update();
document.querySelector('#reset').onclick=()=>{{localStorage.removeItem(KEY);boxes.forEach(b=>b.checked=b.dataset.authoritative==='true');update();}};
document.querySelector('#incomplete').onclick=e=>{{document.body.classList.toggle('incomplete');e.currentTarget.textContent=document.body.classList.contains('incomplete')?'Show all':'Incomplete only';}};
document.querySelector('#expand').onclick=()=>{{document.querySelectorAll('.phase').forEach(p=>p.classList.remove('collapsed'));document.querySelectorAll('.collapse').forEach(b=>{{b.textContent='−';b.setAttribute('aria-expanded','true')}})}};
document.querySelectorAll('.collapse').forEach(b=>b.onclick=()=>{{const p=b.closest('.phase');p.classList.toggle('collapsed');const open=!p.classList.contains('collapsed');b.textContent=open?'−':'+';b.setAttribute('aria-expanded',String(open));}});
document.querySelector('#search').addEventListener('input',e=>{{const q=e.target.value.trim().toLowerCase();document.querySelectorAll('.task').forEach(t=>t.classList.toggle('hidden',q&&!t.textContent.toLowerCase().includes(q)));document.querySelectorAll('.phase').forEach(p=>p.classList.toggle('hidden',q&&![...p.querySelectorAll('.task')].some(t=>!t.classList.contains('hidden'))));}});
</script></body></html>'''


def write(plan: dict[str, Any]) -> None:
    MARKDOWN.write_text(render_markdown(plan), encoding="utf-8")
    HTML.write_text(render_html(plan), encoding="utf-8")


def verify_generated(plan: dict[str, Any]) -> None:
    expected_md, expected_html = render_markdown(plan), render_html(plan)
    if not MARKDOWN.exists() or MARKDOWN.read_text(encoding="utf-8") != expected_md:
        raise ValueError("docs/ROLLING_PLAN.md is stale; regenerate it")
    if not HTML.exists() or HTML.read_text(encoding="utf-8") != expected_html:
        raise ValueError("docs/rolling-plan.html is stale; regenerate it")
    doc = HTML.read_text(encoding="utf-8")
    ids = re.findall(r'\sid="([^"]+)"', doc)
    if len(ids) != len(set(ids)):
        raise ValueError("generated HTML contains duplicate IDs")
    all_tasks = tasks(plan)
    if doc.count('class="task"') != len(all_tasks):
        raise ValueError("generated HTML task count differs from canonical source")
    if doc.count('data-authoritative="true"') != sum(x["status"] == "done" for x in all_tasks):
        raise ValueError("generated authoritative completion count differs from source")
    source_markers = MARKDOWN.read_text(encoding="utf-8").count("- [x]") + MARKDOWN.read_text(encoding="utf-8").count("- [ ]")
    if source_markers != len(all_tasks):
        raise ValueError("generated Markdown task count differs from source")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate source and prove generated views are current")
    args = parser.parse_args()
    plan = load(); validate(plan)
    if args.check:
        verify_generated(plan)
        print(f"OK: {len(tasks(plan))} tasks, generated views current")
    else:
        write(plan); verify_generated(plan)
        print(f"Rendered {MARKDOWN.relative_to(ROOT)} and {HTML.relative_to(ROOT)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
