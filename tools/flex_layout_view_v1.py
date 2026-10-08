"""tools/flex_layout_view_v1.py -- the Composer's layout side (design note docs/stripped-cell/design-notes/composer_layout_viewer_scope.md): import an ICM file or start a blank
board, place cells, set their configuration, join them, insert saved designs as single BLOCKS, move things by hand, and save ICM v3. The layout engine (`flex_layout_v1.Grid`) does
every route, the hop model, `problems()` and `balance()`; this module adds no routing or timing logic of its own and does not change flex_layout_v1.py.

JOINS ARE TAGGED. A join is one route (a chain of plain relay rams, possibly through crossing tiles) or one direct link between neighbours, from a SOURCE cell to a DESTINATION cell.
It carries the output PORT it leaves by and the input ROLE it arrives as:
    ports  out (downstream_mask), second (second_downstream_mask: the adder's carry, the mul's high word), low / equal / high (branch route_*), out on a nano = routing_mask
    roles  in (upstream_mask; a branch's single upstream_dir; a nano listens on any face), set / clear / toggle (latch), inc / dec (accumulator)
Every direction field of every cell is DERIVED from its joins (plus any face that leaves the design, kept from the file), so a cell can be moved and re-joined without touching its
configuration. Import recovers the tags from the file; an imported design re-exports record for record. Cells wired by fields this cannot derive (nano, priority, command) are
PINNED: drawn, joinable only as the file had them, written back exactly as read.

BLOCKS. `place_block(path, r, c)` inserts a saved design as one unit: its cells are prefixed `<block>.`, moved together (`move_block`), and its `io_name` cells become the block's
PORTS (joins attach there). Save flattens blocks into plain cells (ICM v3 has no hierarchy); `unpack_block` turns a block's cells into ordinary cells.

Usage:  python3 tools/flex_layout_view_v1.py FILE.icm.json [--json OUT]     (a summary, or the snapshot JSON)
        python3 tools/flex_layout_view_v1.py --builder fp_add/fp16 ...          (a layout built by Python, e.g. the fp adder)
Test/design-support tooling: it only reads and writes ICM records; the RTL generator stays the oracle."""
import argparse
import collections
import copy
import json
import os
import re
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS_DIR)
sys.path.insert(0, os.path.join(TOOLS_DIR, "..", "nano"))
import flexsub_icm_netlist_v1 as nl  # noqa: E402
import icm_v3  # noqa: E402
from flex_layout_v1 import D, OPP, PAIR, Grid, LayoutError  # noqa: E402
from icm_v3 import IcmV3File, IcmV3Record  # noqa: E402

MASKS = ("upstream_mask", "downstream_mask", "second_downstream_mask")
PINNED_CORES = ("priority", "command", "corner")      # a corner tile (ledger #1035) turns words by its `turn` bit, not by routing: the view keeps its wiring exactly as filed
MARGIN = 3                     # free squares kept round an imported design, so routes can go round its edge
UNDO_DEPTH = 40
OUT_FIELD = {"out": "downstream_mask", "second": "second_downstream_mask", "low": "route_low", "equal": "route_equal", "high": "route_high"}
IN_FIELD = {"in": "upstream_mask", "set": "set_dir", "clear": "clear_dir", "toggle": "toggle_dir", "inc": "inc_dir", "dec": "dec_dir"}
SHORT = {"ram": "ram", "adder": "add", "mul": "mul", "comparator": "cmp", "accumulator": "acc", "latch": "lat", "sequencer": "seq", "branch": "br", "nano": "nano",
         "priority": "pri", "cross": "x", "corner": "cor"}


def table(core):
    return icm_v3.CORE_FIELD_TABLES.get(icm_v3.CORE_IDS.get(core, -1), {})


NANO_OUT = {"out": "routing_mask", "low": "pattern_low", "equal": "pattern_equal", "high": "pattern_high"}     # pattern_* route by the comparator outcome when dynamic_route_en is on
USER_DIR_FIELDS = {"nano": ("cardinal_edge",)}    # face fields the user sets (per incoming face: relay, not consume), not derived from joins


def out_field(core, port):
    return NANO_OUT.get(port) if core == "nano" else OUT_FIELD.get(port)


def in_field(core, role):
    if core == "nano":
        return None                                    # a nano listens on every face: no input field
    if core == "branch":
        return "upstream_dir" if role == "in" else "?"
    return IN_FIELD.get(role)


def out_ports(core):
    t = table(core)
    return [p for p in ("out", "second", "low", "equal", "high") if out_field(core, p) in t]


def in_roles(core):
    if core == "nano":
        return ["in"]
    t = table(core)
    return [r for r in IN_FIELD if in_field(core, r) in t] if core != "branch" else ["in"]


def dir_fields(core):
    """Every field of this core that names faces (all derived from joins)."""
    t = table(core)
    fs = {out_field(core, p) for p in out_ports(core)} | {in_field(core, r) for r in in_roles(core)}
    return [f for f in t if f in fs]


def core_meta():
    """What the page needs to draw a configuration panel: per core, its fields (bit range, kind), ports and roles; plus the add-on fields and the latch layout."""
    meta = {}
    for sel, core in icm_v3.CORE_NAMES.items():
        dirs, udirs = set(dir_fields(core)), set(USER_DIR_FIELDS.get(core, ()))
        fields = [{"name": f, "lo": lo, "hi": hi, "kind": "dirs" if f in dirs else "userdirs" if f in udirs else ("toggle" if lo == hi else "num")}
                  for f, (lo, hi) in icm_v3.CORE_FIELD_TABLES[sel].items()]
        if core == "nano":
            for f in fields:
                if f["name"] == "topology":
                    f["kind"], f["choices"] = "choice", TOPOLOGIES
        meta[core] = {"sel": sel, "fields": fields, "ports": out_ports(core), "roles": in_roles(core), "short": SHORT.get(core, core[:3])}
    addon = [{"name": f, "lo": lo, "hi": hi, "kind": "toggle" if lo == hi else "num"} for f, (lo, hi) in icm_v3._ADDON_FIELDS.items()]
    addon.append({"name": "shift_fine", "lo": 0, "hi": 1, "kind": "num"})
    latch = {"core_select": [icm_v3.CORE_SELECT_LO, icm_v3.CORE_SELECT_HI], "core_config": [icm_v3.CORE_CONFIG_LO, icm_v3.CORE_CONFIG_HI],
             "addon_config": [icm_v3.ADDON_CONFIG_LO, icm_v3.ADDON_CONFIG_HI], "shift_fine": [icm_v3.SHIFT_FINE_LO, icm_v3.SHIFT_FINE_HI], "width": icm_v3.SUPER_LATCH_WIDTH}
    return {"cores": meta, "addon": addon, "latch": latch, "palette": [c for c in icm_v3.CORE_NAMES.values() if c not in ("cross",)]}


TOPOLOGIES = [{"label": l, "value": v} for l, v in (("pass A", 0x000), ("not A", 0x001), ("not B", 0x002), ("nor", 0x004), ("and", 0x007), ("zero", 0x030),
                                                  ("xnor", 0x03C), ("or", 0x024), ("nand", 0x027), ("pass B", 0x02C), ("one", 0x0B0), ("xor", 0x0BC))]   # nano/unicell_gate_core.py TOPO_*


def _faces(cfg, key):
    return [d.lower() for d in nl._dirs(cfg or {}, key)]


def _out_faces(cfg, core):
    """[(face, second, ports)] for every face the cell sends on, grouped: the second word is its own entry."""
    first, second = collections.OrderedDict(), []
    for p in out_ports(core) if core in icm_v3.CORE_IDS else ["out"]:
        f = out_field(core, p)
        for d in (_faces(cfg, f) if f else []):
            if p == "second":
                second.append(d)
            else:
                first.setdefault(d, []).append(p)
    return [(d, False, tuple(ps)) for d, ps in first.items()] + [(d, True, ("second",)) for d in second]


