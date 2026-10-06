#!/usr/bin/env python3
"""
flexsub_icm_generate_v1.py -- STEP 2, SECOND SLICE of the Flex-Sub assembler plan: read an ICM-VIX file as
a map and emit the design it describes as Verilog, into a flat self-contained folder. `sub` family only
(`*_cell_v4s.v`: straight wiring, fixed 1-cycle latency, no ack -- Alan's ruling #924, "just physics").

Reached through project_assemble_v1.py:   -s sub --icm FILE.icm-hier.json --output DIR [--no-align]

HOW IT TRANSLATES (each rule below was read from the real cells / the VM, then checked by simulation):
  * wiring comes from the cells' masks + grid positions (flexsub_icm_netlist_v1), NOT from the advisory
    `connections` list.
  * every v4s cell has exactly ONE cycle of latency (adder_cell_v4s registers its sum, ram_cell_v4s registers
    its data) -- the same as one VM tick per hop, so hop depth IS cycle count.
  * the v4s adder has a single valid_in for BOTH operands, so the operands of ONE item must be present in the
    same cycle. For a single one-shot value this happens by itself: a flowing ram_cell_v4s HOLDS its data_reg
    until the next valid, so an early operand just sits on its wire (checked: an unaligned one-shot is still
    right). It breaks for BACK-TO-BACK items: item n+1's early operand overwrites the held one before item n's
    late operand arrives, mixing items (checked: unaligned back-to-back results were 4321/7210/9100 instead of
    10/100/1000). So the EARLIER operand's path is padded with (depth difference) flowing ram relay cells --
    the project's own "delay cells" (#5, reused by dsp_latency_v1.py in the VM) -- never new hardware. Aligned,
    the design is a full pipeline: one result per cycle. `--no-align` omits the padding (the negative control).
  * operand roles follow the VM's arrival-order rule: A = the first (earlier) arrival, B = the second. The
    static hop-depth estimate matched the real VM on 7/7 adders (tests/test_flexsub_icm_netlist_v1.py).
  * valid_in of an adder is operand B's valid (aligned, so identical to A's) -- wiring, not control.

SCOPE OF THIS SLICE (refused with the reason, never guessed): cores ram and adder only; acyclic; every adder
has exactly two sources at DIFFERENT arrival times; no merges, no constants, no addon_config. Not yet built:
merges (gated OR, Alan: "a free OR"), constants, branch (no v4s branch exists), single-stream operand pairs,
and the whole flex family (ack join on fan-out).

Constants: a constant source is a fixed-mode ram (always valid); its compiler-inserted relay chain just flows. The inputs must
not be presented until the constants have propagated -- ASSEMBLY.json `settle_cycles` says how many cycles after cfg_valid.

Output folder: <top>.v (the design), the cell files + dependencies, <top>.ys (synth_gowin), ASSEMBLY.json.
The top has ports clk, rst, cfg_valid (one pulse after reset arms every cell), and for each io_name:
in_<name>_data[31:0] / in_<name>_valid, out_<name>_data[31:0] / out_<name>_valid.
"""
import copy
import json
import os
import re
import shutil
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)
import flexsub_icm_netlist_v1 as nl  # noqa: E402
import flexsub_assemble_v1 as fsa  # noqa: E402

class IcmGenError(ValueError):
    pass


def _ident(cid):
    return "c_" + re.sub(r"[^A-Za-z0-9_]", "_", cid)


# Per-core translation table. "single": one data input; "pair": two operands (A first, B second, VM arrival-order rule).
# Every module's port list and timing was read from its source: each is exactly ONE cycle of latency.
CORES = {
    "ram": {"kind": "single", "module": "ram_cell_v4s"},
    "comparator": {"kind": "single", "module": "compare_cell_v4s"},    # signed(data) >= threshold -> 0/1, same as the VM
    "adder": {"kind": "pair", "module": "adder_cell_v4s"},
    "mul": {"kind": "pair", "module": "mul_cell_v4s"},                  # low 32 bits of the product
    # nano: first arrival = HELD operand A (registered, loaded by load_hold), second = FLOWING operand B. The held register
    # is loaded a cycle before the gate sees it, so A must arrive exactly ONE cycle before B (unlike adder/mul).
    "nano": {"kind": "pair", "module": "nano_cell_v4s", "hold_flow": True},
    # branch (Alan #935: branch_cell_v4s completes the sub set). One ICM input, a held-reference compare, per-outcome routing to FACES;
    # lowered by lower_branches() below onto the cell's two inputs and two output ports.
    "branch": {"kind": "branch", "module": "branch_cell_v4s"},
    # sequencer (Alan #937): on sub it "loses the ack side and goes back to just the clock pulse side". The VM advances it when a consumer drains
    # its offer (a backward ack); sequencer_cell_v4s instead takes an external `advance_in` PULSE. Exposed as a top-level adv_<name> input,
    # presented on the same cycle as the design's other arguments. The cell pulses the NEXT index's value, so the stored values are rotated one
    # step so the pulsed sequence starts at VALUE_0 and wraps like the VM's.
    "sequencer": {"kind": "tick", "module": "sequencer_cell_v4s"},
    # accumulator / latch (Alan #938). In the VM a continuous-mode accumulator offers its running total, and a latch its 0/1 state, ALWAYS VALID
    # (a LEVEL source); the v4s cells pulse valid_out only on an update. Rule: a level source's valid is held high; its valid_out pulse is unused.
    # A pulse-mode accumulator already matches (a discrete event on the threshold crossing), so it stays an ordinary timed source.
    "accumulator": {"kind": "level", "module": "accumulator_cell_v4s"},
    "latch": {"kind": "level", "module": "latch_cell_v4s"},
}
_LEVEL_ALLOWED = {"accumulator": {"inc_dir", "dec_dir", "downstream_mask", "step_amount", "pulse_mode", "threshold"},
                  "latch": {"set_dir", "clear_dir", "downstream_mask", "toggle_dir"}}


def is_level(r):
    """A VM level source: always-valid output. A continuous-mode accumulator or any latch (pulse mode is a discrete event, not a level)."""
    return r.core == "latch" or (r.core == "accumulator" and not (r.core_config or {}).get("pulse_mode", 0))
# The topology codes nano_cell_v4s actually implements (its `default` silently passes the held value -- never translate those).
NANO_TOPOLOGIES = {0x000, 0x02C, 0x001, 0x002, 0x004, 0x007, 0x024, 0x027, 0x0BC, 0x03C, 0x030, 0x0B0}
NANO_BENIGN_KEYS = {"ready", "routing_mask", "topology"}
SUPPORTED_CORES = set(CORES)
_SHIFT_COARSE = (1, 2, 4, 8, 12, 16, 20, 24, 28)    # the VM's/RTL's supported coarse taps (shift_lane_addon_v2)


_ADDON_KEYS = {"nibble_mask", "mask_en", "shift_amt", "shift_en", "direction", "shift_fine", "lane_cut", "invert_en"}
_M32 = 0xFFFFFFFF


