"""hexn_view_v1.py - SEE WHAT YOU PROGRAMMED (3 Nov 2026; Alan 10:07: 'expand the tools so the user can see what they program, now most will be in the unicell, but they will need to have an option to switch to the Hex-N side').
Two views of the SAME program (the program part of a unit file, or an icm-hexn file), as inline SVG with no script and no library:
  UniCell view : the program as the user wrote it - inputs, operations, outputs and what feeds what, left to right. Nothing about tiles, routing or ticks.
  Hex-N view   : the program as it sits on the grid - which tile type is at each place, every routing cell's connections, the RAM holds, the pads, the pattern id.
render(program, header=None, view='unicell') -> HTML for the body; the two views are both in the page and a switch (CSS radio buttons) shows one, UniCell first. Pure functions, no files, no network."""
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import hexn_icm_export_v3 as X  # noqa: E402

E = html.escape
FACE = {"N": (0.5, 0.0), "E": (1.0, 0.5), "S": (0.5, 1.0), "W": (0.0, 0.5)}
TYPE_NAME = {"UN": "unary", "AL": "aligned 2-input", "JN": "join", "BR": "branch", "MG": "merge", "PR": "priority", "SQ": "sequencer", "LT": "latch", "RAM": "RAM hold"}
TYPE_CLASS = {"UN": "t1", "AL": "t2", "JN": "t3", "BR": "t4", "MG": "t5", "PR": "t6", "SQ": "t7", "LT": "t8"}

CSS = """
.hv-switch{margin:.6rem 0 1rem} .hv-switch label{display:inline-block;padding:.35rem .9rem;border:1px solid var(--line);cursor:pointer;color:var(--fg-dim);font-family:var(--font-mono);font-size:.85rem}
#hv-u:checked~.hv-switch label[for=hv-u],#hv-h:checked~.hv-switch label[for=hv-h]{color:var(--gold);border-color:var(--copper);background:var(--bg-panel-2)}
.hv-radio{position:absolute;opacity:0} .hv-pane{display:none} #hv-u:checked~.hv-panes .hv-u,#hv-h:checked~.hv-panes .hv-h{display:block}
.hv-svg{max-width:100%;height:auto;background:var(--bg-panel);border:1px solid var(--line)} .hv-svg text{font-family:var(--font-mono);fill:var(--fg)} .hv-svg .dim{fill:var(--fg-dim)}
.hv-svg .box{fill:var(--bg-panel-2);stroke:var(--copper-dim)} .hv-svg .io{fill:var(--bg-input);stroke:var(--in)} .hv-svg .edge{stroke:var(--fg-dim);fill:none}
.hv-svg .route{stroke:var(--in);fill:none;stroke-width:2} .hv-svg .cellbg{fill:var(--bg-input);stroke:var(--line)} .hv-svg .hold{fill:var(--warn)}
.hv-svg .cellbg.t1{fill:#25402b}.hv-svg .cellbg.t2{fill:#3a3a22}.hv-svg .cellbg.t3{fill:#2a3a50}.hv-svg .cellbg.t4{fill:#4a2f2a}.hv-svg .cellbg.t5{fill:#3c2a4a}.hv-svg .cellbg.t6{fill:#4a3a20}.hv-svg .cellbg.t7{fill:#20444a}.hv-svg .cellbg.t8{fill:#444}.t1{fill:#25402b}.t2{fill:#3a3a22}.t3{fill:#2a3a50}.t4{fill:#4a2f2a}.t5{fill:#3c2a4a}.t6{fill:#4a3a20}.t7{fill:#20444a}.t8{fill:#444}
"""


def _cfg_text(cell):
    c = cell.get("cfg") or {}; k = cell["kind"]; parts = []
    if k in ("shl", "shr"): parts.append("by %s" % cell.get("k"))
    if k == "merge": parts.append(["A only", "B only", "arbitrate", "join-OR"][c.get("mode", 2)])
    if k == "prio": parts.append(["strict", "weighted", "sequenced"][c.get("mode", 0)])
    if k == "seq": parts.append("%d values" % c.get("len", 0))
    if k == "branch": parts.append("emit %s" % ["fixed", "a", "b", "a-b"][c.get("emit", 1)])
    return ", ".join(parts)


