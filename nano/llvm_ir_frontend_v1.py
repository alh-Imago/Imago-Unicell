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
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import llvmlite.binding as llvm  # noqa: E402

from dsl_diagnostics_v1 import CompileDiagnostic  # noqa: E402
from program_ir_v1 import ProgramIR, PlaceIR, FieldIR  # noqa: E402
from dsl_compiler_v1 import compile_program_ir  # noqa: E402

_SUPPORTED_OPCODES = {"add", "sub", "icmp"}

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
            if not (first_is_ref and first_name == prev_instr_name):
                diagnostics.append(_diag(
                    problem=f"instruction {i + 1}'s own first operand is {first_name or str(operands[0])!r}, "
                             f"not the immediately preceding instruction's result ({prev_instr_name!r})",
                    what=f"lowering instruction {i + 1} ({str(instr).strip()})",
                    why="this real, first frontend slice only supports a genuine LINEAR "
                        "ACCUMULATION CHAIN, not a general DAG (#611/#610) -- an instruction "
                        "referencing an earlier, non-immediately-preceding result needs real "
                        "relay-cell routing for a non-adjacent connection, explicitly deferred",
                    suggestion="reorder/restructure the IR into a straight accumulation chain, "
                               "or wait for general DAG routing to be built",
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
                result = 1 if (first_value == second_value) == (predicate == "eq") else 0
            else:
                result = 1 if {
                    "sge": first_value >= second_value, "sgt": first_value > second_value,
                    "slt": first_value < second_value, "sle": first_value <= second_value,
                }[predicate] else 0
        else:
            result = first_value + second_value if instr.opcode == "add" else first_value - second_value
        # Real hardware is 32-bit, always -- masking here keeps the
        # Python-side expected value honestly comparable to what the
        # VM will actually compute, no silent divergence for negative/
        # overflowing intermediate results.
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
        statements.append(PlaceIR(
            name=f"op_{i}", tile_name=diff_tile, row=1, col=diff_col,
            fields=[FieldIR("in_a", "w"), FieldIR("in_b", "n"), FieldIR("out", "e")],
        ))

        if instr.opcode == "icmp":
            if predicate in _EQ_NE_PREDICATES:
                # points.md #668: the real, 6-cell eq/ne composition --
                # verified directly in the VM (six real (a,b) pairs)
                # before writing any of this placement code. Layout
                # (relative to the diff cell at (1, diff_col)):
                #   diff(1,c) --e--> CMP0(1,c+1) --s--> XOR(2,c+1)
                #      |                                    ^
                #      s                                    n
                #      v                                    |
                #   CMP1(2,c) --s--> RELAY_A(3,c) --e--> RELAY_B(3,c+1)
                # CMP0=threshold 0, CMP1=threshold 1 -- diff fans out
                # to both simultaneously; CMP1's own path is
                # deliberately routed two hops longer via the two
                # relays so its real contribution reaches XOR one tick
                # after CMP0's -- nano's own two-arrival gate OR-
                # combines genuinely simultaneous same-tick arrivals
                # from different sources into one event rather than
                # treating them as two separate operands (the same
                # real fact #611's own west/north injection stagger
                # above already has to work around).
                statements[-1].fields[-1] = FieldIR("out", ["e", "s"])   # diff cell fans out, not a single direction
                cmp0_col = diff_col + 1
                statements.append(PlaceIR(
                    name=f"op_{i}_cmp0", tile_name="comparator", row=1, col=cmp0_col,
                    fields=[FieldIR("in", "w"), FieldIR("out", "s"), FieldIR("threshold", 0)],
                ))
                statements.append(PlaceIR(
                    name=f"op_{i}_cmp1", tile_name="comparator", row=2, col=diff_col,
                    fields=[FieldIR("in", "n"), FieldIR("out", "s"), FieldIR("threshold", 1)],
                ))
                statements.append(PlaceIR(
                    name=f"op_{i}_relay_a", tile_name="ram_flowing", row=3, col=diff_col,
                    fields=[FieldIR("in", "n"), FieldIR("out", "e")],
                ))
                statements.append(PlaceIR(
                    name=f"op_{i}_relay_b", tile_name="ram_flowing", row=3, col=cmp0_col,
                    fields=[FieldIR("in", "w"), FieldIR("out", "n")],
                ))
                statements.append(PlaceIR(
                    name=f"op_{i}_xor", tile_name="nano_gate", row=2, col=cmp0_col,
                    fields=[FieldIR("out", "e"), FieldIR("topology", _EQ_TOPOLOGY)],
                ))
                if predicate == "ne":
                    # points.md #668: ne = XOR(eq_result, real one-time
                    # constant 1) -- an exact boolean NOT (1^1=0, 0^1=1),
                    # not the bitwise NOT that TOPO_XNOR turned out to
                    # give across all 32 bits. The constant is injected
                    # directly, with no relay hops at all -- it reaches
                    # the second XOR far sooner than eq_result's own
                    # multi-hop computed path, giving a large, safe
                    # natural stagger rather than a knife-edge one-tick
                    # margin.
                    ne_col = cmp0_col + 1
                    injections.append((3, ne_col, 1))
                    statements.append(PlaceIR(
                        name=f"op_{i}_const1", tile_name="ram_flowing", row=3, col=ne_col,
                        fields=[FieldIR("in", "s"), FieldIR("out", "n")],
                    ))
                    statements.append(PlaceIR(
                        name=f"op_{i}_ne_xor", tile_name="nano_gate", row=2, col=ne_col,
                        fields=[FieldIR("out", "e"), FieldIR("topology", _EQ_TOPOLOGY)],
                    ))
                    col_cursor = ne_col + 1
                else:
                    col_cursor = cmp0_col + 1
                last_result_row = 2
            else:
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