def addon_bit_map(ad):
    """The addon chain as a fixed per-bit WIRING MAP. Alan #939: with the sub variant fully fixed at build time, mask / shift / invert (and the
    lane cut) are just wiring -- no cell, no latency. The VM applies the chain to every core's offered value as a pure function of 32 bits with
    constant config (apply_addons: nibble_mask -> fine shift -> coarse lane shift (+ lane_cut on right shifts) -> invert), so each OUTPUT bit is
    a constant, an input bit, or its inverse. Computed symbolically by mirroring apply_addons step for step; tests check it against the VM's own
    function over structured and random configs. Returns 32 entries: ("c", 0|1) or ("v", input_bit, inverted)."""
    bits = [("v", k, 0) for k in range(32)]

    def shift(bs, n, right):
        out = []
        for i in range(32):
            j = i + n if right else i - n
            out.append(bs[j] if 0 <= j < 32 else ("c", 0))
        return out

    def kill(bs, mask):
        return [bs[i] if (mask >> i) & 1 else ("c", 0) for i in range(32)]
    if ad.get("mask_en"):
        nm = ad.get("nibble_mask", 0)
        keep = 0
        for nib in range(8):
            if not ((nm >> nib) & 1):
                keep |= 0xF << (4 * nib)
        bits = kill(bits, keep)
    shift_en, direction = ad.get("shift_en", 0), ad.get("direction", 0)
    fine, amt = ad.get("shift_fine", 0) & 3, ad.get("shift_amt", 0)
    if shift_en and fine:
        bits = shift(bits, fine, bool(direction))
    if shift_en and amt in _SHIFT_COARSE:                        # an unsupported amount is a deliberate no-op (as in the RTL)
        if direction:
            bits = shift(bits, amt, True)
            lane_cut = ad.get("lane_cut", 0)
            lane_s = amt + fine
            lane_ones = (1 << lane_s) - 1
            lane_kill = _M32
            if lane_cut & 1:
                lane_kill &= ~((lane_ones << 8) >> lane_s) & _M32
            if lane_cut & 2:
                lane_kill &= ~((lane_ones << 16) >> lane_s) & _M32
            if lane_cut & 4:
                lane_kill &= ~((lane_ones << 24) >> lane_s) & _M32
            bits = kill(bits, lane_kill)
        else:
            bits = shift(bits, amt, False)
    if ad.get("invert_en"):
        bits = [("c", 1 - b[1]) if b[0] == "c" else ("v", b[1], 1 - b[2]) for b in bits]
    return bits


def addon_is_identity(bits):
    return all(b == ("v", k, 0) for k, b in enumerate(bits))


def addon_apply(bits, value):
    """Evaluate a bit map on an integer (for checking against the VM's apply_addons)."""
    out = 0
    for k, b in enumerate(bits):
        v = b[1] if b[0] == "c" else (((value >> b[1]) & 1) ^ b[2])
        out |= v << k
    return out


def addon_expr(bits, raw):
    """A Verilog concatenation (MSB first) realising the map over the 32-bit net `raw`."""
    return "{" + ", ".join((f"1'b{b[1]}" if b[0] == "c" else f"{'~' if b[2] else ''}{raw}[{b[1]}]") for b in reversed(bits)) + "}"


def _const_set(cells, inputs):
    """Constant-valued nodes: preloaded / fixed-mode source rams, and anything fed only by them (always available)."""
    srcs = {c: [q for lst in inputs.get(c, {}).values() for q, _ in lst] for c in cells}
    const = {c for c, r in cells.items() if not srcs[c] and (r.preload_value is not None or (r.core_config or {}).get("fixed_mode"))}
    grew = True
    while grew:
        grew = False
        for c in cells:
            if c not in const and srcs[c] and all(q in const for q in srcs[c]) and not cells[c].io_name:   # an io_name = an external input too
                const.add(c)
                grew = True
    return const


_OUTCOMES = ("low", "equal", "high")
_FACE_OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}


def lower_branches(cells, inputs, outputs):
    """Lower each ICM `branch` onto branch_cell_v4s. The VM's branch is a HELD-REFERENCE comparator (read from _deliver_branch): the
    FIRST arrival on its one upstream face is captured as the reference and produces nothing; every later arrival is compared
    (signed) with it; the outcome (low / equal / high) picks {value source, emit, route faces}; with `rolling_mode` the value just
    compared becomes the new reference. Onto the cell's two dedicated inputs that is:
      const_ref -- the branch is fed by a MERGE of a constant and a stream (how the hand-built cordic loads its reference: the
                   constant arrives first). The merge disappears: in1 = the stream, in2 = the constant (flowing, valid = the
                   constant's own valid), so every stream value is compared with it. [needs rolling_mode = 0]
      rolling   -- rolling_mode = 1: the stream feeds BOTH inputs and in2 is a HELD input loaded by the same valid: the compare uses
                   the previous value (the cell reads its held register before updating it) and the very first arrival finds nothing
                   loaded, so it becomes the reference without an output -- exactly the VM.
    Refused, each with its reason: a reference that is the first arrival of a plain stream with rolling off (it needs a
    "first only" state bit -- control, which the sub family does not have); value sources / fixed values that differ among the
    emitting outcomes (the cell has ONE shared emit_source); more than two routed faces (the cell has two outputs); a routed face
    with no cell on it; a branch fed only by constants.
    Returns (cells, inputs, outputs, plans, problems)."""
    cells = dict(cells)
    inputs = {k: {r: list(v) for r, v in d.items()} for k, d in inputs.items()}
    outputs = {k: list(v) for k, v in outputs.items()}
    plans, problems = {}, []
    const = _const_set(cells, inputs)
    for bid in [c for c, r in cells.items() if r.core == "branch"]:
        cfg = cells[bid].core_config or {}
        srcs = inputs.get(bid, {}).get("in", [])
        if len(srcs) != 1:
            problems.append(f"{bid}: branch has {len(srcs)} sources; the ICM branch has exactly one upstream face")
            continue
        s0 = srcs[0][0]
        vs = {k: int(cfg.get(f"value_source_{k}", 0)) for k in _OUTCOMES}
        fv = {k: int(cfg.get(f"fixed_value_{k}", 0)) for k in _OUTCOMES}
        em = {k: int(cfg.get(f"emit_{k}", 1)) for k in _OUTCOMES}
        routes = {k: [str(d).upper() for d in (cfg.get(f"route_{k}") or [])] for k in _OUTCOMES}
        emitting = [k for k in _OUTCOMES if em[k]]
        if len({vs[k] for k in emitting}) > 1:
            problems.append(f"{bid}: value_source differs among the emitting outcomes {({k: vs[k] for k in emitting})} -- the cell has ONE shared emit_source")
            continue
        fixed_source = bool(emitting) and vs[emitting[0]] == 1
        if fixed_source and len({fv[k] & 0x7F for k in emitting}) > 1:
            problems.append(f"{bid}: fixed_value differs among the emitting outcomes -- the cell has ONE shared emit constant")
            continue
        faces = []
        for k in emitting:
            for d in routes[k]:
                if d not in faces:
                    faces.append(d)
        if len(faces) > 2:
            problems.append(f"{bid}: routes to {len(faces)} distinct faces {faces}; branch_cell_v4s has two outputs")
            continue
        port = {d: i + 1 for i, d in enumerate(faces)}
        consumers = {}
        for dst, roles in inputs.items():
            for lst in roles.values():
                for q, face_at_dst in lst:
                    if q == bid:
                        consumers[_FACE_OPP[face_at_dst]] = dst
        missing = [d for d in faces if d not in consumers]
        if missing:
            problems.append(f"{bid}: routes to face(s) {missing} where no cell listens -- an external/dangling branch output is not translated")
            continue
        rolling = bool(cfg.get("rolling_mode", 0))
        m = cells[s0]
        plan_ = {"emit_source": 0 if fixed_source else 1, "emit_fixed": (fv[emitting[0]] & 0x7F) if fixed_source else 0,
                 "route_bits": {k: sum(1 << (port[d] - 1) for d in routes[k]) if em[k] else 0 for k in _OUTCOMES},
                 "ports": port, "rolling": rolling, "stream": s0, "const_ref": None}
        if s0 in const:
            problems.append(f"{bid}: fed only by a constant ({s0}) -- no stream to compare")
            continue
        m_srcs = [q for q, _ in inputs.get(s0, {}).get("in", [])]
        graph_stream = (m.core == "ram" and not m.addon_config and outputs.get(s0) == [bid] and len(m_srcs) == 2
                        and sum(q in const for q in m_srcs) == 1)
        entry_stream = (m.core == "ram" and not m.addon_config and outputs.get(s0) == [bid] and len(m_srcs) == 1
                        and m_srcs[0] in const and bool(m.io_name))      # the merge's stream is its OWN external entry (cordic's z_input)
        if graph_stream or entry_stream:
            if rolling:
                problems.append(f"{bid}: a constant-reference merge together with rolling_mode (a constant first reference THEN rolling) needs a mux -- not translated")
                continue
            if graph_stream:
                k = next(q for q in m_srcs if q in const)
                x = next(q for q in m_srcs if q not in const)
                face_x = next(f for q, f in inputs[s0]["in"] if q == x)
                inputs[bid]["in"] = [(x, face_x)]                       # the merge is removed: the stream feeds the branch directly
                outputs[x] = [bid if q == s0 else q for q in outputs[x]]
                outputs[k] = [bid if q == s0 else q for q in outputs[k]]
                plan_.update({"mode": "const_ref", "stream": x, "const_ref": k, "merge_removed": s0})
            else:
                k = m_srcs[0]
                inputs[bid].pop("in", None)                             # the branch BECOMES the entry point, under the merge's io_name
                outputs[k] = [bid if q == s0 else q for q in outputs[k]]
                nb = copy.copy(cells[bid])
                nb.io_name = m.io_name
                cells[bid] = nb
                plan_.update({"mode": "const_ref", "stream": None, "const_ref": k, "merge_removed": s0, "entry_io": m.io_name})
            del cells[s0], inputs[s0], outputs[s0]
        elif rolling:
            plan_["mode"] = "rolling"
        else:
            problems.append(f"{bid}: the reference is the FIRST ARRIVAL of a plain stream with rolling_mode off -- holding only the first value needs a "
                            f"'first only' state bit (control), which the sub family does not have. (Representable: a constant reference via a merge, or rolling_mode.)")
            continue
        plans[bid] = plan_
    return cells, inputs, outputs, plans, problems


