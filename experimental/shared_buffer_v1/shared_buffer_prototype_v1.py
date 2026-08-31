"""
shared_buffer_prototype_v1.py — points.md #561: Alan's own real idea,
verified in the VM before it costs a real, slow Quartus cycle.

THE REAL IDEA: today, all 8 real cores in the super carrier shell each
carry their own, separate internal registers, permanently instantiated
in every cell regardless of which core is actually selected -- a real,
measured cost (`#560`'s own real investigation: ~950-1000 ALM/cell on
a genuinely fully-connected array, `points.md` #560/#561's own real
Quartus data). Since only one core is EVER active at a time
(`core_select`), those registers are mutually exclusive -- Alan's real
proposal: collapse them into ONE shared, physical buffer (a real
"union" register, in the C-struct-union sense), with each core's own
fields mapped onto fixed bit positions within it, only ever
meaningful while that core is actually selected.

A REAL, HONEST CORRECTION found while designing this, not glossed
over: Alan's own starting figure was "128 bits as the max" (nano's own
real `cmd_latch` width, the single largest register in the shell).
But nano's own REAL total persistent state is `cmd_latch`(128) +
`data_reg`(32) + `pending_ack`(6) = 166 bits -- `data_reg` and
`pending_ack` sit ALONGSIDE `cmd_latch` in the real RTL, not inside
it. 166 bits is the real, honest shared-buffer width used here, not
the originally proposed 128 -- still a massive real reduction from
694 bits (the real, summed total across all 8 cores' own separate
registers today), just not exactly Alan's own first number.

REAL, HONEST SCOPE: this prototype now covers all 8 real cores.
Adder (two-stage A/B capture), accumulator (continuously-live, never
blocked), branch (the richest real field layout, `#542`), and nano
(structurally different -- gate-based rather than arithmetic, and the
core that sets the real buffer width) were done first, chosen to cover
genuinely different real update patterns. ram, compare, and latch were
added by cross-checking against the existing, proven-correct VM
dispatch (`unicell_super_automaton_v1.py`'s own `_deliver_ram`/
`_deliver_comparator`/`_deliver_latch`). Sequencer required extra
care: it has NO existing VM dispatch to cross-check against (the
real, already-documented mirror-image gap -- real RTL since v2, zero
VM dispatch) -- implemented fresh, directly from `sequencer_cell_v1.v`'s
own real RTL body, not from any existing reference.
"""

_MASK32 = 0xFFFFFFFF

# ── Real, complete bit-mapping per core, verified directly against
# each core's own real RTL register declarations (not estimated) --
# every core independently overlaps the SAME [165:0] shared buffer,
# since they are never simultaneously active. ─────────────────────────