def _in_roles_on(cfg, core, face):
    if core == "nano":
        return ("in",)
    if core == "cross":
        return ("in",) if face in _faces(cfg, "upstream_mask") else ()
    if core not in icm_v3.CORE_IDS:                    # an unknown core: any input field naming this face
        return ("in",) if any(face.upper() in nl._dirs(cfg or {}, f) for f in nl.INPUT_FIELDS) else ()
    return tuple(r for r in in_roles(core) if face in _faces(cfg, in_field(core, r)))


class Layout:
    def __init__(self, records, name="layout", description="", min_bit_width=None, board=None, anchors=()):
        self.name, self.description, self.min_bit_width = name, description, min_bit_width
        self.warnings, self._undo, self.blocks = [], [], {}
        self._build(list(records), board, anchors)

    @staticmethod
    def load(path):
        doc, recs, blocks = read_design(path)
        lay = Layout(recs, name=os.path.basename(path), description=getattr(doc, "description", "") or "", min_bit_width=getattr(doc, "min_bit_width", None),
                     anchors={k for v in blocks.values() for k in v["ports"].values()})
        lay.blocks = lay._adopt_blocks({b: v for b, v in blocks.items() if all(k in lay.grid.nodes for k in v["cells"])})
        return lay

    @staticmethod
    def new(rows=24, cols=40, name="new design"):
        """A blank board."""
        if not (2 <= rows <= 400 and 2 <= cols <= 1000):
            raise LayoutError("a board is 2..400 rows and 2..1000 columns")
        return Layout([], name=name, board=(rows, cols, (0, 0)))

    # ---- import -----------------------------------------------------------------------------------------------------------------------
    def _build(self, recs, board=None, anchors=()):
        """`anchors`: cells that are never folded into a route as relays (a block's ports: a join ends there)."""
        if not recs and board is None:
            raise LayoutError("the file has no cells")
        if board is not None:
            rows, cols, self.offset = board[0], board[1], tuple(board[2])
            orow, ocol = self.offset
            if recs:
                rows = max(rows, max(r.row for r in recs) + orow + 1 + 1)
                cols = max(cols, max(r.col for r in recs) + ocol + 1 + 1)
                if min(r.row + orow for r in recs) < 0 or min(r.col + ocol for r in recs) < 0:
                    raise LayoutError("a cell would be off the board")
        else:
            r0, c0 = min(r.row for r in recs), min(r.col for r in recs)
            self.offset = (MARGIN - r0, MARGIN - c0)              # file square + offset = layout square
            orow, ocol = self.offset
            rows = max(r.row for r in recs) + orow + 1 + MARGIN
            cols = max(r.col for r in recs) + ocol + 1 + MARGIN
        rec = collections.OrderedDict((r.cell_id, r) for r in recs)
        if len(rec) != len(recs):
            raise LayoutError("two cells share a cell_id")
        at = {(r.row + orow, r.col + ocol): r.cell_id for r in recs}
        if len(at) != len(recs):
            raise LayoutError("two cells share a square")
        pos = {k: (r.row + orow, r.col + ocol) for k, r in rec.items()}
        self.io = {k: r.io_name for k, r in rec.items() if r.io_name}
        self.pinned = {k for k, r in rec.items() if r.core in PINNED_CORES or r.core not in icm_v3.CORE_IDS
                       or (r.core == "nano" and any(isinstance((r.core_config or {}).get(f), int) and (r.core_config or {})[f] > 15 for f in NANO_OUT.values()))}
        self._orig_cfg = {k: dict(r.core_config or {}) for k in self.pinned for r in [rec[k]]}
        self._present = {k: set(r.core_config or {}) for k, r in rec.items()}       # an empty direction field the file left out stays left out

        # physical links, from the direction fields + positions (the generator's rule), each tagged with its port and role
        links, ltag = [], {}
        ext = collections.defaultdict(lambda: collections.defaultdict(list))      # cell -> field -> faces with no join behind them (they leave the design)
        ins_of, outs = collections.defaultdict(list), collections.defaultdict(list)
        for k, r in rec.items():
            for d, second, ports in _out_faces(r.core_config, r.core):
                q = at.get((pos[k][0] + D[d][0], pos[k][1] + D[d][1]))
                roles = _in_roles_on(rec[q].core_config, rec[q].core, OPP[d]) if q else ()
                if q is None or not roles:
                    if q is not None:
                        self.warnings.append(f"{k} sends {d.upper()} but {q} does not listen on that face (the word is dropped)")
                    for p in ports:
                        ext[k][out_field(r.core, p)].append(d)
                    continue
                links.append((k, q, second))
                ltag[(k, q, second)] = {"out": ports, "in": roles}
                ins_of[q].append(k)
                outs[k].append((q, second))
        for k, r in rec.items():                                # input faces with no sender behind them: entries from outside
            for role in (in_roles(r.core) if r.core in icm_v3.CORE_IDS and r.core != "nano" else []):
                f = in_field(r.core, role)
                for d in _faces(r.core_config, f):
                    q = at.get((pos[k][0] + D[d][0], pos[k][1] + D[d][1]))
                    if q is None or not any(a == q and b == k and role in ltag[(a, b, s)]["in"] for a, b, s in links):
                        ext[k][f].append(d)
        self.ext = {k: {f: list(v) for f, v in fs.items()} for k, fs in ext.items()}

        def plain_relay(k):
            r = rec[k]
            cfg = r.core_config or {}
            if r.core != "ram" or r.preload_value is not None or r.addon_config or r.io_name or k in self.ext or k in anchors:
                return False
            if any(x not in MASKS + ("fixed_mode",) for x in cfg) or cfg.get("fixed_mode"):
                return False
            return len(ins_of[k]) == 1 and len(outs[k]) == 1 and not outs[k][0][1]

        relay = {k for k in rec if plain_relay(k)}
        cross = {k for k, r in rec.items() if r.core == "cross"}

        def walk(a, b):
            path, prev, cur = [], a, b
            for _ in range(len(rec) + 1):
                if cur in cross:
                    d = next(x for x, (dr, dc) in D.items() if (pos[prev][0] + dr, pos[prev][1] + dc) == pos[cur])
                    nxt = at.get((pos[cur][0] + D[d][0], pos[cur][1] + D[d][1]))
                    if nxt is None or (nxt, False) not in outs[cur]:
                        return None
                    path.append((cur, "x"))
                    prev, cur = cur, nxt
                elif cur in relay:
                    path.append((cur, "r"))
                    prev, cur = cur, outs[cur][0][0]
                else:
                    return cur, path, prev
            return None

        logic = [k for k in rec if k not in relay and k not in cross]
        nets = []
        for _ in range(3):                                     # relays no logic cell reaches (a broken chain) become fixed cells, then walk again
            nets, claimed = [], set()
            for a in logic:
                for b, second in outs[a]:
                    got = walk(a, b)
                    if got is not None:
                        nets.append((a, got[0], second, got[1], {"out": ltag[(a, b, second)]["out"], "in": ltag[(got[2], got[0], False if got[1] else second)]["in"]}))
                        claimed.update(n for n, kind in got[1] if kind == "r")
            loose = relay - claimed
            if not loose:
                break
            relay -= loose
            logic += sorted(loose)
        for a, b, _, _, _ in nets:                             # a route touching a pinned cell keeps the file's wiring exactly: both ends stay put
            if a in self.pinned or b in self.pinned:
                for k in (a, b):
                    if k not in self._orig_cfg:
                        self.pinned.add(k)
                        self._orig_cfg[k] = dict(rec[k].core_config or {})

        g = Grid(rows=rows, cols=cols)
        self.grid, self.tags = g, {}
        for k in logic:
            r = rec[k]
            g.add(k, *pos[k], core=r.core, cfg=self._base_cfg(r.core, r.core_config), addon=r.addon_config, preload=r.preload_value)
        keys, raw = collections.Counter((a, b) for a, b, _, _, _ in nets), []
        for a, b, second, path, tag in nets:
            if keys[(a, b)] > 1 or a in self.pinned or b in self.pinned:     # two routes between one pair, or pinned: plain links (the engine keys routes by their two ends)
                raw.append((a, b, second, path, tag))
                continue
            names, crossings, last, n0 = [], [], a, len(g.links)
            for i, (nm, kind) in enumerate(path):
                if nm not in g.nodes:
                    g.add(nm, *pos[nm], core=rec[nm].core, cfg=self._base_cfg(rec[nm].core, rec[nm].core_config))
                    names.append(nm)
                elif kind == "x":
                    crossings.append(nm)
                g.link(last, nm, second=second and i == 0)
                last = nm
            g.link(last, b, second=second and not path)
            xl = [l for l in g.links[n0:] if l[0] in crossings or l[1] in crossings]
            g.routes[(a, b)] = {"relays": names, "second": second, "tag": None, "extra": 0, "crossings": crossings, "xlinks": xl}
            self.tags[(a, b, second)] = tag
        for a, b, second, path, tag in raw:
            last = a
            for i, (nm, kind) in enumerate(path):
                if nm not in g.nodes:
                    g.add(nm, *pos[nm], core=rec[nm].core, cfg=self._base_cfg(rec[nm].core, rec[nm].core_config))
                g.link(last, nm, second=second and i == 0)
                last = nm
            g.link(last, b, second=second and not path)
            self.tags[(a, b, second)] = tag
            for k in (a, b):
                if k not in self._orig_cfg:
                    self.pinned.add(k)
                    self._orig_cfg[k] = dict(rec[k].core_config or {})
        for x in cross:                                       # a crossing tile: owned by the route that has it as a relay, crossed by the other
            owner = next((k for k, v in g.routes.items() if x in v["relays"]), None)
            other = next((k for k, v in g.routes.items() if x in v["crossings"]), None)
            if x not in g.nodes:
                g.add(x, *pos[x], core="cross")
                self.warnings.append(f"{x}: crossing tile with nothing passing through")
            elif owner and other:
                g.crossed[x] = (owner, other)
        missing = [k for k in rec if k not in g.nodes]
        for k in missing:                                     # relays reached by no route at all (an isolated chain): placed as fixed cells
            g.add(k, *pos[k], core=rec[k].core, cfg=dict(rec[k].core_config or {}), addon=rec[k].addon_config, preload=rec[k].preload_value)
            self.pinned.add(k)
            self._orig_cfg[k] = dict(rec[k].core_config or {})
        for a, b, s in links:
            if (a in missing or b in missing) and (a, b, s) not in g.links:
                g.links.append((a, b, s))
        g._relay = max([int(m.group(1)) for k in g.nodes for m in [re.search(r"\.(\d+)$", k)] if m] + [len(g.nodes), getattr(self, "_relay_floor", 0)])
        self._set_minuends()

    @staticmethod
    def _base_cfg(core, cfg):
        """A cell's configuration without its direction fields (those come from its joins)."""
        dirs = set(dir_fields(core)) | set(MASKS) if core in icm_v3.CORE_IDS else set()
        return {k: v for k, v in (cfg or {}).items() if k not in dirs}

    def _set_minuends(self):
        """Keep a subtract's operand order: the source that arrives first now is declared the minuend, so a later move cannot swap the operands."""
        g = self.grid
        try:
            srcs, t = g.sources(), g.hops()
        except (LayoutError, RecursionError) as e:
            self.warnings.append(f"no timing model: {e}")
            return
        origin = {nm: a for (a, b), v in g.routes.items() for nm in v["relays"]}
        for c, n in g.nodes.items():
            if n["core"] in PAIR and n["cfg"].get("subtract_mode") and len(srcs[c]) == 2 and c not in g.minuend:
                x, y = srcs[c]
                tx, ty = t[x] + g.xdelay.get((c, x), 0), t[y] + g.xdelay.get((c, y), 0)
                if tx != ty:
                    first = x if tx < ty else y
                    g.minuend[c] = origin.get(first, first)

    # ---- queries ----------------------------------------------------------------------------------------------------------------------
    def members(self, b):
        """A block's cells: its logic cells (stored), the relays and crossing tiles of every route between two of them (derived: they change as routes are re-laid)."""
        g = self.grid
        logic = [k for k in self.blocks[b]["logic"] if k in g.nodes]
        mine = set(logic)
        out = list(logic)
        for (a, z), v in g.routes.items():
            if a in mine and z in mine:
                out += [nm for nm in v["relays"] if nm in g.nodes]
        return out

    def _block_map(self):
        return {k: b for b in self.blocks for k in self.members(b)}

    def block_of(self, k):
        return next((b for b in self.blocks if k in self.blocks[b]["logic"]), None) or next((b for b in self.blocks if k in self.members(b)), None)

    def _adopt_blocks(self, blocks):
        """Blocks from a file or an insertion: keep only the LOGIC cells as members (relays are derived), and find each block's model for the standard / function checks."""
        out = {}
        for b, v in blocks.items():
            v = dict(v)
            cells = v.pop("cells", None)
            if "logic" not in v:
                v["logic"] = [k for k in (cells or []) if k in self.grid.nodes and self.is_logic(k)]
            if "ref" not in v:
                path = find_model(v.get("file", ""))
                v["ref"], v["vectors"] = model_reference(path) if path else (None, None)
                v.setdefault("source", next((s for d, s in zip(LIBRARY_DIRS, ("std", "library", "example")) if path and os.path.dirname(os.path.abspath(path)) == os.path.abspath(d)), None))
            v.setdefault("check", None)
            out[b] = v
        return out

    def signature(self, cells, prefix=None):
        """What a block IS, independent of where it stands and of its joins to the outside: each logic cell (name without the block prefix, position relative to the
        block, core, configuration without its face fields, add-on, constant) and each join between two of its cells (ports, roles, and its length in relays)."""
        g = self.grid
        cells = [k for k in cells if k in g.nodes]
        if not cells:
            return "[]"
        r0, c0 = min(g.nodes[k]["r"] for k in cells), min(g.nodes[k]["c"] for k in cells)
        cut = (lambda k: k[len(prefix):] if prefix and k.startswith(prefix) else k)
        mine = set(cells)
        items = []
        for k in cells:
            n = g.nodes[k]
            base = self._orig_cfg[k] if k in self._orig_cfg else self._base_cfg(n["core"], n["cfg"])
            items.append(["cell", cut(k), n["r"] - r0, n["c"] - c0, n["core"], base, n["addon"] or {}, n["preload"]])
        for (a, z), v in g.routes.items():
            if a in mine and z in mine:
                tag = self.tags.get((a, z, v["second"]), {"out": ("second",) if v["second"] else ("out",), "in": ("in",)})
                items.append(["join", cut(a), cut(z), v["second"], len(v["relays"]), sorted(tag["out"]), sorted(tag["in"])])
        for (a, z, sec), tag in self.tags.items():
            if a in mine and z in mine and (a, z) not in g.routes:
                items.append(["link", cut(a), cut(z), sec, sorted(tag["out"]), sorted(tag["in"])])
        return json.dumps(sorted(items, key=lambda x: json.dumps(x, sort_keys=True)), sort_keys=True)

    def block_status(self, b, run=None):
        """{"standard": True / False / None (model not found), "function": "standard" | "intact" | "broken" | "unchecked" | "no-vectors", "detail": ...}.
        A modified block is run on its own in FlexGrid against its model's reference vectors (cached until it changes again)."""
        v = self.blocks[b]
        logic = [k for k in v["logic"] if k in self.grid.nodes]
        sig = self.signature(logic, prefix=b + ".")
        standard = None if v.get("ref") is None else sig == v["ref"]
        if standard:
            return {"standard": True, "function": "standard", "detail": "unchanged from its model"}
        if not v.get("vectors"):
            return {"standard": standard, "function": "no-vectors", "detail": "the model has no reference vectors to check against" if standard is False else "model not found"}
        if v.get("check") and v["check"]["sig"] == sig:
            return dict(v["check"]["result"], standard=standard)
        if run is False or (run is None and len(self.members(b)) > AUTO_CHECK_CELLS):
            return {"standard": standard, "function": "unchecked", "detail": "press Check function"}
        res = self._run_check(b, v["vectors"])
        v["check"] = {"sig": sig, "result": res}
        return dict(res, standard=standard)

    def _run_check(self, b, vec):
        import flex_layout_sim_v1 as fls
        v = self.blocks[b]
        cells = set(self.members(b))
        port_io = {k: io for io, k in v["ports"].items()}
        recs = [IcmV3Record(cell_id=r.cell_id, row=r.row, col=r.col, core=r.core, core_config=r.core_config, addon_config=r.addon_config,
                            io_name=port_io.get(r.cell_id), preload_value=r.preload_value) for r in self.records(file_coords=False) if r.cell_id in cells]
        missing = [io for io in list(vec.get("inputs", {})) + list(vec.get("outputs", {})) if io not in v["ports"]]
        if missing:
            return {"function": "broken", "detail": f"port(s) {', '.join(missing)} no longer exist"}
        try:
            alone = Layout(recs, name=b)
            alone.io = {k: io for k, io in port_io.items() if k in alone.grid.nodes}
            sim = fls.StepSim(alone, width=vec.get("width"))
            sim.run_items({v["ports"][io]: vals for io, vals in vec["inputs"].items()})
        except Exception as e:                          # a block the VM cannot run any more is broken by definition
            return {"function": "broken", "detail": f"it no longer runs: {e.__class__.__name__}: {e}"}
        for io, want in vec["outputs"].items():
            got = sim.seen.get(v["ports"][io], [])
            if got != want:
                i = next((i for i, (x, y) in enumerate(zip(got, want)) if x != y), min(len(got), len(want)))
                return {"function": "broken", "detail": f"output {io}, item {i + 1}: expected {want[i] if i < len(want) else 'nothing'}, got {got[i] if i < len(got) else 'nothing'}"}
        return {"function": "intact", "detail": f"{sum(len(w) for w in vec['outputs'].values())} reference output(s) still match"}

    def check_block(self, b):
        if b not in self.blocks:
            return {"ok": False, "error": f"no block {b}"}
        return dict(self.block_status(b, run=True), ok=True)

    def _relay_of(self, k):
        return next((key for key, v in self.grid.routes.items() if k in v["relays"]), None)

    def is_logic(self, k):
        n = self.grid.nodes.get(k)
        return n is not None and n["core"] != "cross" and self._relay_of(k) is None

    def movable(self, k):
        """A logic cell that is not pinned (a cell inside a block too: editing a block in place is allowed, and its status shows it)."""
        return self.is_logic(k) and k not in self.pinned

    def joins(self, k):
        """Every join touching cell k: [(a, b, second)]."""
        out = [(a, b, v["second"]) for (a, b), v in self.grid.routes.items() if k in (a, b)]
        return out + [t for t in self.tags if k in t[:2] and (t[0], t[1]) not in self.grid.routes]

    # ---- the view ---------------------------------------------------------------------------------------------------------------------
    def snapshot(self):
        g = self.grid
        try:
            t, probs, merges, timing = g.hops(), self.problems(), self.merges(), None
        except (LayoutError, RecursionError) as e:
            t, probs, merges, timing = {}, [], [], str(e)
        recs = {r.cell_id: r for r in self.records(file_coords=False)}
        in_route = {nm: key for key, v in g.routes.items() for nm in v["relays"]}
        srcs = collections.defaultdict(list)
        for (a, b, s), tag in self.tags.items():
            srcs[b].append(a)
        cells, bmap = [], self._block_map()
        for k, n in g.nodes.items():
            if k in in_route and n["core"] != "cross":
                continue
            r = recs[k]
            try:
                latch = f"{icm_v3.encode_super_latch(r.core, r.core_config, r.addon_config):020x}" if r.core in icm_v3.CORE_IDS else None
                bad = None
            except (ValueError, KeyError) as e:
                latch, bad = None, str(e)
            cells.append({"name": k, "r": n["r"], "c": n["c"], "core": n["core"], "hop": t.get(k), "cfg": r.core_config, "addon": n["addon"], "preload": n["preload"],
                          "io": self.io.get(k), "movable": self.movable(k), "pinned": k in self.pinned, "block": bmap.get(k), "latch": latch, "latch_error": bad,
                          "minuend": g.minuend.get(k), "sources": srcs.get(k, [])})
        routes, nxt = [], self._next_map()
        for (a, b), v in g.routes.items():
            tag = self.tags.get((a, b, v["second"]), {"out": ("out",), "in": ("in",)})
            routes.append({"from": a, "to": b, "second": v["second"], "relays": len(v["relays"]), "extra": v["extra"], "crossings": v["crossings"],
                           "points": [list(g.pos(nm)) for nm in self._chain(a, b, v, nxt)], "out": list(tag["out"]), "in": list(tag["in"])})
        loose = [{"a": a, "b": b, "second": s} for a, b, s in g.links if (a, b) not in g.routes and a not in in_route and b not in in_route]
        blocks = []
        for name, v in self.blocks.items():
            mem = self.members(name)
            sq = [g.pos(k) for k in mem]
            if not sq:
                continue
            blocks.append({"name": name, "file": v["file"], "source": v.get("source"), "r0": min(p[0] for p in sq), "c0": min(p[1] for p in sq), "r1": max(p[0] for p in sq),
                           "c1": max(p[1] for p in sq), "cells": len(mem), "status": self.block_status(name),
                           "ports": [{"io": io, "cell": k, "r": g.pos(k)[0], "c": g.pos(k)[1]} for io, k in v["ports"].items() if k in g.nodes]})
        by_core = collections.Counter(n["core"] for n in g.nodes.values())
        return {
            "name": self.name, "rows": g.rows, "cols": g.cols, "offset": list(self.offset),
            "cells": cells, "routes": routes, "links": loose, "blocks": blocks,
            "crossings": [{"name": x, "r": g.nodes[x]["r"], "c": g.nodes[x]["c"], "owner": list(o), "crossing": list(c)} for x, (o, c) in g.crossed.items()],
            "problems": [{"cell": c, "kind": k, "early": x, "late": y} for c, k, x, y in probs],
            "merges": merges,
            "summary": {"cells": len(g.nodes), "by_core": dict(by_core), "routes": len(g.routes), "relays": sum(len(v["relays"]) for v in g.routes.values()),
                        "max_hop": max(t.values(), default=0), "pinned": len(self.pinned), "undo": len(self._undo), "timing_error": timing},
            "warnings": self.warnings[:50],
        }

    def _next_map(self):
        nxt = collections.defaultdict(list)
        for x, y, _ in self.grid.links:
            nxt[x].append(y)
        return nxt

    def _chain(self, a, b, v, nxt=None):
        """The squares of route a -> b in order: a, its relays and crossing tiles, b."""
        g = self.grid
        mine = set(v["relays"]) | set(v["crossings"])
        nxt = nxt or self._next_map()
        chain, cur, seen = [a], a, {a}
        while cur != b:
            step = [y for y in nxt[cur] if (y in mine or y == b) and y not in seen]
            if len(chain) > 1 and g.nodes[cur]["core"] == "cross":
                d = g._dir(g.pos(chain[-2]), g.pos(cur))
                step = [y for y in step if g._dir(g.pos(cur), g.pos(y)) == d] or step
            if not step:
                break
            cur = step[0]
            seen.add(cur)
            chain.append(cur)
        return chain

    def problems(self):
        """The engine's problems(): adder/mul operand ties and minuend order (the generator refuses those)."""
        return list(self.grid.problems())

    def merges(self):
        """Nano cells whose two sources arrive on the SAME tick. That is not a fault: words arriving together are OR-merged (a feature, Alan), so the nano sees one
        merged word; drawn as a note, so a person can tell it from an operand pair that arrives in order."""
        g = self.grid
        srcs, t, out = g.sources(), g.hops(), []
        for c, n in g.nodes.items():
            if n["core"] == "nano" and len(srcs[c]) == 2:
                x, y = srcs[c]
                if t[x] + g.xdelay.get((c, x), 0) == t[y] + g.xdelay.get((c, y), 0):
                    out.append({"cell": c, "a": x, "b": y})
        return out

    def _balance_all(self, limit=60):
        return self.grid.balance(limit)

    # ---- editing: shared machinery ----------------------------------------------------------------------------------------------------
    def _transaction(self, fn):
        """Run an edit; on any LayoutError the layout is restored exactly and the error returned. On success the previous state goes on the undo stack."""
        before = copy.deepcopy({k: v for k, v in self.__dict__.items() if k != "_undo"})
        try:
            out = fn() or {}
        except (LayoutError, StopIteration, RecursionError, ValueError, KeyError) as e:
            self.__dict__.update(before)
            msg = str(e) or e.__class__.__name__
            return {"ok": False, "error": msg.strip("'\"")}
        self._undo.append(before)
        del self._undo[:-UNDO_DEPTH]
        return dict({"ok": True}, **out)

    def _lift(self, keys):
        """Unroute the routes `keys` and every route that crosses them; returns the nets to lay again [(a, b, kwargs)]."""
        g = self.grid
        keys = set(keys)
        while True:
            more = {g.crossed[x][1] for key in keys for x in g.routes[key]["relays"] if x in g.crossed}
            if more <= keys:
                break
            keys |= more
        nets = []
        while keys:
            ready = [key for key in keys if not any(nm in g.crossed for nm in g.routes[key]["relays"])]
            if not ready:
                raise LayoutError("routes cross each other in a cycle: cannot lift them")
            for key in ready:
                rec = g.unroute(*key)
                nets.append((key[0], key[1], {"second": rec["second"]} if rec["second"] else {}))
                keys.discard(key)
        return nets

    def _move_group(self, names, dr, dc):
        """Move the cells `names` (and the relays of routes wholly inside the group) by (dr, dc); routes with one end outside are lifted and laid again; then balance."""
        g = self.grid
        names = set(names)
        inside = [k for k in g.routes if k[0] in names and k[1] in names]
        cut = [k for k in g.routes if (k[0] in names) != (k[1] in names)]
        for key in inside:                                    # a route inside the group that another route crosses: lift that one too
            cut += [g.crossed[x][1] for x in g.routes[key]["relays"] if x in g.crossed and g.crossed[x][1] not in inside]
            cut += [g.crossed[x][0] for x in g.routes[key]["crossings"] if x in g.crossed and g.crossed[x][0] not in inside]
        relays = {nm for v in g.routes.values() for nm in v["relays"]}
        for a, b, _ in g.links:                               # a plain (pinned) link across the group's edge cannot be laid again
            if (a in names) != (b in names) and (a, b) not in g.routes and a not in relays and b not in relays:
                raise LayoutError(f"{a} -> {b} is fixed wiring (pinned) across the move")
        moving = set(names) | {nm for key in inside for nm in g.routes[key]["relays"] + g.routes[key]["crossings"]}
        nets = self._lift(set(cut))
        at = g.at()
        for k in moving:
            sq = (g.nodes[k]["r"] + dr, g.nodes[k]["c"] + dc)
            if not (0 <= sq[0] < g.rows and 0 <= sq[1] < g.cols):
                raise LayoutError(f"({sq[0]},{sq[1]}) is off the board")
            if at.get(sq) is not None and at[sq] not in moving:
                raise LayoutError(f"({sq[0]},{sq[1]}) is taken by {at[sq]}")
        for k in moving:
            g.nodes[k]["r"] += dr
            g.nodes[k]["c"] += dc
        if nets:
            g.route_nets(nets, rounds=60)
        detours = self._balance_all()
        return {"rerouted": [f"{a} -> {b}" for a, b, _ in nets], "detours": detours}

    # ---- editing: the public operations ------------------------------------------------------------------------------------------------
    def move(self, name, r, c, whole_block=True):
        """Move logic cell `name` to layout square (r, c): its routes are lifted, laid again and the layout re-balanced, or the move is refused and nothing changes.
        A cell inside a block moves its whole block, unless whole_block is False (editing the block in place)."""
        g = self.grid
        if name not in g.nodes:
            return {"ok": False, "error": f"no cell {name}"}
        if whole_block and self.block_of(name):
            return self.move_block(self.block_of(name), r - g.nodes[name]["r"], c - g.nodes[name]["c"], relative=True)
        if not self.movable(name):
            why = "a relay of a route (move the cells at its ends)" if self._relay_of(name) else "pinned: it is wired by fields the layout engine does not derive" if name in self.pinned else "not movable"
            return {"ok": False, "error": f"{name} is {why}"}
        if not (0 <= r < g.rows and 0 <= c < g.cols):
            return {"ok": False, "error": f"({r},{c}) is off the board"}
        if (r, c) == g.pos(name):
            return {"ok": True, "rerouted": [], "detours": 0}
        occ = g.at().get((r, c))
        if occ is not None and not any(occ in g.routes[k]["relays"] for k in g.routes if name in k):
            return {"ok": False, "error": f"({r},{c}) is taken by {occ}"}
        return self._transaction(lambda: self._move_group([name], r - g.nodes[name]["r"], c - g.nodes[name]["c"]))

    def add_cell(self, core, r, c, name=None, cfg=None, addon=None, preload=None, io=None, block=None):
        """Place a new cell; `block` makes it part of that block (an edit to the block, which its status then shows)."""
        g = self.grid
        if block is not None and block not in self.blocks:
            return {"ok": False, "error": f"no block {block}"}
        if core not in icm_v3.CORE_IDS or core == "cross":
            return {"ok": False, "error": f"unknown core {core!r}" if core != "cross" else "a crossing tile is made by routing, not placed"}
        if name is None:
            n = 1
            while f"{SHORT[core]}{n}" in g.nodes:
                n += 1
            name = f"{SHORT[core]}{n}"
        name = str(name).strip()
        if not name or name in g.nodes or any(ch in name for ch in " \t\"'<>"):
            return {"ok": False, "error": f"cell name {name!r} is empty, taken or has a space/quote"}

        def do():
            if g.at().get((r, c)) is not None or not (0 <= r < g.rows and 0 <= c < g.cols):
                raise LayoutError(f"({r},{c}) is " + ("taken" if g.at().get((r, c)) else "off the board"))
            g.add(name, r, c, core=core, cfg={"ready": 1} if core == "nano" else {}, addon={}, preload=None)     # a nano with ready=0 never fires
            self._present[name] = set()
            if block is not None:
                self.blocks[block]["logic"].append(name)
            res = self._configure(name, cfg or {}, addon or {}, preload, io)
            return dict(res, name=name)
        return self._transaction(do)

    def _configure(self, name, cfg, addon, preload, io):
        g = self.grid
        n = g.nodes[name]
        core = n["core"]
        dirs = set(dir_fields(core))
        bad = [k for k in cfg if k in dirs]
        if bad:
            raise LayoutError(f"{', '.join(bad)} come from the joins: join the cell instead of setting faces")
        unknown = set(icm_v3.canonical_core_config(core, cfg)) - set(table(core))
        if unknown:
            raise LayoutError(f"{core} has no field(s) {sorted(unknown)}")
        newcfg = dict(n["cfg"])
        for k, v in icm_v3.canonical_core_config(core, cfg).items():
            if v in (None, "", 0) and k not in self._present.get(name, ()):
                newcfg.pop(k, None)
            else:
                newcfg[k] = int(v)
        newaddon = dict(n["addon"])
        for k, v in (addon or {}).items():
            if v in (None, "", 0):
                newaddon.pop(k, None)
            else:
                newaddon[k] = int(v)
        n["cfg"], n["addon"] = newcfg, newaddon
        if preload is not None:
            n["preload"] = None if preload in ("", "none", False) else int(preload) & 0xFFFFFFFF
        if io is not None:
            io = str(io).strip()
            if io and any(v == io for k, v in self.io.items() if k != name):
                raise LayoutError(f"io name {io!r} is already used")
            if io:
                self.io[name] = io
            else:
                self.io.pop(name, None)
        rec = next(r for r in self.records(file_coords=False) if r.cell_id == name)
        latch = icm_v3.encode_super_latch(rec.core, rec.core_config, rec.addon_config)     # raises ValueError on a value too wide for its field
        return {"latch": f"{latch:020x}"}

    def set_config(self, name, cfg=None, addon=None, preload=None, io=None):
        if name not in self.grid.nodes or not self.is_logic(name):
            return {"ok": False, "error": f"no cell {name} (relays are configured by their route)"}
        if name in self.pinned:
            return {"ok": False, "error": f"{name} is pinned: its wiring fields are kept exactly as the file had them"}
        return self._transaction(lambda: self._configure(name, cfg or {}, addon or {}, preload, io))

    def join(self, a, b, out=None, role=None):
        """Join a's output port `out` to b's input role `role`: a route laid by the engine (a direct link when they are neighbours)."""
        g = self.grid
        for k in (a, b):
            if k not in g.nodes or not self.is_logic(k):
                return {"ok": False, "error": f"no cell {k} to join (relays belong to their route)"}
        if a == b:
            return {"ok": False, "error": "a cell cannot be joined to itself"}
        ca, cb = g.nodes[a]["core"], g.nodes[b]["core"]
        out = out or out_ports(ca)[0] if out_ports(ca) else out
        role = role or (in_roles(cb)[0] if in_roles(cb) else None)
        if out not in out_ports(ca):
            return {"ok": False, "error": f"a {ca} has no output port {out!r} (ports: {', '.join(out_ports(ca)) or 'none'})"}
        if role not in in_roles(cb):
            return {"ok": False, "error": f"a {cb} has no input {role!r} (inputs: {', '.join(in_roles(cb)) or 'none'})"}
        for k in (a, b):
            if k in self.pinned:
                return {"ok": False, "error": f"{k} is pinned: its wiring is kept exactly as the file had it"}
        second = out == "second"
        key = (a, b, second)
        if (a, b) in g.routes:
            if g.routes[(a, b)]["second"] != second:
                return {"ok": False, "error": f"{a} -> {b} is already joined by the other word; the engine keeps one route per pair of cells"}

            def merge():
                tag = self.tags.setdefault(key, {"out": ("second",) if second else ("out",), "in": ("in",)})
                tag["out"] = tuple(dict.fromkeys(tag["out"] + (out,)))
                tag["in"] = tuple(dict.fromkeys(tag["in"] + (role,)))
                self._configure(b, {}, {}, None, None)
                return {"joined": f"{a} -> {b}", "merged": True}
            return self._transaction(merge)
        if cb == "branch" and any(t[1] == b for t in self.tags):
            return {"ok": False, "error": f"{b} is a branch: it has ONE input (upstream_dir), already joined"}

        def do():
            try:
                names = g.route(a, b, second=second)
            except LayoutError:
                names = g.route(a, b, second=second, cross=True)
            self.tags[key] = {"out": (out,), "in": (role,)}
            if second and not g.nodes[a]["cfg"].get("second_output"):
                g.nodes[a]["cfg"]["second_output"] = 1           # the second word is only produced when asked for
            for k in (a, b):
                self._configure(k, {}, {}, None, None)
            return {"joined": f"{a} -> {b}", "relays": len(names)}
        return self._transaction(do)

    def unjoin(self, a, b):
        g = self.grid
        if (a, b) not in g.routes:
            return {"ok": False, "error": f"no route {a} -> {b}" + (" (pinned wiring is kept as the file had it)" if any(t[:2] == (a, b) for t in self.tags) else "")}

        def do():
            second = g.routes[(a, b)]["second"]
            nets = [n for n in self._lift({(a, b)}) if (n[0], n[1]) != (a, b)]
            self.tags.pop((a, b, second), None)
            if nets:
                g.route_nets(nets, rounds=60)
            return {"unjoined": f"{a} -> {b}"}
        return self._transaction(do)

    def delete_cell(self, name):
        g = self.grid
        if name not in g.nodes or not self.is_logic(name):
            return {"ok": False, "error": f"no cell {name} to delete (a relay goes with its route: delete the join)"}
        if name in self.pinned and any(name in t[:2] for t in self.tags):
            return {"ok": False, "error": f"{name} is pinned with fixed wiring: it cannot be deleted alone"}

        def do():
            self._delete([name])
            return {"deleted": name}
        return self._transaction(do)

    def _delete(self, names):
        g = self.grid
        names = set(names)
        mine = {k for k in g.routes if k[0] in names or k[1] in names}
        nets = [n for n in self._lift(mine) if n[0] not in names and n[1] not in names]
        for t in [t for t in self.tags if t[0] in names or t[1] in names]:
            del self.tags[t]
        g.links = [l for l in g.links if l[0] not in names and l[1] not in names]
        for k in names:
            del g.nodes[k]
            g.minuend.pop(k, None)
            for d in (self.io, self.ext, self._orig_cfg, self._present):
                d.pop(k, None)
            self.pinned.discard(k)
        for c in [c for c, m in g.minuend.items() if m in names]:
            del g.minuend[c]
        for v in self.blocks.values():                        # a deleted cell leaves its block (and a deleted port leaves the block's ports)
            v["logic"] = [k for k in v["logic"] if k not in names]
            v["ports"] = {io: k for io, k in v["ports"].items() if k not in names}
        if nets:
            g.route_nets(nets, rounds=60)

    def set_minuend(self, cell, source):
        """Declare which joined source of a subtracting adder must arrive FIRST (the minuend); balance() then enforces it."""
        g = self.grid
        if cell not in g.nodes or g.nodes[cell]["core"] not in PAIR:
            return {"ok": False, "error": f"{cell} is not an adder or multiplier"}
        if source and not any(t[0] == source and t[1] == cell for t in self.tags):
            return {"ok": False, "error": f"{source} is not joined to {cell}"}

        def do():
            if source:
                g.minuend[cell] = source
            else:
                g.minuend.pop(cell, None)
            return {"detours": self._balance_all()}
        return self._transaction(do)

    def balance(self):
        return self._transaction(lambda: {"detours": self._balance_all()})

    def undo(self):
        if not self._undo:
            return {"ok": False, "error": "nothing to undo"}
        self.__dict__.update(self._undo.pop())
        return {"ok": True}

    # ---- blocks: a saved design placed as one unit ------------------------------------------------------------------------------------
    def place_block(self, path, r, c, name=None, as_components=False, source=None):
        """Insert the ICM file at `path` with its top-left at layout square (r, c). Its io_name cells become the block's ports. as_components=True places the same
        cells as ordinary cells (no block). The block remembers its model's signature and reference vectors (`<model>.test.json`) for the standard / function checks."""
        try:
            doc, recs, _ = read_design(path)                  # a model that itself holds blocks comes in flat: blocks do not nest
        except Exception as e:                              # a bad file is a refusal, not a crash
            return {"ok": False, "error": f"cannot read {os.path.basename(path)}: {e}"}
        if not recs:
            return {"ok": False, "error": "the file has no cells"}
        base = re.sub(r"(\.icm-hier|\.icm)?\.json$|\.icm$", "", os.path.basename(path))
        base = re.sub(r"[^A-Za-z0-9_]", "_", base)[:16] or "block"
        if name is None:
            n = 1
            while f"{base}_{n}" in self.blocks or any(k.startswith(f"{base}_{n}.") for k in self.grid.nodes):
                n += 1
            name = f"{base}_{n}"
        if name in self.blocks or any(k.startswith(name + ".") for k in self.grid.nodes):
            return {"ok": False, "error": f"block name {name} is taken"}
        r0, c0 = min(x.row for x in recs), min(x.col for x in recs)
        orow, ocol = self.offset
        new = [IcmV3Record(cell_id=f"{name}.{x.cell_id}", row=r + (x.row - r0) - orow, col=c + (x.col - c0) - ocol, core=x.core, core_config=dict(x.core_config or {}),
                           addon_config=dict(x.addon_config or {}), io_name=None, preload_value=x.preload_value) for x in recs]
        g = self.grid
        at = g.at()
        for x in new:
            sq = (x.row + orow, x.col + ocol)
            if not (0 <= sq[0] < g.rows and 0 <= sq[1] < g.cols):
                return {"ok": False, "error": f"the block does not fit: ({sq[0]},{sq[1]}) is off the board"}
            if sq in at:
                return {"ok": False, "error": f"the block does not fit: ({sq[0]},{sq[1]}) is taken by {at[sq]}"}
        ports = {x.io_name: f"{name}.{x.cell_id}" for x in recs if x.io_name}
        try:
            ref, vec = model_reference(path)
        except Exception:                                   # no reference: the block is placed, its status says "model not found"
            ref, vec = None, None

        def do():
            if as_components:
                self._rebuild(self.records(file_coords=True) + new)
                return {"components": len(new), "prefix": name + "."}
            self._rebuild(self.records(file_coords=True) + new, extra_blocks={name: {"file": os.path.basename(path), "cells": [x.cell_id for x in new], "ports": ports,
                                                                                      "ref": ref, "vectors": vec, "source": source}})
            return {"block": name, "ports": sorted(ports)}
        return self._transaction(do)

    def _rebuild(self, recs, extra_blocks=None):
        """Re-import `recs` on the same board (positions in file coordinates), keeping the blocks, declared minuends and names."""
        keep = {"name": self.name, "description": self.description, "min_bit_width": self.min_bit_width, "blocks": dict(self.blocks, **(extra_blocks or {}))}
        minuends = dict(self.grid.minuend)
        board = (self.grid.rows, self.grid.cols, self.offset)
        warnings = list(self.warnings)
        self._relay_floor = self.grid._relay
        self.warnings = []
        self._build(recs, board, anchors={k for v in keep["blocks"].values() for k in v["ports"].values()})
        self.__dict__.update(keep)
        self.blocks = self._adopt_blocks(self.blocks)
        self.warnings = warnings + self.warnings
        for c, m in minuends.items():
            if c in self.grid.nodes and m in self.grid.nodes:
                self.grid.minuend[c] = m

    def move_block(self, name, r, c, relative=False):
        """Move block `name` so its top-left is at (r, c) (or by (r, c) when relative): its inside is carried as it is, its joins to the outside are laid again."""
        if name not in self.blocks:
            return {"ok": False, "error": f"no block {name}"}
        g = self.grid
        cells = [k for k in self.blocks[name]["logic"] if k in g.nodes]
        if not relative:
            r -= min(g.nodes[k]["r"] for k in cells)
            c -= min(g.nodes[k]["c"] for k in cells)
        if (r, c) == (0, 0):
            return {"ok": True, "rerouted": [], "detours": 0}
        return self._transaction(lambda: self._move_group(cells, r, c))

    def unpack_block(self, name):
        if name not in self.blocks:
            return {"ok": False, "error": f"no block {name}"}

        def do():
            n = len(self.members(name))
            self.blocks.pop(name)
            return {"unpacked": name, "cells": n}
        return self._transaction(do)

    def delete_block(self, name):
        if name not in self.blocks:
            return {"ok": False, "error": f"no block {name}"}

        def do():
            g = self.grid
            logic = [k for k in self.blocks[name]["logic"] if k in g.nodes]
            mine = set(logic)
            fixed = {k for a, z, _ in g.links for k in (a, z) if k not in mine and not self.is_logic(k) and self._relay_of(k) is None
                     and all(x in mine or not self.is_logic(x) for x in (a, z))}      # relays of fixed (pinned) chains inside the block
            self.blocks.pop(name)
            self._delete(logic)
            left = {k for k in fixed if k in g.nodes}
            g.links = [l for l in g.links if l[0] not in left and l[1] not in left]
            for k in left:
                del g.nodes[k]
                self.pinned.discard(k)
                self._orig_cfg.pop(k, None)
            return {"deleted": name}
        return self._transaction(do)

    # ---- export -----------------------------------------------------------------------------------------------------------------------
    def records(self, file_coords=True):
        """ICM v3 records: every direction field derived from the joins (plus faces leaving the design), pinned cells exactly as read."""
        g = self.grid
        orow, ocol = self.offset if file_coords else (0, 0)
        out_tag, in_tag, nxt = {}, {}, self._next_map()
        for (a, b), v in g.routes.items():
            tag = self.tags.get((a, b, v["second"]), {"out": ("second",) if v["second"] else ("out",), "in": ("in",)})
            chain = self._chain(a, b, v, nxt)
            if len(chain) >= 2:
                out_tag[(a, chain[1], v["second"] if len(chain) > 1 else False)] = tag["out"]
                in_tag[(chain[-2], b)] = tag["in"]
        for (a, b, s), tag in self.tags.items():
            if (a, b) not in g.routes:
                out_tag.setdefault((a, b, s), tag["out"])
        raw_in = {}
        for (a, b, s), tag in self.tags.items():
            if (a, b) not in g.routes:
                raw_in[(a, b)] = tag["in"]
        faces = collections.defaultdict(lambda: collections.defaultdict(list))
        for a, b, s in g.links:
            d = g._dir(g.pos(a), g.pos(b))
            ca, cb = g.nodes[a]["core"], g.nodes[b]["core"]
            ports = out_tag.get((a, b, s)) or (("second",) if s else ("out",))
            for p in ports:
                f = out_field(ca, p) if ca in icm_v3.CORE_IDS else "downstream_mask"
                if f and d not in faces[a][f]:
                    faces[a][f].append(d)
            for role in in_tag.get((a, b)) or raw_in.get((a, b)) or ("in",):
                f = in_field(cb, role) if cb in icm_v3.CORE_IDS else "upstream_mask"
                if f and OPP[d] not in faces[b][f]:
                    faces[b][f].append(OPP[d])
        out = []
        for k, n in g.nodes.items():
            if k in self._orig_cfg:
                cfg = dict(self._orig_cfg[k])
            else:
                cfg = dict(n["cfg"])
                fs = faces.get(k, {})
                present = self._present.get(k)
                for f in dir_fields(n["core"]):
                    v = list(fs.get(f, []))
                    v += [d for d in self.ext.get(k, {}).get(f, []) if d not in v]
                    if f == "upstream_dir":
                        if len(v) > 1:
                            raise LayoutError(f"{k}: a branch has one input, joined from {len(v)} faces")
                        if v:
                            cfg[f] = "nsew".index(v[0])
                        continue
                    if v or (present is not None and f in present) or (present is None and f in ("upstream_mask", "downstream_mask")):
                        cfg[f] = v
            out.append(IcmV3Record(cell_id=k, row=n["r"] - orow, col=n["c"] - ocol, core=n["core"], core_config=cfg, addon_config=dict(n["addon"] or {}),
                                   io_name=self.io.get(k), preload_value=n["preload"]))
        return out

    def to_vix(self):
        """The design as ICM-VIX: the cells outside any block are pattern `top` (placed at 0,0); each block is a placement of a pattern named after its library model,
        so blocks survive a save. A block's ports keep their io names in the pattern and are cleared per placement (they are joins inside this design, not its own io)."""
        import icm_vix_v1 as vix
        recs = self.records()
        inblock = self._block_map()
        top = [r for r in recs if r.cell_id not in inblock]
        patterns, placements, seen = {}, [], {}

        def cell(r, r0, c0, cid, io):
            return vix.HierCell(cell_id=cid, rel_row=r.row - r0, rel_col=r.col - c0, core=r.core, core_config=dict(r.core_config), addon_config=dict(r.addon_config or {}),
                                io_name=io, preload_value=r.preload_value)
        patterns[TOP] = vix.HierPattern(cells=[cell(r, 0, 0, r.cell_id, r.io_name) for r in top])
        placements.append(vix.HierPlacement(instance=TOP, pattern=TOP, at=(0, 0)))
        for b, v in self.blocks.items():
            mine = [r for r in recs if inblock.get(r.cell_id) == b]
            if not mine:
                continue
            r0, c0 = min(r.row for r in mine), min(r.col for r in mine)
            port_io = {cid: io for io, cid in v["ports"].items()}
            pat = vix.HierPattern(cells=[cell(r, r0, c0, r.cell_id[len(b) + 1:], port_io.get(r.cell_id, r.io_name)) for r in mine])
            key = json.dumps(pat.to_dict(), sort_keys=True)
            base = re.sub(r"(\.icm-hier|\.icm)?\.json$|\.icm$", "", v["file"]) or "block"
            if key not in seen:
                name, n = base, 1
                while name in patterns:
                    n += 1
                    name = f"{base}~{n}"
                patterns[name], seen[key] = pat, name
            over = {r.cell_id[len(b) + 1:]: {"io_name": None} for r in mine if r.cell_id in port_io}
            placements.append(vix.HierPlacement(instance=b, pattern=seen[key], at=(r0, c0), overrides=over))
        return vix.IcmVixFile(patterns=patterns, placements=placements, name=self.name, description=self.description or "made in the Composer (tools/flex_layout_view_v1.py)",
                              min_bit_width=self.min_bit_width)

    def save(self, path, fmt=None):
        """ICM v3 (flat), or ICM-VIX when the design holds blocks (fmt="vix"/"v3" to choose)."""
        fmt = fmt or ("vix" if self.blocks else "v3")
        if fmt == "vix":
            self.to_vix().save(path)
        else:
            IcmV3File(name=self.name, records=self.records(), description=self.description or "made in the Composer (tools/flex_layout_view_v1.py)",
                      min_bit_width=self.min_bit_width).save(path)
        return path