# A multiplier realisation says what it NEEDS; the MAN says what the card HAS (Alan #942: the DSP type, availability and other resources are held in the
# MAN and used by the assembler -- nothing about a vendor or a primitive is assumed here).
#   lut  -- mul_cell_v4s: the exact low-32-bit LUT multiplier. Its cost is a MEASURED property of the cell per logic unit (#901: ~4,277 LUT4, flattened,
#           yosys synth_gowin); a card whose logic unit has no measured cost simply cannot be budget-checked, and the record says so.
#   dsp2 -- mul_cell_v4s_dsp2: one instance of the DSP primitive it instantiates (MULT36X36); the same ports, the same exact product and the same ONE-cycle
#           latency, so a drop-in. How many instances the card can host = its DSP blocks / blocks_per_instance, both read from the MAN.
# The plain-`a*b` variant (mul_cell_v4s_dsp) is NOT used (yosys never maps it to a DSP: the failed #901 experiment). mul_cell_v4s_dsp3 (time-multiplexed,
# 4 states) is NOT in the automatic ladder: multi-cycle latency would drop the WHOLE design's item rate to one per four cycles -- a contract change.
# The LUT multiplier's cost depends on the SYNTHESIS FLOW (ledger #949/#950): 4,277 LUT4 is the default (wide-LUT) flow's figure (#901); under -nowidelut a whole 3-multiplier +
# 2-adder design is 4,195 LUT4, i.e. at most ~1,398 per multiplier (the bare cells measure 1,118 sub / 1,332 flex) -- an upper bound, deliberately conservative.
MUL_REALISATIONS = {"lut": {"module": "mul_cell_v4s", "cost": {"LUT4": {"default": 4277, "nowidelut": 1398}}},
                    "dsp2": {"module": "mul_cell_v4s_dsp2", "primitive": "MULT36X36"}}
MUL_MODULES = {k: v["module"] for k, v in MUL_REALISATIONS.items()}
BUILT_WIDTH = 32     # the width every --icm generator builds today (ledger #958: a declared min_bit_width above this is refused)
FLEX_STAGE1_CORES = {"ram", "adder", "mul", "nano", "comparator", "accumulator", "latch", "branch", "sequencer"}
LUT_BUDGET_FRACTION = 0.9


def dsp_instances(man, primitive):
    """How many instances of `primitive` the card can host, from the MAN alone: floor(DSP blocks / blocks_per_instance). None if the MAN does not list the
    primitive, lists no DSP blocks, or gives no sharing ratio -- then the card offers nothing the assembler can use."""
    if not man:
        return None
    pr = (man.get("dsp_primitives") or {}).get(primitive)
    blocks, bpi = man.get("dsp_blocks"), (pr or {}).get("blocks_per_instance")
    if not pr or not blocks or not bpi:
        return None
    return int(blocks / bpi + 1e-9)


