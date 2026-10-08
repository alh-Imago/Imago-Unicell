"""nano/composer_page_v1.py -- the front panel's /composer page (design note docs/stripped-cell/design-notes/composer_layout_viewer_scope.md).

Import an ICM file or start a blank board; place cells from the palette; set each cell's configuration in an explainer-style panel (every field with its bit range, the add-on
fields, the 80-bit SUPER_LATCH it encodes to); join cells (the layout engine lays the route); insert saved designs from the LIBRARY as single blocks whose io-named cells are their
ports; drag cells and blocks; undo; save ICM v3, or save into the library so the design can be reused as a block. Every edit is a request to
`tools/flex_layout_view_v1.Layout`; a refused edit changes nothing. This module holds the controller (no HTTP) and the page; `frontend_v1.py` dispatches to it."""
import json
import os
import re
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, HERE)

import flex_layout_sim_v1 as fls  # noqa: E402
import flex_layout_view_v1 as flv  # noqa: E402
import ui_theme_v1 as ui  # noqa: E402

EXAMPLES_DIR = os.path.join(HERE, "examples")
STD_DIR = os.path.join(HERE, "library_std")          # the ready-made STANDARD library (read-only here; built by tools/composer_stdlib_v1.py)
LIBRARY_DIR = os.environ.get("IMAGO_LIBRARY", os.path.join(HERE, "library"))
DIRS = {"std": STD_DIR, "library": LIBRARY_DIR, "example": EXAMPLES_DIR}


def _icm_files(d):
    try:
        return sorted(f for f in os.listdir(d) if f.endswith((".icm", ".json")) and not f.endswith(".test.json") and not f.startswith("."))
    except OSError:
        return []


def examples():
    return _icm_files(EXAMPLES_DIR)


_DESC = {}


def _describe(path):
    """A model's one-line description (from its file), cached by modification time."""
    try:
        key = (path, os.path.getmtime(path))
        if key not in _DESC:
            with open(path) as f:
                _DESC[key] = (json.load(f).get("description") or "")[:200]
        return _DESC[key]
    except (OSError, ValueError):
        return ""


def library():
    """Library models: the standard library, the user's library, then the shipped examples."""
    flv.LIBRARY_DIRS[:] = [STD_DIR, LIBRARY_DIR, EXAMPLES_DIR]       # where a block's model is found again after a reload
    out = []
    for source in ("std", "library", "example"):
        d = DIRS[source] if source != "library" else LIBRARY_DIR
        for f in _icm_files(d):
            if f.endswith(".test.json"):
                continue
            out.append({"name": f, "source": source, "desc": _describe(os.path.join(d, f)), "tested": os.path.isfile(flv.vectors_path(os.path.join(d, f)))})
    return out


def _library_path(name, source):
    d = {"std": STD_DIR, "library": LIBRARY_DIR}.get(source, EXAMPLES_DIR)
    base = os.path.basename(name or "")
    if base not in _icm_files(d):
        raise ValueError(f"no {source} model {base}")
    return os.path.join(d, base)


class ComposerController:
    """One layout per front-panel server (a local, single-person tool). Every method returns a JSON-able dict."""

    def __init__(self):
        self.layout = None
        self.sim = None                     # the step-through run; any edit to the design ends it
        self.lock = threading.Lock()

    def _state(self, extra=None):
        out = {"ok": True, "layout": self.layout.snapshot() if self.layout else None, "library": library(), "sim": self.sim.view() if self.sim else None}
        out.update(extra or {})
        return out

    def state(self):
        with self.lock:
            return self._state()

    def load(self, req):
        """req: {"builder"} | {"example"} | {"library"} | {"path"} | {"name", "text"} | {"new": {"rows", "cols", "name"}}."""
        with self.lock:
            try:
                if req.get("new"):
                    n = req["new"]
                    lay = flv.Layout.new(int(n.get("rows", 24)), int(n.get("cols", 40)), str(n.get("name") or "new design"))
                elif req.get("builder"):
                    lay = flv.from_builder(req["builder"])
                elif req.get("example"):
                    lay = flv.Layout.load(_library_path(req["example"], "example"))
                elif req.get("library"):
                    lay = flv.Layout.load(_library_path(req["library"], "library"))
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
            self.layout, self.sim = lay, None
            return self._state()

    def sim_op(self, req):
        """The step-through: op = start | inject {values} | step {n} | run | items {items} | stop."""
        with self.lock:
            if not self.layout:
                return {"ok": False, "error": "no layout"}
            op = req.get("op")
            try:
                if op == "start":
                    self.sim = fls.StepSim(self.layout, width=int(req["width"]) if req.get("width") else None)
                elif op == "stop":
                    self.sim = None
                elif not self.sim:
                    return {"ok": False, "error": "press Start first"}
                elif op == "inject":
                    self.sim.inject(_ints(req.get("values")))
                elif op == "step":
                    self.sim.step(int(req.get("n", 1)))
                elif op == "run":
                    self.sim.run(int(req.get("max", 2000)))
                elif op == "items":
                    items = {k: [int(x, 0) for x in re.split(r"[\s,;]+", str(v).strip()) if x] for k, v in (req.get("items") or {}).items()}
                    self.sim.run_items({k: v for k, v in items.items() if v}, int(req.get("max", 2000)))
                else:
                    return {"ok": False, "error": f"unknown step-through op {op}"}
            except Exception as e:                    # a design the VM cannot run, or a bad value: reported, not raised
                return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}
            return {"ok": True, "sim": self.sim.view() if self.sim else None}

    def move(self, req):
        return self.edit("move", req)

    def undo(self):
        return self.edit("undo", {})

    def edit(self, action, req):
        """One editing action on the current layout: move, add, config, join, unjoin, delete, minuend, balance, undo, block, move_block, unpack_block, delete_block."""
        with self.lock:
            lay = self.layout
            if not lay:
                return {"ok": False, "error": "no layout: import a file or start a new design"}
            try:
                if action == "move":
                    res = lay.move(str(req["name"]), int(req["r"]), int(req["c"]), whole_block=bool(req.get("whole_block", True)))
                elif action == "add":
                    res = lay.add_cell(str(req["core"]), int(req["r"]), int(req["c"]), name=req.get("name") or None, block=req.get("block") or None)
                elif action == "check_block":
                    res = lay.check_block(str(req["name"]))
                elif action == "config":
                    res = lay.set_config(str(req["name"]), cfg=_ints(req.get("cfg")), addon=_ints(req.get("addon")), preload=req.get("preload"), io=req.get("io"))
                elif action == "join":
                    res = lay.join(str(req["a"]), str(req["b"]), out=req.get("out") or None, role=req.get("role") or None)
                elif action == "unjoin":
                    res = lay.unjoin(str(req["a"]), str(req["b"]))
                elif action == "delete":
                    res = lay.delete_cell(str(req["name"]))
                elif action == "minuend":
                    res = lay.set_minuend(str(req["name"]), req.get("source") or None)
                elif action == "balance":
                    res = lay.balance()
                elif action == "undo":
                    res = lay.undo()
                elif action == "block":
                    if req.get("text"):
                        with tempfile.TemporaryDirectory() as d:
                            p = os.path.join(d, os.path.basename(req.get("file") or "block.icm.json"))
                            with open(p, "w") as f:
                                f.write(req["text"])
                            res = lay.place_block(p, int(req["r"]), int(req["c"]), as_components=bool(req.get("components")), source="file")
                    else:
                        src = req.get("source") or "library"
                        res = lay.place_block(_library_path(req.get("file"), src), int(req["r"]), int(req["c"]), as_components=bool(req.get("components")), source=src)
                elif action == "move_block":
                    res = lay.move_block(str(req["name"]), int(req["r"]), int(req["c"]))
                elif action == "unpack_block":
                    res = lay.unpack_block(str(req["name"]))
                elif action == "delete_block":
                    res = lay.delete_block(str(req["name"]))
                else:
                    return {"ok": False, "error": f"unknown action {action}"}
            except (KeyError, ValueError, TypeError) as e:
                return {"ok": False, "error": f"bad {action} request: {e}"}
            if not res.get("ok"):
                return res
            self.sim = None
            return self._state({k: v for k, v in res.items() if k != "ok"})

    def save_library(self, req):
        """Write the current design into the library folder, so it can be placed as a block in another design."""
        with self.lock:
            if not self.layout:
                return {"ok": False, "error": "nothing to save"}
            name = re.sub(r"[^A-Za-z0-9_.-]", "_", str(req.get("name") or "")).strip("._")
            if not name:
                return {"ok": False, "error": "give the model a name"}
            if not name.endswith(".icm.json"):
                name += ".icm.json"
            if not any(self.layout.io.values()):
                return {"ok": False, "error": "a library model needs at least one io-named cell: those are its ports"}
            os.makedirs(LIBRARY_DIR, exist_ok=True)
            path = os.path.join(LIBRARY_DIR, name)
            if os.path.exists(path) and not req.get("overwrite"):
                return {"ok": False, "error": f"{name} is already in the library", "exists": True}
            try:
                vec = None
                sim = self.sim
                if sim and sim.items and sim.fed:                     # what the person just stepped through becomes the model's reference
                    io_in = {k: self.layout.io.get(k) or k for k in sim.inputs}
                    vec = {"width": sim.width, "inputs": {io_in[k]: [item.get(k, 0) for item in sim.fed] for k in sim.inputs},
                           "outputs": {self.layout.io.get(k) or k: list(sim.seen[k]) for k in sim.outputs}}
                _, vec = flv.save_model(self.layout, path, vectors=vec)
            except Exception as e:
                return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}
            return self._state({"saved": name, "vectors": sum(len(v) for v in vec["outputs"].values())})

    def icm_text(self, fmt=None):
        """(file name, text): ICM-VIX when the design holds blocks (they survive), else ICM v3; fmt="v3" forces one flat file."""
        with self.lock:
            if not self.layout:
                return None, None
            from icm_v3 import IcmV3File
            lay = self.layout
            fmt = fmt if fmt in ("v3", "vix") else ("vix" if lay.blocks else "v3")
            if fmt == "vix":
                f = lay.to_vix()
                d = f.to_dict()
                d["record_hash"] = f.record_hash()
            else:
                d = IcmV3File(name=lay.name, records=lay.records(), description=lay.description or "made in the Composer", min_bit_width=lay.min_bit_width).to_dict()
            base = lay.name.split("/")[-1]
            for suf in (".icm-hier.json", ".icm.json", ".json", ".icm"):
                if base.endswith(suf):
                    base = base[: -len(suf)]
            ext = ".icm-hier.json" if fmt == "vix" else ".icm.json"
            return f"{re.sub(r'[^A-Za-z0-9_.-]', '_', base)}.composed{ext}", json.dumps(d, indent=2)


