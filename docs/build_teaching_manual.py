#!/usr/bin/env python3
"""
build_teaching_manual.py -- bake the TEACHING docs into a self-contained tabbed manual

A clone of build_manual.py (same renderer, same page, same style) with its own
SECTIONS list and its own output file, so the main field manual (docs/manual.html,
which is specifically about UniCell itself) is never touched by it.

Generates docs/teaching_manual.html: a single, dependency-free HTML file, one tab
per section, every section's markdown rendered at build time (no runtime fetch, so
it works on a plain double-click, offline, and on GitHub Pages).

It sits beside manual.html on purpose: build_manual.py's link rewriting assumes the
output lives exactly one level below the repo root, and that stays true here.

TO ADD A LESSON: write it as markdown (suggested home: docs/teaching/), then add one
dict to SECTIONS below ("id", "num", "tab", "title", "intro", "parts", "links"; copy
an existing one) and re-run:

    python3 docs/build_teaching_manual.py

Keep it current the same way as the main manual: the docs are the source of truth, and
this file is the on-ramp. Status: a plan (ledger #1037, #1038); nothing here has been
tried with real learners yet.
"""

import os
import re
import html

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT  = os.path.join(HERE, "teaching_manual.html")

# Each section: short tab label, number, title, source doc, framing intro, and
# run/access links (relative paths -- they resolve on a local clone AND on Pages).
def _data_uri(rel):
    """Embed a PNG as a data: URI so the built manual stays one self-contained file."""
    import base64
    with open(os.path.join(HERE, rel), "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")


def _prog_html(name):
    """Fragment with the captured compiler/VM data (docs/teaching/programming_data.json) embedded."""
    import json as _json
    with open(os.path.join(HERE, "teaching", name), encoding="utf-8") as f:
        t = f.read()
    with open(os.path.join(HERE, "teaching", "programming_data.json"), encoding="utf-8") as f:
        data = _json.dumps(_json.load(f), separators=(",", ":")).replace("</", "<\\/")
    return t.replace("@@PROG_DATA@@", data)


def _comp_html(name):
    """Fragment with the captured compiler/placer data (docs/teaching/compiler_data.json) embedded."""
    import json as _json
    with open(os.path.join(HERE, "teaching", name), encoding="utf-8") as f:
        t = f.read()
    with open(os.path.join(HERE, "teaching", "compiler_data.json"), encoding="utf-8") as f:
        data = _json.dumps(_json.load(f), separators=(",", ":")).replace("</", "<\\/")
    return t.replace("@@COMP_DATA@@", data)


def _rtl_html(name):
    """Fragment with the captured assembler/MAN data (docs/teaching/rtl_data.json) embedded."""
    import json as _json
    with open(os.path.join(HERE, "teaching", name), encoding="utf-8") as f:
        t = f.read()
    with open(os.path.join(HERE, "teaching", "rtl_data.json"), encoding="utf-8") as f:
        data = _json.dumps(_json.load(f), separators=(",", ":")).replace("</", "<\\/")
    return t.replace("@@RTL_DATA@@", data)


def _asm_html(name):
    """Fragment with the captured family/flag data (docs/teaching/asm_data.json) embedded."""
    import json as _json
    with open(os.path.join(HERE, "teaching", name), encoding="utf-8") as f:
        t = f.read()
    with open(os.path.join(HERE, "teaching", "asm_data.json"), encoding="utf-8") as f:
        data = _json.dumps(_json.load(f), separators=(",", ":")).replace("</", "<\\/")
    return t.replace("@@ASM_DATA@@", data)


def _grids_html(name):
    """Fragment with the captured SuperGrid/FlexGrid runs (docs/teaching/grids_data.json) embedded."""
    import json as _json
    with open(os.path.join(HERE, "teaching", name), encoding="utf-8") as f:
        t = f.read()
    with open(os.path.join(HERE, "teaching", "grids_data.json"), encoding="utf-8") as f:
        data = _json.dumps(_json.load(f), separators=(",", ":")).replace("</", "<\\/")
    return t.replace("@@GRIDS_DATA@@", data)


