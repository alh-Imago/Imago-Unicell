"""nano/std_ring_control_v1.py -- ledger #1123: ring control for ANY standard-line ICM that contains a closed ring (Alan, 13 Oct 2026: "the ICM must be able to target all families equally").

The design proven by hand in #1116/#1117 (nano/looped_cordic_v1.py `_add_ring_control`) is here made GENERAL: given the flat records of a design, find its ring, pick two flowing relay cells on the ring's single-cell chain (F upstream, G two steps downstream), and place the control cluster on FREE cells next to them. Every cell is an existing standard cell:
    F  (a ring relay)    forks each word onward AND to the counter;
    acc                  accumulator, +1 per word (the running lap count), next to F;
    m_1.. m_k, m1        relays carrying the count to the branch (m1 also receives the reference);
    ref                  a ram preloaded with the reference value: the branch's FIRST arrival, so it is held as the reference;
    branch               LOW (count < ref) -> a token (fixed 0) to tok;  EQUAL -> a flag (fixed 1) to stop;  HIGH -> nothing;
    tok                  a ram that receives the branch's tokens and the host's `ring_release` word and feeds G;
    G  (a ring relay)    becomes a JOIN adder (word + token): a word passes only with a token, so when the tokens run out the word waits there and the ring is held;
    stop                 a ram named `ring_stopped` (valid = the ring has been stopped);  rel: a ram named `ring_release` (the host writes any word: one lap, or a new window).
The branch decides per word and stays in no mode; it is the gate that turns "no token" into "stop" (Alan 12 Oct: the branch cannot steer the flow).
The stop comes OFFSET words after the reference value (two start-up zero offers of the accumulator + the relays on the count path); the offset depends on how the cluster was placed, so it is MEASURED here by running the design in the standard VM, and the reference is set to N - offset
(N must be at least offset + 1). The result is checked once more in the VM before it is returned.
"""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FACE = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}


class RingError(ValueError):
    pass


