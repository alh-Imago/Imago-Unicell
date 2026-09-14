"""llvm_ir_frontend_v1.py — points.md #611: the real, first LLVM IR
frontend for Unicell-S, per `#547`/`#603`/`#610`'s own real scope. Uses
`llvmlite` (confirmed installable and working in this environment,
per `#610`'s own real tooling check) to parse REAL LLVM IR text -- not
a made-up LLVM-like pseudo-language, matching `c_frontend_v1.py`'s own
"real syntax, real parser" precedent.

REAL, DELIBERATELY RESTRICTED FIRST SLICE, matching `#610`'s own
"smallest test first" recommendation exactly -- not general LLVM IR:
- Exactly one function. Either ONE basic block (the original straight-
  line shape, unchanged), OR a real, narrowly-restricted 3-block
  COUNTING LOOP shape (`#652`'s own real prerequisite work, `#661`'s
  own real descending-loop extension: `entry` unconditionally branches
  to `loop`; `loop` holds exactly one `phi` (two incoming edges: a
  literal constant from `entry`, a self-reference from `loop`'s own
  final instruction), one increment (`add` paired with `icmp slt` for
  counting UP, or `sub` paired with `icmp sgt` for counting DOWN,
  `#661`), one `icmp` testing the phi's OWN pre-increment value
  (matching `#638`/`#649`/`#652`'s own real, proven hardware exactly --
  LOOP_CTRL tests what LOOPVAR currently holds BEFORE deciding whether
  the increment even runs that round, not a post-increment test), and
  one conditional `br` back to `loop` or out to `exit`; `exit` holds
  exactly one `ret` of the phi's own pre-increment value (the value
  LOOP_CTRL routes out directly on exit -- that round's own increment,
  though it still computes unconditionally in the same block like any
  ordinary LLVM basic block, is simply never offered to the adder/
  subtractor when the exit path is taken)) -- lowered to `#638`/`#649`/
  `#652`/`#661`'s own real, proven 4-cell bounded-loop-ring tiles
  (`nano_loop_var`/`nano_loop_ctrl`-or-`nano_loop_ctrl_desc`/`adder`-
  or-`subtractor`/`ram_flowing`). `#661`'s own real, hardware-forced
  finding: LOOP_CTRL's comparator always tests "bound (arrives second)
  vs loop-var (arrives first)", so a descending loop needs its own
  real tile (`nano_loop_ctrl_desc`, `continue_out`->`pattern_low`) --
  the polarity can't just be flipped on the existing one, since which
  arrival is "first" vs "second" is fixed by the real topology, not a
  parameter. General multi-block control flow, nested loops, and loops
  with more than one live variable remain real, explicitly deferred
  future work -- this is TWO narrow, real, symmetric shapes, not a
  general control-flow compiler.
- Only `add`/`sub` (32-bit integer) and a terminating `ret`.
- A REAL LINEAR ACCUMULATION CHAIN shape, not general DAG routing:
  each instruction's FIRST operand must be either a real, compile-time
  value (an argument or an LLVM constant) -- only possible for the
  first instruction in the chain -- or the IMMEDIATELY PRECEDING
  instruction's own result. The SECOND operand must always be a
  compile-time value (argument or constant), never a reference to an
  earlier instruction. A program shaped like a genuine DAG (e.g.
  `t3 = add t1, t2` where both are separate prior results) is real,
  explicitly deferred -- it needs real relay-cell routing for
  non-adjacent connections, the actual hard, unsolved part `#610`
  named, not attempted here. Violations produce a real, clear
  diagnostic, never a silently wrong lowering.
- Function ARGUMENTS resolve to REAL, COMPILE-TIME-SUPPLIED integer
  values (a real, honest "specialize this function for these inputs"
  semantic) -- not a general runtime-input mechanism, which stays open
  per `#610`.

REAL LAYOUT, the concrete answer to `#610`'s own "SSA value -> cell"
question for THIS restricted shape (general placement/routing remains
open): row 1 holds one `adder` cell per instruction, west-to-east in
program order -- each consumes the running chain value from its WEST
neighbor and a fresh operand from its NORTH neighbor, broadcasting its
own result EAST. Row 0 holds one `ram_constant` feeder per instruction,
supplying that instruction's own second operand. The very first
instruction's own WEST operand comes from a dedicated feeder at
`(1, 0)`, since it has no real preceding instruction.

REUSES THE REAL, EXISTING SHARED BACKEND (`#344`) -- builds a real
`program_ir_v1.ProgramIR` (the same shape the DSL/Python-AST/C
frontends already produce) and hands it to `dsl_compiler_v1.
compile_program_ir()` unchanged. This frontend's own real job is
narrow: parse LLVM IR, enforce the chain-shape restriction, and decide
positions -- exactly the same real division of labor every other
frontend already has.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import llvmlite.binding as llvm  # noqa: E402

from dsl_diagnostics_v1 import CompileDiagnostic  # noqa: E402
from program_ir_v1 import ProgramIR, PlaceIR, FieldIR  # noqa: E402
from dsl_compiler_v1 import compile_program_ir  # noqa: E402

_SUPPORTED_OPCODES = {"add", "sub", "icmp", "select", "shl", "lshr", "ashr", "and", "or", "xor"}

# points.md #690: real, deterministic decomposition of any shift amount
# 0-31 into (coarse, fine) -- coarse is one of shift_lane_addon_v2.v's
# own 9 real sparse taps (or 0, a real no-op), fine is 0-3
# (shift_fine_addon_v1.v, #683). Picks the LARGEST real coarse tap
# `<= amount`; the remainder is always 0-3 by construction, since no
# gap between consecutive real coarse taps exceeds 4.
_COARSE_TAPS = (0, 1, 2, 4, 8, 12, 16, 20, 24, 28)


def _decompose_shift(amount: int) -> Tuple[int, int]:
    coarse = max(t for t in _COARSE_TAPS if t <= amount)
    fine = amount - coarse
    assert 0 <= fine <= 3, f"internal error: fine={fine} out of range for amount={amount}"
    return coarse, fine


def _compute_needs_relay_tap(body_instructions) -> Dict[str, List[str]]:
    """points.md #701/#713: the real pre-pass general DAG routing
    needs -- scanned BEFORE the main per-instruction loop so a
    producer's own downstream fan-out can be emitted CORRECTLY the
    first time (an extra south tap into the relay lane, #700's own
    real mechanism), rather than needing to retroactively modify an
    already-emitted `PlaceIR`. Purely structural (comparing SSA NAMES
    against the immediately-preceding instruction's own name) -- no
    value resolution needed at all, so this can run before
    `known_values` exists.

    Returns, per producer name, the real, ORDERED list of every later
    consumer that references it non-adjacently -- #713's own real
    extension for shared-producer taps (#706's own proven daisy-chain
    mechanism): a producer may now be tapped by MORE than one
    consumer, each one's own drop relaying onward to the next in the
    exact order they appear in the program, so the main loop can
    correctly decide, for each one, whether it's the LAST in its own
    producer's own chain (routing_mask=["n"] only) or not (["n","e"],
    continuing the daisy chain) -- without ever needing to go back and
    modify an already-emitted drop.

    Real, deliberate scope for this first integration pass, stated
    directly: only `add`/`sub` may be tapped OR be a DAG-referencing
    consumer -- both lower onto the real, commutative "adder" tile
    (`sub` as `add(first, -second)`, `#611`'s own already-verified
    trick), so which of the two real operands (the relayed DAG value,
    the compile-time constant) arrives first at the diff cell
    genuinely doesn't affect correctness. `icmp`'s own subtractor-based
    predicates (`slt`/`sle`/`sgt`/`sge`) ARE real, order-sensitive
    (north-minus-west), and `select`/`shl`/`lshr` have their own real,
    separate result-row conventions -- none of the four are supported
    as a DAG reference SOURCE or CONSUMER in this pass; each gets a
    real, specific diagnostic instead of silently doing the wrong
    thing."""
    producer_opcode: Dict[str, str] = {}
    needs_tap: Dict[str, List[str]] = {}
    for idx, instr in enumerate(body_instructions):
        producer_opcode[instr.name] = instr.opcode
        prev_name = body_instructions[idx - 1].name if idx > 0 else None
        if idx > 0 and instr.opcode == "select":
            # points.md #717: select's own `cond` (its first of three
            # real operands) may reference a non-adjacent, EARLIER
            # icmp -- a real, different eligibility rule from every
            # other consumer here (the producer must be "icmp"
            # specifically, not add/sub), since that's the only real
            # source select's own cond ever accepts.
            sel_operands = list(instr.operands)
            if len(sel_operands) == 3:
                cond_name = _operand_name(sel_operands[0])
                if cond_name and cond_name != prev_name and cond_name in producer_opcode:
                    if producer_opcode[cond_name] == "icmp":
                        needs_tap.setdefault(cond_name, []).append(instr.name)
            continue
        if idx == 0 or instr.opcode not in ("add", "sub", "icmp", "shl", "lshr"):
            continue
        operands = list(instr.operands)
        if len(operands) != 2:
            continue
        first_name = _operand_name(operands[0])
        if first_name and first_name != prev_name and first_name in producer_opcode:
            if producer_opcode[first_name] in ("add", "sub"):
                needs_tap.setdefault(first_name, []).append(instr.name)
    return needs_tap


# points.md #613: real, verified derivation -- reuses the exact same
# real, proven primitives #611 already verified (the adder's own
# negate-and-add sub trick, plus the real "subtractor" tile #608
# registered but never used until now), composed with the real
# "comparator" tile (a stateless `result = 1 if input >= threshold
# else 0` against a FIXED, compile-time threshold -- confirmed
# directly against its own real tile registration, single "in" port,
# no two-operand capture at all). Since comparator can only compare
# ONE dynamic value against a FIXED threshold, every icmp predicate is
# lowered as: (1) a real two-operand diff cell computing some
# `X - Y`, (2) the comparator evaluating that diff against 0 or 1.
#
# Real, necessary derivation, not guessed: comparator's own real
# `>= threshold` only ever needs ONE of two real tile choices to reach
# every one of these four predicates, with NO negation needed on the
# physical "west" (chain-carried) wire -- which matters because a
# chain value arriving via physical adjacency (i > 0) can't be
# retroactively negated at its own source once it's already the
# previous instruction's own real output:
#   sge(A,B): diff = A + (-B)  -- plain ADD, B injected pre-negated
#             (matches #611's own already-verified sub trick exactly)
#   sgt(A,B): same diff, comparator threshold=1 instead of 0
#   slt(A,B): diff = B - A     -- the real SUBTRACTOR tile's own
#             hardware ordering (this layout's north operand always
#             arrives BEFORE west, #611's own confirmed fact) gives
#             north(B) - west(A) directly, with NEITHER operand
#             needing negation at all
#   sle(A,B): same diff, comparator threshold=0 instead of 1
# (tile_name, negate_north_before_injecting, comparator_threshold)
# points.md #611: real diff/threshold shape for the 4 REAL order
# comparisons this frontend has understood since #613. eq/ne need a
# genuinely different shape (#668) -- see _EQ_NE_PREDICATES below and the
# real, dedicated placement logic in the main lowering loop.
_ICMP_LOWERING = {
    "sge": ("adder", True, 0),
    "sgt": ("adder", True, 1),
    "slt": ("subtractor", False, 1),
    "sle": ("subtractor", False, 0),
}

# points.md #668: real, hard-won VM finding, verified in isolation
# before touching this frontend at all -- eq(A,B) is genuinely
# TOPO_XOR(diff>=0, diff>=1): true only when diff is EXACTLY 0 (for
# diff<0 both comparators read 0, XOR=0; for diff==0 the first reads 1
# and the second 0, XOR=1; for diff>=1 both read 1, XOR=0). ne is the
# same real gate with TOPO_XNOR instead -- no extra cells needed, only
# a different fixed topology constant on the same real 2-input gate.
# The one real, non-obvious finding this needed: nano's own two-arrival
# gate OR-COMBINES two same-tick arrivals from different sources into
# ONE event -- it does NOT treat them as two separate sequential
# operands the way #611's own diff-injection stagger already handles
# for west/north. Feeding it two INDEPENDENTLY COMPUTED values (here,
# two comparator outputs) needs the exact same real fix: deliberately
# unequal hop counts so the two arrivals land on genuinely different
# ticks. Verified directly against six real (a, b) pairs in the VM
# before writing any of this lowering code.
# points.md #668: real, final fix -- TOPO_XNOR turned out to be a
# genuine BITWISE not-XOR over all 32 bits, not a clean boolean invert
# (confirmed by testing: gave 0xFFFFFFFE instead of 0, since the eq
# result is 0/1 but XNOR inverts every bit of the 32-bit word). The
# real, working fix: `ne` reuses the exact same eq composition, then
# XORs its clean 0/1 result against a real, ONE-TIME-injected constant
# 1 -- XOR(1,1)=0, XOR(0,1)=1, an exact boolean NOT, not a bitwise one.
# Deliberately a real, one-time injection (matching this frontend's
# own established convention for every constant value), not a
# continuously-live ram_constant -- #611's own real finding already
# warned that a permanently-re-offering source contaminates a nano
# gate's own two-arrival timing once its shielding relay drains and
# reopens.
_EQ_TOPOLOGY = 0x0BC   # TOPO_XOR
_EQ_NE_PREDICATES = ("eq", "ne")
# points.md #718: real, confirmed-correct topology codes for LLVM's own
# bitwise and/or/xor, checked directly against unicell_gate_core.py's
# own compute_gate() table (verified there to do genuine, full 32-bit
# bitwise operations, not a boolean simplification) before using them.
_BITWISE_TOPOLOGY = {"and": 0x007, "or": 0x024, "xor": 0x0BC}


def _diag(problem: str, what: str, why: str, suggestion: Optional[str] = None) -> CompileDiagnostic:
    return CompileDiagnostic(severity="error", stage="llvm-frontend", what=what,
                              problem=problem, why=why, suggestion=suggestion)


@dataclass
class LlvmLoweringInfo:
    """Real, honest bookkeeping returned alongside the compiled ICM --
    everything a caller needs to actually VERIFY the lowering (inject
    the real starting values, run the real VM, check the real cell
    holding the final result), not just trust it compiled."""
    function_name: str
    result_cell: Tuple[int, int]
    expected_result: int
    chain_length: int
    #: real, one-time injections the caller must perform BEFORE
    #: ticking -- (row, col, value). Every real "constant" value this
    #: program needs (arguments and IR literals alike) enters the
    #: fabric this way, not via a permanently-broadcasting ram_constant
    #: -- see the module's own docstring for why.
    injections: List[Tuple[int, int, int]]


def _operand_name(operand) -> str:
    """A real, non-empty name for a %-named SSA value (an argument or
    a previous instruction's own result); empty string for a literal
    constant -- llvmlite's own real behavior, confirmed directly by
    testing before this was written, not assumed."""
    return operand.name


def _resolve_operand_value(operand, known_values: Dict[str, int]) -> Tuple[Optional[int], bool]:
    """Real, honest operand resolution. Returns (value_or_None,
    is_reference) -- `is_reference` is True for a real %-named SSA
    reference (needed so the chain-shape check can tell "this operand
    IS the previous instruction" apart from "this operand happens to
    equal the same literal value"), False for a literal constant."""
    name = operand.name
    if name:
        return known_values.get(name), True
    return _parse_literal(str(operand)), False


def _icmp_predicate(instr) -> Optional[str]:
    """Real, necessary text parsing -- llvmlite exposes no direct
    predicate accessor on an icmp instruction (confirmed by checking
    `dir(instr)` directly before writing this, not assumed), but the
    real instruction text always has the real, stable form
    "%name = icmp PRED TYPE %a, %b" -- the predicate is always the
    token right after "icmp"."""
    parts = str(instr).strip().split()
    if "icmp" in parts:
        idx = parts.index("icmp")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return None


def _parse_literal(text: str) -> Optional[int]:
    """Real, minimal literal parsing -- llvmlite's own operand.name for
    a constant int is the literal's own text form, e.g. "5" (bare) or,
    for some operand kinds, "i32 5". Handles both real forms seen in
    practice, nothing fancier."""
    text = text.strip()
    parts = text.split()
    token = parts[-1] if parts else text
    try:
        return int(token)
    except ValueError:
        return None


def _build_dag_relay(instr_name: str, first_name: str, diff_col: int,
                      statements: List[PlaceIR], injections: List[Tuple[int, int, int]],
                      diagnostics: List, needs_relay_tap: Dict[str, List[str]],
                      tapped_producers: Dict[str, int], dag_reference_ranges: List[Tuple[int, int, str]],
                      dag_reference_count: int, result_positions: Dict[str, Tuple[int, int]]) -> Optional[int]:
    """points.md #701/#713/#716/#717: the real relay/drop/trigger
    machinery every DAG-referencing consumer needs, extracted into a
    real, reusable function so `select`'s own, separately-shaped code
    path (three operands, not two) could use the EXACT SAME real
    mechanism as add/sub/icmp/shl/lshr, rather than a second, drifting
    copy of it. Mutates `statements`/`injections`/`tapped_producers`
    in place (matching every caller's own existing convention); returns
    the real, updated `dag_reference_count` on success, or `None` if a
    real overlap collision was found (with the diagnostic already
    appended to `diagnostics`).

    See #701's own real, original comments (preserved below) for the
    full reasoning behind each individual piece -- extraction changed
    nothing about the actual mechanism itself, only where the code
    lives."""
    producer_row, producer_col = result_positions[first_name]
    # points.md #713: real, shared-producer support -- lifts #701's
    # own "at most one consumer" restriction, using #706's own proven
    # daisy-chain mechanism (a drop's own `routing_mask` can hold more
    # than one direction: deliver to its own consumer AND relay onward
    # to the next drop in the same real trigger event). The pre-pass
    # already knows the FULL, ordered list of every consumer for this
    # producer, so each drop's own routing_mask (last in the chain
    # gets just north; every other gets north+east) is decided
    # correctly the first time, with no need to go back and modify an
    # already-emitted drop.
    consumer_list = needs_relay_tap[first_name]
    consumer_index = consumer_list.index(instr_name)
    is_last_in_chain = consumer_index == len(consumer_list) - 1
    is_first_in_chain = first_name not in tapped_producers
    relay_start_col = producer_col if is_first_in_chain else tapped_producers[first_name]
    # points.md #701: a real, found-empirically constraint -- the tap
    # and drop are both FORCED onto row 2 (the diff cell only has 4
    # real ports, 3 already spoken for: west/south for in_a, north for
    # in_b, east for out -- row 2 is the only real place left for
    # either end to connect from). That means two DIFFERENT DAG
    # references whose own real column ranges OVERLAP would need their
    # own intermediate relay cells to occupy the SAME row-2 positions
    # -- a real, genuine collision, not something a different row
    # choice can dodge (an earlier draft tried per-reference rows and
    # broke the tap's own single-hop connection to its producer,
    # confirmed by an actual failing compile before this check
    # existed). Detected explicitly, with a real, specific reason,
    # rather than relying on the placement layer's own generic "cell
    # already occupied" error to surface it indirectly. Real, honest
    # exception: a chain CONTINUING from the same producer's own
    # previous drop is not a real collision (it's the same,
    # intentional chain, #713) -- only ranges belonging to DIFFERENT
    # producers may not overlap.
    for used_start, used_end, used_instr in dag_reference_ranges:
        if used_instr in consumer_list:
            continue   # same producer's own daisy chain -- not a real collision
        if relay_start_col <= used_end and used_start <= diff_col:
            diagnostics.append(_diag(
                problem=f"instruction {instr_name!r}'s own DAG reference to {first_name!r} "
                         f"(columns {relay_start_col}-{diff_col}) overlaps an earlier one "
                         f"({used_instr!r}, columns {used_start}-{used_end})",
                what=f"lowering instruction {instr_name!r}",
                why="real, honest scope for this pass (#701/#713): a DAG reference's own "
                    "relay lane is forced onto row 2 (the only real free side of the diff "
                    "cell), so two references to DIFFERENT producers whose own column ranges "
                    "overlap would need the same row-2 cells -- a real geometric collision, "
                    "not one a different row choice can avoid without breaking the tap's own "
                    "single-hop connection to its producer",
                suggestion="restructure so DAG-referenced ranges from different producers "
                           "don't overlap, or wait for a real multi-lane relay design",
            ))
            return None
    dag_reference_ranges.append((relay_start_col, diff_col, instr_name))
    tapped_producers[first_name] = diff_col
    # points.md #712: relay lane back to the standard row 2 for EVERY
    # consumer, including eq/ne -- the earlier row-5 workaround was
    # needed only because icmp_eq/icmp_ne's own composed tile used to
    # occupy (row 2, diff_col) directly. Now that `diff`'s own south
    # port is genuinely free (the new `fanout` subcell takes over
    # feeding cmp0/cmp1), the drop's own required position -- directly
    # south of `diff`, at its exact column -- is clear again:
    # icmp_eq/icmp_ne's own internal cells at row 2 now sit one and
    # two columns further east (cmp1, xor_gate), not at diff_col
    # itself.
    relay_row = 2
    relay_col = relay_start_col if is_first_in_chain else relay_start_col + 1
    while relay_col <= diff_col:
        if is_first_in_chain and relay_col == producer_col:
            # the tap itself -- receives the producer's own real south
            # offering (added to the producer's own `out` field
            # elsewhere, via `needs_relay_tap`). Only placed for the
            # FIRST consumer in the chain -- later consumers relay
            # onward from the previous drop instead, which already
            # holds the value.
            statements.append(PlaceIR(
                name=f"op_{instr_name}_relay_tap", tile_name="ram_flowing", row=relay_row, col=relay_col,
                fields=[FieldIR("in", "n"), FieldIR("out", "e")],
            ))
        elif relay_col == diff_col:
            # points.md #700's own real drop cell -- holds the relayed
            # value, delivers it north into the diff cell only once
            # the real, explicit trigger below arrives from the south.
            # Sits DIRECTLY south of the diff cell itself (same
            # column), not one short of it -- confirmed the hard way:
            # an earlier draft placed it at `diff_col - 1`, delivering
            # to an empty cell instead of the diff cell's own real
            # south input. Real, #713's own extension: routing_mask
            # ALSO includes east (continuing the daisy chain onward)
            # unless this is genuinely the last consumer in its own
            # producer's own chain.
            statements.append(PlaceIR(
                name=f"op_{instr_name}_relay_drop", tile_name="nano_hold_trigger", row=relay_row, col=relay_col,
                fields=[FieldIR("out", "n" if is_last_in_chain else ["n", "e"])],
            ))
        else:
            statements.append(PlaceIR(
                name=f"op_{instr_name}_relay_{relay_col}", tile_name="ram_flowing", row=relay_row, col=relay_col,
                fields=[FieldIR("in", "w"), FieldIR("out", "e")],
            ))
        relay_col += 1

    # points.md #700's own real timing fix: the trigger's own chain is
    # DELIBERATELY built far longer than the tap-relay chain could
    # possibly need, so it is GUARANTEED to arrive at the drop only
    # after the drop has already captured the real relayed value --
    # correctness here doesn't actually depend on precisely which of
    # the two operands the diff cell captures first (`add`/`sub` are
    # commutative once `sub`'s own second operand is pre-negated,
    # #611), but the real, intended contract of this mechanism is
    # "delivery happens on an explicit trigger," and this margin makes
    # that genuinely true, not just true by coincidence.
    #
    # Real, found-empirically fix, distinct from the relay lane's own
    # row-2 constraint: the trigger's own horizontal run gets its OWN
    # unique row per DAG reference (`3 + dag_reference_count`), not a
    # shared row 3. A shared row failed for a real, non-obvious
    # reason: a LATER, LONGER trigger chain can "sweep through" the
    # exact same columns an EARLIER, SHORTER one already occupies on
    # that row, even when their own START columns are chosen to differ
    # (confirmed directly by an actual two-reference compile that
    # collided this way before this fix existed). Since the trigger
    # only needs to reach the drop (row 2) by SOME path, not directly
    # like the relay lane does, its own unique row descends to row 2
    # with a few extra hops right at the end, confined to the drop's
    # own column (always unique per instruction, so this short descent
    # never collides with another reference's own descent).
    trigger_row = relay_row + 1 + dag_reference_count
    trigger_start_col = -(2 * diff_col + 10)
    injections.append((trigger_row, trigger_start_col, 0))
    statements.append(PlaceIR(
        name=f"op_{instr_name}_trigger_src", tile_name="ram_flowing", row=trigger_row, col=trigger_start_col,
        fields=[FieldIR("in", "w"), FieldIR("out", "e")],
    ))
    trigger_col = trigger_start_col + 1
    while trigger_col <= diff_col:
        statements.append(PlaceIR(
            name=f"op_{instr_name}_trigger_{trigger_col}", tile_name="ram_flowing", row=trigger_row, col=trigger_col,
            fields=[FieldIR("in", "w"), FieldIR("out", "n" if trigger_col == diff_col else "e")],
        ))
        trigger_col += 1
    descend_row = trigger_row - 1
    while descend_row >= relay_row + 1:
        statements.append(PlaceIR(
            name=f"op_{instr_name}_trigger_descend_{descend_row}", tile_name="ram_flowing",
            row=descend_row, col=diff_col,
            fields=[FieldIR("in", "s"), FieldIR("out", "n")],
        ))
        descend_row -= 1
    return dag_reference_count + 1


def compile_llvm_ir(source: str, argument_values: Dict[str, int]
                     ) -> Tuple[Optional[Any], List[CompileDiagnostic], Optional[LlvmLoweringInfo]]:
    """The whole real pipeline: parse real LLVM IR text, enforce the
    real chain-shape restriction, build a real `ProgramIR`, hand off to
    the SAME shared backend every other frontend uses. Returns
    `(icm_file_or_None, diagnostics, lowering_info_or_None)`."""
    diagnostics: List[CompileDiagnostic] = []

    try:
        mod = llvm.parse_assembly(source)
        mod.verify()
    except RuntimeError as e:
        diagnostics.append(_diag(
            problem=str(e), what="parsing the supplied LLVM IR",
            why="the real LLVM parser (llvmlite) rejected this as invalid IR -- "
                "nothing downstream can proceed from IR that isn't real, valid LLVM IR",
        ))
        return None, diagnostics, None

    functions = list(mod.functions)
    if len(functions) != 1:
        diagnostics.append(_diag(
            problem=f"expected exactly one function, found {len(functions)}",
            what="checking the module's own real function count",
            why="this real, first frontend slice only handles a single function at a time (#611)",
            suggestion="split into separate compile_llvm_ir() calls, one function each",
        ))
        return None, diagnostics, None
    fn = functions[0]

    blocks = list(fn.blocks)
    if len(blocks) == 3:
        return _compile_single_counting_loop(fn, argument_values)
    if len(blocks) != 1:
        diagnostics.append(_diag(
            problem=f"function {fn.name!r} has {len(blocks)} basic blocks, expected exactly 1 "
                     f"(straight-line) or exactly 3 (a real, narrowly-restricted counting loop, #652)",
            what=f"checking {fn.name!r}'s own real control-flow shape",
            why="this real frontend slice supports only two real shapes: a single-block "
                "straight-line chain (#611), or a real, narrow 3-block counting loop (#652) -- "
                "general multi-block control flow remains real, explicitly deferred future work",
        ))
        return None, diagnostics, None
    block = blocks[0]

    arg_names = {a.name for a in fn.arguments}
    missing_args = arg_names - set(argument_values.keys())
    if missing_args:
        diagnostics.append(_diag(
            problem=f"no compile-time value supplied for argument(s): {sorted(missing_args)}",
            what=f"resolving {fn.name!r}'s own real arguments to compile-time values",
            why="this real, first frontend slice specializes a function for FIXED, compile-time-"
                "supplied argument values (#611) -- there is no general runtime-input mechanism yet",
            suggestion="pass every argument's real value in argument_values",
        ))
        return None, diagnostics, None

    instructions = list(block.instructions)
    if not instructions or instructions[-1].opcode != "ret":
        diagnostics.append(_diag(
            problem="the basic block doesn't end with a real 'ret' instruction",
            what="checking the block's own real terminator",
            why="a real, well-formed single-block function must end with ret",
        ))
        return None, diagnostics, None
    ret_instr = instructions[-1]
    body_instructions = instructions[:-1]

    if not body_instructions:
        diagnostics.append(_diag(
            problem="the function body has no real instructions to compile -- only a bare ret",
            what="checking the function has real work to lower",
            why="nothing to place on the fabric",
        ))
        return None, diagnostics, None

    # ── real, honest per-instruction value tracking, straight-line
    # interpretation done alongside the real lowering so the expected
    # result can actually be checked against the VM later ──
    known_values: Dict[str, int] = dict(argument_values)
    statements: List[PlaceIR] = []
    last_result_row = 1   # points.md #668: eq/ne's own real result lives at row 2 (the XOR gate), not row 1 -- updated below when placed
    injections: List[Tuple[int, int, int]] = []
    prev_instr_name: Optional[str] = None
    prev_icmp_predicate: Optional[str] = None   # points.md #674: tracked so select's own cond can be validated
    # points.md #701: real position tracking for general DAG routing --
    # every instruction's own final, readable result cell, keyed by
    # SSA name. Needed so a LATER, non-adjacent reference can find
    # WHERE to tap a relay chain from, without re-deriving it.
    result_positions: Dict[str, Tuple[int, int]] = {}
    # points.md #717: real, per-instruction predicate tracking -- lets
    # select's own cond DAG-reference check confirm a NON-ADJACENT
    # referenced icmp's own real predicate (excluding eq/ne, which
    # aren't valid cond sources, #668), the same way `prev_icmp_
    # predicate` already does for the ordinary, adjacent case.
    icmp_predicates: Dict[str, str] = {}
    needs_relay_tap = _compute_needs_relay_tap(body_instructions)
    # points.md #701: a real, found-empirically fix -- two DIFFERENT
    # DAG references (even from the SAME producer) can have
    # overlapping column ranges, which would otherwise collide on a
    # single shared pair of relay/trigger rows. Each DAG reference
    # gets its own exclusive pair of rows instead (2/3, 4/5, 6/7, ...),
    # confirmed necessary by an actual multi-reference compile that
    # failed with real, specific "cell already occupied" diagnostics
    # before this fix -- not a hypothetical.
    dag_reference_count = 0
    # points.md #713: tracks, per producer, the CURRENT end of its own
    # daisy chain (the column of the most recently placed drop) -- not
    # just whether it's been tapped at all, since #713 now allows more
    # than one consumer per producer.
    tapped_producers: Dict[str, int] = {}
    dag_reference_ranges: List[Tuple[int, int, str]] = []
    # points.md #613: a running column cursor, not a fixed `i + 1` --
    # icmp needs TWO physical columns (a diff cell + a comparator),
    # so instructions no longer map 1:1 onto columns. The invariant
    # this preserves: whatever sits at `col_cursor - 1` after placing
    # an instruction is ALWAYS that instruction's own real result
    # cell, so the next instruction's west neighbor is correct by
    # construction, with no separate bookkeeping needed.
    col_cursor = 1

    for i, instr in enumerate(body_instructions):
        if instr.opcode not in _SUPPORTED_OPCODES:
            diagnostics.append(_diag(
                problem=f"unsupported instruction: {instr.opcode!r} ({str(instr).strip()})",
                what=f"lowering instruction {i + 1} of {len(body_instructions)}",
                why=f"this real, first frontend slice only understands {sorted(_SUPPORTED_OPCODES)} (#611) -- "
                    "every other real LLVM opcode is explicitly deferred future work",
            ))
            return None, diagnostics, None

        if instr.opcode == "select":
            # points.md #674: LLVM's own ternary -- select i1 %cond, %true, %false.
            # A genuinely different operand shape (3, not 2) from every other
            # instruction this frontend handles, so it's validated and placed
            # entirely separately, before the ordinary 2-operand machinery below
            # ever runs.
            sel_operands = list(instr.operands)
            if len(sel_operands) != 3:
                diagnostics.append(_diag(
                    problem=f"select with {len(sel_operands)} operands, expected 3",
                    what=f"lowering instruction {i + 1} ({str(instr).strip()})",
                    why="a real select is always (cond, true_val, false_val)",
                ))
                return None, diagnostics, None
            if i != len(body_instructions) - 1:
                diagnostics.append(_diag(
                    problem=f"select is used mid-chain, not as the final instruction "
                             f"before ret ({str(instr).strip()})",
                    what=f"lowering instruction {i + 1} ({str(instr).strip()})",
                    why="select's own real result lands on a different physical row "
                        "than the ordinary chain convention (#674's own 5-cell "
                        "composition, not a single diff+comparator) -- a later "
                        "instruction reading it as an ordinary chain value would be "
                        "wired to the wrong cell. Only supported as the chain's own "
                        "final, returned value for now, the same real restriction "
                        "eq/ne already has (#668).",
                ))
                return None, diagnostics, None
            cond_name = _operand_name(sel_operands[0])
            select_cond_is_dag_reference = False
            if cond_name == prev_instr_name and prev_icmp_predicate in _ICMP_LOWERING:
                pass   # the ordinary, adjacent case -- unchanged
            elif (cond_name and cond_name in needs_relay_tap
                    and icmp_predicates.get(cond_name) in _ICMP_LOWERING):
                # points.md #717: select's own cond may now reference
                # a non-adjacent, EARLIER icmp too, using the same
                # real relay mechanism as every other DAG-eligible
                # opcode. Scoped identically to the ordinary case --
                # only slt/sle/sgt/sge (never eq/ne, which live at a
                # different row, #668) -- confirmed via the same real
                # per-instruction predicate tracking `prev_icmp_
                # predicate` already uses for the adjacent case.
                #
                # Real, honest limitation found while testing this,
                # left unresolved: this mechanism is real and correctly
                # wired, but no valid LLVM IR program in this frontend
                # can currently REACH it end-to-end. select must be the
                # final instruction, so a non-adjacent cond needs at
                # least one real instruction between the referenced
                # icmp and select -- but that instruction can't be
                # adjacent to the icmp (its own result is i1, and
                # nothing i1-typed can feed real i32 arithmetic; zext
                # isn't in _SUPPORTED_OPCODES), so it must itself be a
                # DAG reference to something EARLIER than the icmp --
                # and that reference's own relay lane, spanning from
                # its own producer up to itself, unavoidably straddles
                # the icmp's own column, genuinely colliding with
                # select's own reference under the real row-2
                # constraint (#701). Confirmed directly by exhausting
                # every real ordering that could plausibly avoid this,
                # not assumed. A real, separate, structural gap from
                # everything else #717 fixed -- not a bug in this
                # mechanism itself, which reuses the exact same,
                # already-proven `_build_dag_relay` used successfully
                # by add/sub/icmp/shl/lshr.
                select_cond_is_dag_reference = True
            else:
                diagnostics.append(_diag(
                    problem=f"select's own cond operand {cond_name or str(sel_operands[0])!r} "
                             f"isn't the immediately preceding ordinary icmp's own result, or a "
                             f"valid non-adjacent DAG reference to one",
                    what=f"lowering instruction {i + 1} ({str(instr).strip()})",
                    why="select's own cond must come from an ordinary icmp (slt/sle/sgt/sge, "
                        "never eq/ne, which live at a different row, #668) -- either the "
                        "immediately preceding instruction, or (#717) a non-adjacent DAG "
                        "reference to an earlier one",
                    suggestion="use an ordinary icmp (slt/sle/sgt/sge) as cond, either "
                               "adjacent or as a real DAG reference",
                ))
                return None, diagnostics, None
            true_value, _ = _resolve_operand_value(sel_operands[1], argument_values)
            false_value, _ = _resolve_operand_value(sel_operands[2], argument_values)
            if true_value is None or false_value is None:
                diagnostics.append(_diag(
                    problem="select's own true_val/false_val operands must both be "
                             "compile-time arguments or constants",
                    what=f"lowering instruction {i + 1} ({str(instr).strip()})",
                    why="neither can reference another instruction's result in this "
                        "real, first slice -- only cond may (and only the immediately "
                        "preceding icmp, per the check above)",
                ))
                return None, diagnostics, None

            cond_value = known_values[cond_name] & 1
            result = (true_value if cond_value else false_value) & 0xFFFFFFFF
            known_values[instr.name] = result

            # points.md #688: promoted to the real, registered `select`
            # composed tile (#686) -- ONE placement statement, not a
            # hand-inlined 10-cell sequence. The tile's own real
            # preload-only sub-cells (its internal zero/0xFFFFFFFF
            # constants, plus true_val/false_val below) are now seeded
            # via the real file-format-level mechanism (#687) --
            # automatically, at grid construction time, well before any
            # dynamically-computed operand like `cond` could possibly
            # arrive (it still has to traverse every earlier instruction
            # in this chain first) -- so the whole-program `injections`
            # list this frontend still uses for RUNTIME values no
            # longer needs (and must NOT include) any of select's own
            # internal constants; they are never delivered as live
            # events at all anymore.
            sub_col = col_cursor
            if select_cond_is_dag_reference:
                # points.md #717: `mask` (the composed tile's own real
                # subtractor subcell) sits at (row 1, sub_col) --
                # exactly the same real "row 1, one column" shape the
                # generic diff-cell relay already targets, so the
                # exact same real relay/drop/trigger mechanism applies
                # directly, with `sub_col` playing `diff_col`'s own
                # role.
                new_count = _build_dag_relay(
                    instr.name, cond_name, sub_col, statements, injections, diagnostics,
                    needs_relay_tap, tapped_producers, dag_reference_ranges, dag_reference_count,
                    result_positions,
                )
                if new_count is None:
                    return None, diagnostics, None
                dag_reference_count = new_count
            statements.append(PlaceIR(
                name=f"op_{i}", tile_name="select", row=0, col=sub_col,
                fields=[
                    FieldIR("cond", "s" if select_cond_is_dag_reference else "w"), FieldIR("out", "e"),
                    FieldIR("true_val", true_value), FieldIR("false_val", false_value),
                ],
            ))
            # points.md #716: widths bumped by 1 -- select's own
            # composed tile grew one column wider (the new `fanout`
            # cell, freeing `mask`'s own south port for the DAG relay
            # -- see composed_tile_library_v1.py's own real comment on
            # this restructuring).
            col_cursor = sub_col + 4
            last_result_row = 1
            prev_instr_name = instr.name
            result_positions[instr.name] = (last_result_row, col_cursor - 1)
            prev_icmp_predicate = None
            continue

        operands = list(instr.operands)
        if len(operands) != 2:
            diagnostics.append(_diag(
                problem=f"{instr.opcode} with {len(operands)} operands, expected 2",
                what=f"lowering instruction {i + 1} ({str(instr).strip()})",
                why="only real, binary add/sub are supported",
            ))
            return None, diagnostics, None

        first_value, first_is_ref = _resolve_operand_value(operands[0], known_values)
        second_value, second_is_ref = _resolve_operand_value(operands[1], known_values)
        first_name = operands[0].name
        second_name = operands[1].name

        # REAL chain-shape enforcement -- the one, explicit restriction
        # this whole frontend slice depends on being honest about.
        is_dag_reference = False
        if i == 0:
            if first_value is None:
                diagnostics.append(_diag(
                    problem=f"first instruction's own first operand {first_name or str(operands[0])!r} "
                             f"is not an argument or a resolved compile-time value",
                    what=f"lowering the chain's first instruction ({str(instr).strip()})",
                    why="the first instruction in the chain has no preceding instruction to "
                        "inherit a running value from -- its own first operand must be a "
                        "real argument or constant (#611's own stated restriction)",
                ))
                return None, diagnostics, None
        else:
            if first_is_ref and first_name == prev_instr_name:
                pass   # the ordinary, adjacent chain reference -- unchanged
            elif first_is_ref and first_name in needs_relay_tap and instr.opcode in ("add", "sub"):
                # points.md #701: a real, in-scope DAG reference -- the
                # pre-pass already confirmed BOTH ends are add/sub
                # (the commutative "adder" tile, #611's own negate-
                # and-add trick), so which of the diff cell's two real
                # operands arrives first doesn't affect correctness.
                is_dag_reference = True
            elif (first_is_ref and first_name in needs_relay_tap and instr.opcode == "icmp"
                    and _icmp_predicate(instr) in ("sge", "sgt")):
                # points.md #710: sge/sgt lower onto the commutative
                # "adder"+negate trick (#611), exactly like add/sub --
                # ZERO new timing work needed.
                is_dag_reference = True
            elif (first_is_ref and first_name in needs_relay_tap and instr.opcode == "icmp"
                    and _icmp_predicate(instr) in ("eq", "ne")):
                # points.md #712: eq/ne's own real diff==0 test (#668)
                # is genuinely sign-agnostic, exactly like sge/sgt is
                # commutative. Re-enabled here after the real, direct
                # cause of #710/#711's own failure was fixed -- the
                # relay drop needs `diff`'s own south port free, and
                # `icmp_eq`/`icmp_ne`'s composed tile now leaves it
                # free (the new `fanout` subcell takes over feeding
                # both cmp0/cmp1, #712).
                is_dag_reference = True
            elif (first_is_ref and first_name in needs_relay_tap and instr.opcode == "icmp"
                    and _icmp_predicate(instr) in ("slt", "sle")):
                # points.md #710: slt/sle use the real, order-sensitive
                # "subtractor" tile (A-B, not commutative) -- unlike
                # add/sub/sge/sgt, which operand arrives first at the
                # diff cell genuinely matters here. Confirmed EMPIRICALLY
                # rather than assumed, per Alan's own real fallback plan
                # ("move the selector back a cell, introduce a delay
                # cell, so you know they're in order") -- tested first
                # to see whether the natural timing already gives the
                # right order before building anything extra. It does:
                # the north constant is a near-instant injection, and
                # the DAG-relayed value is genuinely slower to arrive
                # even with no extra delay at all (it must travel the
                # full tap-relay-drop-trigger chain), so it naturally
                # lands second every time -- exactly the role `west`
                # already plays for the ordinary, non-DAG case. No
                # delay cell needed after all; the fallback stayed
                # unused because the direct approach already worked.
                is_dag_reference = True
            elif first_is_ref and first_name in needs_relay_tap and instr.opcode in ("shl", "lshr"):
                # points.md #716: confirmed directly against the real
                # emission code (#714's own scoping pass) before
                # building this -- the shift cell's own real ports are
                # ONLY west (in) and east (out); north and south are
                # both completely free, unlike icmp_eq/icmp_ne's own
                # real port-scarcity problem (#712). Only one real
                # dynamic operand exists at all (the shift amount is
                # compile-time config, never a second live arrival),
                # so there is no A-vs-B arrival-order question here --
                # simpler than even add/sub's own case.
                is_dag_reference = True
            else:
                why = ("this real, first frontend slice only supports a genuine LINEAR "
                       "ACCUMULATION CHAIN, not a general DAG (#611/#610) -- an instruction "
                       "referencing an earlier, non-immediately-preceding result needs real "
                       "relay-cell routing for a non-adjacent connection")
                suggestion = "reorder/restructure the IR into a straight accumulation chain"
                if first_is_ref and first_name in result_positions:
                    # points.md #701: a real, specific reason, not the
                    # generic message -- this IS a real earlier result,
                    # just not one DAG references are supported for yet
                    # (either the consumer or the producer is outside
                    # add/sub's own real commutative shape).
                    why = ("general DAG routing (#701/#710/#712/#716) is real but deliberately "
                           "narrow so far: add/sub, icmp's slt/sle/sgt/sge/eq/ne predicates, and "
                           "shl/lshr, may reference an EARLIER add/sub result -- all lower onto "
                           "forms where operand arrival order doesn't affect correctness (add/"
                           "sub/sge/sgt via the commutative adder+negate trick, slt/sle confirmed "
                           "empirically to work under the natural timing already present, eq/ne's "
                           "own real diff==0 test is genuinely sign-agnostic, shl/lshr have only "
                           "one real dynamic operand at all). and/or/xor are EXCLUDED for a real, "
                           "different, structural reason (#718), found directly: nano_gate has no "
                           "upstream_mask at all (accepts from ANY physically wired neighbor), so "
                           "it can't selectively ignore the physically adjacent chain wire the way "
                           "subtractor/adder can via in_a -- confirmed by an actual compile where "
                           "an unrelated adjacent instruction's own value silently won the race "
                           "instead of the intended DAG-relayed one. select has its own real, "
                           "separate result-row convention not yet accommodated, so none of the "
                           "two may be a DAG reference source or consumer yet")
                    suggestion = ("use add/sub/slt/sle/sgt/sge/eq/ne/shl/lshr on both ends of the "
                                  "reference, or wait for DAG routing to cover and/or/xor/select "
                                  "too")
                diagnostics.append(_diag(
                    problem=f"instruction {i + 1}'s own first operand is {first_name or str(operands[0])!r}, "
                             f"not the immediately preceding instruction's result ({prev_instr_name!r})",
                    what=f"lowering instruction {i + 1} ({str(instr).strip()})",
                    why=why,
                    suggestion=suggestion,
                ))
                return None, diagnostics, None

        if second_value is None:
            diagnostics.append(_diag(
                problem=f"instruction {i + 1}'s own second operand {second_name or str(operands[1])!r} "
                         f"is not an argument or a resolved compile-time value",
                what=f"lowering instruction {i + 1} ({str(instr).strip()})",
                why="the second operand of every instruction in this real, first frontend "
                    "slice must be a compile-time argument or constant (#611's own stated "
                    "restriction) -- it can never reference another instruction's result",
            ))
            return None, diagnostics, None

        if instr.opcode == "ashr":
            # points.md #703/#705: real, buildable via composition, not
            # new RTL -- `shift_fine_addon_v1.v` only ever performs a
            # plain LOGICAL shift (confirmed directly against the real
            # RTL, #690), but Alan's own sign-magnitude design (branch
            # for the conditional negate, nibble_mask+comparator for
            # lost-bit detection, `#702`/`#703`) closes the gap entirely
            # in software, from primitives that already exist. This is
            # that composition's own real frontend integration -- the
            # topology is `tests/vm/test_ashr_full_composition_v1.py`'s
            # own already-proven layout, ported to `place()` and
            # parameterized on `col_cursor`/the real shift amount.
            #
            # Real, deliberate scope for this pass, matching `#701`'s
            # own narrow-first discipline: only an adjacent chain value
            # (or, for i==0, the function argument) may be shifted --
            # `ashr` is not (yet) a valid DAG-reference source or
            # target. The existing chain-shape check already enforces
            # this correctly (its own add/sub-only DAG carve-out simply
            # never matches `ashr`), so no separate check is needed
            # here.
            if not (0 <= second_value <= 31):
                diagnostics.append(_diag(
                    problem=f"ashr amount {second_value} is outside the real, "
                             f"supported 0-31 range",
                    what=f"lowering instruction {i + 1} ({str(instr).strip()})",
                    why="a 32-bit shift by more than 31 bits is undefined in LLVM itself, "
                        "and every real cardinal cell's own shift addon chain caps out at 31 "
                        "(28 max coarse tap + 3 max fine) -- there is no larger real amount "
                        "to lower this to",
                ))
                return None, diagnostics, None

            # points.md #705->#708->#709: the real limit found in #705
            # (`nibble_mask`'s own 4-bit hardware granularity can't
            # precisely extract a non-nibble-aligned low-bit range) is
            # now lifted -- Alan's own real idea, verified in #708:
            # shifting LEFT by (32-K) discards everything except the
            # low K bits (zero-filled off the top), and shifting the
            # SAME amount back RIGHT restores their position with the
            # same zero-fill clearing everything above bit K-1. Uses
            # ONLY the existing shift mechanism (#690), already proven
            # at full 0-31 bit precision -- no new RTL needed. The
            # real, honest edge case: K=0 needs no chain at all (32-0
            # is out of the real 0-31 shift range, and the answer is
            # already known at compile time -- zero bits are ever
            # shifted out, so the correction is always 0).

            def _real_ashr(x: int, n: int) -> int:
                x &= 0xFFFFFFFF
                if x >= 0x80000000:
                    x -= 0x100000000
                return (x >> n) & 0xFFFFFFFF

            result = _real_ashr(first_value, second_value)
            known_values[instr.name] = result

            coarse, fine = _decompose_shift(second_value)
            if second_value > 0:
                extract_coarse, extract_fine = _decompose_shift(32 - second_value)

            base_col = col_cursor
            if i == 0:
                # Real, found-empirically fix (#701/#702's own
                # discipline continued): injecting the reference (0)
                # and the function argument into the SAME cell would
                # be OR-merged together on the same tick (confirmed
                # directly against `SuperGrid.tick()`'s own real
                # handling of simultaneous injected events) --
                # silently corrupting the reference. Routing the
                # argument through a SEPARATE cell one hop further
                # west avoids the collision entirely: the two
                # injections land in different `_pending` entries, and
                # west_feeder's own ordinary "reject while already
                # holding a value" behavior then enforces the correct
                # order (reference drains into branch first) with no
                # extra timing logic needed at all.
                injections.append((1, base_col - 1, first_value))
                statements.append(PlaceIR(
                    name=f"op_{i}_operand_source", tile_name="ram_flowing", row=1, col=base_col - 1,
                    fields=[FieldIR("in", "w"), FieldIR("out", "e")],
                ))
            injections.append((1, base_col, 0))
            statements.append(PlaceIR(
                name=f"op_{i}_west_feeder", tile_name="ram_flowing", row=1, col=base_col,
                fields=[FieldIR("in", "w"), FieldIR("out", "e")],
            ))
            statements.append(PlaceIR(
                name=f"op_{i}_branch", tile_name="branch", row=1, col=base_col + 1,
                fields=[
                    FieldIR("in", "w"), FieldIR("rolling_mode", 0),
                    FieldIR("route_low", ["e"]), FieldIR("route_equal", ["s"]), FieldIR("route_high", ["s"]),
                ],
            ))
            # ── negative path (x<0): negate -> lshr -> re-negate ->
            # subtract the lost-bit correction. Order matters here --
            # the correction must apply AFTER re-negation, not before
            # (the exact ordering mistake #702's own verification
            # script caught once already, and #703's first circuit
            # draft caught a second time). ──
            statements.append(PlaceIR(
                name=f"op_{i}_subtractor_neg", tile_name="subtractor", row=1, col=base_col + 2,
                fields=[FieldIR("in_a", "w"), FieldIR("in_b", "n"),
                        FieldIR("out", "e" if second_value == 0 else ["e", "s"])],
            ))
            statements.append(PlaceIR(
                name=f"op_{i}_zero_for_negate", tile_name="ram_flowing", row=0, col=base_col + 2,
                fields=[FieldIR("in", "n"), FieldIR("out", "s")],
            ))
            injections.append((0, base_col + 2, 0))
            statements.append(PlaceIR(
                name=f"op_{i}_lshr_shift_neg", tile_name="ram_flowing", row=1, col=base_col + 3,
                fields=[
                    FieldIR("in", "w"), FieldIR("out", "e"),
                    FieldIR("addon.shift_en", 1), FieldIR("addon.direction", 1),
                    FieldIR("addon.shift_amt", coarse), FieldIR("addon.shift_fine", fine),
                ],
            ))
            statements.append(PlaceIR(
                name=f"op_{i}_lshr_sink_neg", tile_name="ram_flowing", row=1, col=base_col + 4,
                fields=[FieldIR("in", "w"), FieldIR("out", "e")],
            ))
            statements.append(PlaceIR(
                name=f"op_{i}_re_negate", tile_name="subtractor", row=1, col=base_col + 5,
                fields=[FieldIR("in_a", "w"), FieldIR("in_b", "n"), FieldIR("out", "e")],
            ))
            statements.append(PlaceIR(
                name=f"op_{i}_zero_for_renegate", tile_name="ram_flowing", row=0, col=base_col + 5,
                fields=[FieldIR("in", "n"), FieldIR("out", "s")],
            ))
            injections.append((0, base_col + 5, 0))
            if second_value == 0:
                # Real, much simpler fix: for K=0 the correction is
                # ALWAYS 0 (zero bits are ever shifted out), so
                # subtract_correction doesn't need to exist at all --
                # re_negate's own output can pass straight through.
                # An earlier draft tried to build the lost-bit
                # machinery anyway and feed it a compile-time zero,
                # but hit a real timing mismatch (a plain relay chain
                # and an adder-based chain of the same HOP COUNT don't
                # take the same real TICK COUNT) that needed
                # increasingly complex fixes for no real benefit --
                # skipping the machinery entirely is both simpler and
                # correct by construction.
                statements.append(PlaceIR(
                    name=f"op_{i}_subtract_correction", tile_name="ram_flowing", row=1, col=base_col + 6,
                    fields=[FieldIR("in", "w"), FieldIR("out", "e")],
                ))
            else:
                statements.append(PlaceIR(
                    name=f"op_{i}_subtract_correction", tile_name="subtractor", row=1, col=base_col + 6,
                    fields=[FieldIR("in_a", "w"), FieldIR("in_b", "s"), FieldIR("out", "e")],
                ))
            # ── lost-bit spine (row 2): real, arbitrary-precision
            # extraction (#708) -- shift left by (32-K) discards
            # everything except the low K bits, shift right by the
            # same amount restores them with correct zero-fill.
            # comparator(threshold=1) then gives the exact 0/1
            # correction directly, same as before (#702). For K=0, no
            # spine is built at all -- see the note above. ──
            if second_value > 0:
                statements.append(PlaceIR(
                    name=f"op_{i}_lost_bit_shift_left", tile_name="ram_flowing", row=2, col=base_col + 2,
                    fields=[FieldIR("in", "n"), FieldIR("out", "e"),
                            FieldIR("addon.shift_en", 1), FieldIR("addon.direction", 0),
                            FieldIR("addon.shift_amt", extract_coarse), FieldIR("addon.shift_fine", extract_fine)],
                ))
                statements.append(PlaceIR(
                    name=f"op_{i}_lost_bit_catch1", tile_name="ram_flowing", row=2, col=base_col + 3,
                    fields=[FieldIR("in", "w"), FieldIR("out", "e")],
                ))
                statements.append(PlaceIR(
                    name=f"op_{i}_lost_bit_shift_right", tile_name="ram_flowing", row=2, col=base_col + 4,
                    fields=[FieldIR("in", "w"), FieldIR("out", "e"),
                            FieldIR("addon.shift_en", 1), FieldIR("addon.direction", 1),
                            FieldIR("addon.shift_amt", extract_coarse), FieldIR("addon.shift_fine", extract_fine)],
                ))
                statements.append(PlaceIR(
                    name=f"op_{i}_lost_bit_catch2", tile_name="ram_flowing", row=2, col=base_col + 5,
                    fields=[FieldIR("in", "w"), FieldIR("out", "e")],
                ))
                statements.append(PlaceIR(
                    name=f"op_{i}_lost_bit_comparator", tile_name="comparator", row=2, col=base_col + 6,
                    fields=[FieldIR("in", "w"), FieldIR("out", "n"), FieldIR("threshold", 1)],
                ))
            # ── positive/zero path (x>=0): no correction is ever
            # needed (logical and arithmetic shift are identical for
            # non-negative values) -- a genuinely shorter route, padded
            # with plain relays to reach the shared final merge. ──
            statements.append(PlaceIR(
                name=f"op_{i}_transit", tile_name="ram_flowing", row=2, col=base_col + 1,
                fields=[FieldIR("in", "n"), FieldIR("out", "s")],
            ))
            statements.append(PlaceIR(
                name=f"op_{i}_direct_relay", tile_name="ram_flowing", row=3, col=base_col + 1,
                fields=[FieldIR("in", "n"), FieldIR("out", "e")],
            ))
            statements.append(PlaceIR(
                name=f"op_{i}_lshr_shift_pos", tile_name="ram_flowing", row=3, col=base_col + 2,
                fields=[
                    FieldIR("in", "w"), FieldIR("out", "e"),
                    FieldIR("addon.shift_en", 1), FieldIR("addon.direction", 1),
                    FieldIR("addon.shift_amt", coarse), FieldIR("addon.shift_fine", fine),
                ],
            ))
            statements.append(PlaceIR(
                name=f"op_{i}_lshr_sink_pos", tile_name="ram_flowing", row=3, col=base_col + 3,
                fields=[FieldIR("in", "w"), FieldIR("out", "e")],
            ))
            for pad_i, pad_col in enumerate((base_col + 4, base_col + 5, base_col + 6)):
                statements.append(PlaceIR(
                    name=f"op_{i}_pos_pad_{pad_i}", tile_name="ram_flowing", row=3, col=pad_col,
                    fields=[FieldIR("in", "w"), FieldIR("out", "e")],
                ))
            statements.append(PlaceIR(
                name=f"op_{i}_pos_pad_last", tile_name="ram_flowing", row=3, col=base_col + 7,
                fields=[FieldIR("in", "w"), FieldIR("out", "n")],
            ))
            statements.append(PlaceIR(
                name=f"op_{i}_pos_pad_up", tile_name="ram_flowing", row=2, col=base_col + 7,
                fields=[FieldIR("in", "s"), FieldIR("out", "n")],
            ))
            # ── final merge ──
            statements.append(PlaceIR(
                name=f"op_{i}", tile_name="ram_flowing", row=1, col=base_col + 7,
                fields=[FieldIR("in", ["w", "s"]), FieldIR("out", "e")],
            ))

            col_cursor = base_col + 8
            last_result_row = 1
            prev_instr_name = instr.name
            result_positions[instr.name] = (last_result_row, col_cursor - 1)
            prev_icmp_predicate = None
            continue

        if instr.opcode in ("shl", "lshr"):
            if not (0 <= second_value <= 31):
                diagnostics.append(_diag(
                    problem=f"{instr.opcode} amount {second_value} is outside the real, "
                             f"supported 0-31 range",
                    what=f"lowering instruction {i + 1} ({str(instr).strip()})",
                    why="a 32-bit shift by more than 31 bits is undefined in LLVM itself, "
                        "and every real cardinal cell's own shift addon chain caps out at 31 "
                        "(28 max coarse tap + 3 max fine) -- there is no larger real amount "
                        "to lower this to",
                ))
                return None, diagnostics, None

            result = ((first_value << second_value) if instr.opcode == "shl"
                      else (first_value >> second_value)) & 0xFFFFFFFF
            known_values[instr.name] = result
            # points.md #716: real placement moved to AFTER the shared
            # relay-building block below (an earlier draft had this
            # here, "continue"ing BEFORE that block ever ran -- the
            # exact same real ordering bug #712 found and fixed for
            # icmp_eq/icmp_ne, confirmed to apply here too before
            # writing any placement code this time).

        if instr.opcode == "icmp":
            predicate = _icmp_predicate(instr)
            if predicate not in _ICMP_LOWERING and predicate not in _EQ_NE_PREDICATES:
                diagnostics.append(_diag(
                    problem=f"icmp predicate {predicate!r} not supported ({str(instr).strip()})",
                    what=f"lowering instruction {i + 1} ({str(instr).strip()})",
                    why=f"this real, first frontend slice only understands "
                        f"{sorted(list(_ICMP_LOWERING) + list(_EQ_NE_PREDICATES))} (#613/#668)",
                ))
                return None, diagnostics, None
            if predicate in _EQ_NE_PREDICATES and i != len(body_instructions) - 1:
                diagnostics.append(_diag(
                    problem=f"icmp {predicate!r} is used mid-chain, not as the final instruction "
                             f"before ret ({str(instr).strip()})",
                    what=f"lowering instruction {i + 1} ({str(instr).strip()})",
                    why="eq/ne's own real result lands on a different physical row than the "
                        "ordinary chain convention (#668's own real 6-cell composition, not a "
                        "single comparator) -- a later instruction reading it as an ordinary "
                        "chain value would be wired to the wrong cell. Only supported as the "
                        "chain's own final, returned value for now.",
                    suggestion="restructure so the eq/ne comparison is the last real instruction "
                               "before ret, or wait for general multi-row chain routing to be built",
                ))
                return None, diagnostics, None
            if predicate in _EQ_NE_PREDICATES:
                # points.md #712: a real, separate sign-representation
                # bug, same root cause as #710's own signed-comparison
                # fix but a different symptom -- first_value (always
                # stored unsigned via known_values) and second_value (a
                # raw literal straight from the IR, not necessarily
                # unsigned-masked) can represent the SAME real value in
                # two DIFFERENT Python representations (4294967291 vs
                # -5), making a direct `==` wrongly false. Masking both
                # to the same unsigned 32-bit representation before
                # comparing fixes it -- equality doesn't care about
                # sign, only about matching representations.
                result = 1 if ((first_value & 0xFFFFFFFF) == (second_value & 0xFFFFFFFF)) == (predicate == "eq") else 0
            else:
                # points.md #710: a real, pre-existing sign bug found
                # by DAG-referencing a negative computed value for the
                # first time -- known_values stores every result as
                # unsigned 32-bit (the line below masks it), but
                # slt/sle/sgt/sge need a genuinely SIGNED comparison.
                # Never triggered before this, since every earlier
                # icmp test happened to compare against a value that
                # was never both computed AND negative.
                def _as_signed32(v: int) -> int:
                    v &= 0xFFFFFFFF
                    return v - 0x100000000 if v >= 0x80000000 else v
                signed_first, signed_second = _as_signed32(first_value), _as_signed32(second_value)
                result = 1 if {
                    "sge": signed_first >= signed_second, "sgt": signed_first > signed_second,
                    "slt": signed_first < signed_second, "sle": signed_first <= signed_second,
                }[predicate] else 0
        elif instr.opcode in ("and", "or", "xor"):
            # points.md #718: compute_gate's own real NOR-decomposition
            # (unicell_gate_core.py) already does genuine, full 32-bit
            # bitwise and/or/xor -- confirmed directly before writing
            # any of this, not assumed -- so this Python-side
            # computation can use the exact same native operators
            # without any real risk of diverging from what the VM
            # actually computes.
            result = {"and": first_value & second_value, "or": first_value | second_value,
                      "xor": first_value ^ second_value}[instr.opcode]
        else:
            result = first_value + second_value if instr.opcode == "add" else first_value - second_value
        # Real hardware is 32-bit, always -- masking here keeps the
        # Python-side expected value honestly comparable to what the
        # VM will actually compute, no silent divergence for negative/
        # overflowing intermediate results.
        if instr.opcode not in ("shl", "lshr"):
            # points.md #716: shl/lshr already computed and stored
            # their own correct result earlier -- this shared
            # add/sub/icmp result computation must not run for them at
            # all (it would silently overwrite the real answer with a
            # wrong, sub-shaped one).
            result &= 0xFFFFFFFF
            known_values[instr.name] = result

        # ── place the real, two-operand "diff" cell every one of these
        # instructions needs (add/sub compute it directly; icmp uses it
        # as the input to a downstream comparator) -- shared logic,
        # points.md #611's own already-verified real design ──
        diff_col = col_cursor
        if instr.opcode == "icmp":
            if predicate in _EQ_NE_PREDICATES:
                # points.md #668: eq/ne's own real test (diff==0 exactly)
                # is genuinely sign-agnostic -- a nonzero diff of EITHER
                # sign makes both comparators agree (both 0 for a
                # negative diff, both 1 for a positive one), giving
                # XOR=0 either way; only diff==0 splits them. So which
                # operand order the subtractor's own real north-minus-
                # west hardware produces doesn't matter here, unlike
                # slt/sgt's own real asymmetric case -- reusing the same
                # "subtractor, no negation" wiring as slt/sle purely for
                # consistency with the rest of this table, not because
                # eq/ne needs that specific sign.
                diff_tile, negate_north = "subtractor", False
            else:
                diff_tile, negate_north, threshold = _ICMP_LOWERING[predicate]
        elif instr.opcode == "sub":
            diff_tile, negate_north = "adder", True
        elif instr.opcode in ("and", "or", "xor"):
            # points.md #718: real placement happens in its own,
            # separate special-case block below (after the shared
            # relay-building block) -- nano_gate has no in_a/in_b
            # named ports at all (accepts from ANY wired neighbor,
            # #701's own tile registration), so it can't reuse the
            # generic subtractor/adder-shaped diff-cell emission this
            # variable feeds. Set here only so nothing downstream
            # falls through to the misleading "adder" default.
            diff_tile, negate_north = None, None
        else:
            diff_tile, negate_north = "adder", False

        # points.md #611: a real, necessary redesign, found empirically
        # by tracing actual VM ticks, not assumed correct from the
        # start. TWO real facts about the adder's own "two-arrival"
        # model, confirmed directly against _deliver_adder():
        # (1) simultaneous arrivals from two different neighbors on the
        # SAME tick get bitwise-OR'd into ONE combined value, not
        # captured as separate A/B; (2) a CONTINUOUSLY-LIVE source
        # (ram_constant, "permanent, never-recaptured") never stops
        # re-offering -- even shielding it behind a single-shot
        # ram_flowing relay only delays the contamination, since the
        # relay itself re-opens and recaptures from the still-live
        # source behind it once drained, eventually racing against
        # the real chain value and corrupting the result (confirmed:
        # a real, observed 20 instead of 18 on the very first two-
        # instruction chain tried). The real, robust fix: every raw
        # value this program needs (arguments AND IR literals alike)
        # is delivered via a real, ONE-TIME `VMSession.inject()` into a
        # `ram_flowing` cell with no real upstream neighbor at all --
        # once delivered and drained, there is nothing left to ever
        # refill or resend it. `LlvmLoweringInfo.injections` carries
        # the real (row, col, value) triples the caller must inject
        # before ticking.
        # Real, deliberate design choice, found necessary by testing
        # `sub` end-to-end, not assumed correct: this layout's own real
        # arrival order always has NORTH land strictly before WEST
        # (confirmed directly by tracing) -- meaning the hardware's own
        # "whichever arrives first becomes A" would make subtract_mode
        # compute second_value - first_value, the WRONG order for
        # LLVM's `sub first, second`. Rather than fight the arrival
        # order, `sub` (and icmp's sge/sgt, which need the same real
        # A-B shape) is lowered as a plain ADD of the real, 32-bit
        # two's-complement NEGATION of second_value -- mathematically
        # identical to a real subtraction, reusing the exact same add
        # pathway already confirmed correct. icmp's slt/sle need the
        # OPPOSITE real shape (B-A) -- rather than negate the WEST
        # operand (impossible once i>0, since it's a physical wire
        # carrying a prior instruction's own real output, not
        # something that can be retroactively negated at its source),
        # the real "subtractor" tile's own hardware ordering
        # (north-arrives-first minus west-arrives-second) gives
        # north(B) - west(A) directly, with NEITHER operand needing
        # negation at all.
        north_value = ((-second_value) & 0xFFFFFFFF) if negate_north else second_value
        injections.append((0, diff_col, north_value))
        statements.append(PlaceIR(
            name=f"value_north_{i}", tile_name="ram_flowing", row=0, col=diff_col,
            fields=[FieldIR("in", "n"), FieldIR("out", "s")],
        ))
        if i == 0:
            # Real, necessary stagger: op_0's own west and north feeders
            # would otherwise both deliver their one-time injection on
            # the SAME tick (simultaneous single-shot arrivals still
            # OR-combine, per the real fact above) -- given west and
            # north are the SAME distance (1 hop) from op_0 otherwise.
            # A real, harmless (no resend risk now -- pure single-shot)
            # extra relay hop on the west path guarantees it arrives
            # strictly one tick after north's.
            injections.append((1, diff_col - 2, first_value))
            statements.append(PlaceIR(
                name="value_west0a", tile_name="ram_flowing", row=1, col=diff_col - 2,
                fields=[FieldIR("in", "w"), FieldIR("out", "e")],
            ))
            statements.append(PlaceIR(
                name="value_west0", tile_name="ram_flowing", row=1, col=diff_col - 1,
                fields=[FieldIR("in", "w"), FieldIR("out", "e")],
            ))
        # points.md #688: eq/ne promoted to the real, registered
        # `icmp_eq`/`icmp_ne` composed tiles (#686) -- each one's own
        # internal "diff" sub-cell (offset (0,0)) IS the shared diff
        # cell every other icmp predicate also needs, so eq/ne places
        # ONE composed-tile statement here instead of a bare diff cell
        # PLUS a separately-appended 6-cell (or 8-cell, ne) extra
        # structure. The preload-only `one_const` inside `icmp_ne`
        # (#686) is seeded via the real file-format mechanism (#687),
        # automatically, well before this instruction's own dynamic
        # operand(s) could possibly arrive -- no manual injection or
        # timing stagger needed for it at all.
        # points.md #701: real DAG-reference relay -- built BEFORE the
        # diff cell itself, since the diff cell's own `in_a` direction
        # depends on whether a relay drop feeds it (south) or an
        # ordinary chain neighbor does (west). Real geometry, chosen
        # to never collide with anything this frontend already places:
        # row 0 is fully occupied by every instruction's own compile-
        # time constant feeder, so the relay lane runs at row 2 (one
        # row south of the main chain), and the trigger's own delay
        # chain at row 3 (one further south still) -- neither row is
        # touched by anything else this frontend emits.
        if is_dag_reference:
            new_count = _build_dag_relay(
                instr.name, first_name, diff_col, statements, injections, diagnostics,
                needs_relay_tap, tapped_producers, dag_reference_ranges, dag_reference_count,
                result_positions,
            )
            if new_count is None:
                return None, diagnostics, None
            dag_reference_count = new_count


        if instr.opcode in ("and", "or", "xor"):
            # points.md #718: real, minimal placement -- genuinely
            # simpler than every other two-operand opcode so far.
            # nano_gate has no in_a/in_b named ports at all (accepts
            # from ANY physically wired neighbor, confirmed directly
            # against its own real tile registration) -- there's
            # nothing to wire differently for a DAG reference (south)
            # vs the ordinary case (west); either way, the gate simply
            # captures whichever two real values arrive. And/or/xor are
            # all genuinely commutative, so arrival order never affects
            # correctness either way -- no ordering question to test at
            # all, unlike icmp's own slt/sle (#710).
            #
            # Real, found-empirically fix: BOTH the shared
            # "value_north_i" feeder AND the i==0 west-side stagger
            # relay (above, #611) already run unconditionally for
            # every opcode that reaches this point -- shl/lshr never
            # collide with either only because they never create a
            # second operand feeder of their own at all. and/or/xor DO
            # need one, so this reuses both already-placed feeders
            # directly (the north feeder's own real value is already
            # correct: `negate_north` is None/falsy here, giving
            # `north_value == second_value`) instead of placing
            # second, colliding ones.
            gate_col = diff_col
            statements.append(PlaceIR(
                name=f"op_{i}", tile_name="nano_gate", row=1, col=gate_col,
                fields=[FieldIR("out", "e"), FieldIR("topology", _BITWISE_TOPOLOGY[instr.opcode])],
            ))
            col_cursor = gate_col + 1
            last_result_row = 1
            prev_instr_name = instr.name
            result_positions[instr.name] = (last_result_row, col_cursor - 1)
            prev_icmp_predicate = None
            continue

        if instr.opcode in ("shl", "lshr"):
            # points.md #716: real placement, moved here (after the
            # shared relay-building block) so a DAG reference gets its
            # own relay/drop/trigger machinery correctly. Genuinely
            # simpler than add/sub/icmp's own shared "diff cell"
            # scaffold -- shl/lshr have only ONE real dynamic input, so
            # `in_a`-equivalent (`in`) just needs to respect
            # `is_dag_reference` (south vs west); there is no second
            # operand to worry about arrival order with at all.
            coarse, fine = _decompose_shift(second_value)
            shift_col = diff_col
            if i == 0:
                # No stagger needed (unlike add/sub/icmp's own i==0
                # case): there is only ever ONE injected value here,
                # never a second one landing on the same tick.
                injections.append((1, shift_col, first_value))
            statements.append(PlaceIR(
                name=f"op_{i}_shift", tile_name="ram_flowing", row=1, col=shift_col,
                fields=[
                    FieldIR("in", "s" if is_dag_reference else "w"), FieldIR("out", "e"),
                    FieldIR("addon.shift_en", 1),
                    FieldIR("addon.direction", 1 if instr.opcode == "lshr" else 0),
                    FieldIR("addon.shift_amt", coarse),
                    FieldIR("addon.shift_fine", fine),
                ],
            ))
            statements.append(PlaceIR(
                name=f"op_{i}", tile_name="ram_flowing", row=1, col=shift_col + 1,
                fields=[FieldIR("in", "w"), FieldIR("out", "e")],
            ))
            col_cursor = shift_col + 2
            last_result_row = 1
            prev_instr_name = instr.name
            result_positions[instr.name] = (last_result_row, col_cursor - 1)
            prev_icmp_predicate = None
            continue

        if instr.opcode == "icmp" and predicate in _EQ_NE_PREDICATES:
            # points.md #710: moved to AFTER the relay-building block
            # above so a DAG reference into eq/ne would get its own
            # relay/drop/trigger machinery, if one were ever built for
            # it. `in_a` respects `is_dag_reference` the same way the
            # generic diff-cell emission below does -- but a real,
            # structural conflict was found and left unresolved here,
            # not fixed: the relay drop must sit DIRECTLY south of the
            # diff cell (the only real free side), and icmp_eq/
            # icmp_ne's own composed tile (#686) already occupies
            # exactly that position with its own internal cmp1/
            # xor_gate subcells. `is_dag_reference` can never actually
            # be True here today (the chain-shape check above excludes
            # eq/ne for precisely this reason) -- this code is ready
            # for whenever that composed tile's own internal layout
            # gets restructured to leave that position free.
            statements.append(PlaceIR(
                name=f"op_{i}", tile_name=f"icmp_{predicate}", row=1, col=diff_col,
                fields=[FieldIR("in_a", "s" if is_dag_reference else "w"), FieldIR("in_b", "n"),
                        FieldIR("out", "e")],
            ))
            # points.md #712: widths bumped by 1 -- icmp_eq/icmp_ne's
            # own composed tile grew one column wider (the new
            # `fanout` cell, freeing `diff`'s own south port for the
            # DAG relay -- see composed_tile_library_v1.py's own real
            # comment on this restructuring).
            col_cursor = diff_col + (4 if predicate == "ne" else 3)
            last_result_row = 2
            prev_instr_name = instr.name
            result_positions[instr.name] = (last_result_row, col_cursor - 1)
            prev_icmp_predicate = predicate
            continue

        statements.append(PlaceIR(
            name=f"op_{i}", tile_name=diff_tile, row=1, col=diff_col,
            fields=[FieldIR("in_a", "s" if is_dag_reference else "w"), FieldIR("in_b", "n"),
                    FieldIR("out", ["e", "s"] if instr.name in needs_relay_tap else "e")],
        ))

        if instr.opcode == "icmp":
            # points.md #688: eq/ne no longer reach this point at all --
            # handled and `continue`d earlier, above, via the real
            # `icmp_eq`/`icmp_ne` composed tiles (#686). Only the
            # ordinary threshold-comparator predicates (slt/sle/sge/sgt)
            # still take this path.
            # points.md #613: comparator sits immediately EAST of the
            # diff cell -- its own real "in" port (single, not two --
            # comparator only ever compares ONE dynamic value against a
            # FIXED, compile-time threshold, confirmed directly against
            # its own real tile registration) receives the diff cell's
            # own real output directly, no relay/timing concerns at all
            # since this is a genuine single-arrival delivery, not a
            # two-arrival capture.
            cmp_col = diff_col + 1
            statements.append(PlaceIR(
                name=f"op_{i}_cmp", tile_name="comparator", row=1, col=cmp_col,
                fields=[FieldIR("in", "w"), FieldIR("out", "e")],
                # threshold is a required param, resolved above per predicate
            ))
            # real param goes on its own field entry (kept separate for clarity)
            statements[-1].fields.append(FieldIR("threshold", threshold))
            col_cursor = cmp_col + 1
        else:
            col_cursor = diff_col + 1

        prev_instr_name = instr.name
        result_positions[instr.name] = (last_result_row, col_cursor - 1)
        prev_icmp_predicate = predicate if instr.opcode == "icmp" else None
        if instr.opcode == "icmp":
            icmp_predicates[instr.name] = predicate

    ret_operand_name = _operand_name(list(ret_instr.operands)[0])
    if ret_operand_name != prev_instr_name:
        diagnostics.append(_diag(
            problem=f"ret returns {ret_operand_name!r}, not the chain's own final result {prev_instr_name!r}",
            what="checking the function's own real return value",
            why="this real, first frontend slice only supports returning the chain's own final "
                "computed value, not an earlier intermediate or a bare argument/constant",
        ))
        return None, diagnostics, None

    program_ir = ProgramIR(name=fn.name, statements=statements)
    icm, backend_diags = compile_program_ir(program_ir, program_name_hint=fn.name)
    diagnostics.extend(backend_diags)
    if icm is None:
        return None, diagnostics, None

    info = LlvmLoweringInfo(
        function_name=fn.name,
        result_cell=(last_result_row, col_cursor - 1),
        expected_result=known_values[prev_instr_name],
        chain_length=len(body_instructions),
        injections=injections,
    )
    return icm, diagnostics, info


# ═══════════════════════════════════════════════════════════════════════
# points.md #652/#653: the real, narrowly-restricted single COUNTING LOOP
# shape -- entry unconditionally branches to loop; loop holds exactly one
# phi (constant from entry, self-reference from loop's own increment),
# one add increment, one icmp (slt only, v1), one conditional br back to
# loop or out to exit; exit holds exactly one ret of the loop's own final
# value. Lowered to #638/#649/#652's own real, proven 4-cell bounded-
# loop-ring tiles at the SAME fixed relative layout #652 already proved:
#   LOOPVAR(0,0) --south--> LOOP_CTRL(1,0) --east--> ADDER(1,1)
#      ^                                                  |
#      |                                                north
#     west                                                |
#      +------------------- RAM_RELAY(0,1) <---------------+
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class LlvmLoopLoweringInfo:
    """Real, honest bookkeeping for the loop shape -- everything a
    caller needs to actually DRIVE the real, per-round protocol
    #636/#649/#652 already established (this fabric has no real command
    core wired in yet to do this from within itself, #644's own real,
    separate, later work) and verify the result, not just trust it
    compiled."""
    function_name: str
    loopvar_pos: Tuple[int, int]
    loop_ctrl_pos: Tuple[int, int]
    adder_pos: Tuple[int, int]   # #661: also the subtractor's own position for a descending loop -- one shared name, the role at this position, not always literally an adder tile
    ram_relay_pos: Tuple[int, int]
    entry_seed_value: int
    bound_value: int
    increment_value: int
    #: the real, final value the loop variable settles on once the real
    #: VM run reaches the real exit condition -- computed here by
    #: literally interpreting the SAME real semantics the hardware
    #: itself uses (increment first, THEN decide continue/exit on the
    #: new value), not assumed equal to a naive Python `for` loop.
    expected_final_value: int
    #: how many real CONTINUE rounds the caller should expect before
    #: the real exit fires (matches #652's own `do_round()` loop count).
    expected_continue_rounds: int


def _block_terminator(block):
    return list(block.instructions)[-1]


def _unconditional_br_target(instr) -> Optional[str]:
    ops = list(instr.operands)
    if instr.opcode != "br" or len(ops) != 1:
        return None
    return ops[0].name


def _conditional_br_targets(instr) -> Optional[Tuple[str, str, str]]:
    """Returns (cond_name, false_dest_name, true_dest_name) -- REAL,
    CONFIRMED llvmlite operand order for a conditional `br`, checked
    directly against the real parser before writing this (a well-known
    real LLVM quirk: source syntax lists iftrue then iffalse, but the
    real operand storage order is [cond, iffalse, iftrue]), not assumed
    from the source syntax order."""
    ops = list(instr.operands)
    if instr.opcode != "br" or len(ops) != 3:
        return None
    return ops[0].name, ops[1].name, ops[2].name


def _compile_single_counting_loop(fn, argument_values: Dict[str, int]
                                    ) -> Tuple[Optional[Any], List[CompileDiagnostic], Optional[LlvmLoopLoweringInfo]]:
    diagnostics: List[CompileDiagnostic] = []
    blocks = {b.name: b for b in fn.blocks}
    entry = list(fn.blocks)[0]   # real, guaranteed LLVM invariant: the first block is always the entry

    def fail(problem, what, why, suggestion=None):
        diagnostics.append(_diag(problem=problem, what=what, why=why, suggestion=suggestion))
        return None, diagnostics, None

    entry_instrs = list(entry.instructions)
    if len(entry_instrs) != 1:
        return fail(
            f"entry block {entry.name!r} has {len(entry_instrs)} instructions, expected exactly 1",
            "checking the loop shape's own real entry block",
            "this real, narrow counting-loop shape (#652) requires entry to hold nothing but "
                "an unconditional branch into the loop -- any real setup work belongs in the "
                "phi's own entry-seed value, not as separate entry-block instructions",
        )
    loop_name = _unconditional_br_target(entry_instrs[0])
    if loop_name is None or loop_name not in blocks:
        return fail(
            f"entry block {entry.name!r} doesn't end with a real, unconditional branch "
                f"to another real block in this function",
            "checking the loop shape's own real entry block",
            "this real, narrow counting-loop shape (#652) requires entry's own terminator "
                "to be exactly `br label %loop_block_name`",
        )
    loop_block = blocks[loop_name]
    other_names = [n for n in blocks if n not in (entry.name, loop_name)]
    if len(other_names) != 1:
        return fail(
            f"function {fn.name!r} has {len(other_names) + 2} basic blocks after identifying "
                f"entry and loop, expected exactly 1 remaining (the real exit block)",
            "checking the loop shape's own real block count",
            "this real, narrow counting-loop shape (#652) is exactly 3 real blocks: entry, "
                "loop, exit -- no more, no fewer",
        )
    exit_block = blocks[other_names[0]]

    loop_instrs = list(loop_block.instructions)
    if len(loop_instrs) != 4:
        return fail(
            f"loop block {loop_block.name!r} has {len(loop_instrs)} instructions, expected exactly 4 "
                f"(phi, increment, icmp, conditional br)",
            "checking the loop block's own real instruction shape",
            "this real, narrow counting-loop shape (#652) supports exactly one phi, one add "
                "increment, one icmp, and one conditional branch -- nothing else inside the loop "
                "body yet, real, explicitly deferred future work",
        )
    phi_instr, inc_instr, icmp_instr, br_instr = loop_instrs

    if phi_instr.opcode != "phi":
        return fail(f"loop block {loop_block.name!r}'s own first instruction is "
                     f"{phi_instr.opcode!r}, not a real phi",
                     "checking the loop block's own real instruction order",
                     "this real, narrow shape requires the loop-carried variable's own phi "
                         "to be the loop block's first real instruction")
    phi_ops = list(phi_instr.operands)
    if len(phi_ops) != 2:
        return fail(f"loop variable {phi_instr.name!r}'s own phi has {len(phi_ops)} incoming "
                     f"values, expected exactly 2",
                     "checking the loop variable's own real phi",
                     "this real, narrow shape supports exactly one loop-carried variable with "
                         "exactly two real incoming edges (entry's seed value, the loop's own "
                         "self-referencing increment) -- more incoming edges mean a real, more "
                         "general control-flow shape, explicitly deferred")
    entry_seed_value, entry_seed_is_ref = _resolve_operand_value(phi_ops[0], {})
    if entry_seed_is_ref or entry_seed_value is None:
        return fail(f"loop variable {phi_instr.name!r}'s own entry-seed operand "
                     f"{phi_ops[0].name or str(phi_ops[0])!r} is not a real, literal compile-time constant",
                     "checking the loop variable's own real entry-seed value",
                     "this real, narrow shape requires the phi's own entry-block incoming value "
                         "to be a literal constant -- LOOPVAR's own real entry-seed (#636) has no "
                         "other real source wired in yet")

    if inc_instr.opcode not in ("add", "sub"):
        return fail(f"loop block {loop_block.name!r}'s own second instruction is "
                     f"{inc_instr.opcode!r}, not a real add or sub",
                     "checking the loop's own real increment instruction",
                     "this real, narrow shape supports a counting-UP loop via a real `add` "
                         "(paired with `icmp slt`) or a counting-DOWN loop via a real `sub` "
                         "(paired with `icmp sgt`) -- no other increment shape is wired up yet")
    is_descending = (inc_instr.opcode == "sub")
    inc_ops = list(inc_instr.operands)
    if not (inc_ops[0].name == phi_instr.name):
        return fail(f"the loop's own real increment {inc_instr.name!r} doesn't "
                     f"{'subtract from' if is_descending else 'add to'} "
                     f"{phi_instr.name!r} (the loop variable's own phi) as its first operand",
                     "checking the loop's own real increment instruction",
                     "this real, narrow shape requires the increment to be exactly "
                         f"`{inc_instr.name} = {inc_instr.opcode} {phi_instr.name}, <compile-time constant>`")
    increment_value, increment_is_ref = _resolve_operand_value(inc_ops[1], argument_values)
    if increment_value is None:
        return fail(f"the loop's own real increment's second operand "
                     f"{inc_ops[1].name or str(inc_ops[1])!r} is not a real compile-time value",
                     "checking the loop's own real increment instruction",
                     "the increment amount must be a real argument or literal constant")

    if icmp_instr.opcode != "icmp":
        return fail(f"loop block {loop_block.name!r}'s own third instruction is "
                     f"{icmp_instr.opcode!r}, not a real icmp",
                     "checking the loop's own real exit condition",
                     "this real, narrow shape requires the third instruction to be the real "
                         "icmp deciding whether the loop continues")
    predicate = _icmp_predicate(icmp_instr)
    expected_predicate = "sgt" if is_descending else "slt"
    if predicate != expected_predicate:
        return fail(f"loop exit condition uses predicate {predicate!r}, expected "
                     f"{expected_predicate!r} to match the real `{inc_instr.opcode}` increment "
                     f"already used",
                     "checking the loop's own real exit condition",
                     f"this real, narrow shape requires `add` paired with `icmp slt` (counting "
                         f"up, \"continue while less than the bound\") or `sub` paired with "
                         f"`icmp sgt` (counting down, \"continue while greater than the bound\") "
                         f"-- LOOP_CTRL's own real comparator (#637/#650/#661) can express other "
                         f"real shapes, but only these two are wired up in the frontend yet")
    icmp_ops = list(icmp_instr.operands)
    if icmp_ops[0].name != phi_instr.name:
        return fail(f"the loop's own real icmp compares {icmp_ops[0].name or str(icmp_ops[0])!r}, "
                     f"not the loop variable's own real, held (pre-increment) value {phi_instr.name!r}",
                     "checking the loop's own real exit condition",
                     f"this real, narrow shape (matching #638/#649/#652's own proven real hardware "
                         f"topology -- LOOP_CTRL tests the value LOOPVAR currently holds BEFORE "
                         f"deciding whether the increment even runs this round) requires exactly "
                         f"`icmp {predicate} {phi_instr.name}, <bound>` -- note this is the phi's OWN "
                         f"value, not the incremented one; `{inc_instr.name}` (the increment) "
                         f"still computes unconditionally in the same block either way, it's just "
                         f"unused on the exit path, same as any ordinary LLVM basic block")
    bound_value, bound_is_ref = _resolve_operand_value(icmp_ops[1], argument_values)
    if bound_value is None:
        return fail(f"the loop's own real bound {icmp_ops[1].name or str(icmp_ops[1])!r} is not "
                     f"a real, compile-time-resolved argument or constant",
                     "checking the loop's own real exit condition",
                     "the loop bound must be a real function argument (given a compile-time "
                         "value via argument_values) or a literal constant")

    if br_instr.opcode != "br":
        return fail(f"loop block {loop_block.name!r}'s own real terminator is "
                     f"{br_instr.opcode!r}, not a real conditional br",
                     "checking the loop's own real terminator",
                     "this real, narrow shape requires the loop block's own real terminator to "
                         "be the conditional branch deciding continue vs exit")
    targets = _conditional_br_targets(br_instr)
    if targets is None:
        return fail(f"loop block {loop_block.name!r}'s own real terminator isn't a real "
                     f"conditional `br i1 ..., label ..., label ...`",
                     "checking the loop's own real terminator",
                     "this real, narrow shape requires exactly a conditional branch here")
    cond_name, false_dest, true_dest = targets
    if cond_name != icmp_instr.name:
        return fail(f"the loop's own real terminator branches on {cond_name!r}, not the "
                     f"loop's own real icmp result {icmp_instr.name!r}",
                     "checking the loop's own real terminator",
                     "the conditional branch must test the loop's own real icmp result directly")
    if true_dest != loop_block.name or false_dest != exit_block.name:
        return fail(f"the loop's own real terminator branches TRUE->{true_dest!r}/"
                     f"FALSE->{false_dest!r}, expected TRUE->{loop_block.name!r} (continue) / "
                     f"FALSE->{exit_block.name!r} (exit)",
                     "checking the loop's own real terminator",
                     "this real, narrow shape (matching `icmp slt`'s own real meaning, \"continue "
                         "while less than the bound\") requires the TRUE destination to re-enter "
                         "the loop and the FALSE destination to leave it")

    exit_instrs = list(exit_block.instructions)
    if len(exit_instrs) != 1 or exit_instrs[0].opcode != "ret":
        return fail(f"exit block {exit_block.name!r} doesn't hold exactly one real `ret`",
                     "checking the loop shape's own real exit block",
                     "this real, narrow shape requires exit to hold nothing but the real "
                         "`ret` of the loop's own final value")
    ret_operand_name = _operand_name(list(exit_instrs[0].operands)[0])
    if ret_operand_name != phi_instr.name:
        return fail(f"exit block {exit_block.name!r} returns {ret_operand_name!r}, not the "
                     f"loop variable's own real, held (pre-increment) value {phi_instr.name!r}",
                     "checking the loop shape's own real exit block",
                     f"matching #638/#649/#652's own proven real hardware -- the value LOOP_CTRL "
                         f"routes out on exit is whatever LOOPVAR currently holds, not a value "
                         f"ADDER computed this round (that round's own real increment is never "
                         f"even offered to ADDER when the exit path is taken) -- this real, narrow "
                         f"shape requires exactly `ret i32 {phi_instr.name}`")

    # ── Real, honest interpretation, matching the REAL hardware's own
    # semantics exactly (#636/#649/#652): increment first, THEN decide
    # continue/exit on the NEW value -- not a naive Python `for` loop's
    # own pre-test semantics. ──
    # ── Real, honest interpretation, matching the REAL, proven
    # hardware's own semantics exactly (#638/#649/#652): LOOP_CTRL
    # tests the CURRENT (pre-increment) value BEFORE deciding whether
    # the increment even runs this round -- NOT a post-increment test.
    # #661: real, symmetric descending case added alongside the
    # existing ascending one. ──
    i = entry_seed_value
    rounds = 0
    while True:
        rounds += 1
        if rounds > 1_000_000:   # real, honest safety valve -- never trust an unbounded loop blindly
            return fail("the loop's own real compile-time interpretation didn't terminate "
                        "within 1,000,000 rounds",
                        "computing the loop's own real expected final value",
                        "either the bound/increment don't actually converge, or this frontend's "
                        "own interpreter has a real bug -- refusing to hang either way")
        continuing = (i > bound_value) if is_descending else (i < bound_value)
        if continuing:
            i = ((i - increment_value) if is_descending else (i + increment_value)) & 0xFFFFFFFF
            continue
        expected_final_value = i
        break

    # ── Real, proven 4-cell layout, #638/#649/#652's own real, fixed
    # relative positions -- LOOPVAR(0,0)/LOOP_CTRL(1,0)/ADDER-or-
    # SUBTRACTOR(1,1)/RAM_RELAY(0,1). #661: the descending case swaps
    # in nano_loop_ctrl_desc (continue_out->pattern_low, the real,
    # necessary mirror of the ascending tile's own mapping) and
    # subtractor (the same real adder core, subtract_mode fixed on) --
    # everything else about the topology is identical. ──
    if is_descending:
        loop_ctrl_fields = [FieldIR("continue_out", "e"), FieldIR("exit_out", "s"),
                             FieldIR("pattern_high", ["s"])]
        loop_ctrl_tile, op_tile = "nano_loop_ctrl_desc", "subtractor"
    else:
        loop_ctrl_fields = [FieldIR("continue_out", "e"), FieldIR("exit_out", "s"),
                             FieldIR("pattern_low", ["s"])]
        loop_ctrl_tile, op_tile = "nano_loop_ctrl", "adder"
    statements: List[PlaceIR] = [
        PlaceIR(name="loopvar", tile_name="nano_loop_var", row=0, col=0,
                fields=[FieldIR("out", "s")]),
        PlaceIR(name="loop_ctrl", tile_name=loop_ctrl_tile, row=1, col=0, fields=loop_ctrl_fields),
        PlaceIR(name="op", tile_name=op_tile, row=1, col=1,
                fields=[FieldIR("in_a", "w"), FieldIR("in_b", "s"), FieldIR("out", "n")]),
        PlaceIR(name="ram_relay", tile_name="ram_flowing", row=0, col=1,
                fields=[FieldIR("in", "s"), FieldIR("out", "w")]),
    ]

    program_ir = ProgramIR(name=fn.name, statements=statements)
    icm, backend_diags = compile_program_ir(program_ir, program_name_hint=fn.name)
    diagnostics.extend(backend_diags)
    if icm is None:
        return None, diagnostics, None

    info = LlvmLoopLoweringInfo(
        function_name=fn.name,
        loopvar_pos=(0, 0), loop_ctrl_pos=(1, 0), adder_pos=(1, 1), ram_relay_pos=(0, 1),
        entry_seed_value=entry_seed_value, bound_value=bound_value, increment_value=increment_value,
        expected_final_value=expected_final_value, expected_continue_rounds=rounds - 1,
    )
    return icm, diagnostics, info