def _mirror_html(name):
    """Fragment with the captured mirror / Walker data (docs/teaching/mirror_data.json) embedded."""
    import json as _json
    with open(os.path.join(HERE, "teaching", name), encoding="utf-8") as f:
        t = f.read()
    with open(os.path.join(HERE, "teaching", "mirror_data.json"), encoding="utf-8") as f:
        data = _json.dumps(_json.load(f), separators=(",", ":")).replace("</", "<\\/")
    return t.replace("@@MIRROR_DATA@@", data)


def _wb_data():
    """The Workbench tab's captured grid/option runs (docs/teaching/wb_data.json) as a JS literal."""
    import json as _json
    with open(os.path.join(HERE, "teaching", "wb_data.json"), encoding="utf-8") as f:
        return _json.dumps(_json.load(f), separators=(",", ":")).replace("</", "<\\/")


def _cell_pages():
    """One hidden page per cell kind, built from docs/teaching/cells_data.json (parsed Verilog) and cells_text.py."""
    import json as _json, sys as _sys
    _sys.path.insert(0, os.path.join(HERE, "teaching"))
    import cells_text as ct
    with open(os.path.join(HERE, "teaching", "cells_data.json"), encoding="utf-8") as f:
        D = _json.load(f)
    with open(os.path.join(HERE, "teaching", "cell_fragment.html"), encoding="utf-8") as f:
        TPL = f.read()
    sizes = D["sizes"]
    order = ct.ORDER
    pages = []
    for i, k in enumerate(order):
        txt = ct.CELLS[k]
        sz = {"standalone_full": sizes["standalone_full"].get(k), "standalone_lean": sizes["standalone_lean"].get(k),
              "carrier_whole": sizes["carrier_whole"], "tang_lut4": sizes["tang_lut4"],
              "flex_measured": (sizes["flex"].get(k) or {}).get("measured")}
        payload = {"kind": k, "text": txt, "files": D["kinds"][k], "sizes": sz,
                   "famtext": {fk: v[1] for fk, v in ct.FAMILIES.items()}}
        data = _json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
        prev_ = order[i - 1] if i else None
        next_ = order[i + 1] if i < len(order) - 1 else None
        links = [("← Back to " + (prev_ if prev_ else "All the Cells"), "#sec-cell-" + prev_ if prev_ else "#sec-cells", "section"),
                 ("Continue → " + (next_ if next_ else "All the Cells"), "#sec-cell-" + next_ if next_ else "#sec-cells", "section")]
        pages.append({"id": "cell-" + k, "num": "20." + str(i + 1).zfill(2), "tab": k, "sub": True, "parent": "cells",
                      "title": "The " + k.replace("_", " ").title() + " Cell: " + txt["short"].rstrip("."),
                      "intro": txt["short"] + " Its capabilities, how data moves through it, what is inside the Verilog in each family, and the source.",
                      "html": TPL.replace("@@K@@", k).replace("@@CELL_DATA@@", data), "links": links})
    groups = [("Remembering", ["ram", "latch", "sequencer"]), ("Arithmetic", ["adder", "accumulator", "mul"]),
              ("Deciding", ["compare", "branch"]), ("Joining and splitting", ["merge", "priority", "router"]),
              ("Wiring", ["corner", "cross"]), ("Reshaping words", ["shift", "shift_stage", "mask"]),
              ("The gate, and control", ["nano", "command"])]
    h = ['<style>.cellidx .grp{margin:1.2em 0 .3em;font-weight:700}.cellidx .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:8px}'
         '.cellidx a.cc{display:block;border:2px solid var(--accent);border-radius:10px;padding:8px 12px;text-decoration:none;color:var(--ink);background:var(--paper-edge)}'
         '.cellidx a.cc:hover{background:#D7D2C1}.cellidx a.cc b{font-family:var(--mono);display:block}'
         '.cellidx a.cc span.s{display:block;font-size:.88em;color:var(--ink-soft);margin:.15em 0 .35em}'
         '.cellidx a.cc span.f{font-family:var(--mono);font-size:.76em}.cellidx a.cc span.f i{font-style:normal;padding:0 5px;margin-right:3px;border:1px solid var(--accent);border-radius:8px;background:rgba(21,117,109,.14)}</style>',
         '<div class="cellidx"><p>Each cell kind has a page of its own: what it can do, how data moves through it, a diagram drawn from the real Verilog, the parts it is made of, the size, and the full source, for each family that has it. '
         'The family tags show where it exists: <code>v4</code> standalone, <code>v4c</code> carrier, <code>v4s</code> sub, <code>v4sa</code> flex. '
         'The <a class="ref" href="#sec-assembler">Assembler</a> page compares the families themselves.</p>']
    for gname, ks in groups:
        h.append('<div class="grp">' + html.escape(gname) + '</div><div class="cards">')
        for k in ks:
            fams = "".join("<i>" + fk + "</i>" for fk in ("v4", "v4c", "v4s", "v4sa") if D["kinds"][k].get(fk))
            h.append('<a class="ref cc" href="#sec-cell-' + k + '"><b>' + html.escape(k) + '</b><span class="s">' + html.escape(ct.CELLS[k]["short"]) + '</span><span class="f">' + fams + '</span></a>')
        h.append("</div>")
    h.append('<p class="fine" style="font-size:.85em;color:var(--ink-soft);border-top:1px solid var(--rule);margin-top:1.4em;padding-top:.6em">Scope. 18 kinds across four families, 55 Verilog files embedded in full. The kinds are counted from file names: shift and mask exist in the older families as add-on blocks inside every cell rather than as cells, and the page for each says so.</p></div>')
    index = {"id": "cells", "num": "20", "tab": "Cells", "title": "The Cells, One Page Each",
             "intro": "Eighteen kinds of cell, each with a page: capability, a diagram of what is inside, the Verilog, and which families have it.",
             "html": "\n".join(h), "links": [("← Back to The Assembler", "#sec-assembler", "section"), ("Continue → Start", "#sec-start", "section")]}
    return [index] + pages