TOP = "top"
NANO_DIR = os.path.join(TOOLS_DIR, "..", "nano")
# where a block's model is looked for by name (to tell whether a block is still standard after a reload): the standard library, the user's library, the examples
LIBRARY_DIRS = [os.path.join(NANO_DIR, "library_std"), os.environ.get("IMAGO_LIBRARY", os.path.join(NANO_DIR, "library")), os.path.join(NANO_DIR, "examples")]
AUTO_CHECK_CELLS = 600          # a modified block up to this size is re-checked after every edit; a larger one when asked (Check function)
_REF_CACHE = {}


def vectors_path(model_path):
    """The reference test vectors that travel with a library model: `<model>.test.json` beside it."""
    return re.sub(r"(\.icm-hier|\.icm)?\.json$|\.icm$", "", model_path) + ".test.json"


def find_model(file_name):
    for d in LIBRARY_DIRS:
        p = os.path.join(d, os.path.basename(file_name))
        if os.path.isfile(p):
            return p
    return None


def model_reference(path):
    """(signature, vectors) of a library model file, cached by path and modification time. The signature is what a block placed from it must still match to be standard."""
    try:
        key = (os.path.abspath(path), os.path.getmtime(path))
    except OSError:
        return None, None
    if key not in _REF_CACHE:
        lay = Layout.load(path)
        vec = None
        vp = vectors_path(path)
        if os.path.isfile(vp):
            with open(vp) as f:
                vec = json.load(f)
        _REF_CACHE[key] = (lay.signature([k for k in lay.grid.nodes if lay.is_logic(k)], prefix=""), vec)
    return _REF_CACHE[key]


