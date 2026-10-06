"""nano/composer_page_v1.py -- the front panel's /composer page (design note docs/stripped-cell/design-notes/composer_layout_viewer_scope.md).

Import an ICM file (upload, a path on this machine, or a layout built by Python such as the fp adder), see it on the board, and drag logic cells to new squares. Each drop is a request to
the layout engine: `tools/flex_layout_view_v1.Layout.move` lifts the cell's routes, moves it, re-routes and re-balances, or refuses and leaves the layout as it was. The edited design is
saved as ICM v3. This module holds the controller (no HTTP) and the page; `frontend_v1.py` dispatches to it."""
import json
import os
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, HERE)

import flex_layout_view_v1 as flv  # noqa: E402
import ui_theme_v1 as ui  # noqa: E402

EXAMPLES_DIR = os.path.join(HERE, "examples")


def examples():
    try:
        return sorted(f for f in os.listdir(EXAMPLES_DIR) if f.endswith((".icm", ".json")))
    except OSError:
        return []


class ComposerController:
    """One layout per front-panel server (a local, single-person tool). Every method returns a JSON-able dict."""

    def __init__(self):
        self.layout = None
        self.lock = threading.Lock()

    def _state(self, extra=None):
        out = {"ok": True, "layout": self.layout.snapshot() if self.layout else None}
        out.update(extra or {})
        return out

    def state(self):
        with self.lock:
            return self._state()

    def load(self, req):
        """req: {"builder": name} | {"example": file} | {"path": local path} | {"name": file name, "text": file contents}."""
        with self.lock:
            try:
                if req.get("builder"):
                    lay = flv.from_builder(req["builder"])
                elif req.get("example"):
                    name = os.path.basename(req["example"])
                    if name not in examples():
                        raise ValueError(f"no example {name}")
                    lay = flv.Layout.load(os.path.join(EXAMPLES_DIR, name))
                elif req.get("path"):
                    lay = flv.Layout.load(os.path.expanduser(req["path"]))
                elif req.get("text"):
                    with tempfile.TemporaryDirectory() as d:
                        p = os.path.join(d, os.path.basename(req.get("name") or "upload.icm.json"))
                        with open(p, "w") as f:
                            f.write(req["text"])
                        lay = flv.Layout.load(p)
                else:
                    raise ValueError("nothing to load: give a file, a path, an example or a builder")
            except Exception as e:                     # a bad file is reported on the page, never a server error
                return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}
            self.layout = lay
            return self._state()

    def move(self, req):
        with self.lock:
            if not self.layout:
                return {"ok": False, "error": "no layout loaded"}
            try:
                res = self.layout.move(str(req["name"]), int(req["r"]), int(req["c"]))
            except (KeyError, ValueError, TypeError) as e:
                return {"ok": False, "error": f"bad move request: {e}"}
            if not res["ok"]:
                return res
            return self._state({"rerouted": res["rerouted"], "detours": res["detours"]})

    def undo(self):
        with self.lock:
            if not self.layout:
                return {"ok": False, "error": "no layout loaded"}
            res = self.layout.undo()
            return self._state() if res["ok"] else res

    def icm_text(self):
        with self.lock:
            if not self.layout:
                return None, None
            from icm_v3 import IcmV3File
            lay = self.layout
            f = IcmV3File(name=lay.name, records=lay.records(), description=lay.description or "edited in the Composer", min_bit_width=lay.min_bit_width)
            base = lay.name.split("/")[-1]
            for suf in (".icm-hier.json", ".icm.json", ".json", ".icm"):
                if base.endswith(suf):
                    base = base[: -len(suf)]
            return f"{base.replace('/', '_')}.composed.icm.json", json.dumps(f.to_dict(), indent=2)