def _ints(d):
    """Form values as integers: decimal, 0x hex or 0b binary; '' means 0."""
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, bool):
            v = int(v)
        if isinstance(v, str):
            v = v.strip().replace("_", "")
            v = int(v, 0) if v else 0
        out[str(k)] = int(v)
    return out


COMPOSER_CSS = """
.composer { display: grid; grid-template-columns: 1fr 330px; gap: 14px; align-items: start; }
.composer .side { display: flex; flex-direction: column; gap: 12px; min-width: 0; position: sticky; top: 64px; max-height: calc(100vh - 76px); overflow-y: auto; overscroll-behavior: contain; padding-right: 2px; }
.composer .panel { background: var(--bg-panel); border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px; min-width: 0; }
.composer .panel h3 { margin: 0 0 8px; font-size: 13px; letter-spacing: .04em; text-transform: uppercase; color: var(--fg-dim); }
.board-wrap { position: relative; background: var(--bg-input); border: 1px solid var(--line); border-radius: 6px; height: 70vh; min-height: 360px; overflow: hidden; touch-action: none; }
#board { width: 100%; height: 100%; display: block; cursor: grab; user-select: none; -webkit-user-select: none; }
#board.panning { cursor: grabbing; } #board.placing, #board.joining, #board.deleting { cursor: crosshair; }
.board-tools { position: absolute; top: 8px; left: 8px; right: 8px; display: flex; gap: 6px; flex-wrap: wrap; pointer-events: none; }
.board-tools > * { pointer-events: auto; }
.board-tools button { padding: 4px 9px; font-size: 13px; }
.toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 0 0 10px; }
.toolbar input[type=text], .toolbar select, .modes select { min-width: 0; max-width: 100%; }
.filepick { display: inline-flex; gap: 6px; align-items: center; max-width: 100%; color: var(--fg-dim); }
.filepick input { min-width: 0; max-width: 100%; }
.toolbar .grow { flex: 1 1 200px; }
.lede { color: var(--fg-dim); max-width: var(--wide); }
.modes { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 8px; align-items: center; }
.modes button.on { background: var(--copper); color: var(--bg); border-color: var(--copper); }
.palette { display: flex; flex-wrap: wrap; gap: 4px; }
.palette button { font-size: 12px; padding: 3px 7px; border-left: 4px solid var(--sw); }
.palette button.on { background: var(--bg-panel-2); outline: 1px solid var(--fg); }
#status { min-height: 1.4em; font-size: 14px; margin: 8px 0; overflow-wrap: anywhere; }
#status.err { color: var(--err); } #status.ok { color: var(--ok); }
.stat { font-family: var(--font-mono); font-size: 12.5px; color: var(--fg-dim); line-height: 1.6; overflow-wrap: anywhere; }
.stat b { color: var(--fg); font-weight: 500; }
#problems { list-style: none; margin: 0; padding: 0; font-size: 13px; }
#problems li { padding: 4px 0; border-top: 1px solid var(--line-soft); cursor: pointer; overflow-wrap: anywhere; }
#problems li:first-child { border-top: 0; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 12px; font-size: 12.5px; color: var(--fg-dim); }
.legend span::before { content: ""; display: inline-block; width: 10px; height: 10px; margin-right: 5px; vertical-align: -1px; background: var(--sw); border-radius: 2px; }
.cell.mov { cursor: move; }
.cell.sel rect { stroke: var(--fg); stroke-width: 1.6; }
.cell.src rect { stroke: var(--gold); stroke-width: 1.8; }
.cell.pinned rect { stroke-dasharray: 2 1.5; }
.route { fill: none; stroke-width: 1.8; stroke-linejoin: round; stroke-linecap: round; opacity: .85; }
.route.second { stroke-dasharray: 5 4; }
.route.hl { stroke-width: 3.4; opacity: 1; }
.blk rect.body { fill: var(--bg-panel-2); stroke: var(--copper); stroke-width: 1.2; }
.blk.sel rect.body { stroke: var(--fg); stroke-width: 1.8; }
.blk { cursor: move; }
.blk.open rect.body { fill: none; stroke-dasharray: 4 2; }
.blk.open { cursor: default; }
.blk .bar { fill: var(--bg-panel-2); stroke: var(--copper); stroke-width: .6; cursor: move; }
.badge { font-family: var(--font-mono); pointer-events: none; }
.st-ok { color: var(--ok); } .st-mod { color: var(--warn); } .st-bad { color: var(--err); }
.blk text { font-family: var(--font-mono); fill: var(--fg); pointer-events: none; }
.port { fill: var(--gold); stroke: #0e130f; stroke-width: .6; cursor: crosshair; }
.ghost rect { fill: none; stroke-width: 1.6; }
.ghost.good rect { stroke: var(--ok); } .ghost.bad rect { stroke: var(--err); }
.lbl { font-family: var(--font-mono); fill: #0e130f; font-weight: 500; pointer-events: none; }
.chooser { position: absolute; z-index: 5; background: var(--bg-panel); border: 1px solid var(--copper); border-radius: 6px; padding: 6px; display: flex; flex-direction: column; gap: 4px; min-width: 120px; }
.chooser b { font-size: 12px; color: var(--fg-dim); font-weight: 500; }
.chooser button { font-size: 13px; padding: 3px 8px; text-align: left; }
#cfg .row { display: grid; grid-template-columns: 1fr 112px; gap: 6px; align-items: center; margin: 3px 0; }
#cfg .row label { font-family: var(--font-mono); font-size: 12px; color: var(--fg-dim); overflow-wrap: anywhere; }
#cfg .row label small { color: var(--fg-faint); }
#cfg .row input[type=text], #cfg .row select { width: 100%; font-family: var(--font-mono); font-size: 12px; padding: 3px 5px; }
#cfg .dirs { display: flex; gap: 3px; }
#cfg .dirs span { width: 22px; text-align: center; font-family: var(--font-mono); font-size: 11px; border: 1px solid var(--line); border-radius: 3px; color: var(--fg-faint); }
#cfg .dirs span.on { background: var(--copper); color: var(--bg); border-color: var(--copper); }
#cfg details { margin: 6px 0; } #cfg summary { cursor: pointer; font-size: 12.5px; color: var(--fg-dim); }
#cfg .actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.bitbar { display: flex; height: 16px; border: 1px solid var(--line); border-radius: 3px; overflow: hidden; margin: 8px 0 2px; }
.bitbar span { border-right: 1px solid var(--bg); background: var(--bg-input); }
.bitbar span.set { background: var(--copper); } .bitbar span.dir.set { background: var(--in); }
.bitbar span.sel.set { background: var(--gold); } .bitbar span.addon.set { background: var(--ok); }
.latch { font-family: var(--font-mono); font-size: 12px; color: var(--fg); overflow-wrap: anywhere; }
.joins { font-size: 12px; margin: 6px 0 0; padding-left: 16px; }
.joins li { overflow-wrap: anywhere; }
.joins button { font-size: 11px; padding: 0 5px; margin-left: 4px; }
#run .io { display: grid; grid-template-columns: 70px 1fr; gap: 4px 6px; align-items: center; margin: 4px 0; }
#run .io input { width: 100%; font-family: var(--font-mono); font-size: 12px; padding: 3px 5px; }
#run .btns { display: flex; flex-wrap: wrap; gap: 5px; margin: 6px 0; }
#run .btns button { font-size: 12px; padding: 3px 8px; }
#run .got { font-family: var(--font-mono); font-size: 12px; color: var(--fg); overflow-wrap: anywhere; }
#run .ok { color: var(--ok); } #run .bad { color: var(--err); }
#run pre.log { max-height: 140px; overflow: auto; font-size: 11px; margin: 6px 0 0; white-space: pre-wrap; }
.tok { fill: none; stroke: var(--gold); stroke-width: 1.4; }
.tokv { font-family: var(--font-mono); fill: var(--gold); paint-order: stroke; stroke: #0e130f; stroke-width: .8; pointer-events: none; }
#cfg .dirs span.edit { cursor: pointer; }
@media (max-width: 900px) {
  .composer { grid-template-columns: 1fr; }
  .composer .side { position: static; max-height: none; overflow: visible; }
  .board-wrap { height: 62vh; }
}
"""