def choose_multipliers(mul_cells, man, mode, nowidelut=False):
    """Realise each `mul` as the DSP cell while the card (per its MAN) can host more of the primitive it needs, else as the LUT multiplier; refuse if even
    that cannot fit. Both are exact low-32-bit products with the same ports and the same ONE-cycle latency, so the choice never changes a result or the
    timing -- only what the card has to pay. Returns (impl: cell -> 'dsp2'|'lut', info dict)."""
    cells = sorted(mul_cells)
    n = len(cells)
    prim = MUL_REALISATIONS["dsp2"]["primitive"]
    avail = dsp_instances(man, prim)
    if mode == "lut":
        n_dsp = 0
    elif mode == "dsp":
        if avail is None:
            raise IcmGenError(f"--mul dsp needs the MAN to list the {prim} primitive under device.dsp.primitives (with the card's DSP block count and its "
                              f"blocks_per_instance); this MAN does not")
        if n > avail:
            raise IcmGenError(f"--mul dsp: {n} multipliers but the card can host only {avail} {prim} instance(s) "
                              f"({man.get('dsp_blocks')} DSP blocks / {man['dsp_primitives'][prim]['blocks_per_instance']} per instance, from its MAN)")
        n_dsp = n
    else:                                                     # auto: DSP while the card can host more, LUT as the fall back
        n_dsp = min(n, avail) if avail else 0
    impl = {c: ("dsp2" if k < n_dsp else "lut") for k, c in enumerate(cells)}
    n_lut = n - n_dsp
    unit, total = (man or {}).get("logic_unit"), (man or {}).get("logic_total")
    flow = "nowidelut" if nowidelut else "default"
    cost = (MUL_REALISATIONS["lut"]["cost"].get(unit) or {}).get(flow)
    checked = bool(n_lut and cost and total)
    if checked and n_lut * cost > LUT_BUDGET_FRACTION * total:
        raise IcmGenError(f"{n} multipliers: {n_dsp} fit in the card's {avail or 0} {prim} instance(s), and the other {n_lut} would be LUT multipliers at "
                          f"~{cost} {unit} each = ~{n_lut * cost}, more than {int(LUT_BUDGET_FRACTION * 100)}% of the card's {total} {unit}. "
                          f"The card's resources are used up -- not translated.")
    if n_lut and not checked:
        budget = ("no MAN: the LUT budget cannot be checked" if man is None else
                  f"the card's logic unit is {unit!r} and the LUT multiplier has no measured cost in that unit: the LUT budget cannot be checked")
    else:
        budget = "checked" if n_lut else "not needed (no LUT multipliers)"
    why = ("no MAN given: no resource information, so the always-exact LUT multiplier is used" if man is None and mode == "auto" else
           f"the MAN does not list {prim} under device.dsp.primitives (or lists no DSP blocks): the card offers no DSP the assembler can use -> LUT multipliers"
           if mode == "auto" and avail is None else
           f"--mul {mode}" if mode != "auto" else
           f"auto: DSP while the card's {avail} {prim} instance(s) last, LUT fall back for the remaining {n_lut}" if n_lut else
           f"auto: all {n} fit in the card's {avail} {prim} instance(s)")
    return impl, {"mode": mode, "dsp2": [c for c in cells if impl[c] == "dsp2"], "lut": [c for c in cells if impl[c] == "lut"],
                  "dsp_primitive": prim, "dsp_instances_available": avail, "dsp_abilities_in_man": (man or {}).get("dsp_abilities", []),
                  "logic_unit": unit, "synth_flow": flow, "lut_multiplier_cost_estimate": (n_lut * cost) if cost else None, "lut_budget": budget, "reason": why}


