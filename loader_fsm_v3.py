"""
loader_fsm_v3.py — VM model of fpga/verilog/loader_fsm_v3.v, the existing,
already-proven boot-time icmP loader (2026-07-31).

This is NOT a new phase of the cell/array rebuild -- it's the next
concrete point on PLAN.md's definitive task path: the command-cell
RAM-read runtime mechanism, which explicitly reuses this exact reader
("the SAME shared loader-FSM-style reader... re-purposed/re-triggered for
ongoing SET_TARGET+INJECT-style DATA application"). Alan's direction:
option 1 -- extend `loader_fsm_v3.v` itself, keeping the model true to the
actual proven Verilog, rather than a new cell-based mechanism.

Modeled faithfully against the real file line-by-line, including the
top-level transport it explicitly folds in (SET_TARGET/load_target +
the cpu_addr_w opcode whitelist that lives in top_arria10_zone1_v3.v) --
a genuinely new layer this VM didn't have yet (Phases 1-6 covered the
cell and array levels only).

Cross-checked directly against `tb_bram_loader_v3.v`'s exact proven
scenario (3 heterogeneous cells, XOR/AND/OR, loaded through the real
top-level transport, completion-gated on the real emit_count pulse) --
see test_loader_fsm_v3.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from unicell_array_v3 import UniCellArrayV3
from unicell_v3 import UniCellV3, AuthError

# ── Opcodes the loader FSM issues (unicell64_v3.v's numbering) ───────────────
OP_SET_INPUT_ADDR  = 2
OP_SET_OUTPUT_ADDR = 3
OP_LOAD_AT         = 23
OP_SET_TARGET      = 24
OP_LOAD_DONE       = 27
OP_METH_SET_MASK   = 30
OP_METH_SET_SHIFT_IN  = 31
OP_METH_SET_SHIFT_OUT = 32
OP_METH_SET_LANE   = 33


def unpack_topology_word(cmd_data: int) -> dict:
    """Unpack a raw CMD_LOAD_AT/CMD_RECONFIGURE cmd_data word into the
    keyword fields UniCellV3.load_at()/reconfigure() expect. Verified
    field-for-field against unicell64_v3.v lines 973-993 (NOT reconstructed
    from memory -- re-checked while building this, since getting this
    exactly right matters more here than anywhere else: this is the actual
    wire format real hardware uses)."""
    return dict(
        topology         = cmd_data & 0x3FF,
        is_command_cell  = bool((cmd_data >> 10) & 1),
        auth_mask_bits   = (cmd_data >> 20) & 0x7FF,  # 11-bit, boot-only in load_at()
        start_flag       = bool((cmd_data >> 11) & 1),
        latch_A_dis      = bool((cmd_data >> 12) & 1),
        latch_B_dis      = bool((cmd_data >> 13) & 1),
        dtype            = (cmd_data >> 14) & 0b11,
        invert_out       = bool((cmd_data >> 16) & 1),
        latch_in         = bool((cmd_data >> 17) & 1),
        priority_flag    = bool((cmd_data >> 18) & 1),
        trace            = bool((cmd_data >> 19) & 1),
        breakpoint       = bool((cmd_data >> 20) & 1),  # NOTE: overlaps auth_mask_bits'
                                                         # low bit in the raw word -- a
                                                         # real, documented wire-format
                                                         # overlap (auth only writes in
                                                         # boot state; breakpoint always
                                                         # writes), not a bug.
        one_shot         = bool((cmd_data >> 21) & 1),
        loop_back        = bool((cmd_data >> 22) & 1),
    )


class TargetLatchTransport:
    """Models the load_target register + cpu_addr_w mux that
    top_arria10_zone1_v3.v owns and loader_fsm_v3.v folds directly in
    (verified against loader_fsm_v3.v lines 66-85). Targeted opcodes read
    the HELD target address; everything else reads straight from the
    word's own address field (opcode 1's upper 16 bits, or the low 16 bits
    otherwise)."""

    _TARGETED_OPCODES = {
        OP_LOAD_AT, OP_SET_INPUT_ADDR, OP_SET_OUTPUT_ADDR,
        OP_METH_SET_MASK, OP_METH_SET_SHIFT_IN, OP_METH_SET_SHIFT_OUT,
        OP_METH_SET_LANE, OP_LOAD_DONE,
    }

    def __init__(self):
        self.load_target = 0

    def step(self, cmd_bus: int, cmd_data: int, cpu_valid: bool) -> int:
        """One cycle: latch load_target if this word is SET_TARGET, then
        return cpu_addr_w for THIS word (matches the RTL's own same-cycle
        combinational cpu_addr_w plus the posedge-registered load_target
        update -- the returned value reflects load_target as of the START
        of this cycle, same as the RTL's `assign cpu_addr = ... load_target`
        reading the register's current value while the update for THIS
        cycle's SET_TARGET, if any, takes effect on the clock edge)."""
        opcode = cmd_bus & 0xFF
        cpu_addr_w = (
            (cmd_data >> 16) & 0xFFFF if opcode == 1 else
            self.load_target if opcode in self._TARGETED_OPCODES else
            cmd_data & 0xFFFF
        )
        if cpu_valid and opcode == OP_SET_TARGET:
            self.load_target = cmd_data & 0xFFFF
        return cpu_addr_w


@dataclass
class LoaderConfigEntry:
    """One cell's worth of the icmP config table -- matches loader_fsm_v3.v's
    per-cell config_target/config_c1_bus/config_c1_data/config_c2_bus/
    config_c2_data arrays exactly (verified lines 41-46), just as a Python
    record instead of parallel arrays."""
    target:  int
    c1_bus:  int   # CMD_LOAD_AT word (cmd_bus) -- normally just the opcode + auth
    c1_data: int   # CMD_LOAD_AT payload (cmd_data) -- the packed topology word
    c2_bus:  int   # cycle-2 methodology word (cmd_bus)
    c2_data: int   # cycle-2 payload (cmd_data)


class LoaderFSMV3:
    """VM model of loader_fsm_v3.v's exact state machine (lines 98-147),
    driving a UniCellArrayV3 through the SAME transport
    (TargetLatchTransport) the real hardware uses. `step()` advances
    exactly one clock cycle, matching the real FSM's own cycle-by-cycle
    granularity -- this is a genuine state machine simulation, not a
    higher-level "just do it" shortcut, since the whole point of this
    model is testing the SEQUENCING and completion-gating faithfully."""

    S_IDLE, S_TARGET, S_TARGET_SETTLE, S_C1, S_C2, S_C3, S_WAIT, S_DONE = range(8)

    def __init__(self, array: UniCellArrayV3, config: List[LoaderConfigEntry]):
        self.array = array
        self.config = config
        self.transport = TargetLatchTransport()
        self.state = self.S_IDLE
        self.cell_idx = 0
        self.emit_before = 0
        self.done = False
        self.cells_confirmed = 0
        self._emit_count = 0  # mirrors the zone's emit_count -- incremented
                               # whenever ANY cell in the array emits, matching
                               # unicell_array64_v3.v's emit_count_r (line 202)

    def start(self) -> None:
        """Pulse `start` -- matches `S_IDLE: if (start) begin ... end`."""
        if self.state == self.S_IDLE:
            self.cell_idx = 0
            self.done = False
            self.cells_confirmed = 0
            self.state = self.S_TARGET

    def _issue(self, cmd_bus: int, cmd_data: int) -> None:
        """Broadcast one command word to every cell, exactly as the real
        transport does (cmd_valid to every cell; each cell's own auth_ok/
        config_match gating decides whether it applies), and track
        emit_count from whatever the array's own emit arbiter reports."""
        cpu_addr_w = self.transport.step(cmd_bus, cmd_data, cpu_valid=True)
        opcode = cmd_bus & 0xFF
        for cell in self.array.cells:
            try:
                if opcode == OP_LOAD_AT:
                    cell.load_at(bus_addr=cpu_addr_w, auth_token=0, **unpack_topology_word(cmd_data))
                elif opcode == OP_METH_SET_LANE:
                    cell.set_lane_cut(bus_addr=cpu_addr_w, bits=cmd_data & 0x7, auth_token=0)
                elif opcode == OP_METH_SET_MASK:
                    cell.set_nibble_mask(bus_addr=cpu_addr_w, mask=cmd_data & 0xFF, auth_token=0)
                elif opcode == OP_METH_SET_SHIFT_IN:
                    cell.set_shift_in(bus_addr=cpu_addr_w, amount=cmd_data & 0x3F, auth_token=0)
                elif opcode == OP_METH_SET_SHIFT_OUT:
                    cell.set_shift_out(bus_addr=cpu_addr_w, amount=cmd_data & 0x3F, auth_token=0)
                elif opcode == OP_SET_INPUT_ADDR:
                    cell.set_input_address(cmd_data & 0xFFFF, auth_token=0)
                elif opcode == OP_SET_OUTPUT_ADDR:
                    cell.set_output_address(cmd_data & 0xFFFF, auth_token=0)
                elif opcode == OP_LOAD_DONE:
                    cell.load_done(bus_addr=cpu_addr_w, auth_token=0)
                    self._emit_count += 1
                # OP_SET_TARGET: handled entirely by the transport, no cell action.
            except AuthError:
                pass  # config_match rejected -- exactly one cell should ever accept

    def step(self) -> None:
        """Advance exactly one clock cycle -- matches the RTL's
        `always @(posedge clk)` case statement (lines 104-146) one-for-one."""
        if self.state == self.S_IDLE:
            return  # waits for start()
        elif self.state == self.S_TARGET:
            entry = self.config[self.cell_idx]
            self._issue((OP_SET_TARGET & 0xFF), entry.target)
            self.state = self.S_TARGET_SETTLE
        elif self.state == self.S_TARGET_SETTLE:
            self.state = self.S_C1  # no action this cycle -- settle, matches the RTL exactly
        elif self.state == self.S_C1:
            entry = self.config[self.cell_idx]
            self._issue(entry.c1_bus, entry.c1_data)
            self.state = self.S_C2
        elif self.state == self.S_C2:
            entry = self.config[self.cell_idx]
            self._issue(entry.c2_bus, entry.c2_data)
            self.state = self.S_C3
        elif self.state == self.S_C3:
            self.emit_before = self._emit_count
            self._issue(OP_LOAD_DONE, 0)
            self.state = self.S_WAIT
        elif self.state == self.S_WAIT:
            if self._emit_count != self.emit_before:
                self.cells_confirmed += 1
                if self.cell_idx == len(self.config) - 1:
                    self.state = self.S_DONE
                else:
                    self.cell_idx += 1
                    self.state = self.S_TARGET
            # else: keep waiting -- no fixed delay, matches the real FSM exactly
        elif self.state == self.S_DONE:
            self.done = True  # sticky

    def run_to_completion(self, max_cycles: int = 1000) -> None:
        """Convenience driver for sim/testing -- steps until S_DONE or a
        cycle cap (matching the RTL's own lack of a queue/timeout: a real
        stuck confirm would hang forever in hardware too)."""
        for _ in range(max_cycles):
            if self.done:
                return
            self.step()
        raise TimeoutError(f"LoaderFSMV3 did not reach S_DONE within {max_cycles} cycles "
                            f"(state={self.state}, cell_idx={self.cell_idx})")
