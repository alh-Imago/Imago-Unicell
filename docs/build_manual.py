#!/usr/bin/env python3
"""
build_manual.py — bake the docs into a self-contained tabbed field manual

REWRITTEN, REAL AGAIN (points.md #376): the `SECTIONS` list previously
flagged as stale (`#368`, referencing old, mostly-archived docs like
`COMPOUND_OPCODES.md`, the Trix ecosystem, the old Composer/MathTrix
frontend) has been rebuilt from scratch against ONLY real, current,
existing docs -- 9 sections matching the CURRENT system's real shape
(the super carrier shell, ICM v3, the DSL/C/Python-AST frontends, the
workbench, real hardware numbers), not the old topic structure carried
forward regardless of relevance. Every referenced path checked to
actually exist before being added. Safe to run again.

Generates docs/manual.html: a single, dependency-free HTML file that walks a
newcomer through the system section by section, with the prose pulled from the
canonical markdown docs plus per-section framing and run/access links. Right-
edge binder tabs (like a physical manual) switch sections.

BAKED-IN: each section's markdown is rendered to HTML at build time and
embedded, so there is NO runtime fetch — the manual works on a plain
double-click (file://), offline, and on GitHub Pages alike.

KEEP IT CURRENT: the docs are the source of truth; this manual is the on-ramp.
After editing any doc in SECTIONS, re-run this script to regenerate manual.html.

    python3 docs/build_manual.py

Markdown rendering uses the `markdown` package if installed (full fidelity,
tables + fenced code); otherwise a compact built-in fallback covers headings,
code, lists, links, emphasis, blockquotes, and rules.
"""

import os
import re
import html

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT  = os.path.join(HERE, "manual.html")

