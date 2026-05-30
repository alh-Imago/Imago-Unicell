"""
unicell.py — UniCell VM implementation.

Ground truth: fpga/verilog/unicell.v (silicon-validated, iCEBreaker 2026-05-17).

Two-arrival model (all cells, all topologies):
  First arrival at input_address  -> stored in a_data, a_arrived set, NO output
  Second arrival at input_address -> fires gate tree on (a_data, arrival_value)
                                     a_arrived cleared, output emitted

NOT(A) = NOR(A,A): compiler emits Y-formation so A arrives twice at same address.
latch_in (GS_LATCH_IN / cell_type=latch): a_arrived stays set after fire —
  single arrival fires (memory/counter mode).
edge_mode (GS_EDGE_MODE): fires on data transition, single arrival.

Address width: VM always uses full 32-bit addresses. The iCEBreaker Verilog
narrows to 16 bits for timing reasons only — that is a hardware constraint,
not an architectural one. Do not change the 0xFFFFFFFF masks here.

Retired from this file:
  FUNCTION_LOAD_PATTERN and the LOAD_PATTERN config protocol
  input_b_address, receive_b(), _input_b, _b_address
  _sync_buf (v1 SYNC_WAIT compat)
  output_address_alt (SELECT cells retired)
  latch_mode (replaced by cell_type=latch)
  storage_mode (replaced by cell_type=latch + PASS topology)
  addr_latch, _config_upper (64-bit address model retired)
  broadcast (GS_BROADCAST not in Verilog)
  sync_wait as explicit flag (two-arrival is default, no flag)
  loop_back_en/src/dst (simplified to single loop_back bool, bit 31)
  fall_edge (odd_phase is internal to Verilog)
  out_posedge (internal to Verilog)
  _config_mode, _config_step (LOAD_PATTERN config protocol)
  _execute_nor_gates() v1 single-input path
  SELECT cell routing (GS_SELECT retired)
"""

import imago_log
from typing import Optional
from gate_states import (GS_LATCH_IN, GS_INVERT_OUT_BIT, GS_DTYPE_MASK, GS_DTYPE_SHIFT,
                          GS_PRIORITY, GS_TRACE, GS_BREAKPOINT, GS_ONE_SHOT, GS_LOOP_BACK,
                          GS_EDGE_MODE, GS_CTYPE_MASK, GS_CTYPE_SHIFT)


# ── ECC (SECDED) helpers — RESERVED, NOT ACTIVE ──────────────────────────────
#
# ECC field is on the command bus (bits 22-31), not the data bus.
# Data bus is 32 bits. There is no 39-bit packet.
# Pre-Hamming: XOR check on cmd_bus[31:22] for bridge transaction integrity.
# Full Hamming SECDED deferred to production silicon.

def _compute_ecc(value: int) -> int:
    """ECC — RESERVED. Returns 0 (passthrough)."""
    return 0

def _verify_ecc(value: int, check: int) -> tuple:
    """ECC — RESERVED. Returns (value, False, False) passthrough."""
    return value, False, False

class ECCError(RuntimeError):
    """Raised when a double-bit ECC error is detected."""
    pass


# ── UniCell ───────────────────────────────────────────────────────────────────

# Retired constants — kept to prevent ImportError in legacy code
FUNCTION_LOAD_PATTERN = None  # retired v2.2