def make_vectors(layout, inputs=None, n=8, seed=1):
    """Reference test vectors for a design: its io inputs fed `inputs` ({io: [values]}, or n deterministic values each), its io outputs as FlexGrid gives them.
    These are the model's own behaviour, recorded, so a later copy can be checked against it."""
    import random
    import flex_layout_sim_v1 as fls
    sim = fls.StepSim(layout)
    io_of = {k: layout.io.get(k) or k for k in sim.inputs}
    rng = random.Random(seed)
    top = (1 << min(sim.width, 16)) - 1
    if inputs is None:
        inputs = {io_of[k]: [0, 1, 2, 3][: min(n, 4)] + [rng.randint(0, top) for _ in range(max(0, n - 4))] for k in sim.inputs}
    cell_of = {io: k for k, io in io_of.items()}
    sim.run_items({cell_of[io]: list(v) for io, v in inputs.items() if io in cell_of})
    return {"width": sim.width, "inputs": {io: list(v) for io, v in inputs.items()},
            "outputs": {layout.io.get(k) or k: list(sim.seen[k]) for k in sim.outputs}}


def save_model(layout, path, vectors=None, fmt=None):
    """Save a design as a library model: the ICM file and, beside it, its reference test vectors (recorded now if not given)."""
    layout.save(path, fmt)
    vec = vectors if vectors is not None else make_vectors(layout)
    with open(vectors_path(path), "w") as f:
        json.dump(vec, f, indent=1)
    return path, vec