CORE_COLOURS = {"adder": "#c17f45", "mul": "#d9b46a", "comparator": "#7fa6d0", "const": "#7fae7a", "io": "#e9ede6", "ram": "#627262", "cross": "#d0786a",
                "branch": "#b48ad0", "nano": "#b48ad0", "latch": "#a7b58c", "accumulator": "#8cb5ad", "sequencer": "#b5a58c", "priority": "#9aab98", "corner": "#d0a06a", "merge": "#8fb0c8"}


def page_composer():
    ex_opts = "".join(f'<option value="{e}">{e}</option>' for e in examples())
    b_opts = "".join(f'<option value="{b}">{b}</option>' for b in flv.BUILDERS)
    legend = "".join(f'<span style="--sw:{c}">{k}</span>' for k, c in CORE_COLOURS.items() if k not in ("priority",))
    meta = flv.core_meta()
    body = f"""<h1>Composer</h1>
<p class="lede">Build a design on the board, or import one and arrange it. <b>Place</b> cells from the palette and set each cell's fields; the panel shows the
80-bit SUPER_LATCH the cell encodes to, as the explainer does. <b>Join</b> a cell's output to another cell's input; the layout engine
(<code>tools/flex_layout_v1.py</code>) lays the route, and <b>Balance</b> adds timing detours where two operands would arrive together. <b>Insert block</b>
reuses a saved design as one unit; its io-named cells are its ports. Drag cells or blocks to move them; a move the engine cannot route is refused and
changes nothing. <b>Save ICM</b> writes ICM v3; <b>Save to library</b> keeps the design so another design can use it as a block.</p>

<div class="toolbar">
  <button id="newBtn">New design</button>
  <label class="filepick">Import ICM <input type="file" id="file" accept=".json,.icm"></label>
  <select id="example"><option value="">open an example…</option>{ex_opts}</select>
  <select id="builder"><option value="">built by Python…</option>{b_opts}</select>
  <input type="text" id="path" class="grow" placeholder="or a path on this machine">
  <button id="loadPath">Open path</button>
</div>
<div class="modes" id="modes">
  <button data-mode="select" class="on" title="drag cells and blocks; tap to inspect">Select / move</button>
  <button data-mode="place" title="tap a free square to place the core chosen below">Place</button>
  <button data-mode="join" title="tap the source cell, then the destination">Join</button>
  <button data-mode="delete" title="tap a cell, a route or a block to remove it">Delete</button>
  <button data-mode="block" title="tap a square to put the chosen library model there (its top-left)">Insert block</button>
  <select id="libSel" title="the standard library, your library, then the examples"></select>
  <label class="filepick" title="place the model's cells as ordinary cells instead of one block"><input type="checkbox" id="asComp"> as components</label>
  <label class="filepick" title="use any ICM file as a block">or a file <input type="file" id="blockFile" accept=".json,.icm"></label>
</div>
<div class="palette" id="palette"></div>
<div id="status" role="status"></div>

<div class="composer">
  <div class="board-wrap" id="wrap">
    <svg id="board" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg"><g id="view"><g id="grid"></g><g id="routes"></g><g id="cells"></g><g id="blocks"></g><g id="sim"></g><g id="over"></g></g></svg>
    <div class="board-tools">
      <button id="fit" title="fit the layout to the view">Fit</button>
      <button id="zin" title="zoom in">+</button>
      <button id="zout" title="zoom out">−</button>
      <button id="undo" title="undo the last edit">Undo</button>
      <button id="balance" title="add timing detours until no operand pair ties">Balance</button>
      <button id="heat" title="tint cells by hop depth">Hop heat</button>
      <button id="inside" title="blocks: open when zoomed in (auto), always tiles, or always open">Blocks: auto</button>
      <button id="save" class="primary" title="download the design: ICM-VIX when it holds blocks (they are kept), else ICM v3">Save ICM</button>
      <button id="saveFlat" title="download one flat ICM v3 file (blocks become plain cells)">Save flat v3</button>
      <button id="saveLib" title="save into the library, for use as a block">Save to library</button>
    </div>
  </div>
  <div class="side">
    <div class="panel"><h3>Selected</h3><div id="cfg" class="stat">tap a cell or a block</div></div>
    <div class="panel"><h3>Run / step</h3><div id="run" class="stat"></div></div>
    <div class="panel"><h3>Layout</h3><div id="summary" class="stat">nothing loaded</div></div>
    <div class="panel"><h3>Find</h3><input type="text" id="find" placeholder="cell name" style="width:100%"></div>
    <div class="panel"><h3>Problems</h3><ul id="problems"><li>none</li></ul></div>
    <div class="panel"><h3>Legend</h3><div class="legend">{legend}<span style="--sw:transparent;outline:1px dashed var(--fg-dim)">pinned</span></div>
      <div class="stat" style="margin-top:6px">line: a join (dashed: the second word, carry / high word); ✕: crossing tile; framed tile: a block, gold dots are its ports</div></div>
  </div>
</div>
<pre>python3 tools/flex_layout_view_v1.py FILE.icm.json          # the same import, as a summary
python3 tools/flex_layout_view_v1.py --builder fp_add/fp16 --json out.json</pre>
<script>{_JS.replace("__COLOURS__", json.dumps(CORE_COLOURS)).replace("__META__", json.dumps(meta))}</script>"""
    return ui.page("Composer", body, active="composer", extra_css=COMPOSER_CSS, narrow=False)


