"""arith_blocks_v1.py -- ledger #1080: STORED, PRE-LAID-OUT blocks for the arithmetic plan library: a base stage with fixed cell positions and a rule for joining copies, so the
design is written down directly instead of being routed by the general placer.

Why: the general placer (routed_x) spends most of its cells on wire. Cells only talk to their neighbours, so a "relay" is a wire segment. A dot product of 8 terms came to 326 cells,
296 of them relays (ledger #1079). A block that puts each stage's cells next to the stage before it needs no long wires.

`mac_chain`: the multiply-accumulate chain, acc_k = acc_(k-1) + a_k * b_k (acc_0 = a_0 * b_0), 7 cells per stage, stage pitch 3 rows, 5 columns wide:

      col2   col3   col4
 R    A_k                          A_k, B_k  input cells (ram), A above P1 and B below it
 R+1  P1_k   MUL_k  P2_k           P1 priority (a,b arrive from n and s, leave east); MUL east; P2 priority (product from west, acc from north)
 R+2  B_k           ADD_k          ADD south (to the next stage)
 R+3                WIRE_k         one wire cell carries the running total to the next stage's P2 (R+3 is the next stage's R)

Stage 0 has no add: its product runs down column 4 through three wire cells into stage 1. The last add has no downstream and is the result cell `main.r`.
The priority cell in front of every two-operand cell is the compiler's own protocol (it serialises the two arrivals): the same cell types and masks the compiler writes.

`ramp_pipe` (ledger #1080, Alan's design): a feed pipe that runs north to south and carries a value past n "calc points". At the head of each point is a split (a ram cell with two
outputs: one east to the tap, one south down the pipe); between splits the pipe passes through an adder that adds the step. A start value in at the top therefore gives
start, start + step, start + 2 step, ... at taps 0, 1, 2, ...; the pipe's delay makes them arrive in order. Stage = split, tap, step constant, priority cell, adder (5 cells;
the last stage has only split and tap), so n taps are 5n - 3 cells. This is the LARGE form; the small form (one adder looped, the calc point reloading each new number) needs the
loop ring and is not built.

`matvec` (ledger #1082): y = A x for a constant m-by-n matrix A and a run-time vector x. m parallel multiply-accumulate chains side by side (3 columns each); the vector element x_j
runs along ONE feed line (row 3j, west to east) that splits into every chain: in each chain a ram cell with two outputs sends it down to that chain's stage j and on east. The
feed line crosses each chain's running total through a CROSS tile (core "cross": straight through both ways). The matrix entries are constant cells next to each multiplier.
Cells: 8n per chain, 7n - 1 for the last chain: 8n(m - 1) + 7n - 1 in all. Outputs: the last adder of chain i is the cell main.y<i+1>.
"""
from __future__ import annotations

import dataclasses
from typing import Dict, List, Sequence, Tuple

from icm_v3 import IcmV3Record

PITCH = 3
CELLS_PER_STAGE = 7                       # stage 0 also has 7: A, B, P1, MUL and three wires; the last stage has 6 (no trailing wire)
WIDTH = 5


def _ram_in(d: str) -> dict:
    return {"upstream_mask": [], "downstream_mask": [d]}


def _wire(u: str, d: str) -> dict:
    return {"fixed_mode": 0, "upstream_mask": [u], "downstream_mask": [d]}


def _pri(ups: Sequence[str], d: str) -> dict:
    return {"upstream_mask": list(ups), "downstream_mask": [d], "priority_rank_n": 0, "priority_rank_s": 0, "priority_rank_e": 0, "priority_rank_w": 0, "scheduling_mode": 0}


def mac_chain_cell_count(n: int) -> int:
    """Cells of an n-term multiply-accumulate chain (n >= 2): 7 per stage, one fewer for the last stage. Checked against what is built."""
    return CELLS_PER_STAGE * n - 1


