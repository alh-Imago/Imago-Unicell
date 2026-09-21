"""
llvm_dag_frontend_v1.py — points.md #795: the first real frontend for
`compile_dag()` (`vix_dag_dispatcher_v1.py`, `#780`). Built to
`compile_dag_frontend_scope.md`'s own item 8 ("the proof case"): real
LLVM IR text -> symbol resolution -> real `DagInstr` -> the UNCHANGED
`compile_dag()` -> the VM -> checked against the correct numeric answer.

WHERE THIS ATTACHES, AND WHY IT DIFFERS FROM THE SCOPE NOTE'S ITEM 1
(checked against the real code, not assumed -- see the addendum in
`compile_dag_frontend_scope.md`): the scope note proposed bridging
`ProgramIR -> DagInstr`. `ProgramIR` turns out to be the OLD frontend's
own POST-PLACEMENT output -- every `PlaceIR` already carries a row/col,
names are synthetic (`op_0`, `value_north_0`), `sub x, 3` has already
been rewritten into `add x, 0xFFFFFFFD`, and dependencies exist only
implicitly as column adjacency. Recovering dataflow from that would
mean reverse-engineering it out of geometry. The real dataflow -- real
`%names`, real opcodes, real operand order -- lives one level up, in
llvmlite's own parse of the function. This module therefore reuses the
existing PARSER (llvmlite, the same parse+verify step the old frontend
uses), which is the scope note's own stated intent for item 1
("reuses the existing, proven parser rather than teaching it a second
output format"), while skipping the post-placement IR that cannot carry
what `DagInstr` needs. The old frontend is untouched.

STRUCTURE (deliberately layered so a second source language -- the DSL,
C, Python -- needs only its own thin extractor, per scope item 2):
  1. `extract_llvm_function()`   -- the ONLY LLVM-specific part.
  2. `resolve_symbols()`         -- SOURCE-AGNOSTIC, three real passes:
       (1) find every referenced name, (2) confirm each is declared
       before use, (3) classify: function argument -> DETERMINED
       (`DagOperand(kind="dynamic")`), earlier result -> `ref`, literal
       -> `const`. Collects EVERY problem, doesn't stop at the first.
  3. `_check_capabilities()`     -- rejects shapes the backend cannot
       yet compile correctly, with a precise diagnostic, rather than
       handing them to `compile_dag()` to be silently miscompiled.
  4. `compile_llvm_via_dag()`    -- glue; `run_in_vm()` -- the harness.

REAL, DELIBERATE CHOICES (all per the scope note):
  * Every function argument is DETERMINED (`dynamic`), never a compile-
    time constant -- so the same compiled result runs correctly for any
    input (unlike the old frontend, which bakes arguments into its own
    injections). Named consequence: `STAGGER` is rarely selected.
  * The original `%name` is used directly as `DagInstr.name` (scope
    item 7 -- traceable for a person other than the author).
  * `sub %v, C` is lowered to `add %v, -C` (recorded in `rewrites`).
    Found necessary by this very frontend: the backend's plain-chain
    path gives a non-commutative op NO operand-order guarantee (see
    `_lower_for_backend`). #796: the backend now GUARANTEES operand
    order for order-sensitive ops (`ingestion_path()` routes them through
    the sequenced convergence path), so `sub C, %v` compiles too; the
    rewrite stays because it is strictly cheaper than a sequencer.
  * The scan pass (`scan_ordering`) records, per instruction, whether
    operand order is essential and what guarantees it.

REAL, HONEST SCOPE OF THIS FIRST SLICE: a single function, a single
basic block (no control flow, no loops), `i32` only, binary opcodes
that already have a real library entry (`add`/`sub`/`mul`/`and`/`or`/
`xor`), every SSA value NAMED. Not attempted: opcode escalation (scope
item 4 -- an opcode without a library entry is a clear diagnostic, not
an escalation), I/O beyond direct injection, loops, `icmp`/`select`/
shifts, unnamed temporaries (`%0`).
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import llvmlite.binding as llvm  # noqa: E402

from dsl_diagnostics_v1 import CompileDiagnostic  # noqa: E402
from vix_dag_dispatcher_v1 import compile_dag, ingestion_path, DagInstr, DagOperand  # noqa: E402
from vix_opcode_library_v1 import lookup as library_lookup  # noqa: E402

_MASK32 = 0xFFFFFFFF
_SUPPORTED_TYPE = "i32"
_LITERAL_RE = re.compile(r"^(?:i\d+\s+)?(-?\d+)$")


# ---------------------------------------------------------------------------
# Source-agnostic intermediate: what any frontend's extractor produces.
# ---------------------------------------------------------------------------

@dataclass
class SourceOperand:
    """`kind` is "name" (a reference to an argument or an earlier
    result) or "literal" (a compile-time integer)."""
    kind: str
    name: Optional[str] = None
    value: Optional[int] = None


@dataclass
class SourceInstr:
    name: str
    opcode: str
    operands: List[SourceOperand] = field(default_factory=list)
    type_name: str = _SUPPORTED_TYPE


@dataclass
class SourceFunction:
    function_name: str
    arguments: List[str]
    instrs: List[SourceInstr]
    result_name: str


@dataclass
class ResolvedProgram:
    dag: List[DagInstr]
    #: argument name -> every (instruction name, operand index) that reads it.
    #: One argument can feed many instructions; each use is its own real
    #: injection site in the compiled fabric (`compile_dag()`'s dynamic
    #: operands are per-use, not shared).
    arg_uses: Dict[str, List[Tuple[str, int]]]


@dataclass
class OrderNote:
    """One entry of the scan pass's ordering report (points.md #796).
    Operand order is only essential for SOME instructions; the scan
    records which, why, and what guarantees it -- so ingestion is chosen
    from a recorded fact, not rediscovered downstream."""
    name: str
    opcode: str            # as written in the source
    order_sensitive: bool  # non-commutative two-operand op
    ingestion: str         # "plain_chain" | "convergence" -- the dispatcher's own decision
    guarantee: str         # "not needed" | "lowered to commutative" | "sequencer"
    reason: str


@dataclass
class DagFrontendResult:
    function_name: str
    dag: List[DagInstr]
    icm: object
    records: List[object]
    positions: Dict[str, Tuple[int, int]]
    seq_orders: Dict[str, Tuple[int, int]]
    #: argument name -> every real (row, col) that must receive its value.
    arg_injections: Dict[str, List[Tuple[int, int]]]
    result_name: str
    result_cell: Tuple[int, int]
    result_core: str
    #: human-readable record of every instruction the frontend lowered to a
    #: different (equivalent) form before handing it to the backend --
    #: traceability (scope item 7), so `%b = sub %a, 3` becoming an `add`
    #: is never a silent surprise to a reader.
    rewrites: List[str] = field(default_factory=list)
    #: the scan pass's per-instruction ordering report (points.md #796).
    ordering: List[OrderNote] = field(default_factory=list)


def _diag(stage: str, what: str, problem: str, why: str,
          suggestion: Optional[str] = None) -> CompileDiagnostic:
    return CompileDiagnostic(severity="error", stage=stage, what=what, problem=problem,
                             why=why, suggestion=suggestion)


# ---------------------------------------------------------------------------
# 1. The LLVM-specific extractor.
# ---------------------------------------------------------------------------

def _source_operand(op) -> Tuple[Optional[SourceOperand], Optional[str]]:
    """Returns (operand, problem). llvmlite reports `name == ''` BOTH for
    a literal AND for a reference to an unnamed temporary (`%0`) -- and
    in the latter case `str(op)` is the whole defining instruction, whose
    last token can look like a number. So a literal is recognised ONLY by
    matching the whole text against `i32 <int>`, never by taking a last
    token (the trap a naive last-token parse falls into)."""
    if op.name:
        return SourceOperand(kind="name", name=op.name), None
    text = str(op).strip()
    m = _LITERAL_RE.match(text)
    if m:
        return SourceOperand(kind="literal", value=int(m.group(1)) & _MASK32), None
    if "%" in text:
        return None, ("an operand references an unnamed SSA value "
                      f"({text.split('=')[0].strip()!r}) -- llvmlite gives such values no name to resolve by")
    return None, f"an operand {text!r} is not a plain integer literal or a named value"


def extract_llvm_function(source: str) -> Tuple[Optional[SourceFunction], List[CompileDiagnostic]]:
    diags: List[CompileDiagnostic] = []
    what = "reading the supplied LLVM IR"
    try:
        mod = llvm.parse_assembly(source)
        mod.verify()
    except RuntimeError as e:
        return None, [_diag("llvm-frontend", what, str(e),
                            "the real LLVM parser (llvmlite) rejected this as invalid IR -- nothing "
                            "downstream can proceed from IR that is not real, valid LLVM IR")]

    functions = list(mod.functions)
    if len(functions) != 1:
        return None, [_diag("llvm-frontend", what, f"expected exactly one function, found {len(functions)}",
                            "this frontend slice compiles one function at a time",
                            "split into separate compile calls, one function each")]
    fn = functions[0]

    blocks = list(fn.blocks)
    if len(blocks) != 1:
        return None, [_diag("llvm-frontend", what,
                            f"function has {len(blocks)} basic blocks -- control flow is not supported here",
                            "a DAG of dataflow needs exactly one straight-line block; branching and loops "
                            "are separate, later work (scope note item 5)")]

    arguments: List[str] = []
    for a in fn.arguments:
        if not a.name:
            diags.append(_diag("llvm-frontend", what, "an unnamed function argument",
                               "arguments are bound to injection sites by name",
                               "give every argument a name (e.g. `%x`)"))
        elif str(a.type) != _SUPPORTED_TYPE:
            diags.append(_diag("llvm-frontend", what, f"argument %{a.name} has type {a.type}, not i32",
                               "the fabric's cells are 32-bit; a wider or narrower type would be "
                               "silently truncated or mis-sized"))
        else:
            arguments.append(a.name)

    instrs: List[SourceInstr] = []
    result_name: Optional[str] = None
    for ins in blocks[0].instructions:
        ops = list(ins.operands)
        if ins.opcode == "ret":
            if len(ops) != 1 or not ops[0].name:
                diags.append(_diag("llvm-frontend", what,
                                   "`ret` must return exactly one named value",
                                   "the frontend needs to know which computed cell holds the result",
                                   "return a named SSA value, e.g. `ret i32 %b`"))
            else:
                result_name = ops[0].name
            continue
        if not ins.name:
            diags.append(_diag("llvm-frontend", what,
                               f"an unnamed SSA value produced by `{ins.opcode}`",
                               "llvmlite gives unnamed temporaries (`%0`) no name later operands can "
                               "resolve against, so a dependency on one cannot be traced",
                               "name every value (e.g. `%a = add i32 %x, 5`)"))
            continue
        src_ops: List[SourceOperand] = []
        for op in ops:
            so, problem = _source_operand(op)
            if problem:
                diags.append(_diag("llvm-frontend", f"reading operands of %{ins.name}", problem,
                                   "every operand must be traceable to an argument, an earlier "
                                   "result, or a literal"))
            else:
                src_ops.append(so)
        instrs.append(SourceInstr(name=ins.name, opcode=ins.opcode, operands=src_ops,
                                  type_name=str(ins.type)))

    if any(d.severity == "error" for d in diags):
        return None, diags
    if result_name is None:
        return None, [_diag("llvm-frontend", what, "no `ret` found", "nothing marks the result cell")]
    return SourceFunction(function_name=fn.name, arguments=arguments, instrs=instrs,
                          result_name=result_name), []


# ---------------------------------------------------------------------------
# 2. Source-agnostic symbol resolution -- three real passes.
# ---------------------------------------------------------------------------

def resolve_symbols(arguments: List[str], instrs: List[SourceInstr]
                    ) -> Tuple[Optional[ResolvedProgram], List[CompileDiagnostic]]:
    """Pass 1: every referenced name. Pass 2: is it declared, and BEFORE
    use? Pass 3: classify (argument -> dynamic, earlier result -> ref,
    literal -> const). Every problem is collected; resolution never
    stops at the first. Written source-agnostically on purpose -- LLVM's
    own verifier already guarantees SSA (so redefinition can't reach here
    from LLVM), but a DSL or other source carries no such guarantee."""
    diags: List[CompileDiagnostic] = []
    what = "resolving names"

    # Declarations, in order. An argument name may not be redefined.
    defined_at: Dict[str, int] = {}
    arg_set: Set[str] = set(arguments)
    for i, ins in enumerate(instrs):
        if ins.name in arg_set:
            diags.append(_diag("resolve", what, f"`{ins.name}` is defined by an instruction but is also a function argument",
                               "one name would mean two different values"))
        elif ins.name in defined_at:
            diags.append(_diag("resolve", what, f"`{ins.name}` is defined more than once",
                               "a reference to it would be ambiguous",
                               "give each value a distinct name"))
        else:
            defined_at[ins.name] = i

    # Pass 1 + 2 + 3, per operand.
    dag: List[DagInstr] = []
    arg_uses: Dict[str, List[Tuple[str, int]]] = {a: [] for a in arguments}
    for i, ins in enumerate(instrs):
        dag_ops: List[DagOperand] = []
        for k, op in enumerate(ins.operands):
            if op.kind == "literal":
                dag_ops.append(DagOperand(kind="const", value=op.value))
            elif op.name in arg_set:
                dag_ops.append(DagOperand(kind="dynamic"))
                arg_uses[op.name].append((ins.name, k))
            elif op.name in defined_at:
                if defined_at[op.name] >= i:
                    diags.append(_diag("resolve", f"resolving operand {k} of `{ins.name}`",
                                       f"`{op.name}` is used before it is defined",
                                       "a value cannot feed an instruction that runs before it exists"))
                dag_ops.append(DagOperand(kind="ref", ref_name=op.name))
            else:
                diags.append(_diag("resolve", f"resolving operand {k} of `{ins.name}`",
                                   f"`{op.name}` is not declared",
                                   "it is neither a function argument nor the result of any instruction",
                                   "declare it, or check the spelling"))
                dag_ops.append(DagOperand(kind="ref", ref_name=op.name))
        dag.append(DagInstr(name=ins.name, opcode=ins.opcode, operands=dag_ops))

    if diags:
        return None, diags
    return ResolvedProgram(dag=dag, arg_uses=arg_uses), []


# ---------------------------------------------------------------------------
# 3a. Equivalence-preserving lowering, chosen by what the backend gets right.
# ---------------------------------------------------------------------------

def _lower_for_backend(dag: List[DagInstr]) -> Tuple[List[DagInstr], List[str]]:
    """`sub %v, C` -> `add %v, (-C mod 2^32)`. Found necessary by the
    first real frontend (#795): `compile_dag()`'s plain-chain path gives
    a non-commutative op's real and constant operands NO ordering
    guarantee -- whichever arrives first becomes the minuend (`#770`'s
    hazard), so `sub %a, 3` computed 3-a. Addition is commutative, so
    this rewrite is correct by construction rather than by arrival luck.
    It is also exactly what the old frontend does and what LLVM itself
    canonicalizes `sub x, C` to. Every rewrite is recorded, not hidden."""
    out: List[DagInstr] = []
    notes: List[str] = []
    for ins in dag:
        kinds = [o.kind for o in ins.operands]
        if ins.opcode == "sub" and len(ins.operands) == 2 and kinds[0] != "const" and kinds[1] == "const":
            neg = (-ins.operands[1].value) & _MASK32
            out.append(DagInstr(name=ins.name, opcode="add",
                                operands=[ins.operands[0], DagOperand(kind="const", value=neg)]))
            notes.append(f"%{ins.name}: sub <value>, {ins.operands[1].value}  ->  add <value>, {neg:#x}")
        else:
            out.append(ins)
    return out, notes


# ---------------------------------------------------------------------------
# 3b. The scan pass's ordering report.
# ---------------------------------------------------------------------------

def scan_ordering(source_dag: List[DagInstr], lowered_dag: List[DagInstr]) -> List[OrderNote]:
    """Record, per instruction, whether operand ORDER is essential and what
    guarantees it. Order matters only for a non-commutative two-operand op
    (today: `sub`); everywhere else ("add", "mul", "and", "or", "xor") it
    does not, and the cheaper plain chain / PRIORITY shape is correct.
    `ingestion` is read from the dispatcher's OWN `ingestion_path()` -- the
    scan records the decision the backend will actually make, it does not
    re-derive it."""
    notes: List[OrderNote] = []
    for src, low in zip(source_dag, lowered_dag):
        entry = library_lookup(src.opcode)
        sensitive = entry is not None and (not entry.is_commutative) and len(src.operands) == 2
        ingestion = ingestion_path(low.opcode, [o.kind for o in low.operands])
        if not sensitive:
            notes.append(OrderNote(src.name, src.opcode, False, ingestion, "not needed",
                                   f"`{src.opcode}` is commutative; either arrival order gives the same result"))
        elif low.opcode != src.opcode:
            notes.append(OrderNote(src.name, src.opcode, True, ingestion, "lowered to commutative",
                                   f"`{src.opcode}` is order-sensitive, but with a literal subtrahend it is "
                                   f"rewritten to commutative `{low.opcode}`, so order no longer matters"))
        else:
            notes.append(OrderNote(src.name, src.opcode, True, ingestion, "sequencer",
                                   f"`{src.opcode}` is order-sensitive; operand order is enforced by the "
                                   f"sequenced-channel priority cell (#772/#774), independent of arrival timing"))
    return notes


# ---------------------------------------------------------------------------
# 3c. Backend-capability guards: refuse rather than silently miscompile.
# ---------------------------------------------------------------------------

def _check_capabilities(instrs: List[SourceInstr], dag: List[DagInstr]) -> List[CompileDiagnostic]:
    diags: List[CompileDiagnostic] = []
    for src, ins in zip(instrs, dag):
        what = f"checking `%{ins.name} = {ins.opcode}`"
        entry = library_lookup(ins.opcode)
        if entry is None:
            diags.append(_diag("dag-lowering", what, f"no library entry for opcode `{ins.opcode}`",
                               "the dispatcher only places opcodes the opcode library knows",
                               "this is where `#752`'s escalation ladder would apply (shared library, "
                               "then AI research, then the Composer) -- not built yet"))
            continue
        if src.type_name != _SUPPORTED_TYPE:
            diags.append(_diag("dag-lowering", what, f"result type is {src.type_name}, not i32",
                               "the fabric's cells are 32-bit"))
        if len(ins.operands) != 2:
            diags.append(_diag("dag-lowering", what, f"{len(ins.operands)} operands, expected 2",
                               "every library entry so far is a two-operand core"))
            continue
        kinds = [o.kind for o in ins.operands]
        if kinds == ["const", "const"]:
            diags.append(_diag("dag-lowering", what, "both operands are literals",
                               "the dispatcher places one constant per instruction; it would drop "
                               "one and silently compute the wrong value",
                               "constant-fold it first (constant folding is not built into this frontend)"))
    return diags


# ---------------------------------------------------------------------------
# 4. Glue and the VM harness.
# ---------------------------------------------------------------------------

def _arg_labels(dag: List[DagInstr], arg_uses: Dict[str, List[Tuple[str, int]]]) -> Dict[str, List[str]]:
    """Predict the injection label `compile_dag()` gives each dynamic
    operand: `<name>_x` on the plain-chain path, else `<name>_a`/`<name>_b`
    by operand index (rule shared with the dispatcher via `ingestion_path`). The caller
    cross-checks every predicted label against what `compile_dag()`
    actually returned, so this can never drift silently."""
    by_name = {d.name: d for d in dag}
    out: Dict[str, List[str]] = {}
    for arg, uses in arg_uses.items():
        labels = []
        for instr_name, idx in uses:
            ins = by_name[instr_name]
            plain = ingestion_path(ins.opcode, [o.kind for o in ins.operands]) == "plain_chain"
            labels.append(f"{instr_name}_x" if plain else (f"{instr_name}_a" if idx == 0 else f"{instr_name}_b"))
        out[arg] = labels
    return out


def compile_llvm_via_dag(source: str) -> Tuple[Optional[DagFrontendResult], List[CompileDiagnostic]]:
    fn, diags = extract_llvm_function(source)
    if fn is None:
        return None, diags

    resolved, diags = resolve_symbols(fn.arguments, fn.instrs)
    if resolved is None:
        return None, diags

    if fn.result_name not in {d.name for d in resolved.dag}:
        return None, [_diag("resolve", "resolving the returned value",
                            f"`ret` returns `{fn.result_name}`, which is not the result of any instruction",
                            "returning an argument directly leaves no computed cell to read")]

    lowered, rewrites = _lower_for_backend(resolved.dag)
    diags = _check_capabilities(fn.instrs, lowered)
    if diags:
        return None, diags
    ordering = scan_ordering(resolved.dag, lowered)

    icm, positions, dynamic_positions, seq_orders = compile_dag(lowered)
    problems = icm.check_connections()
    if problems:
        return None, [_diag("emit", "checking compiled connections", str(p),
                            "the dispatcher produced an inconsistent layout") for p in problems]

    dyn = {label: (r, c) for label, r, c in dynamic_positions}
    arg_injections: Dict[str, List[Tuple[int, int]]] = {}
    for arg, labels in _arg_labels(lowered, resolved.arg_uses).items():
        sites = []
        for label in labels:
            if label not in dyn:
                raise RuntimeError(f"internal: predicted injection label {label!r} not produced by "
                                   f"compile_dag() (got {sorted(dyn)}) -- the frontend's label rule has "
                                   f"drifted from the dispatcher's")
            sites.append(dyn[label])
        arg_injections[arg] = sites

    records, _ = icm.flatten()
    core_at = {(r.row, r.col): r.core for r in records}
    result_cell = positions[fn.result_name]
    return DagFrontendResult(function_name=fn.function_name, dag=lowered, icm=icm, records=records,
                             positions=positions, seq_orders=seq_orders, arg_injections=arg_injections,
                             result_name=fn.result_name, result_cell=result_cell,
                             result_core=core_at[result_cell], rewrites=rewrites, ordering=ordering), []


def _read_result(cell, core: str) -> int:
    if core == "adder":
        return cell.adder_out_buffer
    if core == "mul":
        return cell.mul_out_buffer
    if core == "nano":
        return cell._nano.out_buffer
    raise ValueError(f"no known result field for core {core!r}")


def run_in_vm(result: DagFrontendResult, arg_values: Dict[str, int], ticks: int = 600) -> int:
    """Build a fresh real grid, inject each argument at EVERY site that
    reads it, apply any SEQUENCER orders (the caller-side step
    `compile_dag()`'s own docstring requires), tick, and read the result
    cell. A fresh grid per call -- the compiled result is reusable for
    any input."""
    from unicell_super_automaton_v1 import SuperGrid

    missing = set(result.arg_injections) - set(arg_values)
    if missing:
        raise ValueError(f"no value supplied for argument(s): {sorted(missing)}")
    grid = SuperGrid(result.records)
    for arg, sites in result.arg_injections.items():
        for (r, c) in sites:
            cell = grid.cells[(r, c)]
            cell.ram_data_reg = arg_values[arg] & _MASK32
            cell.ram_data_valid = True
    for name, order in result.seq_orders.items():
        for rec in result.records:
            if rec.cell_id == f"main.pri_{name}":
                grid.cells[(rec.row, rec.col)].pri_seq_order = order
    for _ in range(ticks):
        grid.tick()
    return _read_result(grid.cells[result.result_cell], result.result_core)
