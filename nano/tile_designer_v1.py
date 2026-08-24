"""
tile_designer_v1.py — the real Tile Designer (points.md #487), per
`docs/stripped-cell/design-notes/tile_designer_scope.md`'s own real
scoping pass: an interactive tool for placing and wiring real,
registered tiles (any kind in `tile_source_registry_v1.py`, plus every
Tier-1 composed tile) into a real model, exporting a real ICM v3/v4
file -- the DSL's own visual sibling, not a competitor to it.

TWO REAL LAYERS, DELIBERATELY SEPARATE, matching `workbench_v1.py`'s
own already-proven split exactly (`workbench_scope.md`'s own
precedent): `TileDesignerController` holds the current in-progress
design and implements every real operation as a plain Python method
returning a JSON-ready dict -- no HTTP knowledge at all, fully
testable without a live socket. `TileDesignerHandler` is a thin
`http.server` dispatcher on top.

REUSES, DOES NOT REIMPLEMENT: `tile_source_registry_v1.find_source_for
()`/`all_sources()` (the real tile catalog), `composed_tile_library_v1.
place_composed()` and each source's own `place_fn` (the real, single
source of port/param validation truth -- a Designer-built instance is
checked against the EXACT SAME contract a hand-written DSL placement
is), and `icm_v3.IcmV3File`/`icm_v4.IcmV4File` (the real output
format, unchanged). The Designer's own code is placement/wiring
bookkeeping and HTTP glue -- nothing here re-validates a port/param
contract independently of the real `place()`/`place_composed()` calls
already proven correct elsewhere.
"""

from __future__ import annotations

import http.server
import json
import sys
import threading
import webbrowser
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import icm_v3 as v3
import icm_v4 as v4
from composed_tile_library_v1 import composed_tile_library, place_composed
# Imported for their own self-registration side effects (points.md
# #485) -- same discipline dsl_compiler_v1.py already follows: this
# is the ONE line a future tile-kind module needs added here to be
# resolvable by name/listed in the library panel.
import super_tile_library_v1  # noqa: F401
import dsp_wrapper_tile_library_v1  # noqa: F401
from tile_source_registry_v1 import find_source_for, all_sources

_DIR_DELTA = {"n": (-1, 0), "s": (1, 0), "e": (0, 1), "w": (0, -1)}


@dataclass
class TileInstance:
    """One placed-but-possibly-still-being-wired tile on the design
    canvas. `port_directions`/`params` accumulate incrementally as a
    real person (or a test) sets them one at a time -- an instance
    with missing/wrong entries simply fails `validate()`'s own real
    `place()`/`place_composed()` call, the same honest failure mode a
    hand-written DSL placement gets."""
    instance_id: str
    tile_name: str
    row: int
    col: int
    port_directions: Dict[str, object] = field(default_factory=dict)
    params: Dict[str, object] = field(default_factory=dict)


def _composed_param_names(tile) -> List[str]:
    """Real, small, LOCAL recursive param-name computation for the
    library-panel LISTING only (not used for validation -- `place_
    composed()`'s own real check is authoritative there). Deliberately
    NOT importing `dsl_compiler_v1._param_names` (a private, underscore-
    prefixed helper of another module) -- this file keeps its own
    small, honest duplicate rather than reaching into another module's
    private internals, matching this codebase's own "private means
    private" convention elsewhere."""
    if hasattr(tile, "param_names"):
        return list(tile.param_names)
    names: List[str] = []
    for sub in tile.subcells:
        if sub.tile_name in composed_tile_library.names():
            sub_tile = composed_tile_library.get(sub.tile_name)
        else:
            source = find_source_for(sub.tile_name)
            sub_tile = source.library.get(sub.tile_name) if source is not None else None
        if sub_tile is None:
            continue
        for p in _composed_param_names(sub_tile):
            if p not in sub.fixed_params:
                names.append(f"{sub.name}.{p}")
    return names


