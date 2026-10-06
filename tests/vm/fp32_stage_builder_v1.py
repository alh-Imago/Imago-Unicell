"""tests/vm/fp32_stage_builder_v1.py -- a small helper (ledger #984) that turns "cells at grid positions + links between them" into ICM records: the up/down masks are DERIVED from the
links (a link between two adjacent cells sets the sender's downstream face and the receiver's opposite upstream face), and `route()` lays a chain of plain relay rams between two
cells over free grid squares (shortest path). Test support only -- it exists so a multi-cell stage can be written as a graph instead of hand-computed masks."""
import collections

from icm_v3 import IcmV3Record

D = {"n": (-1, 0), "s": (1, 0), "e": (0, 1), "w": (0, -1)}
OPP = {"n": "s", "s": "n", "e": "w", "w": "e"}


class Grid:
    def __init__(self, rows=10, cols=14):
        self.rows, self.cols = rows, cols
        self.nodes, self.links, self._relay = collections.OrderedDict(), [], 0

    def add(self, name, r, c, core="ram", cfg=None, addon=None, preload=None):
        assert (r, c) not in self.at(), f"{name}: square ({r},{c}) already used"
        self.nodes[name] = {"r": r, "c": c, "core": core, "cfg": dict(cfg or {}), "addon": dict(addon or {}), "preload": preload}
        return name

    def at(self):
        return {(n["r"], n["c"]): k for k, n in self.nodes.items()}

    def link(self, a, b, second=False):
        (ar, ac), (br, bc) = (self.nodes[a]["r"], self.nodes[a]["c"]), (self.nodes[b]["r"], self.nodes[b]["c"])
        assert abs(ar - br) + abs(ac - bc) == 1, f"{a} -> {b}: cells are not adjacent"
        self.links.append((a, b, second))

    def route_via(self, a, b, via, tag=None):
        """A route that is deliberately NOT the shortest: a -> a relay at the free square `via` -> b (used to lengthen a path so two operands of one cell arrive in different hops)."""
        nm = f"{tag or a + '_' + b}.via"
        self.add(nm, *via)
        self.route(a, nm, tag=tag)
        self.route(nm, b, tag=tag)

    def route(self, a, b, tag=None, avoid=(), second=False):
        """Shortest chain of relay rams from a to b through free squares; returns the relay names."""
        occupied = set(self.at()) | set(avoid)
        src, dst = (self.nodes[a]["r"], self.nodes[a]["c"]), (self.nodes[b]["r"], self.nodes[b]["c"])
        prev, q = {src: None}, collections.deque([src])
        while q:
            cur = q.popleft()
            for dr, dc in D.values():
                nxt = (cur[0] + dr, cur[1] + dc)
                if nxt == dst:
                    path, x = [], cur
                    while x != src:
                        path.append(x)
                        x = prev[x]
                    path.reverse()
                    names, last = [], a
                    for i, (r, c) in enumerate(path):
                        self._relay += 1
                        nm = f"{tag or a + '_' + b}.{self._relay}"
                        self.add(nm, r, c)
                        self.link(last, nm, second=second and i == 0)       # `second`: the FIRST hop leaves the source by its second-word face
                        names.append(nm)
                        last = nm
                    self.link(last, b, second=second and not path)
                    return names
                if 0 <= nxt[0] < self.rows and 0 <= nxt[1] < self.cols and nxt not in occupied and nxt not in prev:
                    prev[nxt] = cur
                    q.append(nxt)
        raise AssertionError(f"no free route {a} -> {b}")

    def records(self):
        up, down, down2 = collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)
        pos = {k: (n["r"], n["c"]) for k, n in self.nodes.items()}
        for a, b, second in self.links:
            d = next(k for k, (dr, dc) in D.items() if (pos[a][0] + dr, pos[a][1] + dc) == pos[b])
            (down2 if second else down)[a].append(d)
            up[b].append(OPP[d])
        out = []
        for k, n in self.nodes.items():
            cfg = dict({"upstream_mask": up[k], "downstream_mask": down[k]}, **n["cfg"])
            if down2[k]:
                cfg["second_downstream_mask"] = down2[k]
            out.append(IcmV3Record(cell_id=k, row=n["r"], col=n["c"], core=n["core"], core_config=cfg, addon_config=n["addon"] or {}, preload_value=n["preload"]))
        return out