def plan(icm_path, align=True, man=None, mul_mode="auto", family="sub", nowidelut=False):
    """Everything the emitter needs, with every refusal raised here. Returns a plain dict."""
    doc, recs, cells, edges, inputs, outputs, ext_out, warnings = nl.extract(icm_path)
    declared_width = getattr(doc, "min_bit_width", None)         # the design's DECLARED minimum bit width (ledger #958); None = absent = 32
    problems = []
    if declared_width is not None and declared_width > BUILT_WIDTH:
        problems.append(f"the design declares min_bit_width = {declared_width} in its header, but this generator builds {BUILT_WIDTH}-bit designs only (width plumbing is not built yet): "
                        f"a design that needs at least {declared_width} bits cannot be met by a {BUILT_WIDTH}-bit build, so it is refused rather than silently built too narrow "
                        f"(a declared minimum up to {BUILT_WIDTH} IS met: building wider than the minimum satisfies it)")
    for w_ in warnings:                    # a sender facing a neighbour that does NOT listen on that face is a malformed design, not a note
        if "output dropped" in w_:
            problems.append(f"{w_}. In the VM that offer is never accepted and the sender stalls for ever; fixed-latency wiring would silently drop it, "
                            f"which is a different behaviour -- fix the wiring (the neighbour must listen on the opposite face).")
    # priority arbiters that only serialised two operands onto one input are eliminated (dedicated ports replace them)
    cells, inputs, outputs, tiekeys, eliminated, pri_problems = nl.eliminate_priority(cells, inputs, outputs)
    problems += pri_problems
    cells, inputs, outputs, branch_plans, br_problems = lower_branches(cells, inputs, outputs)
    problems += br_problems
    # --- the design's OUTPUTS, and what is dead. A cell with a downstream face that LEAVES the grid is offering to the outside world (that is
    # what the VM does with it), so it is an output -- even if it also feeds other cells. Only a design with NO such cell (hand-built exits that
    # simply have nothing downstream) falls back to "a cell with nothing downstream". Found by a compiled loop: the compiler's result cell also fed
    # unrolled iterations nobody uses, and the LAST of those dead adders was the only cell with no outgoing edge -- the old rule exported IT.
    CYCLE_MSG = ("the design has a cycle (feedback). Counted loops compile UNROLLED into an acyclic graph (the LLVM frontend, #801) and DO translate; "
                 "a genuine cycle is a ring whose exit depends on the data (e.g. #638's bounded-loop ring), so the number of times round it -- and "
                 "therefore the output's arrival time -- is variable. Fixed-latency wiring cannot align a variable latency, and a second item entering "
                 "while one is circulating would collide; that needs the handshake (flex) or an explicit one-item-at-a-time host contract. Not translated on sub.")
    _, cyclic_pre = nl.hop_depths(cells, [(q, c_, None, None, ()) for c_, roles_ in inputs.items() for lst_ in roles_.values() for q, _ in lst_])
    if cyclic_pre:
        problems.append(CYCLE_MSG)                                  # checked on the WHOLE graph, before any pruning can hide a ring
    marked = {c for c in cells if cells[c].io_name == "result"}
    if marked:
        exit_rule, exits_set = "marked io_name='result' (authoritative)", marked
    elif any(ext_out.get(c) for c in cells):
        exit_rule, exits_set = "face leaving the grid", {c for c in cells if ext_out.get(c)}
    else:
        exit_rule, exits_set = "sink inference (no marker in the file: the cell(s) with nothing downstream)", {c for c in cells if not outputs.get(c)}
    if not exits_set:
        problems.append("no output cell: nothing is marked `result`, no cell has a face leaving the grid, and every cell feeds another -- the file does not say what the design computes")
    live, stack = set(exits_set), list(exits_set)
    while stack:
        c = stack.pop()
        deps = [q for lst in inputs.get(c, {}).values() for q, _ in lst]
        if c in branch_plans and branch_plans[c].get("const_ref"):
            deps.append(branch_plans[c]["const_ref"])                 # a lowered branch reads its constant reference directly, not through an edge
        for q in deps:
            if q in cells and q not in live:
                live.add(q)
                stack.append(q)
    pruned = sorted(set(cells) - live)
    for c in pruned:
        cells.pop(c, None)
        inputs.pop(c, None)
        outputs.pop(c, None)
    for c in list(outputs):
        outputs[c] = [q for q in outputs[c] if q in cells]
    for c in list(inputs):
        inputs[c] = {role: [(q, f) for q, f in lst if q in cells] for role, lst in inputs[c].items()}
    branch_plans = {k: v for k, v in branch_plans.items() if k in cells}
    edges = [(src, dst) for dst, roles in inputs.items() for lst in roles.values() for src, _ in lst]
    depth, cyclic = nl.hop_depths(cells, [(s_, d_, None, None, ()) for s_, d_ in edges])

    srcs_of = {c: [src for lst in inputs.get(c, {}).values() for src, _ in lst] for c in cells}
    addons = {}
    for r in cells.values():
        c = r.cell_id
        spec = CORES.get(r.core)
        if spec is None:
            why = ("no v4s branch cell exists (branch_cell_v4sa is flex-only)" if r.core == "branch"
                   else "arbiter that could not be eliminated (see above)" if r.core == "priority" else "not yet translated")
            problems.append(f"{c}: core {r.core!r} unsupported on sub -- {why}")
            continue
        ad = r.addon_config or {}
        if ad:
            unknown = sorted(k for k in ad if k not in _ADDON_KEYS)
            if unknown:
                problems.append(f"{c}: addon_config has unknown field(s) {unknown}")
            elif r.core == "nano":
                problems.append(f"{c}: addon_config on a nano -- the VM's offer pass skips nano entirely, so its addon behaviour is not defined")
            else:
                bm = addon_bit_map(ad)
                if not addon_is_identity(bm):
                    addons[c] = bm
        if r.core == "nano":
            cfgn = r.core_config or {}
            odd = sorted(k for k, v in cfgn.items() if k not in NANO_BENIGN_KEYS and v)
            if odd:
                problems.append(f"{c}: nano uses {odd} (relay/hold/update/one-shot modes) -- only the plain two-arrival gate is translated")
            if int(cfgn.get("topology", 0)) not in NANO_TOPOLOGIES:
                problems.append(f"{c}: nano topology {int(cfgn.get('topology', 0)):#x} is not implemented by nano_cell_v4s (its default would silently pass the held value)")
        if r.core == "sequencer":
            if srcs_of[c]:
                problems.append(f"{c}: something feeds a sequencer; the VM's sequencer refuses every arrival (ack tied low), so such a wire never delivers")
            extra = sorted(k for k in (r.core_config or {}) if k not in ("VALUE_0", "VALUE_1", "VALUE_2", "VALUE_3", "SEQUENCE_LEN", "downstream_mask"))
            if extra:
                problems.append(f"{c}: sequencer config uses {extra} -- only VALUE_0..3, SEQUENCE_LEN and downstream_mask are translated")
            if r.addon_config:
                problems.append(f"{c}: addon_config on a sequencer is not translated")
        if spec["kind"] == "level":
            odd = sorted(k for k in (r.core_config or {}) if k not in _LEVEL_ALLOWED[r.core])
            if odd:
                problems.append(f"{c}: {r.core} config uses {odd} -- only {sorted(_LEVEL_ALLOWED[r.core])} are translated")
            if r.addon_config:
                problems.append(f"{c}: addon_config on a {r.core} is not translated")
            if not srcs_of[c]:
                problems.append(f"{c}: {r.core} with no pulse input connected -- nothing can ever change it")
        seq_srcs = [q for q in srcs_of[c] if cells[q].core == "sequencer"]
        if seq_srcs and family == "flex" and spec["kind"] != "pair" and len(srcs_of[c]) > 1:
            problems.append(f"{c}: a sequencer feeding a MERGE is not translated on flex (which of its values the merge should take is ambiguous)")
        if seq_srcs and family == "sub" and (spec["kind"] == "pair" or len(srcs_of[c]) > 1):
            problems.append(f"{c}: fed by sequencer {seq_srcs} together with other sources. The VM's sequencer is perpetually live and re-offers at once, "
                            f"and a two-operand cell (or a merge) pairs/ORs by ARRIVAL, so in the VM the sequence values pair with EACH OTHER, not with the "
                            f"stream; the sub translation (one host advance pulse per item) would pair them with the stream -- different semantics. "
                            f"Not translated: feed the sequencer to a single-input consumer, or decide the pairing rule explicitly.")
        is_source = not srcs_of[c]
        if r.preload_value is not None and not (r.core == "ram" and is_source):
            problems.append(f"{c}: preload_value on a cell that is not a source ram")
        if spec["kind"] == "pair" and len(srcs_of[c]) != 2:
            problems.append(f"{c}: {r.core} has {len(srcs_of[c])} source(s), needs exactly 2 "
                            f"(one stream carrying both operands needs a stagger spec -- not translated)")
        if is_source and r.core not in ("ram", "sequencer") and not (r.core == "branch" and c in branch_plans and branch_plans[c]["stream"] is None):
            problems.append(f"{c}: {r.core} with no source is not a ram injection point or constant")
    if family == "flex":
        # STAGES 1-2 of the flex emitter (the handshake family): ram, adder, mul and constants only. Everything else is refused, with the reason, until it is built AND
        # verified -- never silently mistranslated. Timing/alignment refusals below that only make sense for FIXED latency do not apply to a handshake design.
        for r in cells.values():
            if r.core not in FLEX_STAGE1_CORES:
                problems.append(f"{r.cell_id}: core {r.core!r} is not yet translated on flex (stage 1 covers {sorted(FLEX_STAGE1_CORES)})")
    # --- ledger #976: SECOND-OUTPUT cells. The compiler sets ONE flag on the cell (an adder's `carry_mode`, a multiplier's `wide_mode`); the planner records which cells have it so
    # the assembler/emitter builds the second port (SECOND_PORT=1) and routes it. In the VM the second word goes to the SAME downstream as the first, one after the other; on flex that is
    # a merge core (arbitrate, first port first) in front of each consumer, so a consumer must be a single-input relay-type cell (ram / comparator).
    second_ports = sorted(c for c, r in cells.items() if (r.core == "adder" and (r.core_config or {}).get("carry_mode")) or (r.core == "mul" and (r.core_config or {}).get("wide_mode")))
    if second_ports and family != "flex":
        problems.append(f"{second_ports}: a second output word (adder carry_mode / mul wide_mode) exists on the flex family only; the sub family has no second port, so it would be silently dropped")
    elif second_ports:
        for c in second_ports:
            if c in exits_set:
                problems.append(f"{c}: a cell with a second output word as a design OUTPUT is not translated on flex (the host would have to take two words per result)")
            if cells[c].addon_config:
                problems.append(f"{c}: addon_config on a cell with a second output word is not translated (the add-on chain would have to apply to the second word too)")
            for dst in cells:
                if c in srcs_of[dst] and cells[dst].core not in ("ram", "comparator"):
                    problems.append(f"{dst}: fed by {c}, which delivers a second word to the same downstream; only a single-input relay-type consumer (ram / comparator) is translated -- a {cells[dst].core} would have to pair the two words by arrival")
    if problems:
        raise IcmGenError(f"cannot generate {family} Verilog from %s:\n  - " % os.path.basename(icm_path) + "\n  - ".join(problems))

    # constant-valued nodes: preloaded / fixed-mode source rams and anything fed only by them (always available)
    const = {c for c, r in cells.items() if not srcs_of[c] and (r.preload_value is not None or (r.core_config or {}).get("fixed_mode"))}
    level = {c for c, r in cells.items() if is_level(r)}
    const |= level                       # a level source is ALWAYS VALID: for timing it behaves like a constant (its data changes, its availability does not)
    grew = True
    while grew:
        grew = False
        for c in cells:
            if c not in const and srcs_of[c] and all(q in const for q in srcs_of[c]) and not cells[c].io_name:
                const.add(c)
                grew = True

    for c in cells:                      # a level/constant source into a COUNTING or TOGGLING input is rate-dependent -> refuse
        r = cells[c]
        if CORES[r.core]["kind"] != "level":
            continue
        for role, lst in inputs.get(c, {}).items():
            rate_dependent = (r.core == "accumulator" and role in ("inc", "dec")) or (r.core == "latch" and role == "toggle")
            bad = [q for q, _ in lst if q in const]
            if rate_dependent and bad:
                raise IcmGenError(f"{c}: {bad} is an always-valid (constant or level) source feeding the {role} input of a {r.core}. The VM counts/toggles once "
                                  f"per DRAINED OFFER while this design does so once per CYCLE, so the result would depend on the rate -- not translated. "
                                  f"(set/clear from a level source is idempotent and is translated.)")

    order = []
    remaining = set(cells)
    while remaining:
        ready = [c for c in sorted(remaining) if all(q not in remaining for q in srcs_of[c])]
        if not ready:
            raise IcmGenError("internal: dependency order could not be resolved")
        order += ready
        remaining -= set(ready)

    t_vm, t_rtl, roles, merges = {}, {}, {}, {}

    def ident_key(c, q):
        return (t_vm[q], tiekeys.get((c, q), (0, 0)))

    for c in order:
        r, srcs = cells[c], srcs_of[c]
        extra = 0                                           # addons are wiring: no latency
        # the VM's hop-count time -- operand IDENTITY only. A branch that absorbed its reference merge still pays that merge's hop in the VM.
        t_vm[c] = max((t_vm[q] for q in srcs), default=0) + 1 + (1 if "merge_removed" in branch_plans.get(c, {}) else 0)
        if CORES[r.core]["kind"] == "pair":
            if all(q in const for q in srcs):
                raise IcmGenError(f"{c}: both operands are constant or level (always-valid) sources -- nothing live to time the result by")
            tks = [tiekeys.get((c, q)) for q in srcs]
            if all(t is not None for t in tks) and tks[0][0] != tks[1][0]:
                # DIFFERENT ranks (a file written by flexsub_compile_v1, #929): rank DEFINES operand identity, because this
                # assembler equalises arrival itself
                sa, sb = sorted(srcs, key=lambda q: tiekeys[(c, q)])
                identity_by = "rank"
            else:
                sa, sb = sorted(srcs, key=lambda q: ident_key(c, q))
                if t_vm[sa] == t_vm[sb] and tiekeys.get((c, sa)) is None:
                    raise IcmGenError(f"{c}: both operands arrive at hop {t_vm[sa]} with no arbiter to order them -- a same-time pair "
                                      f"is an OR-combined single arrival in the VM; no operand order exists. Not translated.")
                identity_by = "arbiter tie-break" if (tiekeys.get((c, sa)) is not None and t_vm[sa] == t_vm[sb]) else "arrival order"
            live = [q for q in (sa, sb) if q not in const]                  # constants never constrain timing
            pad = {sa: 0, sb: 0}
            hf = CORES[r.core].get("hold_flow")
            valid_from = "B" if sb not in const else "A"
            if hf:
                # the held operand A must arrive exactly ONE cycle before the flowing operand B
                if len(live) == 2:
                    tb = max(t_rtl[sb], t_rtl[sa] + 1)
                    if align:
                        pad = {sa: tb - 1 - t_rtl[sa], sb: tb - t_rtl[sb]}
                    t_in = tb
                elif sa not in const:                                         # A live, B constant: the gate sees A one cycle later
                    t_in = t_rtl[sa] + 1
                    valid_from = "A_delayed"                                  # valid_in must be A's valid delayed by one cycle
                else:                                                         # A constant (held for ever), B live
                    t_in = t_rtl[sb]
            else:
                if len(live) == 2 and align:
                    late = max(t_rtl[sa], t_rtl[sb])
                    pad = {sa: late - t_rtl[sa], sb: late - t_rtl[sb]}
                t_in = max((t_rtl[q] for q in live), default=0)
            roles[c] = {"A": sa, "B": sb, "identity_by": identity_by, "pad_A": pad[sa], "pad_B": pad[sb],
                        "valid_from": valid_from, "const_operands": [q for q in (sa, sb) if q in const]}
        else:
            live = [q for q in srcs if q not in const]
            if len(srcs) > 1 and CORES[r.core]["kind"] != "level":   # a MERGE (gated OR, Alan #924: "a free OR when needed")
                if len(live) != len(srcs):
                    raise IcmGenError(f"{c}: a merge that includes a constant source -- the constant is always valid, so the OR "
                                      f"would swamp the stream; no definite behaviour. Not translated.")
                if family == "sub" and len({t_rtl[q] for q in live}) > 1:
                    raise IcmGenError(f"{c}: merge of sources arriving at different latencies "
                                      f"{sorted((q, t_rtl[q]) for q in live)} -- the cell's output time would depend on WHICH source fired, "
                                      f"which a fixed-latency design cannot align; that needs flow control (flex). Not translated on sub.")
                merges[c] = list(srcs)
            t_in = max((t_rtl[q] for q in live), default=0)
        t_rtl[c] = None if c in const else t_in + 1 + extra
    mul_impl, mul_info = choose_multipliers([c for c in cells if cells[c].core == "mul"], man, mul_mode, nowidelut)
    branch_port = {}                      # (consumer, branch) -> which of the branch's two output ports feeds that consumer
    for dst, role_map in inputs.items():                  # (not `roles`: that name holds the operand-role dict computed above)
        for lst in role_map.values():
            for q, face_at_dst in lst:
                if q in branch_plans:
                    branch_port[(dst, q)] = branch_plans[q]["ports"][_FACE_OPP[face_at_dst]]
    return {"doc": doc, "recs": recs, "cells": cells, "edges": edges, "inputs": inputs, "outputs": outputs,
            "t_out": t_rtl, "t_vm": t_vm, "order": order, "adder_roles": roles, "align": align, "warnings": warnings,
            "eliminated_priority": eliminated, "const": const, "addons": addons, "merges": merges,
            "branch_plans": branch_plans, "branch_port": branch_port, "second_ports": second_ports, "exits": [c for c in order if c in exits_set and c in cells], "pruned": pruned, "exit_rule": exit_rule, "min_bit_width": declared_width,
            "mul_impl": mul_impl, "mul_info": mul_info}


