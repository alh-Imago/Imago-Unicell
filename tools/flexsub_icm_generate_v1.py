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


def decode_addon(r):
    """(total_shift, direction, None) for an addon_config that is only a shift, (0, 0, None) for none, or
    (None, None, reason) when it needs something this translation does not have. Rules from the VM's own
    addon function: fine shift first, then the coarse shift only if its amount is one of the supported taps (an
    unsupported amount is a deliberate no-op); direction 0 = left, 1 = right (logical)."""
    ad = r.addon_config or {}
    if not ad:
        return 0, 0, None
    extra = {k: v for k, v in ad.items() if k not in ("shift_en", "direction", "shift_fine", "shift_amt") and v}
    if extra:
        return None, None, f"addon_config uses {sorted(extra)} -- only a plain shift is translated (mask/invert/lane_cut need their own cells)"
    if not ad.get("shift_en"):
        return 0, 0, None
    fine = ad.get("shift_fine", 0) & 3
    amt = ad.get("shift_amt", 0)
    coarse = amt if amt in _SHIFT_COARSE else 0
    return fine + coarse, 1 if ad.get("direction", 0) else 0, None


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


def plan(icm_path, align=True):
    """Everything the emitter needs, with every refusal raised here. Returns a plain dict."""
    doc, recs, cells, edges, inputs, outputs, ext_out, warnings = nl.extract(icm_path)
    problems = []
    # priority arbiters that only serialised two operands onto one input are eliminated (dedicated ports replace them)
    cells, inputs, outputs, tiekeys, eliminated, pri_problems = nl.eliminate_priority(cells, inputs, outputs)
    problems += pri_problems
    cells, inputs, outputs, branch_plans, br_problems = lower_branches(cells, inputs, outputs)
    problems += br_problems
    edges = [(src, dst) for dst, roles in inputs.items() for lst in roles.values() for src, _ in lst]
    depth, cyclic = nl.hop_depths(cells, [(s_, d_, None, None, ()) for s_, d_ in edges])
    if cyclic:
        problems.append("the design has a cycle (feedback) -- the fixed-latency translation has no rule for it yet")
    srcs_of = {c: [src for lst in inputs.get(c, {}).values() for src, _ in lst] for c in cells}
    shifts = {}
    for r in cells.values():
        c = r.cell_id
        spec = CORES.get(r.core)
        if spec is None:
            why = ("no v4s branch cell exists (branch_cell_v4sa is flex-only)" if r.core == "branch"
                   else "arbiter that could not be eliminated (see above)" if r.core == "priority" else "not yet translated")
            problems.append(f"{c}: core {r.core!r} unsupported on sub -- {why}")
            continue
        total, direction, why = decode_addon(r)
        if why:
            problems.append(f"{c}: {why}")
        elif total:
            if r.core != "ram":
                problems.append(f"{c}: addon shift on a {r.core} cell -- only a ram relay's output shift is translated")
            else:
                shifts[c] = (total, direction)
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
        if seq_srcs and (spec["kind"] == "pair" or len(srcs_of[c]) > 1):
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
    if problems:
        raise IcmGenError("cannot generate sub Verilog from %s:\n  - " % os.path.basename(icm_path) + "\n  - ".join(problems))

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
        extra = 1 if c in shifts else 0
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
                if len({t_rtl[q] for q in live}) > 1:
                    raise IcmGenError(f"{c}: merge of sources arriving at different latencies "
                                      f"{sorted((q, t_rtl[q]) for q in live)} -- the cell's output time would depend on WHICH source fired, "
                                      f"which a fixed-latency design cannot align; that needs flow control (flex). Not translated on sub.")
                merges[c] = list(srcs)
            t_in = max((t_rtl[q] for q in live), default=0)
        t_rtl[c] = None if c in const else t_in + 1 + extra
    branch_port = {}                      # (consumer, branch) -> which of the branch's two output ports feeds that consumer
    for dst, role_map in inputs.items():                  # (not `roles`: that name holds the operand-role dict computed above)
        for lst in role_map.values():
            for q, face_at_dst in lst:
                if q in branch_plans:
                    branch_port[(dst, q)] = branch_plans[q]["ports"][_FACE_OPP[face_at_dst]]
    return {"doc": doc, "recs": recs, "cells": cells, "edges": edges, "inputs": inputs, "outputs": outputs,
            "t_out": t_rtl, "t_vm": t_vm, "order": order, "adder_roles": roles, "align": align, "warnings": warnings,
            "eliminated_priority": eliminated, "const": const, "shifts": shifts, "merges": merges,
            "branch_plans": branch_plans, "branch_port": branch_port}


