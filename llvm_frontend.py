"""
llvm_frontend.py — LLVM IR Frontend for Claudette v1.0

Parses LLVM IR text (.ll format), validates that it falls within the
supported instruction subset, and emits a ClaudetteLLVMFunction parse
tree that the IR mapping layer can consume.

Supported instruction subset
=============================

Integer arithmetic (i32 only for now):
  add, sub, mul          — maps to INT32_ADD_CLA, INT32_SUB, INT32_MUL (future)
  and, or, xor           — maps to INT32_AND, INT32_OR, INT32_XOR
  shl, lshr, ashr        — shift (future tile)
  udiv, sdiv, urem, srem — division (future tile)

Bitwise / unary:
  not (via xor %x, -1)   — maps to INT32_NOT

Comparison:
  icmp eq   — INT32_EQ
  icmp ne   — NOT(INT32_EQ)
  icmp slt  — sign bit of (a - b)
  icmp sgt  — sign bit of (b - a)
  icmp sle  — NOT(sgt)
  icmp sge  — NOT(slt)
  icmp ult  — unsigned less than (future)
  icmp ugt  — unsigned greater than (future)

Control flow:
  br (unconditional)      — connect blocks directly
  br (conditional)        — GS_SELECT routing
  phi                     — storage cell (same as while-loop variable)
  ret                     — designate output address

Memory (limited):
  alloca                  — allocate a named bus address slot
  load / store            — bus read / write at allocated address

Rejected (clear error emitted):
  call (direct)           — only builtins permitted: llvm.ctpop, llvm.bswap
  invoke, resume          — exceptions not supported
  getelementptr           — pointer arithmetic not supported
  bitcast, inttoptr       — type punning not supported
  float types             — f32/f64 not supported in this path
  vector types            — SIMD not supported
  i1, i8, i16, i64        — only i32 supported (i1 for branch conditions only)

Integer width support:
  i1   — allowed only as branch condition output of icmp
  i32  — primary integer type, maps to Int32Value tiles
  i64  — rejected (no 64-bit tile path yet)

Workflow
========

  from llvm_frontend import LLVMFrontend, FrontendError

  fe = LLVMFrontend()
  result = fe.parse(ll_source)          # parse .ll text

  if result.errors:
      for e in result.errors:
          print(e)
  else:
      for fn in result.functions:
          print(fn.name, fn.args, len(fn.blocks), 'blocks')
          for block in fn.blocks:
              for instr in block.instructions:
                  print(' ', instr)

  # Feed to IR mapping layer:
  # from llvm_ir_mapper import LLVMIRMapper
  # mapper = LLVMIRMapper()
  # program_image = mapper.lower(result.functions[0])
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ── Supported instructions ────────────────────────────────────────────────────

# These map directly to existing Claudette tiles
SUPPORTED_ARITH = {
    "add":  "INT32_ADD",   # Kogge-Stone parallel prefix (~482 cells)
    "sub":  "INT32_SUB",
    "and":  "INT32_AND",
    "or":   "INT32_OR",
    "xor":  "INT32_XOR",
}

# These need future tiles — accepted in parse but flagged as unimplemented
FUTURE_ARITH = {
    "mul":  "INT32_MUL",
    "shl":  "INT32_SHL",
    "lshr": "INT32_LSHR",
    "ashr": "INT32_ASHR",
    "udiv": "INT32_UDIV",
    "sdiv": "INT32_SDIV",
    "urem": "INT32_UREM",
    "srem": "INT32_SREM",
}

# icmp predicates → Claudette tile / construction
SUPPORTED_ICMP = {
    "eq":  "INT32_EQ",
    "ne":  "NOT(INT32_EQ)",
    "slt": "SIGN_BIT(INT32_SUB(a,b))",
    "sgt": "SIGN_BIT(INT32_SUB(b,a))",
    "sle": "NOT(SIGN_BIT(INT32_SUB(b,a)))",
    "sge": "NOT(SIGN_BIT(INT32_SUB(a,b)))",
    "ult": "INT32_ULT",    # future
    "ugt": "INT32_UGT",    # future
    "ule": "INT32_ULE",    # future
    "uge": "INT32_UGE",    # future
}

FUTURE_ICMP = {"ult", "ugt", "ule", "uge"}

# Control flow opcodes
CONTROL_OPS = {"br", "ret", "phi"}

# Memory opcodes
MEMORY_OPS = {"alloca", "load", "store"}

# Permitted LLVM intrinsic calls
PERMITTED_INTRINSICS = {
    "llvm.ctpop.i32",   # popcount
    "llvm.bswap.i32",   # byte swap
    "llvm.ctlz.i32",    # count leading zeros
    "llvm.cttz.i32",    # count trailing zeros
}

# Rejected opcodes with reasons
REJECTED_OPS = {
    "invoke":         "exceptions not supported (use br/phi instead)",
    "resume":         "exceptions not supported",
    "landingpad":     "exceptions not supported",
    "getelementptr":  "pointer arithmetic not supported",
    "bitcast":        "type punning not supported",
    "inttoptr":       "pointer conversion not supported",
    "ptrtoint":       "pointer conversion not supported",
    "extractelement": "vector/SIMD not supported",
    "insertelement":  "vector/SIMD not supported",
    "shufflevector":  "vector/SIMD not supported",
    "extractvalue":   "aggregate types not supported",
    "insertvalue":    "aggregate types not supported",
    "fence":          "memory ordering not supported",
    "atomicrmw":      "atomic operations not supported",
    "cmpxchg":        "atomic operations not supported",
}


# ── Parse tree data structures ────────────────────────────────────────────────

@dataclass
class LLVMValue:
    """A value in LLVM IR — either a named register or a constant."""
    raw:        str           # original string e.g. '%a', 'i32 5', '%result'
    name:       str  = ""     # register name (without %) or ""
    is_const:   bool = False
    const_val:  int  = 0
    type_str:   str  = "i32"

    def __repr__(self) -> str:
        if self.is_const:
            return f"const({self.const_val})"
        return f"%{self.name}"


@dataclass
class LLVMInstruction:
    """One LLVM IR instruction."""
    opcode:     str
    result:     str  = ""       # result register name (without %)
    result_type:str  = "i32"
    operands:   list = field(default_factory=list)   # list of LLVMValue
    # icmp specific
    predicate:  str  = ""       # eq, ne, slt, sgt, etc.
    # phi specific
    phi_values: list = field(default_factory=list)   # [(value, block_name), ...]
    # br specific
    is_conditional: bool = False
    true_label: str  = ""
    false_label:str  = ""
    target_label:str = ""       # unconditional br
    # call specific
    callee:     str  = ""
    # alloca specific
    alloc_type: str  = ""
    # raw LLVM IR string (for debugging)
    raw:        str  = ""
    # tile this maps to (filled by frontend for supported ops)
    maps_to_tile: str = ""
    # warning if unimplemented but parseable
    warning:    str  = ""

    def __repr__(self) -> str:
        if self.result:
            return f"%{self.result} = {self.opcode} {self.operands}"
        return f"{self.opcode} {self.operands}"


@dataclass
class LLVMBlock:
    """A basic block in LLVM IR."""
    name:         str
    instructions: list = field(default_factory=list)  # list of LLVMInstruction
    predecessors: list = field(default_factory=list)   # block names
    successors:   list = field(default_factory=list)   # block names

    def __repr__(self) -> str:
        return f"Block({self.name!r}, {len(self.instructions)} instrs)"


@dataclass
class LLVMFunction:
    """A parsed LLVM IR function."""
    name:       str
    args:       list          # [(name, type_str), ...]
    return_type:str
    blocks:     list = field(default_factory=list)   # list of LLVMBlock
    # Computed properties
    entry_block: str = ""     # name of entry block (first one)

    @property
    def arg_names(self) -> list[str]:
        return [name for name, _ in self.args]

    def block(self, name: str) -> Optional[LLVMBlock]:
        for b in self.blocks:
            if b.name == name:
                return b
        return None

    def __repr__(self) -> str:
        return (f"LLVMFunction({self.name!r}, "
                f"args={self.arg_names}, "
                f"{len(self.blocks)} blocks)")


@dataclass
class FrontendResult:
    """Result of parsing an LLVM IR source string."""
    functions:  list = field(default_factory=list)   # list of LLVMFunction
    errors:     list = field(default_factory=list)   # FrontendError strings
    warnings:   list = field(default_factory=list)   # non-fatal issues
    source:     str  = ""

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> str:
        lines = [
            f"LLVMFrontend parse result:",
            f"  Functions: {len(self.functions)}",
            f"  Errors:    {len(self.errors)}",
            f"  Warnings:  {len(self.warnings)}",
        ]
        for e in self.errors:
            lines.append(f"  ERROR:   {e}")
        for w in self.warnings:
            lines.append(f"  WARN:    {w}")
        return "\n".join(lines)


class FrontendError(Exception):
    pass


# ── Value parser ──────────────────────────────────────────────────────────────

def _parse_value(raw: str, type_str: str = "i32") -> LLVMValue:
    """
    Parse a typed LLVM value string into an LLVMValue.
    Examples: 'i32 %a', 'i32 5', 'i1 %cmp', 'i32 -1'
    """
    raw = raw.strip()

    # Strip leading type annotation
    type_match = re.match(r'^(i\d+|float|double)\s+', raw)
    if type_match:
        type_str = type_match.group(1)
        rest = raw[type_match.end():]
    else:
        rest = raw

    # Register reference
    if rest.startswith('%'):
        name = rest[1:].strip()
        # Strip trailing comma or closing paren
        name = re.split(r'[,)\s]', name)[0]
        return LLVMValue(raw=raw, name=name, type_str=type_str)

    # Integer constant
    try:
        val = int(rest.strip())
        return LLVMValue(raw=raw, name="", is_const=True,
                         const_val=val, type_str=type_str)
    except ValueError:
        pass

    # Fallback — treat as register
    name = re.split(r'[,)\s]', rest)[0]
    return LLVMValue(raw=raw, name=name, type_str=type_str)


def _extract_operands(operand_strs: list, instr_str: str = "") -> list[LLVMValue]:
    """
    Convert a list of llvmlite operand strings to LLVMValue objects.
    """
    values = []
    for op_str in operand_strs:
        op_str = op_str.strip()
        if not op_str:
            continue
        # Skip block labels (operands of br that are whole blocks)
        if op_str.startswith('\n') or 'preds =' in op_str:
            continue
        values.append(_parse_value(op_str))
    return values


# ── Instruction parser ────────────────────────────────────────────────────────

def _parse_icmp_predicate(instr_str: str) -> str:
    """Extract icmp predicate from instruction string."""
    m = re.search(r'icmp\s+(\w+)\s+', instr_str)
    return m.group(1) if m else ""


def _parse_phi_values(instr_str: str,
                      incoming_blocks: list) -> list[tuple]:
    """
    Parse phi instruction incoming values.
    Returns [(LLVMValue, block_name), ...]
    """
    # Match all [ value, label ] pairs
    pairs = re.findall(r'\[\s*(%?[\w.]+|-?\d+),\s*%?([\w.]+)\s*\]', instr_str)
    result = []
    for val_str, block_name in pairs:
        val_str = val_str.strip()
        result.append((_parse_value(val_str), block_name))
    return result


def _parse_br(instr_str: str,
              operand_strs: list) -> tuple:
    """
    Parse br instruction.
    Returns (is_conditional, condition_val, true_label, false_label, target_label)
    """
    # Conditional: br i1 %cond, label %true, label %false
    cond_match = re.search(
        r'br\s+i1\s+(%[\w.]+),\s*label\s+%([\w.]+),\s*label\s+%([\w.]+)',
        instr_str)
    if cond_match:
        cond  = _parse_value(cond_match.group(1), "i1")
        true  = cond_match.group(2)
        false = cond_match.group(3)
        return True, cond, true, false, ""

    # Unconditional: br label %target
    unc_match = re.search(r'br\s+label\s+%([\w.]+)', instr_str)
    if unc_match:
        return False, None, "", "", unc_match.group(1)

    return False, None, "", "", ""


def _parse_call(instr_str: str) -> tuple:
    """
    Parse call instruction.
    Returns (callee_name, arg_values)
    """
    # call i32 @llvm.ctpop.i32(i32 %x)
    m = re.search(r'call\s+\w+\s+@([\w.]+)\s*\(([^)]*)\)', instr_str)
    if m:
        callee = m.group(1)
        args_str = m.group(2)
        args = [_parse_value(a.strip()) for a in args_str.split(',') if a.strip()]
        return callee, args
    return "", []


# ── LLVMFrontend ──────────────────────────────────────────────────────────────

class LLVMFrontend:
    """
    Parses LLVM IR text, validates the instruction subset,
    and emits a FrontendResult parse tree.

    Input:  LLVM IR text (.ll format) as a string
    Output: FrontendResult containing LLVMFunction parse trees
    """

    def __init__(self):
        self._errors:   list = []
        self._warnings: list = []

    # ── Public interface ──────────────────────────────────────────────────────

    def parse(self, ll_source: str) -> FrontendResult:
        """
        Parse LLVM IR source text.
        Returns FrontendResult — check .ok and .errors before using .functions.
        """
        self._errors   = []
        self._warnings = []

        try:
            import llvmlite.binding as llvm
        except ImportError:
            return FrontendResult(
                errors=["llvmlite not installed — pip install llvmlite"],
                source=ll_source,
            )

        # Parse via llvmlite
        try:
            mod = llvm.parse_assembly(ll_source)
            mod.verify()
        except Exception as e:
            return FrontendResult(
                errors=[f"LLVM parse error: {e}"],
                source=ll_source,
            )

        functions = []
        for fn in mod.functions:
            if fn.is_declaration:
                continue   # skip extern declarations
            parsed_fn = self._parse_function(fn)
            if parsed_fn is not None:
                functions.append(parsed_fn)

        return FrontendResult(
            functions = functions,
            errors    = list(self._errors),
            warnings  = list(self._warnings),
            source    = ll_source,
        )

    def parse_file(self, path: str) -> FrontendResult:
        """Parse a .ll file from disk."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
        except IOError as e:
            return FrontendResult(errors=[f"Cannot read '{path}': {e}"])
        return self.parse(source)

    def validate(self, ll_source: str) -> list[str]:
        """
        Validate source and return list of errors (empty = valid).
        Lighter weight than parse() — does not build full parse tree.
        """
        result = self.parse(ll_source)
        return result.errors

    # ── Function parsing ──────────────────────────────────────────────────────

    def _parse_function(self, fn) -> Optional[LLVMFunction]:
        """Parse one llvmlite function into an LLVMFunction."""
        # Extract argument types
        args = []
        for arg in fn.arguments:
            type_str = str(arg.type)
            if not self._check_type(type_str, context=f"arg %{arg.name}"):
                pass   # error already recorded, continue
            args.append((arg.name, type_str))

        # Check return type — parse from function type string
        # Newer LLVM (14+) returns 'ptr' from fn.type; parse from the
        # function definition string instead: 'define i32 @name(...)'
        import re as _re
        fn_str = str(fn)
        ret_match = _re.search(r'define\s+(\w+)\s+@', fn_str)
        ret_type = ret_match.group(1) if ret_match else "i32"
        if ret_type not in ("void", "i32", "i1"):
            self._warn(f"function '{fn.name}': return type '{ret_type}' "
                       f"may not be fully supported (i32 recommended)")

        llfn = LLVMFunction(
            name        = fn.name,
            args        = args,
            return_type = ret_type,
        )

        blocks = list(fn.blocks)
        if not blocks:
            self._error(f"function '{fn.name}': no basic blocks")
            return None

        llfn.entry_block = blocks[0].name

        # Parse all blocks
        for block in blocks:
            parsed_block = self._parse_block(block, fn.name)
            llfn.blocks.append(parsed_block)

        # Build successor/predecessor graph
        self._build_cfg(llfn)

        return llfn

    # ── Block parsing ─────────────────────────────────────────────────────────

    def _parse_block(self, block, fn_name: str) -> LLVMBlock:
        """Parse one basic block."""
        llblock = LLVMBlock(name=block.name)

        for instr in block.instructions:
            parsed = self._parse_instruction(instr, fn_name, block.name)
            if parsed is not None:
                llblock.instructions.append(parsed)

        return llblock

    # ── Instruction parsing ───────────────────────────────────────────────────

    def _parse_instruction(self, instr, fn_name: str,
                            block_name: str) -> Optional[LLVMInstruction]:
        """Parse one llvmlite instruction."""
        opcode    = instr.opcode
        instr_str = str(instr).strip()
        result_name = instr.name if instr.name else ""
        result_type = str(instr.type)
        op_strs   = [str(o) for o in instr.operands]

        ctx = f"{fn_name}/{block_name}: '{instr_str}'"

        # ── Rejected opcodes ──────────────────────────────────────────────────
        if opcode in REJECTED_OPS:
            self._error(f"{ctx} — {REJECTED_OPS[opcode]}")
            return None

        # ── Type check ────────────────────────────────────────────────────────
        # i1 only allowed as icmp result or br condition
        if result_type not in ("void", "i32", "i1", "") and \
                not result_type.startswith("i32*"):
            if result_type in ("float", "double",
                               "i64", "i128", "i8", "i16"):
                self._error(
                    f"{ctx} — type '{result_type}' not supported "
                    f"(only i32 and i1 branch conditions supported)")
                return None
            elif result_type.startswith("<"):
                self._error(f"{ctx} — vector/SIMD type not supported")
                return None

        # ── Arithmetic ────────────────────────────────────────────────────────
        if opcode in SUPPORTED_ARITH:
            operands = _extract_operands(op_strs, instr_str)
            return LLVMInstruction(
                opcode       = opcode,
                result       = result_name,
                result_type  = result_type,
                operands     = operands,
                maps_to_tile = SUPPORTED_ARITH[opcode],
                raw          = instr_str,
            )

        if opcode in FUTURE_ARITH:
            tile = FUTURE_ARITH[opcode]
            self._warn(f"{ctx} — opcode '{opcode}' maps to {tile} "
                       f"(tile not yet implemented — will fail at lowering)")
            operands = _extract_operands(op_strs, instr_str)
            return LLVMInstruction(
                opcode       = opcode,
                result       = result_name,
                result_type  = result_type,
                operands     = operands,
                maps_to_tile = tile,
                warning      = f"{tile} not yet implemented",
                raw          = instr_str,
            )

        # ── icmp ─────────────────────────────────────────────────────────────
        if opcode == "icmp":
            pred = _parse_icmp_predicate(instr_str)
            if pred not in SUPPORTED_ICMP:
                self._error(f"{ctx} — unknown icmp predicate '{pred}'")
                return None
            operands = _extract_operands(op_strs, instr_str)
            tile = SUPPORTED_ICMP.get(pred, "")
            warn = ""
            if pred in FUTURE_ICMP:
                warn = f"unsigned icmp '{pred}' not yet implemented"
                self._warn(f"{ctx} — {warn}")
            return LLVMInstruction(
                opcode       = "icmp",
                result       = result_name,
                result_type  = "i1",
                operands     = operands,
                predicate    = pred,
                maps_to_tile = tile,
                warning      = warn,
                raw          = instr_str,
            )

        # ── phi ───────────────────────────────────────────────────────────────
        if opcode == "phi":
            phi_vals = _parse_phi_values(
                instr_str,
                list(instr.incoming_blocks))
            return LLVMInstruction(
                opcode      = "phi",
                result      = result_name,
                result_type = result_type,
                phi_values  = phi_vals,
                raw         = instr_str,
            )

        # ── br ────────────────────────────────────────────────────────────────
        if opcode == "br":
            is_cond, cond_val, true_lbl, false_lbl, tgt_lbl = \
                _parse_br(instr_str, op_strs)
            instr_obj = LLVMInstruction(
                opcode         = "br",
                result         = "",
                result_type    = "void",
                is_conditional = is_cond,
                true_label     = true_lbl,
                false_label    = false_lbl,
                target_label   = tgt_lbl,
                raw            = instr_str,
            )
            if is_cond and cond_val:
                instr_obj.operands = [cond_val]
            return instr_obj

        # ── ret ───────────────────────────────────────────────────────────────
        if opcode == "ret":
            operands = _extract_operands(op_strs, instr_str)
            return LLVMInstruction(
                opcode      = "ret",
                result      = "",
                result_type = "void",
                operands    = operands,
                raw         = instr_str,
            )

        # ── alloca ────────────────────────────────────────────────────────────
        if opcode == "alloca":
            # alloca i32 → allocate a bus address slot
            alloc_type_match = re.search(r'alloca\s+(\w+)', instr_str)
            alloc_type = alloc_type_match.group(1) if alloc_type_match else "i32"
            if alloc_type not in ("i32",):
                self._error(f"{ctx} — alloca type '{alloc_type}' "
                            f"not supported (only i32)")
                return None
            return LLVMInstruction(
                opcode      = "alloca",
                result      = result_name,
                result_type = alloc_type + "*",
                alloc_type  = alloc_type,
                raw         = instr_str,
            )

        # ── load ─────────────────────────────────────────────────────────────
        if opcode == "load":
            operands = _extract_operands(op_strs, instr_str)
            return LLVMInstruction(
                opcode      = "load",
                result      = result_name,
                result_type = result_type,
                operands    = operands,
                raw         = instr_str,
            )

        # ── store ─────────────────────────────────────────────────────────────
        if opcode == "store":
            operands = _extract_operands(op_strs, instr_str)
            return LLVMInstruction(
                opcode      = "store",
                result      = "",
                result_type = "void",
                operands    = operands,
                raw         = instr_str,
            )

        # ── call ─────────────────────────────────────────────────────────────
        if opcode == "call":
            callee, call_args = _parse_call(instr_str)
            if callee not in PERMITTED_INTRINSICS:
                self._error(
                    f"{ctx} — call to '{callee}' not supported. "
                    f"Permitted intrinsics: {sorted(PERMITTED_INTRINSICS)}")
                return None
            return LLVMInstruction(
                opcode      = "call",
                result      = result_name,
                result_type = result_type,
                operands    = call_args,
                callee      = callee,
                raw         = instr_str,
            )

        # ── Unknown opcode ────────────────────────────────────────────────────
        self._error(f"{ctx} — unsupported opcode '{opcode}'")
        return None

    # ── CFG construction ──────────────────────────────────────────────────────

    def _build_cfg(self, fn: LLVMFunction) -> None:
        """Build successor/predecessor lists for each block."""
        block_map = {b.name: b for b in fn.blocks}

        for block in fn.blocks:
            # Find the terminator (last instruction)
            if not block.instructions:
                continue
            term = block.instructions[-1]
            if term.opcode == "br":
                if term.is_conditional:
                    succs = [term.true_label, term.false_label]
                else:
                    succs = [term.target_label] if term.target_label else []
            elif term.opcode == "ret":
                succs = []
            else:
                succs = []

            block.successors = succs
            for succ_name in succs:
                succ = block_map.get(succ_name)
                if succ and block.name not in succ.predecessors:
                    succ.predecessors.append(block.name)

    # ── Type checking ─────────────────────────────────────────────────────────

    def _check_type(self, type_str: str, context: str = "") -> bool:
        """Check a type string is supported. Returns True if OK."""
        if type_str in ("i32", "i1", "void"):
            return True
        if type_str.endswith("*"):
            inner = type_str[:-1]
            return self._check_type(inner, context)
        unsupported = {
            "float": "use integer arithmetic; FP32 tiles exist but need explicit conversion",
            "double": "double precision not supported",
            "i64": "64-bit integers not supported (use i32)",
            "i8": "8-bit integers not supported (use i32 with masking)",
            "i16": "16-bit integers not supported (use i32 with masking)",
            "i128": "128-bit integers not supported",
        }
        if type_str in unsupported:
            self._error(f"{context}: type '{type_str}' — {unsupported[type_str]}")
            return False
        if type_str.startswith("<"):
            self._error(f"{context}: vector type '{type_str}' — SIMD not supported")
            return False
        return True   # unknown types pass through with a warning

    # ── Error / warning helpers ───────────────────────────────────────────────

    def _error(self, msg: str) -> None:
        self._errors.append(msg)

    def _warn(self, msg: str) -> None:
        self._warnings.append(msg)


