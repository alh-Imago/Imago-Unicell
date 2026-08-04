#!/usr/bin/env python3
"""
build_manual.py — bake the docs into a self-contained tabbed field manual

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

# ── The manual: ordered sections (MOCKUP = first two). ────────────────────────
# ── The Lab section's custom body (not from a doc). Plain string: the example
#    code's braces stay literal. No raw <, >, & inside the <textarea> example. ──
LAB_HTML = """
<div class="lab-pad">
  <div class="lab-pad-label">Scratchpad — a model, built by hand. Edit it, then run it either way below.</div>
  <textarea class="lab-code" spellcheck="false">
# my_gate.py - a tiny UniCell tile
from fp_tiles import TileAddressAllocator, NORBuilder, Tile, TileMetadata

def make_my_gate(base=0x20000):
    a = TileAddressAllocator(base)
    x, y = a.alloc(), a.alloc()
    b = NORBuilder(a)
    for addr in (x, y):
        b.depth_map[addr] = 0
    out = b.NOT(b.OR2(x, y))          # NOR(x, y) - the universal gate
    return Tile(records=b.records, in_a=[x], in_b=[y], out=[out],
                preload_map=getattr(b, "preload_map", {}),
                metadata=TileMetadata(operation="MY_GATE", precision=1,
                    pipeline_depth=max(b.depth_of(out), 1),
                    cell_count=len(b.records)))
  </textarea>
</div>

<div class="lab-paths">
  <div class="lab-card">
    <div class="lab-card-tag tag-direct">Direct Python · full power</div>
    <p>For when you know your way around. Runs native CPython at full speed and
       writes the hashed <code>.icm</code> straight to disk.</p>
    <div class="lab-cmd">$ python3 examples/walker/walk_tiles.py --builder my_gate:make_my_gate</div>
    <p class="lab-note">Checks the builder and emits <code>my_gate/MY_GATE.icm</code>, loadable anywhere.</p>
  </div>
  <div class="lab-card">
    <div class="lab-card-tag tag-browser">Browser Lab · start here</div>
    <p>A resident cell array you drive from a dashboard — editable cell count,
       a source editor, step/run — all in your browser.</p>
    <div class="lab-cmd">$ python3 workbench.py</div>
    <a class="wb-open" href="http://localhost:7420" target="_blank" rel="noopener">Open the Workbench →</a>
    <span class="wb-badge" id="wb-badge">checking localhost:7420…</span>
  </div>
</div>

<div class="lab-tools">
  <div class="lab-tools-label">Visual tools — pure HTML, these run anywhere</div>
  <a class="ref ref-run" href="../composer/unicell_composer.html" target="_blank" rel="noopener"><span class="ref-kind">▸ run</span><span class="ref-text">Open the Composer</span></a>
  <a class="ref ref-run" href="../frontend/mathtrix_frontend.html" target="_blank" rel="noopener"><span class="ref-kind">▸ run</span><span class="ref-text">Open the MathTrix frontend</span></a>
  <a class="ref ref-run" href="../composer/region_connector.html" target="_blank" rel="noopener"><span class="ref-kind">▸ run</span><span class="ref-text">Open the Region Connector</span></a>
</div>

<div class="lab-files">
  <div class="lab-files-label">Working with .icm files</div>
  <p>The compiler is pure Python, so it runs the same in either door — it turns
     source into records in memory, no disk needed. The difference is where the
     result lands. The <strong>Workbench is native Python under a browser
     dashboard</strong>, so it reads and writes <code>.icm</code> to your repo
     exactly like the command line — full access, nothing sandboxed.</p>
  <p>A true in-page engine (the optional Pyodide mode) is different: it runs in
     a sandbox, so it <em>generates</em> an <code>.icm</code> as a download
     rather than writing into the tree, and it <strong>loads</strong> an
     <code>.icm</code> through a file picker — which is exactly how the Composer
     already opens files, so loading any <code>.icm</code> from your clone works
     either way.</p>