def read_design(path):
    """(doc, records, blocks) from any ICM file. An ICM-VIX file the Composer saved (it has a placement named `top`) gives its blocks back: every other placement is a block
    whose ports are its pattern's io-named cells; the `top.` prefix is taken off the other cells' ids. Any other file has no blocks."""
    doc, recs = nl.load_records(path)
    blocks = {}
    pls = getattr(doc, "placements", None) or []
    if any(p.instance == TOP for p in pls):
        strip = TOP + "."
        recs = [IcmV3Record(cell_id=r.cell_id[len(strip):] if r.cell_id.startswith(strip) else r.cell_id, row=r.row, col=r.col, core=r.core, core_config=r.core_config,
                            addon_config=r.addon_config, io_name=r.io_name, preload_value=r.preload_value) for r in recs]
        for p in pls:
            if p.instance == TOP:
                continue
            pat = doc.patterns[p.pattern]
            blocks[p.instance] = {"file": p.pattern.split("~")[0] + ".icm.json", "cells": [f"{p.instance}.{c.cell_id}" for c in pat.cells],
                                  "ports": {c.io_name: f"{p.instance}.{c.cell_id}" for c in pat.cells if c.io_name}}
    return doc, recs, blocks


# ---- layouts built by Python (the fp tools): a name -> records -------------------------------------------------------------------------------
def _fp_add(fmt_name):
    def build():
        import fp_assembler_v1 as fa
        import fp_add_v1 as fadd
        g = Grid(rows=34, cols=330)
        fadd.fp_add(g, getattr(fa, fmt_name))
        g.balance()
        return g.records()
    return build