COMPOSER_CSS = """
.composer { display: grid; grid-template-columns: 1fr 300px; gap: 14px; align-items: start; }
.composer .side { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.composer .panel { background: var(--bg-panel); border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px; min-width: 0; }
.composer .panel h3 { margin: 0 0 8px; font-size: 13px; letter-spacing: .04em; text-transform: uppercase; color: var(--fg-dim); }
.board-wrap { position: relative; background: var(--bg-input); border: 1px solid var(--line); border-radius: 6px; height: 68vh; min-height: 360px; overflow: hidden; touch-action: none; }
#board { width: 100%; height: 100%; display: block; cursor: grab; user-select: none; -webkit-user-select: none; }
#board.panning { cursor: grabbing; }
.board-tools { position: absolute; top: 8px; left: 8px; display: flex; gap: 6px; flex-wrap: wrap; }
.board-tools button { padding: 4px 9px; font-size: 13px; }
.toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 0 0 10px; }
.toolbar input[type=text], .toolbar select { min-width: 0; max-width: 100%; }
.toolbar .filepick { display: inline-flex; gap: 6px; align-items: center; max-width: 100%; color: var(--fg-dim); }
.toolbar .filepick input { min-width: 0; max-width: 100%; }
.lede { color: var(--fg-dim); max-width: var(--wide); }
.toolbar .grow { flex: 1 1 200px; }
#status { min-height: 1.4em; font-size: 14px; margin: 0 0 8px; }
#status.err { color: var(--err); } #status.ok { color: var(--ok); }
.stat { font-family: var(--font-mono); font-size: 12.5px; color: var(--fg-dim); line-height: 1.6; overflow-wrap: anywhere; }
.stat b { color: var(--fg); font-weight: 500; }
#info pre { margin: 6px 0 0; max-height: 220px; overflow: auto; font-size: 12px; white-space: pre-wrap; overflow-wrap: anywhere; }
#problems { list-style: none; margin: 0; padding: 0; font-size: 13px; }
#problems li { padding: 4px 0; border-top: 1px solid var(--line-soft); cursor: pointer; overflow-wrap: anywhere; }
#problems li:first-child { border-top: 0; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 12px; font-size: 12.5px; color: var(--fg-dim); }
.legend span::before { content: ""; display: inline-block; width: 10px; height: 10px; margin-right: 5px; vertical-align: -1px; background: var(--sw); border-radius: 2px; }
.cell { cursor: default; }
.cell.mov { cursor: move; }
.cell.sel rect { stroke: var(--fg); stroke-width: 2.2; }
.cell.pinned rect { stroke-dasharray: 3 2; }
.route { fill: none; stroke-width: 1.8; stroke-linejoin: round; stroke-linecap: round; opacity: .85; }
.route.second { stroke-dasharray: 5 4; }
.route.hl { stroke-width: 3.4; opacity: 1; }
.ghost rect { fill: none; stroke-width: 2.5; }
.ghost.good rect { stroke: var(--ok); } .ghost.bad rect { stroke: var(--err); }
.lbl { font-family: var(--font-mono); fill: #0e130f; font-weight: 500; pointer-events: none; }
@media (max-width: 860px) {
  .composer { grid-template-columns: 1fr; }
  .board-wrap { height: 60vh; }
}
"""

CORE_COLOURS = {"adder": "#c17f45", "mul": "#d9b46a", "comparator": "#7fa6d0", "const": "#7fae7a", "io": "#e9ede6", "ram": "#627262", "cross": "#d0786a",
                "branch": "#b48ad0", "nano": "#b48ad0", "latch": "#9aab98", "accumulator": "#9aab98", "sequencer": "#9aab98"}


