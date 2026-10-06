"""tools/flex_layout_view_v1.py -- the Composer's layout side (design note docs/stripped-cell/design-notes/composer_layout_viewer_scope.md): import an ICM file, show it as a
layout, and move cells by hand with the layout engine re-routing and re-balancing behind each move.

  * `Layout.load(path)` reads ICM v3 / v4 / VIX (via flexsub_icm_netlist_v1.load_records). The physical links come from each cell's masks and its position, the same rule the generator
    uses. Chains of PLAIN RELAY rams (one way in, one way out, no constant, add-on or io name) and crossing tiles are folded back into ROUTES between the logic cells at their ends, and the
    whole design is rebuilt as a `flex_layout_v1.Grid`. The engine is the single source of truth: this module adds no routing or timing logic of its own, and it does not change
    flex_layout_v1.py.
  * `snapshot()` is the JSON the /composer page draws: logic cells, routes as polylines, crossing tiles, hop depth, `problems()`.
  * `move(name, r, c)` lifts the cell's routes (and any route crossing them), moves it, re-routes with `route_nets`, then runs `balance()`. A move that cannot be routed or balanced is
    refused and the layout is left as it was. `undo()` steps back.
  * `records()` / `save(path)` write the edited design as ICM v3, in the file's own coordinates.

What can move: a logic cell whose wiring is all masks (ram, adder, mul, comparator, accumulator, latch with plain masks, ...) and whose routes all end at such cells. Cells wired by other
fields (nano's routing_mask, branch's route_*, a latch's set_dir, ...) are drawn but PINNED, as are the cells they connect to: the engine derives only up/down masks, so re-routing them would
lose wiring. Operand order is kept: where a subtracting adder's minuend arrives first on import, `Grid.minuend` keeps it first after a move.

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
from flex_layout_v1 import D, OPP, PAIR, Grid, LayoutError  # noqa: E402
from icm_v3 import IcmV3File, IcmV3Record  # noqa: E402

MASKS = ("upstream_mask", "downstream_mask", "second_downstream_mask")
OTHER_DIR_FIELDS = ("upstream_dir", "set_dir", "clear_dir", "toggle_dir", "inc_dir", "dec_dir", "routing_mask", "route_low", "route_equal", "route_high", "cardinal_edge")
PINNED_CORES = ("nano", "branch", "priority", "command", "sequencer")
MARGIN = 3                     # free squares kept round the design, so routes can go round its edge
UNDO_DEPTH = 40


def _faces(cfg, key):
    return [d.lower() for d in nl._dirs(cfg or {}, key)]


def _inputs(cfg, core):
    if core == "nano":
        return set("nsew")
    return {d for k in nl.INPUT_FIELDS for d in _faces(cfg, k)}


def _outputs(cfg, core):
    """[(face, second)] for every face the cell sends on."""
    out = [(d, False) for d in _faces(cfg, "downstream_mask")]
    out += [(d, True) for d in _faces(cfg, "second_downstream_mask")]
    if core == "nano":
        out += [(d, False) for d in _faces(cfg, "routing_mask")]
    if core == "branch":
        for k in ("low", "equal", "high"):
            out += [(d, False) for d in _faces(cfg, f"route_{k}")]
    seen, res = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            res.append(x)
    return res


class Layout:
    def __init__(self, records, name="layout", description="", min_bit_width=None):
        self.name, self.description, self.min_bit_width = name, description, min_bit_width
        self.warnings, self._undo = [], []
        self._build(list(records))

    @staticmethod
    def load(path):
        doc, recs = nl.load_records(path)
        return Layout(recs, name=os.path.basename(path), description=getattr(doc, "description", "") or "", min_bit_width=getattr(doc, "min_bit_width", None))

    # ---- import -----------------------------------------------------------------------------------------------------------------------
    def _build(self, recs):
        if not recs:
            raise LayoutError("the file has no cells")
        r0, c0 = min(r.row for r in recs), min(r.col for r in recs)
        self.offset = (MARGIN - r0, MARGIN - c0)              # file square + offset = layout square
        orow, ocol = self.offset
        rows = max(r.row for r in recs) + orow + 1 + MARGIN
        cols = max(r.col for r in recs) + ocol + 1 + MARGIN
        rec = {r.cell_id: r for r in recs}
        at = {(r.row + orow, r.col + ocol): r.cell_id for r in recs}
        pos = {k: (r.row + orow, r.col + ocol) for k, r in rec.items()}
        self.io = {k: r.io_name for k, r in rec.items() if r.io_name}
        self._orig_cfg = {k: dict(r.core_config or {}) for k, r in rec.items()}
        self._mask_keys = {k: {m for m in MASKS if m in (r.core_config or {})} for k, r in rec.items()}     # an empty mask the file left out stays left out

        # physical links, from masks + positions (the generator's rule); faces with nobody there are external
        links, self.ext = [], collections.defaultdict(lambda: {"up": [], "down": [], "down2": []})
        ins_of = collections.defaultdict(list)
        for k, r in rec.items():
            for d, second in _outputs(r.core_config, r.core):
                q = at.get((pos[k][0] + D[d][0], pos[k][1] + D[d][1]))
                if q is None:
                    self.ext[k]["down2" if second else "down"].append(d)
                    continue
                if OPP[d] not in _inputs(rec[q].core_config, rec[q].core):
                    self.warnings.append(f"{k} sends {d.upper()} but {q} does not listen on that face (the word is dropped)")
                    continue
                links.append((k, q, second))
                ins_of[q].append(k)
        for k, r in rec.items():
            for d in _faces(r.core_config, "upstream_mask"):
                q = at.get((pos[k][0] + D[d][0], pos[k][1] + D[d][1]))
                if q is None or k not in [b for a, b, _ in links if a == q]:
                    if q is None:
                        self.ext[k]["up"].append(d)
        outs = collections.defaultdict(list)
        for a, b, s in links:
            outs[a].append((b, s))

        def plain_relay(k):
            r = rec[k]
            cfg = r.core_config or {}
            if r.core != "ram" or r.preload_value is not None or r.addon_config or r.io_name or k in self.ext:
                return False
            if any(x not in MASKS + ("fixed_mode",) for x in cfg) or cfg.get("fixed_mode"):
                return False
            return len(ins_of[k]) == 1 and len(outs[k]) == 1 and not outs[k][0][1]

        relay = {k for k in rec if plain_relay(k)}
        cross = {k for k, r in rec.items() if r.core == "cross"}

        def walk(a, b, second):
            """Follow a link out of logic cell a through relays and crossing tiles to the logic cell it reaches: (dst, [(name, kind)]) or None (a dead end)."""
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
                    return cur, path
            return None

        logic = [k for k in rec if k not in relay and k not in cross]
        nets, claimed = [], set()
        for _ in range(3):                                     # relays no logic cell reaches (a broken chain) become fixed cells, then walk again
            nets, claimed = [], set()
            for a in logic:
                for b, second in outs[a]:
                    got = walk(a, b, second)
                    if got is not None:
                        nets.append((a, got[0], second, got[1]))
                        claimed.update(n for n, kind in got[1] if kind == "r")
            loose = relay - claimed
            if not loose:
                break
            relay -= loose
            logic += sorted(loose)

        # what may move: mask-wired cores, and only when every route they take part in ends at another mask-wired cell
        def mask_wired(k):
            r = rec[k]
            return k not in cross and r.core not in PINNED_CORES and not any(f in (r.core_config or {}) for f in OTHER_DIR_FIELDS)
        self.pinned = {k for k in logic if not mask_wired(k)}
        for a, b, _, _ in nets:
            if a in self.pinned or b in self.pinned:
                self.pinned.update((a, b))

        # the Grid
        g = Grid(rows=rows, cols=cols)
        self.grid = g
        for k in logic:
            r = rec[k]
            cfg = dict(r.core_config or {})
            if k not in self.pinned:
                for m in MASKS:
                    cfg.pop(m, None)
            g.add(k, *pos[k], core=r.core, cfg=cfg, addon=r.addon_config, preload=r.preload_value)
        keys, raw = collections.Counter((a, b) for a, b, _, _ in nets), []
        for a, b, second, path in nets:
            if keys[(a, b)] > 1 or a in self.pinned:          # two routes between the same pair, or pinned: kept as plain links (the engine keys routes by their two ends)
                raw.append((a, b, second, path))
                continue
            names, crossings, last, n0 = [], [], a, len(g.links)
            for i, (nm, kind) in enumerate(path):
                if nm not in g.nodes:
                    cfg = {x: v for x, v in (rec[nm].core_config or {}).items() if x not in MASKS}
                    g.add(nm, *pos[nm], core=rec[nm].core, cfg=cfg)
                    names.append(nm)
                elif kind == "x":
                    crossings.append(nm)
                g.link(last, nm, second=second and i == 0)
                last = nm
            g.link(last, b, second=second and not path)
            xl = [l for l in g.links[n0:] if l[0] in crossings or l[1] in crossings]
            g.routes[(a, b)] = {"relays": names, "second": second, "tag": None, "extra": 0, "crossings": crossings, "xlinks": xl}
        for a, b, second, path in raw:
            last = a
            for i, (nm, kind) in enumerate(path):
                if nm not in g.nodes:
                    g.add(nm, *pos[nm], core=rec[nm].core, cfg=dict(rec[nm].core_config or {}) if a in self.pinned else {x: v for x, v in (rec[nm].core_config or {}).items() if x not in MASKS})
                g.link(last, nm, second=second and i == 0)
                last = nm
            g.link(last, b, second=second and not path)
            self.pinned.update((a, b))
        for x in cross:                                       # a crossing tile: owned by the route that has it as a relay, crossed by the other
            owner = next((k for k, v in g.routes.items() if x in v["relays"]), None)
            other = next((k for k, v in g.routes.items() if x in v["crossings"]), None)
            if x not in g.nodes:
                g.add(x, *pos[x], core="cross")
                self.warnings.append(f"{x}: crossing tile with nothing passing through")
            elif owner and other:
                g.crossed[x] = (owner, other)
            else:                                             # used by one direction only, or by a pinned link: leave it fixed
                for k in (owner, other):
                    if k:
                        self.pinned.update(k)
        for k in [k for k in g.nodes if k not in rec]:
            raise LayoutError(f"internal: {k} not in the file")
        missing = set(rec) - set(g.nodes)
        for k in sorted(missing):                             # relays reached by no route at all (an isolated chain): placed as fixed cells
            g.add(k, *pos[k], core=rec[k].core, cfg=dict(rec[k].core_config or {}), addon=rec[k].addon_config, preload=rec[k].preload_value)
            self.pinned.add(k)
        for a, b, s in links:                                 # links among those leftovers
            if (a in missing or b in missing) and (a, b, s) not in g.links:
                g.links.append((a, b, s))
        g._relay = max([int(m.group(1)) for k in g.nodes for m in [re.search(r"\.(\d+)$", k)] if m] + [len(g.nodes)])
        self._orig_cfg = {k: v for k, v in self._orig_cfg.items() if k in self.pinned}     # a pinned cell never moves, so it is written back exactly as it was read
        self._set_minuends()

    def _set_minuends(self):
        """Keep a subtract's operand order: the source that arrives first now is declared the minuend, so a later move cannot swap the operands."""
        g = self.grid
        try:
            srcs, t = g.sources(), g.hops()
        except (LayoutError, RecursionError) as e:
            self.warnings.append(f"no timing model: {e}")
            return
        origin = {}
        for (a, b), v in g.routes.items():
            for nm in v["relays"]:
                origin[nm] = a
        for c, n in g.nodes.items():
            if n["core"] in PAIR and n["cfg"].get("subtract_mode") and len(srcs[c]) == 2:
                x, y = srcs[c]
                tx, ty = t[x] + g.xdelay.get((c, x), 0), t[y] + g.xdelay.get((c, y), 0)
                if tx != ty:
                    first = x if tx < ty else y
                    g.minuend[c] = origin.get(first, first)

    # ---- the view ---------------------------------------------------------------------------------------------------------------------
    def movable(self, k):
        n = self.grid.nodes.get(k)
        if n is None or k in self.pinned or n["core"] == "cross" or self._relay_of(k):
            return False
        return True

    def _relay_of(self, k):
        return next((key for key, v in self.grid.routes.items() if k in v["relays"]), None)

    def snapshot(self):
        g = self.grid
        try:
            t, probs, timing = g.hops(), g.problems(), None
        except (LayoutError, RecursionError) as e:
            t, probs, timing = {}, [], str(e)
        in_route = {nm: key for key, v in g.routes.items() for nm in v["relays"]}
        cells = []
        for k, n in g.nodes.items():
            if k in in_route and n["core"] != "cross":
                continue
            cells.append({"name": k, "r": n["r"], "c": n["c"], "core": n["core"], "hop": t.get(k), "cfg": n["cfg"], "addon": n["addon"], "preload": n["preload"],
                          "io": self.io.get(k), "movable": self.movable(k), "pinned": k in self.pinned})
        routes = []
        for (a, b), v in g.routes.items():
            chain = self._chain(a, b, v)
            pts = [list(g.pos(nm)) for nm in chain]
            routes.append({"from": a, "to": b, "second": v["second"], "relays": len(v["relays"]), "extra": v["extra"], "crossings": v["crossings"], "points": pts})
        linked = {(a, b) for (a, b) in g.routes}
        loose = [{"a": a, "b": b, "second": s} for a, b, s in g.links if (a, b) not in linked and a not in in_route and b not in in_route]
        by_core = collections.Counter(n["core"] for n in g.nodes.values())
        return {
            "name": self.name, "rows": g.rows, "cols": g.cols, "offset": list(self.offset),
            "cells": cells, "routes": routes, "links": loose,
            "crossings": [{"name": x, "r": g.nodes[x]["r"], "c": g.nodes[x]["c"], "owner": list(o), "crossing": list(c)} for x, (o, c) in g.crossed.items()],
            "problems": [{"cell": c, "kind": k, "early": x, "late": y} for c, k, x, y in probs],
            "summary": {"cells": len(g.nodes), "by_core": dict(by_core), "routes": len(g.routes), "relays": sum(len(v["relays"]) for v in g.routes.values()),
                        "max_hop": max(t.values(), default=0), "pinned": len(self.pinned), "undo": len(self._undo), "timing_error": timing},
            "warnings": self.warnings[:50],
        }

    def _chain(self, a, b, v):
        """The squares of route a -> b in order: a, its relays and crossing tiles, b."""
        g = self.grid
        mine = set(v["relays"]) | set(v["crossings"])
        nxt = collections.defaultdict(list)
        for x, y, _ in g.links:
            nxt[x].append(y)
        chain, cur, seen = [a], a, {a}
        while cur != b:
            step = [y for y in nxt[cur] if (y in mine or y == b) and y not in seen]
            if cur in g.crossed or (cur in mine and g.nodes[cur]["core"] == "cross"):
                d = g._dir(g.pos(chain[-2]), g.pos(cur))
                step = [y for y in step if g._dir(g.pos(cur), g.pos(y)) == d] or step
            if not step:
                break
            cur = step[0]
            seen.add(cur)
            chain.append(cur)
        return chain

    # ---- editing ----------------------------------------------------------------------------------------------------------------------
    def move(self, name, r, c):
        """Move logic cell `name` to layout square (r, c), re-route its routes and re-balance. Returns {"ok", "error"?, "rerouted", "detours"}."""
        g = self.grid
        if name not in g.nodes:
            return {"ok": False, "error": f"no cell {name}"}
        if not self.movable(name):
            why = "a relay of a route (move the cells at its ends)" if self._relay_of(name) else "pinned: it is wired by fields the layout engine does not derive" if name in self.pinned else "not movable"
            return {"ok": False, "error": f"{name} is {why}"}
        if not (0 <= r < g.rows and 0 <= c < g.cols):
            return {"ok": False, "error": f"({r},{c}) is off the board"}
        if (r, c) == g.pos(name):
            return {"ok": True, "rerouted": [], "detours": 0}
        mine = {key for key in g.routes if name in key}
        while True:                                           # a route crossed by another cannot be lifted alone: lift the crossing one too
            more = {g.crossed[x][1] for key in mine for x in g.routes[key]["relays"] if x in g.crossed}
            if more <= mine:
                break
            mine |= more
        occupant = g.at().get((r, c))
        lifted = {nm for key in mine for nm in g.routes[key]["relays"]}
        if occupant is not None and occupant not in lifted:
            return {"ok": False, "error": f"({r},{c}) is taken by {occupant}"}
        backup = copy.deepcopy(g)
        try:
            todo, nets = set(mine), []
            while todo:
                ready = [key for key in todo if not any(nm in g.crossed for nm in g.routes[key]["relays"])]
                if not ready:
                    raise LayoutError("routes cross each other in a cycle: cannot lift them")
                for key in ready:
                    rec = g.unroute(*key)
                    nets.append((key[0], key[1], {"second": rec["second"]} if rec["second"] else {}))
                    todo.discard(key)
            g.nodes[name]["r"], g.nodes[name]["c"] = r, c
            g.route_nets(nets, rounds=60)
            detours = g.balance()
        except (LayoutError, StopIteration, RecursionError) as e:
            self.grid = backup
            return {"ok": False, "error": str(e) or e.__class__.__name__}
        self._undo.append(backup)
        del self._undo[:-UNDO_DEPTH]
        return {"ok": True, "rerouted": [f"{a} -> {b}" for a, b, _ in nets], "detours": detours}

    def undo(self):
        if not self._undo:
            return {"ok": False, "error": "nothing to undo"}
        self.grid = self._undo.pop()
        return {"ok": True}

    # ---- export -----------------------------------------------------------------------------------------------------------------------
    def records(self):
        orow, ocol = self.offset
        out = []
        for rec in self.grid.records():
            cfg = dict(rec.core_config)
            k = rec.cell_id
            if k in self._orig_cfg:
                cfg = dict(self._orig_cfg[k])
            elif k in self.ext:            # faces that leave the design (entries and exits on the file's edge) come back as they were
                e = self.ext[k]
                for key, faces in (("upstream_mask", e["up"]), ("downstream_mask", e["down"]), ("second_downstream_mask", e["down2"])):
                    if faces:
                        cfg[key] = list(cfg.get(key, [])) + [d for d in faces if d not in cfg.get(key, [])]
            ud = cfg.get("upstream_dir")
            if isinstance(ud, (list, tuple)) and len(ud) == 1 and str(ud[0]).upper() in "NSEW":     # ICM-VIX writes a branch's input as ["W"]; ICM v3 keeps a direction CODE (0=N 1=S 2=E 3=W)
                cfg["upstream_dir"] = "NSEW".index(str(ud[0]).upper())
            for m in MASKS:
                if k in self._mask_keys and m in cfg and not cfg[m] and m not in self._mask_keys[k]:
                    del cfg[m]
            out.append(IcmV3Record(cell_id=k, row=rec.row - orow, col=rec.col - ocol, core=rec.core, core_config=cfg, addon_config=rec.addon_config,
                                   io_name=self.io.get(k), preload_value=rec.preload_value))
        return out

    def save(self, path):
        f = IcmV3File(name=self.name, records=self.records(), description=self.description or "edited in the Composer (tools/flex_layout_view_v1.py)", min_bit_width=self.min_bit_width)
        f.save(path)
        return path


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
