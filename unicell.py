from typing import Optional

# ── constants ──────────────────────────────────────────────────────────────

FUNCTION_LOAD_PATTERN = 0xA5A5A5A5
VAR_FALSE = 0
VAR_TRUE  = 1


# ── NOR gate logic ──────────────────────────────────────────────────────────

def nor(a: int, b: int) -> int:
    return 0 if (a == VAR_TRUE or b == VAR_TRUE) else 1


# ── ECC (SECDED) helpers ────────────────────────────────────────────────────

# ── ECC -- RESERVED, NOT ACTIVE ───────────────────────────────────────────────
#
# Bus packet format (39 bits total):
#   bits  0-31:  32-bit data word
#   bits 32-37:  ECC parity bits p1,p2,p4,p8,p16,p32  (reserved, always 0)
#   bit  38:     ECC overall parity p64                 (reserved, always 0)
#
# When implemented: Hamming(39,32) SECDED
#   - Single Error Correction, Double Error Detection
#   - 7 parity bits cover all 32 data bits
#   - Encoder: combinational logic on cell bus output driver
#   - Decoder: combinational logic on cell bus input receiver
#   - Cost: ~200 LUTs per cell -- deferred until production silicon
#
# For testing: ECC bits reserved as 0, passthrough only.
# Do not remove the ecc_check parameter from the bus tuple --
# the packet format is fixed at 39 bits for future compatibility.

def _compute_ecc(value: int) -> int:
    """
    ECC computation -- RESERVED, NOT ACTIVE.
    Returns 0 (passthrough). Bus format reserves 7 bits for future
    Hamming(39,32) SECDED implementation in silicon.
    """
    return 0


def _verify_ecc(value: int, check: int) -> tuple[int, bool, bool]:
    """
    ECC verification -- RESERVED, NOT ACTIVE.
    Returns (value, False, False) passthrough.
    Bus format reserves 7 ECC bits for future Hamming(39,32) SECDED.
    """
    return value, False, False


# ── ECCError ────────────────────────────────────────────────────────────────

class ECCError(RuntimeError):
    """Raised when a double-bit error is detected and cannot be corrected."""
    pass


# ── UniCell ──────────────────────────────────────────────────────────────────