def page_composer():
    ex_opts = "".join(f'<option value="{e}">{e}</option>' for e in examples())
    b_opts = "".join(f'<option value="{b}">{b}</option>' for b in flv.BUILDERS)
    legend = "".join(f'<span style="--sw:{c}">{k}</span>' for k, c in CORE_COLOURS.items() if k not in ("latch", "accumulator", "sequencer", "nano"))
    body = f"""<h1>Composer: arrange a layout</h1>
<p class="lede">Import an ICM file and move its logic cells by dragging them. On each drop the layout engine (<code>tools/flex_layout_v1.py</code>) re-routes that cell's
connections and re-balances operand timing. If it cannot, the move is refused and nothing changes. Relays are drawn as the route lines they make up. Cells wired by fields
the engine does not derive (nano, branch) are drawn dashed and stay where they are. The page only arranges cells; it never adds connections. Save writes ICM v3, in the
file's own coordinates.</p>

<div class="toolbar">
  <label class="filepick">ICM file <input type="file" id="file" accept=".json,.icm"></label>
  <select id="example"><option value="">example…</option>{ex_opts}</select>
  <select id="builder"><option value="">built by Python…</option>{b_opts}</select>
  <input type="text" id="path" class="grow" placeholder="or a path on this machine, e.g. out/design.icm.json">
  <button id="loadPath">Load path</button>
</div>
<div id="status" role="status"></div>

<div class="composer">
  <div class="board-wrap" id="wrap">
    <svg id="board" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg"><g id="view"><g id="grid"></g><g id="routes"></g><g id="cells"></g><g id="over"></g></g></svg>
    <div class="board-tools">
      <button id="fit" title="fit the layout to the view">Fit</button>
      <button id="zin" title="zoom in">+</button>
      <button id="zout" title="zoom out">−</button>
      <button id="undo" title="undo the last move">Undo</button>
      <button id="heat" title="tint cells by hop depth">Hop heat</button>
      <button id="save" class="primary" title="download the edited design as ICM v3">Save ICM</button>
    </div>
  </div>
  <div class="side">
    <div class="panel"><h3>Layout</h3><div id="summary" class="stat">nothing loaded</div></div>
    <div class="panel"><h3>Find</h3><input type="text" id="find" placeholder="cell name" style="width:100%"></div>
    <div class="panel"><h3>Cell</h3><div id="info" class="stat">tap or hover a cell</div></div>
    <div class="panel"><h3>Problems</h3><ul id="problems"><li>none</li></ul></div>
    <div class="panel"><h3>Legend</h3><div class="legend">{legend}<span style="--sw:transparent;outline:1px dashed var(--fg-dim)">pinned</span></div>
      <div class="stat" style="margin-top:6px">solid line: a route; dashed: a second word (carry / high word); ✕: crossing tile</div></div>
  </div>
</div>
<pre>python3 tools/flex_layout_view_v1.py FILE.icm.json          # the same import, as a summary
python3 tools/flex_layout_view_v1.py --builder fp_add/fp16 --json out.json</pre>
<script>{_JS.replace("__COLOURS__", json.dumps(CORE_COLOURS))}</script>"""
    return ui.page("Composer", body, active="composer", extra_css=COMPOSER_CSS, narrow=False)