</div>
"""

# Each section: short tab label, number, title, source doc, framing intro, and
# run/access links (relative paths — they resolve on a local clone AND on Pages).
SECTIONS = [
    {"id":"idea","num":"01","tab":"The Idea","title":"Topology Is Computation",
     "intro":"Before a line of code or any hardware, the one idea the rest of the "
             "manual follows from — that the <em>structure</em> of the fabric is the "
             "program, not a thing the program runs on.",
     "parts":[{"md":"archeology/shared/docs/software/VISION.md"}],
     "links":[("Continue → Start Here","#sec-start","section")]},

    {"id":"start","num":"02","tab":"Start","title":"Start Here",
     "intro":"Orientation and your first run: what the project is, how the pieces "
             "fit, and how to get the VM going. <strong>Repo layout changed 2026-08-04</strong> "
             "— if a path you remember doesn't resolve, the three docs below explain "
             "exactly where everything went and why.",
     "parts":[{"sub":"Read me first","md":"README.md"},
              {"sub":"Repo layout: docs/ (verified, current)","md":"docs/README.md"},
              {"sub":"Repo layout: current/ (the three live documents)","md":"current/README.md"},
              {"sub":"Repo layout: archeology/ (history + not-yet-re-examined)","md":"archeology/README.md"},
              {"sub":"Quick start","md":"current/START.md"},
              {"sub":"The VM, step by step","md":"archeology/shared/docs/software/VM_GETTING_STARTED.md"}],
     "links":[("Open the Composer","../composer/unicell_composer.html","run"),
              ("Continue → The Cell","#sec-cell","section")]},

    {"id":"cell","num":"03","tab":"The Cell","title":"The Cell",
     "intro":"One reconfigurable NOR-universal cell, a two-arrival firing model, and "
             "how values are addressed and preloaded. Everything scales up from here. "
             "<strong>Points at the STRIPPED/nano cell's docs</strong> — the currently "
             "active line, verified against real RTL 2026-08-04 — rather than the older "
             "\"v2.3\"-era FULL-cell reference this section used to show, which was "
             "already known stale before either current cell existed.",
     "parts":[{"sub":"What's shared between both cell lines","md":"docs/shared/SYSTEM_MECHANICS.md"},
              {"sub":"Cell internals (STRIPPED/nano, active line)","md":"docs/stripped-cell/CELL_INTERNALS.md"},
              {"sub":"The preload model","md":"archeology/shared/docs/software/PRELOAD_MODEL.md"},
              {"sub":"Addressing (FULL cell)","md":"archeology/full-cell/docs/core/addressing_note.md"}],
     "links":[("Continue → Instruction Set","#sec-opcodes","section")]},

    {"id":"opcodes","num":"04","tab":"Opcodes","title":"The Instruction Set",
     "intro":"The compound opcodes — how a handful of configuration bits select a "
             "cell's behaviour, and the emergent properties that fall out.",
     "parts":[{"md":"archeology/full-cell/docs/core/COMPOUND_OPCODES.md"}],
     "links":[("Continue → Architecture","#sec-arch","section")]},

    {"id":"arch","num":"05","tab":"Arch","title":"Architecture",
     "intro":"The whole stack: cell logic, the OS tiers, and the decision tree that "
             "decides where a thing belongs.",
     "parts":[{"sub":"Architecture","md":"archeology/full-cell/docs/core/ARCHITECTURE.md"},
              {"sub":"Branch decision tree","md":"archeology/full-cell/docs/core/BRANCH_DECISION_TREE.md"},
              {"sub":"Native filesystem","md":"archeology/full-cell/docs/core/NATIVE_FS.md"}],
     "links":[("Continue → Tiles & .icm","#sec-tiles","section")]},

    {"id":"tiles","num":"06","tab":"Tiles","title":"Tiles, Compiler & .icm",
     "intro":"Composing cells into reusable tiles, how the compiler configures them, "
             "and the portable <code>.icm</code> program format they emit.",
     "parts":[{"sub":"The tile library","md":"archeology/shared/docs/software/LIBRARY.md"},
              {"sub":"Compiler tile config","md":"archeology/shared/docs/software/COMPILER_TILE_CONFIG.md"},
              {"sub":"The .icm format","md":"docs/shared/ICM_FORMAT.md"}],
     "links":[("Open the Composer","../composer/unicell_composer.html","run"),
              ("Continue → Run & Examples","#sec-run","section")]},

    {"id":"run","num":"07","tab":"Run","title":"Running & Examples",
     "intro":"How to run programs on the VM, and worked examples to learn from.",
     "parts":[{"sub":"Running","md":"archeology/shared/docs/software/RUNNING.md"},
              {"sub":"Examples","md":"archeology/shared/docs/software/EXAMPLES.md"}],
     "links":[("Open the Lab","#sec-lab","section"),
              ("Continue → Formats & Trix","#sec-trix","section")]},

    {"id":"trix","num":"08","tab":"Trix","title":"Formats & the Trix Ecosystem",
     "intro":"Finite-alphabet domains packed into cells: how a format is defined, the "
             "MIF float format, the Trix family, typed neural work, and the MathTrix front end.",
     "parts":[{"sub":"Defining a format","md":"archeology/shared/docs/software/FORMAT_DEFINITION_GUIDE.md"},
              {"sub":"The MIF format","md":"docs/shared/MIF_FORMAT.md"},
              {"sub":"The Trix ecosystem","md":"archeology/shared/docs/software/TRIX_ECOSYSTEM.md"},
              {"sub":"Typed neural","md":"archeology/shared/docs/software/TYPED_NEURAL.md"},
              {"sub":"MathTrix front end","md":"archeology/shared/docs/software/math_frontend_design.md"}],
     "links":[("Open the MathTrix front end","../frontend/mathtrix_frontend.html","run"),
              ("Continue → Hardware","#sec-hw","section")]},

    {"id":"hw","num":"09","tab":"Hardware","title":"Hardware",
     "intro":"From simulator to silicon: the FPGA targets, board bring-up, and the "
             "Verilog that is the ground truth for every naming convention. The "
             "hardware-setup doc here is known stale (pre-Arria10/Quartus era) — "
             "flagged in <code>archeology/TRIAGE.md</code>, not yet rewritten.",
     "parts":[{"sub":"FPGA hardware","md":"archeology/full-cell/docs/archive/FPGA_HARDWARE.md"},
              {"sub":"Hardware setup","md":"archeology/shared/docs/hardware/HARDWARE_SETUP.md"},
              {"sub":"Verilog spec","md":"archeology/full-cell/docs/archive/VERILOG_SPEC.md"}],
     "links":[("Continue → The Lab","#sec-lab","section")]},

    {"id":"lab","num":"10","tab":"The Lab","title":"The Lab — Two Ways to Run It",
     "intro":"Once you've cloned the repo you have two doors into the same system: the "
             "<strong>direct Python commands</strong> — full power, for when you know your "
             "way around — and the <strong>browser lab</strong>, a smaller resident cell "
             "count you drive from a dashboard, made to start gently. Same fabric, same "
             "<code>.icm</code> files; only the entry point differs.",
     "html":LAB_HTML,
     "links":[("Continue → The Paper","#sec-paper","section")]},

    {"id":"paper","num":"11","tab":"Paper","title":"The Technical Paper",
     "intro":"The full write-up of the architecture and its results, in draft.",
     "parts":[{"md":"archeology/shared/docs/software/PAPER_DRAFT.md"}],
     "links":[("Continue → Roadmap","#sec-roadmap","section")]},

    {"id":"roadmap","num":"12","tab":"Roadmap","title":"Roadmap & Beyond",
     "intro":"Where the project is heading: the active plan, the multi-language path, "
             "the running task list, ideas flagged for later re-examination, and the "
             "full document index. Also the archeology sweep's own triage — a real, "
             "concrete roadmap for which docs still need re-examining and where.",
     "parts":[{"sub":"The plan","md":"current/PLAN.md"},
              {"sub":"Archeology triage — what's checked, what's next","md":"archeology/TRIAGE.md"},
              {"sub":"LLVM / multi-language","md":"archeology/shared/docs/software/LLVM.md"},
              {"sub":"Task list","md":"TODO.md"},
              {"sub":"Points to re-examine","md":"points.md"},
              {"sub":"Document index","md":"archeology/shared/docs/software/INDEX.md"}],
     "links":[("Continue → Sessions","#sec-sessions","section")]},

    {"id":"sessions","num":"13","tab":"Sessions","title":"Session Logs",
     "intro":"The repo is its own memory. Each working session is logged; rather than "
             "reprint them here, this is an index — open any log directly from your "
             "clone. Dated/archived logs now live under "
             "<code>archeology/sessions/</code> (2026-08-04 reorg) — pure history, kept "
             "exactly as written.",
     "sessions":True,
     "links":[("← Back to The Idea","#sec-idea","section")]},
]

TOTAL = str(len(SECTIONS)).zfill(2)


# ── Markdown rendering ────────────────────────────────────────────────────────

def render_markdown(text: str) -> str:
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
            rendered = render_markdown(f.read())
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
