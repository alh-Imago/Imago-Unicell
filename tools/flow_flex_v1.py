"""tools/flow_flex_v1.py -- ledger #1033: FLOW DYNAMICS in a medium of flex cells (Alan: "a repeating style pattern with handoffs ... demonstrate a standard flow plus an instructed flow in the medium").

The medium is a row of N cells, each holding an amount C_i (a quantity of fluid).  Time is unrolled into space as in the LIF neuron (#1030): one STAGE per time step, the amounts handed from stage to stage.
Per step, every cell does two things, both conservative (what leaves one cell arrives in its neighbour, so the total never changes; the two end walls are closed):
  * STANDARD flow (diffusion): it hands  d_i = C_i >> k  to EACH neighbour;
  * INSTRUCTED flow (a pump): a command word a_i (0 .. 2^s, one per cell per step, entering the medium from outside) makes it hand  p_i = (C_i * a_i) >> s  to its RIGHT neighbour.
        C'_i = C_i - (#neighbours) * d_i - p_i + d_(i-1) + d_(i+1) + p_(i-1)            (the last cell has no right neighbour, so no pump; keep  2/2^k + a/2^s <= 1)
Each (cell, step) is two small tiles: tile A (works out the hand-offs from C_i and the command) and tile B (adds what arrives), so the lanes between cells are short.
`flow_ref` is the exact integer reference."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_add_v1 as fadd  # noqa: E402
import netplace_v1 as npl  # noqa: E402
import fp_mul_tight_v1 as fmt1  # noqa: E402

shl, shr = fadd.shl, fadd.shr


def flow_ref(c0, cmds, k=3, s=3):
    """c0: initial amounts; cmds[t][i]: command of cell i at step t (cmds[t][N-1] is ignored). -> list of profiles after each step."""
    N, c, out = len(c0), list(c0), []
    for cm in cmds:
        d = [x >> k for x in c]
        p = [(c[i] * cm[i]) >> s if i < N - 1 else 0 for i in range(N)]
        n = []
        for i in range(N):
            nb = (i > 0) + (i < N - 1)
            v = c[i] - nb * d[i] - p[i]
            if i > 0:
                v += d[i - 1] + p[i - 1]
            if i < N - 1:
                v += d[i + 1]
            n.append(v)
        c = n
        out.append(list(c))
    return out


def build_a(i, N, k, s):
    n = npl.Net()
    n.op("C", "relay", [])
    n.op("D", "relay", ["C"], addon=shr(k))
    if i > 0:
        n.op("O.dL", "relay", ["D"])                               # to the left neighbour
    if i < N - 1:
        n.op("O.dR", "relay", ["D"])                               # to the right neighbour
        n.op("A", "relay", [])                                     # this step's command
        n.op("Cx", "relay", ["C"])                                 # a spacer: the amount reaches the multiplier after the command
        n.op("Mp", "mul", ["Cx", "A"])
        n.op("P", "relay", ["Mp"], addon=shr(s))
        n.op("O.P", "relay", ["P"])
    out = "D"
    if 0 < i < N - 1:
        n.op("D2", "relay", ["D"], addon=shl(1))                   # 2 * d: it goes both ways
        out = "D2"
    if i < N - 1:
        n.op("O", "add", [out, "P"])
        out = "O"
    n.op("Ox", "relay", [out])
    n.op("KM", "const", const=(1 << 32) - 1)
    n.op("Ng", "mul", ["Ox", "KM"])                                # minus the total leaving: an add needs no operand ORDER, only no tie (a subtract's minuend must arrive first, and C's lane is the long one here)
    n.op("E", "add", ["C", "Ng"])
    n.op("O.E", "relay", ["E"])
    return n


def build_b(i, N):
    n = npl.Net()
    n.op("E", "relay", [])
    ins = []
    if i > 0:
        n.op("dL", "relay", [])
        n.op("pL", "relay", [])
        ins += ["dL", "pL"]
    if i < N - 1:
        n.op("dR", "relay", [])
        ins.append("dR")
    last = ins[0]
    for q, x in enumerate(ins[1:]):
        n.op(f"S{q}", "add", [last, x])
        last = f"S{q}"
    n.op("Cn", "add", ["E", last])
    n.op("O.C", "relay", ["Cn"])
    n.op("O.Obs", "relay", ["Cn"])
    return n


def flow_medium(g, N, T, k=3, s=3, name="FLOW", r0=3, c0=2, gap=5, rh=22, rgap=6):
    """N cells x T steps. Returns (entries {('C', i): cell, ('A', i, t): command entry}, exits {(i, t): amount after step t}, consts)."""
    ent, ex, consts, A, B = {}, {}, {}, {}, {}
    col = c0

    def place(n, entries, outs, nm, row, rows, cols):
        sg = fmt1._scratch(g)
        names, cs, _ = fmt1.place_net_tight(sg, n, nm, 2, 2, entries, rows, cols, pitch=3, gap=2, outs=outs)
        consts.update(cs)
        _, _, cmin, cmax = fmt1._bbox(sg)
        fmt1._transplant(g, sg, row, col, flip_h=False)
        return names, cmax - cmin + 1
    for t in range(T):
        wmax = 0
        for i in range(N):
            ents = ["C"] + (["A"] if i < N - 1 else [])
            outs = ["O.E"] + (["O.dL"] if i > 0 else []) + (["O.dR", "O.P"] if i < N - 1 else [])
            A[(i, t)], w = place(build_a(i, N, k, s), ents, outs, f"{name}.A{i}_{t}", r0 + i * (rh + rgap), rh, 30)
            wmax = max(wmax, w)
            if t == 0:
                ent[("C", i)] = A[(i, t)]["C"]
            if i < N - 1:
                ent[("A", i, t)] = A[(i, t)]["A"]
        col += wmax + gap
        if t:
            g.route_nets([(B[(i, t - 1)]["O.C"], A[(i, t)]["C"], {"spread": True}) for i in range(N)])
        wmax = 0
        for i in range(N):
            ents = ["E"] + (["dL", "pL"] if i > 0 else []) + (["dR"] if i < N - 1 else [])
            B[(i, t)], w = place(build_b(i, N), ents, ["O.C", "O.Obs"], f"{name}.B{i}_{t}", r0 + i * (rh + rgap), rh, 22)
            ex[(i, t)] = B[(i, t)]["O.Obs"]
            wmax = max(wmax, w)
        col += wmax + gap
        nets = []
        for i in range(N):
            nets.append((A[(i, t)]["O.E"], B[(i, t)]["E"], {"spread": True}))
            if i > 0:
                nets += [(A[(i - 1, t)]["O.dR"], B[(i, t)]["dL"], {"spread": True}), (A[(i - 1, t)]["O.P"], B[(i, t)]["pL"], {"spread": True})]
            if i < N - 1:
                nets.append((A[(i + 1, t)]["O.dL"], B[(i, t)]["dR"], {"spread": True}))
        g.route_nets(nets)
    return ent, ex, consts