def unicell_svg(prog):
    cells = prog["cells"]; nodes = {}                                   # name -> dict(kind, label, ins, level)
    for key, c in sorted(cells.items()):
        nm = c["outs"][0] if c.get("outs") else key
        nodes[nm] = dict(kind=c["kind"], label=c["kind"], sub=_cfg_text(c), ins=list(c.get("ins", [])), outs=list(c.get("outs", [])), key=key)
    producer = {}
    for nm, n in nodes.items():
        for o in n["outs"]: producer[o] = nm
    level = {}
    def lv(name):
        if name in level: return level[name]
        level[name] = 0
        if name in nodes: level[name] = 1 + max([lv(i) for i in nodes[name]["ins"]] or [0]) if False else 1 + max([lv(producer.get(i, i)) for i in nodes[name]["ins"]] or [0])
        return level[name]
    for n in nodes: lv(n)
    inputs = sorted(prog["pads_in"]); outputs = sorted(prog["pads_out"])
    maxl = max([level[n] for n in nodes] or [0])
    cols = {0: [("in", i) for i in inputs]}
    for n in sorted(nodes, key=lambda x: nodes[x]["key"]): cols.setdefault(level[n], []).append(("op", n))
    cols[maxl + 1] = [("out", o) for o in outputs]
    W, H, bw, bh = 150, 62, 120, 44; pos = {}
    ncol = maxl + 2; height = max(len(v) for v in cols.values()) * H + 20
    for c, items in cols.items():
        for r, (kind, name) in enumerate(items): pos[(kind, name)] = (14 + c * W, 14 + r * H)
    out = ['<svg class="hv-svg" viewBox="0 0 %d %d" role="img" aria-label="UniCell view of the program">' % (ncol * W + 20, height)]
    def anchor(kind, name, right): x, y = pos[(kind, name)]; return (x + (bw if right else 0), y + bh / 2)
    for nm, n in nodes.items():
        for i in n["ins"]:
            src = ("op", producer[i]) if i in producer else ("in", i)
            if src in pos:
                x1, y1 = anchor(*src, True); x2, y2 = anchor("op", nm, False)
                out.append('<path class="edge" d="M%.0f,%.0f C%.0f,%.0f %.0f,%.0f %.0f,%.0f"/>' % (x1, y1, x1 + 30, y1, x2 - 30, y2, x2, y2))
    for o in outputs:
        pr = producer.get(o)
        if pr:
            x1, y1 = anchor("op", pr, True); x2, y2 = anchor("out", o, False)
            out.append('<path class="edge" d="M%.0f,%.0f C%.0f,%.0f %.0f,%.0f %.0f,%.0f"/>' % (x1, y1, x1 + 30, y1, x2 - 30, y2, x2, y2))
    for (kind, name), (x, y) in pos.items():
        if kind == "op":
            n = nodes[name]
            out.append('<rect class="box" x="%d" y="%d" width="%d" height="%d" rx="4"/><text x="%d" y="%d" font-size="13">%s</text><text class="dim" x="%d" y="%d" font-size="10">%s</text>' % (x, y, bw, bh, x + 8, y + 18, E(n["label"]), x + 8, y + 34, E((n["sub"] + " -> " + name) if n["sub"] else "-> " + name)))
        else:
            out.append('<rect class="io" x="%d" y="%d" width="%d" height="%d" rx="14"/><text x="%d" y="%d" font-size="12">%s</text>' % (x, y + 8, bw, bh - 16, x + 12, y + 26, E(("in  " if kind == "in" else "out ") + name)))
    out.append("</svg>")
    return "".join(out)