_JS = r"""
(() => {
const COL = __COLOURS__;
const META = __META__;
const S = 10;                       // one square = 10 svg units
const NS = 'http://www.w3.org/2000/svg';
const $ = id => document.getElementById(id);
const svg = $('board'), view = $('view'), wrap = $('wrap');
function W() { return Math.max(1, wrap.getBoundingClientRect().width); }
function H() { return Math.max(1, wrap.getBoundingClientRect().height); }
let L = null, LIB = [], cellBy = {}, blockBy = {}, occ = {}, sel = null, selBlock = null, heat = false, blockMode = 'auto', openNow = '';
let mode = 'select', placeCore = 'adder', joinSrc = null, joinPort = null, blockUpload = null, SIM = null, simInputs = {}, simExpect = {};
let vb = {x: 0, y: 0, w: 400, h: 300};

function status(msg, kind) { const s = $('status'); s.textContent = msg || ''; s.className = kind || ''; }
function el(tag, attrs, parent) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function esc(s) { return String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c])); }
let lodTimer = null, drawnScale = 0;
function setVB() {
  svg.setAttribute('viewBox', `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
  if (L && blockMode === 'auto' && L.blocks.length) { clearTimeout(lodTimer); lodTimer = setTimeout(() => { if (openKey() !== openNow || (!drawnScale || vb.w / drawnScale > 1.6 || drawnScale / vb.w > 1.6)) draw(true); }, 120); }
}
async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  return r.json();
}
async function edit(action, body, okMsg) {
  const res = await api('/composer/api/' + action, body || {});
  if (!res.ok) { status('refused: ' + res.error, 'err'); return null; }
  take(res, true);
  if (okMsg) status(typeof okMsg === 'function' ? okMsg(res) : okMsg, 'ok');
  return res;
}
function take(res, keepView) {
  if (res.library) { LIB = res.library; libOptions(); }
  if ('sim' in res) SIM = res.sim;
  if (res.layout !== undefined) { L = res.layout; draw(keepView); }
  if (sel && !(L && cellBy[sel])) sel = null;
  if (selBlock && !(L && blockBy[selBlock])) selBlock = null;
  showSelected();
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
function isOpen(b) {                 // a block shows its cells when zoomed in far enough (auto), or always / never
  if (!b) return false;
  if (blockMode !== 'auto') return blockMode === 'open';
  const px = W() / vb.w * S;
  return px >= 14 && (b.c1 - b.c0 + 1) * px >= 240;
}
function openKey() { return L ? L.blocks.filter(isOpen).map(b => b.name).join('|') : ''; }
function hidden(c) { return c.block && !isOpen(blockBy[c.block]); }
function statusBadge(st) {
  if (!st) return ['', ''];
  if (st.function === 'standard') return ['st-ok', 'standard ✓'];
  if (st.standard === null || st.standard === undefined) return ['st-mod', st.function === 'intact' ? 'model not found · function ✓' : 'model not found'];
  return {intact: ['st-mod', 'modified · function ✓'], broken: ['st-bad', 'modified · function ✗'], unchecked: ['st-mod', 'modified · unchecked'], 'no-vectors': ['st-mod', 'modified · no reference']}[st.function] || ['st-mod', 'modified'];
}
const BADGE_FILL = {'st-ok': 'var(--ok)', 'st-mod': 'var(--warn)', 'st-bad': 'var(--err)'};

// ---- drawing -------------------------------------------------------------------------------------------------------------------------
function draw(keepView) {
  ['grid', 'routes', 'cells', 'blocks', 'over'].forEach(id => { $(id).innerHTML = ''; });
  if (!L) { summary(); return; }
  cellBy = {}; blockBy = {}; occ = {};
  for (const c of L.cells) cellBy[c.name] = c;
  for (const b of L.blocks) blockBy[b.name] = b;
  const g = $('grid');
  el('rect', {x: 0, y: 0, width: L.cols * S, height: L.rows * S, fill: 'var(--bg)', stroke: 'var(--line)'}, g);
  let d = '';
  for (let r = 1; r < L.rows; r++) d += `M0 ${r * S}H${L.cols * S}`;
  for (let c = 1; c < L.cols; c++) d += `M${c * S} 0V${L.rows * S}`;
  el('path', {d, stroke: 'var(--line-soft)', 'stroke-width': .5, fill: 'none'}, g);
  const rg = $('routes');
  for (const rt of L.routes) {
    for (const p of rt.points.slice(1, -1)) occ[p[0] + ',' + p[1]] = 'route:' + rt.from + '|' + rt.to;
    const a = cellBy[rt.from], b = cellBy[rt.to];
    if (a && b && a.block && a.block === b.block && hidden(a)) continue;
    const pts = rt.points.map(p => `${p[1] * S + S / 2},${p[0] * S + S / 2}`).join(' ');
    const line = el('polyline', {points: pts, class: 'route' + (rt.second ? ' second' : ''), stroke: a ? colour(a) : COL.ram}, rg);
    line.dataset.from = rt.from; line.dataset.to = rt.to;
    const tag = (rt.out.join('+') !== 'out' ? rt.out.join('+') + ' ' : '') + '→' + (rt.in.join('+') !== 'in' ? ' ' + rt.in.join('+') : '');
    line.addEventListener('mouseenter', () => { line.classList.add('hl'); status(`join ${rt.from} ${tag} ${rt.to}: ${rt.relays} relays` + (rt.extra ? `, ${rt.extra} of them a timing detour` : '') + (rt.crossings.length ? `, ${rt.crossings.length} crossing tile(s)` : '')); });
    line.addEventListener('mouseleave', () => line.classList.remove('hl'));
  }
  for (const ln of L.links) {
    const a = cellBy[ln.a], b = cellBy[ln.b];
    if (a && b && !(hidden(a) && hidden(b))) el('line', {x1: a.c * S + S / 2, y1: a.r * S + S / 2, x2: b.c * S + S / 2, y2: b.r * S + S / 2, class: 'route' + (ln.second ? ' second' : ''), stroke: colour(a)}, rg);
  }
  const cg = $('cells');
  for (const x of L.crossings) {
    occ[x.r + ',' + x.c] = 'cross:' + x.name;
    const cx = x.c * S + S / 2, cy = x.r * S + S / 2, k = S * .32;
    el('path', {d: `M${cx - k} ${cy - k}L${cx + k} ${cy + k}M${cx + k} ${cy - k}L${cx - k} ${cy + k}`, stroke: COL.cross, 'stroke-width': 2}, cg);
  }
  const maxHop = L.summary.max_hop;
  for (const c of L.cells) {
    if (c.core === 'cross') continue;
    occ[c.r + ',' + c.c] = c.name;
    if (hidden(c)) continue;
    const gr = el('g', {class: 'cell' + (c.movable || c.block ? ' mov' : '') + (c.pinned ? ' pinned' : '') + (sel === c.name ? ' sel' : '') + (joinSrc === c.name ? ' src' : ''), transform: `translate(${c.c * S},${c.r * S})`}, cg);
    gr.dataset.name = c.name;
    const fill = heat ? heatColour(c.hop, maxHop) : colour(c);
    el('rect', {x: .8, y: .8, width: S - 1.6, height: S - 1.6, rx: 1.6, fill, stroke: c.pinned ? 'var(--fg-dim)' : '#0008', 'stroke-width': .8}, gr);
    const short = c.name.split('.').pop();
    const t = el('text', {x: S / 2, y: S / 2 + 1.2, 'text-anchor': 'middle', 'font-size': 3.2, class: 'lbl lblsmall'}, gr);
    t.textContent = short.length > 6 ? short.slice(0, 6) : short;
  }
  const bg = $('blocks'), ppu = W() / vb.w;      // screen pixels per board unit: tile text and port dots are sized to stay readable when zoomed out
  for (const b of L.blocks) {
    const open = isOpen(b), [cls, txt] = statusBadge(b.status);
    const gr = el('g', {class: 'blk' + (open ? ' open' : '') + (selBlock === b.name ? ' sel' : ''), transform: `translate(${b.c0 * S},${b.r0 * S})`}, bg);
    gr.dataset.block = b.name;
    const w = (b.c1 - b.c0 + 1) * S, h = (b.r1 - b.r0 + 1) * S;
    el('rect', {class: 'body', x: .6, y: .6, width: w - 1.2, height: h - 1.2, rx: 2}, gr);
    if (open) {                         // zoomed in: an outline and a header bar (drag the bar to move the whole block; the cells inside are edited one by one)
      const bar = el('rect', {class: 'bar', x: .6, y: -6, width: Math.min(w - 1.2, 120), height: 5.4, rx: 1}, gr);
      bar.dataset.bar = b.name;
      const t = el('text', {x: 2.4, y: -2, 'font-size': 3}, gr);
      t.textContent = `${b.name} · ${txt}`;
      t.style.fill = BADGE_FILL[cls] || 'var(--fg)';
    } else {
      const fs = Math.max(2.4, Math.min(Math.max(5, 13 / ppu), h * .28, w / Math.max(4, b.name.length) * 1.4));
      const t = el('text', {x: w / 2, y: h / 2 - fs * .2, 'text-anchor': 'middle', 'font-size': fs}, gr);
      t.textContent = b.name;
      const t2 = el('text', {x: w / 2, y: h / 2 + fs * .8, 'text-anchor': 'middle', 'font-size': fs * .6}, gr);
      t2.textContent = `${b.file} · ${b.cells} cells`;
      t2.style.fill = 'var(--fg-dim)';
      const t3 = el('text', {class: 'badge', x: w / 2, y: h / 2 + fs * 1.7, 'text-anchor': 'middle', 'font-size': fs * .6}, gr);
      t3.textContent = txt;
      t3.style.fill = BADGE_FILL[cls] || 'var(--fg-dim)';
    }
    for (const p of b.ports) {
      const pr = open ? 1.6 : Math.min(S * 1.2, Math.max(2.6, 4 / ppu));
      const pc = el('circle', {class: 'port', cx: (p.c - b.c0) * S + S / 2, cy: (p.r - b.r0) * S + S / 2, r: pr}, gr);
      pc.dataset.name = p.cell;
      const pt = el('text', {x: (p.c - b.c0) * S + S / 2, y: (p.r - b.r0) * S + S / 2 - (open ? 5.6 : pr + 1), 'text-anchor': 'middle', 'font-size': open ? 3 : Math.min(S * 1.4, Math.max(3, 10 / ppu))}, gr);
      pt.textContent = p.io;
    }
  }
  openNow = openKey(); drawnScale = vb.w;
  drawSim();
  updateLabels(); summary(); problems(); runPanel();
  if (!keepView) fit();
}
function fmtv(v) { return v > 4095 ? '0x' + v.toString(16).toUpperCase() : String(v); }
function drawSim() {
  const sg = $('sim'); sg.innerHTML = '';
  if (!SIM || !L) return;
  for (const [name, st] of Object.entries(SIM.state)) {
    if (!st.valid) continue;
    const c = cellBy[name];
    if (c && hidden(c)) continue;
    const cx = st.c * S + S / 2, cy = st.r * S + S / 2;
    el('circle', {class: 'tok', cx, cy, r: S * .46}, sg);
    const t = el('text', {class: 'tokv', x: cx, y: cy - S * .55, 'text-anchor': 'middle', 'font-size': 3.4}, sg);
    t.textContent = fmtv(st.v);
  }
}
function parseList(s) { return String(s || '').split(/[\s,;]+/).filter(x => x).map(x => Number(x)); }
function runPanel() {
  const box = $('run');
  if (!L) { box.textContent = 'load or build a design first'; return; }
  if (!SIM) {
    box.innerHTML = `Inject values into the design's inputs and step it in FlexGrid (the flex VM), watching each value move.<div class="btns"><button id="simStart" class="primary">Start</button></div>`;
    $('simStart').onclick = () => sim({op: 'start'}, 'started: type values for each input, then Run all or Inject + Step');
    return;
  }
  let h = `tick <b>${SIM.ticks}</b> · items in ${SIM.items} · width ${SIM.width}` + (SIM.pending ? ` · ${SIM.pending} pending` : '');
  h += `<div style="margin-top:6px">inputs <small>(values, comma separated; 0x for hex)</small></div>`;
  for (const i of SIM.inputs) h += `<div class="io"><label title="${esc(i.cell)}">${esc(i.io || i.cell)}</label><input type="text" data-in="${esc(i.cell)}" value="${esc(simInputs[i.cell] || '')}" placeholder="e.g. 1, 5, 100"></div>`;
  h += `<div class="btns"><button id="simAll" class="primary" title="inject each item in turn and run until the design settles">Run all</button><button id="simInj" title="inject the next item only">Inject next</button>` +
       `<button id="simStep" title="one tick">Step</button><button id="simStep10">Step ×10</button><button id="simRun" title="tick until nothing changes">Run to settle</button><button id="simStop">Stop</button></div>`;
  h += `<div>outputs <small>(type expected values to check)</small></div>`;
  for (const o of SIM.outputs) {
    const exp = parseList(simExpect[o.cell]);
    const got = o.values.map((v, i) => i < exp.length ? `<span class="${exp[i] === v ? 'ok' : 'bad'}">${fmtv(v)}</span>` : fmtv(v)).join(', ');
    const verdict = exp.length ? (o.values.length >= exp.length && exp.every((v, i) => o.values[i] === v) ? ' <span class="ok">✓ all match</span>' : (o.values.length >= exp.length ? ' <span class="bad">✗ mismatch</span>' : '')) : '';
    h += `<div class="io"><label title="${esc(o.cell)}">${esc(o.io || o.cell)}</label><input type="text" data-exp="${esc(o.cell)}" value="${esc(simExpect[o.cell] || '')}" placeholder="expected"></div><div class="got">→ ${got || '—'}${verdict}</div>`;
  }
  h += `<pre class="log">${esc(SIM.log.slice(-12).join('\n'))}</pre>`;
  box.innerHTML = h;
  box.querySelectorAll('[data-in]').forEach(i => { i.oninput = () => { simInputs[i.dataset.in] = i.value; }; });
  box.querySelectorAll('[data-exp]').forEach(i => { i.onchange = () => { simExpect[i.dataset.exp] = i.value; runPanel(); }; });
  const items = () => Object.fromEntries(SIM.inputs.map(i => [i.cell, simInputs[i.cell] || '']));
  $('simAll').onclick = () => sim({op: 'items', items: items()}, r => `ran ${r.sim.items} item(s) in ${r.sim.ticks} ticks`);
  $('simInj').onclick = () => {
    const vals = {}, n = SIM.items;
    for (const i of SIM.inputs) { const l = parseList(simInputs[i.cell]); if (n < l.length) vals[i.cell] = l[n]; }
    if (!Object.keys(vals).length) { status('no more input values: add some, or Start again', 'err'); return; }
    sim({op: 'inject', values: vals}, `item ${n + 1} injected: Step to watch it move`);
  };
  $('simStep').onclick = () => sim({op: 'step', n: 1});
  $('simStep10').onclick = () => sim({op: 'step', n: 10});
  $('simRun').onclick = () => sim({op: 'run'}, r => `settled at tick ${r.sim.ticks}`);
  $('simStop').onclick = () => sim({op: 'stop'}, 'step-through stopped');
}
async function sim(body, okMsg) {
  const res = await api('/composer/api/sim', body);
  if (!res.ok) { status('step-through: ' + res.error, 'err'); return; }
  SIM = res.sim; drawSim(); runPanel();
  if (okMsg) status(typeof okMsg === 'function' ? okMsg(res) : okMsg, 'ok');
}
function updateLabels() {
  const px = W() / vb.w * S;
  document.querySelectorAll('.lblsmall').forEach(t => { t.style.display = px > 26 ? '' : 'none'; });
}
function summary() {
  if (!L) { $('summary').textContent = 'nothing loaded: start a new design or import a file'; return; }
  const s = L.summary, bc = Object.entries(s.by_core).map(([k, v]) => `${k} ${v}`).join(', ');
  const mov = L.cells.filter(c => c.movable).length;
  $('summary').innerHTML = `<b>${esc(L.name)}</b> · board ${L.rows} × ${L.cols}<br>${s.cells} cells (${esc(bc) || 'empty'})<br>${s.routes} joins, ${s.relays} relays, ${L.crossings.length} crossings, ${L.blocks.length} blocks<br>` +
    `deepest hop <b>${s.max_hop}</b>; ${mov} movable, ${s.pinned} pinned` + (s.undo ? `; ${s.undo} undo step(s)` : '') +
    (s.timing_error ? `<br><span style="color:var(--err)">no timing: ${esc(s.timing_error)}</span>` : '') +
    (L.warnings.length ? `<br><span style="color:var(--warn)">${L.warnings.length} warning(s): ${esc(L.warnings.slice(0, 3).join('; '))}</span>` : '');
}
function problems() {
  const ul = $('problems'); ul.innerHTML = '';
  for (const m of (L && L.merges) || []) {
    const li = document.createElement('li');
    li.textContent = `note: ${m.cell} (nano) gets ${m.a} and ${m.b} on the same tick: they are OR-merged into one word`;
    li.style.color = 'var(--fg-dim)'; li.onclick = () => focusCell(m.cell); ul.appendChild(li);
  }
  if (!L || !L.problems.length) { const li = document.createElement('li'); li.style.cssText = 'cursor:default;color:var(--ok)'; li.textContent = 'none: every operand pair is ordered'; ul.appendChild(li); return; }
  for (const p of L.problems) {
    const li = document.createElement('li');
    li.textContent = `${p.cell}: ${p.kind === 'tie' ? 'operands arrive together' : 'minuend not first'} (${p.early} / ${p.late}); press Balance`;
    li.style.color = p.kind === 'tie' ? 'var(--warn)' : 'var(--err)';
    li.onclick = () => focusCell(p.cell);
    ul.appendChild(li);
  }
}

// ---- the selected cell: an explainer-style configuration panel ------------------------------------------------------------------------
function dirsOf(v) { return Array.isArray(v) ? v.map(d => String(d).toLowerCase()) : (typeof v === 'number' ? ['n', 's', 'e', 'w'].filter((d, i) => (v >> i) & 1) : []); }
function fieldVal(cfg, f) {
  const v = cfg[f.name];
  if (f.kind === 'dirs') { if (f.name === 'upstream_dir') return typeof v === 'number' ? (1 << v) : 0; return dirsOf(v).reduce((m, d) => m | (1 << 'nsew'.indexOf(d)), 0); }
  return Number(v || 0);
}
function bitbar(c) {
  const m = META.cores[c.core]; if (!m) return '';
  const seg = (w, cls, title) => `<span class="${cls}" style="flex:${w}" title="${esc(title)}"></span>`;
  let out = `<div class="bitbar" title="core_select [4:0] · core_config [46:5] · add-on [66:47]">` + seg(5, 'sel set', `core_select = ${m.sel} (${c.core})`);
  let at = 0;
  for (const f of [...m.fields].sort((a, b) => a.lo - b.lo)) {
    if (f.lo > at) out += seg(f.lo - at, '', `core_config bits ${at}..${f.lo - 1}: unused`);
    const v = fieldVal(c.cfg, f);
    out += seg(f.hi - f.lo + 1, (f.kind === 'dirs' ? 'dir' : '') + (v ? ' set' : ''), `${f.name} [${f.hi}:${f.lo}] = ${v}`);
    at = f.hi + 1;
  }
  if (at < 42) out += seg(42 - at, '', `core_config bits ${at}..41: unused`);
  out += seg(20, 'addon' + (Object.values(c.addon || {}).some(v => v) ? ' set' : ''), 'add-on config [66:47]');
  return out + '</div>';
}
function showSelected() {
  const box = $('cfg');
  if (selBlock && blockBy[selBlock]) {
    const b = blockBy[selBlock], st = b.status || {}, [cls, txt] = statusBadge(st);
    const src = {std: 'standard library', library: 'your library', example: 'examples', file: 'a file'}[b.source] || 'unknown';
    box.innerHTML = `<b>block ${esc(b.name)}</b><br>model ${esc(b.file)} (${src}) · ${b.cells} cells<br>ports: ` +
      (b.ports.map(p => `<b>${esc(p.io)}</b>`).join(', ') || 'none') +
      `<div class="${cls}" style="margin-top:6px"><b>${txt}</b></div><div>${esc(st.detail || '')}</div>` +
      (st.standard === false ? `<div style="margin-top:4px;color:var(--fg-faint)">non-standard: its cells or joins differ from ${esc(b.file)}</div>` : '') +
      `<div class="actions"><button id="bCheck" title="run the block on its own against its model's reference vectors">Check function</button>` +
      `<button id="bUnpack" title="turn the block's cells into ordinary cells">Unpack</button><button id="bDel">Delete block</button></div>` +
      `<div style="margin-top:6px">Zoom in to open the block and edit its cells; drag its header bar (or the tile) to move it. In Join mode, tap a port (gold dot).</div>`;
    $('bCheck').onclick = () => { status(`checking ${b.name} against its reference vectors (a large block takes a while)…`); edit('check_block', {name: b.name}, r => `${b.name}: ${statusBadge(r)[1]}. ${r.detail || ''}`); };
    $('bUnpack').onclick = () => edit('unpack_block', {name: b.name}, `unpacked ${b.name}: its cells are ordinary cells now`);
    $('bDel').onclick = () => edit('delete_block', {name: b.name}, `deleted ${b.name}`);
    return;
  }
  const c = sel && cellBy[sel];
  if (!c) { box.textContent = L ? 'tap a cell or a block' : 'nothing loaded'; return; }
  const m = META.cores[c.core] || {fields: [], ports: [], roles: []};
  const [fr, fc] = fileSquare(c.r, c.c);
  const ro = c.pinned;
  let h = `<b>${esc(c.name)}</b> · ${c.core}${c.block ? ' · in block ' + esc(c.block) : ''}<br>file square (${fr}, ${fc}) · hop ${c.hop ?? '?'}` +
    (c.pinned ? '<br><span style="color:var(--warn)">pinned: wiring kept exactly as the file had it</span>' : '') +
    (c.block ? `<br><span style="color:var(--warn)">inside block ${esc(c.block)}: an edit here makes the block non-standard (its status shows whether its function still holds)</span>` : '');
  h += `<div class="row"><label>io name <small>(a port when used as a block)</small></label><input type="text" data-k="io" value="${esc(c.io || '')}" ${ro ? 'disabled' : ''}></div>`;
  if (c.core === 'ram') h += `<div class="row"><label>preload <small>(a constant)</small></label><input type="text" data-k="preload" value="${c.preload ?? ''}" placeholder="none" ${ro ? 'disabled' : ''}></div>`;
  for (const f of m.fields) {
    const rng = f.lo === f.hi ? `[${f.lo}]` : `[${f.hi}:${f.lo}]`;
    if (f.kind === 'userdirs') {
      const on = dirsOf(c.cfg[f.name]);
      h += `<div class="row"><label>${f.name} <small>${rng} relay, not consume</small></label><div class="dirs" data-ud="${f.name}" data-mask="${fieldVal(c.cfg, {name: f.name, kind: 'dirs'})}">${['n', 's', 'e', 'w'].map((d, i) => `<span class="edit ${on.includes(d) ? 'on' : ''}" data-bit="${i}">${d.toUpperCase()}</span>`).join('')}</div></div>`;
    } else if (f.kind === 'choice') {
      const v = Number(c.cfg[f.name] ?? 0);
      const known = f.choices.some(o => o.value === v);
      h += `<div class="row"><label>${f.name} <small>${rng}</small></label><select data-f="${f.name}" ${ro ? 'disabled' : ''}>${f.choices.map(o => `<option value="${o.value}" ${o.value === v ? 'selected' : ''}>${o.label} (0x${o.value.toString(16).toUpperCase()})</option>`).join('')}${known ? '' : `<option value="${v}" selected>custom 0x${v.toString(16).toUpperCase()}</option>`}</select></div>`;
    } else if (f.kind === 'dirs') {
      const on = f.name === 'upstream_dir' ? (typeof c.cfg[f.name] === 'number' ? ['nsew'[c.cfg[f.name]]] : []) : dirsOf(c.cfg[f.name]);
      h += `<div class="row"><label>${f.name} <small>${rng} from joins</small></label><div class="dirs">${['n', 's', 'e', 'w'].map(d => `<span class="${on.includes(d) ? 'on' : ''}">${d.toUpperCase()}</span>`).join('')}</div></div>`;
    } else {
      const v = Number(c.cfg[f.name] ?? 0), w = f.hi - f.lo + 1;
      h += `<div class="row"><label>${f.name} <small>${rng} ${w}-bit</small></label><input type="text" data-f="${f.name}" value="${f.kind === 'toggle' || v < 10 ? v : '0x' + v.toString(16).toUpperCase()}" ${ro ? 'disabled' : ''}></div>`;
    }
  }
  h += `<details><summary>add-on fields (mask / shift / invert)</summary>`;
  for (const f of META.addon) {
    const v = (c.addon || {})[f.name] ?? 0;
    h += `<div class="row"><label>${f.name} <small>${f.lo === f.hi ? '[' + f.lo + ']' : '[' + f.hi + ':' + f.lo + ']'}</small></label><input type="text" data-a="${f.name}" value="${v}" ${ro ? 'disabled' : ''}></div>`;
  }
  h += `</details>`;
  if (c.core === 'adder' && c.cfg.subtract_mode && c.sources.length === 2 && !ro) {
    h += `<div class="row"><label>minuend <small>(arrives first)</small></label><select id="minuend"><option value="">by arrival</option>${c.sources.map(s => `<option ${c.minuend === s ? 'selected' : ''}>${esc(s)}</option>`).join('')}</select></div>`;
  }
  h += bitbar(c) + `<div class="latch">SUPER_LATCH 0x${c.latch ? c.latch.toUpperCase() : '?'}</div>` + (c.latch_error ? `<div style="color:var(--err)">${esc(c.latch_error)}</div>` : '');
  const ins = L.routes.filter(r => r.to === c.name), outs = L.routes.filter(r => r.from === c.name);
  if (ins.length || outs.length) {
    h += `<ul class="joins">` + ins.map(r => `<li>from ${esc(r.from)}${r.out.join('+') !== 'out' ? ' (' + r.out.join('+') + ')' : ''} as ${r.in.join('+')}${ro ? '' : ` <button data-un="${esc(r.from)}|${esc(r.to)}">unjoin</button>`}</li>`).join('') +
      outs.map(r => `<li>${r.out.join('+')} to ${esc(r.to)}${r.in.join('+') !== 'in' ? ' (' + r.in.join('+') + ')' : ''}${ro ? '' : ` <button data-un="${esc(r.from)}|${esc(r.to)}">unjoin</button>`}</li>`).join('') + `</ul>`;
  }
  h += `<div class="actions">` + (ro ? '' : `<button id="apply" class="primary">Apply</button>`) + `<button id="joinFrom" title="join from this cell">Join from here</button>` + (ro ? '' : `<button id="delCell">Delete</button>`) + `</div>`;
  box.innerHTML = h;
  if (!ro) box.querySelectorAll('[data-ud] span.edit').forEach(sp => { sp.onclick = () => {
    const d = sp.parentElement; const m = Number(d.dataset.mask) ^ (1 << Number(sp.dataset.bit)); d.dataset.mask = m; sp.classList.toggle('on'); }; });
  box.querySelectorAll('[data-un]').forEach(b => { b.onclick = () => { const [a, z] = b.dataset.un.split('|'); edit('unjoin', {a, b: z}, `unjoined ${a} → ${z}`); }; });
  $('joinFrom').onclick = ev => { setMode('join'); pickSource(ev, c.name); };
  if (ro) return;
  $('apply').onclick = () => {
    const cfg = {}, addon = {};
    box.querySelectorAll('[data-f]').forEach(i => { cfg[i.dataset.f] = i.value.trim(); });
    box.querySelectorAll('[data-ud]').forEach(d => { cfg[d.dataset.ud] = d.dataset.mask; });
    box.querySelectorAll('[data-a]').forEach(i => { addon[i.dataset.a] = i.value.trim(); });
    const body = {name: c.name, cfg, addon, io: box.querySelector('[data-k=io]').value};
    const pre = box.querySelector('[data-k=preload]'); if (pre) body.preload = pre.value.trim() === '' ? 'none' : pre.value.trim();
    edit('config', body, r => `${c.name} configured: SUPER_LATCH 0x${(r.latch || '').toUpperCase()}`);
  };
  if ($('minuend')) $('minuend').onchange = ev => edit('minuend', {name: c.name, source: ev.target.value}, r => `minuend set; ${r.detours} detour(s)`);
  $('delCell').onclick = () => edit('delete', {name: c.name}, `deleted ${c.name}`);
}
function focusCell(name) {
  const c = cellBy[name]; if (!c) { status(`no cell ${name}`, 'err'); return; }
  sel = name; selBlock = null; vb.w = 24 * S; vb.h = vb.w * H() / W();
  vb.x = c.c * S - vb.w / 2; vb.y = c.r * S - vb.h / 2; setVB(); draw(true); showSelected();
}
function fit() {
  if (!L) return;
  let r0 = 1e9, r1 = -1, c0 = 1e9, c1 = -1;
  for (const c of L.cells) { r0 = Math.min(r0, c.r); r1 = Math.max(r1, c.r); c0 = Math.min(c0, c.c); c1 = Math.max(c1, c.c); }
  for (const rt of L.routes) for (const p of rt.points) { r0 = Math.min(r0, p[0]); r1 = Math.max(r1, p[0]); c0 = Math.min(c0, p[1]); c1 = Math.max(c1, p[1]); }
  if (r1 < 0) { r0 = 0; c0 = 0; r1 = L.rows - 1; c1 = L.cols - 1; }
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
function squareAt(ev) { const p = toSvg(ev); return [Math.floor(p.y / S), Math.floor(p.x / S)]; }

// ---- modes ---------------------------------------------------------------------------------------------------------------------------
const HINT = {select: 'drag a cell or a block to move it; tap to inspect', join: 'tap the cell (or block port) to join FROM', delete: 'tap a cell, a join line or a block to remove it'};
function setMode(m) {
  mode = m; joinSrc = null; joinPort = null; closeChooser(); clearGhost();
  document.querySelectorAll('#modes button[data-mode]').forEach(b => b.classList.toggle('on', b.dataset.mode === m));
  svg.setAttribute('class', {place: 'placing', join: 'joining', delete: 'deleting', block: 'placing'}[m] || '');
  $('palette').style.display = m === 'place' ? '' : 'none';
  status(m === 'place' ? `tap a free square to place a ${placeCore}` : m === 'block' ? `tap the square for the block's top-left (${blockUpload ? blockUpload.file : $('libSel').value ? $('libSel').selectedOptions[0].textContent : 'choose a model first'})` : HINT[m]);
  if (L) draw(true);
}
document.querySelectorAll('#modes button[data-mode]').forEach(b => { b.onclick = () => setMode(b.dataset.mode); });
function palette() {
  const p = $('palette'); p.innerHTML = '';
  for (const core of META.palette) {
    const b = document.createElement('button'); b.textContent = core; b.style.setProperty('--sw', COL[core] || COL.ram);
    b.className = core === placeCore ? 'on' : ''; b.title = `outputs: ${META.cores[core].ports.join(', ') || 'none'}; inputs: ${META.cores[core].roles.join(', ') || 'none'}`;
    b.onclick = () => { placeCore = core; palette(); status(`tap a free square to place a ${core}`); };
    p.appendChild(b);
  }
  p.style.display = mode === 'place' ? '' : 'none';
}
function libOptions() {
  const s = $('libSel'), cur = s.value;
  const group = (src, label) => { const ms = LIB.filter(m => m.source === src); return ms.length ? `<optgroup label="${label}">` + ms.map(m => `<option value="${m.source}|${esc(m.name)}" title="${esc(m.desc || '')}">${esc(m.name.replace(/(\.icm-hier|\.icm)?\.json$/, ''))}${m.tested ? '' : ' (no reference)'}</option>`).join('') + '</optgroup>' : ''; };
  s.innerHTML = '<option value="">library model…</option>' + group('std', 'Standard library') + group('library', 'Your library') + group('example', 'Examples');
  if ([...s.options].some(o => o.value === cur)) s.value = cur;
}
$('libSel').onchange = () => { blockUpload = null; if ($('libSel').value) setMode('block'); };
$('blockFile').onchange = async ev => { const f = ev.target.files[0]; if (f) { blockUpload = {file: f.name, text: await f.text()}; setMode('block'); } ev.target.value = ''; };

// the small chooser used when a cell has more than one output port or input role
let chooserEl = null;
function closeChooser() { if (chooserEl) { chooserEl.remove(); chooserEl = null; } }
function choose(ev, title, options) {
  closeChooser();
  if (options.length <= 1) return Promise.resolve(options[0]);
  return new Promise(resolve => {
    chooserEl = document.createElement('div'); chooserEl.className = 'chooser';
    const rect = wrap.getBoundingClientRect();
    chooserEl.style.left = Math.min(rect.width - 150, Math.max(4, (ev.clientX || rect.left + 20) - rect.left + 8)) + 'px';
    chooserEl.style.top = Math.max(40, Math.min(rect.height - 34 * (options.length + 2), (ev.clientY || rect.top + 60) - rect.top + 8)) + 'px';
    chooserEl.innerHTML = `<b>${esc(title)}</b>`;
    for (const o of options) { const b = document.createElement('button'); b.textContent = o; b.onclick = () => { closeChooser(); resolve(o); }; chooserEl.appendChild(b); }
    const x = document.createElement('button'); x.textContent = 'cancel'; x.onclick = () => { closeChooser(); resolve(null); }; chooserEl.appendChild(x);
    wrap.appendChild(chooserEl);
  });
}
async function pickSource(ev, name) {
  const cell = cellBy[name];
  let ports = (META.cores[cell.core] || {ports: []}).ports;
  if (!cell.cfg.second_output) ports = ports.filter(p => p !== 'second');     // the carry / high word exists only when second_output is on
  if (!ports.length) { status(`a ${cell.core} has no output`, 'err'); return; }
  const p = await choose(ev, `${name}: which output`, ports); if (!p) return;
  joinSrc = name; joinPort = p; draw(true);
  status(`joining from ${name}${ports.length > 1 ? ' (' + p + ')' : ''}: tap the destination`);
}

async function tapAt(ev, target) {
  if (!L) return;
  const [r, c] = squareAt(ev);
  const cellG = target.closest && target.closest('.cell'), portEl = target.closest && target.closest('.port'), blkG = target.closest && target.closest('.blk');
  const route = target.closest && target.closest('.route');
  const name = portEl ? portEl.dataset.name : cellG ? cellG.dataset.name : null;
  if (mode === 'place') {
    if (occ[r + ',' + c] || r < 0 || c < 0 || r >= L.rows || c >= L.cols) { status('that square is taken or off the board', 'err'); return; }
    const inBlk = L.blocks.find(b => isOpen(b) && r >= b.r0 && r <= b.r1 && c >= b.c0 && c <= b.c1);
    const res = await edit('add', {core: placeCore, r, c, block: inBlk ? inBlk.name : null}, x => `placed ${x.name}` + (inBlk ? ` inside block ${inBlk.name} (the block is now non-standard)` : '') + '; set its fields on the right, then join it');
    if (res) { sel = res.name; selBlock = null; draw(true); showSelected(); }
    return;
  }
  if (mode === 'block') {
    const v = $('libSel').value;
    let body;
    if (blockUpload) body = Object.assign({r, c}, blockUpload);
    else if (v) { const i = v.indexOf('|'); body = {r, c, source: v.slice(0, i), file: v.slice(i + 1)}; }
    else { status('choose a library model (or a file) first', 'err'); return; }
    body.components = $('asComp').checked;
    const res = await edit('block', body);
    if (res && res.components) { blockUpload = null; setMode('select'); status(`placed ${res.components} cells as components (prefix ${res.prefix})`, 'ok'); return; }
    if (res) {
      blockUpload = null; selBlock = res.block; sel = null; setMode('select'); showSelected();
      status(`inserted block ${res.block}; ports: ${res.ports.join(', ') || 'none (give cells io names to make ports)'}`, 'ok');
    }
    return;
  }
  if (mode === 'join') {
    if (!name) { status(joinSrc ? 'tap a cell (or a block port) as the destination' : 'tap the cell to join FROM', 'err'); return; }
    if (!joinSrc) { pickSource(ev, name); return; }
    const cell = cellBy[name];
    const roles = (META.cores[cell.core] || {roles: []}).roles;
    if (!roles.length) { status(`a ${cell.core} has no input`, 'err'); return; }
    const role = await choose(ev, `${name}: which input`, roles); if (!role) return;
    const a = joinSrc, out = joinPort; joinSrc = null; joinPort = null;
    await edit('join', {a, b: name, out, role}, x => `joined ${a} → ${name}` + (x.relays !== undefined ? ` (${x.relays} relays)` : '') + (L.problems.length ? '; two operands arrive together: press Balance' : '') + '. Tap the next source, or Esc to stop');
    draw(true);
    return;
  }
  if (mode === 'delete') {
    if (blkG && !portEl) { const b = blkG.dataset.block; if (confirm(`delete block ${b}?`)) edit('delete_block', {name: b}, `deleted ${b}`); return; }
    if (name) { edit('delete', {name}, `deleted ${name}`); return; }
    if (route && route.dataset.from) { edit('unjoin', {a: route.dataset.from, b: route.dataset.to}, `unjoined ${route.dataset.from} → ${route.dataset.to}`); return; }
    return;
  }
  const barEl = target.closest && target.closest('.bar');
  if (barEl || (blkG && !portEl && !name && !isOpen(blockBy[blkG.dataset.block]))) { selBlock = (barEl || blkG).dataset.bar || blkG.dataset.block; sel = null; draw(true); showSelected(); return; }
  if (name) { sel = name; selBlock = null; draw(true); showSelected(); }
}

// ---- pointer handling: pan, pinch, drag a cell or a block, taps ----------------------------------------------------------------------
const pts = new Map(); let pan = null, drag = null, pinch = null, down = null;
svg.addEventListener('pointerdown', ev => {
  svg.setPointerCapture(ev.pointerId); pts.set(ev.pointerId, ev);
  if (pts.size === 2) { const [a, b] = [...pts.values()]; pinch = {d: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY)}; pan = drag = down = null; clearGhost(); return; }
  down = {x: ev.clientX, y: ev.clientY, target: ev.target};
  if (mode === 'select' && L) {
    const blkG = ev.target.closest('.blk'), cellG = ev.target.closest('.cell');
    const c = cellG && cellBy[cellG.dataset.name];
    const bar = ev.target.closest('.bar');
    const b = bar ? blockBy[bar.dataset.bar] : (blkG && !isOpen(blockBy[blkG.dataset.block])) ? blockBy[blkG.dataset.block] : (c && c.block && !isOpen(blockBy[c.block]) ? blockBy[c.block] : null);
    if (b) { const [r, cc] = squareAt(ev); drag = {block: b, r0: r, c0: cc, r, cc, moved: false}; return; }
    if (c && c.movable) { drag = {c, r: c.r, cc: c.c, moved: false}; return; }
  }
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
    const [r, c] = squareAt(ev);
    if (r !== drag.r || c !== drag.cc) {
      drag.r = r; drag.cc = c;
      if (drag.block) { drag.moved = r !== drag.r0 || c !== drag.c0; ghostBlock(drag.block, r - drag.r0, c - drag.c0); }
      else { drag.moved = r !== drag.c.r || c !== drag.c.c; ghost(drag.c, r, c); }
    }
    return;
  }
  if (pan) {
    const k = vb.w / W();
    vb.x = pan.vx - (ev.clientX - pan.x) * k; vb.y = pan.vy - (ev.clientY - pan.y) * k; setVB();
  }
});
function endPointer(ev) {
  pts.delete(ev.pointerId);
  if (pinch) { if (pts.size < 2) pinch = null; return; }
  svg.classList.remove('panning');
  const wasTap = down && Math.hypot(ev.clientX - down.x, ev.clientY - down.y) < 6 && ev.type === 'pointerup';
  const target = down && down.target; down = null; pan = null;
  if (drag) {
    const d = drag; drag = null; clearGhost();
    if (d.moved && ev.type === 'pointerup') { if (d.block) doMoveBlock(d.block, d.r - d.r0, d.cc - d.c0); else doMove(d.c, d.r, d.cc); return; }
  }
  if (wasTap) tapAt(ev, target);
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
  status(ok ? `drop to move ${c.name} to (${fr}, ${fc})` : `(${fr}, ${fc}) is taken` + (o && !o.startsWith('route:') ? ` by ${o}` : ' by a join'), ok ? '' : 'err');
}
function ghostBlock(b, dr, dc) {
  clearGhost();
  const g = el('g', {class: 'ghost good', transform: `translate(${(b.c0 + dc) * S},${(b.r0 + dr) * S})`}, $('over'));
  el('rect', {x: .4, y: .4, width: (b.c1 - b.c0 + 1) * S - .8, height: (b.r1 - b.r0 + 1) * S - .8, rx: 1.6}, g);
  status(`drop to move block ${b.name} by (${dr}, ${dc})`);
}
function clearGhost() { $('over').innerHTML = ''; }
async function doMove(c, r, cc) {
  const [fr, fc] = fileSquare(r, cc);
  status(`moving ${c.name} to (${fr}, ${fc}): re-routing…`);
  const res = await edit('move', {name: c.name, r, c: cc, whole_block: false}, x => `moved ${c.name} to (${fr}, ${fc}); re-routed ${x.rerouted.length} join(s)` + (x.detours ? `, ${x.detours} timing detour(s) added` : '') + (L.problems.length ? `; ${L.problems.length} problem(s) left` : ''));
  if (res) { sel = c.name; showSelected(); }
}
async function doMoveBlock(b, dr, dc) {
  status(`moving block ${b.name}: re-routing its joins…`);
  await edit('move_block', {name: b.name, r: b.r0 + dr, c: b.c0 + dc}, x => `moved block ${b.name}; re-routed ${x.rerouted.length} join(s)` + (x.detours ? `, ${x.detours} detour(s)` : ''));
}

// ---- loading, saving -----------------------------------------------------------------------------------------------------------------
async function load(body) {
  status('loading…');
  const res = await api('/composer/api/load', body);
  if (!res.ok) { status(res.error, 'err'); return false; }
  sel = null; selBlock = null; take(res, false);
  status(`loaded ${L.name}`, 'ok');
  return true;
}
$('newBtn').onclick = async () => {
  const dims = prompt('New design: rows × columns', '24 x 40'); if (!dims) return;
  const m = dims.match(/(\d+)\D+(\d+)/); if (!m) { status('give two numbers, e.g. 24 x 40', 'err'); return; }
  const name = prompt('Design name', 'new design') || 'new design';
  if (await load({new: {rows: +m[1], cols: +m[2], name}})) setMode('place');
};
$('file').onchange = async ev => { const f = ev.target.files[0]; if (f) load({name: f.name, text: await f.text()}); ev.target.value = ''; };
$('example').onchange = ev => { if (ev.target.value) load({example: ev.target.value}); ev.target.value = ''; };
$('builder').onchange = ev => { if (ev.target.value) { status('building ' + ev.target.value + '…'); load({builder: ev.target.value}); } ev.target.value = ''; };
$('loadPath').onclick = () => { const p = $('path').value.trim(); if (p) load({path: p}); };
$('path').onkeydown = ev => { if (ev.key === 'Enter') $('loadPath').onclick(); };
$('fit').onclick = fit;
$('zin').onclick = () => zoom(1 / 1.4);
$('zout').onclick = () => zoom(1.4);
$('heat').onclick = () => { heat = !heat; $('heat').classList.toggle('primary', heat); draw(true); };
$('inside').onclick = () => { blockMode = {auto: 'tiles', tiles: 'open', open: 'auto'}[blockMode]; $('inside').textContent = 'Blocks: ' + blockMode; $('inside').classList.toggle('primary', blockMode !== 'auto'); draw(true); showSelected(); };
$('undo').onclick = () => edit('undo', {}, 'undone');
$('balance').onclick = () => edit('balance', {}, r => r.detours ? `balanced: ${r.detours} timing detour(s) added` : 'already balanced');
$('save').onclick = () => { if (!L) { status('nothing to save', 'err'); return; } window.location = '/composer/api/save'; if (L.blocks.length) status('saved as ICM-VIX: each block is a placement of its model, so it comes back as a block', 'ok'); };
$('saveFlat').onclick = () => { if (!L) { status('nothing to save', 'err'); return; } window.location = '/composer/api/save?fmt=v3'; };
$('saveLib').onclick = async () => {
  if (!L) { status('nothing to save', 'err'); return; }
  const name = prompt('Library model name (its io-named cells become its ports)', L.name.replace(/(\.icm-hier|\.icm)?\.json$/, '').replace(/[^A-Za-z0-9_.-]/g, '_'));
  if (!name) return;
  let res = await api('/composer/api/save_library', {name});
  if (!res.ok && res.exists && confirm(res.error + '. Replace it?')) res = await api('/composer/api/save_library', {name, overwrite: true});
  if (!res.ok) { status(res.error, 'err'); return; }
  take(res, true); status(`saved ${res.saved} to the library: put it in any design with Insert block`, 'ok');
};
$('find').onkeydown = ev => {
  if (ev.key !== 'Enter') return;
  const q = ev.target.value.trim().toLowerCase(); if (!q || !L) return;
  const hit = L.cells.find(c => c.name.toLowerCase() === q) || L.cells.find(c => c.name.toLowerCase().includes(q));
  hit ? focusCell(hit.name) : status(`no cell matches ${q}`, 'err');
};
document.addEventListener('keydown', ev => { if (ev.key === 'Escape') setMode('select'); });
window.addEventListener('resize', () => { if (L) { vb.h = vb.w * H() / W(); setVB(); updateLabels(); } });
palette();
api('/composer/api/state').then(res => { take(res, false); if (!res.layout) { setVB(); status('start a new design, import an ICM file, or open an example'); } });
})();
"""