class TileDesignerController:
    """The real, HTTP-unaware core. Every method returns a plain,
    JSON-ready dict with an `"ok"` key -- matching `WorkbenchController`
    's own established convention exactly, so `TileDesignerHandler`
    stays a pure dispatcher with zero business logic of its own."""

    def __init__(self):
        self.instances: Dict[str, TileInstance] = {}

    # ── Real tile resolution, reused everywhere below ──────────────

    def _resolve_tile(self, tile_name: str):
        """Returns (kind, tile_obj, place_fn) -- `place_fn` is `None`
        for a composed tile (placed via `place_composed()` directly,
        not a per-kind `place_fn`). Raises `KeyError` if unknown --
        same real error `SuperTileLibrary.get()`/`DspWrapperTileLibrary
        .get()`/`ComposedTileLibrary.get()` already raise, not a new
        convention invented here."""
        if tile_name in composed_tile_library.names():
            return "composed", composed_tile_library.get(tile_name), None
        source = find_source_for(tile_name)
        if source is not None:
            return source.kind, source.library.get(tile_name), source.place_fn
        raise KeyError(f"no tile named {tile_name!r} in any registered library")

    def _place_instance(self, inst: TileInstance) -> list:
        kind, tile, place_fn = self._resolve_tile(inst.tile_name)
        if kind == "composed":
            return place_composed(tile, inst.row, inst.col, inst.port_directions,
                                   inst.params, composed_library=composed_tile_library)
        return [place_fn(tile, inst.row, inst.col, inst.port_directions, inst.params,
                          cell_id=f"{inst.instance_id}@{inst.row},{inst.col}")]

    def _describe_instance(self, inst: TileInstance) -> Dict[str, Any]:
        try:
            kind, tile, _ = self._resolve_tile(inst.tile_name)
            ports = tile.port_names()
        except KeyError:
            kind, ports = "unknown", []
        return {
            "instance_id": inst.instance_id, "tile_name": inst.tile_name, "kind": kind,
            "row": inst.row, "col": inst.col,
            "ports": ports, "port_directions": dict(inst.port_directions),
            "params": dict(inst.params),
            "connections": self._port_connections(inst),
        }

    def _instance_at(self, row: int, col: int) -> Optional[str]:
        for iid, other in self.instances.items():
            if other.row == row and other.col == col:
                return iid
        return None

    def _port_connections(self, inst: TileInstance) -> Dict[str, List[Dict[str, Any]]]:
        """Real, GEOMETRIC connection status per wired port -- computed
        server-side (not duplicated in JS) so it's testable the normal
        way, matching this whole project's own discipline. For each
        direction a port currently points, reports whether a real
        neighboring instance sits there (`"connected"`) or not
        (`"open"` -- a real, honest boundary, either genuinely
        unconnected or a real future injection point, per Alan's own
        next-step request). NOTE, stated plainly: this is computed
        from the INSTANCE's own anchor `(row, col)` -- exact for every
        Tier-0-shaped tile (whose anchor IS its one real cell), but an
        approximation for a composed (Tier-1) instance, whose real
        ports may belong to a sub-cell offset from the anchor
        (`#486`). The underlying export via `place()`/`place_composed()`
        is unaffected either way -- this only concerns how the
        indicator is drawn, not what gets exported."""
        conns: Dict[str, List[Dict[str, Any]]] = {}
        for port, direction in inst.port_directions.items():
            dirs = direction if isinstance(direction, list) else [direction]
            entries = []
            for d in dirs:
                d_norm = str(d).lower()
                if d_norm not in _DIR_DELTA:
                    entries.append({"direction": d, "status": "invalid"})
                    continue
                dr, dc = _DIR_DELTA[d_norm]
                trow, tcol = inst.row + dr, inst.col + dc
                target_id = self._instance_at(trow, tcol)
                entries.append({
                    "direction": d_norm, "target_row": trow, "target_col": tcol,
                    "target_instance_id": target_id,
                    "status": "connected" if target_id else "open",
                })
            conns[port] = entries
        return conns

    # ── Real library panel ──────────────────────────────────────────

    def list_library(self) -> Dict[str, Any]:
        entries = []
        for name in composed_tile_library.names():
            tile = composed_tile_library.get(name)
            entries.append({
                "name": name, "kind": "composed", "description": tile.description,
                "ports": tile.port_names(), "params": _composed_param_names(tile),
                "proven": tile.proven,
            })
        for source in all_sources():
            for name in source.library.names():
                tile = source.library.get(name)
                entries.append({
                    "name": name, "kind": source.kind, "description": tile.description,
                    "ports": tile.port_names(), "params": list(getattr(tile, "param_names", [])),
                    "proven": getattr(tile, "proven", "n/a"),
                })
        entries.sort(key=lambda e: e["name"])
        return {"ok": True, "tiles": entries}

    # ── Real design bookkeeping ─────────────────────────────────────

    def add_instance(self, instance_id: str, tile_name: str, row: int, col: int) -> Dict[str, Any]:
        if not instance_id:
            return {"ok": False, "error": "instance_id is required"}
        if instance_id in self.instances:
            return {"ok": False, "error": f"instance {instance_id!r} already exists"}
        try:
            self._resolve_tile(tile_name)
        except KeyError as e:
            return {"ok": False, "error": str(e)}
        self.instances[instance_id] = TileInstance(instance_id, tile_name, row, col)
        return {"ok": True, "instance": self._describe_instance(self.instances[instance_id])}

    def move_instance(self, instance_id: str, row: int, col: int) -> Dict[str, Any]:
        inst = self.instances.get(instance_id)
        if inst is None:
            return {"ok": False, "error": f"no instance {instance_id!r}"}
        inst.row, inst.col = row, col
        return {"ok": True, "instance": self._describe_instance(inst)}

    def remove_instance(self, instance_id: str) -> Dict[str, Any]:
        if instance_id not in self.instances:
            return {"ok": False, "error": f"no instance {instance_id!r}"}
        del self.instances[instance_id]
        return {"ok": True}

    def set_port(self, instance_id: str, port_name: str, direction) -> Dict[str, Any]:
        inst = self.instances.get(instance_id)
        if inst is None:
            return {"ok": False, "error": f"no instance {instance_id!r}"}
        try:
            _, tile, _ = self._resolve_tile(inst.tile_name)
        except KeyError as e:
            return {"ok": False, "error": str(e)}
        if port_name not in tile.port_names():
            return {"ok": False, "error": f"tile {inst.tile_name!r} has no port {port_name!r} "
                                           f"(has: {tile.port_names()})"}
        inst.port_directions[port_name] = direction
        return {"ok": True, "instance": self._describe_instance(inst)}

    def set_param(self, instance_id: str, param_name: str, value) -> Dict[str, Any]:
        """Deliberately NOT pre-validated against a computed param-name
        set here (a composed tile's real namespaced params can only be
        known authoritatively by walking its own real sub-cell tree,
        `_composed_param_names()`'s own listing-only approximation is
        not used as a gate) -- `validate()`/`export_icm()`'s own real
        `place()`/`place_composed()` call is the one, authoritative
        check, exactly matching `dsl_compiler_v1.py`'s own "defer to
        the real placement function" discipline."""
        inst = self.instances.get(instance_id)
        if inst is None:
            return {"ok": False, "error": f"no instance {instance_id!r}"}
        inst.params[param_name] = value
        return {"ok": True, "instance": self._describe_instance(inst)}

    def describe(self) -> Dict[str, Any]:
        return {"ok": True, "instances": [self._describe_instance(i) for i in self.instances.values()]}

    # ── Real validate/export -- the whole point ─────────────────────

    def validate(self) -> Dict[str, Any]:
        """Attempts a real `place()`/`place_composed()` resolution for
        EVERY instance, collecting real errors -- reuses the exact same
        validation truth the DSL compiler and every other real caller
        of these functions already relies on. Also checks for a real,
        GLOBAL position collision across every instance's own resolved
        cell(s) -- the same check `dsl_compiler_v1.compile_program_ir()`
        already runs for a DSL program, applied here to a Designer
        session instead."""
        errors: List[Dict[str, str]] = []
        occupied: Dict[Tuple[int, int], str] = {}
        for iid, inst in self.instances.items():
            try:
                records = self._place_instance(inst)
            except (ValueError, KeyError) as e:
                errors.append({"instance_id": iid, "problem": str(e)})
                continue
            for rec in records:
                key = (rec.row, rec.col)
                if key in occupied and occupied[key] != iid:
                    errors.append({
                        "instance_id": iid,
                        "problem": f"cell {key} is already occupied by instance {occupied[key]!r}",
                    })
                else:
                    occupied[key] = iid
        return {"ok": len(errors) == 0, "errors": errors}

    def export_icm(self, name: str, description: str = ""):
        """Real, direct construction of `v3.IcmV3File` or `v4.IcmV4File`
        -- format SELECTED the same way `#485`'s own compiler output
        selection works: plain `IcmV3File` when no instance resolved to
        a `DspWrapperRecord`, `IcmV4File` only when at least one did.
        Raises `ValueError` (not a dict) if the design doesn't validate
        -- this is the one real method in this controller meant to be
        called from trusted, already-checked code (`save_icm()`,
        direct Python/test use), not directly off an unchecked HTTP
        body; the HTTP handler calls `validate()` first and only calls
        this once it's confirmed clean."""
        result = self.validate()
        if not result["ok"]:
            raise ValueError(f"design has {len(result['errors'])} real error(s), can't export: "
                              f"{result['errors']}")

        super_records: List["v3.IcmV3Record"] = []
        dsp_wrapper_records: List["v4.DspWrapperRecord"] = []
        for inst in self.instances.values():
            for rec in self._place_instance(inst):
                if isinstance(rec, v4.DspWrapperRecord):
                    dsp_wrapper_records.append(rec)
                else:
                    super_records.append(rec)

        if dsp_wrapper_records:
            return v4.IcmV4File(name=name, super_records=super_records,
                                 dsp_wrapper_records=dsp_wrapper_records, description=description)
        return v3.IcmV3File(name=name, records=super_records, description=description)

    def save_icm(self, path: str, name: str, description: str = "") -> Dict[str, Any]:
        try:
            icm = self.export_icm(name, description)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        icm.save(path)
        return {"ok": True, "path": path, "format_version": icm.format_version}