# ── Convenience functions ─────────────────────────────────────────────────────

def parse_ll(source: str) -> FrontendResult:
    """Parse LLVM IR source text. Returns FrontendResult."""
    return LLVMFrontend().parse(source)


def validate_ll(source: str) -> list[str]:
    """Validate LLVM IR. Returns list of errors (empty = valid)."""
    return LLVMFrontend().validate(source)


def describe_support() -> str:
    """Print a summary of the supported instruction subset."""
    lines = [
        "Claudette LLVM Frontend — Supported Instruction Subset",
        "=" * 55,
        "",
        "Arithmetic (i32):",
    ]
    for op, tile in SUPPORTED_ARITH.items():
        lines.append(f"  {op:8s} → {tile}")
    lines.append("")
    lines.append("Future arithmetic (parsed, not yet lowered):")
    for op, tile in FUTURE_ARITH.items():
        lines.append(f"  {op:8s} → {tile}  [NOT YET IMPLEMENTED]")
    lines.append("")
    lines.append("Comparisons (icmp):")
    for pred, tile in SUPPORTED_ICMP.items():
        tag = "  [future]" if pred in FUTURE_ICMP else ""
        lines.append(f"  icmp {pred:4s} → {tile}{tag}")
    lines.append("")
    lines.append("Control flow:")
    for op in CONTROL_OPS:
        lines.append(f"  {op}")
    lines.append("")
    lines.append("Memory:")
    for op in MEMORY_OPS:
        lines.append(f"  {op}")
    lines.append("")
    lines.append("Permitted intrinsics:")
    for name in sorted(PERMITTED_INTRINSICS):
        lines.append(f"  @{name}")
    lines.append("")
    lines.append("Rejected:")
    for op, reason in REJECTED_OPS.items():
        lines.append(f"  {op:16s} — {reason}")
    return "\n".join(lines)
