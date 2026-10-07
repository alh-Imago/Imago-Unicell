"""tools/flex_layout_v1.py -- a small LAYOUT ENGINE for flex designs (ledger #989): cells at grid squares + links between neighbours -> ICM records, with the parts that were hand-tuned in #984-#988 done by the tool.

  * `add(name, r, c, core, cfg, addon, preload)` puts a cell on a square; `link(a, b, second=False)` joins two ADJACENT cells (the up/down masks of both ends are derived; `second` = the sender's second-word face).
  * `route(a, b, second=False, extra=0)` lays a chain of plain relay rams over free squares (shortest, or exactly `extra` relays longer: a deliberate detour).
  * `hops()` is the generator's own hop-count model (entry = 1, a cell = 1 + the latest source), so ties can be found WITHOUT running the generator; `balance()` removes them: where the two operands
    of an adder / multiplier would arrive in the same hop (the generator refuses that: no operand order exists) it lengthens one ROUTED operand path by two relays (a longer route on a grid can only differ
    by a detour, so +2); where a subtract must have its minuend earlier (`minuend[cell] = source`) it lengthens the subtrahend's path the same way.
  * `records()` -> IcmV3Record list.
Test/design-support tooling: it only writes ICM records, the RTL generator stays the oracle."""
import collections
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nano"))
from icm_v3 import IcmV3Record  # noqa: E402
sys.setrecursionlimit(max(sys.getrecursionlimit(), 20000))   # hops() recurses along a path; long lanes (#1001) make paths a few hundred cells deep

D = {"n": (-1, 0), "s": (1, 0), "e": (0, 1), "w": (0, -1)}
OPP = {"n": "s", "s": "n", "e": "w", "w": "e"}
PAIR = ("adder", "mul")


class LayoutError(AssertionError):
    pass