def _faces(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    return list(v)


def _down(r):
    c = r.core_config
    if r.core == "branch":
        out = []
        for k in ("route_low", "route_equal", "route_high"):
            out += _faces(c.get(k))
        return sorted(set(out))
    return _faces(c.get("downstream_mask"))


def _accepts(r, face_from_neighbour):
    """does record r take a word arriving on its face `face_from_neighbour`?"""
    c = r.core_config
    if r.core == "branch":
        return face_from_neighbour in _faces(c.get("upstream_dir"))
    if r.core == "accumulator":
        return face_from_neighbour in _faces(c.get("inc_dir")) or face_from_neighbour in _faces(c.get("dec_dir"))
    return face_from_neighbour in _faces(c.get("upstream_mask"))


def _graph(recs):
    pos = {(r.row, r.col): r for r in recs}
    succ = {r.cell_id: [] for r in recs}
    for r in recs:
        for f in _down(r):
            dr, dc = FACE[f]
            n = pos.get((r.row + dr, r.col + dc))
            if n is not None and _accepts(n, OPP[f]):
                succ[r.cell_id].append(n.cell_id)
    return pos, succ


def _scc_of(succ, start):
    """cells that are both reachable from `start` and can reach it"""
    def reach(adj, s):
        seen, stack = {s}, [s]
        while stack:
            x = stack.pop()
            for y in adj.get(x, ()):
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        return seen
    pred = {k: [] for k in succ}
    for a, bs in succ.items():
        for b in bs:
            pred[b].append(a)
    return reach(succ, start) & reach(pred, start)


def _chain_before(succ, scc, result_id):
    """the maximal single-in single-out chain of ring cells that ends at the result cell, in flow order (the way back round the outside)"""
    pred = {k: [] for k in scc}
    for a in scc:
        for b in succ[a]:
            if b in scc:
                pred[b].append(a)
    chain = [result_id]
    while True:
        ps = pred[chain[0]]
        if len(ps) != 1:
            break
        p = ps[0]
        if p in chain or len([b for b in succ[p] if b in scc]) != 1:
            break
        chain.insert(0, p)
    return chain


def _is_relay(r):
    c = r.core_config
    return r.core == "ram" and not c.get("fixed_mode") and len(_faces(c.get("upstream_mask"))) == 1 and len(_faces(c.get("downstream_mask"))) == 1


def _face_between(a, b):
    for f, (dr, dc) in FACE.items():
        if (a[0] + dr, a[1] + dc) == b:
            return f
    raise RingError("cells %s and %s are not neighbours" % (a, b))


def _nbrs(p):
    return [(p[0] + dr, p[1] + dc) for f, (dr, dc) in FACE.items()]


def _place(occupied, F, G, F_used, G_used, box):
    """-> dict of positions for acc, chain(list), m1, ref, branch, tok, rel, stop; or None. Pure adjacency search over free cells."""
    r0, r1, c0, c1 = box

    def free(p, taken):
        return r0 <= p[0] <= r1 and c0 <= p[1] <= c1 and p not in occupied and p not in taken

    for tok in _nbrs(G):
        if not free(tok, ()) or _face_between(G, tok) in G_used:
            continue
        for branch in _nbrs(tok):
            if not free(branch, {tok}):
                continue
            for m1 in _nbrs(branch):
                if not free(m1, {tok, branch}):
                    continue
                for stop in _nbrs(branch):
                    if not free(stop, {tok, branch, m1}):
                        continue
                    for rel in _nbrs(tok):
                        if not free(rel, {tok, branch, m1, stop}):
                            continue
                        for ref in _nbrs(m1):
                            taken = {tok, branch, m1, stop, rel, ref}
                            if not free(ref, taken - {ref}):
                                continue
                            # the count path: acc next to F, then relays, ending next to m1 (not on the branch's or ref's face)
                            starts = [p for p in _nbrs(F) if free(p, taken) and _face_between(F, p) not in F_used]
                            best = None
                            for acc in starts:
                                prev = {acc: None}
                                queue = [acc]
                                goal = None
                                while queue and goal is None:
                                    x = queue.pop(0)
                                    if m1 in _nbrs(x):
                                        goal = x
                                        break
                                    for y in _nbrs(x):
                                        if y not in prev and free(y, taken | {acc}):
                                            prev[y] = x
                                            queue.append(y)
                                if goal is None:
                                    continue
                                path = []
                                x = goal
                                while x is not None:
                                    path.append(x)
                                    x = prev[x]
                                path.reverse()
                                if best is None or len(path) < len(best):
                                    best = path
                            if best is not None:
                                return dict(acc=best[0], chain=best[1:], m1=m1, ref=ref, branch=branch, tok=tok, rel=rel, stop=stop)
    return None


def _cluster(recs, F, G, spots, ref_value):
    """records for the cluster and the edited F and G (returned as new records; the originals are not touched)"""
    from icm_v3 import IcmV3Record as Rec
    pos = {(r.row, r.col): r for r in recs}
    F2, G2 = copy.deepcopy(F), copy.deepcopy(G)
    fa = _face_between((F.row, F.col), spots["acc"])
    F2.core_config["downstream_mask"] = _faces(F.core_config["downstream_mask"]) + [fa]
    ga_in = _face_between((G.row, G.col), spots["tok"])
    G2.core = "adder"
    G2.core_config = {"upstream_mask": _faces(G.core_config["upstream_mask"]) + [ga_in], "downstream_mask": _faces(G.core_config["downstream_mask"]), "join_mode": 1}
    out = []

    def add(cid, p, core, cfg, **kw):
        out.append(Rec(cell_id=cid, row=p[0], col=p[1], core=core, core_config=cfg, addon_config={}, io_name=kw.get("io_name"), preload_value=kw.get("preload_value")))

    chain = [spots["acc"]] + spots["chain"]
    nxt = lambda a, b: _face_between(a, b)
    add("ctl_acc", spots["acc"], "accumulator", {"inc_dir": [OPP[fa]], "downstream_mask": [nxt(spots["acc"], (chain[1] if len(chain) > 1 else spots["m1"]))], "step_amount": 1, "pulse_mode": 0, "threshold": 0})
    for i in range(1, len(chain)):
        prev, here = chain[i - 1], chain[i]
        to = chain[i + 1] if i + 1 < len(chain) else spots["m1"]
        add("ctl_m%d" % (i + 1), here, "ram", {"upstream_mask": [nxt(here, prev)], "downstream_mask": [nxt(here, to)], "fixed_mode": 0})
    last = chain[-1]
    add("ctl_m1", spots["m1"], "ram", {"upstream_mask": [nxt(spots["m1"], last), nxt(spots["m1"], spots["ref"])], "downstream_mask": [nxt(spots["m1"], spots["branch"])], "fixed_mode": 0})
    add("ctl_ref", spots["ref"], "ram", {"downstream_mask": [nxt(spots["ref"], spots["m1"])], "fixed_mode": 0}, preload_value=ref_value)
    add("ctl_branch", spots["branch"], "branch", {"upstream_dir": [nxt(spots["branch"], spots["m1"])], "value_source_low": 1, "value_source_equal": 1, "value_source_high": 1,
                                                  "fixed_value_low": 0, "fixed_value_equal": 1, "fixed_value_high": 0, "emit_low": 1, "emit_equal": 1, "emit_high": 0,
                                                  "route_low": [nxt(spots["branch"], spots["tok"])], "route_equal": [nxt(spots["branch"], spots["stop"])], "route_high": [], "rolling_mode": 0})
    add("ctl_tok", spots["tok"], "ram", {"upstream_mask": [nxt(spots["tok"], spots["branch"]), nxt(spots["tok"], spots["rel"])], "downstream_mask": [OPP[ga_in]], "fixed_mode": 0})
    add("ctl_rel", spots["rel"], "ram", {"upstream_mask": [], "downstream_mask": [nxt(spots["rel"], spots["tok"])], "fixed_mode": 0}, io_name="ring_release")
    add("ctl_stop", spots["stop"], "ram", {"upstream_mask": [nxt(spots["stop"], spots["branch"])], "downstream_mask": [], "fixed_mode": 0}, io_name="ring_stopped")
    new = []
    for r in recs:
        if r.cell_id == F.cell_id:
            new.append(F2)
        elif r.cell_id == G.cell_id:
            new.append(G2)
        else:
            new.append(copy.deepcopy(r))
    return new + out


def _vm_laps(recs, input_io, result_io, z0, max_laps):
    """run the design in the standard VM; the number of words that arrive at the result cell"""
    from unicell_super_automaton_v1 import SuperGrid
    g = SuperGrid(recs)
    for _ in range(10):
        g.tick()
    inp = next(r for r in recs if r.io_name == input_io)
    res = next(r for r in recs if r.io_name == result_io)
    g.inject(inp.row, inp.col, z0 & 0xFFFFFFFF)
    laps, last, ticks = 0, False, 0
    limit = (max_laps + 6) * 80
    while ticks < limit:
        g.tick()
        ticks += 1
        c = g.cells[(res.row, res.col)]
        v = bool(getattr(c, "ram_data_valid", False))
        if v and not last:
            laps += 1
            if laps >= max_laps + 4:
                break
        last = v
    # let a stopped ring prove it is quiet
    return laps


def insert_ring_control(recs, n, input_io="z_input", result_io="result", z0=50000):
    """-> (records with the control cluster, info). Raises RingError with the reason when the design has no usable ring or no room."""
    recs = [copy.deepcopy(r) for r in recs]
    for r in recs:
        if r.core == "adder":
            r.core_config["join_mode"] = 1          # the ICM's meaning is a true join (the flex family's two-operand cells are joins); the standard cell needs the bit
    if any(r.cell_id.startswith("ctl_") for r in recs):
        raise RingError("the design already has ring control cells (ctl_*)")
    res = [r for r in recs if r.io_name == result_io]
    if not res:
        raise RingError("no cell is named io_name '%s' (the ring's observation point)" % result_io)
    pos, succ = _graph(recs)
    scc = _scc_of(succ, res[0].cell_id)
    if len(scc) < 2:
        raise RingError("the cell '%s' is not on a ring (no closed path of cells leads back to it)" % result_io)
    chain = _chain_before(succ, scc, res[0].cell_id)
    byid = {r.cell_id: r for r in recs}
    occupied = set(pos)
    rows = [p[0] for p in occupied]
    cols = [p[1] for p in occupied]
    box = (min(rows) - 4, max(rows) + 4, min(cols) - 4, max(cols) + 4)
    tried = 0
    for i in range(len(chain) - 3):             # F = chain[i], G = chain[i+2]; the result cell stays downstream of G
        F, G = byid[chain[i]], byid[chain[i + 2]]
        if not (_is_relay(F) and _is_relay(G) and _is_relay(byid[chain[i + 1]])):
            continue
        tried += 1
        F_used = set(_faces(F.core_config["downstream_mask"]) + _faces(F.core_config["upstream_mask"]))
        G_used = set(_faces(G.core_config["downstream_mask"]) + _faces(G.core_config["upstream_mask"]))
        spots = _place(occupied, (F.row, F.col), (G.row, G.col), F_used, G_used, box)
        if spots is None:
            continue
        # measure the offset with a trial reference, then set the real one
        trial = 8
        laps0 = _vm_laps(_cluster(recs, F, G, spots, trial), input_io, result_io, z0, trial + 6)
        offset = laps0 - trial
        if offset < 0 or offset > 40:
            raise RingError("the control did not behave in the VM (reference %d gave %d laps): the design may not be a plain ring" % (trial, laps0))
        if n < offset + 1:
            raise RingError("N must be at least %d for this design (the count path holds %d words); got %d" % (offset + 1, offset, n))
        ref = n - offset
        out = _cluster(recs, F, G, spots, ref)
        got = _vm_laps(out, input_io, result_io, z0, n)
        if got != n:
            raise RingError("the control was placed but the VM gave %d laps for N = %d" % (got, n))
        info = dict(fork=F.cell_id, gate=G.cell_id, offset=offset, reference=ref, laps_checked_in_vm=got, cluster=[r.cell_id for r in out if r.cell_id.startswith("ctl_")],
                    release_cell=next(r.cell_id for r in out if r.io_name == "ring_release"), stopped_cell=next(r.cell_id for r in out if r.io_name == "ring_stopped"))
        return out, info
    if not tried:
        raise RingError("the ring has no stretch of three flowing relay cells in a row on its way back to '%s' (the control forks at one and gates at the other)" % result_io)
    raise RingError("no free cells next to the ring to place the control cluster (tried %d fork/gate pairs; the free space around the design is limited to 4 cells)" % tried)