# ── Real HTML/JS page, per tile_designer_scope.md's own corrected
# link paradigm: choosing a real cardinal direction per port, not a
# blind drag-anywhere-to-anywhere gesture. Real, working code -- its
# own interactive polish is real, separate, future work once someone
# actually clicks through it (stated honestly in the scope note: this
# part can't be interactively verified in this environment). ────────
TILE_DESIGNER_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Unicell-S Tile Designer</title>
<style>
  body { font-family: monospace; margin: 12px; background: #1a1a1a; color: #ddd; }
  #layout { display: flex; gap: 16px; }
  #library { width: 280px; }
  .tile-entry { border: 1px solid #444; padding: 6px; margin-bottom: 4px; cursor: pointer; }
  .tile-entry:hover { background: #2a2a2a; }
  .tile-entry.selected { background: #35502f; border-color: #7c7; }
  #grid { border-collapse: collapse; }
  #grid td { width: 44px; height: 44px; border: 1px solid #333; text-align: center;
             vertical-align: middle; font-size: 10px; cursor: pointer; position: relative; }
  #grid td.occupied { background: #2b3d5a; }
  #grid td.selected { outline: 2px solid #7c7; }
  #grid td.drop-target { outline: 2px dashed #77c; }
  .port-indicator { position: absolute; width: 9px; height: 9px; border-radius: 50%;
                     border: 1px solid #111; pointer-events: none; }
  .port-indicator.dir-n { top: -5px; left: 50%; margin-left: -5px; }
  .port-indicator.dir-s { bottom: -5px; left: 50%; margin-left: -5px; }
  .port-indicator.dir-e { right: -5px; top: 50%; margin-top: -5px; }
  .port-indicator.dir-w { left: -5px; top: 50%; margin-top: -5px; }
  .port-indicator.status-connected { background: #4a7; }
  .port-indicator.status-open { background: #c93; }
  .port-indicator.status-invalid { background: #c33; }
  #inspector { width: 320px; }
  .dirbtn { width: 28px; }
  .dirbtn.active { background: #4a7; color: #000; }
  #log { white-space: pre-wrap; font-size: 11px; color: #9c9; max-height: 200px; overflow-y: auto; }
</style>
</head>
<body>
<h2>Unicell-S Tile Designer</h2>
<div id="layout">
  <div id="library">
    <h3>Library</h3>
    <div id="libraryList"></div>
  </div>
  <div id="canvas">
    <h3>Grid (click a cell to place the selected tile, or select an instance)</h3>
    <table id="grid"></table>
    <button onclick="validateDesign()">Validate</button>
    <button onclick="exportDesign()">Export ICM</button>
    <div id="log"></div>
  </div>
  <div id="inspector">
    <h3>Selected instance</h3>
    <div id="inspectorBody">(none selected)</div>
  </div>
</div>
<script>
const GRID_SIZE = 12;
let selectedTile = null;
let selectedInstance = null;
let library = [];
let instances = [];

async function api(path, body) {
  const opts = body ? {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)}
                     : {method: "GET"};
  const res = await fetch(path, opts);
  return res.json();
}

function log(msg) {
  const el = document.getElementById("log");
  el.textContent = msg + "\\n" + el.textContent;
}

async function loadLibrary() {
  const data = await api("/library");
  library = data.tiles || [];
  const el = document.getElementById("libraryList");
  el.innerHTML = "";
  for (const tile of library) {
    const div = document.createElement("div");
    div.className = "tile-entry";
    div.textContent = tile.name + " [" + tile.kind + "]";
    div.title = tile.description;
    div.onclick = () => selectTileToPlace(tile.name, div);
    el.appendChild(div);
  }
}

function selectTileToPlace(name, el) {
  selectedTile = name;
  document.querySelectorAll(".tile-entry").forEach(e => e.classList.remove("selected"));
  el.classList.add("selected");
}

// ── Pure geometry helper, deliberately no DOM/state references --
// kept separable so it's directly testable outside a browser (node),
// matching this project's own "prove what's provable" discipline even
// for a piece of client-side JS. ──────────────────────────────────
function directionFromDelta(dr, dc) {
  if (dr === -1 && dc === 0) return "n";
  if (dr === 1 && dc === 0) return "s";
  if (dr === 0 && dc === 1) return "e";
  if (dr === 0 && dc === -1) return "w";
  return null;
}

function unwiredPorts(inst) {
  return inst.ports.filter(p => !(p in inst.port_directions));
}

function buildGrid() {
  const table = document.getElementById("grid");
  table.innerHTML = "";
  for (let r = 0; r < GRID_SIZE; r++) {
    const tr = document.createElement("tr");
    for (let c = 0; c < GRID_SIZE; c++) {
      const td = document.createElement("td");
      td.dataset.row = r; td.dataset.col = c;
      td.onclick = () => cellClicked(r, c);
      // Real drag-to-connect target: any cell can be dropped on --
      // connectDrag() itself rejects a non-adjacent drop with a real
      // message rather than silently doing nothing.
      td.ondragover = (e) => { e.preventDefault(); td.classList.add("drop-target"); };
      td.ondragleave = () => td.classList.remove("drop-target");
      td.ondrop = (e) => {
        e.preventDefault();
        td.classList.remove("drop-target");
        const sourceId = e.dataTransfer.getData("text/plain");
        if (sourceId) connectDrag(sourceId, r, c);
      };
      tr.appendChild(td);
    }
    table.appendChild(tr);
  }
}

async function cellClicked(row, col) {
  const existing = instances.find(i => i.row === row && i.col === col);
  if (existing) {
    selectInstance(existing.instance_id);
    return;
  }
  if (!selectedTile) {
    log("select a tile from the library first");
    return;
  }
  const id = selectedTile + "_" + Date.now();
  const result = await api("/add_instance", {instance_id: id, tile_name: selectedTile, row, col});
  if (!result.ok) { log("error: " + result.error); return; }
  await refresh();
  selectInstance(id);
}

// ── Real drag-to-connect gesture: drag from an occupied cell (the
// SOURCE instance, wired up in refresh() below), drop on an
// immediately-adjacent cell -- the direction is inferred from the
// real geometry, then whichever of the source's own still-unwired
// ports applies gets set to it (prompting only if genuinely
// ambiguous, i.e. more than one unwired port remains). Deliberately
// one real cardinal step only -- matches the underlying model exactly
// (`tile_designer_scope.md`'s own corrected link paradigm: a real
// direction, not an arbitrary wire). ────────────────────────────────
async function connectDrag(sourceId, targetRow, targetCol) {
  const source = instances.find(i => i.instance_id === sourceId);
  if (!source) return;
  const dir = directionFromDelta(targetRow - source.row, targetCol - source.col);
  if (!dir) {
    log("connections must be to an immediately adjacent cell (one real cardinal step)");
    return;
  }
  const candidates = unwiredPorts(source);
  if (candidates.length === 0) {
    log("no unwired ports left on " + sourceId + " -- use the inspector to change an existing one");
    return;
  }
  let port = candidates[0];
  if (candidates.length > 1) {
    const typed = prompt("Which port on " + sourceId + "? (" + candidates.join(", ") + ")", candidates[0]);
    if (!typed) return;
    if (!candidates.includes(typed)) { log("unknown or already-wired port " + typed); return; }
    port = typed;
  }
  const result = await api("/set_port", {instance_id: sourceId, port_name: port, direction: dir});
  if (!result.ok) { log("error: " + result.error); return; }
  await refresh();
  renderInspector();
}

async function selectInstance(id) {
  selectedInstance = id;
  await refresh();
  renderInspector();
}

function renderInspector() {
  const el = document.getElementById("inspectorBody");
  const inst = instances.find(i => i.instance_id === selectedInstance);
  if (!inst) { el.innerHTML = "(none selected)"; return; }
  let html = "<b>" + inst.instance_id + "</b> (" + inst.tile_name + ")<br>";
  html += "row=" + inst.row + " col=" + inst.col + "<br><br>";
  for (const port of inst.ports) {
    const current = inst.port_directions[port] || "";
    html += port + ": ";
    for (const d of ["n", "s", "e", "w"]) {
      const active = current === d || (Array.isArray(current) && current.includes(d));
      html += "<button class='dirbtn" + (active ? " active" : "") + "' " +
              "onclick=\\"setPort('" + inst.instance_id + "','" + port + "','" + d + "')\\">" + d + "</button>";
    }
    html += "<br>";
  }
  html += "<br><button onclick=\\"removeInstance('" + inst.instance_id + "')\\">Remove</button>";
  html += "<br><br><i>tip: drag this tile's own grid cell onto an adjacent cell to connect a port by direction</i>";
  el.innerHTML = html;
}

async function setPort(instanceId, port, direction) {
  const result = await api("/set_port", {instance_id: instanceId, port_name: port, direction});
  if (!result.ok) { log("error: " + result.error); return; }
  await refresh();
  renderInspector();
}

async function removeInstance(instanceId) {
  await api("/remove_instance", {instance_id: instanceId});
  selectedInstance = null;
  await refresh();
  renderInspector();
}

function renderConnectionIndicators() {
  document.querySelectorAll(".port-indicator").forEach(el => el.remove());
  for (const inst of instances) {
    const td = document.querySelector(`#grid td[data-row='${inst.row}'][data-col='${inst.col}']`);
    if (!td || !inst.connections) continue;
    for (const port in inst.connections) {
      for (const conn of inst.connections[port]) {
        if (!["n", "s", "e", "w"].includes(conn.direction)) continue;
        const marker = document.createElement("div");
        marker.className = "port-indicator dir-" + conn.direction + " status-" + conn.status;
        marker.title = inst.instance_id + "." + port + " -> " + conn.direction + " (" + conn.status + ")";
        td.appendChild(marker);
      }
    }
  }
}

async function refresh() {
  const data = await api("/describe");
  instances = data.instances || [];
  document.querySelectorAll("#grid td").forEach(td => {
    td.classList.remove("occupied", "selected");
    td.textContent = "";
    td.draggable = false;
    td.ondragstart = null;
  });
  for (const inst of instances) {
    const td = document.querySelector(`#grid td[data-row='${inst.row}'][data-col='${inst.col}']`);
    if (td) {
      td.classList.add("occupied");
      if (inst.instance_id === selectedInstance) td.classList.add("selected");
      td.textContent = inst.tile_name;
      // Real drag SOURCE -- any occupied cell can start a
      // drag-to-connect gesture toward an adjacent cell.
      td.draggable = true;
      td.ondragstart = (e) => { e.dataTransfer.setData("text/plain", inst.instance_id); };
    }
  }
  renderConnectionIndicators();
}

async function validateDesign() {
  const result = await api("/validate", {});
  if (result.ok) { log("valid -- 0 errors"); }
  else { log("invalid -- " + result.errors.length + " error(s):\\n" +
             result.errors.map(e => "  " + e.instance_id + ": " + e.problem).join("\\n")); }
}

async function exportDesign() {
  const name = prompt("Program name?", "my_design");
  if (!name) return;
  const result = await api("/export_icm", {name});
  if (!result.ok) { log("export failed: " + result.error); return; }
  log("exported: " + JSON.stringify(result.icm, null, 2));
}

buildGrid();
loadLibrary();
refresh();
</script>
</body>
</html>
"""


class TileDesignerHandler(http.server.BaseHTTPRequestHandler):
    controller: Optional[TileDesignerController] = None

    def _json_response(self, data: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _html_response(self, html: str) -> None:
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        if self.path == "/library":
            self._json_response(self.controller.list_library())
        elif self.path == "/describe":
            self._json_response(self.controller.describe())
        elif self.path in ("/", "/index.html"):
            self._html_response(TILE_DESIGNER_HTML)
        else:
            self._json_response({"ok": False, "error": "not found"}, status=404)

    def do_POST(self):
        body = self._read_json_body()
        if self.path == "/add_instance":
            self._json_response(self.controller.add_instance(
                body.get("instance_id", ""), body.get("tile_name", ""),
                body.get("row", 0), body.get("col", 0)))
        elif self.path == "/move_instance":
            self._json_response(self.controller.move_instance(
                body.get("instance_id", ""), body.get("row", 0), body.get("col", 0)))
        elif self.path == "/remove_instance":
            self._json_response(self.controller.remove_instance(body.get("instance_id", "")))
        elif self.path == "/set_port":
            self._json_response(self.controller.set_port(
                body.get("instance_id", ""), body.get("port_name", ""), body.get("direction")))
        elif self.path == "/set_param":
            self._json_response(self.controller.set_param(
                body.get("instance_id", ""), body.get("param_name", ""), body.get("value")))
        elif self.path == "/validate":
            self._json_response(self.controller.validate())
        elif self.path == "/export_icm":
            try:
                icm = self.controller.export_icm(body.get("name", "untitled"), body.get("description", ""))
                self._json_response({"ok": True, "icm": icm.to_dict()})
            except ValueError as e:
                self._json_response({"ok": False, "error": str(e)})
        else:
            self._json_response({"ok": False, "error": "not found"}, status=404)

    def log_message(self, fmt, *args):
        pass


def serve(port: int = 7421, open_browser: bool = False) -> http.server.HTTPServer:
    TileDesignerHandler.controller = TileDesignerController()
    server = http.server.HTTPServer(("localhost", port), TileDesignerHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    if open_browser:
        webbrowser.open(f"http://localhost:{port}")
    return server


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7421
    server = serve(port, open_browser=True)
    print(f"Tile Designer serving at http://localhost:{port}")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        server.shutdown()