class Grid:
    def __init__(self, rows=10, cols=14):
        self.rows, self.cols = rows, cols
        self.nodes, self.links, self._relay = collections.OrderedDict(), [], 0
        self.routes = {}                  # (a, b) -> {"relays": [...], "second": bool}
        self.minuend = {}                 # subtract cell -> the source that must arrive FIRST
        self.crossed = {}                 # crossing tile name -> (owner route key, crossing route key): a relay of the owner that a second route passes straight through (core "cross")

    # ---- building -------------------------------------------------------------------------------------------------------------------
    def add(self, name, r, c, core="ram", cfg=None, addon=None, preload=None):
        if (r, c) in self.at():
            raise LayoutError(f"{name}: square ({r},{c}) already used by {self.at()[(r, c)]}")
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            raise LayoutError(f"{name}: square ({r},{c}) is outside the {self.rows}x{self.cols} grid")
        self.nodes[name] = {"r": r, "c": c, "core": core, "cfg": dict(cfg or {}), "addon": dict(addon or {}), "preload": preload}
        return name

    def at(self):
        return {(n["r"], n["c"]): k for k, n in self.nodes.items()}

    def pos(self, a):
        return (self.nodes[a]["r"], self.nodes[a]["c"])

    def link(self, a, b, second=False):
        (ar, ac), (br, bc) = self.pos(a), self.pos(b)
        if abs(ar - br) + abs(ac - bc) != 1:
            raise LayoutError(f"{a} -> {b}: cells are not adjacent")
        self.links.append((a, b, second))

    def _free(self, extra_blocked=()):
        return set(self.at()) | set(extra_blocked)

    def _paths(self, a, b, n, blocked, spread=False):
        """Yield a simple path of EXACTLY n relay squares from a to b through free squares (n = None: the shortest)."""
        src, dst = self.pos(a), self.pos(b)
        if n is None and spread:
            # SPREAD: a cheapest path where every square next to an occupied one costs more, so routes keep to the middle of the channels and do not wall cells in (loose fit, #1001)
            import heapq
            best, prev, hp = {src: 0.0}, {src: None}, [(0.0, src)]
            while hp:
                cost, cur = heapq.heappop(hp)
                if cost > best.get(cur, 1e18):
                    continue
                for dr, dc in D.values():
                    nxt = (cur[0] + dr, cur[1] + dc)
                    if nxt == dst:
                        path, x = [], cur
                        while x != src:
                            path.append(x)
                            x = prev[x]
                        path.reverse()
                        return path
                    if not (0 <= nxt[0] < self.rows and 0 <= nxt[1] < self.cols) or nxt in blocked:
                        continue
                    near = sum(1 for er, ec in D.values() if (nxt[0] + er, nxt[1] + ec) in blocked and (nxt[0] + er, nxt[1] + ec) not in (src, dst))
                    nc = cost + 1.0 + 0.6 * near
                    if nc < best.get(nxt, 1e18):
                        best[nxt], prev[nxt] = nc, cur
                        heapq.heappush(hp, (nc, nxt))
            return None
        if n is None:
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
                        return path
                    if 0 <= nxt[0] < self.rows and 0 <= nxt[1] < self.cols and nxt not in blocked and nxt not in prev:
                        prev[nxt] = cur
                        q.append(nxt)
            return None
        budget = [300000]

        def dfs(cur, path, seen):
            budget[0] -= 1
            if budget[0] < 0:
                return None
            left = n - len(path)
            if left == 0:
                return list(path) if abs(cur[0] - dst[0]) + abs(cur[1] - dst[1]) == 1 else None
            if abs(cur[0] - dst[0]) + abs(cur[1] - dst[1]) - 1 > left:
                return None
            nbrs = sorted(((cur[0] + dr, cur[1] + dc) for dr, dc in D.values()), key=lambda p: abs(p[0] - dst[0]) + abs(p[1] - dst[1]))
            for nxt in nbrs:
                if 0 <= nxt[0] < self.rows and 0 <= nxt[1] < self.cols and nxt not in blocked and nxt not in seen and nxt != dst:
                    seen.add(nxt)
                    path.append(nxt)
                    got = dfs(nxt, path, seen)
                    if got:
                        return got
                    path.pop()
                    seen.discard(nxt)
            return None
        return dfs(src, [], {src})

    def _dir(self, p, q):
        return next(k for k, (dr, dc) in D.items() if (p[0] + dr, p[1] + dc) == q)

    def _crossable(self, name, d):
        """Can a route travelling in direction d pass STRAIGHT THROUGH the relay `name`? Only a plain relay of another route that itself runs straight, at right angles."""
        n = self.nodes.get(name)
        if n is None or n["core"] != "ram" or n["preload"] is not None or n["addon"] or name in self.crossed:
            return False
        ins = [l[0] for l in self.links if l[1] == name]
        outs = [l[1] for l in self.links if l[0] == name]
        if len(ins) != 1 or len(outs) != 1:
            return False
        din, dout = self._dir(self.pos(ins[0]), self.pos(name)), self._dir(self.pos(name), self.pos(outs[0]))
        return din == dout and d not in (din, OPP[din]) and not any(l[2] for l in self.links if l[0] == name or l[1] == name)

    def _paths_x(self, a, b, blocked, inbounds):
        """Shortest path that may cross other routes' straight relays at right angles. Returns [(square, crossing_node_or_None)] (a crossing entry is the tile passed through, it is not a new relay)."""
        src, dst = self.pos(a), self.pos(b)
        at = self.at()
        owned = {nm for rec in self.routes.values() for nm in rec["relays"]}
        prev, q = {src: None}, collections.deque([src])
        while q:
            cur = q.popleft()
            for dn, (dr, dc) in D.items():
                nxt = (cur[0] + dr, cur[1] + dc)
                step = [(nxt, None)]
                if nxt == dst:
                    path, x = [], cur
                    while x != src:
                        path = prev[x][1] + path
                        x = prev[x][0]
                    return path
                if not inbounds(nxt):
                    continue
                if nxt in blocked:
                    # through ONE OR MORE crossable relays in a row (Alan: "even if it has to cross multiple times"), landing on a free square
                    if cur == src:
                        continue
                    hops_, sq_ = [], nxt
                    while sq_ in blocked:
                        nm = at.get(sq_)
                        if nm is None or nm not in owned or not self._crossable(nm, dn) or any(h[1] == nm for h in hops_):
                            hops_ = None
                            break
                        hops_.append((sq_, nm))
                        sq_ = (sq_[0] + dr, sq_[1] + dc)
                    if not hops_ or not inbounds(sq_) or sq_ == dst or sq_ in prev:
                        continue
                    prev[sq_] = (cur, hops_ + [(sq_, None)])
                    q.append(sq_)
                elif nxt not in prev:
                    prev[nxt] = (cur, step)
                    q.append(nxt)
        return None

    def route(self, a, b, tag=None, avoid=(), second=False, extra=0, _extra_total=None, cross=False, spread=False):
        """A chain of relay rams from a to b: the shortest, or `extra` relays longer (extra must be even on a grid). `cross=True`: if no free route exists, the chain may pass STRAIGHT THROUGH
        another route's relay at right angles (that relay becomes a crossing tile, core "cross": pure wiring, both words pass without a register)."""
        blocked = self._free(avoid)
        short = self._paths(a, b, None, blocked, spread)
        items = None
        if short is not None and cross and not extra and len(short) > 40:        # a long free way round may be worse than crossing a few lines (#1007: a lane went round the whole board)
            alt = self._paths_x(a, b, blocked, lambda p: 0 <= p[0] < self.rows and 0 <= p[1] < self.cols)
            if alt is not None and sum(1 for sq, nm in alt if nm) and len(alt) + 24 < len(short):
                items, short = alt, [sq for sq, nm in alt]
        if short is None and cross and not extra:
            items = self._paths_x(a, b, blocked, lambda p: 0 <= p[0] < self.rows and 0 <= p[1] < self.cols)
            if items is not None:
                short = [sq for sq, nm in items]
        if short is None:
            raise LayoutError(f"no free route {a} -> {b}")
        path = short if not extra else self._paths(a, b, len(short) + extra, blocked)
        if path is None:
            raise LayoutError(f"no free route {a} -> {b} with {extra} extra relays")
        if items is None:
            items = [(sq, None) for sq in path]
        return self._lay(a, b, items, tag, second, extra, _extra_total, len(path))

    def _lay(self, a, b, items, tag, second, extra, _extra_total, n_path):
        names, last, crossings, n_start = [], a, [], len(self.links)
        for i, ((r, c), xn) in enumerate(items):
            if xn is not None:
                nm = xn
                owner = next(k for k, rec in self.routes.items() if nm in rec["relays"])
                self.nodes[nm]["core"] = "cross"
                self.crossed[nm] = (owner, (a, b))
                crossings.append(nm)
            else:
                self._relay += 1
                nm = f"{tag or a + '_' + b}.{self._relay}"
                self.add(nm, r, c)
                names.append(nm)
            self.link(last, nm, second=second and i == 0)
            last = nm
        self.link(last, b, second=second and not n_path)
        xlinks = [l for l in self.links[n_start:] if l[0] in crossings or l[1] in crossings]
        self.routes[(a, b)] = {"relays": names, "second": second, "tag": tag, "extra": extra if _extra_total is None else _extra_total, "crossings": crossings, "xlinks": xlinks}
        return names

    def route_line(self, a, b, tag=None):
        """A STRAIGHT chain of relays from cell a to cell b (same row or same column), nothing else: where it meets another route's straight relay at right angles it passes through it (that relay
        becomes a crossing tile, one tick per tile); anything else in the way is an error. For layouts that are planned as lines (#1001: "lay out each path as a separate thing ... where they cross, use a cross")."""
        (ar, ac), (br, bc) = self.pos(a), self.pos(b)
        if (ar != br and ac != bc) or (ar, ac) == (br, bc):
            raise LayoutError(f"route_line {a} -> {b}: not on one row or column")
        dr, dc = (br > ar) - (br < ar), (bc > ac) - (bc < ac)
        dname = next(k for k, v in D.items() if v == (dr, dc))
        at = self.at()
        owned = {nm for rec in self.routes.values() for nm in rec["relays"]}
        items, sq = [], (ar + dr, ac + dc)
        while sq != (br, bc):
            if not (0 <= sq[0] < self.rows and 0 <= sq[1] < self.cols):
                raise LayoutError(f"route_line {a} -> {b}: leaves the grid")
            if sq in at:
                nm = at[sq]
                if nm not in owned or not self._crossable(nm, dname):
                    raise LayoutError(f"route_line {a} -> {b}: square {sq} is taken by {nm}")
                items.append((sq, nm))
            else:
                items.append((sq, None))
            sq = (sq[0] + dr, sq[1] + dc)
        return self._lay(a, b, items, tag, False, 0, None, len(items))

    def route_nets(self, nets, rounds=300, seed=1, use_cross=True):
        """Route a list of nets (a, b[, kwargs]) in an order that works: a failing net goes to the FRONT and everything is rerouted (rip-up by reordering); when that cycles, the order is
        shuffled (seeded, so the result is deterministic)."""
        import random
        rng = random.Random(seed)
        order = [(n[0], n[1], n[2] if len(n) > 2 else {}) for n in nets]
        last = None
        for k in range(rounds):
            done, bad = [], None
            for i, (a, b, kw) in enumerate(order):
                try:
                    try:
                        self.route(a, b, **kw)
                    except LayoutError:
                        if not use_cross:
                            raise
                        self.route(a, b, cross=True, **kw)        # no free way: pass straight through another route's relay (a crossing tile)
                    done.append((a, b))
                except LayoutError:
                    bad = i
                    break
            if bad is None:
                return order
            last = (order[bad][0], order[bad][1])
            for a, b in reversed(done):
                self.unroute(a, b)
            if k % 20 == 19:
                rng.shuffle(order)
            else:
                order.insert(0, order.pop(bad))
        raise LayoutError(f"route_nets: no order found; last failure {last[0]} -> {last[1]}")

    def unroute(self, a, b):
        if any(nm in self.crossed for nm in self.routes[(a, b)]["relays"]):
            raise LayoutError(f"route {a} -> {b} is crossed by another route: unroute that one first")
        rec = self.routes.pop((a, b))
        for nm in rec.get("crossings", []):                     # give the tile back to the route that owns it: a plain relay again
            self.nodes[nm]["core"] = "ram"
            self.crossed.pop(nm, None)
        xl = set(rec.get("xlinks", []))
        self.links = [l for l in self.links if l not in xl]
        gone = set(rec["relays"])
        for nm in gone:
            del self.nodes[nm]
        self.links = [l for l in self.links if l[0] not in gone and l[1] not in gone and not (l[0] == a and l[1] == b)]
        return rec

    def _lengthen(self, a, b):
        """Re-lay the route a -> b two relays longer than it is now (the free squares are re-searched; a failure restores everything exactly). A route that other routes cross is lengthened too
        (#1005): the crossing routes are lifted first and laid again afterwards (crossing the new path if they must); a route that itself crosses others is not."""
        import copy
        if self.routes[(a, b)].get("crossings"):
            raise LayoutError(f"route {a} -> {b} crosses another route: not lengthened")
        snap = (copy.deepcopy(self.nodes), list(self.links), copy.deepcopy(self.routes), dict(self.crossed))      # restore EXACTLY on a failure
        try:
            crossers = []
            for nm in self.routes[(a, b)]["relays"]:
                if nm in self.crossed and self.crossed[nm][1] not in crossers:
                    crossers.append(self.crossed[nm][1])
            lifted = []
            for key in crossers:
                if key not in self.routes:
                    continue
                if any(n2 in self.crossed for n2 in self.routes[key]["relays"]):
                    raise LayoutError(f"route {key[0]} -> {key[1]} is crossed too: not lifted")
                if self.routes[key]["extra"]:
                    raise LayoutError(f"route {key[0]} -> {key[1]} is itself lengthened: cannot cross again")
                lifted.append((key, self.unroute(*key)))
            rec = self.unroute(a, b)
            want = rec["extra"] + 2
            self.route(a, b, tag=rec["tag"], second=rec["second"], extra=want, _extra_total=want)
            for key, r2 in lifted:
                self.route(key[0], key[1], tag=r2["tag"], second=r2["second"], cross=True)
            return True
        except LayoutError:
            self.nodes, self.links, self.routes, self.crossed = snap
            raise

    # ---- timing -----------------------------------------------------------------------------------------------------------------------
    def sources(self):
        """Who feeds whom, with crossing tiles transparent as to WHO (a word that enters a crossing leaves it in the same direction) but not as to TIME: a crossing is one register slice
        per direction, ONE TICK PER TILE like every other core (Alan, 6 Oct 2026). `self.xdelay[(consumer, source)]` = the number of crossing tiles on the way."""
        srcs = collections.defaultdict(list)
        self.xdelay = {}
        out = collections.defaultdict(list)
        for a, b, _ in self.links:
            out[a].append(b)
        for a, b, _ in self.links:
            if self.nodes[a]["core"] == "cross":
                continue
            cur, d, n_x = b, self._dir(self.pos(a), self.pos(b)), 0
            while self.nodes[cur]["core"] == "cross":
                n_x += 1
                cur = next((q for q in out[cur] if self._dir(self.pos(cur), self.pos(q)) == d), None)
                if cur is None:
                    break
            if cur is not None and a not in srcs[cur]:
                srcs[cur].append(a)
                self.xdelay[(cur, a)] = n_x
        return srcs

    def hops(self):
        """The generator's hop model: t = 1 + the latest source (an entry cell has t = 1)."""
        srcs, t = self.sources(), {}

        def tv(c, stack=()):
            if c in t:
                return t[c]
            if c in stack:
                raise LayoutError(f"cycle through {c}")
            t[c] = max((tv(q, stack + (c,)) + self.xdelay.get((c, q), 0) for q in srcs[c]), default=0) + 1
            return t[c]
        for c in self.nodes:
            if self.nodes[c]["core"] != "cross":
                tv(c)
        return t

    def _descends(self, q, m):
        """Is cell m the cell q itself or one of its ancestors?"""
        srcs, seen, todo = self.sources(), set(), [q]
        while todo:
            c = todo.pop()
            if c == m:
                return True
            if c not in seen:
                seen.add(c)
                todo.extend(srcs.get(c, []))
        return False

    def problems(self):
        """(cell, kind, early_source, late_source) for every pair cell whose operands tie, or whose declared minuend is not strictly first."""
        srcs, t, out = self.sources(), self.hops(), []
        for c, n in self.nodes.items():
            if n["core"] not in PAIR or len(srcs[c]) != 2:
                continue
            x, y = srcs[c]
            tx, ty = t[x] + self.xdelay.get((c, x), 0), t[y] + self.xdelay.get((c, y), 0)       # arrival = source + the crossing tiles on its way
            if tx == ty:
                out.append((c, "tie", x, y))
            m = self.minuend.get(c)
            if m is not None:                     # `m` names a cell UPSTREAM of one of the two sources (the route's last relay is the actual source)
                mx = next((q for q in (x, y) if self._descends(q, m)), None)
                if mx is None:
                    raise LayoutError(f"{c}: declared minuend {m} is upstream of neither operand")
                oth = y if mx == x else x
                if t[mx] + self.xdelay.get((c, mx), 0) >= t[oth] + self.xdelay.get((c, oth), 0):
                    out.append((c, "order", mx, oth))
        return out

    def balance(self, limit=60):
        """Lengthen ROUTED operand paths by two relays until no pair cell ties and every declared minuend is first. Returns the number of detours added."""
        added = 0
        for _ in range(limit):
            probs = self.problems()
            if not probs:
                return added
            c, kind, x, y = probs[0]
            # lengthen a routed path on the critical path of the side that should be LATER (the second operand; for a bad minuend order, the subtrahend), else of the other side
            t, srcs = self.hops(), self.sources()
            done = False
            for src in ([y, x] if kind in ("order", "tie") else [x, y]):
                cur = src
                while cur is not None and not done:
                    rec_key = next((k for k, rec in self.routes.items() if k[1] == cur or (rec["relays"] and rec["relays"][-1] == cur and k[1] == c)), None)
                    if rec_key is not None:
                        try:
                            self._lengthen(*rec_key)
                            done = True
                        except LayoutError:
                            pass
                    if done:
                        break
                    preds = srcs.get(cur, [])
                    cur = max(preds, key=lambda q: t[q]) if preds else None
                if done:
                    break
            if not done:
                raise LayoutError(f"{c}: operands {x} and {y} cannot be separated -- neither is a routed path (insert a route or a spacer on one of them)")
            added += 1
        raise LayoutError("balance did not settle")

    # ---- output -----------------------------------------------------------------------------------------------------------------------
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

    def dump(self):
        rows = [["." for _ in range(self.cols)] for _ in range(self.rows)]
        for k, n in self.nodes.items():
            rows[n["r"]][n["c"]] = {"ram": "r", "adder": "+", "mul": "*", "comparator": "?"}.get(n["core"], "?") if "." in k and k.rsplit(".", 1)[-1].isdigit() is False else "r"
        return "\n".join("".join(r) for r in rows)