def mac_chain(pairs: Sequence[Tuple[str, str, str]]) -> Tuple[List[IcmV3Record], Dict[str, List[Tuple[int, int]]], Tuple[int, int]]:
    """Build the chain. `pairs` = [(arg_a, arg_b, mul_name)] per term; mul_name names the multiply in the IR the front end writes (the input cells are called
    main.dynq_<mul_name>_a / _b, the compiler's own naming, so tools that read the IR still find them). Returns (records, arg_injections, result (row, col))."""
    n = len(pairs)
    if n < 2:
        raise ValueError("a multiply-accumulate chain needs at least two terms")
    recs: List[IcmV3Record] = []
    inj: Dict[str, List[Tuple[int, int]]] = {}

    def add(cell_id, r, c, core, cfg):
        recs.append(IcmV3Record(cell_id=cell_id, row=r, col=c, core=core, core_config=cfg))

    for k, (a, b, mn) in enumerate(pairs):
        R = PITCH * k
        add(f"main.dynq_{mn}_a", R, 2, "ram", _ram_in("s"))
        add(f"main.mac{k}_p1", R + 1, 2, "priority", _pri(["n", "s"], "e"))
        add(f"main.dynq_{mn}_b", R + 2, 2, "ram", _ram_in("n"))
        add(f"main.mac{k}_mul", R + 1, 3, "mul", {"upstream_mask": ["w"], "downstream_mask": ["e"], "second_output": 0})
        inj.setdefault(a, []).append((R, 2))
        inj.setdefault(b, []).append((R + 2, 2))
        if k == 0:
            add("main.mac0_w0", 1, 4, "ram", _wire("w", "s"))
            add("main.mac0_w1", 2, 4, "ram", _wire("n", "s"))
            add("main.mac0_w2", 3, 4, "ram", _wire("n", "s"))
        else:
            last = (k == n - 1)
            add(f"main.mac{k}_p2", R + 1, 4, "priority", _pri(["n", "w"], "s"))
            add("main.r" if last else f"main.mac{k}_add", R + 2, 4, "adder", {"upstream_mask": ["n"], "downstream_mask": [] if last else ["s"]})
            if not last:
                add(f"main.mac{k}_w", R + 3, 4, "ram", _wire("n", "s"))
    res = (PITCH * (n - 1) + 2, 4)
    return recs, inj, res


def as_result(template, records, arg_injections, result_cell):
    """A compile result (the front end's own dataclass) carrying this block instead of the placer's layout, so run_in_vm and the rest of the tooling work unchanged."""
    return dataclasses.replace(template, records=records, arg_injections=arg_injections, result_cell=result_cell, result_core="adder", seq_orders={},
                               positions={r.cell_id: (r.row, r.col) for r in records}, placer="stored_block:mac_chain", caveats=list(template.caveats))


def ramp_pipe_cell_count(n: int) -> int:
    """Cells of an n-tap ramp pipe: five per stage, two in the last."""
    return 5 * (n - 1) + 2


def ramp_pipe(n: int, step: int, start_name: str = "start", tap_prefix: str = "main.tap") -> Tuple[List[IcmV3Record], Dict[str, List[Tuple[int, int]]], List[Tuple[int, int]]]:
    """Build the ramp pipe. Returns (records, arg_injections, tap squares). `start_name` is the argument injected at the top split; tap k is the ram cell `<tap_prefix><k>` and
    holds start + k * step (mod 2^32). Column 4 is the pipe, column 5 the taps, column 3 the step constants."""
    if n < 2:
        raise ValueError("a ramp pipe needs at least two taps")
    recs: List[IcmV3Record] = []
    c = 4

    def add(cell_id, r, col, core, cfg, pre=None):
        recs.append(IcmV3Record(cell_id=cell_id, row=r, col=col, core=core, core_config=cfg, preload_value=pre))

    taps = []
    for k in range(n):
        r = PITCH * k
        add(f"main.ramp_s{k}", r, c, "ram", {"fixed_mode": 0, "upstream_mask": [] if k == 0 else ["n"], "downstream_mask": ["e"] + (["s"] if k < n - 1 else [])})
        add(f"{tap_prefix}{k}", r, c + 1, "ram", {"fixed_mode": 0, "upstream_mask": ["w"], "downstream_mask": []})
        taps.append((r, c + 1))
        if k < n - 1:
            add(f"main.ramp_k{k}", r + 1, c - 1, "ram", {"fixed_mode": 0, "downstream_mask": ["e"]}, step & 0xFFFFFFFF)
            add(f"main.ramp_p{k}", r + 1, c, "priority", _pri(["n", "w"], "s"))
            add(f"main.ramp_a{k}", r + 2, c, "adder", {"upstream_mask": ["n"], "downstream_mask": ["s"]})
    return recs, {start_name: [(0, c)]}, taps