SECTIONS = [
    {"id":"tour","num":"01","tab":"Tour","title":"Tour: What Is Where, and How to Run It",
     "intro":"The parts you will use, each a link, with a live picture of what is inside one "
             "cell and a measured picture of how long a sum takes. Start here: it shows what "
             "everything is, where it lives in the repository, and the three commands that get "
             "you to a working screen.",
     "html":open(os.path.join(HERE, "teaching", "tour_fragment.html"), encoding="utf-8").read(),
     "links":[("Continue → the Composer","#sec-composer","section")]},

    {"id":"composer","num":"02","tab":"Composer","title":"The Composer: A Tour With Labels",
     "intro":"The composer is the real drawing board behind every picture in this manual. A "
             "screenshot with numbered labels shows what each part does, and the second half "
             "explains the file it saves, the ICM.",
     "html":open(os.path.join(HERE, "teaching", "composer_fragment.html"), encoding="utf-8").read().replace("@@COMPOSER_IMG@@", _data_uri("teaching/composer_screenshot.png")),
     "links":[("← Back to the Tour","#sec-tour","section"),("Continue → the Family","#sec-family","section")]},

    {"id":"family","num":"03","tab":"Family","title":"The Rest of the Flex Family",
     "intro":"The nano cell is one of fourteen kinds of flex cell. Here is a sentence and a link "
             "for each, grouped by what they do, plus the one thing they all share: how they hand "
             "data on. Each cell will get its own page later. This is the brief overview.",
     "html":open(os.path.join(HERE, "teaching", "family_fragment.html"), encoding="utf-8").read(),
     "links":[("← Back to the Composer","#sec-composer","section"),("Continue → Chaining","#sec-chaining","section")]},

    {"id":"chaining","num":"04","tab":"Chaining","title":"Chaining Cells",
     "intro":"One cell on its own does one small thing. Chained, the output of one becomes the "
             "input of the next, through dedicated ports with no shared bus. Drag cells into a "
             "simple grid, type a number in, and see what comes out of the end of the chain.",
     "html":open(os.path.join(HERE, "teaching", "chaining_fragment.html"), encoding="utf-8").read(),
     "links":[("← Back to the Family","#sec-family","section"),("Continue → Maths","#sec-maths","section")]},

    {"id":"maths","num":"05","tab":"Maths","title":"Arithmetic: Adder, Multiplier, Accumulator",
     "intro":"The arithmetic cells, opened up: the carry that travels along an add, the half of a "
             "product that does not fit, and a running total that keeps counting.",
     "html":open(os.path.join(HERE, "teaching", "maths_fragment.html"), encoding="utf-8").read(),
     "links":[("← Back to Chaining","#sec-chaining","section"),("Continue → Branching","#sec-branching","section")]},

    {"id":"branching","num":"06","tab":"Branching","title":"Branching and Decisions",
     "intro":"Chained cells run straight on. Two flex cells make choices: the branch cell decides "
             "where one value goes, and the priority cell decides which of several waiting values "
             "goes next. Try both with your own numbers.",
     "html":open(os.path.join(HERE, "teaching", "branching_fragment.html"), encoding="utf-8").read(),
     "links":[("← Back to Maths","#sec-maths","section"),("Continue → Joining and Splitting","#sec-joinsplit","section")]},

    {"id":"joinsplit","num":"07","tab":"Join & Split","title":"Joining and Splitting Paths",
     "intro":"Two small cells show how data meets and parts. The merge cell brings two paths into "
             "one; the router cell sends one path to up to two places. Both teach what has to "
             "wait for what.",
     "html":open(os.path.join(HERE, "teaching", "joinsplit_fragment.html"), encoding="utf-8").read(),
     "links":[("← Back to Branching","#sec-branching","section"),("Continue → Routing","#sec-routing","section")]},

    {"id":"routing","num":"08","tab":"Routing","title":"Crossing and Turning: Cross and Corner Tiles",
     "intro":"Two wiring tiles let paths cross and turn on a flat grid. They change nothing about a "
             "word; they only decide which way it leaves. Send words in and watch them cross.",
     "html":open(os.path.join(HERE, "teaching", "routing_fragment.html"), encoding="utf-8").read(),
     "links":[("← Back to Joining and Splitting","#sec-joinsplit","section"),("Continue → Memory","#sec-memory","section")]},

    {"id":"memory","num":"09","tab":"Memory","title":"Remembering: Latch, Sequencer and Ram",
     "intro":"Everything so far let go of its value as soon as it passed it on. The latch keeps one "
             "bit until it is told to change; the sequencer keeps a short list and steps through it; "
             "the ram cell holds a word in one of three ways. "
             "Press the buttons and watch what is stored and what is reported.",
     "html":open(os.path.join(HERE, "teaching", "memory_fragment.html"), encoding="utf-8").read(),
     "links":[("← Back to Routing","#sec-routing","section"),("Continue → Bits","#sec-bits","section")]},

    {"id":"bits","num":"10","tab":"Bits","title":"Reshaping Words: Shift and Mask",
     "intro":"A word is a row of bits. The shift stage slides the bits along; the mask cell switches "
             "whole groups of them off. See each stage's bits, what fell off the end, and how the two "
             "together can pull a field out of a word.",
     "html":open(os.path.join(HERE, "teaching", "bits_fragment.html"), encoding="utf-8").read(),
     "links":[("← Back to Memory","#sec-memory","section"),("Continue → The VM","#sec-vm","section")]},

    {"id":"vm","num":"11","tab":"The VM","title":"The VM: What It Is and How It Fits",
     "intro":"Every picture so far was drawn by the page itself. The VM is the real program they "
             "imitate. A map of its parts, how the two modes differ, a short Python run you can "
             "repeat, and a plain account of how far each part has been trusted.",
     "html":open(os.path.join(HERE, "teaching", "vm_fragment.html"), encoding="utf-8").read(),
     "links":[("← Back to Bits","#sec-bits","section"),("Continue → SuperGrid and FlexGrid","#sec-grids","section")]},

    {"id":"grids","num":"12","tab":"Two Grids","title":"The Two Grids: SuperGrid and FlexGrid",
     "intro":"The VM comes in two versions of its cell grid: the standard one and the flex mirror. "
             "How to start each, what each accepts at other word widths, and the same small "
             "designs run on both so you can see where they agree and where they differ.",
     "html":_grids_html("grids_fragment.html"),
     "links":[("← Back to The VM","#sec-vm","section"),("Continue → The Mirror VM","#sec-mirror","section")]},

    {"id":"mirror","num":"13","tab":"Mirror VM","title":"The Mirror VM: Pretending to Be One Card",
     "intro":"The VM can be made to reflect a particular card: its layout, and (separately) its word "
             "width. The layout rule drawn live over real library designs, a simulated Walker you can "
             "step through, the two mirrors run together by hand, the options and every refusal, and "
             "what is not joined up yet.",
     "html":_mirror_html("mirror_fragment.html"),
     "links":[("← Back to The Two Grids","#sec-grids","section"),("Continue → The Workbench","#sec-workbench","section")]},

    {"id":"workbench","num":"12","tab":"Workbench","title":"The Workbench: See and Use the VM",
     "intro":"The workbench is where you sit at the VM: load a small program, deliver values "
             "into cells, step the clock and watch every register. A labelled screenshot, a "
             "worked 7 + 5, what it can and cannot show, and which grid it builds and what "
             "you can set.",
     "html":open(os.path.join(HERE, "teaching", "workbench_fragment.html"), encoding="utf-8").read().replace("@@WB_IMG@@", _data_uri("teaching/workbench_screenshot.png")).replace("@@WB_DATA@@", _wb_data()),
     "links":[("← Back to The Mirror VM","#sec-mirror","section"),("Continue → The DSL","#sec-dsl","section")]},

    {"id":"dsl","num":"13","tab":"DSL","title":"Programming: The DSL",
     "intro":"The small text language for placing cells and wiring their faces. Sketch a "
             "program and see it drawn, watch a real run (including a timing mistake that loses "
             "a number), see the compiler's own error messages, and meet the tiles.",
     "html":_prog_html("dsl_fragment.html"),
     "links":[("← Back to The Workbench","#sec-workbench","section"),("Continue → LLVM IR","#sec-llvm","section")]},

    {"id":"llvm","num":"14","tab":"LLVM IR","title":"Programming: From LLVM IR",
     "intro":"Take a real function as LLVM IR through the real compiler: see the cells it "
             "becomes, run them in the VM, see what it refuses, and follow the route on to "
             "the flex family's Verilog.",
     "html":_prog_html("llvm_fragment.html"),
     "links":[("← Back to the DSL","#sec-dsl","section"),("Continue → The Compiler","#sec-compiler","section")]},

    {"id":"compiler","num":"15","tab":"Compiler","title":"The Compiler: From Description to Cells",
     "intro":"One real function followed through the compiler's five stages, the two ways in, "
             "how it reports every problem at once, how it decides what lets two values into a "
             "cell, the operations it has, and whether the result fits a card.",
     "html":_comp_html("compiler_fragment.html"),
     "links":[("← Back to LLVM IR","#sec-llvm","section"),("Continue → Tightener and Placer","#sec-placer","section")]},

    {"id":"placer","num":"16","tab":"Placer","title":"The Placer and the Tightener",
     "intro":"Putting cells on squares and joining them with relays, then making the result "
             "small and still correct: two placers side by side, tightening by spacing, "
             "folding, and the rat's-nest way of shrinking one connection a step at a time.",
     "html":_comp_html("placer_fragment.html"),
     "links":[("← Back to the Compiler","#sec-compiler","section"),("Continue → Verilog / RTL","#sec-rtl","section")]},

    {"id":"rtl","num":"17","tab":"Verilog / RTL","title":"The Verilog, and Keeping the Program Apart from the Card",
     "intro":"The hardware form of the design: one short file per kind of cell, in two families, "
             "and how the program (a card-neutral map) is kept separate from the card (the MAN "
             "file) until a tool combines them. Try the same program against two real cards.",
     "html":_rtl_html("rtl_fragment.html"),
     "links":[("← Back to the Placer","#sec-placer","section"),("Continue → The MAN File","#sec-man","section")]},

    {"id":"man","num":"18","tab":"MAN File","title":"The MAN File: One Card, Written Down",
     "intro":"What is inside a card file, who reads each part (the assembler, the mirror VM and the "
             "card-fit check), what a cell costs on the card, what the card claims it can do, and "
             "how far each of the two real files can be trusted.",
     "html":_rtl_html("man_fragment.html"),
     "links":[("← Back to Verilog / RTL","#sec-rtl","section"),("Continue → The Assembler","#sec-assembler","section")]},

    {"id":"assembler","num":"19","tab":"Assembler","title":"The Assembler: Four Cell Families and Its Flags",
     "intro":"The tool that turns a program and a card into hardware files has to choose what kind of "
             "cell to build from. The four families (standalone, carrier, sub, flex) side by side, "
             "by what each can and cannot do, and the flags that steer the assembler.",
     "html":_asm_html("assembler_fragment.html"),
     "links":[("← Back to The MAN File","#sec-man","section"),("Continue → The Cells","#sec-cells","section")]},

    {"id":"__CELLS__"},

    {"id":"start","num":"21","tab":"Start","title":"How Computers Work, Seen Step by Step",
     "intro":"A plan for teaching how computers work from the very bottom: one kind of "
             "logic gate, then the other gates made from it, then why timing matters and "
             "why moving data costs something. The UniCell design is finished and is not "
             "being extended for this; its tools (the composer and the VM) let a learner "
             "pause a small circuit and look at every value. <strong>This is a plan, not a "
             "course yet.</strong> Each proposed lesson says whether it has actually been "
             "run.",
     "parts":[{"sub":"The teaching plan","md":"docs/teaching/README.md"}],
     "links":[("← Back to The Cells","#sec-cells","section"),("Continue → The Backdrop","#sec-backdrop","section")]},

    {"id":"backdrop","num":"22","tab":"Backdrop","title":"The Backdrop: What UniCell Is",
     "intro":"UniCell is the thing the lessons are drawn on, not the thing being taught. "
             "Read the status notice at the top of this page first: UniCell is an "
             "unconfirmed idea, it did not come out ahead of hand-written hardware when "
             "measured, and some of what it describes has only been run in simulation. "
             "That does not matter for teaching logic, timing and routing, but it should "
             "never be hidden. For the full technical manual about UniCell itself, see "
             "<code>docs/manual.html</code>.",
     "parts":[{"sub":"The repository README","md":"README.md"}],
     "links":[("← Back to Start","#sec-start","section")]},
]