# Each section: short tab label, number, title, source doc, framing intro, and
# run/access links (relative paths — they resolve on a local clone AND on Pages).
SECTIONS = [
    {"id":"idea","num":"01","tab":"The Idea","title":"Topology Is Computation",
     "intro":"A spatial FPGA compute architecture where the physical WIRING is the "
             "program, not a thing the program runs on. There's no CPU, no instruction "
             "set, and no shared bus &mdash; a physical cell holds a fixed set of real "
             "hardware cores, each wired directly to its North/South/East/West "
             "neighbors. Computation happens as values arrive and propagate across that "
             "topology, one wire-delay hop at a time. A cell fires only once it has "
             "received arrivals from two directions (a <strong>two-arrival firing "
             "model</strong>) &mdash; no global clock coordinates it, wire delay does.<br><br>"
             "<strong>What this actually is, stated plainly:</strong> a research project "
             "building real, working pieces of this architecture, on real hardware, with "
             "real measured numbers &mdash; not a general-purpose computer, not "
             "commercially packaged. If the PCIe host-integration work succeeds, the "
             "realistic best case is an FPGA accelerator card for specific spatial-"
             "dataflow workloads, not a CPU replacement.",
     "links":[("Continue → Start Here","#sec-start","section")]},

    {"id":"start","num":"02","tab":"Start","title":"Start Here",
     "intro":"Orientation and your first run: what the project is, current status, "
             "and how to get the VM/workbench going.",
     "parts":[{"sub":"Read me first","md":"README.md"},
              {"sub":"Documentation index","md":"docs/README.md"},
              {"sub":"The current/ folder (session catch-up docs)","md":"current/README.md"}],
     "links":[("Continue → The Cell","#sec-cell","section")]},

    {"id":"cell","num":"03","tab":"The Cell","title":"The Cell",
     "intro":"Two real, related cell designs. The <strong>super carrier shell</strong> "
             "is the active line of development: a single physical cell holding all 6 "
             "real cores simultaneously (a NOR-gate logic cell, RAM, an adder, an "
             "accumulator, a comparator, and a latch), with the active one chosen by a "
             "runtime configuration write. The standalone <strong>nano cell</strong> is a "
             "real, independently buildable, smaller design covering just the NOR-gate "
             "logic core on its own.",
     "parts":[{"sub":"The super carrier shell (active line)","md":"docs/stripped-cell/SUPER_CELL_INTERNALS.md"},
              {"sub":"The standalone nano cell","md":"docs/stripped-cell/CELL_INTERNALS.md"}],
     "links":[("Continue → ICM v3 & Cores","#sec-icm","section")]},

    {"id":"icm","num":"04","tab":"ICM v3","title":"The ICM v3 Format & Core Reference",
     "intro":"The program format (a shape of records at row/col grid positions, "
             "verified two independent ways against real compiled RTL), and a real "
             "reference for every one of the 6 cores' own ports and behavior.",
     "parts":[{"sub":"The ICM v3 format","md":"docs/stripped-cell/ICM_V3_FORMAT.md"},
              {"sub":"Cores & wrappers reference","md":"docs/stripped-cell/CORES_AND_WRAPPERS_REFERENCE.md"}],
     "links":[("Continue → The DSL & Compiler","#sec-dsl","section")]},

    {"id":"dsl","num":"05","tab":"DSL","title":"The DSL, Compiler & Other Frontends",
     "intro":"A real, purpose-built language for authoring Unicell-S programs, plus a "
             "real C-AST frontend and a real Python-AST frontend, all compiling down to "
             "the exact same shared IR and backend. Every worked example in this "
             "reference was independently compiled and confirmed working before being "
             "written down.",
     "parts":[{"md":"docs/stripped-cell/UNICELL_S_DSL_MANUAL.md"}],
     "links":[("Continue → The Workbench","#sec-workbench","section")]},

    {"id":"workbench","num":"06","tab":"Workbench","title":"The Browser Workbench",
     "intro":"Compile a program, watch it run, drive individual cells, and load "
             "multiple independent programs onto one shared grid as named regions "
             "&mdash; either at a manual offset or via a real auto-placement search. "
             "Run it with:<br><br><code>python3 nano/workbench_v1.py</code><br>"
             "→ opens at <code>http://localhost:7420</code>",
     "parts":[{"sub":"The original scoping note (what's dead vs. reusable from the old workbench)",
               "md":"docs/stripped-cell/design-notes/workbench_scope.md"}],
     "links":[("Continue → Hardware","#sec-hw","section")]},

    {"id":"hw","num":"07","tab":"Hardware","title":"Hardware",
     "intro":"From simulator to silicon: real Quartus-confirmed numbers for the super "
             "carrier shell (213 ALM, 257 registers, 200.76 MHz &mdash; 8.03&times; "
             "margin over the 25 MHz requirement), the target board, and real bring-up "
             "findings.",
     "parts":[{"sub":"Arria 10 programming procedure","md":"hardware/Arria10_Programming_Procedure.md"},
              {"sub":"Real bring-up findings","md":"hardware/YPCB_00338_bringup_findings.md"}],
     "links":[("Continue → Roadmap","#sec-roadmap","section")]},

    {"id":"roadmap","num":"08","tab":"Roadmap","title":"Roadmap & The Project's Own Record",
     "intro":"Where the project is heading, the active plan, and the full, honest, "
             "append-only decision log &mdash; every real design decision, bug found, "
             "and measurement taken, with its actual reasoning, not just a changelog "
             "line. <code>points.md</code> itself is genuinely huge (300+ numbered "
             "entries, one growing project-long log) &mdash; linked below rather than "
             "embedded inline, the same real reason the Session Logs section (next) "
             "links out instead of reprinting.",
     "parts":[{"sub":"The active plan","md":"current/PLAN.md"},
              {"sub":"Session catch-up (most recent state)","md":"current/latest.md"}],
     "links":[("Open points.md — the full decision log","../points.md","run"),
              ("Continue → Sessions","#sec-sessions","section")]},

    {"id":"sessions","num":"09","tab":"Sessions","title":"Session Logs",
     "intro":"The repo is its own memory. Each working session is logged; rather than "
             "reprint them here, this is an index &mdash; open any log directly from "
             "your clone.",
     "sessions":True,
     "links":[("← Back to The Idea","#sec-idea","section")]},
]

TOTAL = str(len(SECTIONS)).zfill(2)


# ── Markdown rendering ────────────────────────────────────────────────────────