BUILDERS = {"fp_add/fp16": _fp_add("FP16"), "fp_add/bf16": _fp_add("BF16"), "fp_add/fp32": _fp_add("FP32")}


def from_builder(name):
    if name not in BUILDERS:
        raise LayoutError(f"unknown builder {name}: one of {', '.join(BUILDERS)}")
    return Layout(BUILDERS[name](), name=name)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("path", nargs="?")
    ap.add_argument("--builder", choices=sorted(BUILDERS))
    ap.add_argument("--json", metavar="OUT", help="write the snapshot JSON here ('-' = stdout)")
    a = ap.parse_args(argv)
    if not a.path and not a.builder:
        ap.error("give an ICM file or --builder")
    lay = from_builder(a.builder) if a.builder else Layout.load(a.path)
    snap = lay.snapshot()
    if a.json:
        txt = json.dumps(snap, indent=1)
        if a.json == "-":
            print(txt)
        else:
            open(a.json, "w").write(txt)
        return 0
    s = snap["summary"]
    print(f"{snap['name']}: {s['cells']} cells {s['by_core']}, {s['routes']} routes ({s['relays']} relays), {len(snap['crossings'])} crossings, "
          f"max hop {s['max_hop']}, {len(snap['problems'])} problems, {s['pinned']} pinned, movable {sum(c['movable'] for c in snap['cells'])}")
    for w in snap["warnings"]:
        print("  warning:", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