def emit_top(top, p, width=32):
    cells, inputs, outputs, roles = p["cells"], p["inputs"], p["outputs"], p["adder_roles"]
    const, shifts = p["const"], p["shifts"]
    L = []
    a = L.append
    a(f"// {top}.v -- GENERATED by tools/flexsub_icm_generate_v1.py (-s sub --icm); do not hand-edit.")
    a(f"// Source ICM: {p['doc'].name or '(unnamed)'}; {len(cells)} cells; align={'on' if p['align'] else 'OFF (negative control)'}.")
    a("// Straight wiring, fixed 1-cycle cells, no ack (Alan #924). Early operands are padded with relay cells;")
    a("// constants are fixed-mode rams (always valid) and never constrain timing; shifts are separate shift_stage cells.")
    a("`default_nettype none")
    a("`timescale 1ns / 1ps")
    entries = [c for c in p["order"] if not inputs.get(c) and c not in const]
    exits = [c for c in p["order"] if not outputs.get(c)]

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
        if c in shifts:                                         # the cell drives a private net; a shift_stage drives {i}_d/_v
            out_d, out_v = f"{i}_raw_d", f"{i}_raw_v"
            a(f"wire [31:0] {out_d}; wire {out_v};")
        srcs = [src for lst in inputs.get(c, {}).values() for src, _ in lst]
        kind = CORES[r.core]["kind"]
        mod = CORES[r.core]["module"]
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
            a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({ca}, .cfg_emit_fixed_value({hexw(bp['emit_fixed'])}), "
              f".in1_data({d1}), .in1_valid({v1}), .in2_data({d2}), .in2_valid({v2}), "
              f".data_out_1({i}_d1), .valid_out_1({i}_v1), .data_out_2({i}_d2), .valid_out_2({i}_v2));")
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
        if c in shifts:
            amt, direction = shifts[c]
            ca = cfg_args("32'h0")
            a(f"shift_stage_v4s #(.CELL_ID(16'd{2000 + idx[c]}), .SHIFT_AMT(5'd{amt}), .DIRECTION(1'b{direction})) {i}_shift "
              f"({ca}, .data_in({out_d}), .valid_in({out_v}), .data_out({i}_d), .valid_out({i}_v));")
    for c in exits:
        n, i = pname(cells[c].io_name, c), _ident(c)
        a(f"assign out_{n}_data = {i}_d;")
        a(f"assign out_{n}_valid = {i}_v;")
    a("endmodule")
    return "\n".join(L) + "\n", pad_count[0]


def generate(icm_path, output, top=None, align=True, cell_dir=None):
    p = plan(icm_path, align)
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
        f"read_verilog -sv {' '.join(files)}\nhierarchy -top {top}\nsynth_gowin -top {top} -json {top}.json\nstat\n")
    rec = {"generator": "tools/flexsub_icm_generate_v1.py", "family": "sub", "source": os.path.basename(icm_path),
           "top": top, "cells": len(p["cells"]), "pad_relay_cells": pad_count, "align": p["align"],
           "output_latency_cycles": {c: p["t_out"][c] for c in p["order"] if not p["outputs"].get(c)},
           "constants": sorted(p["const"]), "settle_cycles": (max((p["t_vm"][c] for c in p["const"]), default=0) + 1) if p["const"] else 0, "shift_stages": {c: list(v) for c, v in p["shifts"].items()},
           "adder_roles": p["adder_roles"], "merges": p["merges"], "branches": p["branch_plans"], "level_sources": sorted(c for c in p["cells"] if is_level(p["cells"][c])),
           "sequencers": {c: {"advance_port": "adv_" + re.sub(r"[^A-Za-z0-9_]", "_", p["cells"][c].io_name or c),
                              "length": int((p["cells"][c].core_config or {}).get("SEQUENCE_LEN", 0) & 3) + 1}
                          for c in p["cells"] if p["cells"][c].core == "sequencer"}, "eliminated_priority_cells": p["eliminated_priority"], "files": files + [f"{top}.ys"]}
    json.dump(rec, open(os.path.join(output, "ASSEMBLY.json"), "w"), indent=2)
    return rec