def render_markdown(text: str) -> str:
    # Real, confirmed bug in the `markdown` package (independently
    # verified, not assumed): a line starting with "#" immediately
    # followed by a digit -- e.g. a wrapped continuation line reading
    # "#347). If this..." -- gets misread as an ATX heading even though
    # standard Markdown requires a SPACE after "#" for that. Also
    # confirmed to trigger inside blockquotes ("> #170/#171's..."),
    # since the quote marker is stripped before this same false-
    # positive check runs internally. This shows up constantly in this
    # project's own docs, which reference points.md entries by number
    # throughout prose (`#347`, `#170`, etc.) that frequently land at
    # the start of a wrapped line purely by chance. Escaping only that
    # exact false-positive pattern (never a real heading, which always
    # has "# text") before rendering, preserving any blockquote prefix
    # -- legitimate "# Heading"/"## Heading"/"> quoted text" lines are
    # untouched.
    text = re.sub(r"(?m)^((?:>\s*)*)(#+)(\d)", r"\1\\\2\3", text)
    try:
        import markdown
        return markdown.markdown(
            text, extensions=["fenced_code", "tables", "sane_lists"]
        )
    except Exception:
        return _fallback_md(text)


def _fallback_md(text: str) -> str:
    """Compact dependency-free markdown -> HTML (covers the common cases)."""
    out, lines, i = [], text.split("\n"), 0
    def inline(s):
        s = html.escape(s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
        return s
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            i += 1; buf = []
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(html.escape(lines[i])); i += 1
            out.append("<pre><code>" + "\n".join(buf) + "</code></pre>"); i += 1; continue
        m = re.match(r"^(#{1,6})\s+(.*)", ln)
        if m:
            lvl = len(m.group(1)); out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>"); i += 1; continue
        if re.match(r"^---+\s*$", ln):
            out.append("<hr>"); i += 1; continue
        if re.match(r"^\s*[-*]\s+", ln):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append("<li>" + inline(re.sub(r"^\s*[-*]\s+", "", lines[i])) + "</li>"); i += 1
            out.append("<ul>" + "".join(items) + "</ul>"); continue
        if ln.startswith(">"):
            out.append("<blockquote>" + inline(ln.lstrip("> ")) + "</blockquote>"); i += 1; continue
        if ln.strip() == "":
            i += 1; continue
        para = [ln]; i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,6}\s|```|>|\s*[-*]\s|---+\s*$)", lines[i]):
            para.append(lines[i]); i += 1
        out.append("<p>" + inline(" ".join(para)) + "</p>")
    return "\n".join(out)


def links_block(links):
    if not links:
        return ""
    rows = []
    for text, href, kind in links:
        arrow = "▸ run" if kind == "run" else "§"
        target = ' target="_blank" rel="noopener"' if kind == "run" else ""
        rows.append(
            f'<a class="ref ref-{kind}" href="{html.escape(href)}"{target}>'
            f'<span class="ref-kind">{arrow}</span>'
            f'<span class="ref-text">{html.escape(text)}</span></a>'
        )
    return ('<aside class="tryit"><div class="tryit-label">Try it / Reference</div>'
            + "".join(rows) + "</aside>")


# ── Page assembly ─────────────────────────────────────────────────────────────

def build_sessions_index():
    """Lean index of session logs — links into the clone, not baked content.

    Reorg (2026-08-04): dated/archived logs now live under
    archeology/sessions/ ("history, but important history" — Alan).
    current/latest.md (the fast catch-up doc, NOT history) moved out of
    that folder entirely, so it's handled as its own pinned-first row
    rather than found by listing archeology/sessions/ — it never
    appears there anymore, and shouldn't be searched for there.
    """
    sdir = os.path.join(REPO, "archeology", "sessions")
    files = [f for f in os.listdir(sdir) if f.endswith(".md")] if os.path.isdir(sdir) else []
    files = sorted(files)
    def datekey(f):
        m = re.search(r"\d{4}-\d{2}-\d{2}", f)
        return m.group(0) if m else "0000-00-00"
    rest = sorted(files, key=datekey, reverse=True)
    rows = [
        f'<a class="sess" href="../current/latest.md" target="_blank" rel="noopener">'
        f'<span class="sess-name">Latest session</span>'
        f'<span class="sess-file">current/latest.md</span></a>'
    ]
    for f in rest:
        rows.append(
            f'<a class="sess" href="../archeology/sessions/{html.escape(f)}" target="_blank" rel="noopener">'
            f'<span class="sess-name">{html.escape(f[:-3])}</span>'
            f'<span class="sess-file">archeology/sessions/{html.escape(f)}</span></a>'
        )
    return (f'<p class="doc"><em>{len(files) + 1} logs.</em> These open the raw markdown '
            f'from your clone (or the hosted tree) — nothing is reprinted here. '
            f'Dated/archived logs live under <code>archeology/sessions/</code>; the '
            f'current one lives in <code>current/latest.md</code>.</p>'
            f'<div class="sesslist">' + "".join(rows) + "</div>")


def _rewrite_relative_links(text: str) -> str:
    """Every embedded doc's own internal markdown links (e.g.
    README.md's own `[x](docs/foo.md)`) are written relative to the
    REPO ROOT -- correct for GitHub/a local clone, but WRONG once baked
    into `docs/manual.html`, which lives one level deeper. Confirmed a
    real, live case before writing this fix, not assumed: README.md's
    own embedded content in the "Start" section rendered a link to
    `docs/stripped-cell/SUPER_CELL_INTERNALS.md` that would have
    resolved to the non-existent `docs/docs/stripped-cell/...` from
    manual.html's own location. `docs/` is always exactly one level
    below the repo root, so prefixing every relative (non-http, non-
    anchor, non-absolute) markdown link target with `../` is correct
    and general, not specific to any one doc."""
    def fix(m):
        target = m.group(1)
        if target.startswith(("http://", "https://", "#", "/", "../")):
            return m.group(0)
        return f"]({'../' + target})"
    return re.sub(r"\]\(([^)]+)\)", fix, text)


def render_body(s):
    """A section body comes from custom html, a sessions index, or one-or-more docs."""
    if s.get("html"):
        return s["html"]
    if s.get("sessions"):
        return build_sessions_index()
    chunks = []
    parts = s.get("parts", [])
    multi = len(parts) > 1
    for part in parts:
        with open(os.path.join(REPO, part["md"])) as f:
            rendered = render_markdown(_rewrite_relative_links(f.read()))
        if multi and part.get("sub"):
            chunks.append(f'<div class="partsub">{html.escape(part["sub"])}'
                          f'<span class="partsrc">{html.escape(part["md"])}</span></div>')
        chunks.append(rendered)
    return "\n".join(chunks)


def build():
    tabs, panels = [], []
    for idx, s in enumerate(SECTIONS):
        body = render_body(s)
        active = " active" if idx == 0 else ""
        tabs.append(
            f'<button class="tab{active}" data-target="sec-{s["id"]}" '
            f'role="tab" aria-selected="{"true" if idx==0 else "false"}">'
            f'<span class="tab-num">{s["num"]}</span>'
            f'<span class="tab-label">{html.escape(s["tab"])}</span></button>'
        )
        prev_s = SECTIONS[idx-1] if idx > 0 else None
        next_s = SECTIONS[idx+1] if idx < len(SECTIONS)-1 else None
        nav = ['<nav class="pagenav">']
        nav.append(
            f'<button class="pn pn-prev" data-target="sec-{prev_s["id"]}">‹ {html.escape(prev_s["tab"])}</button>'
            if prev_s else '<span class="pn pn-empty"></span>')
        nav.append(
            f'<button class="pn pn-next" data-target="sec-{next_s["id"]}">{html.escape(next_s["tab"])} ›</button>'
            if next_s else '<span class="pn pn-empty"></span>')
        nav.append("</nav>")
        panels.append(
            f'<section class="panel{active}" id="sec-{s["id"]}" role="tabpanel">'
            f'<div class="eyebrow">Imago UniCell · Field Manual'
            f'<span class="sectno">§{s["num"]} / {TOTAL}</span></div>'
            f'<h1 class="ptitle">{html.escape(s["title"])}</h1>'
            f'<p class="intro">{s["intro"]}</p>'
            f'<hr class="rule">'
            f'<div class="doc">{body}</div>'
            f'{links_block(s["links"])}'
            f'{"".join(nav)}'
            f'</section>'
        )
    return PAGE.replace("{{TABS}}", "\n".join(tabs)).replace("{{PANELS}}", "\n".join(panels))


PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Imago UniCell — Field Manual</title>
<style>
  :root{
    --paper:#E9E6DC; --paper-edge:#DED9CB; --ink:#1C1B17; --ink-soft:#5C584C;
    --accent:#15756D; --accent-bright:#1E9B90; --rule:#C3BCAB;
    --tab-rest:#CDC7B7; --tab-ink:#46423a; --code-bg:#26241F; --code-ink:#D9E8E4;
    --serif:Georgia,'Iowan Old Style','Times New Roman',serif;
    --mono:ui-monospace,'SF Mono','Cascadia Mono',Menlo,Consolas,monospace;
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%}
  body{
    background:#15140f; color:var(--ink); font-family:var(--serif);
    display:flex; justify-content:center; align-items:stretch;
  }
  /* the manual sits as a "page" with the tab rail on its right edge */
  .manual{
    position:relative; display:flex; width:min(980px,100%); height:100%;
    background:var(--paper);
    box-shadow:0 0 0 1px var(--paper-edge), 0 24px 60px rgba(0,0,0,.55);
  }
  .page{
    flex:1; overflow-y:auto; padding:54px clamp(28px,6vw,84px) 40px;
  }
  .reading{max-width:660px; margin:0 auto}
  .panel{display:none} .panel.active{display:block}

  .eyebrow{
    font-family:var(--mono); font-size:11px; letter-spacing:.18em;
    text-transform:uppercase; color:var(--ink-soft);
    display:flex; justify-content:space-between; align-items:baseline;
    border-bottom:1px solid var(--rule); padding-bottom:10px;
  }
  .sectno{color:var(--accent)}
  .ptitle{
    font-family:var(--mono); font-weight:600; font-size:clamp(26px,4vw,38px);
    line-height:1.12; letter-spacing:-.01em; margin:26px 0 14px;
  }
  .intro{font-size:18px; line-height:1.6; color:#322f28; margin:0 0 8px}
  .rule{border:0; border-top:2px solid var(--ink); margin:22px 0 26px; opacity:.85}

  /* rendered doc body */
  .doc{font-size:16.5px; line-height:1.72}
  .doc h1,.doc h2,.doc h3{font-family:var(--mono); font-weight:600; line-height:1.2}
  .doc h1{font-size:24px; margin:34px 0 12px}
  .doc h2{font-size:20px; margin:30px 0 10px; padding-bottom:6px; border-bottom:1px solid var(--rule)}
  .doc h3{font-size:16px; margin:24px 0 8px; color:var(--ink-soft); letter-spacing:.02em}
  .doc p{margin:0 0 16px}
  .doc strong{color:#000}
  .doc em{color:#3a372f}
  .doc a{color:var(--accent); text-decoration:none; border-bottom:1px solid rgba(21,117,109,.35)}
  .doc a:hover{color:var(--accent-bright); border-bottom-color:var(--accent-bright)}
  .doc code{font-family:var(--mono); font-size:.86em; background:#DED9C9;
    padding:1px 5px; border-radius:3px}
  .doc pre{background:var(--code-bg); color:var(--code-ink); padding:16px 18px;
    border-radius:6px; overflow-x:auto; font-size:13.5px; line-height:1.6;
    border-left:3px solid var(--accent)}
  .doc pre code{background:none; padding:0; color:inherit}
  .doc blockquote{margin:16px 0; padding:4px 18px; border-left:3px solid var(--rule);
    color:var(--ink-soft); font-style:italic}
  .doc hr{border:0; border-top:1px solid var(--rule); margin:26px 0}
  .doc ul,.doc ol{padding-left:22px; margin:0 0 16px}
  .doc li{margin:5px 0}
  .doc table{border-collapse:collapse; width:100%; margin:0 0 16px; font-size:14px}
  .doc th,.doc td{border:1px solid var(--rule); padding:6px 10px; text-align:left}
  .doc th{font-family:var(--mono); background:#DED9C9}

  /* the "try it / reference" callout */
  .tryit{margin:30px 0 8px; border:1px solid var(--rule); background:#E2DECF;
    border-radius:6px; padding:14px 16px}
  .tryit-label{font-family:var(--mono); font-size:10.5px; letter-spacing:.18em;
    text-transform:uppercase; color:var(--ink-soft); margin-bottom:8px}
  .ref{display:flex; align-items:center; gap:10px; text-decoration:none;
    color:var(--ink); padding:7px 6px; border-radius:4px; font-family:var(--mono);
    font-size:13.5px}
  .ref:hover{background:#D7D2C1}
  .ref-kind{font-size:11px; color:var(--ink-soft); min-width:34px}
  .ref-run .ref-kind{color:var(--accent)}
  .ref-run .ref-text{color:var(--accent); font-weight:600}

  .pagenav{display:flex; justify-content:space-between; margin-top:34px;
    border-top:1px solid var(--rule); padding-top:16px}
  .pn{font-family:var(--mono); font-size:13px; background:none; border:0;
    color:var(--ink-soft); cursor:pointer; padding:6px 2px}
  .pn:hover{color:var(--accent)}
  .pn-empty{visibility:hidden}

  /* right-edge binder tabs */
  .rail{width:46px; flex:0 0 46px; background:var(--paper-edge);
    display:flex; flex-direction:column; gap:7px; padding:18px 0 18px 0;
    border-left:1px solid #cfc9ba; overflow-y:auto; overflow-x:hidden}
  .rail::-webkit-scrollbar{width:0}
  .tab{position:relative; left:0; width:46px; min-height:74px; flex:0 0 auto; border:0; cursor:pointer;
    background:var(--tab-rest); color:var(--tab-ink); font-family:var(--mono);
    writing-mode:vertical-rl; text-orientation:mixed; padding:14px 0;
    display:flex; align-items:center; justify-content:flex-start; gap:12px;
    border-radius:0 5px 5px 0; box-shadow:inset 2px 0 4px rgba(0,0,0,.08);
    transition:left .12s ease, background .12s ease}
  .tab:hover{left:-4px; background:#D8D2C2}
  .tab .tab-num{font-size:11px; letter-spacing:.1em; opacity:.7}
  .tab .tab-label{font-size:12.5px; letter-spacing:.14em; text-transform:uppercase}
  .tab.active{left:-7px; background:var(--accent); color:#EAF6F4;
    box-shadow:0 2px 10px rgba(0,0,0,.25)}
  .tab:focus-visible{outline:2px solid var(--accent-bright); outline-offset:2px}

  @media (max-width:640px){
    .ptitle{font-size:26px} .page{padding:38px 22px 32px}
    .tab{min-height:74px; width:42px} .rail{width:42px; flex-basis:42px}
  }
  /* multi-doc chapter: sub-section divider */
  .partsub{font-family:var(--mono); font-size:15px; font-weight:600;
    margin:38px 0 14px; padding-bottom:8px; border-bottom:2px solid var(--ink);
    display:flex; justify-content:space-between; align-items:baseline}
  .partsub:first-child{margin-top:6px}
  .partsrc{font-size:10.5px; font-weight:400; letter-spacing:.06em; color:var(--ink-soft)}
  /* sessions index */
  .sesslist{display:flex; flex-direction:column; gap:2px; margin-top:6px}
  .sess{display:flex; justify-content:space-between; align-items:baseline;
    text-decoration:none; color:var(--ink); font-family:var(--mono);
    font-size:13px; padding:8px 10px; border-radius:4px; border-bottom:1px solid var(--rule)}
  .sess:hover{background:#D7D2C1}
  .sess-name{color:var(--accent)}
  .sess-file{font-size:11px; color:var(--ink-soft)}

  /* ── The Lab ── */
  .lab-pad{margin:6px 0 22px}
  .lab-pad-label,.lab-tools-label,.lab-files-label{font-family:var(--mono);
    font-size:10.5px; letter-spacing:.16em; text-transform:uppercase;
    color:var(--ink-soft); margin-bottom:8px}
  .lab-code{width:100%; min-height:300px; resize:vertical; background:var(--code-bg);
    color:var(--code-ink); border:0; border-left:3px solid var(--accent);
    border-radius:6px; padding:16px 18px; font-family:var(--mono);
    font-size:13px; line-height:1.6; white-space:pre; overflow:auto}
  .lab-code:focus{outline:2px solid var(--accent-bright); outline-offset:2px}
  .lab-paths{display:grid; grid-template-columns:1fr 1fr; gap:16px; margin:8px 0 26px}
  .lab-card{border:1px solid var(--rule); background:#E2DECF; border-radius:6px;
    padding:16px 16px 18px}
  .lab-card p{font-size:14.5px; line-height:1.55; margin:0 0 10px}
  .lab-card-tag{font-family:var(--mono); font-size:11px; letter-spacing:.12em;
    text-transform:uppercase; font-weight:600; margin-bottom:10px;
    display:inline-block; padding:3px 8px; border-radius:3px}
  .tag-direct{background:#D7D2C1; color:#3a372f}
  .tag-browser{background:var(--accent); color:#EAF6F4}
  .lab-cmd{font-family:var(--mono); font-size:12.5px; background:var(--code-bg);
    color:var(--code-ink); padding:9px 12px; border-radius:5px; overflow-x:auto;
    white-space:nowrap}
  .lab-note{color:var(--ink-soft); font-size:13px!important; margin-top:8px!important}
  .wb-open{display:inline-block; margin-top:12px; font-family:var(--mono);
    font-size:13px; color:var(--accent); text-decoration:none; font-weight:600}
  .wb-open:hover{color:var(--accent-bright)}
  .wb-badge{display:inline-block; margin-left:10px; font-family:var(--mono);
    font-size:11px; padding:2px 8px; border-radius:10px; background:#D7D2C1;
    color:var(--ink-soft)}
  .wb-badge.up{background:#1E9B90; color:#EAF6F4}
  .wb-badge.down{background:#D7D2C1; color:var(--ink-soft)}
  .lab-tools{margin:0 0 24px}
  .lab-files{border-top:1px solid var(--rule); padding-top:18px}
  .lab-files p{font-size:14.5px; line-height:1.6; margin:0 0 12px}
  @media (max-width:640px){ .lab-paths{grid-template-columns:1fr} }
  @media (prefers-reduced-motion:reduce){ .tab{transition:none} }
</style>
</head>
<body>
  <div class="manual">
    <div class="page"><div class="reading">
      {{PANELS}}
    </div></div>
    <div class="rail" role="tablist" aria-label="Manual sections">
      {{TABS}}
    </div>
  </div>
<script>
  const tabs = [...document.querySelectorAll('.tab')];
  const panels = [...document.querySelectorAll('.panel')];
  const page = document.querySelector('.page');
  function show(id){
    panels.forEach(p=>p.classList.toggle('active', p.id===id));
    tabs.forEach(t=>{
      const on = t.dataset.target===id;
      t.classList.toggle('active', on);
      t.setAttribute('aria-selected', on?'true':'false');
    });
    page.scrollTop = 0;
  }
  tabs.forEach(t=>t.addEventListener('click', ()=>show(t.dataset.target)));
  document.addEventListener('click', e=>{
    const b = e.target.closest('[data-target]');
    if(b && b.classList.contains('pn')) show(b.dataset.target);
  });
  // internal section cross-links (#sec-...)
  document.querySelectorAll('.ref[href^="#sec-"]').forEach(a=>{
    a.addEventListener('click', e=>{ e.preventDefault(); show(a.getAttribute('href').slice(1)); });
  });
  // detect a running local Workbench (localhost:7420). Works from a local
  // clone / file://; on hosted https the call is blocked as mixed content, so
  // we just show the start instruction instead of a false "not running".
  (function(){
    const badge = document.getElementById('wb-badge');
    if(!badge) return;
    if(location.protocol === 'https:'){
      badge.textContent = 'start it locally to enable'; badge.className='wb-badge down'; return;
    }
    const done = (up)=>{ badge.textContent = up ? 'running ✓' : 'not started';
      badge.className = 'wb-badge ' + (up?'up':'down'); };
    const t = setTimeout(()=>done(false), 1500);
    fetch('http://localhost:7420/', {mode:'no-cors'})
      .then(()=>{ clearTimeout(t); done(true); })
      .catch(()=>{ clearTimeout(t); done(false); });
  })();
</script>
</body>
</html>"""


if __name__ == "__main__":
    with open(OUT, "w") as f:
        f.write(build())
    print(f"wrote {OUT}  ({len(SECTIONS)} sections)")