def hexn_svg(prog, n=None):
    pts = [tuple(map(int, k.split(","))) for k in list(prog["cells"]) + list(prog["routing"])] + [tuple(v) for v in list(prog["pads_in"].values()) + list(prog["pads_out"].values())]
    n = n or (max(max(p) for p in pts) + 1 if pts else 1)
    S, M = 64, 70
    out = ['<svg class="hv-svg" viewBox="0 0 %d %d" role="img" aria-label="Hex-N view of the program">' % (n * S + 2 * M, n * S + 20)]
    for r in range(n):
        for c in range(n):
            x, y = M + c * S, 10 + r * S; key = "%d,%d" % (r, c); cell = prog["cells"].get(key)
            out.append('<rect class="cellbg%s" x="%d" y="%d" width="%d" height="%d"/>' % (" " + TYPE_CLASS.get(cell["type"], "") if cell else "", x, y, S, S))
            if cell:
                out.append('<text x="%d" y="%d" font-size="13">%s</text><text class="dim" x="%d" y="%d" font-size="10">%s</text>' % (x + 6, y + 24, E(cell["type"]), x + 6, y + 40, E(cell["kind"] + (" " + str(cell["k"]) if cell["kind"] in ("shl", "shr") else ""))))
            for o, i in (prog["routing"].get(key) or {}).items():
                (ax, ay), (bx, by) = FACE[i], FACE[o]
                out.append('<path class="route" d="M%.0f,%.0f L%.0f,%.0f"/>' % (x + ax * S, y + ay * S, x + bx * S, y + by * S))
            h = (prog.get("holds") or {}).get(key)
            if h: out.append('<circle class="hold" cx="%d" cy="%d" r="5"/><text class="dim" x="%d" y="%d" font-size="9">hold %d</text>' % (x + S - 10, y + 10, x + 2, y + S - 4, h["dly"]))
    for name, (r, c) in prog["pads_in"].items(): out.append('<text x="2" y="%d" font-size="11">in %s</text>' % (10 + r * S + S // 2 + 4, E(name)))
    for name, (r, c) in prog["pads_out"].items(): out.append('<text x="%d" y="%d" font-size="11">out %s</text>' % (M + n * S + 4, 10 + r * S + S // 2 + 4, E(name)))
    out.append("</svg>")
    return "".join(out)


def legend(prog):
    used = sorted({c["type"] for c in prog["cells"].values()})
    return "".join('<span style="margin-right:1rem"><svg width="12" height="12"><rect class="%s" width="12" height="12"/></svg> %s (%s)</span>' % (TYPE_CLASS.get(t, ""), E(t), E(TYPE_NAME.get(t, t))) for t in used)


def table(prog):
    rows = "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (E(k), E(c["type"]), E(c["kind"] + (" " + _cfg_text(c) if _cfg_text(c) else "")), E(" , ".join(c.get("ins", [])) + " -> " + " , ".join(c.get("outs", []))))
                   for k, c in sorted(prog["cells"].items()))
    return '<table class="fields"><tr><th>Place</th><th>Tile</th><th>Does</th><th>In -> out</th></tr>%s</table>' % rows


def render(program, header=None):
    """program: an icm-hexn-v2 dict or the dict X.from_icm gives; header: a unit header (optional)"""
    prog = program if "pads_in" in program else X.from_icm(program)
    h = header or {}
    head = ""
    if h: head = "<p>Pattern <b>%s</b>, id <code>%s</code>, base <code>%s</code>.</p>" % (E(h.get("pattern")), E("%08X" % h["pattern_id"]) if h.get("pattern_id") is not None else "-", E(h.get("base")))
    return ('%s<input type="radio" class="hv-radio" name="hv" id="hv-u" checked><input type="radio" class="hv-radio" name="hv" id="hv-h">'
            '<div class="hv-switch"><label for="hv-u">UniCell view</label> <label for="hv-h">Hex-N view</label></div><div class="hv-panes">'
            '<div class="hv-pane hv-u"><p>What the program does, as you wrote it.</p>%s</div>'
            '<div class="hv-pane hv-h"><p>Where it sits on the Hex-N grid. %s</p>%s%s</div></div>') % (head, unicell_svg(prog), legend(prog), hexn_svg(prog), table(prog))
