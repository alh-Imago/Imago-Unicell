"""
llvm_ir_mapper.py — LLVM IR → Claudette Cell Mapper

Takes a LLVMFunction parse tree from llvm_frontend.py and lowers it
to a flat CellMapRecord list wrapped in a ProgramImage.

Mapping strategy
================

Each LLVM basic block becomes a pipeline segment. Registers within a
block map to bus addresses. The value produced by an instruction lives
at the output address of the last cell in its tile chain.

  LLVM construct        →  Claudette mechanism
  ─────────────────────────────────────────────────────────────────
  i32 register          →  bus address (32-bit, one address per bit in tiles)
  i1 register           →  single bus address (1-bit result)
  function argument     →  INPUT node (caller injects via bus_address)
  integer constant      →  constant cell (pre-loaded before run)

  add/sub/and/or/xor    →  tile instance (INT32_ADD_CLA etc.)
  icmp eq/ne            →  INT32_EQ tile + optional NOT
  icmp slt/sgt/sle/sge  →  INT32_SUB sign bit extraction
  icmp ne               →  NOT(INT32_EQ)

  br (conditional)      →  GS_SELECT cell: routes true or false branch
  br (unconditional)    →  direct address wiring (no cell needed)
  phi                   →  storage cell with LATCH mode
                            - receives value from each predecessor
                            - re-emits each tick (same as while loop variable)
  ret                   →  designates output address in ProgramImage

Block ordering
==============

Blocks are processed in reverse-post-order (RPO) — entry block first,
then each block after all its predecessors have been processed. This
matches the natural data flow direction. Back edges (loop back-edges
for phi nodes) are handled by the storage cell mechanism — the storage
cell holds the previous iteration's value and re-emits it.

Phi node implementation
=======================

A phi node [ %a, %entry ], [ %result, %loop ] means:
  - on first entry (from %entry): value = %a
  - on each loop iteration (from %loop): value = %result

This maps to the while-loop storage cell model:
  - allocate a storage cell (GS_LATCH | LOOP_MODE)
  - the storage cell's input listens on a shared "phi input" address
  - each predecessor block writes to that address before branching
  - the storage cell holds the last value and re-emits it

Address allocation
==================

32-bit values use a SINGLE representative address — the output of the
tile that produced them. The tile handles the full 32-bit computation
internally. This matches the existing Int32 tile model where in_a[0]
through in_a[31] are individual bit addresses but the compiler/mapper
works with the representative address (in_a[0]).

Usage
=====

  from llvm_frontend import parse_ll
  from llvm_ir_mapper import LLVMIRMapper

  result = parse_ll(ll_source)
  if not result.ok:
      print(result.errors)
  else:
      mapper = LLVMIRMapper()
      program = mapper.lower(result.functions[0])
      print(program)
      output = program.run(inputs={"a": 5, "b": 3})
      print(output)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional, Any

from llvm_frontend import (
    LLVMFunction, LLVMBlock, LLVMInstruction, LLVMValue,
    SUPPORTED_ARITH, SUPPORTED_ICMP, FUTURE_ARITH,
)


# ── Tile name → TileLibrary name mapping ─────────────────────────────────────

TILE_MAP = {
    "INT32_ADD_CLA":          "INT32_ADD_CLA",
    "INT32_SUB":              "INT32_SUB",
    "INT32_AND":              "INT32_AND",
    "INT32_OR":               "INT32_OR",
    "INT32_XOR":              "INT32_XOR",
    "INT32_EQ":               "INT32_EQ",
    # icmp sign-bit constructions use INT32_SUB + sign bit extraction
    "SIGN_BIT(INT32_SUB(a,b))": "INT32_SUB",
    "SIGN_BIT(INT32_SUB(b,a))": "INT32_SUB",
    "NOT(INT32_EQ)":          "INT32_EQ",
    "NOT(SIGN_BIT(INT32_SUB(b,a)))": "INT32_SUB",
    "NOT(SIGN_BIT(INT32_SUB(a,b)))": "INT32_SUB",
}


# ── Value environment ─────────────────────────────────────────────────────────

class ValueEnv:
    """
    Maps LLVM register names to Claudette representative addresses.
    A "representative address" is the bus address where the value lives —
    for a 32-bit int tile, it's in_a[0] of the tile's output port.
    """

    def __init__(self):
        self._map: dict[str, int] = {}         # name → bus address
        self._multi: dict[str, list] = {}      # name → [bit0_addr, ...] for 32-bit

    def set(self, name: str, addr: int,
            bit_addresses: list = None) -> None:
        self._map[name] = addr
        if bit_addresses:
            self._multi[name] = bit_addresses

    def get(self, name: str) -> Optional[int]:
        return self._map.get(name)

    def get_bits(self, name: str) -> Optional[list]:
        return self._multi.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._map


# ── Lowered instruction ────────────────────────────────────────────────────────

@dataclass
class LoweredInstr:
    """One lowered instruction — a tile placement or cell record."""
    llvm_result: str       # original LLVM register name (or "")
    result_addr: int       # bus address where result lives
    result_bits: list      # full 32-bit addresses if available
    records:     list      # CellMapRecord list
    tile_name:   str = ""  # tile used (or "" for raw cells)
    depth:       int = 0   # pipeline depth of this instruction


# ── LLVMIRMapper ──────────────────────────────────────────────────────────────

class LLVMIRMapper:
    """
    Lowers a parsed LLVM IR function to a Claudette ProgramImage.

    Two-pass process:
      Pass 1: topological block ordering, phi node pre-allocation
      Pass 2: instruction lowering (tile placement, cell wiring)
    """

    def __init__(self, tile_library=None):
        """
        tile_library: TileLibrary or CombinedLibrary instance.
                      If None, a default TileLibrary is created.
        """
        if tile_library is None:
            from fp_tiles import TileLibrary
            tile_library = TileLibrary()
        self._lib = tile_library

    def lower(self, fn: LLVMFunction) -> "ProgramImage":
        """
        Lower a LLVMFunction to a ProgramImage.

        Returns a ProgramImage with:
          - All compiled cell records
          - Named ranges for function arguments (INPUT) and return value (OUTPUT)
          - MODELS NEEDED populated from tiles used
        """
        from controller import CellMapRecord
        from gate_states import GS_PASS, GS_NOT, GS_LATCH, LOOP_MODE
        from fp_tiles import TilePlacer

        self._records: list = []
        self._env     = ValueEnv()
        self._alloc_base = 0x300000   # base address for mapper allocations
        self._next_addr  = self._alloc_base
        self._tiles_used: set = set()
        self._errors:  list = []
        self._warnings:list = []
        self._phi_storage: dict = {}   # register name → storage cell addr

        # ── Pass 1: allocate addresses for function arguments ─────────────────
        input_ranges = []
        for arg_name, arg_type in fn.args:
            addr = self._alloc()
            self._env.set(arg_name, addr)
            input_ranges.append((arg_name, addr, arg_type))

        # ── Pass 1b: pre-allocate phi storage cells ───────────────────────────
        for block in fn.blocks:
            for instr in block.instructions:
                if instr.opcode == "phi" and instr.result:
                    # Allocate a storage cell for this phi
                    phi_addr = self._alloc()
                    self._phi_storage[instr.result] = phi_addr
                    self._env.set(instr.result, phi_addr)

        # ── Pass 2: lower blocks in topological order ─────────────────────────
        ordered_blocks = self._topo_order(fn)
        output_addr = None
        output_bits = []

        for block in ordered_blocks:
            block_result = self._lower_block(block, fn)
            if block_result is not None:
                output_addr, output_bits = block_result

        # ── Build ProgramImage ────────────────────────────────────────────────
        from program_image import ProgramImage, NamedRange, RangeKind

        ranges = []

        # Input ranges (function arguments)
        for arg_name, addr, arg_type in input_ranges:
            ranges.append(NamedRange(
                name        = arg_name,
                bus_address = addr,
                width       = 32 if arg_type == "i32" else 1,
                kind        = RangeKind.INPUT,
                description = f"LLVM arg %{arg_name}: {arg_type}",
            ))

        # Output range (ret value)
        if output_addr is not None:
            if output_bits:
                ranges.append(NamedRange(
                    name          = "output",
                    bus_address   = output_bits[0],
                    width         = len(output_bits),
                    kind          = RangeKind.OUTPUT,
                    description   = f"LLVM ret value",
                    bit_addresses = output_bits,
                ))
            else:
                ranges.append(NamedRange(
                    name        = "output",
                    bus_address = output_addr,
                    width       = 1,
                    kind        = RangeKind.OUTPUT,
                    description = "LLVM ret value (1-bit)",
                ))

        # Phi storage cells as ACCUMULATOR ranges
        for reg_name, phi_addr in self._phi_storage.items():
            ranges.append(NamedRange(
                name        = f"phi_{reg_name}",
                bus_address = phi_addr,
                width       = 1,
                kind        = RangeKind.ACCUMULATOR,
                description = f"phi storage for %{reg_name}",
            ))

        img = ProgramImage(
            name       = fn.name,
            records    = self._records,
            ranges     = ranges,
            models     = sorted(self._tiles_used),
        )

        if self._errors:
            print(f"[LLVM_MAPPER] Lowering errors for '{fn.name}':")
            for e in self._errors:
                print(f"  ERROR: {e}")

        if self._warnings:
            for w in self._warnings:
                print(f"[LLVM_MAPPER] WARN: {w}")

        print(f"[LLVM_MAPPER] '{fn.name}' lowered: "
              f"{len(self._records)} cells, "
              f"{len(ranges)} named ranges, "
              f"tiles: {sorted(self._tiles_used)}")

        return img

    # ── Block lowering ────────────────────────────────────────────────────────

    def _lower_block(self, block: LLVMBlock, fn: LLVMFunction):
        """
        Lower one basic block.
        Returns (output_addr, output_bits) if a ret was encountered, else None.
        """
        for instr in block.instructions:
            result = self._lower_instr(instr, block, fn)
            if instr.opcode == "ret" and result is not None:
                return result
        return None

    # ── Instruction lowering ──────────────────────────────────────────────────

    def _lower_instr(self, instr: LLVMInstruction,
                     block: LLVMBlock,
                     fn: LLVMFunction):
        """Lower one instruction. Returns (addr, bits) for ret, else None."""
        op = instr.opcode

        # ── phi ──────────────────────────────────────────────────────────────
        if op == "phi":
            return self._lower_phi(instr, block, fn)

        # ── Arithmetic: tile-based ────────────────────────────────────────────
        if op in SUPPORTED_ARITH:
            return self._lower_arith(instr)

        if op in FUTURE_ARITH:
            self._warn(f"opcode '{op}' → tile {FUTURE_ARITH[op]} not yet "
                       f"implemented — result of %{instr.result} is undefined")
            # Allocate an address so downstream instructions don't crash
            addr = self._alloc()
            self._env.set(instr.result, addr)
            return None

        # ── icmp ──────────────────────────────────────────────────────────────
        if op == "icmp":
            return self._lower_icmp(instr)

        # ── br ────────────────────────────────────────────────────────────────
        if op == "br":
            return self._lower_br(instr, block, fn)

        # ── ret ───────────────────────────────────────────────────────────────
        if op == "ret":
            return self._lower_ret(instr)

        # ── alloca ────────────────────────────────────────────────────────────
        if op == "alloca":
            addr = self._alloc()
            self._env.set(instr.result, addr)
            return None

        # ── load ─────────────────────────────────────────────────────────────
        if op == "load":
            return self._lower_load(instr)

        # ── store ────────────────────────────────────────────────────────────
        if op == "store":
            return self._lower_store(instr)

        # ── call (permitted intrinsics) ───────────────────────────────────────
        if op == "call":
            return self._lower_intrinsic(instr)

        return None

    # ── Arithmetic lowering ───────────────────────────────────────────────────

    def _lower_arith(self, instr: LLVMInstruction):
        """Lower add/sub/and/or/xor via tile placement."""
        from fp_tiles import TilePlacer

        tile_name = SUPPORTED_ARITH[instr.opcode]
        try:
            tile = self._lib.get(tile_name)
        except KeyError:
            self._error(f"tile '{tile_name}' not in library")
            return None

        base = self._alloc_block(tile.metadata.cell_count * 4)
        placer = TilePlacer(base_address=base)
        records, in_a, in_b, out = placer.place(tile)
        self._records.extend(records)
        self._tiles_used.add(tile_name)

        # Wire operand A
        op_a = self._resolve_value(instr.operands[0])
        if op_a is not None:
            self._wire_to(op_a, in_a[0])

        # Wire operand B
        if len(instr.operands) > 1:
            op_b = self._resolve_value(instr.operands[1])
            if op_b is not None:
                self._wire_to(op_b, in_b[0])

        # Result lives at out[0]
        result_addr = out[0]
        self._env.set(instr.result, result_addr, out)
        return result_addr, out

    # ── icmp lowering ─────────────────────────────────────────────────────────

    def _lower_icmp(self, instr: LLVMInstruction):
        """Lower icmp via appropriate tile expression."""
        from fp_tiles import TilePlacer
        from controller import CellMapRecord
        from gate_states import GS_NOT

        pred = instr.predicate
        tile_expr = SUPPORTED_ICMP.get(pred, "")

        op_a_addr = self._resolve_value(instr.operands[0])
        op_b_addr = self._resolve_value(instr.operands[1]) if len(instr.operands) > 1 else None

        # icmp eq → INT32_EQ tile
        if pred == "eq":
            return self._place_eq_tile(instr, op_a_addr, op_b_addr, invert=False)

        # icmp ne → NOT(INT32_EQ)
        if pred == "ne":
            return self._place_eq_tile(instr, op_a_addr, op_b_addr, invert=True)

        # icmp slt → sign bit of (a - b)
        if pred == "slt":
            return self._place_sub_sign(instr, op_a_addr, op_b_addr, invert=False)

        # icmp sgt → sign bit of (b - a)
        if pred == "sgt":
            return self._place_sub_sign(instr, op_b_addr, op_a_addr, invert=False)

        # icmp sle → NOT(sign bit of (b - a))  [NOT sgt]
        if pred == "sle":
            return self._place_sub_sign(instr, op_b_addr, op_a_addr, invert=True)

        # icmp sge → NOT(sign bit of (a - b))  [NOT slt]
        if pred == "sge":
            return self._place_sub_sign(instr, op_a_addr, op_b_addr, invert=True)

        self._warn(f"icmp predicate '{pred}' not yet lowered")
        addr = self._alloc()
        self._env.set(instr.result, addr)
        return addr, [addr]

    def _place_eq_tile(self, instr, op_a_addr, op_b_addr, invert: bool):
        """Place INT32_EQ tile, optionally invert result."""
        from fp_tiles import TilePlacer
        from controller import CellMapRecord
        from gate_states import GS_NOT

        tile = self._lib.get("INT32_EQ")
        base = self._alloc_block(tile.metadata.cell_count * 4)
        placer = TilePlacer(base_address=base)
        records, in_a, in_b, out = placer.place(tile)
        self._records.extend(records)
        self._tiles_used.add("INT32_EQ")

        if op_a_addr: self._wire_to(op_a_addr, in_a[0])
        if op_b_addr: self._wire_to(op_b_addr, in_b[0])

        eq_out = out[0]   # 1 = equal, 0 = not equal

        if invert:
            # NOT cell after EQ output
            not_addr = self._alloc()
            self._records.append(CellMapRecord(GS_NOT, eq_out, not_addr))
            result_addr = not_addr
        else:
            result_addr = eq_out

        self._env.set(instr.result, result_addr)
        return result_addr, [result_addr]

    def _place_sub_sign(self, instr, op_a_addr, op_b_addr, invert: bool):
        """
        Sign bit of (a - b): place INT32_SUB, extract bit 31 (MSB).
        If invert: add NOT after sign bit.
        """
        from fp_tiles import TilePlacer
        from controller import CellMapRecord
        from gate_states import GS_PASS, GS_NOT

        tile = self._lib.get("INT32_SUB")
        base = self._alloc_block(tile.metadata.cell_count * 4)
        placer = TilePlacer(base_address=base)
        records, in_a, in_b, out = placer.place(tile)
        self._records.extend(records)
        self._tiles_used.add("INT32_SUB")

        if op_a_addr: self._wire_to(op_a_addr, in_a[0])
        if op_b_addr: self._wire_to(op_b_addr, in_b[0])

        # Sign bit = out[31] (MSB of 32-bit result)
        sign_bit_addr = out[31] if len(out) >= 32 else out[-1]

        if invert:
            not_addr = self._alloc()
            self._records.append(CellMapRecord(GS_NOT, sign_bit_addr, not_addr))
            result_addr = not_addr
        else:
            result_addr = sign_bit_addr

        self._env.set(instr.result, result_addr)
        return result_addr, [result_addr]

    # ── Phi lowering ─────────────────────────────────────────────────────────

    def _lower_phi(self, instr: LLVMInstruction,
                   block: LLVMBlock, fn: LLVMFunction):
        """
        Lower phi node to a storage cell.

        The storage cell (GS_LATCH | LOOP_MODE) holds the last value
        written to its input address and re-emits it each tick.
        Each predecessor block writes its value to the phi input address
        before branching. The storage cell's output is the phi result.
        """
        from controller import CellMapRecord
        from gate_states import GS_PASS, GS_LATCH, LOOP_MODE

        phi_addr   = self._phi_storage.get(instr.result)
        if phi_addr is None:
            phi_addr = self._alloc()
            self._phi_storage[instr.result] = phi_addr

        # Phi input address — predecessors write here
        phi_input  = self._alloc()

        # Storage cell: listens on phi_input, holds value, re-emits to phi_addr
        self._records.append(CellMapRecord(
            GS_LATCH | LOOP_MODE, phi_input, phi_addr))

        # Wire each incoming value to phi_input
        # Values from predecessors that have already been lowered
        for val, from_block in instr.phi_values:
            src_addr = self._resolve_value(val)
            if src_addr is not None:
                # PASS cell: when from_block produces value, feed to phi_input
                pass_addr = self._alloc()
                self._records.append(CellMapRecord(GS_PASS, src_addr, phi_input))

        self._env.set(instr.result, phi_addr)
        return None

    # ── Branch lowering ───────────────────────────────────────────────────────

    def _lower_br(self, instr: LLVMInstruction,
                  block: LLVMBlock, fn: LLVMFunction):
        """
        Lower branch instruction.

        Conditional: GS_SELECT routes to true or false successor.
        Unconditional: no cells needed (direct address flow).
        """
        from controller import CellMapRecord
        from gate_states import GS_SELECT, GS_PASS

        if not instr.is_conditional:
            # Unconditional — no cells needed
            return None

        # Conditional: wire condition to SELECT cell
        cond_addr = None
        if instr.operands:
            cond_addr = self._resolve_value(instr.operands[0])

        # SELECT cell: cond=1 → true branch, cond=0 → false branch
        # GS_SELECT routes input to one of two outputs based on condition
        if cond_addr is not None:
            true_addr  = self._alloc()
            false_addr = self._alloc()
            self._records.append(CellMapRecord(
                GS_SELECT, cond_addr, true_addr))
            # Store branch routing in env for downstream phi resolution
            self._env.set(f"__branch_{block.name}_true",  true_addr)
            self._env.set(f"__branch_{block.name}_false", false_addr)

        return None

    # ── Return lowering ───────────────────────────────────────────────────────

    def _lower_ret(self, instr: LLVMInstruction):
        """Lower ret — return the address of the return value."""
        if not instr.operands:
            return None, []

        ret_val = instr.operands[0]
        addr = self._resolve_value(ret_val)
        if addr is None:
            return None, []

        bits = self._env.get_bits(ret_val.name) if ret_val.name else []
        return addr, bits or [addr]

    # ── Load / Store lowering ─────────────────────────────────────────────────

    def _lower_load(self, instr: LLVMInstruction):
        """Lower load: read from alloca'd address."""
        from controller import CellMapRecord
        from gate_states import GS_PASS

        if not instr.operands:
            return None

        ptr_addr = self._resolve_value(instr.operands[0])
        if ptr_addr is None:
            return None

        # Load: PASS cell reads from the pointer address
        load_out = self._alloc()
        self._records.append(CellMapRecord(GS_PASS, ptr_addr, load_out))
        self._env.set(instr.result, load_out)
        return load_out, [load_out]

    def _lower_store(self, instr: LLVMInstruction):
        """Lower store: write value to alloca'd address."""
        from controller import CellMapRecord
        from gate_states import GS_PASS

        if len(instr.operands) < 2:
            return None

        val_addr = self._resolve_value(instr.operands[0])
        ptr_addr = self._resolve_value(instr.operands[1])

        if val_addr is not None and ptr_addr is not None:
            # PASS cell: value → storage address
            self._records.append(CellMapRecord(GS_PASS, val_addr, ptr_addr))

        return None

    # ── Intrinsic lowering ────────────────────────────────────────────────────

    def _lower_intrinsic(self, instr: LLVMInstruction):
        """Lower permitted LLVM intrinsic calls."""
        self._warn(f"intrinsic '{instr.callee}' lowered as PASS (stub)")
        if instr.operands:
            src = self._resolve_value(instr.operands[0])
            if src and instr.result:
                from controller import CellMapRecord
                from gate_states import GS_PASS
                out = self._alloc()
                self._records.append(CellMapRecord(GS_PASS, src, out))
                self._env.set(instr.result, out)
                return out, [out]
        return None

    # ── Wiring helpers ────────────────────────────────────────────────────────

    def _wire_to(self, src_addr: int, dst_addr: int) -> None:
        """Add a PASS cell connecting src → dst."""
        from controller import CellMapRecord
        from gate_states import GS_PASS
        self._records.append(CellMapRecord(GS_PASS, src_addr, dst_addr))

    def _resolve_value(self, val: "LLVMValue") -> Optional[int]:
        """
        Resolve an LLVMValue to a bus address.
        Constants: allocate a constant cell pre-loaded with the value.
        Registers: look up in environment.
        """
        if val is None:
            return None

        if val.is_const:
            return self._make_constant(val.const_val)

        if val.name and val.name in self._env:
            return self._env.get(val.name)

        # Try to find by name in env
        if val.name:
            addr = self._env.get(val.name)
            if addr:
                return addr

        # Allocate placeholder (value not yet defined — forward reference)
        addr = self._alloc()
        if val.name:
            self._env.set(val.name, addr)
        return addr

    def _make_constant(self, value: int) -> int:
        """
        Create a constant cell: a LATCH cell pre-loaded with the value.
        The constant is always available on the bus.
        """
        from controller import CellMapRecord
        from gate_states import GS_LATCH
        addr = self._alloc()
        # LATCH cell holds the constant value
        # The caller must pre-load this address before run()
        self._records.append(CellMapRecord(GS_LATCH, addr, addr))
        return addr

    # ── Address allocation ────────────────────────────────────────────────────

    def _alloc(self) -> int:
        addr = self._next_addr
        self._next_addr += 1
        return addr

    def _alloc_block(self, size: int) -> int:
        addr = self._next_addr
        self._next_addr += size
        return addr

    # ── Topological ordering ──────────────────────────────────────────────────

    def _topo_order(self, fn: LLVMFunction) -> list:
        """
        Return blocks in reverse-post-order (RPO).
        Entry block first, then each block after all predecessors.
        Back edges (loop back-edges) are visited in natural order.
        """
        if not fn.blocks:
            return []

        visited = set()
        order   = []

        def dfs(block_name: str):
            if block_name in visited:
                return
            visited.add(block_name)
            block = fn.block(block_name)
            if block is None:
                return
            for succ in block.successors:
                if succ not in visited:
                    dfs(succ)
            order.append(block)

        dfs(fn.entry_block)

        # Any remaining blocks (disconnected — shouldn't happen but be safe)
        for block in fn.blocks:
            if block.name not in visited:
                order.append(block)

        order.reverse()   # RPO
        return order

    # ── Error helpers ─────────────────────────────────────────────────────────

    def _error(self, msg: str) -> None:
        self._errors.append(msg)

    def _warn(self, msg: str) -> None:
        self._warnings.append(msg)


# ── Convenience function ──────────────────────────────────────────────────────

def compile_ll(ll_source: str,
               tile_library=None) -> tuple:
    """
    Parse and lower LLVM IR source to a ProgramImage list.

    Returns (images, errors):
      images: list of ProgramImage (one per function in the module)
      errors: list of error strings (empty = success)
    """
    from llvm_frontend import LLVMFrontend
    fe = LLVMFrontend()
    result = fe.parse(ll_source)

    if not result.ok:
        return [], result.errors

    mapper = LLVMIRMapper(tile_library=tile_library)
    images = []
    errors = list(result.warnings)

    for fn in result.functions:
        try:
            img = mapper.lower(fn)
            images.append(img)
        except Exception as e:
            errors.append(f"Lowering '{fn.name}' failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

    return images, errors