_JS = r"""
(() => {
const COL = __COLOURS__;
const S = 10;                       // one square = 10 svg units
const NS = 'http://www.w3.org/2000/svg';
const $ = id => document.getElementById(id);
const svg = $('board'), view = $('view'), wrap = $('wrap');
function W() { return Math.max(1, wrap.getBoundingClientRect().width); }
function H() { return Math.max(1, wrap.getBoundingClientRect().height); }
let L = null, cellBy = {}, occ = {}, sel = null, heat = false;
let vb = {x: 0, y: 0, w: 400, h: 300};

function status(msg, kind) { const s = $('status'); s.textContent = msg || ''; s.className = kind || ''; }
function el(tag, attrs, parent) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function setVB() { svg.setAttribute('viewBox', `${vb.x} ${vb.y} ${vb.w} ${vb.h}`); }
async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  return r.json();
}
function colour(c) {
  if (c.core === 'ram') return c.io ? COL.io : (c.preload !== null && c.preload !== undefined ? COL.const : COL.ram);
  return COL[c.core] || COL.ram;
}
function heatColour(h, max) {
  if (h === null || h === undefined) return '#333';
  const t = max ? h / max : 0;
  return `hsl(${Math.round(210 - 190 * t)},55%,${Math.round(38 + 14 * t)}%)`;
}
function fileSquare(r, c) { return [r - L.offset[0], c - L.offset[1]]; }

function draw(keepView) {
  ['grid', 'routes', 'cells', 'over'].forEach(id => { $(id).innerHTML = ''; });
  if (!L) return;
  cellBy = {}; occ = {};
  for (const c of L.cells) cellBy[c.name] = c;
  const g = $('grid');
  el('rect', {x: 0, y: 0, width: L.cols * S, height: L.rows * S, fill: 'var(--bg)', stroke: 'var(--line)'}, g);
  const pat = el('path', {d: '', stroke: 'var(--line-soft)', 'stroke-width': .5, fill: 'none'}, g);
  let d = '';
  for (let r = 1; r < L.rows; r++) d += `M0 ${r * S}H${L.cols * S}`;
  for (let c = 1; c < L.cols; c++) d += `M${c * S} 0V${L.rows * S}`;
  pat.setAttribute('d', d);
  const rg = $('routes');
  for (const rt of L.routes) {
    const pts = rt.points.map(p => `${p[1] * S + S / 2},${p[0] * S + S / 2}`).join(' ');
    const src = cellBy[rt.from];
    const line = el('polyline', {points: pts, class: 'route' + (rt.second ? ' second' : ''), stroke: src ? colour(src) : COL.ram}, rg);
    line.dataset.key = rt.from + '→' + rt.to;
    line.addEventListener('mouseenter', () => { line.classList.add('hl'); status(`route ${rt.from} → ${rt.to}: ${rt.relays} relays` + (rt.extra ? `, ${rt.extra} of them a timing detour` : '') + (rt.crossings.length ? `, ${rt.crossings.length} crossing tile(s)` : '')); });
    line.addEventListener('mouseleave', () => line.classList.remove('hl'));
    for (const p of rt.points.slice(1, -1)) occ[p[0] + ',' + p[1]] = 'route:' + rt.from + '|' + rt.to;
  }
  for (const ln of L.links) {
    const a = cellBy[ln.a], b = cellBy[ln.b];
    if (a && b) el('line', {x1: a.c * S + S / 2, y1: a.r * S + S / 2, x2: b.c * S + S / 2, y2: b.r * S + S / 2, class: 'route' + (ln.second ? ' second' : ''), stroke: colour(a)}, rg);
  }
  const cg = $('cells');
  for (const x of L.crossings) {
    const cx = x.c * S + S / 2, cy = x.r * S + S / 2, k = S * .32;
    el('path', {d: `M${cx - k} ${cy - k}L${cx + k} ${cy + k}M${cx + k} ${cy - k}L${cx - k} ${cy + k}`, stroke: COL.cross, 'stroke-width': 2}, cg);
  }
  const maxHop = L.summary.max_hop;
  for (const c of L.cells) {
    if (c.core === 'cross') continue;
    occ[c.r + ',' + c.c] = c.name;
    const gr = el('g', {class: 'cell' + (c.movable ? ' mov' : '') + (c.pinned ? ' pinned' : ''), transform: `translate(${c.c * S},${c.r * S})`}, cg);
    gr.dataset.name = c.name;
    const fill = heat ? heatColour(c.hop, maxHop) : colour(c);
    el('rect', {x: .8, y: .8, width: S - 1.6, height: S - 1.6, rx: 1.6, fill, stroke: c.pinned ? 'var(--fg-dim)' : '#0008', 'stroke-width': .8}, gr);
    const short = c.name.split('.').pop();
    const t = el('text', {x: S / 2, y: S / 2 + 1.2, 'text-anchor': 'middle', 'font-size': 3.2, class: 'lbl lblsmall'}, gr);
    t.textContent = short.length > 6 ? short.slice(0, 6) : short;
    if (sel === c.name) gr.classList.add('sel');
  }
  updateLabels();
  summary();
  problems();
  if (!keepView) fit();
}

function updateLabels() {
  const px = W() / vb.w * S;          // screen pixels per square
  document.querySelectorAll('.lblsmall').forEach(t => { t.style.display = px > 26 ? '' : 'none'; });
}
function summary() {
  const s = L.summary, bc = Object.entries(s.by_core).map(([k, v]) => `${k} ${v}`).join(', ');
  const mov = L.cells.filter(c => c.movable).length;
  $('summary').innerHTML = `<b>${L.name}</b><br>${s.cells} cells (${bc})<br>${s.routes} routes, ${s.relays} relays, ${L.crossings.length} crossings<br>` +
    `deepest hop <b>${s.max_hop}</b>; ${mov} movable, ${s.pinned} pinned` + (s.undo ? `; ${s.undo} undo step(s)` : '') +
    (s.timing_error ? `<br><span style="color:var(--err)">no timing: ${s.timing_error}</span>` : '') +
    (L.warnings.length ? `<br><span style="color:var(--warn)">${L.warnings.length} warning(s): ${L.warnings.slice(0, 3).join('; ')}</span>` : '');
}
function problems() {
  const ul = $('problems'); ul.innerHTML = '';
  if (!L.problems.length) { ul.innerHTML = '<li style="cursor:default;color:var(--ok)">none: every operand pair is ordered</li>'; return; }
  for (const p of L.problems) {
    const li = document.createElement('li');
    li.textContent = `${p.cell}: ${p.kind === 'tie' ? 'operands tie' : 'minuend not first'} (${p.early} / ${p.late})`;
    li.style.color = p.kind === 'tie' ? 'var(--warn)' : 'var(--err)';
    li.onclick = () => focusCell(p.cell);
    ul.appendChild(li);
  }
}
function showInfo(c) {
  if (!c) { $('info').textContent = 'tap or hover a cell'; return; }
  const [fr, fc] = fileSquare(c.r, c.c);
  const ins = L.routes.filter(r => r.to === c.name).map(r => r.from), outs = L.routes.filter(r => r.from === c.name).map(r => r.to);
  const detail = Object.assign({}, c.cfg, Object.keys(c.addon || {}).length ? {addon: c.addon} : {}, c.preload !== null && c.preload !== undefined ? {preload: c.preload} : {});
  $('info').innerHTML = `<b>${c.name}</b><br>${c.core}${c.io ? ' · io ' + c.io : ''} · file square (${fr}, ${fc}) · hop ${c.hop ?? '?'}<br>` +
    (c.movable ? 'drag to move' : c.pinned ? '<span style="color:var(--warn)">pinned</span>' : 'fixed') +
    (ins.length ? `<br>from: ${ins.join(', ')}` : '') + (outs.length ? `<br>to: ${outs.join(', ')}` : '') +
    `<pre>${JSON.stringify(detail, null, 1)}</pre>`;
}
function focusCell(name) {
  const c = cellBy[name]; if (!c) { status(`no cell ${name}`, 'err'); return; }
  sel = name; vb.w = 24 * S; vb.h = vb.w * H() / W();
  vb.x = c.c * S - vb.w / 2; vb.y = c.r * S - vb.h / 2; setVB(); draw(true); showInfo(c);
}
function fit() {
  if (!L) return;
  let r0 = 1e9, r1 = -1, c0 = 1e9, c1 = -1;
  for (const c of L.cells) { r0 = Math.min(r0, c.r); r1 = Math.max(r1, c.r); c0 = Math.min(c0, c.c); c1 = Math.max(c1, c.c); }
  for (const rt of L.routes) for (const p of rt.points) { r0 = Math.min(r0, p[0]); r1 = Math.max(r1, p[0]); c0 = Math.min(c0, p[1]); c1 = Math.max(c1, p[1]); }
  const w = (c1 - c0 + 3) * S, h = (r1 - r0 + 3) * S, ar = W() / H();
  vb.w = Math.max(w, h * ar); vb.h = vb.w / ar;
  vb.x = (c0 - 1) * S - (vb.w - w) / 2; vb.y = (r0 - 1) * S - (vb.h - h) / 2;
  setVB(); updateLabels();
}
function zoom(f, cx, cy) {
  if (cx === undefined) { cx = vb.x + vb.w / 2; cy = vb.y + vb.h / 2; }
  vb.x = cx - (cx - vb.x) * f; vb.y = cy - (cy - vb.y) * f; vb.w *= f; vb.h *= f; setVB(); updateLabels();
}
function toSvg(ev) { const p = svg.createSVGPoint(); p.x = ev.clientX; p.y = ev.clientY; return p.matrixTransform(view.getScreenCTM().inverse()); }

// pointer handling: drag the background to pan, drag a movable cell to move it, two fingers to pinch-zoom
const pts = new Map(); let pan = null, drag = null, pinch = null;
svg.addEventListener('pointerdown', ev => {
  svg.setPointerCapture(ev.pointerId); pts.set(ev.pointerId, ev);
  if (pts.size === 2) { const [a, b] = [...pts.values()]; pinch = {d: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY)}; pan = drag = null; clearGhost(); return; }
  const g = ev.target.closest('.cell');
  const c = g && cellBy[g.dataset.name];
  if (c) { sel = c.name; showInfo(c); document.querySelectorAll('.cell.sel').forEach(x => x.classList.remove('sel')); g.classList.add('sel'); }
  if (c && c.movable) { drag = {c, start: toSvg(ev), r: c.r, cc: c.c, moved: false}; return; }
  pan = {x: ev.clientX, y: ev.clientY, vx: vb.x, vy: vb.y}; svg.classList.add('panning');
});
svg.addEventListener('pointermove', ev => {
  if (pts.has(ev.pointerId)) pts.set(ev.pointerId, ev);
  if (pinch && pts.size === 2) {
    const [a, b] = [...pts.values()], d = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
    const mid = toSvg({clientX: (a.clientX + b.clientX) / 2, clientY: (a.clientY + b.clientY) / 2});
    if (d > 0) zoom(pinch.d / d, mid.x, mid.y); pinch.d = d; return;
  }
  if (drag) {
    const p = toSvg(ev), r = Math.floor(p.y / S), c = Math.floor(p.x / S);
    if (r !== drag.r || c !== drag.cc) { drag.r = r; drag.cc = c; drag.moved = r !== drag.c.r || c !== drag.c.c; ghost(drag.c, r, c); }
    return;
  }
  if (pan) {
    const k = vb.w / W();
    vb.x = pan.vx - (ev.clientX - pan.x) * k; vb.y = pan.vy - (ev.clientY - pan.y) * k; setVB(); return;
  }
  const g = ev.target.closest && ev.target.closest('.cell');
  if (g && cellBy[g.dataset.name] && ev.pointerType === 'mouse') showInfo(cellBy[g.dataset.name]);
});
function endPointer(ev) {
  pts.delete(ev.pointerId);
  if (pinch) { if (pts.size < 2) pinch = null; return; }
  svg.classList.remove('panning'); pan = null;
  if (drag) { const d = drag; drag = null; clearGhost(); if (d.moved && ev.type === 'pointerup') doMove(d.c, d.r, d.cc); }
}
svg.addEventListener('pointerup', endPointer);
svg.addEventListener('pointercancel', endPointer);
svg.addEventListener('wheel', ev => { ev.preventDefault(); const p = toSvg(ev); zoom(ev.deltaY > 0 ? 1.15 : 1 / 1.15, p.x, p.y); }, {passive: false});

function ownRoute(c, key) { return key && key.startsWith('route:') && key.slice(6).split('|').includes(c.name); }
function ghost(c, r, cc) {
  clearGhost();
  const o = occ[r + ',' + cc];
  const ok = r >= 0 && cc >= 0 && r < L.rows && cc < L.cols && (!o || o === c.name || ownRoute(c, o));
  const g = el('g', {class: 'ghost ' + (ok ? 'good' : 'bad'), transform: `translate(${cc * S},${r * S})`}, $('over'));
  el('rect', {x: .4, y: .4, width: S - .8, height: S - .8, rx: 1.6}, g);
  const [fr, fc] = fileSquare(r, cc);
  status(ok ? `drop to move ${c.name} to (${fr}, ${fc})` : `(${fr}, ${fc}) is taken` + (o && !o.startsWith('route:') ? ` by ${o}` : ' by a route'), ok ? '' : 'err');
}
function clearGhost() { $('over').innerHTML = ''; }

async function doMove(c, r, cc) {
  const [fr, fc] = fileSquare(r, cc);
  status(`moving ${c.name} to (${fr}, ${fc}): re-routing…`);
  const res = await api('/composer/api/move', {name: c.name, r, c: cc});
  if (!res.ok) { status(`refused: ${res.error}`, 'err'); return; }
  L = res.layout; draw(true); showInfo(cellBy[c.name]);
  status(`moved ${c.name} to (${fr}, ${fc}); re-routed ${res.rerouted.length} route(s)` + (res.detours ? `, ${res.detours} timing detour(s) added` : '') +
         (L.problems.length ? `; ${L.problems.length} problem(s) left` : '; no timing problems'), 'ok');
}
async function load(body) {
  status('loading…');
  const res = await api('/composer/api/load', body);
  if (!res.ok) { status(res.error, 'err'); return; }
  L = res.layout; sel = null; showInfo(null); draw(false);
  status(`loaded ${L.name}`, 'ok');
}
$('file').onchange = async ev => { const f = ev.target.files[0]; if (f) load({name: f.name, text: await f.text()}); ev.target.value = ''; };
$('example').onchange = ev => { if (ev.target.value) load({example: ev.target.value}); ev.target.value = ''; };
$('builder').onchange = ev => { if (ev.target.value) { status('building ' + ev.target.value + '…'); load({builder: ev.target.value}); } ev.target.value = ''; };
$('loadPath').onclick = () => { const p = $('path').value.trim(); if (p) load({path: p}); };
$('path').onkeydown = ev => { if (ev.key === 'Enter') $('loadPath').onclick(); };
$('fit').onclick = fit;
$('zin').onclick = () => zoom(1 / 1.4);
$('zout').onclick = () => zoom(1.4);
$('heat').onclick = () => { heat = !heat; $('heat').classList.toggle('primary', heat); draw(true); };
$('undo').onclick = async () => { const res = await api('/composer/api/undo', {}); if (!res.ok) { status(res.error, 'err'); return; } L = res.layout; draw(true); status('undone', 'ok'); };
$('save').onclick = () => { if (!L) { status('nothing to save', 'err'); return; } window.location = '/composer/api/save'; };
$('find').onkeydown = ev => {
  if (ev.key !== 'Enter') return;
  const q = ev.target.value.trim().toLowerCase(); if (!q || !L) return;
  const hit = L.cells.find(c => c.name.toLowerCase() === q) || L.cells.find(c => c.name.toLowerCase().includes(q));
  hit ? focusCell(hit.name) : status(`no cell matches ${q}`, 'err');
};
window.addEventListener('resize', () => { if (L) { vb.h = vb.w * H() / W(); setVB(); updateLabels(); } });
api('/composer/api/state').then(res => { if (res.layout) { L = res.layout; draw(false); } else { setVB(); status('import an ICM file, or pick an example or a layout built by Python'); } });
})();
"""