class UniCell:
    """
    One UniCell — the fundamental unit of the Imago spatial computing fabric.

    A UniCell has three configuration registers and one control line:
      input_address:      bus address this cell listens to
      output_address:     bus address this cell drives (the pointer)
      gate_state:         what the cell does to the value before sending it
      start_flag:         separate control line — whether the cell participates

    The start_flag is architecturally distinct from the data bus. It is set
    and cleared directly by the controller, never via the bus. This gives it
    four distinct roles:

      1. Configuration gate — cells are loaded (gate_state, addresses, data)
         with start_flag=False. Configuration completes, then start_flag is
         asserted. The cell begins participating on the next tick. This
         guarantees no cell fires on partial configuration.

      2. Branch routing — when a SELECT cell routes a data wave to one path,
         the controller asserts start_flag on the chosen branch's cells and
         clears it on the unchosen branch. Only the chosen cells participate.
         The unchosen cells are present but silent.

      3. Pond freeze / snapshot — clearing start_flags on a set of cells
         freezes them in place. Their configuration and stored values are
         intact. The frozen state can be read out as a snapshot image and
         reloaded later — onto the same array or a different one. This is
         the checkpoint/resume mechanism for Pond migration and persistence.

      4. Debug freeze — clearing start_flags on a selected subset of cells
         pauses computation at a specific point without disturbing the rest
         of the array. The frozen cells can be inspected (stored values,
         configuration) and then thawed (start_flags re-asserted) to resume.

    The start_flag is the only signal that crosses from controller space into
    cell space outside the data bus and config protocol. It is a dedicated
    hardware line, not a bus address.

    Gate state register (11 bits):
      Bits 0-8:  NOR gate topology — which of the 9 gates are active
      Bit 9:     GS_SELECT sentinel — cell is a conditional router, not compute
      Bit 10:    LOOP_MODE flag — cell does not clear start_flag after firing

    ECC (Engineering Addendum v0.1, Section 2):
      When ecc_enabled is True, the cell computes a 7-bit SECDED Hamming
      check word on every data word it emits, and verifies it on every
      data word it receives. Single-bit errors are corrected silently;
      double-bit errors raise ECCError.

    Storage mode:
      When storage_mode is True the cell operates as a persistent latch.
      It retains _stored_value across clock cycles, re-emitting it every
      tick while start_flag is asserted, and updating when new data arrives
      on its input_address. Used for loop variables and branch state.
    """

    def __init__(self, address: int):
        self.address: int = address

        # config registers
        self.gate_state: int          = 0
        self.input_address:   int = 0
        self.input_b_address: int = 0   # v2: falling-edge B input address
        self.output_address: int      = 0
        self.output_address_alt: Optional[int] = None  # SELECT cells only
        # Mode flags — extracted from gate_state register bits 10-31 at config time.
        self.loop_mode:     bool = False   # bit 10: stay armed after firing
        self.latch_mode:    bool = False   # bit 11: hold and re-emit result each tick
        self.one_shot:      bool = False   # bit 12: fire once then lock permanently
        self.addr_latch:    bool = False   # bit 23: extended address latch mode
        self._config_upper: int  = 0       # upper 32 bits of the 64-bit config register
                                           # written via CMD_RECONFIGURE + scope=EXTENDED
                                           # same command bus connection as lower config
                                           # ZERO connection to data bus or NOR compute path
                                           # acts as upper forwarding address when addr_latch set
        self.invert_out:    bool = False   # bit 13: flip output after gate computation
        self.broadcast:     bool = False   # bit 14: fan out to all cells at output_address
        self.sync_wait:     bool = False   # bit 15: wait for two inputs before firing
        self.loop_back_en:  bool = False   # bit 16: enable internal G8->G0 feedback
        self.loop_back_src: int  = 8       # bits 17-19: loopback source gate (default G8)
        self.loop_back_dst: int  = 0       # bits 20-22: loopback dest gate (default G0)
        self.fall_edge:     bool = False   # bit 24: assert on falling edge (hardware only)
        self.latch_in:      bool = False   # bit 25: input-side latch
        self.out_posedge:   bool = False   # bit 26: output buffer releases on rising edge
                                           #         (default False = releases on falling edge)
        self.trace_en:      bool = False   # bit 30: log every firing to debug buffer
        self.breakpoint:    bool = False   # bit 31: halt array when this cell fires

        # Output buffer (UniCell-edge model)
        # The cell always computes on the falling edge (when B arrives).
        # The result is held here and released to the bus one cycle later:
        #   out_posedge=False -> released on the next falling edge
        #   out_posedge=True  -> released on the next rising edge
        # In the VM the array drains _output_buf into the bus at the start
        # of each tick (before delivering new inputs), modelling the one-cycle
        # hold. tick() loads the buffer and returns None; the array publishes
        # it on the next tick boundary.
        self._output_buf: Optional[tuple] = None   # (output_address, value, ecc_check)

        # storage mode
        self.storage_mode: bool         = False
        self._stored_value: Optional[int] = None

        # v2 compatibility: falling-edge B input
        self._input_b: int | None = None
        self._b_address: int = 0   # registered B input address

        # Input latch (GS_LATCH_IN, bit 25)
        # Holds the last value received on the bus at input_address.
        # If no new data arrives this tick, the cell re-evaluates using
        # this latched value on the falling edge. Enables single-cell counter.
        self._input_latch: Optional[int] = None

        # ECC
        self.ecc_enabled: bool    = False
        self._ecc_check: int      = 0      # stored check bits for current data
        self.ecc_corrections: int = 0      # cumulative single-bit corrections
        self.ecc_double_errors: int = 0    # cumulative double-bit detections

        # runtime state
        self.data: Optional[int]  = None
        self.start_flag: bool     = False
        self._sync_buf: Optional[int] = None   # SYNC_WAIT second-input buffer
        self._breakpoint_triggered: bool = False  # set by tick() when GS_BREAKPOINT fires

        # config recogniser
        self._config_mode: bool = False
        self._config_step: int  = 0

    # ── Snapshot / restore ───────────────────────────────────────────────────

    def snapshot(self) -> dict:
        """
        Return the complete state of this cell as a serialisable dict.

        Used for Pond freeze/snapshot (start_flag role 3) and debug
        inspection (role 4). The snapshot captures everything needed to
        restore the cell to its exact current state on any array:
          - Configuration registers (gate_state, addresses)
          - Runtime flags (start_flag, loop_mode, storage_mode)
          - Stored value (for storage cells — the live data they hold)
          - ECC state

        To restore: call load_map() with a CellMapRecord built from
        this snapshot, set storage_mode and start_flag directly.
        """
        return {
            "address":            self.address,
            "gate_state":         self.gate_state,
            "input_address":      self.input_address,
            "output_address":     self.output_address,
            "output_address_alt": self.output_address_alt,
            "loop_mode":          self.loop_mode,
            "latch_mode":         self.latch_mode,
            "one_shot":           self.one_shot,
            "invert_out":         self.invert_out,
            "broadcast":          self.broadcast,
            "sync_wait":          self.sync_wait,
            "loop_back_en":       self.loop_back_en,
            "loop_back_src":      self.loop_back_src,
            "loop_back_dst":      self.loop_back_dst,
            "trace_en":           self.trace_en,
            "breakpoint":         self.breakpoint,
            "storage_mode":       self.storage_mode,
            "stored_value":       self._stored_value,
            "input_latch":        self._input_latch,
            "start_flag":         self.start_flag,
            "ecc_enabled":        self.ecc_enabled,
            # data in transit (present if cell received but not yet ticked)
            "data_in_transit":    self.data,
            "addr_latch_mode":   self.addr_latch,
            "config_upper":      hex(self._config_upper) if self.addr_latch else None,
            "extended_address":  hex((self._config_upper << 32) | (self.output_address or 0)) if self.addr_latch else None,
        }

    # ── ECC public interface ──────────────────────────────────────────────────

    def inject_bit_flip(self, bit_position: int):
        """
        Inject a single-bit error into the held data value (test harness).
        bit_position: 0–31 for data bits.
        Used by the simulator test harness to validate ECC correction.
        """
        if self.data is not None:
            self.data = self.data ^ (1 << bit_position)
        elif self._stored_value is not None:
            self._stored_value = self._stored_value ^ (1 << bit_position)

    def inject_double_bit_flip(self, bit_a: int, bit_b: int):
        """Inject a double-bit error (should be detected, not corrected)."""
        if self.data is not None:
            self.data = self.data ^ (1 << bit_a) ^ (1 << bit_b)
        elif self._stored_value is not None:
            self._stored_value = (self._stored_value
                                  ^ (1 << bit_a) ^ (1 << bit_b))

    def _ecc_emit(self, value: int) -> tuple[int, int]:
        """Compute ECC check bits for a value about to be emitted."""
        check = _compute_ecc(value) if self.ecc_enabled else 0
        return value, check

    def _ecc_receive(self, value: int, check: int) -> int:
        """
        Verify ECC on a received value. Corrects single-bit errors in place.
        Raises ECCError on double-bit errors.
        Returns the (possibly corrected) value.
        """
        if not self.ecc_enabled or check == 0:
            return value
        corrected, single, double = _verify_ecc(value, check)
        if double:
            self.ecc_double_errors += 1
            raise ECCError(
                f"UniCell 0x{self.address:08X}: uncorrectable double-bit ECC "
                f"error on received data 0x{value:08X}"
            )
        if single:
            self.ecc_corrections += 1
        return corrected

    # ── config and data reception ─────────────────────────────────────────────

    def receive_a(self, value: int) -> None:
        """
        Receive rising-edge input A (v2 two-input mode).
        Equivalent to receive() -- stored in data for processing on tick.
        """
        if not self.start_flag or self._config_mode:
            return
        self.data = self._ecc_receive(value, 0)
        if self.latch_in:
            self._input_latch = self.data

    def receive_b(self, value: int) -> None:
        """
        Receive falling-edge input B (v2 two-input mode).
        Stored in _input_b -- kept SEPARATE from A (self.data).
        The tick() method uses both A and B independently via _execute_nor_gates_v2.
        Do NOT combine A and B here -- that would corrupt the A value.
        """
        if not self.start_flag or self._config_mode:
            return
        self._input_b = value & 0xFFFFFFFF

    def receive(self, value: int, ecc_check: int = 0) -> bool:
        """
        Deliver a value to this cell.

        Config sequence (triggered by FUNCTION_LOAD_PATTERN):
          field 0: gate_state, field 1: input_address, field 2: output_address.

        Storage mode is set directly on self.storage_mode by the controller
        after configuration — never via the bus receive() path.

        ecc_check: the 7-bit SECDED check word accompanying this value.
          Only used when ecc_enabled=True. Config packets carry check=0
          (ECC not applied to config writes).

        Returns True if consumed as config, False if stored as data.
        """
        if not self._config_mode:
            if (value & 0xFFFFFFFF) == FUNCTION_LOAD_PATTERN:
                self._config_mode = True
                self._config_step = 0
                return True
            # Data delivery — verify ECC before storing
            self.data = self._ecc_receive(value, ecc_check)
            return False

        if self._config_step == 0:
            # Gate state: 32-bit field (extended architecture).
            # Bits 0-8:   NOR gate topology
            # Bit 9:      GS_SELECT sentinel
            # Bit 10:     LOOP_MODE — stay armed after firing
            # Bit 11:     GS_LATCH — hold and re-emit result
            # Bit 12:     GS_ONE_SHOT — fire once then lock
            # Bit 13:     GS_INVERT_OUT — flip output after gate
            # Bit 14:     GS_BROADCAST — fan out to all receivers
            # Bit 15:     GS_SYNC_WAIT — wait for two inputs before firing
            # Bit 16:     GS_LOOP_BACK — internal G8→G0 feedback
            # Bits 17-22: loopback src/dst gate selectors
            # Bit 23:     GS_ADDR_LATCH — extended 64-bit address (bridge cells)
            # Bit 24:     GS_FALL_EDGE — falling-edge assertion (hardware only,
            #             ignored in VM — edge separation is a silicon timing
            #             mechanism; the VM is synchronous and tick-based)
            # Bit 25:     GS_LATCH_IN — input-side latch. VM implements this:
            #             cell stores last received value in _input_latch.
            #             If no new data arrives this tick, re-evaluates using
            #             the latched input value. Enables single-cell counter.
            # Bits 29-31: PRIORITY, TRACE, BREAKPOINT
            raw = value & 0xFFFFFFFF
            self.loop_mode    = bool(raw & 0x400)
            self.latch_mode   = bool(raw & 0x800)
            self.one_shot     = bool(raw & 0x1000)
            self.invert_out   = bool(raw & 0x2000)
            self.broadcast    = bool(raw & 0x4000)
            self.sync_wait    = bool(raw & 0x8000)
            self.loop_back_en = bool(raw & 0x10000)
            self.loop_back_src = (raw >> 17) & 0b111
            self.loop_back_dst = (raw >> 20) & 0b111
            self.addr_latch   = bool(raw & 0x800000)   # bit 23 — GS_ADDR_LATCH
            # bit 24 — GS_FALL_EDGE: parsed but not acted on in VM
            self.fall_edge    = bool(raw & 0x1000000)
            # bit 25 — GS_LATCH_IN: input-side latch — fully implemented in VM
            self.latch_in     = bool(raw & 0x2000000)
            # bit 26 — GS_OUT_POSEDGE: output buffer releases on rising edge
            self.out_posedge  = bool(raw & 0x4000000)
            self.trace_en     = bool(raw & 0x40000000)
            self.breakpoint   = bool(raw & 0x80000000)
            self.gate_state   = raw & 0x3FF   # keep SELECT + NOR bits
        elif self._config_step == 1:
            self.input_address = value & 0xFFFFFFFF
        elif self._config_step == 2:
            self.output_address = value & 0xFFFFFFFF
            # Normal cells close config here.
            # SELECT cells stay open for output_address_alt (step 3).
            # addr_latch cells stay open for config_upper (step 4).
            # write_config() forcibly closes config if no further fields sent.
            from gate_states import GS_SELECT
            if self.gate_state != GS_SELECT and not self.addr_latch:
                self._config_mode = False
        elif self._config_step == 3:
            # Field 4: output_address_alt for SELECT cells.
            # For addr_latch cells this field is skipped (SELECT and addr_latch
            # are mutually exclusive — a bridge is not a conditional router).
            self.output_address_alt = value & 0xFFFFFFFF
            if not self.addr_latch:
                self._config_mode = False
            # addr_latch cells stay open for one more field (config_upper)
        elif self._config_step == 4:
            # Field 5: config_upper — upper 32 bits of the 64-bit config register.
            # Only reached by addr_latch cells (bridge cells with extended routing).
            # Same command bus path as lower config — just the upper half of the
            # same register extended to 64 bits.
            # NEVER touches data bus. NEVER touches NOR compute path.
            # Written via CMD_RECONFIGURE + scope=EXTENDED.
            self._config_upper = value & 0xFFFFFFFF
            self._config_mode  = False
        self._config_step += 1
        return True

    # ── clock tick ────────────────────────────────────────────────────────────

    def tick(self) -> Optional[tuple]:
        """
        Execute one clock cycle.

        Returns (output_address, result, ecc_check) if the cell posted a result,
        or None if the cell took no action.

        Mode flags (from 32-bit gate_state register) affect behaviour:

          GS_LATCH (bit 11):
            The cell retains the last computed result and re-emits it every tick.
            Updates _stored_value when new data arrives. Replaces storage_mode
            with a proper 32-bit register model.

          GS_SYNC_WAIT (bit 15):
            Cell accumulates incoming packets in _sync_buf until two have arrived,
            then fires with the OR of both values. Eliminates depth-equalisation
            PASS chains — signals on different-depth paths are merged naturally.

          GS_LOOP_BACK (bit 16):
            After computing, the result is fed back to G0 input internally before
            being emitted. Creates a single-cell SR latch or ring oscillator.

          GS_ONE_SHOT (bit 12):
            After firing, start_flag is cleared and never re-armed by this cell.
            Useful for edge-triggered logic that must fire exactly once.

          GS_INVERT_OUT (bit 13):
            The result is bitwise inverted before emission. Free NOT on output.

          SELECT cells (gate_state == GS_SELECT):
            Reads incoming value as a 1-bit condition; routes to output_address
            (condition=1) or output_address_alt (condition=0). Value unchanged.
        """
        from gate_states import GS_SELECT

        if not self.start_flag or self._config_mode:
            return None

        # ── LATCH mode (bit 11) ───────────────────────────────────────────────
        # Supersedes old storage_mode for new-architecture cells.
        # Re-emits stored value every tick; updates when new data arrives.
        if self.latch_mode or self.storage_mode:
            if self.data is not None:
                _raw = self._execute_nor_gates_v2(self.data, 0)
                computed = (_raw & 1) if (self.gate_state & 0x1FF) else _raw
                if self.invert_out:
                    computed = 1 - computed
                self._stored_value = computed
                self.data = None
            if self._stored_value is None:
                return None
            val, chk = self._ecc_emit(self._stored_value)
            if self.trace_en:
                print(f"[TRACE] {hex(self.address)}: LATCH emit {val}")
            # Sentry cells write to PTT bus range — intercept silently in VM
            if (self.output_address is not None and
                    self.output_address >= 0xFFE00000):
                ptt = getattr(self, '_ptt_ref', None)
                if ptt is not None:
                    ptt.bus_tick(self.output_address, val)
                return None
            return self._buf((self.output_address, val, chk))

        # ── SYNC_WAIT mode (bit 15) ───────────────────────────────────────────
        # v2 two-input mode: if input_b_address is set, A and B come from
        # different bus addresses. Use execute_nor_gates(a, b) directly.
        # v1 compat: if no input_b_address, use _sync_buf (same-address OR).
        if self.sync_wait:
            if self.data is not None:
                # v2: two-input cell with separate B address
                if getattr(self, 'input_b_address', 0) and self._input_b is not None:
                    a = self.data
                    b = self._input_b
                    self.data    = None
                    self._input_b = None
                    # v2 two-input tree: A and B as distinct inputs
                    result = self._execute_nor_gates_v2(a, b)
                    if self.invert_out:
                        result = (~result) & 0xFFFFFFFF
                    if self.loop_back_en:
                        self.data = result
                    if not self.loop_mode:
                        self.start_flag = False
                    if self.one_shot:
                        self.start_flag = False
                    val, chk = self._ecc_emit(result)
                    if self.trace_en:
                        print(f"[TRACE] {hex(self.address)}: SYNC_WAIT_V2 fire {val}")
                    return self._buf((self.output_address, val, chk))
                elif getattr(self, 'input_b_address', 0) and self._input_b is None:
                    # B not yet received -- wait
                    return None
                elif not hasattr(self, '_sync_buf') or self._sync_buf is None:
                    self._sync_buf = self.data   # first packet — hold and wait
                    self.data = None
                    return None                  # not ready yet
                else:
                    # Second packet arrived — OR both and fire (v1 mode)
                    combined = self.data | self._sync_buf
                    self._sync_buf = None
                    self.data = None
                    result = self._execute_nor_gates(combined)
                    if self.invert_out:
                        result = 1 - result
                    if self.loop_back_en:
                        self.data = result       # feed back into next cycle
                    if not self.loop_mode:
                        self.start_flag = False
                    if self.one_shot:
                        self.start_flag = False
                    val, chk = self._ecc_emit(result)
                    if self.trace_en:
                        print(f"[TRACE] {hex(self.address)}: SYNC_WAIT fire {val}")
                    return self._buf((self.output_address, val, chk))
            return None

        # ── GS_LATCH_IN (bit 25) — input-side latch ───────────────────────────
        # If new data arrived this tick: store it in _input_latch, then proceed
        # normally using the new data.
        # If no data arrived but _input_latch has a value: use the latched input
        # and re-evaluate. This gives the cell a one-tick input memory.
        # Combined with LOOP_MODE this enables a single-cell counter:
        #   each tick re-evaluates the latched value, LOOP_MODE feeds output
        #   back to input_address, latch holds the running state.
        if self.latch_in:
            if self.data is not None:
                # New data arrived — update latch
                self._input_latch = self.data
            elif self._input_latch is not None:
                # No new data — re-fire using latched input
                self.data = self._input_latch

        if self.data is None:
            return None

        # For addr_latch cells: upper 32 bits come from _latch_upper register.
        # This is a dedicated store, set by set_addr_latch() via CommandInterface.
        # It is never touched by the NOR compute path.
        # self.data is the bus input — it flows through GS_PASS normally.
        _upper_addr = self._config_upper if self.addr_latch else None

        # ── SELECT: conditional router ────────────────────────────────────────
        if self.gate_state == GS_SELECT:
            condition = self.data & 1
            self.data = None
            if not self.loop_mode:
                self.start_flag = False
            target = (self.output_address
                      if condition == 1
                      else (self.output_address_alt
                            if self.output_address_alt is not None
                            else self.output_address))
            val, chk = self._ecc_emit(condition)
            return self._buf((target, val, chk))

        # ── Normal compute / PASS / loopback ──────────────────────────────────
        # v2 path: use two-input tree. For single-input cells, b=0 is safe.
        # Mask to bit 0 only when a gate is active (gate_state bits 0-8 non-zero).
        # PASS (gate_state=0) preserves full value -- VM may carry multi-bit data.
        _b_val = getattr(self, "_input_b", None) or 0
        _raw = self._execute_nor_gates_v2(self.data, _b_val)
        result = (_raw & 1) if (self.gate_state & 0x1FF) else _raw
        self.data = None

        # Internal loopback: feed result back to data for next cycle (bit 16)
        if self.loop_back_en:
            self.data = result

        # Invert output (bit 13)
        if self.invert_out:
            result = 1 - result

        # Determine if start_flag should clear
        if self.one_shot:
            self.start_flag = False          # lock permanently
        elif not self.is_loopback and not self.loop_mode and not self.loop_back_en:
            self.start_flag = False          # normal one-shot compute

        # Breakpoint: halt array by raising a flag (checked by array.tick)
        if self.breakpoint:
            self._breakpoint_triggered = True
            print(f"[BREAKPOINT] Cell {hex(self.address)} fired — value={result}")

        if self.trace_en:
            print(f"[TRACE] {hex(self.address)}: gs={hex(self.gate_state)} "
                  f"result={result}")

        val, chk = self._ecc_emit(result)

        # If this cell is an address latch, include the full 64-bit
        # forwarding address alongside the normal 32-bit output.
        # The array/command layer uses this to route via extended bus.
        # Data bus delivery (to output_address) is 32-bit — unchanged.
        if self.addr_latch and _upper_addr is not None:
            full_addr = (_upper_addr << 32) | (self.output_address or 0)
            return self._buf((self.output_address, val, chk, full_addr))

        # ── PTT bus address interception (VM only) ────────────────────────────
        # Sentry cells write to the reserved PTT bus range (0xFFE00000+).
        # In the VM there is no physical PTT bus — route the tick to the
        # PTT object directly and return None so the controller does not
        # see this as bus activity. This prevents LOOP_MODE sentry cells
        # from keeping the simulation running forever.
        # On silicon, these writes go to real bus addresses and the Ward
        # reads them directly — no interception needed.
        if (self.output_address is not None and
                self.output_address >= 0xFFE00000):
            # Route to PTT if one is attached to this cell's context
            ptt = getattr(self, '_ptt_ref', None)
            if ptt is not None:
                ptt.bus_tick(self.output_address, val)
            # Return None — sentry ticks are invisible to the controller
            return None

        return self._buf((self.output_address, val, chk))

    def _buf(self, result_tuple: tuple) -> tuple:
        """
        Load the output buffer with a computed result and return it.

        For one-shot feed-forward cells: result goes into _output_buf and is
        published to the bus by the array on the next tick (one-cycle delay).
        This is the UniCell-edge output buffer model.

        For feedback/loop cells (loop_mode, latch_mode, storage_mode): the
        output buffer is bypassed. The result is returned directly and the
        array's Phase 2 places it on new_bus immediately, because these cells
        depend on seeing their own output on the bus within the same tick to
        maintain feedback state. Delaying by one cycle breaks the loop.

        The array's Phase 0 publishes _output_buf to the bus for buffered cells.
        Unit tests and the controller use the return value for direct inspection.
        """
        is_feedback = self.loop_mode or self.latch_mode or self.storage_mode
        if is_feedback:
            # Bypass: no delay, result available on bus this tick
            # _output_buf stays None so Phase 0 doesn't double-publish
            return result_tuple
        self._output_buf = result_tuple
        return result_tuple

    def drain_output_buf(self) -> Optional[tuple]:
        """
        Called by the array at the start of each tick to publish any pending
        output buffer contents to the bus.

        Returns the buffered (output_address, value, ecc_check) tuple and
        clears the buffer, or None if nothing is pending.

        This models the output register flip-flop: the cell computed on
        cycle N, result was latched into _output_buf, and it is now being
        driven onto the bus at the start of cycle N+1.
        """
        result = self._output_buf
        self._output_buf = None
        return result



    def _execute_nor_gates(self, value: int) -> int:
        """DEPRECATED: v1 single-input gate tree. Use _execute_nor_gates_v2(a, b) instead."""
        def active(n):
            return bool((self.gate_state >> n) & 1)
        def gate(n, a, b):
            return nor(a, b) if active(n) else a
        g1 = gate(0, value, value)
        g2 = gate(1, value, value)
        g3 = gate(2, g1,   g2   )
        g4 = gate(3, g3,   value)
        g5 = gate(4, g3,   value)
        g6 = gate(5, g4,   g5   )
        g7 = gate(6, g6,   value)
        g8 = gate(7, g7,   g6   )
        return gate(8, g8,  0    )

    def _execute_nor_gates_v2(self, a: int, b: int) -> int:
        """
        Execute the 9-gate NOR tree with two distinct inputs (v2 mode).
        A = rising-edge input, B = falling-edge input.
        Verified truth tables in gate_states_v2.py.
        """
        gs = self.gate_state & 0x1FF
        def _nor(x, y): return (~(x | y)) & 0xFFFFFFFF
        def gate(n, x, y): return _nor(x, y) if (gs >> n) & 1 else x
        g0 = gate(0, a, a)   # NOT(A)
        g1 = gate(1, b, b)   # NOT(B)
        g2 = gate(2, g0, g1) # AND(A,B)
        g3 = gate(3, g2, b)
        g4 = gate(4, g2, a)
        g5 = gate(5, g3, g4)
        g6 = gate(6, g5, b)
        g7 = gate(7, g6, g5)
        return gate(8, g7, 0)

    # ── loopback (backward compat) ────────────────────────────────────────────

    @property
    def is_loopback(self) -> bool:
        return self.output_address == self.input_address

    def __repr__(self) -> str:
        if self.storage_mode:
            mode = f"STOR(={self._stored_value})"
        elif self.is_loopback:
            mode = "MEM"
        else:
            mode = "LOG"
        ecc = " ECC" if self.ecc_enabled else ""
        return (
            f"UniCell(addr=0x{self.address:08X} "
            f"in=0x{self.input_address:08X} "
            f"out=0x{self.output_address:08X} "
            f"gs=0b{self.gate_state:09b} "
            f"mode={mode}{ecc} "
            f"flag={'RUN' if self.start_flag else 'WAIT'} "
            f"data={self.data})"
        )
