"""experimental/three_d/composer3d_v1.py -- a SEPARATE Composer for the six-face (3D) toy grid.  VM ONLY, an exploration (ledger #1312).

REAL, HONEST SCOPE. There is no 3D hardware, no 3D RTL and no card to run any of this on (see README.md and CELL_AUDIT_6_FACE.md in this folder). This tool edits and runs designs in the toy model
`experimental_3d_nor_v2.py` (relay cells with the shift add-on, and gate cells AND / OR / XOR / NOR / NAND / XNOR, six faces N S E W U D, one tick per cell, no flow control). It does NOT read or write ICM files and
is not connected to the main Composer (`nano/composer_page_v1.py`), the layout engine or any generator; its design files are its own (`imago-3d-design`, version 1) and nothing else can load them.

What it is for: laying a design out over a variable number of layers and SEEING it. The page shows
  * the FLOOR PLAN of one layer (where you place, join and delete cells), with the layers above and below faded in behind it;
  * a ROTATABLE 3D VIEW of the whole stack;
  * a DEPTH SLIDER that chooses the current layer: that layer is shown in full and everything on other layers is faded (how much is a setting);
  * a stepper that runs the design in the same tick model as `Grid3.run` (checked equal in tests/vm/test_composer3d_v1.py).

    python3 experimental/three_d/composer3d_v1.py                 # serve on http://127.0.0.1:7422 and open it
    python3 experimental/three_d/composer3d_v1.py --example adder --no-browser
    python3 experimental/three_d/composer3d_v1.py --open my_design.3d.json
"""
import argparse
import copy
import http.server
import json
import os
import random
import re
import sys
import threading
import webbrowser
from collections import defaultdict, deque

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in (os.path.join(REPO, "tools"), os.path.join(REPO, "nano"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import experimental_3d_nor_v2 as m3  # noqa: E402  (the six-neighbour toy; gate / shift / relay behaviour)
import ui_theme_v1 as ui  # noqa: E402  (the one shared look)

PORT = 7422
M32 = m3.M32
FACE_NAMES = "NSEWUD"                      # index = the face's number in the toy: N=0 S=1 E=2 W=3 U=4 D=5 (U / D are the new faces)
FACE_INDEX = {f: i for i, f in enumerate(FACE_NAMES)}
DELTA = m3.DELTA
OPP = m3.OPP
GATES = tuple(m3.GATES)                    # AND OR XOR NOR NAND XNOR
KINDS = ("relay", "gate")
FORMAT = "imago-3d-design"
NAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,24}$")
LIMITS = {"rows": (1, 40), "cols": (1, 40), "layers": (1, 24)}
MAX_ROUTE = 80
MAX_TICKS = 2000


class DesignError(ValueError):
    """A refused edit: nothing was changed."""


def _add(pos, d):
    dr, dc, dl = DELTA[d]
    return (pos[0] + dr, pos[1] + dc, pos[2] + dl)


def key(pos):
    return "%d,%d,%d" % tuple(pos)


def shifted(node, v):
    """The shift add-on exactly as `Cell3.shifted` does it."""
    if not node["shift"]:
        return v & M32
    return (v << node["shift"]) & M32 if node["left"] else (v >> node["shift"]) & M32


# ----------------------------------------------------------------------------------------------------------------------------- the design
class Design:
    def __init__(self, rows=10, cols=10, layers=4):
        self.rows, self.cols, self.layers = rows, cols, layers
        self.nodes = {}                    # (row, col, layer) -> {name, kind, gate, shift, left, down: set of face numbers}
        self.description = ""
        self.meta = {}
        self._undo = []

    # ---- housekeeping
    def _snap(self):
        return copy.deepcopy((self.rows, self.cols, self.layers, self.nodes, self.description, self.meta))

    def _push(self):
        self._undo.append(self._snap())
        del self._undo[:-100]

    def undo(self):
        if not self._undo:
            raise DesignError("nothing to undo")
        self.rows, self.cols, self.layers, self.nodes, self.description, self.meta = self._undo.pop()

    def inside(self, pos):
        return len(pos) == 3 and 0 <= pos[0] < self.rows and 0 <= pos[1] < self.cols and 0 <= pos[2] < self.layers

    def _check_pos(self, pos):
        pos = tuple(int(x) for x in pos)
        if not self.inside(pos):
            raise DesignError("square %s is outside the %dx%dx%d board" % (pos, self.rows, self.cols, self.layers))
        return pos

    def name_of(self, pos):
        return self.nodes[pos]["name"]

    def pos_of(self, name):
        for p, n in self.nodes.items():
            if n["name"] == name:
                return p
        raise DesignError("no cell named %r" % name)

    def _auto_name(self, prefix="c"):
        used = {n["name"] for n in self.nodes.values()}
        i = 1
        while "%s%d" % (prefix, i) in used:
            i += 1
        return "%s%d" % (prefix, i)

    @staticmethod
    def _clean(kind, gate, shift, left):
        if kind not in KINDS:
            raise DesignError("kind must be one of %s" % ", ".join(KINDS))
        if kind == "gate":
            gate = gate or "AND"
            if gate not in GATES:
                raise DesignError("gate must be one of %s" % ", ".join(GATES))
        else:
            gate = None
        shift = int(shift or 0)
        if not 0 <= shift <= 31:
            raise DesignError("shift must be 0 to 31")
        return kind, gate, shift, bool(left)

    # ---- edits (each is one undo step; a refused edit changes nothing)
    def place(self, pos, kind="relay", gate=None, shift=0, left=True, name=None):
        pos = self._check_pos(pos)
        if pos in self.nodes:
            raise DesignError("square %s is already used by %s" % (pos, self.nodes[pos]["name"]))
        kind, gate, shift, left = self._clean(kind, gate, shift, left)
        if kind == "gate" and shift:
            raise DesignError("a gate has no shift add-on in this model (use a relay after it)")
        if name is None:
            name = self._auto_name("g" if kind == "gate" else "r")
        elif not NAME_RE.match(name) or any(n["name"] == name for n in self.nodes.values()):
            raise DesignError("the name %r is not valid or is already used" % name)
        self._push()
        self.nodes[pos] = {"name": name, "kind": kind, "gate": gate, "shift": shift, "left": left, "down": set()}
        return pos

    def delete(self, pos):
        pos = self._check_pos(pos)
        if pos not in self.nodes:
            raise DesignError("nothing at %s" % (pos,))
        self._push()
        del self.nodes[pos]

    def set_cell(self, pos, name=None, kind=None, gate=None, shift=None, left=None):
        pos = self._check_pos(pos)
        if pos not in self.nodes:
            raise DesignError("nothing at %s" % (pos,))
        n = self.nodes[pos]
        new_kind = kind if kind is not None else n["kind"]
        new_gate = gate if gate is not None else n["gate"]
        new_shift = shift if shift is not None else n["shift"]
        new_left = left if left is not None else n["left"]
        new_kind, new_gate, new_shift, new_left = self._clean(new_kind, new_gate, new_shift, new_left)
        if new_kind == "gate" and new_shift:
            new_shift = 0
        if name is not None and name != n["name"]:
            if not NAME_RE.match(name) or any(o["name"] == name for p, o in self.nodes.items() if p != pos):
                raise DesignError("the name %r is not valid or is already used" % name)
        self._push()
        if name is not None:
            n["name"] = name
        n.update(kind=new_kind, gate=new_gate, shift=new_shift, left=new_left)

    def set_face(self, pos, face, on):
        pos = self._check_pos(pos)
        if pos not in self.nodes:
            raise DesignError("nothing at %s" % (pos,))
        f = FACE_INDEX.get(face)
        if f is None:
            raise DesignError("face must be one of N S E W U D")
        if on and _add(pos, f) not in self.nodes:
            raise DesignError("there is no cell on the %s face of %s to send to" % (face, self.nodes[pos]["name"]))
        self._push()
        (self.nodes[pos]["down"].add if on else self.nodes[pos]["down"].discard)(f)

    def link(self, src, dst, route=True, any_layer=True):
        """Join src's output to dst. Adjacent cells: one face. Otherwise (route=True) a shortest chain of relay cells is laid through free squares (any layer, or only src's layer)."""
        src, dst = self._check_pos(src), self._check_pos(dst)
        if src not in self.nodes or dst not in self.nodes:
            raise DesignError("both ends of a join must be cells")
        if src == dst:
            raise DesignError("a cell cannot be joined to itself")
        d = next((k for k in range(6) if _add(src, k) == dst), None)
        if d is not None:
            if d in self.nodes[src]["down"]:
                raise DesignError("%s already sends %s to %s" % (self.name_of(src), FACE_NAMES[d], self.name_of(dst)))
            self._push()
            self.nodes[src]["down"].add(d)
            return []
        if not route:
            raise DesignError("%s and %s are not neighbours" % (self.name_of(src), self.name_of(dst)))
        path = self._route(src, dst, any_layer)
        self._push()
        chain = [src] + path + [dst]
        for a, b in zip(chain, chain[1:]):
            if a != src:
                self.nodes[a] = {"name": self._auto_name("w"), "kind": "relay", "gate": None, "shift": 0, "left": True, "down": set()}
            self.nodes[a]["down"].add(next(k for k in range(6) if _add(a, k) == b))
        return path

    def _route(self, src, dst, any_layer):
        pointed = {_add(p, f) for p, n in self.nodes.items() for f in n["down"]}      # squares some face already sends to: a new relay there would be fed by accident
        blocked = set(self.nodes) | pointed

        def ok(q):
            return self.inside(q) and q not in blocked and (any_layer or q[2] == src[2])

        prev, q = {}, deque()
        for k in range(6):
            s = _add(src, k)
            if ok(s):
                prev[s] = None
                q.append(s)
        goal = None
        while q:
            cur = q.popleft()
            if any(_add(cur, k) == dst for k in range(6)):
                goal = cur
                break
            for k in range(6):
                nx = _add(cur, k)
                if ok(nx) and nx not in prev:
                    prev[nx] = cur
                    q.append(nx)
        if goal is None:
            raise DesignError("no free route from %s to %s%s" % (self.name_of(src), self.name_of(dst), "" if any_layer else " on this layer"))
        path, x = [], goal
        while x is not None:
            path.append(x)
            x = prev[x]
        path.reverse()
        if len(path) > MAX_ROUTE:
            raise DesignError("the route would need %d relay cells (limit %d)" % (len(path), MAX_ROUTE))
        return path

    def resize(self, rows=None, cols=None, layers=None):
        r, c, l = (int(x) if x is not None else y for x, y in ((rows, self.rows), (cols, self.cols), (layers, self.layers)))
        for nm, v in (("rows", r), ("cols", c), ("layers", l)):
            lo, hi = LIMITS[nm]
            if not lo <= v <= hi:
                raise DesignError("%s must be %d to %d" % (nm, lo, hi))
        for p, n in self.nodes.items():
            if p[0] >= r or p[1] >= c or p[2] >= l:
                raise DesignError("%s at %s would fall outside the smaller board" % (n["name"], p))
        self._push()
        self.rows, self.cols, self.layers = r, c, l

    def add_layer(self, side):
        if self.layers >= LIMITS["layers"][1]:
            raise DesignError("at most %d layers" % LIMITS["layers"][1])
        self._push()
        self.layers += 1
        if side == "bottom":                                  # every cell moves up one: neighbours stay neighbours
            self.nodes = {(p[0], p[1], p[2] + 1): n for p, n in self.nodes.items()}
        elif side != "top":
            raise DesignError("side must be top or bottom")

    def remove_layer(self, side):
        if self.layers <= 1:
            raise DesignError("a design needs at least one layer")
        target = self.layers - 1 if side == "top" else 0
        if side not in ("top", "bottom"):
            raise DesignError("side must be top or bottom")
        if any(p[2] == target for p in self.nodes):
            raise DesignError("the %s layer still holds cells" % side)
        self._push()
        self.layers -= 1
        if side == "bottom":
            self.nodes = {(p[0], p[1], p[2] - 1): n for p, n in self.nodes.items()}

    def clear(self, rows=10, cols=10, layers=4):
        self._push()
        self.rows, self.cols, self.layers, self.nodes, self.description, self.meta = rows, cols, layers, {}, "", {}

    # ---- analysis
    def graph(self):
        """(incoming, outgoing, dangling): incoming[pos] = sources; outgoing[pos] = targets; dangling = [(pos, face)] for faces that point at no cell."""
        inc, out, dangling = defaultdict(list), defaultdict(list), []
        for p, n in self.nodes.items():
            for f in sorted(n["down"]):
                t = _add(p, f)
                if t in self.nodes:
                    out[p].append(t)
                    inc[t].append(p)
                else:
                    dangling.append((p, f))
        return inc, out, dangling

    def entries(self):
        inc, out, _ = self.graph()
        return [p for p in sorted(self.nodes) if not inc[p] and out[p]]

    def exits(self):
        inc, out, _ = self.graph()
        return [p for p in sorted(self.nodes) if inc[p] and not out[p]]

    def problems(self):
        inc, out, dangling = self.graph()
        res = []
        for p, f in dangling:
            res.append({"level": "warn", "pos": list(p), "msg": "%s sends %s but there is no cell there" % (self.name_of(p), FACE_NAMES[f])})
        for p, n in sorted(self.nodes.items()):
            if n["kind"] == "gate" and len(inc[p]) != 2:
                res.append({"level": "warn", "pos": list(p), "msg": "gate %s has %d input(s); it fires when two words have arrived" % (n["name"], len(inc[p]))})
            if not inc[p] and not out[p] and not n["down"]:
                res.append({"level": "info", "pos": list(p), "msg": "%s is not joined to anything" % n["name"]})
        # a loop: a word would circulate for ever (the chaos run shows this)
        color, cyc = {}, None
        for s in self.nodes:
            if cyc or s in color:
                continue
            stack = [(s, iter(out[s]))]
            color[s] = 1
            trail = [s]
            while stack and not cyc:
                v, it = stack[-1]
                for w in it:
                    if color.get(w) == 1:
                        cyc = trail[trail.index(w):]
                        break
                    if w not in color:
                        color[w] = 1
                        trail.append(w)
                        stack.append((w, iter(out[w])))
                        break
                else:
                    color[v] = 2
                    trail.pop()
                    stack.pop()
        if cyc:
            res.append({"level": "warn", "pos": list(cyc[0]), "msg": "a loop: %s -> back to %s (a word would go round for ever)" % (" -> ".join(self.name_of(p) for p in cyc[:6]) + (" ..." if len(cyc) > 6 else ""), self.name_of(cyc[0]))})
        return res

    def summary(self):
        inc, out, _ = self.graph()
        gates = sum(1 for n in self.nodes.values() if n["kind"] == "gate")
        shifts = sum(1 for n in self.nodes.values() if n["kind"] == "relay" and n["shift"])
        vertical = sum(1 for p, n in self.nodes.items() for f in n["down"] if f in (4, 5) and _add(p, f) in self.nodes)
        layers_used = sorted({p[2] for p in self.nodes})
        neigh = max((len(set(inc[p]) | set(out[p])) for p in self.nodes), default=0)
        box = None
        if self.nodes:
            ps = list(self.nodes)
            box = [max(p[i] for p in ps) - min(p[i] for p in ps) + 1 for i in range(3)]
        return {"cells": len(self.nodes), "gates": gates, "shift_cells": shifts, "plain_relays": len(self.nodes) - gates - shifts, "vertical_links": vertical,
                "layers_used": len(layers_used), "bounding_box": box, "most_neighbours": neigh}

    # ---- files
    def export(self):
        return {"format": FORMAT, "version": 1,
                "note": "VM-only exploration model (experimental_3d_nor_v2.py); not an ICM file, nothing but composer3d_v1.py reads this",
                "description": self.description, "size": {"rows": self.rows, "cols": self.cols, "layers": self.layers}, "meta": self.meta,
                "cells": [{"name": n["name"], "pos": list(p), "kind": n["kind"], "gate": n["gate"], "shift": n["shift"], "left": n["left"],
                           "down": [FACE_NAMES[f] for f in sorted(n["down"])]} for p, n in sorted(self.nodes.items())]}

    @classmethod
    def from_export(cls, doc):
        if not isinstance(doc, dict) or doc.get("format") != FORMAT:
            raise DesignError("not an %s file" % FORMAT)
        if doc.get("version") != 1:
            raise DesignError("unknown version %r" % doc.get("version"))
        size = doc.get("size") or {}
        d = cls(int(size.get("rows", 10)), int(size.get("cols", 10)), int(size.get("layers", 4)))
        for nm in ("rows", "cols", "layers"):
            lo, hi = LIMITS[nm]
            if not lo <= getattr(d, nm) <= hi:
                raise DesignError("size: %s must be %d to %d" % (nm, lo, hi))
        d.description = str(doc.get("description") or "")[:500]
        d.meta = doc.get("meta") if isinstance(doc.get("meta"), dict) else {}
        for c in doc.get("cells") or []:
            try:
                pos = d._check_pos(c["pos"])
                if pos in d.nodes:
                    raise DesignError("two cells on %s" % (pos,))
                kind, gate, shift, left = d._clean(c.get("kind", "relay"), c.get("gate"), c.get("shift", 0), c.get("left", True))
                name = str(c["name"])
                if not NAME_RE.match(name) or any(n["name"] == name for n in d.nodes.values()):
                    raise DesignError("bad or repeated name %r" % name)
                faces = set()
                for f in c.get("down", []):
                    if f not in FACE_INDEX:
                        raise DesignError("bad face %r on %s" % (f, name))
                    faces.add(FACE_INDEX[f])
            except (KeyError, TypeError, ValueError) as e:
                raise DesignError("bad cell entry: %s" % e)
            d.nodes[pos] = {"name": name, "kind": kind, "gate": gate, "shift": shift, "left": left, "down": faces}
        return d


# ----------------------------------------------------------------------------------------------------------------------------- the stepper
class Sim:
    """The tick model of `Grid3.run`, one tick at a time. Tick 1 processes the injected words; what a cell sends in tick t arrives in tick t+1. Checked equal to Grid3.run in the tests."""

    def __init__(self, design, injections, watch=None):
        self.nodes = {p: {**n, "down": sorted(n["down"])} for p, n in design.nodes.items()}
        self.held = {p: None for p in self.nodes}
        self.out = {p: None for p in self.nodes}
        self.first_out = {}
        self.arrivals = {}
        for p, v in injections.items():
            self.arrivals.setdefault(p, []).append(int(v) & M32)
        self.tick = 0
        self.fired, self.moves = [], []
        self.watch = watch

    @property
    def settled(self):
        return not self.arrivals

    def step(self):
        if not self.arrivals:
            return False
        self.tick += 1
        nxt, self.fired, self.moves = {}, [], []
        for pos, vals in self.arrivals.items():
            c = self.nodes[pos]
            self.fired.append(pos)
            if c["kind"] == "relay":
                for v in vals:
                    self.out[pos] = shifted(c, v)
                    self._send(pos, nxt)
            else:
                for v in vals:
                    if self.held[pos] is None:
                        self.held[pos] = v
                    else:
                        self.out[pos] = m3.GATES[c["gate"]](self.held[pos], v)
                        self.held[pos] = None
                        self._send(pos, nxt)
            if self.out[pos] is not None and pos not in self.first_out:
                self.first_out[pos] = self.tick
        self.arrivals = nxt
        return True

    def _send(self, pos, nxt):
        for f in self.nodes[pos]["down"]:
            nb = _add(pos, f)
            if nb in self.nodes:
                nxt.setdefault(nb, []).append(self.out[pos])
                self.moves.append((pos, nb, self.out[pos]))

    def run(self, max_ticks=MAX_TICKS):
        n = 0
        while self.arrivals and n < max_ticks:
            self.step()
            n += 1
        return self.settled

    def run_to_watch(self, max_ticks=MAX_TICKS):
        """Stop where `Grid3.run` stops: the tick at which the watched cell holds a word and nothing more is coming to it. Returns (tick, word) or (None, None)."""
        while self.arrivals and self.tick < max_ticks:
            self.step()
            if self.out[self.watch] is not None and self.watch not in self.arrivals:
                return self.tick, self.out[self.watch]
        return None, None


def vectors(seed=5, n=60):
    rng = random.Random(seed)
    return [(0, 0), (M32, 1), (1, M32), (M32, M32), (0x7FFFFFFF, 1), (0x55555555, 0xAAAAAAAA)] + [((1 << i) - 1, 1) for i in range(1, 33)] + [(rng.getrandbits(32), rng.getrandbits(32)) for _ in range(n)]


def selfcheck(design):
    """For a design that declares meta.expect == 'add32' with meta.inputs [A, B] and meta.watch: run the adder vectors and compare with real addition."""
    m = design.meta
    if m.get("expect") == "netlist":                      # a design made by placer3d_v1.py: compare every exit with direct evaluation of the netlist it was made from
        import placer3d_v1 as pl
        try:
            cells, nets = pl.parse_netlist(m["netlist"])
            nodes = {p: {**n, "down": set(n["down"])} for p, n in design.nodes.items()}
            r = pl.verify(nodes, cells, nets, trials=100)
        except (pl.PlaceError, KeyError) as e:
            raise DesignError("cannot check against the netlist: %s" % e)
        return {"ok": r["ok"], "checked": r["trials"], "failed": None if r["ok"] else {"a": 0, "b": 0, "got": r["failed"]["got"], "exit": r["failed"]["exit"]}, "ticks": r["ticks"], "kind": "netlist"}
    if m.get("expect") != "add32":
        raise DesignError("this design declares no expected function")
    a, b, w = design.pos_of(m["inputs"][0]), design.pos_of(m["inputs"][1]), design.pos_of(m["watch"])
    ticks, n = set(), 0
    for x, y in vectors():
        t, v = Sim(design, {a: x, b: y}, w).run_to_watch()
        n += 1
        if v != (x + y) & M32:
            return {"ok": False, "checked": n, "failed": {"a": x, "b": y, "got": v}, "ticks": sorted(ticks)}
        ticks.add(t)
    return {"ok": True, "checked": n, "failed": None, "ticks": sorted(ticks)}


# ----------------------------------------------------------------------------------------------------------------------------- examples
def _from_grid3(g, placed, description, meta):
    """Turn a Grid3 layout (cells at squares, `placed` = names of the netlist cells) into a Design, moved so the lowest square on each axis is 1 and the board has one empty square all round."""
    pts = list(g.cells)
    lo = [min(p[i] for p in pts) - 1 for i in range(3)]
    d = Design(max(p[0] for p in pts) - lo[0] + 2, max(p[1] for p in pts) - lo[1] + 2, max(p[2] for p in pts) - lo[2] + 2)
    names = {tuple(p): n for n, p in placed.items()}
    wires = 0
    for p in sorted(pts):
        c = g.cells[p]
        q = tuple(p[i] - lo[i] for i in range(3))
        nm = names.get(tuple(p))
        if nm is None:
            wires += 1
            nm = "w%d" % wires
        d.nodes[q] = {"name": nm, "kind": c.kind, "gate": c.gate if c.kind == "gate" else None, "shift": c.shift, "left": c.left, "down": set(c.down)}
    d.description, d.meta = description, meta
    return d


def example_adder():
    import nor_adder_3d_v1 as t3
    try:
        r = json.load(open(t3.JSON))
        perms, seed = tuple(r["orientations"]), r["seed"]
    except (OSError, ValueError, KeyError):
        r = t3.measure()
        perms, seed = tuple(r["orientations"]), r["seed"]
    g, placed = t3.build_stacked_grid(perms, seed)
    return _from_grid3(g, placed, "The NOR-built 32-bit adder (word-level Kogge-Stone, 17 gates, 10 shift cells) in the six-face toy grid, as laid out by tools/nor_adder_3d_v1.py. Inputs A and B, result at E.",
                       {"expect": "add32", "inputs": ["A", "B"], "watch": "E"})


def example_crossing():
    d = Design(5, 5, 3)
    for c in range(5):
        d.nodes[(2, c, 1)] = {"name": "a%d" % c, "kind": "relay", "gate": None, "shift": 0, "left": True, "down": {2} if c < 4 else set()}
    b = [(0, 2, 1), (1, 2, 1), (1, 2, 0), (2, 2, 0), (3, 2, 0), (3, 2, 1), (4, 2, 1)]
    for i, p in enumerate(b):
        d.nodes[p] = {"name": "b%d" % i, "kind": "relay", "gate": None, "shift": 0, "left": True, "down": set()}
        if i + 1 < len(b):
            d.nodes[p]["down"].add(next(k for k in range(6) if _add(p, k) == b[i + 1]))
    d.description = "Two paths cross in the plan view without sharing a cell: path b dips down one layer under a2 and comes back up. Inject into a0 and b0."
    return d


def example_gate():
    d = Design(3, 4, 2)
    d.nodes[(1, 0, 0)] = {"name": "A", "kind": "relay", "gate": None, "shift": 0, "left": True, "down": {2}}
    d.nodes[(1, 1, 1)] = {"name": "B", "kind": "relay", "gate": None, "shift": 0, "left": True, "down": {5}}
    d.nodes[(1, 1, 0)] = {"name": "G", "kind": "gate", "gate": "XOR", "shift": 0, "left": True, "down": {2}}
    d.nodes[(1, 2, 0)] = {"name": "E", "kind": "relay", "gate": None, "shift": 4, "left": True, "down": set()}
    d.description = "The smallest vertical design: A arrives from the west, B from the layer above; a XOR gate on the floor takes both and E shifts the result left 4."
    return d


def example_adder_auto():
    import placer3d_v1 as pl
    cells, nets = pl.adder_netlist()
    d, rep = pl.place(cells, nets, layers=3, seed=1, keep=2)
    return d


EXAMPLES = {"adder_auto": ("NOR adder placed AUTOMATICALLY (3 layers; about 3 s)", example_adder_auto), "adder": ("NOR adder, 44 cells, 3 layers", example_adder), "crossing": ("two wires crossing on two layers", example_crossing), "gate": ("one gate fed from two layers", example_gate)}


# ----------------------------------------------------------------------------------------------------------------------------- the controller
class Composer3D:
    def __init__(self, design=None):
        self.design = design or Design()
        self.sim = None
        self.sim_inputs = {}
        self.lock = threading.RLock()

    def state(self, extra=None):
        d = self.design
        inc, out, _ = d.graph()
        cells = [{"name": n["name"], "pos": list(p), "kind": n["kind"], "gate": n["gate"], "shift": n["shift"], "left": n["left"], "down": [FACE_NAMES[f] for f in sorted(n["down"])],
                  "from": [d.name_of(s) for s in inc[p]]} for p, n in sorted(d.nodes.items())]
        links = []
        for p, n in sorted(d.nodes.items()):
            for f in sorted(n["down"]):
                t = _add(p, f)
                links.append({"src": list(p), "face": FACE_NAMES[f], "dst": list(t) if t in d.nodes else None})
        st = {"ok": True, "size": {"rows": d.rows, "cols": d.cols, "layers": d.layers}, "cells": cells, "links": links, "problems": d.problems(), "summary": d.summary(),
              "entries": [d.name_of(p) for p in d.entries()], "exits": [d.name_of(p) for p in d.exits()], "description": d.description, "meta": d.meta,
              "can_undo": bool(d._undo), "examples": [{"id": k, "label": v[0]} for k, v in EXAMPLES.items()], "sim": self._sim_state(), "limits": LIMITS}
        if extra:
            st.update(extra)
        return st

    def _sim_state(self):
        s = self.sim
        if s is None:
            return None
        cells = {}
        for p in s.nodes:
            inc = s.arrivals.get(p)
            if s.out[p] is not None or s.held[p] is not None or inc:
                cells[key(p)] = {"out": s.out[p], "held": s.held[p], "incoming": inc or []}
        w = None
        if s.watch is not None:
            w = {"name": s.nodes[s.watch]["name"], "value": s.out[s.watch], "first_tick": s.first_out.get(s.watch)}
        return {"tick": s.tick, "settled": s.settled, "cells": cells, "fired": [list(p) for p in s.fired], "moves": [{"src": list(a), "dst": list(b), "value": v} for a, b, v in s.moves], "watch": w}

    def handle(self, action, body):
        """One request. Returns the new state (plus any `extra`), or raises DesignError."""
        d = self.design
        with self.lock:
            if action == "state":
                return self.state()
            if action == "undo":
                d.undo()
                self.sim = None
            elif action == "export_icm3d":
                import icm3d_v1 as icm
                try:
                    doc = icm.from_design(d, body.get("name") or "design")
                except icm.IcmError as e:
                    raise DesignError(str(e))
                import base64
                return self.state({"icm3d": doc, "icm3d_bin": base64.b64encode(icm.pack(doc)).decode("ascii")})
            elif action in ("place", "delete", "set", "face", "link", "resize", "add_layer", "remove_layer", "clear", "example", "load", "description", "autoplace", "load_icm3d", "load_icm3d_bin"):
                self.sim = None
                if action == "place":
                    d.place(body["pos"], body.get("kind", "relay"), body.get("gate"), body.get("shift", 0), body.get("left", True), body.get("name"))
                elif action == "delete":
                    d.delete(body["pos"])
                elif action == "set":
                    d.set_cell(body["pos"], body.get("name"), body.get("kind"), body.get("gate"), body.get("shift"), body.get("left"))
                elif action == "face":
                    d.set_face(body["pos"], body["face"], bool(body["on"]))
                elif action == "link":
                    path = d.link(body["src"], body["dst"], body.get("route", True), body.get("any_layer", True))
                    return self.state({"routed": [list(p) for p in path]})
                elif action == "resize":
                    d.resize(body.get("rows"), body.get("cols"), body.get("layers"))
                elif action == "add_layer":
                    d.add_layer(body.get("side", "top"))
                elif action == "remove_layer":
                    d.remove_layer(body.get("side", "top"))
                elif action == "clear":
                    d.clear(int(body.get("rows", 10)), int(body.get("cols", 10)), int(body.get("layers", 4)))
                elif action == "example":
                    if body.get("id") not in EXAMPLES:
                        raise DesignError("unknown example")
                    new = EXAMPLES[body["id"]][1]()
                    d._push()
                    d.rows, d.cols, d.layers, d.nodes, d.description, d.meta = new.rows, new.cols, new.layers, new.nodes, new.description, new.meta
                elif action == "load":
                    new = Design.from_export(body["doc"])
                    d._push()
                    d.rows, d.cols, d.layers, d.nodes, d.description, d.meta = new.rows, new.cols, new.layers, new.nodes, new.description, new.meta
                elif action in ("autoplace", "load_icm3d", "load_icm3d_bin"):
                    new = self._build(action, body)
                    d._push()
                    d.rows, d.cols, d.layers, d.nodes, d.description, d.meta = new.rows, new.cols, new.layers, new.nodes, new.description, new.meta
                elif action == "description":
                    d._push()
                    d.description = str(body.get("text", ""))[:500]
            elif action == "export":
                return self.state({"doc": d.export()})
            elif action == "sim_start":
                inj = {}
                for nm, v in (body.get("inputs") or {}).items():
                    inj[d.pos_of(nm)] = _parse_word(v)
                if not inj:
                    raise DesignError("give at least one input word")
                watch = d.pos_of(body["watch"]) if body.get("watch") else None
                self.sim = Sim(d, inj, watch)
            elif action in ("sim_step", "sim_run"):
                if self.sim is None:
                    raise DesignError("start the run first")
                if action == "sim_step":
                    for _ in range(max(1, min(int(body.get("n", 1)), 100))):
                        if not self.sim.step():
                            break
                else:
                    ok = self.sim.run()
                    if not ok:
                        return self.state({"warning": "did not settle in %d ticks (a loop?)" % MAX_TICKS})
            elif action == "sim_reset":
                self.sim = None
            elif action == "check":
                res = selfcheck(d)
                return self.state({"check": res})
            else:
                raise DesignError("unknown action %r" % action)
            return self.state()


def _build(self, action, body):
    """The heavier loaders: auto-place a netlist, or read an ICM-3D file (JSON document, or base64 of the binary)."""
    if action == "autoplace":
        import placer3d_v1 as pl
        try:
            cells, nets = pl.parse_netlist(body["doc"])
            layers = int(body.get("layers", 3))
            new, rep = pl.place(cells, nets, layers=layers, seed=int(body.get("seed", 1)), keep=int(body.get("keep", 2)))
        except pl.PlaceError as e:
            raise DesignError(str(e))
        return new
    import icm3d_v1 as icm
    try:
        if action == "load_icm3d_bin":
            import base64
            import binascii
            try:
                data = base64.b64decode(body["b64"], validate=True)
            except (binascii.Error, ValueError):
                raise icm.IcmError("the upload is not valid base64")
            doc = icm.unpack(data)
        else:
            doc = body["doc"]
        return icm.to_design(doc)
    except icm.IcmError as e:
        raise DesignError(str(e))


Composer3D._build = _build


def _parse_word(v):
    if isinstance(v, int):
        return v & M32
    s = str(v).strip().replace("_", "")
    try:
        return int(s, 0) & M32
    except ValueError:
        raise DesignError("%r is not a number (decimal or 0x hex)" % v)


# ----------------------------------------------------------------------------------------------------------------------------- the page and the server
CSS = """
.c3 { display: grid; grid-template-columns: 1fr 340px; gap: 14px; align-items: start; }
.c3 .side { display: flex; flex-direction: column; gap: 12px; min-width: 0; position: sticky; top: 64px; max-height: calc(100vh - 76px); overflow-y: auto; overscroll-behavior: contain; padding-right: 2px; }
.c3 .panel { background: var(--bg-panel); border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px; min-width: 0; }
.c3 .panel h3 { margin: 0 0 8px; font-size: 13px; letter-spacing: .04em; text-transform: uppercase; color: var(--fg-dim); }
.c3 .scope summary { cursor: pointer; }
.c3 .scope[open] summary { margin-bottom: 6px; }
.c3 .scope { border-left: 3px solid var(--copper); padding: 6px 12px; background: var(--bg-panel); color: var(--fg-dim); font-size: 14px; max-width: var(--wide); margin: 0 0 12px; }
.c3 .bar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 0 0 8px; }
.c3 .bar select, .c3 .bar input[type=text], .c3 .bar input[type=number] { min-width: 0; max-width: 100%; }
.c3 .bar .sep { width: 1px; height: 22px; background: var(--line); }
.c3 button.on { background: var(--copper); color: var(--bg); border-color: var(--copper); }
.c3 .palette { display: flex; flex-wrap: wrap; gap: 4px; margin: 0 0 8px; }
.c3 .palette button { font-size: 12px; padding: 3px 7px; border-left: 4px solid var(--sw); }
.c3 .palette button.on { background: var(--bg-panel-2); color: var(--fg); outline: 1px solid var(--fg); }
.c3 .depth { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; background: var(--bg-panel); border: 1px solid var(--line); border-radius: 6px; padding: 8px 12px; margin: 0 0 8px; }
.c3 .depth input[type=range] { flex: 1 1 220px; min-width: 120px; accent-color: var(--copper); }
.c3 .depth .lab { font-family: var(--font-mono); font-size: 13px; color: var(--fg); min-width: 130px; }
.c3 .views { display: grid; gap: 8px; grid-template-columns: 1fr 1fr; }
.c3 .views.plan-only, .c3 .views.d3-only { grid-template-columns: 1fr; }
.c3 .views.plan-only .v3, .c3 .views.d3-only .vp { display: none; }
.c3 .view { position: relative; background: var(--bg-input); border: 1px solid var(--line); border-radius: 6px; height: 62vh; min-height: 340px; overflow: hidden; touch-action: none; }
.c3 .view canvas { width: 100%; height: 100%; display: block; }
.c3 .view .cap { position: absolute; top: 6px; left: 8px; font-family: var(--font-mono); font-size: 12px; color: var(--fg-dim); pointer-events: none; }
.c3 .view .tools { position: absolute; top: 6px; right: 6px; display: flex; gap: 4px; flex-wrap: wrap; justify-content: flex-end; }
.c3 .view .tools button { padding: 2px 8px; font-size: 12px; }
#plan.place, #plan.link, #plan.delete { cursor: crosshair; }
#d3 { cursor: grab; } #d3.drag { cursor: grabbing; }
#status { min-height: 1.4em; font-size: 14px; margin: 8px 0; overflow-wrap: anywhere; }
#status.err { color: var(--err); } #status.ok { color: var(--ok); }
.c3 .stat { font-family: var(--font-mono); font-size: 12.5px; color: var(--fg-dim); line-height: 1.6; overflow-wrap: anywhere; }
.c3 .stat b { color: var(--fg); font-weight: 500; }
#problems { list-style: none; margin: 0; padding: 0; font-size: 13px; }
#problems li { padding: 4px 0; border-top: 1px solid var(--line-soft); cursor: pointer; overflow-wrap: anywhere; }
#problems li:first-child { border-top: 0; }
#problems li.warn { color: var(--warn); }
.c3 .legend { display: flex; flex-wrap: wrap; gap: 6px 12px; font-size: 12.5px; color: var(--fg-dim); }
.c3 .legend span::before { content: ""; display: inline-block; width: 10px; height: 10px; margin-right: 5px; vertical-align: -1px; background: var(--sw); border-radius: 2px; }
#cfg .row { display: grid; grid-template-columns: 1fr 120px; gap: 6px; align-items: center; margin: 3px 0; }
#cfg .row label { font-family: var(--font-mono); font-size: 12px; color: var(--fg-dim); }
#cfg .row input, #cfg .row select { width: 100%; font-family: var(--font-mono); font-size: 12px; padding: 3px 5px; }
#cfg .faces { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; margin: 6px 0; }
#cfg .faces button { font-family: var(--font-mono); font-size: 12px; padding: 3px 4px; text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
#cfg .faces button.on { background: var(--copper); color: var(--bg); border-color: var(--copper); }
#cfg .faces button:disabled { opacity: .35; }
#cfg .actions, #run .actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
#run .in { display: grid; grid-template-columns: 70px 1fr; gap: 6px; align-items: center; margin: 3px 0; font-family: var(--font-mono); font-size: 12px; }
#run input[type=text], #run select { width: 100%; font-family: var(--font-mono); font-size: 12px; padding: 3px 5px; }
@media (max-width: 1100px) { .c3 { grid-template-columns: 1fr; } .c3 .side { position: static; max-height: none; } .c3 .views { grid-template-columns: 1fr; } }
"""

COLOURS = {"relay": "#627262", "shift": "#d9b46a", "AND": "#c17f45", "OR": "#7fa6d0", "XOR": "#b48ad0", "NOR": "#7fae7a", "NAND": "#8cb5ad", "XNOR": "#d0786a"}


def page():
    legend = "".join('<span style="--sw:%s">%s</span>' % (c, k) for k, c in COLOURS.items())
    opts = "".join('<option value="%s">%s</option>' % (k, v[0]) for k, v in EXAMPLES.items())
    body = """<div class="c3">
<div>
<h1 style="margin:0 0 6px;font-size:22px">3D Composer</h1>
<details class="scope"><summary><b>Exploration only</b> — a VM toy, not hardware (what this is)</summary>A separate composer for the six-face toy grid (N S E W and up / down). There is no 3D hardware, no 3D RTL and no card to run it on; this edits and runs the VM model
<code>experimental_3d_nor_v2.py</code> and saves its own files, which are not ICM files and are not connected to the main Composer. <b>Floor plan</b> (left): place, join and delete cells on the current layer. <b>3D view</b> (right):
drag to rotate, right-drag or shift-drag to pan, wheel to zoom. The <b>depth slider</b> chooses the current layer; everything on other layers is faded. Keys: [ and ] change layer, Delete removes the selected cell, Ctrl+Z undoes.</details>
<div class="bar">
  <button id="newBtn">New design</button>
  <select id="example"><option value="">open an example…</option>__OPTS__</select>
  <button id="openBtn">Open file…</button><input type="file" id="file" accept=".json" hidden>
  <button id="save" class="primary" title="download the design as an imago-3d-design file">Save design</button>
  <button id="saveIcm" title="download as an ICM-3D v1 JSON file (needs every face to point at a cell)">Save ICM-3D</button>
  <button id="saveIcmBin" title="download as an ICM-3D v1 binary file">Save ICM-3D binary</button>
  <button id="autoBtn" title="open a netlist file (imago-3d-netlist) and place it automatically">Auto-place netlist…</button><input type="file" id="netfile" accept=".json" hidden>
  <label title="layers the automatic placer may use">layers <input type="number" id="autoLayers" min="1" max="24" value="3" style="width:56px"></label>
  <button id="undo" title="undo the last edit (Ctrl+Z)">Undo</button>
  <span class="sep"></span>
    <label>rows <input type="number" id="rows" min="1" max="40" style="width:60px"></label>
  <label>cols <input type="number" id="cols" min="1" max="40" style="width:60px"></label>
  <button id="layerTop" title="add an empty layer on top">+ layer top</button>
  <button id="layerBot" title="add an empty layer underneath (everything moves up one)">+ layer bottom</button>
  <button id="rmTop" title="remove the top layer if it is empty">− top</button>
  <button id="rmBot" title="remove the bottom layer if it is empty">− bottom</button>
</div>
<div class="bar" id="tools">
  <button data-tool="select" class="on" title="click a cell to select it">Select</button>
  <button data-tool="place" title="click an empty square of the current layer to place the chosen cell">Place</button>
  <button data-tool="link" title="click a cell, then another cell: a face if they touch, otherwise a chain of relay cells is laid (any layer unless the box below is unticked)">Join</button>
  <button data-tool="delete" title="click a cell to delete it (or press Delete)">Delete</button>
  <label title="a join between cells that do not touch may route through other layers"><input type="checkbox" id="anyLayer" checked> joins may route through other layers</label>
</div>
<div class="palette" id="palette"></div>
<div class="depth">
  <b>Depth</b>
  <button id="dDown" title="one layer down (])" aria-label="one layer down">▼</button>
  <input type="range" id="depth" min="0" max="3" value="0" aria-label="current layer">
  <button id="dUp" title="one layer up ([)" aria-label="one layer up">▲</button>
  <span class="lab" id="depthLab"></span>
  <label>others <select id="fade" title="how strongly cells on other layers are faded">
     <option value="0">hidden</option><option value="0.1">very faint</option><option value="0.22" selected>faint</option><option value="0.5">visible</option></select></label>
  <label>layer gap <input type="range" id="gap" min="1" max="4" step="0.1" value="2" style="width:90px" aria-label="space between layers in the 3D view"></label>
  <label>show <select id="layout"><option value="split" selected>plan + 3D</option><option value="plan-only">plan only</option><option value="d3-only">3D only</option></select></label>
</div>
<div id="status" role="status"></div>
<div class="views" id="views">
  <div class="view vp"><div class="cap" id="capPlan">floor plan</div><canvas id="plan" role="img" aria-label="floor plan of the current layer"></canvas></div>
  <div class="view v3"><div class="cap">3D view</div>
    <div class="tools"><button data-cam="iso">3/4</button><button data-cam="top">Top</button><button data-cam="front">Front</button><button data-cam="side">Side</button><button id="spin" title="slowly turn the view">Spin</button></div>
    <canvas id="d3" role="img" aria-label="rotatable 3D view of the whole stack"></canvas></div>
</div>
</div>
<div class="side">
  <div class="panel"><h3>Legend</h3><div class="legend">__LEGEND__</div>
    <div class="stat" style="margin-top:6px">arrow: a join; gold arrow: a vertical join (up / down); ▲▼ on a tile: it sends or takes a word through the layer above / below; shift cells show «n or »n</div></div>
  <div class="panel"><h3>Selected</h3><div id="cfg" class="stat">tap a cell</div></div>
  <div class="panel"><h3>Run / step</h3><div id="run" class="stat"></div></div>
  <div class="panel"><h3>Design</h3><div id="summary" class="stat"></div><div class="stat" id="desc" style="margin-top:6px"></div></div>
  <div class="panel"><h3>Problems</h3><ul id="problems"><li>none</li></ul></div>
</div>
</div>
<script>window.C3_COLOURS = __COLOURS__;</script>
<script src="/composer3d_v1.js"></script>""".replace("__OPTS__", opts).replace("__LEGEND__", legend).replace("__COLOURS__", json.dumps(COLOURS))
    return ui.page("3D Composer", body, active="", app="composer3d", extra_css=CSS, narrow=False)


class Handler(http.server.BaseHTTPRequestHandler):
    controller = None
    server_version = "composer3d/1"

    def log_message(self, *a):
        pass

    def _host_ok(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("localhost", "127.0.0.1", "[::1]")

    def _send(self, code, data, ctype):
        b = data if isinstance(data, bytes) else data.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj), "application/json")

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, "bad host", "text/plain")
        path = self.path.split("?")[0]
        if path == "/":
            return self._send(200, page(), "text/html; charset=utf-8")
        if path == "/composer3d_v1.js":
            with open(os.path.join(HERE, "composer3d_v1.js"), "rb") as f:
                return self._send(200, f.read(), "application/javascript; charset=utf-8")
        if path == "/api/state":
            return self._json(self.controller.handle("state", {}))
        self._send(404, "not found", "text/plain")

    def do_POST(self):
        if not self._host_ok():
            return self._send(403, "bad host", "text/plain")
        if not self.path.startswith("/api/"):
            return self._send(404, "not found", "text/plain")
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(body, dict):
                raise DesignError("the request body must be a JSON object")
            self._json(self.controller.handle(self.path[5:], body))
        except DesignError as e:
            self._json({"ok": False, "error": str(e)})
        except (KeyError, TypeError, ValueError) as e:
            self._json({"ok": False, "error": "bad request: %s" % e})


def serve(controller=None, port=PORT, block=True):
    controller = controller or Composer3D()
    handler = type("H", (Handler,), {"controller": controller})
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    srv.controller = controller
    if block:
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            srv.server_close()
    else:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main(argv=None):
    ap = argparse.ArgumentParser(description="the 3D Composer (VM-only exploration of the six-face toy grid)")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--example", choices=sorted(EXAMPLES))
    ap.add_argument("--open", metavar="FILE", help="open an imago-3d-design file")
    a = ap.parse_args(argv)
    c = Composer3D()
    if a.example:
        c.design = EXAMPLES[a.example][1]()
    if a.open:
        with open(a.open) as f:
            c.design = Design.from_export(json.load(f))
    url = "http://127.0.0.1:%d/" % a.port
    print("3D Composer (exploration, VM only) at %s   -- Ctrl+C to stop" % url)
    if not a.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    serve(c, a.port)


if __name__ == "__main__":
    sys.modules.setdefault("composer3d_v1", sys.modules["__main__"])     # the loaders import this module by name: they must get THIS copy
    main()