_i = next(i for i, s in enumerate(SECTIONS) if s["id"] == "__CELLS__")
SECTIONS[_i:_i + 1] = _cell_pages()
_n, _k = 0, 0
for _s in SECTIONS:                                  # numbers follow the order of the list, so inserting a tab renumbers the rest
    if _s.get("sub"):
        _k += 1
        _s["num"] = f"{_n:02d}.{_k:02d}"
    else:
        _n += 1
        _k = 0
        _s["num"] = f"{_n:02d}"
TOTAL = str(len([s for s in SECTIONS if not s.get("sub")])).zfill(2)


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
    top = [s for s in SECTIONS if not s.get("sub")]
    subs = [s for s in SECTIONS if s.get("sub")]
    for idx, s in enumerate(SECTIONS):
        body = render_body(s)
        is_sub = bool(s.get("sub"))
        active = " active" if idx == 0 else ""
        if not is_sub:
            tabs.append(
                f'<button class="tab{active}" data-target="sec-{s["id"]}" '
                f'role="tab" aria-selected="{"true" if idx==0 else "false"}">'
                f'<span class="tab-num">{s["num"]}</span>'
                f'<span class="tab-label">{html.escape(s["tab"])}</span></button>'
            )
        group = subs if is_sub else top
        gi = group.index(s)
        prev_s = group[gi-1] if gi > 0 else (next(x for x in SECTIONS if x["id"] == s["parent"]) if is_sub else None)
        next_s = group[gi+1] if gi < len(group)-1 else (next(x for x in SECTIONS if x["id"] == s["parent"]) if is_sub else None)
        nav = ['<nav class="pagenav">']
        nav.append(
            f'<button class="pn pn-prev" data-target="sec-{prev_s["id"]}">‹ {html.escape(prev_s["tab"])}</button>'
            if prev_s else '<span class="pn pn-empty"></span>')
        nav.append(
            f'<button class="pn pn-next" data-target="sec-{next_s["id"]}">{html.escape(next_s["tab"])} ›</button>'
            if next_s else '<span class="pn pn-empty"></span>')
        nav.append("</nav>")
        parent_attr = f' data-parent="sec-{s["parent"]}"' if is_sub else ""
        sect = (f'§{s["num"]} / {TOTAL} · cell' if is_sub else f'§{s["num"]} / {TOTAL}')
        panels.append(
            f'<section class="panel{active}" id="sec-{s["id"]}" role="tabpanel"{parent_attr}>'
            f'<div class="eyebrow">Imago UniCell · Teaching Manual'
            f'<span class="sectno">{sect}</span></div>'
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
<title>Imago UniCell — Teaching Manual</title>
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
      const pp = (document.getElementById(id)||{}).dataset; const on = t.dataset.target===((pp&&pp.parent)||id);
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
