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
basic block (no control flow, no loops), `i32` only, opcodes that
already have a real library entry (`add`/`sub`/`mul`/`and`/`or`/`xor`,
and from #797 `shl`/`lshr` with a literal amount), named or numbered SSA values (`%0` becomes `v0`, #799). Not attempted: opcode escalation (scope
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
from icm_vix_v1 import IcmVixFormatError  # noqa: E402
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
    #: `icmp`'s predicate (`slt`, `eq`, ...); None for every other opcode.
    predicate: Optional[str] = None


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
    #: the source instruction this one came from, when the frontend expanded
    #: one source instruction into several library ops (icmp/select/ashr).
    origin: Optional[str] = None


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
    #: known, PRECISELY-BOUNDED inexactness in a compiled program -- surfaced,
    #: never silent (points.md #798).
    caveats: List[str] = field(default_factory=list)


def _diag(stage: str, what: str, problem: str, why: str,
          suggestion: Optional[str] = None) -> CompileDiagnostic:
    return CompileDiagnostic(severity="error", stage=stage, what=what, problem=problem,
                             why=why, suggestion=suggestion)


# ---------------------------------------------------------------------------
# 1. The LLVM-specific extractor.
# ---------------------------------------------------------------------------

_UNNAMED_DEF_RE = re.compile(r"^%(\S+)\s*=")          # a reference to an unnamed RESULT prints as its defining instruction
_UNNAMED_ARG_RE = re.compile(r"^(?:i\d+\s+)%(\S+)$")     # a reference to an unnamed ARGUMENT prints as `i32 %0`


def _source_operand(op, label) -> Tuple[Optional[SourceOperand], Optional[str]]:
    """Returns (operand, problem). llvmlite reports `name == ''` for a literal
    AND for a reference to an unnamed value (`%0`, `%3`, ...) -- and for an
    unnamed RESULT, `str(op)` is the whole defining instruction, whose last
    token can look like an integer. So a literal is recognised ONLY by matching
    the whole text against `i32 <int>` (never a last-token parse -- the trap a
    naive parse falls into), and an unnamed value is recognised by its own
    printed form, then given a stable identifier by `label` (points.md #799)."""
    if op.name:
        return SourceOperand(kind="name", name=op.name), None
    text = str(op).strip()
    m = _LITERAL_RE.match(text)
    if m:
        return SourceOperand(kind="literal", value=int(m.group(1)) & _MASK32), None
    m = _UNNAMED_DEF_RE.match(text) or _UNNAMED_ARG_RE.match(text)
    if m:
        return SourceOperand(kind="name", name=label(m.group(1))), None
    return None, f"an operand {text!r} is not a plain integer literal or a named/numbered value"


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

    # Unnamed values (`%0`, `%3`) get the identifier `v<N>`, uniquified against every
    # real name in the function so the mapping is stable and collision-free.
    real_names = {a.name for a in fn.arguments if a.name} | {i.name for i in blocks[0].instructions if i.name}

    def label(n: str) -> str:
        name = f"v{n}"
        while name in real_names:
            name += "_"
        return name

    arguments: List[str] = []
    for a in fn.arguments:
        aname = a.name
        if not aname:
            m = _UNNAMED_ARG_RE.match(str(a).strip())
            aname = label(m.group(1)) if m else ""
        if not aname:
            diags.append(_diag("llvm-frontend", what, "an unnamed function argument that could not be identified",
                               "arguments are bound to injection sites by name"))
        elif str(a.type) != _SUPPORTED_TYPE:
            diags.append(_diag("llvm-frontend", what, f"argument %{a.name} has type {a.type}, not i32",
                               "the fabric's cells are 32-bit; a wider or narrower type would be "
                               "silently truncated or mis-sized"))
        else:
            arguments.append(aname)

    instrs: List[SourceInstr] = []
    result_name: Optional[str] = None
    for ins in blocks[0].instructions:
        ops = list(ins.operands)
        if ins.opcode == "ret":
            so_ret, problem = _source_operand(ops[0], label) if len(ops) == 1 else (None, "no value")
            if problem or so_ret.kind != "name":
                diags.append(_diag("llvm-frontend", what,
                                   "`ret` must return exactly one named or numbered value",
                                   "the frontend needs to know which computed cell holds the result",
                                   "return an SSA value, e.g. `ret i32 %b`"))
            else:
                result_name = so_ret.name
            continue
        iname = ins.name
        if not iname:
            m = _UNNAMED_DEF_RE.match(str(ins).strip())
            iname = label(m.group(1)) if m else ""
        if not iname:
            diags.append(_diag("llvm-frontend", what,
                               f"a value produced by `{ins.opcode}` whose identifier could not be determined",
                               "later operands must be able to resolve against it"))
            continue
        src_ops: List[SourceOperand] = []
        for op in ops:
            so, problem = _source_operand(op, label)
            if problem:
                diags.append(_diag("llvm-frontend", f"reading operands of %{iname}", problem,
                                   "every operand must be traceable to an argument, an earlier "
                                   "result, or a literal"))
            else:
                src_ops.append(so)
        predicate = None
        if ins.opcode == "icmp":
            m = re.search(r"=\s*icmp\s+(\w+)\s", str(ins))
            predicate = m.group(1) if m else None
        instrs.append(SourceInstr(name=iname, opcode=ins.opcode, operands=src_ops,
                                  type_name=str(ins.type), predicate=predicate))

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
                # `ref_name` carries the ARGUMENT NAME on a dynamic operand, so
                # the operand stays self-describing through every later
                # rewrite/expansion (the dispatcher ignores it for dynamics).
                dag_ops.append(DagOperand(kind="dynamic", ref_name=op.name))
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
        dag.append(DagInstr(name=ins.name, opcode=ins.opcode, operands=dag_ops,
                            params=({"predicate": ins.predicate} if ins.predicate else {})))

    if diags:
        return None, diags
    return ResolvedProgram(dag=dag, arg_uses=arg_uses), []


# ---------------------------------------------------------------------------
# 3a. Source-level capability checks: refuse rather than silently miscompile.
# ---------------------------------------------------------------------------

#: opcodes with NO single library entry that the frontend EXPANDS into
#: several library ops (compose before building new hardware).
_EXPANDABLE = {"icmp", "select", "ashr"}
#: predicate -> (swap operands before the subtraction, comparator threshold).
#: sge/sgt: diff = A-B; slt/sle: diff = B-A (the old frontend's own table, #611).
_ICMP_ORDERED = {"sge": (False, 0), "sgt": (False, 1), "slt": (True, 1), "sle": (True, 0)}
_ICMP_EQ_NE = ("eq", "ne")
_TYPE_FOR = {"icmp": "i1"}


def _shift_problem(ins: DagInstr) -> Optional[str]:
    """Why a shift-shaped instruction (value, literal amount) cannot be lowered."""
    kinds = [o.kind for o in ins.operands]
    if len(kinds) != 2:
        return f"{len(kinds)} operands, expected 2"
    if kinds == ["const", "const"]:
        return "both operands are literals (constant folding is not built into this frontend)"
    if kinds[1] != "const":
        return ("the shift amount is not a compile-time literal -- a variable shift amount would need a "
                "barrel shifter, which the shift addon (fixed coarse+fine taps) is not")
    if kinds[0] == "const":
        return "the shifted value is a literal (constant folding is not built into this frontend)"
    if not 0 <= ins.operands[1].value <= 31:
        return f"the shift amount {ins.operands[1].value} is outside 0-31 (poison in LLVM; the addon covers 0-31)"
    return None


def _check_source(instrs: List[SourceInstr], dag: List[DagInstr]) -> List[CompileDiagnostic]:
    diags: List[CompileDiagnostic] = []
    types: Dict[str, str] = {}
    for src, ins in zip(instrs, dag):
        what = f"checking `%{ins.name} = {ins.opcode}`"
        types[ins.name] = src.type_name
        op = ins.opcode
        entry = library_lookup(op)
        if entry is None and op not in _EXPANDABLE:
            diags.append(_diag("dag-lowering", what, f"no library entry for opcode `{op}`",
                               "the dispatcher only places opcodes the opcode library knows",
                               "this is where `#752`'s escalation ladder would apply (shared library, "
                               "then AI research, then the Composer) -- not built yet"))
            continue
        want = _TYPE_FOR.get(op, _SUPPORTED_TYPE)
        if src.type_name != want:
            diags.append(_diag("dag-lowering", what, f"result type is {src.type_name}, not {want}",
                               "the fabric's cells are 32-bit; a wider or narrower type would be "
                               "silently truncated or mis-sized"))
            continue
        kinds = [o.kind for o in ins.operands]

        if op == "select":
            if len(ins.operands) != 3:
                diags.append(_diag("dag-lowering", what, f"{len(ins.operands)} operands, expected 3",
                                   "`select` takes a condition and two values"))
                continue
            c = ins.operands[0]
            if c.kind != "ref" or types.get(c.ref_name) != "i1":
                diags.append(_diag("dag-lowering", what, "the condition is not the result of an earlier `icmp`",
                                   "only a 0/1 boolean produced by a comparison can be widened to a mask; "
                                   "a literal or wider condition would give a wrong mask"))
            continue
        if op == "icmp":
            if len(ins.operands) != 2:
                diags.append(_diag("dag-lowering", what, f"{len(ins.operands)} operands, expected 2",
                                   "`icmp` compares two values"))
            elif ins.params.get("predicate") not in _ICMP_ORDERED and ins.params.get("predicate") not in _ICMP_EQ_NE:
                diags.append(_diag("dag-lowering", what, f"predicate `{ins.params.get('predicate')}` is not supported",
                                   f"supported: {sorted(list(_ICMP_ORDERED) + list(_ICMP_EQ_NE))} -- the same "
                                   f"set the old frontend has (unsigned predicates are separate, unbuilt work)"))
            elif kinds == ["const", "const"]:
                diags.append(_diag("dag-lowering", what, "both operands are literals",
                                   "constant folding is not built into this frontend"))
            continue
        if op == "ashr" or (entry is not None and entry.arity == 1):
            problem = _shift_problem(ins)
            if problem:
                diags.append(_diag("dag-lowering", what, f"`{op}` cannot be lowered: {problem}",
                                   "the shift addon takes its amount as compile-time configuration",
                                   "use a literal amount in 0-31 on a variable value"))
            continue
        if len(ins.operands) != 2:
            diags.append(_diag("dag-lowering", what, f"{len(ins.operands)} operands, expected 2",
                               "every two-operand library entry expects exactly 2"))
        elif kinds == ["const", "const"]:
            diags.append(_diag("dag-lowering", what, "both operands are literals",
                               "the dispatcher places one constant per instruction; it would drop "
                               "one and silently compute the wrong value",
                               "constant-fold it first (constant folding is not built into this frontend)"))
    return diags


# ---------------------------------------------------------------------------
# 3b. Lowering: 1:N expansions, then 1:1 rewrites, with lineage.
# ---------------------------------------------------------------------------

def _fresh(base: str, tag: str, used: Set[str]) -> str:
    name = f"{base}__{tag}"
    while name in used:
        name += "_"
    used.add(name)
    return name


def _ref(name: str) -> DagOperand:
    return DagOperand(kind="ref", ref_name=name)


def _const(v: int) -> DagOperand:
    return DagOperand(kind="const", value=v & _MASK32)


def _expand(ins: DagInstr, used: Set[str]) -> List[DagInstr]:
    """One source instruction -> several LIBRARY ops (the last keeps the
    source `%name`; the rest get `<name>__<tag>`). Composition before new
    hardware: every piece below already exists, and the order-sensitive
    `sub` inside gets the backend's ordering guarantee (#796) for free."""
    n, op = ins.name, ins.opcode
    if op == "icmp":
        pred = ins.params["predicate"]
        x, y = ins.operands
        if pred in _ICMP_ORDERED:
            swap, thr = _ICMP_ORDERED[pred]
            a, b = (y, x) if swap else (x, y)
            d = _fresh(n, "d", used)
            return [DagInstr(d, "sub", [a, b]), DagInstr(n, "cmp_ge", [_ref(d)], params={"threshold": thr})]
        # eq/ne: diff is exactly 0 iff XOR(diff>=0, diff>=1) (#668)
        d, c0, c1 = _fresh(n, "d", used), _fresh(n, "ge0", used), _fresh(n, "ge1", used)
        out = [DagInstr(d, "sub", [x, y]),
               DagInstr(c0, "cmp_ge", [_ref(d)], params={"threshold": 0}),
               DagInstr(c1, "cmp_ge", [_ref(d)], params={"threshold": 1})]
        if pred == "eq":
            out.append(DagInstr(n, "xor", [_ref(c0), _ref(c1)]))
        else:  # ne = NOT eq, as XOR with 1 (a bitwise XNOR would flip all 32 bits, #668)
            e = _fresh(n, "eq", used)
            out += [DagInstr(e, "xor", [_ref(c0), _ref(c1)]), DagInstr(n, "xor", [_ref(e), _const(1)])]
        return out
    if op == "select":
        c, t, f = ins.operands
        m, nm = _fresh(n, "mask", used), _fresh(n, "nmask", used)
        at, af = _fresh(n, "t", used), _fresh(n, "f", used)
        return [DagInstr(m, "sub", [_const(0), c]),                 # 0/1 -> 0 / 0xFFFFFFFF
                DagInstr(nm, "xor", [_ref(m), _const(_MASK32)]),    # ~mask
                DagInstr(at, "and", [t, _ref(m)]),
                DagInstr(af, "and", [f, _ref(nm)]),
                DagInstr(n, "or", [_ref(at), _ref(af)])]
    if op == "ashr":
        x, amt = ins.operands
        k = amt.value
        if k == 0:
            return [DagInstr(n, "add", [x, _const(0)])]
        # arithmetic shift = logical shift, OR a sign-fill: the top k bits are the
        # sign mask (0 or all-ones) shifted left by 32-k. No sign-magnitude, no
        # branch, no correction stage -- only library ops that already exist.
        s, m, fill, lo = (_fresh(n, "sign", used), _fresh(n, "smask", used),
                          _fresh(n, "fill", used), _fresh(n, "lo", used))
        return [DagInstr(s, "lshr", [x, _const(31)]),
                DagInstr(m, "sub", [_const(0), _ref(s)]),
                DagInstr(fill, "shl", [_ref(m), _const(32 - k)]),
                DagInstr(lo, "lshr", [x, _const(k)]),
                DagInstr(n, "or", [_ref(lo), _ref(fill)])]
    raise AssertionError(op)


def _rewrite_one(ins: DagInstr) -> Tuple[DagInstr, Optional[str]]:
    """1:1, equivalence-preserving rewrites chosen by what the backend does
    best. `sub %v, C` -> `add %v, -C` (commutative: cheaper than a sequencer
    and correct by construction; also what the old frontend does and what
    LLVM canonicalizes to). A shift's literal amount moves out of the operand
    list into `params` (it is configuration, not a data operand)."""
    kinds = [o.kind for o in ins.operands]
    entry = library_lookup(ins.opcode)
    if entry is not None and entry.arity == 1 and len(ins.operands) == 2:
        amount = ins.operands[1].value
        return (DagInstr(name=ins.name, opcode=ins.opcode, operands=[ins.operands[0]], params={"amount": amount}),
                f"%{ins.name}: {ins.opcode} <value>, {amount}  ->  one-operand {ins.opcode} with amount "
                f"{amount} in addon config")
    if ins.opcode == "sub" and len(ins.operands) == 2 and kinds[0] != "const" and kinds[1] == "const":
        neg = (-ins.operands[1].value) & _MASK32
        return (DagInstr(name=ins.name, opcode="add", operands=[ins.operands[0], _const(neg)]),
                f"%{ins.name}: sub <value>, {ins.operands[1].value}  ->  add <value>, {neg:#x}")
    return ins, None


def _lower_and_expand(dag: List[DagInstr], used: Set[str]
                      ) -> Tuple[List[DagInstr], List[str], Dict[str, Tuple[str, str]]]:
    """Returns (final DAG, human-readable rewrite notes, lineage). `lineage`
    maps each final instruction's name to (source instruction name, the
    opcode it had BEFORE the 1:1 rewrites) -- so the scan pass and any reader
    can trace a library op back to the `%name` it came from."""
    final: List[DagInstr] = []
    notes: List[str] = []
    lineage: Dict[str, Tuple[str, str]] = {}
    for ins in dag:
        if ins.opcode in _EXPANDABLE:
            parts = _expand(ins, used)
            notes.append(f"%{ins.name}: {ins.opcode} expanded into {len(parts)} library ops: "
                         + ", ".join(f"%{p.name}={p.opcode}" for p in parts))
        else:
            parts = [ins]
        for p in parts:
            lineage[p.name] = (ins.name, p.opcode)
            q, note = _rewrite_one(p)
            if note:
                notes.append(note)
            final.append(q)
    return final, notes, lineage


# ---------------------------------------------------------------------------
# 3c. The scan pass's ordering report.
# ---------------------------------------------------------------------------

def scan_ordering(final: List[DagInstr], lineage: Dict[str, Tuple[str, str]]) -> List[OrderNote]:
    """Record, per instruction of the FINAL DAG, whether operand ORDER is
    essential and what guarantees it. Order matters only for a non-commutative
    two-operand op (today: `sub`); everywhere else the cheaper plain chain /
    PRIORITY shape is correct. `ingestion` is read from the dispatcher's OWN
    `ingestion_path()` -- the scan records the decision the backend will
    actually make, it does not re-derive it. `origin` traces an expanded
    library op back to its source `%name`."""
    notes: List[OrderNote] = []
    for ins in final:
        origin, pre_opcode = lineage[ins.name]
        pre = library_lookup(pre_opcode)
        entry = library_lookup(ins.opcode)
        sensitive = pre is not None and not pre.is_commutative
        ingestion = ingestion_path(ins.opcode, [o.kind for o in ins.operands])
        shown = pre_opcode
        o = origin if origin != ins.name else None
        if not sensitive:
            single = entry is not None and entry.arity == 1
            notes.append(OrderNote(ins.name, shown, False, ingestion, "not needed",
                                   f"`{shown}` has one data operand (any amount/threshold is configuration); "
                                   f"there is no operand order to get wrong" if single else
                                   f"`{shown}` is commutative; either arrival order gives the same result", o))
        elif ins.opcode != pre_opcode:
            notes.append(OrderNote(ins.name, shown, True, ingestion, "lowered to commutative",
                                   f"`{shown}` is order-sensitive, but with a literal subtrahend it is "
                                   f"rewritten to commutative `{ins.opcode}`, so order no longer matters", o))
        else:
            notes.append(OrderNote(ins.name, shown, True, ingestion, "sequencer",
                                   f"`{shown}` is order-sensitive; operand order is enforced by the "
                                   f"sequenced-channel priority cell (#772/#774), independent of arrival timing", o))
    return notes


# ---------------------------------------------------------------------------
# 4. Glue and the VM harness.
# ---------------------------------------------------------------------------

def _arg_labels(dag: List[DagInstr], arg_uses: Dict[str, List[Tuple[str, int]]]) -> Dict[str, List[str]]:
    """Predict the injection label `compile_dag()` gives each dynamic
    operand: `<name>_x` on the plain-chain path, else `<name>_a`/`<name>_b`
    by operand index (rule shared with the dispatcher via `ingestion_path`).
    The caller cross-checks every predicted label against what `compile_dag()`
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

    diags = _check_source(fn.instrs, resolved.dag)
    if diags:
        return None, diags

    used: Set[str] = set(fn.arguments) | {d.name for d in resolved.dag}
    final, rewrites, lineage = _lower_and_expand(resolved.dag, used)
    ordering = scan_ordering(final, lineage)
    caveats = [f"%{i.name}: `icmp {i.params['predicate']}` is exact only while the signed difference it computes "
               f"does not overflow 32 bits (opposite-sign operands whose magnitudes sum past 2^31-1 give the "
               f"WRONG answer, not an error) -- inherited from the old frontend (#711), bounded exactly (#798). "
               f"`eq`/`ne` are exact for every input."
               for i in resolved.dag if i.opcode == "icmp" and i.params.get("predicate") in _ICMP_ORDERED]

    try:
        icm, positions, dynamic_positions, seq_orders = compile_dag(final)
        problems = icm.check_connections()
    except (IcmVixFormatError, ValueError) as e:
        # A LOUD, PRECISE refusal -- never a raw exception, never a silent miscompile. The
        # growing-frontier placement (#780) has no global occupancy planning: two
        # independently-computed chains that must merge are routed straight-then-turn and can
        # cross other structure; `flatten()` rejects that collision (points.md #798).
        return None, [_diag("place", "placing the compiled DAG", str(e),
                            "the dispatcher's growing-frontier placement has no global occupancy planning "
                            "yet, so it cannot route every shape -- typically two independently-computed "
                            "values that must be merged (e.g. a `select` whose BOTH arms are computed), "
                            "or a chain of `select`s",
                            "restructure so at most one merge input is an independent computed chain; "
                            "occupancy-aware placement / tightening is separate, named work")]
    if problems:
        return None, [_diag("emit", "checking compiled connections", str(p),
                            "the dispatcher produced an inconsistent layout") for p in problems]

    # Argument bindings come from the FINAL DAG (each dynamic operand carries its
    # argument name), so they stay right through any expansion or rewrite.
    arg_uses: Dict[str, List[Tuple[str, int]]] = {a: [] for a in fn.arguments}
    for ins in final:
        for k, o in enumerate(ins.operands):
            if o.kind == "dynamic":
                arg_uses[o.ref_name].append((ins.name, k))

    dyn = {label: (r, c) for label, r, c in dynamic_positions}
    arg_injections: Dict[str, List[Tuple[int, int]]] = {}
    for arg, labels in _arg_labels(final, arg_uses).items():
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
    return DagFrontendResult(function_name=fn.function_name, dag=final, icm=icm, records=records,
                             positions=positions, seq_orders=seq_orders, arg_injections=arg_injections,
                             result_name=fn.result_name, result_cell=result_cell,
                             result_core=core_at[result_cell], rewrites=rewrites, ordering=ordering,
                             caveats=caveats), []


def _read_result(cell, core: str) -> int:
    if core == "adder":
        return cell.adder_out_buffer
    if core == "mul":
        return cell.mul_out_buffer
    if core == "nano":
        return cell._nano.out_buffer
    if core == "ram":
        return cell.ram_data_reg
    if core == "comparator":
        return cell.cmp_out_buffer
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
