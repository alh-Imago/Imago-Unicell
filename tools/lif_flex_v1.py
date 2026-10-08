"""tools/lif_flex_v1.py -- ledger #1030: a LEAKY-INTEGRATE-AND-FIRE neuron on the flex cells, "time unrolled into space" (Alan: revisit the LIF neuron with the new designs).

The old sketch (archeology: neural_pond_design.md / lif_neuron_reference.v) was a 5-cell NOR-latch circuit with a bitwise-OR leak approximation and was never built on the flex family.  The flex generator refuses
feedback loops, so the membrane cannot circulate in a ring; instead each TIME STEP is a small stage of cells and the membrane value flows from one stage to the next (time becomes distance).  One stage:

    L  = V_prev >> k            (leak: a relay with a right-shift addon)
    D  = V_prev - L             (subtract; V_prev arrives first)
    V  = D + I_t                (the input current of this step)
    S  = [V >= TH]              (comparator: 1 = spike)
    R  = S << log2(TH)          (relay with a left-shift addon: S * TH, TH a power of two)
    V' = V - R                  (soft reset: a spike removes one threshold's worth)

Entries I_0 .. I_{T-1} (one word per step); exits S_0 .. S_{T-1} (spike 0/1) and VF (the membrane after the last step).  Step 0 starts from an empty membrane (V = I_0).
`lif_ref` is the exact integer reference.  Netlist placed with the tight placer; the cells are the existing flex cells only."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_add_v1 as fadd  # noqa: E402
import netplace_v1 as npl  # noqa: E402
import fp_mul_tight_v1 as fmt1  # noqa: E402

shl, shr = fadd.shl, fadd.shr


def lif_ref(currents, k=3, th=256, v0=0, mask=(1 << 32) - 1):
    """-> (spikes, final membrane).  v <- v - (v >> k) + I;  spike if v >= th;  v <- v - th on a spike."""
    v, sp = v0, []
    for t, i in enumerate(currents):
        if t > 0 or v0:
            v = v - (v >> k)
        v = (v + i) & mask
        s = 1 if v >= th else 0
        sp.append(s)
        v = (v - (th if s else 0)) & mask
    return sp, v


def build_stage(k=3, th=256, first=False):
    """One time step as its own small netlist. Entries: PV (the membrane from the previous step; absent in the first stage) and I (this step's input); exits O.S (spike) and O.W (the membrane handed on)."""
    assert th & (th - 1) == 0, "the threshold is a power of two (the reset is a shift)"
    lg = th.bit_length() - 1
    n = npl.Net()
    kk = (1 << k) - 1
    if first:
        n.op("I", "relay", [])
        n.op("V", "relay", ["I"])
    else:
        # leak without a subtraction (whose operand order the layout engine would have to enforce): v - (v >> k) == (v * (2^k - 1) + (2^k - 1)) >> k for v >= 0
        n.op("PV", "relay", [])
        n.op("I", "relay", [])
        n.op("KC", "const", const=kk)
        n.op("M", "mul", ["PV", "KC"])
        n.op("KC2", "const", const=kk)
        n.op("A", "add", ["M", "KC2"])
        n.op("D", "relay", ["A"], addon=shr(k))
        n.op("V", "add", ["D", "I"])
    n.op("S", "cmp", ["V"], thr=th)
    n.op("O.S", "relay", ["S"])
    n.op("KN", "const", const=(1 << 32) - th)                      # -th (32-bit two's complement): the reset adds S * (-th)
    n.op("R", "mul", ["S", "KN"])
    n.op("Q", "relay", ["V"])                                      # a spacer: V reaches the final adder before the reset term
    n.op("O.W", "add", ["Q", "R"])
    return n


def lif_neuron(g, T, k=3, th=256, name="LIF", r0=3, c0=2, gap=6, rows=14, cols=26):
    """Place the T-step neuron on grid g as T stage tiles side by side, the membrane lane from each tile into the next.  Returns (entries {I_t: cell}, exits {S_t.., VF: cell}, consts)."""
    ent, ex, consts = {}, {}, {}
    prevW, col = None, c0
    for t in range(T):
        sg = fmt1._scratch(g)
        first = (t == 0)
        n = build_stage(k, th, first)
        entries = ["I"] if first else ["PV", "I"]
        nm, cs, _ = fmt1.place_net_tight(sg, n, f"{name}.T{t}", 2, 2, entries, rows, cols, pitch=3, gap=2, outs=["O.S", "O.W"])
        consts.update(cs)
        _, _, cmin, cmax = fmt1._bbox(sg)
        fmt1._transplant(g, sg, r0, col, flip_h=False)
        ent[f"I{t}"] = nm["I"]
        ex[f"S{t}"] = nm["O.S"]
        if prevW is not None:
            g.route_nets([(prevW, nm["PV"], {"spread": True})])
        prevW = nm["O.W"]
        col += (cmax - cmin + 1) + gap
    ex["VF"] = prevW
    return ent, ex, consts


# ----------------------------------------------------------------------------------------------------------------------------------
# a NETWORK of N neurons: the spike of neuron i at step t adds W[i][j] to neuron j's membrane at step t+1 (excitatory, non-negative weights; the unrolled graph stays feed-forward, so the
# generator accepts it).  Neuron j at step t:  v <- v - (v >> k) + I_j[t] + sum_i W[i][j] * S_i[t-1];  spike if v >= th;  v <- v - th on a spike.
def net_ref(ext, W, k=3, th=256):
    """ext[j] = list of T external currents of neuron j.  -> (spikes[j][t], final membranes)."""
    N, T = len(ext), len(ext[0])
    v, prev, sp = [0] * N, [0] * N, [[] for _ in range(N)]
    for t in range(T):
        cur = []
        for j in range(N):
            x = v[j] - (v[j] >> k) if t else 0
            x += ext[j][t] + sum(W[i][j] * prev[i] for i in range(N))
            s = 1 if x >= th else 0
            sp[j].append(s)
            cur.append(x - (th if s else 0))
        v, prev = cur, [sp[j][t] for j in range(N)]
    return sp, v


def build_tile(k, th, first, srcs, dsts, W, j):
    """Stage tile of neuron j: entries PV, I and C<i> for every source neuron i; exits O.S, O.W and O.C<d> for every target d (S * weight)."""
    n = npl.Net()
    kk = (1 << k) - 1
    if first:
        n.op("I", "relay", [])
        n.op("V0", "relay", ["I"])
    else:
        n.op("PV", "relay", [])
        n.op("I", "relay", [])
        n.op("KC", "const", const=kk)
        n.op("M", "mul", ["PV", "KC"])
        n.op("KC2", "const", const=kk)
        n.op("A", "add", ["M", "KC2"])
        n.op("D", "relay", ["A"], addon=shr(k))
        n.op("V0", "add", ["D", "I"])
        for i in srcs:
            n.op(f"C{i}", "relay", [])
    last = "V0"
    for i in srcs:
        if not first:
            n.op(f"VC{i}", "add", [last, f"C{i}"])
            last = f"VC{i}"
    n.op("V", "relay", [last]) if last != "V0" else None
    vv = "V" if last != "V0" else "V0"
    n.op("S", "cmp", [vv], thr=th)
    n.op("O.S", "relay", ["S"])
    for d in dsts:
        n.op(f"KW{d}", "const", const=W[j][d])
        n.op(f"O.C{d}", "mul", ["S", f"KW{d}"])
    n.op("KN", "const", const=(1 << 32) - th)
    n.op("R", "mul", ["S", "KN"])
    n.op("Q", "relay", [vv])
    n.op("O.W", "add", ["Q", "R"])
    return n


def lif_network(g, N, T, W, k=3, th=256, name="NET", r0=3, c0=2, gap=6, rows=24, cols=34, rgap=10):
    """N neurons x T steps as a grid of tiles (row j = neuron j, column t = step), lanes: membrane along the row, spike*weight from tile (i, t) into tile (j, t+1).
    Returns (entries {(j, t): cell}, exits {(j, t): spike cell, (j, 'VF'): final membrane}, consts)."""
    srcs = {j: [i for i in range(N) if W[i][j]] for j in range(N)}
    dsts = {i: [j for j in range(N) if W[i][j]] for i in range(N)}
    ent, ex, consts, nm = {}, {}, {}, {}
    col, row = c0, r0
    widths = []
    for t in range(T):
        wmax = 0
        for j in range(N):
            sg = fmt1._scratch(g)
            first = t == 0
            n = build_tile(k, th, first, srcs[j], dsts[j], W, j)
            entries = ["I"] if first else ["PV", "I"] + [f"C{i}" for i in srcs[j]]
            outs = ["O.S", "O.W"] + [f"O.C{d}" for d in dsts[j]]
            names, cs, _ = fmt1.place_net_tight(sg, n, f"{name}.N{j}T{t}", 2, 2, entries, rows, cols, pitch=3, gap=2, outs=outs)
            consts.update(cs)
            _, _, cmin, cmax = fmt1._bbox(sg)
            fmt1._transplant(g, sg, row + j * (rows + rgap), col, flip_h=False)
            nm[(j, t)] = names
            wmax = max(wmax, cmax - cmin + 1)
            ent[(j, t)] = names["I"]
            ex[(j, t)] = names["O.S"]
        col += wmax + gap
        if t:
            nets = [(nm[(j, t - 1)]["O.W"], nm[(j, t)]["PV"], {"spread": True}) for j in range(N)]
            nets += [(nm[(i, t - 1)][f"O.C{j}"], nm[(j, t)][f"C{i}"], {"spread": True}) for i in range(N) for j in dsts[i]]
            g.route_nets(nets)
    for j in range(N):
        ex[(j, "VF")] = nm[(j, T - 1)]["O.W"]
    return ent, ex, consts