class UniCell:
    """
    One UniCell — the fundamental unit of the Imago spatial computing fabric.

    Matches fpga/verilog/unicell.v exactly. See docs/CELL_INTERNALS.md.

    Configuration:
      CMD_RECONFIGURE: loads a single 32-bit cmd_latch word.
      CMD_SET_INPUT_ADDR:  sets input_address independently.
      CMD_SET_OUTPUT_ADDR: sets output_address independently.
      CMD_FREEZE / CMD_RELEASE: disarm / re-arm.

    cmd_latch fields (all unpacked into named attributes at configure time):
      topology   [9:0]   — NOR gate wiring
      edge_mode  [10]    — 0=two-arrival, 1=edge-triggered
      dtype      [24:23] — output type (NUMERIC/SIGNED/ALPHA/DATETIME)
      cell_type  [26:25] — 00=standard 01=latch 10=posedge 11=negedge
      latch_in   [26]    — derived from cell_type: a_arrived stays set
      priority   [27]    — schedule first each tick
      trace      [28]    — record every fire to Ward
      breakpoint [29]    — halt array on fire
      one_shot   [30]    — fire once then disarm
      loop_back  [31]    — feed output back as next a_data

    Two-arrival model:
      First arrival  -> a_data = value, a_arrived = True, no output
      Second arrival -> gate_tree(a_data, value), output emitted, a_arrived = False
      latch_in=True  -> a_arrived stays True (single arrival fires, memory mode)
      edge_mode=True -> fires on 0->1 or 1->0 transition, single arrival

    Note on start_flag:
      start_flag is controlled directly (not packed into cmd_latch in the VM).
      Set True by configure(). Cleared by freeze() or one_shot disarm.
    """

    def __init__(self, address: int):
        self.address: int = address

        # ── Address registers (32-bit — VM architectural width) ───────────────
        self.input_address:  int = address        # preset to CELL_ID (matches Verilog)
        self.output_address: int = address + 1    # preset to CELL_ID+1

        # ── cmd_latch fields ──────────────────────────────────────────────────
        self.cmd_latch:  int  = 0      # raw 32-bit word (auth_mask bits always 0 here)
        self.topology:   int  = 0      # bits 9-0
        self.edge_mode:  bool = False  # bit 10
        self.dtype:      int  = 0      # bits 24-23 (0=NUMERIC 1=SIGNED 2=ALPHA 3=DATETIME)
        self.cell_type:  int  = 0      # bits 26-25 (0=standard 1=latch 2=posedge 3=negedge)
        self.latch_in:   bool = False  # derived: cell_type == 1 (latch)
        self.invert_out: bool = False  # derived: cell_type == 3 (negedge)
        self.priority:   bool = False  # bit 27
        self.trace_en:   bool = False  # bit 28
        self.breakpoint: bool = False  # bit 29
        self.one_shot:   bool = False  # bit 30
        self.loop_back:  bool = False  # bit 31

        # ── Control ───────────────────────────────────────────────────────────
        self.start_flag: bool = False  # armed — set by configure(), cleared by freeze()
        self.frozen:     bool = False

        # ── Two-arrival state ─────────────────────────────────────────────────
        self.a_arrived: bool = False   # first arrival stored
        self.a_data:    int  = 0       # value from first arrival
        self.prev_data: int  = 0       # last seen bus value (edge_mode detection)

        # ── Output buffer ─────────────────────────────────────────────────────
        # Cell computes on second arrival -> result held here -> published next tick.
        # Matches Verilog out_buf_valid / out_buf_data / odd_phase drain.
        self._output_buf: Optional[tuple] = None   # (output_address, value, ecc_check)

        # ── One-shot disarm tracking ──────────────────────────────────────────
        self._one_shot_fired: bool = False

        # ── ECC (stub) ────────────────────────────────────────────────────────
        self.ecc_enabled:      bool = False
        self.ecc_corrections:  int  = 0
        self.ecc_double_errors: int = 0

        # ── PTT reference (OS layer — set by controller.load_map) ─────────────
        self._ptt_ref = None

        # ── Breakpoint flag (checked by array after tick) ─────────────────────
        self._breakpoint_triggered: bool = False

    # ── Configuration ─────────────────────────────────────────────────────────

    def configure(self, cmd_latch: int,
                  input_addr:  Optional[int] = None,
                  output_addr: Optional[int] = None) -> None:
        """
        Configure this cell from a 32-bit cmd_latch word.

        Equivalent to CMD_RECONFIGURE on the hardware command bus.
        Auth_mask bits (21-11) are ignored in the VM — always zero in Python words.

        Optionally set input_address and output_address at the same time
        (mirrors CMD_SET_INPUT_ADDR / CMD_SET_OUTPUT_ADDR).
        """
        from gate_states import (
            TOPO_MASK, GS_EDGE_MODE,
            GS_DTYPE_SHIFT, GS_DTYPE_MASK,
            GS_CTYPE_SHIFT, GS_CTYPE_MASK,
            GS_PRIORITY, GS_TRACE, GS_BREAKPOINT,
            GS_ONE_SHOT, GS_LOOP_BACK,
        )
        self.cmd_latch  = cmd_latch & 0xFFFFFFFF

        # topology: bits 9-0
        self.topology   = cmd_latch & TOPO_MASK

        # edge_mode: bit 10
        self.edge_mode  = bool(cmd_latch & GS_EDGE_MODE)

        # dtype: bits 24-23
        self.dtype      = (cmd_latch & GS_DTYPE_MASK) >> GS_DTYPE_SHIFT

        # cell_type: derived from two separate bits (v2.3)
        #   bit 26 = latch_in   (was incorrectly called ctype bit 1)
        #   bit 25 = invert_out (was incorrectly called ctype bit 0)
        self.latch_in   = bool(cmd_latch & GS_LATCH_IN)       # bit 26
        self.invert_out = bool(cmd_latch & GS_INVERT_OUT_BIT)  # bit 25
        # cell_type kept for legacy compatibility — 0=standard, 1=latch
        self.cell_type  = (1 if self.latch_in else 0)

        # scheduling / debug flags
        self.priority   = bool(cmd_latch & GS_PRIORITY)
        self.trace_en   = bool(cmd_latch & GS_TRACE)
        self.breakpoint = bool(cmd_latch & GS_BREAKPOINT)

        # fire control
        self.one_shot   = bool(cmd_latch & GS_ONE_SHOT)
        self.loop_back  = bool(cmd_latch & GS_LOOP_BACK)

        # addresses (optional — separate CMD_SET_* commands)
        if input_addr is not None:
            self.input_address  = input_addr  & 0xFFFFFFFF
        if output_addr is not None:
            self.output_address = output_addr & 0xFFFFFFFF

        # arm the cell (CMD_RECONFIGURE sets start_flag)
        self.start_flag    = True
        self.frozen        = False
        self._one_shot_fired = False
        self.a_arrived     = False

    def freeze(self) -> None:
        """CMD_FREEZE — disarm, suppress output."""
        self.frozen    = True
        self.start_flag = False
        self._output_buf = None

    def release(self) -> None:
        """CMD_RELEASE — re-arm."""
        self.frozen    = False
        self.start_flag = True

    def set_input_addr(self, addr: int) -> None:
        """CMD_SET_INPUT_ADDR."""
        self.input_address = addr & 0xFFFFFFFF

    def set_output_addr(self, addr: int) -> None:
        """CMD_SET_OUTPUT_ADDR."""
        self.output_address = addr & 0xFFFFFFFF

    # ── Data reception ────────────────────────────────────────────────────────

    def receive(self, value: int, ecc_check: int = 0) -> None:
        """
        Deliver a value to this cell's input_address.

        Two-arrival model:
          Call 1: stores value in a_data, sets a_arrived. No output.
          Call 2: triggers tick with (a_data, value). Clears a_arrived.

        latch_in=True: a_arrived stays set — every call triggers.
        edge_mode=True: transition detection, always single-arrival.

        ecc_check: reserved (ECC stub). Pass 0.
        """
        if not self.start_flag or self.frozen:
            return
        if self.ecc_enabled and ecc_check:
            value, _, _ = _verify_ecc(value, ecc_check)
        value = value & 0xFFFFFFFF

        if self.edge_mode:
            # Edge mode: single arrival, fires on transition
            self._edge_receive(value)
            return

        if not self.a_arrived:
            # First arrival — store, do not fire
            self.a_data    = value
            self.a_arrived = True
        else:
            # Second arrival — fire
            self._fire(self.a_data, value)
            if not self.latch_in:
                self.a_arrived = False

    def _edge_receive(self, value: int) -> None:
        """Handle edge-mode single arrival."""
        prev = self.prev_data
        self.prev_data = value & 1
        if self.invert_out:
            # negedge: 1->0 transition
            if prev and not (value & 1):
                self._fire(value, 0)
        else:
            # posedge: 0->1 transition
            if not prev and (value & 1):
                self._fire(value, 0)

    # ── Gate tree and fire ────────────────────────────────────────────────────

    def _fire(self, a: int, b: int) -> None:
        """
        Run the NOR gate tree on (a, b) and load the output buffer.
        Matches the combinatorial gate tree in unicell.v exactly.
        """
        if self._one_shot_fired and self.one_shot:
            return

        result = self._execute_nor_gates(a, b)

        if self.invert_out:
            result = (~result) & 1

        if self.loop_back:
            # Feed result back: becomes a_data for next trigger
            self.a_data = result

        if self.one_shot:
            self._one_shot_fired = True
            self.start_flag = False

        if self.breakpoint:
            self._breakpoint_triggered = True
            imago_log.info(f"[BREAKPOINT] Cell {self.address:#010x} fired — value={result}")

        if self.trace_en:
            imago_log.info(f"[TRACE] {self.address:#010x}: topo={self.topology:#05x} "
                           f"a={a} b={b} result={result}")

        val, chk = self._ecc_emit(result)

        # PTT bus interception (sentry cells write to reserved range 0xFFE00000+)
        if self.output_address >= 0xFFE00000:
            if self._ptt_ref is not None:
                self._ptt_ref.bus_tick(self.output_address, val)
            return

        self._output_buf = (self.output_address, val, chk)

    def _execute_nor_gates(self, a: int, b: int) -> int:
        """
        10-gate NOR tree with two single-bit inputs. Matches unicell.v exactly.

        The Verilog operates entirely on single bits: bus_data[0], a_data[0].
        Gate tree is 1-bit in, 1-bit out. Bit 0 is extracted from a and b.
        Result is always 0 or 1.

        Topology (bits 9-0): bit N set = gate N active (NOR), clear = bypass.
        Gate wiring (identical to unicell.v combinatorial block):
          g0 = NOR(a,a) = NOT(A)
          g1 = NOR(b,b) = NOT(B)
          g2 = NOR(g0,g1) = AND(A,B)
          g3 = NOR(g2,b)
          g4 = NOR(g2,a)
          g5 = NOR(g3,g4)
          g6 = NOR(g5,b)
          g7 = NOR(g6,g5)
          g8 = NOR(g7,0)
          PASS (topology=0): output = a[0]

        a = first arrival (a_data). b = second arrival (trigger value).
        NOT(A): both arrivals carry same value so a==b, NOR(a,a)=NOT(a).
        """
        gs = self.topology & 0x3FF
        M  = 0xFFFFFFFF

        # 32-bit NOR tree — verified on silicon 2026-05-17 (iCEBreaker, 15/15 tests).
        # Operates on full 32-bit words. Matches fpga/verilog/unicell.v exactly.
        # a = first arrival (stored in a_data). b = second arrival (trigger value).
        def nor(x, y): return (~(x | y)) & M

        g0 = nor(a, a)    # NOT(A)
        g1 = nor(b, b)    # NOT(B)
        g2 = nor(g0, g1)  # AND(A,B)
        g3 = nor(g2, g2)  # NAND(A,B)
        g4 = nor(a, b)    # NOR(A,B)
        g5 = nor(g4, g4)  # OR(A,B)
        g6 = nor(a, g4)   # NOR(A, NOR(A,B))
        g7 = nor(b, g4)   # NOR(B, NOR(A,B))
        g8 = nor(g6, g7)  # XNOR(A,B)
        g9 = nor(g8, g8)  # XOR(A,B)

        # Topology values match gate_states.py constants exactly.
        topo_map = {
            0x000: a,               # PASS(A)
            0x02C: b,               # PASS(B)
            0x001: g0,              # NOT(A)
            0x002: g1,              # NOT(B)
            0x004: g4,              # NOR(A,B)
            0x007: g2,              # AND(A,B)
            0x024: g5,              # OR(A,B)
            0x027: g3,              # NAND(A,B)
            0x0BC: g9,              # XOR(A,B)
            0x03C: g8,              # XNOR(A,B)
            0x030: 0,               # ZERO
            0x0B0: M,               # ONE
        }
        return topo_map.get(gs, a)  # fallback: PASS(A)

    # ── Output buffer ─────────────────────────────────────────────────────────

    def drain_output_buf(self) -> Optional[tuple]:
        """
        Called by the array at the start of each tick to publish pending output.
        Returns (output_address, value, ecc_check) and clears the buffer.
        Matches Verilog odd_phase drain: output loaded even-phase, drained odd-phase.
        """
        result = self._output_buf
        self._output_buf = None
        return result

    # ── Snapshot / restore ────────────────────────────────────────────────────

    def snapshot(self) -> dict:
        """
        Return complete cell state as a serialisable dict.
        Used for Pond freeze/snapshot and debug inspection.
        """
        return {
            "address":        self.address,
            "cmd_latch":      self.cmd_latch & 0xFFC007FF,  # auth_mask zeroed
            "input_address":  self.input_address,
            "output_address": self.output_address,
            "start_flag":     self.start_flag,
            "frozen":         self.frozen,
            "a_arrived":      self.a_arrived,
            "a_data":         self.a_data,
            "output_buf":     self._output_buf,
            "ecc_enabled":    self.ecc_enabled,
        }

    def restore(self, snap: dict) -> None:
        """Restore cell state from a snapshot dict."""
        self.cmd_latch      = snap.get("cmd_latch", 0)
        self.input_address  = snap.get("input_address",  self.address)
        self.output_address = snap.get("output_address", self.address + 1)
        self.start_flag     = snap.get("start_flag", False)
        self.frozen         = snap.get("frozen", False)
        self.a_arrived      = snap.get("a_arrived", False)
        self.a_data         = snap.get("a_data", 0)
        self._output_buf    = snap.get("output_buf")
        self.ecc_enabled    = snap.get("ecc_enabled", False)
        # Re-unpack cmd_latch fields
        if self.cmd_latch:
            self.configure(self.cmd_latch)
            # Restore runtime state that configure() resets
            self.start_flag = snap.get("start_flag", True)
            self.a_arrived  = snap.get("a_arrived", False)
            self.a_data     = snap.get("a_data", 0)

    # ── ECC stubs ─────────────────────────────────────────────────────────────

    def _ecc_emit(self, value: int) -> tuple:
        check = _compute_ecc(value) if self.ecc_enabled else 0
        return value, check

    def inject_bit_flip(self, bit_position: int) -> None:
        """Test harness: inject a single-bit error into held data."""
        if self.a_arrived:
            self.a_data ^= (1 << bit_position)

    def inject_double_bit_flip(self, bit_a: int, bit_b: int) -> None:
        """Test harness: inject a double-bit error."""
        if self.a_arrived:
            self.a_data ^= (1 << bit_a) ^ (1 << bit_b)

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def armed(self) -> bool:
        """True if the cell will process data this tick."""
        return self.start_flag and not self.frozen

    @property
    def is_loopback(self) -> bool:
        """True if output feeds back to input (same address)."""
        return self.output_address == self.input_address

    # ── Legacy attribute aliases (v1 compatibility) ───────────────────────────
    @property
    def gate_state(self) -> int:
        """Legacy alias for cmd_latch."""
        return self.cmd_latch

    @gate_state.setter
    def gate_state(self, value: int) -> None:
        self.cmd_latch = value & 0xFFFFFFFF

    @property
    def loop_mode(self) -> bool:
        """Legacy alias — True if GS_LOOP_BACK set in cmd_latch."""
        return bool(self.cmd_latch & (1 << 31))

    def __repr__(self) -> str:
        mode = "LATCH" if self.latch_in else ("EDGE" if self.edge_mode else "STD")
        return (
            f"UniCell(addr={self.address:#010x} "
            f"in={self.input_address:#010x} "
            f"out={self.output_address:#010x} "
            f"topo={self.topology:#05x} "
            f"mode={mode} "
            f"{'ARMED' if self.armed else 'WAIT'} "
            f"a_arrived={self.a_arrived})"
        )


# ── Compatibility shims ───────────────────────────────────────────────────────
# Code that used the old receive_a() / receive_b() / receive(LOAD_PATTERN)
# interface will get clear errors. Do not silently swallow old calls.

VAR_FALSE = 0x00000000  # 32-bit bus word: logical false
VAR_TRUE  = 0xFFFFFFFF  # 32-bit bus word: logical true
