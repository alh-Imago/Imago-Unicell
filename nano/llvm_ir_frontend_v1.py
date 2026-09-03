"""llvm_ir_frontend_v1.py — points.md #611: the real, first LLVM IR
frontend for Unicell-S, per `#547`/`#603`/`#610`'s own real scope. Uses
`llvmlite` (confirmed installable and working in this environment,
per `#610`'s own real tooling check) to parse REAL LLVM IR text -- not
a made-up LLVM-like pseudo-language, matching `c_frontend_v1.py`'s own
"real syntax, real parser" precedent.

REAL, DELIBERATELY RESTRICTED FIRST SLICE, matching `#610`'s own
"smallest test first" recommendation exactly -- not general LLVM IR:
- Exactly one function, one basic block. No control flow (`br`, `phi`,
  loops) at all yet -- real, explicitly deferred future work, `#610`'s
  own "genuinely novel, unsolved" territory.
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
_ICMP_LOWERING = {
    "sge": ("adder", True, 0),
    "sgt": ("adder", True, 1),
    "slt": ("subtractor", False, 1),
    "sle": ("subtractor", False, 0),
}


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
    if len(blocks) != 1:
        diagnostics.append(_diag(
            problem=f"function {fn.name!r} has {len(blocks)} basic blocks, expected exactly 1",
            what=f"checking {fn.name!r}'s own real control-flow shape",
            why="this real, first frontend slice has no control-flow support at all yet (#611/#610) -- "
                "branches, loops, and multi-block functions are real, explicitly deferred future work",
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
            if predicate not in _ICMP_LOWERING:
                diagnostics.append(_diag(
                    problem=f"icmp predicate {predicate!r} not supported ({str(instr).strip()})",
                    what=f"lowering instruction {i + 1} ({str(instr).strip()})",
                    why=f"this real, first frontend slice only understands {sorted(_ICMP_LOWERING)} "
                        "(#613) -- eq/ne need a real AND of two comparisons, not yet built",
                ))
                return None, diagnostics, None
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
        result_cell=(1, col_cursor - 1),
        expected_result=known_values[prev_instr_name],
        chain_length=len(body_instructions),
        injections=injections,
    )
    return icm, diagnostics, info