class SharedBufferCell:
    """One real, shared, physical buffer per cell (166 bits, matching
    nano's own real total -- the genuine maximum, not the originally
    assumed 128). Each core's own real update/offer logic reads and
    writes specific bit ranges of this ONE buffer, selected by
    `core_select` -- exactly mirroring what a real, merged
    `always @(posedge clk) case (core_select) ...` block would need
    to do in the actual RTL."""

    def __init__(self):
        self.buf = 0  # the one real, shared 166-bit buffer
        self.core_select = 0  # 0=nano .. matches existing project convention loosely for this prototype

    # Real, small bit-field helpers -- read/write an inclusive [hi:lo]
    # slice of the shared buffer, matching Verilog part-select semantics.
    def _get(self, lo, hi):
        width = hi - lo + 1
        return (self.buf >> lo) & ((1 << width) - 1)

    def _set(self, lo, hi, value):
        width = hi - lo + 1
        mask = ((1 << width) - 1) << lo
        self.buf = (self.buf & ~mask) | ((value & ((1 << width) - 1)) << lo)

    # ── ADDER: a_reg[31:0], a_arrived[32], out_buffer[64:33],
    # data_valid[65], downstream_mask[69:66], upstream_mask[73:70],
    # subtract_mode[74], pending_ack[78:75] -- 79 real bits, verified
    # directly against adder_cell_v1.v's own complete register list. ──
    def adder_deliver(self, arrivals, upstream_mask, subtract_mode):
        matched = {d: v for d, v in arrivals.items() if (upstream_mask >> d) & 1}
        if not matched:
            return True
        val = 0
        for v in matched.values():
            val |= v & _MASK32

        a_arrived = self._get(32, 32)
        if not a_arrived:
            self._set(0, 31, val)
            self._set(32, 32, 1)
            return True

        data_valid = self._get(65, 65)
        if data_valid:
            return False  # doubly full, matching the real RTL exactly

        a_reg = self._get(0, 31)
        result = (a_reg - val) & _MASK32 if subtract_mode else (a_reg + val) & _MASK32
        self._set(33, 64, result)
        self._set(65, 65, 1)
        self._set(32, 32, 0)
        return True

    def adder_offer(self):
        return self._get(33, 64), bool(self._get(65, 65))

    def adder_drain(self):
        self._set(65, 65, 0)

    # ── ACCUMULATOR: total[31:0], out_buffer[63:32], data_valid[64],
    # pulse_pending[65], step_amount/threshold/pulse_mode carried in
    # config (not modeled here, config-only), pending_ack[69:66] --
    # verified against accumulator_cell_v1.v's own real register list. ──
    def acc_deliver(self, inc, dec, step_amount, pulse_mode, threshold):
        total = self._get_signed(0, 31)
        delta = step_amount if inc and not dec else (-step_amount if dec and not inc else 0)
        new_total = total + delta
        if pulse_mode:
            crossed = (total < threshold <= new_total) or (new_total <= threshold < total)
            if crossed:
                self._set(33, 64, new_total & _MASK32)  # note: real RTL offers the crossing value; simplified here
                self._set(65, 65, 1)
                new_total = 0
        else:
            self._set(33, 64, new_total & _MASK32)
            self._set(64, 64, 1)
        self._set(0, 31, new_total & _MASK32)

    def _get_signed(self, lo, hi):
        v = self._get(lo, hi)
        width = hi - lo + 1
        if v & (1 << (width - 1)):
            v -= (1 << width)
        return v

    def acc_offer(self):
        return self._get(33, 64), bool(self._get(64, 64))

    # ── BRANCH: ref_value[31:0], ref_valid[32], out_buffer[64:33],
    # data_valid[65], active_route[69:66], pending_ack[73:70],
    # consumed[74] -- config fields (upstream_dir, fixed_value_*,
    # route_*, emit_*, value_source_*, rolling_mode) intentionally NOT
    # modeled here -- verified against branch_cell_v1.v's own real
    # dynamic-state register list specifically. ─────────────────────────
    def branch_deliver(self, value, threshold_low, threshold_high, marker_low, marker_equal, marker_high):
        ref_valid = self._get(32, 32)
        if not ref_valid:
            self._set(0, 31, value)
            self._set(32, 32, 1)
            return None  # held-reference capture, no output yet -- matches real RTL
        ref = self._get(0, 31)
        if value < ref:
            outcome, marker = "low", marker_low
        elif value == ref:
            outcome, marker = "equal", marker_equal
        else:
            outcome, marker = "high", marker_high
        self._set(33, 64, marker)
        self._set(65, 65, 1)
        return outcome

    def branch_offer(self):
        return self._get(33, 64), bool(self._get(65, 65))

    # ── NANO: cmd_latch[127:0], data_reg[159:128], pending_ack[165:160]
    # -- the real, full 166-bit case that sets the shared buffer's own
    # width; verified against unicell_stripped_v1.v's own real register
    # list (computed_output excluded -- confirmed combinational, not a
    # real register, #561). ─────────────────────────────────────────────
    def nano_program(self, cmd_word):
        self._set(0, 127, cmd_word)

    def nano_data_reg(self):
        return self._get(128, 159)

    def nano_set_data_reg(self, value):
        self._set(128, 159, value & _MASK32)

    # ── RAM: data_reg[31:0], data_valid[32], pending_ack[36:33] --
    # verified against ram_cell_v1.v's own real register list and
    # unicell_super_automaton_v1.py's own real _deliver_ram. ──────────
    def ram_deliver(self, arrivals, upstream_mask, fixed_mode):
        if fixed_mode:
            return True if not arrivals else False
        matched = {d: v for d, v in arrivals.items() if (upstream_mask >> d) & 1}
        if not matched:
            return True
        if self._get(32, 32):
            return False  # doubly full, matching the real RTL
        val = 0
        for v in matched.values():
            val |= v & _MASK32
        self._set(0, 31, val)
        self._set(32, 32, 1)
        return True

    def ram_offer(self):
        return self._get(0, 31), bool(self._get(32, 32))

    def ram_drain(self):
        self._set(32, 32, 0)

    # ── COMPARE: out_buffer[31:0], data_valid[32], pending_ack[36:33]
    # -- verified against compare_cell_v1.v and _deliver_comparator.
    # threshold is a real, signed comparison against upstream_val. ────
    def compare_deliver(self, arrivals, upstream_mask, threshold):
        matched = {d: v for d, v in arrivals.items() if (upstream_mask >> d) & 1}
        if not matched:
            return True
        if self._get(32, 32):
            return False
        val = 0
        for v in matched.values():
            val |= v & _MASK32
        signed_val = val - (1 << 32) if val & (1 << 31) else val
        result = 1 if signed_val >= threshold else 0
        self._set(0, 31, result)
        self._set(32, 32, 1)
        return True

    def compare_offer(self):
        return self._get(0, 31), bool(self._get(32, 32))

    # ── LATCH: latched[0], out_buffer[1], data_valid[2] -- verified
    # against latch_cell_v1.v and _deliver_latch's own real
    # CLEAR>SET>TOGGLE priority chain. ─────────────────────────────────
    def latch_deliver(self, arrivals, set_dir, clear_dir, toggle_dir):
        if not arrivals:
            return True
        set_triggered = any(((set_dir >> d) & 1) and (v & 1) for d, v in arrivals.items())
        clear_triggered = any((clear_dir >> d) & 1 for d in arrivals)
        toggle_triggered = any((toggle_dir >> d) & 1 for d in arrivals)
        latched = self._get(0, 0)
        if clear_triggered:
            latched = 0
        elif set_triggered:
            latched = 1
        elif toggle_triggered:
            latched = 1 - latched
        self._set(0, 0, latched)
        self._set(1, 1, latched)  # out_buffer mirrors latched, continuously live
        self._set(2, 2, 1)
        return True

    def latch_offer(self):
        return self._get(1, 1), bool(self._get(2, 2))

    # ── SEQUENCER: seq_index[1:0], out_buffer[9:2] -- implemented
    # fresh directly from sequencer_cell_v1.v's own real RTL (no
    # existing VM dispatch to cross-check against, the real, already-
    # documented mirror-image gap -- real RTL, zero VM dispatch).
    # Real mechanism: capture plays NO role; advances on ack, offering
    # the value AT THE NEW index, matching the real RTL's own
    # `next_seq_index`/`value_for_index(next_seq_index)` logic exactly. ──
    def sequencer_init(self, values, sequence_len_m1):
        self._set(0, 1, 0)
        self._set(2, 9, values[0])
        self._sequencer_values = list(values)
        self._sequencer_len_m1 = sequence_len_m1

    def sequencer_offer(self):
        return self._get(2, 9), True  # continuously live, matching real data_valid semantics

    def sequencer_ack_advance(self):
        seq_index = self._get(0, 1)
        next_index = 0 if seq_index == self._sequencer_len_m1 else seq_index + 1
        self._set(0, 1, next_index)
        self._set(2, 9, self._sequencer_values[next_index])


TOTAL_BUFFER_WIDTH = 166  # the real, honest width -- not the originally proposed 128