def emit_top(top, p, width=32):
    cells, inputs, outputs, roles = p["cells"], p["inputs"], p["outputs"], p["adder_roles"]
    const, addons = p["const"], p["addons"]
    L = []
    a = L.append
    a(f"// {top}.v -- GENERATED by tools/flexsub_icm_generate_v1.py (-s sub --icm); do not hand-edit.")
    a(f"// Source ICM: {p['doc'].name or '(unnamed)'}; {len(cells)} cells; align={'on' if p['align'] else 'OFF (negative control)'}.")
    a("// Straight wiring, fixed 1-cycle cells, no ack (Alan #924). Early operands are padded with relay cells;")
    a("// constants are fixed-mode rams (always valid) and never constrain timing; addons (mask/shift/invert) are pure wiring.")
    a("`default_nettype none")
    a("`timescale 1ns / 1ps")
    entries = [c for c in p["order"] if not inputs.get(c) and c not in const]
    exits = list(p["exits"])

    def pname(io, cid):
        return re.sub(r"[^A-Za-z0-9_]", "_", io or cid)
    a(f"module {top} (")
    a("    input  wire clk,")
    a("    input  wire rst,")
    a("    input  wire cfg_valid,")
    ports = []
    for c in entries:
        n = pname(cells[c].io_name, c)
        if cells[c].core == "sequencer":                          # a tick, not a datum: the pulse that advances the sequence
            ports.append(f"    input  wire        adv_{n}")
        else:
            ports += [f"    input  wire [31:0] in_{n}_data", f"    input  wire        in_{n}_valid"]
    for c in exits:
        n = pname(cells[c].io_name, c)
        ports += [f"    output wire [31:0] out_{n}_data", f"    output wire        out_{n}_valid"]
    a(",\n".join(ports))
    a(");")
    for c in p["order"]:
        i = _ident(c)
        a(f"wire [31:0] {i}_d; wire {i}_v;")
        if cells[c].core == "branch":                            # a branch has TWO output ports; consumers pick theirs via net()
            a(f"wire [31:0] {i}_d1, {i}_d2; wire {i}_v1, {i}_v2;")
    a("")
    idx = {c: k for k, c in enumerate(p["order"])}
    pad_count = [0]

    def cfg_args(data="32'h0", fixed=None):
        """Port-connection prefix every cell shares: clock, reset, config strobe and word (+ ram's fixed-mode port)."""
        t = ".clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(" + data + ")"
        return t + (", .cfg_fixed_mode(1'b" + str(int(fixed)) + ")" if fixed is not None else "")

    def hexw(v):
        return "32'h" + format(int(v) & 0xFFFFFFFF, "X")

    branch_plans, branch_port = p["branch_plans"], p["branch_port"]

    def net(dst, src):
        """(data, valid) net of `src` as seen by consumer `dst`: a branch exposes one of its two ports per routed face."""
        i_ = _ident(src)
        if src in branch_plans:
            k = branch_port[(dst, src)]
            return f"{i_}_d{k}", f"{i_}_v{k}"
        return f"{i_}_d", f"{i_}_v"

    def feed(cid, srcs):
        """Data/valid nets feeding a single-input cell. One source: wired straight. Several (a merge): each source is GATED by its
        own valid before the OR -- these cells keep driving stale data_out after their valid pulse, so a raw OR would leak an
        idle source's old value. Same-cycle arrivals OR together (the VM's rule); valid is the OR of the valids."""
        if len(srcs) == 1:
            return net(cid, srcs[0])
        i = _ident(cid)
        nets = [net(cid, q) for q in srcs]
        terms = " | ".join(f"({v} ? {d} : 32'h0)" for d, v in nets)
        a(f"wire [31:0] {i}_mrg_d = {terms};   // gated-OR merge of {len(srcs)} sources")
        a(f"wire {i}_mrg_v = " + " | ".join(v for _, v in nets) + ";")
        return f"{i}_mrg_d", f"{i}_mrg_v"

    def padded(cid, d, v, n, tag):
        for k in range(n):                                      # delay with flowing ram relay cells
            pad_count[0] += 1
            pi = f"{_ident(cid)}_pad{tag}{k}"
            a(f"wire [31:0] {pi}_d; wire {pi}_v;")
            ca = cfg_args("32'h0", 0)
            a(f"ram_cell_v4s #(.CELL_ID(16'd{1000 + pad_count[0]})) {pi} ({ca}, "
              f".data_in({d}), .valid_in({v}), .data_out({pi}_d), .valid_out({pi}_v));")
            d, v = f"{pi}_d", f"{pi}_v"
        return d, v

    for c in p["order"]:
        r, i = cells[c], _ident(c)
        cfg = r.core_config or {}
        out_d, out_v = f"{i}_d", f"{i}_v"
        if c in addons and CORES[r.core]["kind"] != "branch":   # the cell drives a private raw net; the addon wiring drives {i}_d (valid is untouched)
            out_d = f"{i}_raw_d"
            a(f"wire [31:0] {out_d};")
        srcs = [src for lst in inputs.get(c, {}).values() for src, _ in lst]
        kind = CORES[r.core]["kind"]
        mod = MUL_MODULES[p["mul_impl"][c]] if r.core == "mul" else CORES[r.core]["module"]
        if kind == "pair":
            role = roles[c]
            ad, av = net(c, role["A"])
            bd, bv = net(c, role["B"])
            ad, av = padded(c, ad, av, role["pad_A"], "A")
            bd, bv = padded(c, bd, bv, role["pad_B"], "B")
            if CORES[r.core].get("hold_flow"):
                if role["valid_from"] == "A_delayed":                         # B is a constant: valid_in = A's valid, one cycle later
                    _, vin = padded(c, ad, av, 1, "V")
                else:
                    vin = bv
                ca = cfg_args(hexw(cfg.get("topology", 0)))
                a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({ca}, .hold_in_data({ad}), .load_hold({av}), "
                  f".flow_in_data({bd}), .valid_in({vin}), .data_out({out_d}), .valid_out({out_v}));")
            else:
                vin = bv if role["valid_from"] == "B" else av
                word = hexw(int(bool(cfg.get("subtract_mode", 0)))) if r.core == "adder" else "32'h0"
                ca = cfg_args(word)
                a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({ca}, "
                  f".in_a({ad}), .in_b({bd}), .valid_in({vin}), .data_out({out_d}), .valid_out({out_v}));")
        elif r.core == "branch":
            bp = branch_plans[c]
            if bp["stream"] is None:                              # the branch is the entry point (it absorbed the merge that carried the io_name)
                n_ = pname(r.io_name, c)
                d1, v1 = f"in_{n_}_data", f"in_{n_}_valid"
            else:
                d1, v1 = net(c, bp["stream"])
            if bp["mode"] == "const_ref":                        # in2 = the constant reference (flowing, valid = the constant's own valid)
                d2, v2 = f"{_ident(bp['const_ref'])}_d", f"{_ident(bp['const_ref'])}_v"
                in2_fixed = 0
            else:                                                 # rolling: in2 is a HELD copy of the same stream, loaded by the same valid
                d2, v2 = d1, v1
                in2_fixed = 1
            rb = bp["route_bits"]
            word = (in2_fixed << 1) | (bp["emit_source"] << 2) | (rb["low"] << 4) | (rb["equal"] << 6) | (rb["high"] << 8)
            ca = cfg_args(hexw(word))
            if c in addons:
                a(f"wire [31:0] {i}_rd1, {i}_rd2;")
            a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({ca}, .cfg_emit_fixed_value({hexw(bp['emit_fixed'])}), "
              f".in1_data({d1}), .in1_valid({v1}), .in2_data({d2}), .in2_valid({v2}), "
              f".data_out_1({i}_{'rd1' if c in addons else 'd1'}), .valid_out_1({i}_v1), "
              f".data_out_2({i}_{'rd2' if c in addons else 'd2'}), .valid_out_2({i}_v2));")
            if c in addons:
                a(f"assign {i}_d1 = {addon_expr(addons[c], i + '_rd1')};   // addon wiring on both output ports")
                a(f"assign {i}_d2 = {addon_expr(addons[c], i + '_rd2')};")
        elif CORES[r.core]["kind"] == "level":
            roles_ = inputs.get(c, {})

            def any_valid(role, gate_bit0=False):
                terms = []
                for q, _ in roles_.get(role, []):
                    d_, v_ = net(c, q)
                    terms.append(f"({v_} & {d_}[0])" if gate_bit0 else v_)
                return " | ".join(terms) if terms else "1'b0"
            lvl = is_level(r)
            pv = f"{i}_pulse" if lvl else out_v                      # a level cell's own valid pulse is unused; a pulse-mode accumulator's IS the output valid
            if lvl:
                a(f"wire {pv};")
            if r.core == "accumulator":
                word = (int(cfg.get("step_amount", 0)) & 0xFF) | ((1 if cfg.get("pulse_mode", 0) else 0) << 8) | ((int(cfg.get("threshold", 0)) & 0xFFFF) << 9)
                a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({cfg_args(hexw(word))}, .inc_pulse({any_valid('inc')}), .dec_pulse({any_valid('dec')}), "
                  f".data_out({out_d}), .valid_out({pv}));")
            else:
                a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({cfg_args()}, .set_in({any_valid('set', True)}), .clear_in({any_valid('clear')}), "
                  f".toggle_in({any_valid('toggle')}), .data_out({out_d}), .valid_out({pv}));")
            if lvl:
                a(f"assign {out_v} = 1'b1;   // LEVEL source (Alan #938): the VM offers this always valid; the cell's own valid pulse ({pv}) is unused")
        elif r.core == "sequencer":
            n_ = pname(r.io_name, c)
            vals = [int(cfg.get(f"VALUE_{k}", 0)) & 0xFF for k in range(4)]
            len_m1 = int(cfg.get("SEQUENCE_LEN", 0)) & 3
            n_vals = len_m1 + 1
            rot = [vals[(j - 1) % n_vals] if j < n_vals else 0 for j in range(4)]       # rot[j] = V[(j-1) mod n]
            word = rot[0] | (rot[1] << 8) | (rot[2] << 16) | (rot[3] << 24)
            ca = cfg_args(hexw(word))
            a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({ca}, .cfg_seq_len_m1(2'd{len_m1}), .advance_in(adv_{n_}), "
              f".data_out({out_d}), .valid_out({out_v}));   // values rotated one step: the pulsed sequence starts at VALUE_0")
        elif r.core == "comparator":
            dd, vv = feed(c, srcs)
            ca = cfg_args(hexw(cfg.get("threshold", 0)))
            a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({ca}, "
              f".data_in({dd}), .valid_in({vv}), .data_out({out_d}), .valid_out({out_v}));")
        else:   # ram
            if c in const and not srcs:                          # a constant SOURCE: a fixed-mode ram, always valid (its relays just flow)
                val = r.preload_value if r.preload_value is not None else cfg.get("init_data", 0)
                ca = cfg_args(hexw(val), 1)
                a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({ca}, "
                  f".data_in(32'h0), .valid_in(1'b0), .data_out({out_d}), .valid_out({out_v}));")
            else:
                if srcs:
                    dd, vv = feed(c, srcs)
                else:
                    n = pname(r.io_name, c)
                    dd, vv = f"in_{n}_data", f"in_{n}_valid"
                ca = cfg_args("32'h0", bool(cfg.get("fixed_mode", 0)))
                a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({ca}, "
                  f".data_in({dd}), .valid_in({vv}), .data_out({out_d}), .valid_out({out_v}));")
        if c in addons and CORES[r.core]["kind"] != "branch":
            a(f"assign {i}_d = {addon_expr(addons[c], out_d)};   // addon chain (mask/shift/lane-cut/invert) as pure wiring, no latency")
    for c in exits:
        n, i = pname(cells[c].io_name, c), _ident(c)
        a(f"assign out_{n}_data = {i}_d;")
        a(f"assign out_{n}_valid = {i}_v;")
    a("endmodule")
    return "\n".join(L) + "\n", pad_count[0]


def generate(icm_path, output, top=None, align=True, cell_dir=None, man_path=None, mul_mode="auto", family="sub", nowidelut=None, merge_mode="arbitrate"):
    if family == "flex":
        import flexsub_icm_flex_v1 as ff
        return ff.generate_flex(icm_path, output, top=top, cell_dir=cell_dir, man_path=man_path, nowidelut=nowidelut, merge_mode=merge_mode)
    man = fsa.load_man_flexsub(man_path) if man_path else None
    nowidelut, nowidelut_why = fsa.resolve_nowidelut(nowidelut, man)
    p = plan(icm_path, align, man=man, mul_mode=mul_mode, nowidelut=nowidelut)
    stem = re.sub(r"[^A-Za-z0-9_]", "_", os.path.basename(icm_path).split(".")[0])
    top = top or f"icm_{stem}_sub"
    cell_dir = cell_dir or fsa.DEFAULT_CELL_DIR
    os.makedirs(output, exist_ok=True)
    text, pad_count = emit_top(top, p)
    top_path = os.path.join(output, f"{top}.v")
    open(top_path, "w").write(text)
    dep_pairs = fsa._derive_deps(top_path, cell_dir)
    for fname, src in dep_pairs:
        shutil.copy2(os.path.join(src, fname), os.path.join(output, fname))
    files = [f"{top}.v"] + [f for f, _ in dep_pairs]
    open(os.path.join(output, f"{top}.ys"), "w").write(
        f"read_verilog -sv {' '.join(files)}\nhierarchy -top {top}\nsynth_gowin -top {top}{' -nowidelut' if nowidelut else ''} -json {top}.json\nstat\n")
    rec = {"generator": "tools/flexsub_icm_generate_v1.py", "family": "sub", "source": os.path.basename(icm_path),
           "top": top, "cells": len(p["cells"]), "pad_relay_cells": pad_count, "align": p["align"],
           "output_latency_cycles": {c: p["t_out"][c] for c in p["exits"]}, "pruned_dead_cells": p["pruned"], "exit_rule": p["exit_rule"],
           "constants": sorted(p["const"]), "settle_cycles": (max((p["t_vm"][c] for c in p["const"]), default=0) + 1) if p["const"] else 0, "addon_wiring": {c: {k: v for k, v in (p["cells"][c].addon_config or {}).items() if v} for c in p["addons"]},
           "adder_roles": p["adder_roles"], "merges": p["merges"], "branches": p["branch_plans"], "multipliers": p["mul_info"], "min_bit_width": p["min_bit_width"], "built_width": BUILT_WIDTH, "synth_flags": "-nowidelut" if nowidelut else "(wide-LUT mapping)", "synth_flags_reason": nowidelut_why,
           **({"sim_note": "this design instantiates the Gowin MULT36X36 primitive (mul_cell_v4s_dsp2); simulation needs a behavioural stand-in "
                           "(yosys ships none) -- see sub/verilog/tb_mul_cell_v4s_dsp2.v. Synthesis uses the primitive directly."} if p["mul_info"]["dsp2"] else {}), "level_sources": sorted(c for c in p["cells"] if is_level(p["cells"][c])),
           "sequencers": {c: {"advance_port": "adv_" + re.sub(r"[^A-Za-z0-9_]", "_", p["cells"][c].io_name or c),
                              "length": int((p["cells"][c].core_config or {}).get("SEQUENCE_LEN", 0) & 3) + 1}
                          for c in p["cells"] if p["cells"][c].core == "sequencer"}, "eliminated_priority_cells": p["eliminated_priority"], "files": files + [f"{top}.ys"]}
    json.dump(rec, open(os.path.join(output, "ASSEMBLY.json"), "w"), indent=2)
    return rec
