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
# Each section: short tab label, number, title, source doc, framing intro, and
# run/access links (relative paths — they resolve on a local clone AND on Pages).
SECTIONS = [
    {
        "id": "idea",
        "num": "01",
        "tab": "The Idea",
        "title": "Topology Is Computation",
        "md": "docs/VISION.md",
        "intro": (
            "Start here. Before a single line of code or any hardware, this is "
            "the one idea the rest of the manual follows from — that the "
            "<em>structure</em> of the fabric is the program, not a thing the "
            "program runs on."
        ),
        "links": [
            ("Continue → A Single Cell", "#sec-cell", "section"),
            ("Open the Composer", "../composer/unicell_composer.html", "run"),
        ],
    },
    {
        "id": "cell",
        "num": "02",
        "tab": "Composer",
        "title": "The Composer — Build It By Hand",
        "md": "composer/README.md",
        "intro": (
            "The fastest way to feel how the fabric works is to place and wire "
            "cells yourself. The Composer runs entirely in your browser — no "
            "install, no server — so the link below works whether you opened "
            "this manual from a local clone or from the hosted pages."
        ),
        "links": [
            ("Open the Composer", "../composer/unicell_composer.html", "run"),
            ("Open the Region Connector", "../composer/region_connector.html", "run"),
            ("← Back to The Idea", "#sec-idea", "section"),
        ],
    },
]

TOTAL = "09"   # placeholder total for the eyebrow (full manual will set this)


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

def build():
    tabs, panels = [], []
    for idx, s in enumerate(SECTIONS):
        md_path = os.path.join(REPO, s["md"])
        with open(md_path) as f:
            body = render_markdown(f.read())
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
    display:flex; flex-direction:column; gap:10px; padding:54px 0 0 0;
    border-left:1px solid #cfc9ba}
  .tab{position:relative; left:0; width:46px; min-height:96px; border:0; cursor:pointer;
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
</script>
</body>
</html>"""


if __name__ == "__main__":
    with open(OUT, "w") as f:
        f.write(build())
    print(f"wrote {OUT}  ({len(SECTIONS)} sections)")