def matvec_cell_count(m: int, n: int) -> int:
    """Cells of an m-by-n matrix-vector block: eight per stage in all chains but the last, which has seven per stage less one."""
    return 8 * n * (m - 1) + 7 * n - 1


def matvec(coeffs: Sequence[Sequence[int]], x_names: Sequence[str]) -> Tuple[List[IcmV3Record], Dict[str, List[Tuple[int, int]]], List[Tuple[int, int]]]:
    """Build the block for the constant matrix `coeffs` (m rows of n entries, taken mod 2^32) and the vector arguments `x_names` (n names). Returns (records, arg_injections,
    result squares, one per row in order). x_j is injected at chain 0's split on row 3j."""
    m, n = len(coeffs), len(x_names)
    if m < 1 or n < 2 or any(len(row) != n for row in coeffs):
        raise ValueError("matvec needs at least one row, at least two columns, and a rectangular matrix")
    recs: List[IcmV3Record] = []
    inj: Dict[str, List[Tuple[int, int]]] = {x: [] for x in x_names}
    exits: List[Tuple[int, int]] = []

    def add(cell_id, r, c, core, cfg, pre=None):
        recs.append(IcmV3Record(cell_id=cell_id, row=r, col=c, core=core, core_config=cfg, preload_value=pre))

    for i in range(m):
        b = 3 * i
        first, last = (i == 0), (i == m - 1)
        for j in range(n):
            R = PITCH * j
            tag = f"main.mv{i}_{j}"
            add(f"{tag}_a", R, b, "ram", {"fixed_mode": 0, "upstream_mask": [] if first else ["w"], "downstream_mask": ["s"] + ([] if last else ["e"])})
            if first:
                inj[x_names[j]].append((R, b))
            if not last:
                add(f"{tag}_lw", R, b + 1, "ram", _wire("w", "e"))
                if j == 0:
                    add(f"{tag}_lx", R, b + 2, "ram", _wire("w", "e"))
            if j >= 1:
                add(f"{tag}_x", R, b + 2, "cross", {"upstream_mask": ["n"] if last else ["n", "w"], "downstream_mask": ["s"] if last else ["s", "e"]})     # lanes: n->s (running total), w->e (feed line)
            add(f"{tag}_p1", R + 1, b, "priority", _pri(["n", "s"], "e"))
            add(f"{tag}_k", R + 2, b, "ram", {"fixed_mode": 0, "downstream_mask": ["n"]}, coeffs[i][j] & 0xFFFFFFFF)
            add(f"{tag}_mul", R + 1, b + 1, "mul", {"upstream_mask": ["w"], "downstream_mask": ["e"], "second_output": 0})
            if j == 0:
                add(f"{tag}_w1", 1, b + 2, "ram", _wire("w", "s"))
                add(f"{tag}_w2", 2, b + 2, "ram", _wire("n", "s"))
            else:
                add(f"{tag}_p2", R + 1, b + 2, "priority", _pri(["n", "w"], "s"))
                lastj = (j == n - 1)
                add(f"main.y{i + 1}" if lastj else f"{tag}_add", R + 2, b + 2, "adder", {"upstream_mask": ["n"], "downstream_mask": [] if lastj else ["s"]})
                if lastj:
                    exits.append((R + 2, b + 2))
    return recs, inj, exits
