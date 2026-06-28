#!/usr/bin/env python3
"""
icm_stream.py — stream an ICM file onto the fabric as (SET_TARGET, CMD_LOAD_AT) pairs.

This is the compiler<->silicon bridge: an ICM file becomes an ordered list of
targeted-reconfigure transactions, one cell at a time, through the address-lane
target latch that is silicon-proven on the Arria 10 GX660.

    ICM record  ->  SET_TARGET(cell_addr)      # opcode 24, top-only, holds address lane
                    CMD_LOAD_AT(config_word)   # opcode 23, cell self-gates on addr_match+auth

GROUND TRUTH (verified against fpga/verilog/unicell.v, unicell_array.v,
pcie/top_arria10.v, fpga/zone_target.tcl, fpga/verilog/tb_top_target.v):

  * SET_TARGET (24) is TOP-ONLY: top latches cpu_data[15:0] -> load_target and HOLDS it.
  * For CMD_LOAD_AT (23) the top drives cpu_addr_w = load_target (the held target);
    for every other opcode cpu_addr_w = cpu_data[15:0].
  * The array BROADCASTS cmd_valid for opcode 23; the CELL self-gates the write on
    (addr_match && auth_ok). addr_match = physical CELL_ID in boot (physical_mode=1),
    logical input_address in run. A fresh cell has auth_mask==0 => auth_boot => accepts.
  * CMD_LOAD_AT config-word packing into cmd_latch (from unicell.v decode):
        [9:0]  topology      [10] command_cell   [11] start_flag (arm)
        [12]   latch_A_dis    [13] latch_B_dis    [15:14] dtype
        [16]   invert_out     [17] latch_in       [18] priority
        [19]   trace          [20] breakpoint     [21] one_shot   [22] loop_back
        [30:23] auth_mask  (written ONLY in physical_mode / boot)
    and the cell also forces output_set=1, clears frozen/a_arrived/one_shot_fired.

RELOCATABLE / OFFSET-NATIVE (docs/ARCHITECTURE.md "Relocatable models"):
  ICM records hold OFFSETS from the model root, not absolute addresses. The loader
  forms  absolute = root + offset  and never bakes absolute-only into the format.
  Block-local 16-bit offsets for now (an intra-block model fits); the record format
  reserves room to widen to full on-die offsets later without a format break.

SCOPE / HONEST LIMITS on the *currently flashed* bitstream:
  The target latch decouples target from config for CMD_LOAD_AT only. SET_INPUT_ADDR(2)
  / SET_OUTPUT_ADDR(3) still take cpu_addr from cpu_data[15:0] (dual-use), so arbitrary
  per-cell in/out addressing is NOT yet streamable on hardware. Until that reflash
  (route load_target into cpu_addr_w for opcodes 2/3, + cell addr_match-gate them),
  this loader places cells contiguously and relies on the physical defaults
  (in=CELL_ID, out=CELL_ID+1). It CHECKS each record's in/out offsets against those
  defaults and warns if a design needs the not-yet-flashed address-targeting path.
  The per-cell in/out offsets are carried in the stream regardless, so the same ICM
  loads unchanged once that reflash lands.

TRANSPORTS:
  --emit tcl   writes an in-system-source-probe .tcl (ISSP/JTAG), zone_target format.
  --emit txt   writes a human-readable transaction listing.
  (UART and PCIe BAR transports drop in behind the same Transaction stream later —
   the carrier changes, the (opcode, cmd_word, data_word) records do not.)

Usage:
  python3 fpga/icm_stream.py --icm examples/icm/xor_and_or.icm --verify
  python3 fpga/icm_stream.py --icm examples/icm/xor_and_or.icm --emit tcl -o fpga/icm_xor_and_or.tcl
  python3 fpga/icm_stream.py --icm examples/icm/xor_and_or.icm --cell-root 0 --emit tcl --verify
"""

import json
import argparse
import sys

# ── Opcodes (mirror unicell.v / top_arria10.v exactly) ──────────────────────────
OP_NOP            = 0
OP_SET_INPUT_ADDR = 2
OP_SET_OUTPUT_ADDR= 3
OP_RECONFIGURE    = 4
OP_BOOT_COMMIT    = 7
OP_ARRAY_RESET    = 8
OP_LOAD_AT        = 23   # 0x17 — targeted reconfigure, address-lane gated
OP_SET_TARGET     = 24   # 0x18 — top-only, latches + holds the target address

# cmd_bus full words used by the proven scripts
CMD_LOAD_AT_BUS   = OP_LOAD_AT          # auth_token=0 (boot/auth_boot accepts)
CMD_SET_TARGET_BUS= OP_SET_TARGET
# array reset: opcode 8 with a NON-ZERO auth field [28:21] so auth_rst_pulse fires
CMD_ARRAY_RESET_BUS = OP_ARRAY_RESET | (1 << 21)   # 0x00200008

# cmd_data config-word bit positions for CMD_LOAD_AT / CMD_RECONFIGURE
CFG_TOPO_MASK   = 0x3FF
CFG_CMDCELL_BIT = 10
CFG_ARM_BIT     = 11
CFG_LATCHA_BIT  = 12
CFG_LATCHB_BIT  = 13
CFG_DTYPE_SHIFT = 14    # 2 bits [15:14]
CFG_INVERT_BIT  = 16
CFG_LATCHIN_BIT = 17
CFG_PRIORITY_BIT= 18
CFG_TRACE_BIT   = 19
CFG_BREAK_BIT   = 20
CFG_ONESHOT_BIT = 21
CFG_LOOPBACK_BIT= 22
CFG_AUTH_SHIFT  = 23    # 8 bits [30:23]

# gate_state (ICM gs) bit positions we currently map (topology + the unambiguous flags)
GS_TOPO_MASK    = 0x3FF
GS_DTYPE_SHIFT  = 23    # [24:23]
GS_LATCHIN_BIT  = 25
# Flag bits in gs beyond these are NOT yet mapped to the cmd_data packing — the full
# gs<->cmd_data table is part of the 64-bit setup-model rewrite (cmd_latch_64bit.md).
# Anything outside this mask in gs triggers a warning so nothing drops silently.
GS_MAPPED_MASK  = GS_TOPO_MASK | (0b11 << GS_DTYPE_SHIFT) | (1 << GS_LATCHIN_BIT)


class Transaction:
    """One ISSP/UART/PCIe transaction: a cmd_bus word + a data word."""
    __slots__ = ("op", "cmd_bus", "data", "note")
    def __init__(self, op, cmd_bus, data, note=""):
        self.op = op
        self.cmd_bus = cmd_bus & 0xFFFFFFFF
        self.data = data & 0xFFFFFFFF
        self.note = note
    def __repr__(self):
        return f"<{self.note or self.op}: cmd=0x{self.cmd_bus:08X} data=0x{self.data:08X}>"


# ── gate_state (ICM) -> CMD_LOAD_AT config word ─────────────────────────────────
def gs_to_loadat_config(gs, arm=True, cmd_cell=False, auth_mask=0):
    """Translate an ICM gate_state into the cmd_data config word CMD_LOAD_AT consumes.

    Maps the proven, unambiguous subset: topology, dtype, latch_in, plus arm /
    command-cell / boot auth_mask. Returns (config_word, unmapped_gs_bits)."""
    cfg = gs & CFG_TOPO_MASK                      # topology straight through
    if cmd_cell:
        cfg |= (1 << CFG_CMDCELL_BIT)
    if arm:
        cfg |= (1 << CFG_ARM_BIT)
    dtype = (gs >> GS_DTYPE_SHIFT) & 0b11
    cfg |= (dtype << CFG_DTYPE_SHIFT)
    if (gs >> GS_LATCHIN_BIT) & 1:
        cfg |= (1 << CFG_LATCHIN_BIT)
    if auth_mask:
        cfg |= ((auth_mask & 0xFF) << CFG_AUTH_SHIFT)
    unmapped = gs & ~GS_MAPPED_MASK & 0xFFFFFFFF
    return cfg & 0xFFFFFFFF, unmapped


# ── ICM -> transaction stream (offset-native) ───────────────────────────────────
def build_stream(icm, cell_root=0, root=0, reset_first=True, arm=True):
    """Turn an ICM into an ordered transaction stream.

    cell_root : physical cell slot the first record lands on (contiguous placement).
    root      : address root added to every in/out OFFSET to form the absolute wire.
    Returns (transactions, warnings, placement) where placement[i] = (slot, in_abs, out_abs).
    """
    records = icm.get("records", [])
    txns, warnings, placement = [], [], []

    if reset_first:
        txns.append(Transaction(OP_ARRAY_RESET, CMD_ARRAY_RESET_BUS, 0,
                                "ARRAY_RESET (all cells -> boot/physical_mode)"))

    for i, rec in enumerate(records):
        slot   = cell_root + i                       # physical CELL_ID this record occupies
        gs     = int(rec.get("gs", 0))
        in_off = int(rec.get("in", i))
        out_off= int(rec.get("out", i + 1))
        in_abs = root + in_off
        out_abs= root + out_off
        placement.append((slot, in_abs, out_abs))

        # Wiring-consistency guard against the currently-flashed transport.
        # Physical defaults are in=CELL_ID(=slot), out=CELL_ID+1(=slot+1).
        if in_abs != slot or out_abs != slot + 1:
            warnings.append(
                f"record {i}: wants in=0x{in_abs:04X} out=0x{out_abs:04X} but the flashed "
                f"transport only provides physical defaults in=0x{slot:04X} out=0x{slot+1:04X}. "
                f"Topology will load correctly; the in/out wiring needs the SET_INPUT/"
                f"SET_OUTPUT-on-target-latch reflash before it is represented on hardware."
            )

        cfg, unmapped = gs_to_loadat_config(gs, arm=arm)
        if unmapped:
            warnings.append(
                f"record {i}: gs bits 0x{unmapped:08X} are not yet mapped to the LOAD_AT "
                f"config word (deferred to the 64-bit setup-model cut). Topology+arm loaded."
            )

        note = rec.get("_note", "")
        txns.append(Transaction(OP_SET_TARGET, CMD_SET_TARGET_BUS, slot,
                                f"SET_TARGET cell {slot}"))
        txns.append(Transaction(OP_LOAD_AT, CMD_LOAD_AT_BUS, cfg,
                                f"LOAD_AT  cell {slot} <- gs=0x{gs:03X} {note} (cfg=0x{cfg:08X})"))

    return txns, warnings, placement


# ── Oracle: faithful model of the top latch + cell CMD_LOAD_AT decode ───────────
class CellModel:
    """Mirrors the unicell.v registers/decode relevant to the LOAD_AT load path."""
    def __init__(self, cell_id):
        self.cell_id = cell_id
        self.reset()
    def reset(self):
        self.cmd_latch     = 0
        self.input_address = self.cell_id & 0xFFFF
        self.output_address= (self.cell_id + 1) & 0xFFFF
        self.physical_mode = 1
        self.output_set    = 0
    @property
    def auth_mask(self):
        return (self.cmd_latch >> 11) & 0xFF
    def addr_match(self, bus_addr):
        return bus_addr == (self.cell_id if self.physical_mode else self.input_address)
    def auth_ok(self, auth_token):
        return self.auth_mask == 0 or auth_token == self.auth_mask
    def apply_load_at(self, bus_addr, cmd_data, auth_token):
        if not (self.addr_match(bus_addr) and self.auth_ok(auth_token)):
            return False
        cl = self.cmd_latch
        cl = (cl & ~0x3FF) | (cmd_data & 0x3FF)               # [9:0] topology
        for bit in (10, 22):                                  # [10] cmd_cell, [22] loop_back
            pass
        # explicit field writes per unicell.v CMD_LOAD_AT
        def setbit(word, dst, src):
            word &= ~(1 << dst)
            word |= (((cmd_data >> src) & 1) << dst)
            return word
        cl = setbit(cl, 10, 10)   # command_cell
        if self.physical_mode:    # auth_mask boot-only
            cl = (cl & ~(0xFF << 11)) | (((cmd_data >> 23) & 0xFF) << 11)
        cl = setbit(cl, 22, 11)   # start_flag
        cl = setbit(cl, 20, 12)   # latch_A_dis
        cl = setbit(cl, 21, 13)   # latch_B_dis
        cl = (cl & ~(0b11 << 23)) | (((cmd_data >> 14) & 0b11) << 23)  # dtype
        cl = setbit(cl, 25, 16)   # invert_out
        cl = setbit(cl, 26, 17)   # latch_in
        cl = setbit(cl, 27, 18)   # priority
        cl = setbit(cl, 28, 19)   # trace
        cl = setbit(cl, 29, 20)   # breakpoint
        cl = setbit(cl, 30, 21)   # one_shot
        cl = setbit(cl, 31, 22)   # loop_back
        self.cmd_latch = cl & 0xFFFFFFFF
        self.output_set = 1
        return True


class FabricOracle:
    """Top target-latch + a row of cells; replays a transaction stream."""
    def __init__(self, num_cells=32, cell_base=0):
        self.cells = [CellModel(cell_base + c) for c in range(num_cells)]
        self.load_target = 0
    def reset_all(self):
        for cell in self.cells:
            cell.reset()
        self.load_target = 0
    def run(self, txns):
        for t in txns:
            op = t.cmd_bus & 0xFF
            auth_token = (t.cmd_bus >> 21) & 0xFF
            if op == OP_ARRAY_RESET and ((t.cmd_bus >> 21) & 0xFF) != 0:
                self.reset_all()
            elif op == OP_SET_TARGET:
                self.load_target = t.data & 0xFFFF        # latch + hold
            elif op == OP_LOAD_AT:
                bus_addr = self.load_target               # top drives cpu_addr_w = load_target
                for cell in self.cells:
                    cell.apply_load_at(bus_addr, t.data, auth_token)
            # other opcodes not needed for the LOAD_AT stream
    def cell(self, cid):
        for c in self.cells:
            if c.cell_id == cid:
                return c
        return None


def verify(icm, txns, placement, cell_base=0, num_cells=32):
    """Replay the stream through the oracle and check each loaded cell's topology/arm."""
    fab = FabricOracle(num_cells=num_cells, cell_base=cell_base)
    fab.run(txns)
    records = icm.get("records", [])
    results, ok = [], True
    for i, rec in enumerate(records):
        slot = placement[i][0]
        cell = fab.cell(slot)
        want_topo = int(rec.get("gs", 0)) & 0x3FF
        got_topo  = cell.cmd_latch & 0x3FF
        armed     = (cell.cmd_latch >> 22) & 1
        passed    = (got_topo == want_topo) and bool(armed)
        ok &= passed
        results.append((slot, want_topo, got_topo, armed, passed))
    # exclusion spot-check: a cell NOT in the program must stay unconfigured
    used = {p[0] for p in placement}
    spare = next((c.cell_id for c in fab.cells if c.cell_id not in used), None)
    spare_clean = True
    if spare is not None:
        sc = fab.cell(spare)
        spare_clean = (sc.cmd_latch & 0x3FF) == 0 and ((sc.cmd_latch >> 22) & 1) == 0
        ok &= spare_clean
    return ok, results, (spare, spare_clean)


# ── Emitters ────────────────────────────────────────────────────────────────────
def emit_tcl(icm, txns, placement, inst=0, hwm="USB-Blaster"):
    """ISSP in-system-source-probe .tcl, same handshake/format as fpga/zone_target.tcl."""
    name = icm.get("name", "icm")
    L = []
    L.append(f"# {name}.tcl — AUTO-GENERATED by icm_stream.py")
    L.append(f"# Streams the ICM '{name}' as (SET_TARGET, CMD_LOAD_AT) pairs through the")
    L.append(f"# target latch. Requires the build with SET_TARGET(op24) + CMD_LOAD_AT(op23).")
    L.append(f"# Reads cell-0 cmd_latch via probe view selector 3 (dbg0_cmd_latch[79:48]).")
    L.append("set INST 0")
    L.append("if {$argc >= 1} { set INST [lindex $argv 0] }")
    L.append(f'set HWM "{hwm}"')
    L.append("if {$argc >= 2} { set HWM [lindex $argv 1] }")
    L.append("set ::INST $INST")
    L.append("proc uc_open {m} { set ns [get_hardware_names]; set ::HW [lindex $ns 0]")
    L.append('    foreach h $ns { if {[string match "*$m*" $h]} { set ::HW $h; break } }')
    L.append("    set ::DEV [lindex [get_device_names -hardware_name $::HW] 0]")
    L.append('    puts "Hardware : $::HW"; puts "Device   : $::DEV"')
    L.append("    start_insystem_source_probe -device_name $::DEV -hardware_name $::HW }")
    L.append("proc uc_close {} { end_insystem_source_probe }")
    L.append("proc sf {snap go cmd data} { set hi [expr {(($snap&1)<<1)|($go&1)}]")
    L.append('    write_source_data -instance_index $::INST -value [format "%x%08x%08x" $hi [expr {$cmd&0xFFFFFFFF}] [expr {$data&0xFFFFFFFF}]] -value_in_hex }')
    L.append("proc cmd {cb cd} { sf 0 0 $cb $cd; sf 0 1 $cb $cd; sf 0 0 $cb $cd }")
    L.append("proc rd_latch {} { sf 1 0 0x00000003 0x0; sf 0 0 0x00000003 0x0")
    L.append('    set v [expr {"0x[string trim [read_probe_data -instance_index $::INST -value_in_hex]]"}]')
    L.append("    return [expr {($v>>48)&0xFFFFFFFF}] }")
    L.append("")
    L.append("uc_open $HWM")
    L.append(f'puts "================= ICM STREAM: {name} ================="')
    for t in txns:
        L.append(f"cmd 0x{t.cmd_bus:08X} 0x{t.data:08X}   ;# {t.note}")
    # cell-0 readback (only cell 0's latch is probe-visible at selector 3)
    cell0 = next((i for i, p in enumerate(placement) if p[0] == 0), None)
    if cell0 is not None:
        want = int(icm["records"][cell0].get("gs", 0)) & 0x3FF
        L.append("set l0 [rd_latch]")
        L.append(f'puts [format "  cell0 latch topo = 0x%03x  (want 0x{want:03X})  %s" '
                 f'[expr {{$l0 & 0x3FF}}] [expr {{($l0 & 0x3FF)==0x{want:03X} ? "PASS" : "** FAIL **"}}]]')
        L.append('puts "  (only cell-0 latch is probe-visible; the rest are oracle/sim-verified)"')
    L.append("uc_close")
    L.append('puts "=== done ==="')
    return "\n".join(L) + "\n"


def emit_txt(txns):
    out = ["# ICM transaction stream (opcode  cmd_bus      data        note)"]
    for t in txns:
        out.append(f"  op{t.op:<2}  0x{t.cmd_bus:08X}  0x{t.data:08X}  {t.note}")
    return "\n".join(out) + "\n"


def emit_tb(icm, txns, placement):
    """Generate an iverilog testbench that replays THIS stream against the real
    unicell RTL (unicell_zone/array/cell) and checks each programmed cell's topology.
    Mirrors fpga/verilog/tb_top_target.v's harness — sim-first proof of the loader."""
    name = icm.get("name", "icm")
    max_cell = max((p[0] for p in placement), default=0)
    num_cells = max(28, max_cell + 1)
    # per-cell expected topology + arm
    expected = []
    for i, rec in enumerate(icm.get("records", [])):
        slot = placement[i][0]
        expected.append((slot, int(rec.get("gs", 0)) & 0x3FF))
    L = []
    L.append("`timescale 1ns/1ps")
    L.append(f"// tb_icm_{name}.v — AUTO-GENERATED by icm_stream.py.")
    L.append(f"// Replays the '{name}' ICM stream (SET_TARGET,CMD_LOAD_AT pairs) against the")
    L.append("// real unicell RTL through the target-latch transport, then checks each cell's")
    L.append("// loaded topology. Compile: iverilog -o tb.vvp tb_icm_*.v unicell_zone.v unicell_array.v unicell.v")
    L.append(f"module tb_icm_{name};")
    L.append("    reg clk=0,rst=0; always #5 clk=~clk;")
    L.append("    reg [31:0] cpu_bus=0, cpu_data=0; reg cpu_valid=0;")
    L.append("    localparam [7:0] OP_SET_TARGET=8'd24, OP_LOAD_AT=8'd23;")
    L.append("    reg [15:0] load_target=16'h0;")
    L.append("    always @(posedge clk) if (cpu_valid && cpu_bus[7:0]==OP_SET_TARGET) load_target<=cpu_data[15:0];")
    L.append("    wire [15:0] cpu_addr_w = (cpu_bus[7:0]==8'd1)?cpu_data[31:16]:(cpu_bus[7:0]==OP_LOAD_AT)?load_target:cpu_data[15:0];")
    L.append("    wire preload_act=(cpu_bus[18:17]!=2'b00);")
    L.append("    wire cmd_valid_w=cpu_valid && (cpu_bus[7:0]!=8'd1) && ((cpu_bus[7:0]!=8'd0)||preload_act);")
    L.append("    wire [1:0] tv=0; wire [31:0] ta=0,td=0;")
    L.append(f"    unicell_zone #(.NUM_CELLS({num_cells}),.NUM_BRIDGES(2),.ZONE_ID(0)) z(.clk(clk),.rst(rst),")
    L.append("      .cmd_bus(cpu_bus),.cmd_data(cpu_data),.cmd_valid(cmd_valid_w),.cpu_addr(cpu_addr_w),.cpu_data(cpu_data),.cpu_valid(cpu_valid),")
    L.append("      .out_addr(),.out_data(),.out_valid(),.armed_count(),.arrived_count(),.output_set_count(),.emit_count(),")
    L.append("      .dbg0_cmd_latch(),.dbg0_input_addr(),.dbg0_output_addr(),.dbg0_a_data(),.cycle_count(),")
    L.append("      .bridge_n_in_valid(tv),.bridge_n_in_addr(ta),.bridge_n_in_data(td),.bridge_n_out_valid(),.bridge_n_out_addr(),.bridge_n_out_data(),")
    L.append("      .bridge_s_in_valid(tv),.bridge_s_in_addr(ta),.bridge_s_in_data(td),.bridge_s_out_valid(),.bridge_s_out_addr(),.bridge_s_out_data(),")
    L.append("      .bridge_e_in_valid(tv),.bridge_e_in_addr(ta),.bridge_e_in_data(td),.bridge_e_out_valid(),.bridge_e_out_addr(),.bridge_e_out_data(),")
    L.append("      .bridge_w_in_valid(tv),.bridge_w_in_addr(ta),.bridge_w_in_data(td),.bridge_w_out_valid(),.bridge_w_out_addr(),.bridge_w_out_data());")
    L.append("    task pulse; input [31:0] b,d; begin")
    L.append("        @(negedge clk); cpu_bus<=b; cpu_data<=d; cpu_valid<=1;")
    L.append("        @(posedge clk); #1; cpu_valid<=0; cpu_bus<=0; cpu_data<=0;")
    L.append("        repeat(3) @(posedge clk); #1; end endtask")
    L.append("    integer fails=0;")
    L.append("    task chk; input [15:0] cid; input [9:0] want; reg [9:0] got; begin")
    L.append("        case (cid)")
    for slot, _ in expected:
        L.append(f"          {slot}: got = z.cells.cell_array[{slot}].cell_inst.cmd_latch[9:0];")
    L.append("          default: got = 10'h3FF;")
    L.append("        endcase")
    L.append('        $display("  cell %0d topo=0x%03x want=0x%03x %s", cid, got, want, (got===want)?"PASS":"** FAIL **");')
    L.append("        if (got!==want) fails=fails+1; end endtask")
    L.append("    initial begin")
    L.append("        rst=1; repeat(5)@(posedge clk);#1; rst=0; repeat(2)@(posedge clk);#1;")
    L.append(f'        $display("=== ICM STREAM replay: {name} ===");')
    for t in txns:
        L.append(f"        pulse(32'h{t.cmd_bus:08X}, 32'h{t.data:08X});  // {t.note}")
    for slot, topo in expected:
        L.append(f"        chk(16'd{slot}, 10'h{topo:03X});")
    L.append(f'        if (fails==0) $display("  >>> PASS: all {len(expected)} programmed cells match");')
    L.append('        else $display("  >>> FAIL: %0d mismatch(es)", fails);')
    L.append("        $finish; end")
    L.append("endmodule")
    return "\n".join(L) + "\n"


# ── CLI ──────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Stream an ICM as (SET_TARGET, CMD_LOAD_AT) pairs.")
    ap.add_argument("--icm", required=True, help="Path to .icm file")
    ap.add_argument("--cell-root", type=int, default=0, help="Physical cell slot for record 0 (default 0)")
    ap.add_argument("--root", type=int, default=0, help="Address root added to in/out offsets (default 0)")
    ap.add_argument("--no-arm", action="store_true", help="Load cells disarmed (start_flag=0)")
    ap.add_argument("--no-reset", action="store_true", help="Do not prepend ARRAY_RESET")
    ap.add_argument("--emit", choices=["tcl", "txt", "tb"], help="Emit a transport script or sim testbench")
    ap.add_argument("-o", "--out", help="Output path for --emit")
    ap.add_argument("--verify", action="store_true", help="Replay through the oracle and report")
    ap.add_argument("--num-cells", type=int, default=32, help="Oracle fabric size (default 32)")
    args = ap.parse_args()

    with open(args.icm) as f:
        icm = json.load(f)

    txns, warnings, placement = build_stream(
        icm, cell_root=args.cell_root, root=args.root,
        reset_first=not args.no_reset, arm=not args.no_arm)

    print(f"[ICM] {icm.get('name','?')}  records={len(icm.get('records',[]))}  "
          f"transactions={len(txns)}  cell_root={args.cell_root}  root={args.root}")
    for i, (slot, in_abs, out_abs) in enumerate(placement):
        rec = icm["records"][i]
        print(f"  rec {i}: cell {slot:<3} gs=0x{int(rec.get('gs',0)):03X}  "
              f"in=0x{in_abs:04X} out=0x{out_abs:04X}  {rec.get('_note','')}")
    for w in warnings:
        print(f"  [warn] {w}")

    if args.verify:
        ok, results, (spare, spare_clean) = verify(
            icm, txns, placement, cell_base=0, num_cells=args.num_cells)
        print("\n[ORACLE] replaying the stream through the top-latch + cell decode model:")
        for slot, want, got, armed, passed in results:
            print(f"  cell {slot:<3} topo want 0x{want:03X}  got 0x{got:03X}  "
                  f"armed={armed}  {'PASS' if passed else '** FAIL **'}")
        if spare is not None:
            print(f"  cell {spare:<3} (unused) stays unconfigured: "
                  f"{'PASS' if spare_clean else '** FAIL **'}  (exclusion)")
        print(f"\n[ORACLE] {'ALL PASS' if ok else '** FAILURE **'}")

    if args.emit:
        if args.emit == "tcl":
            text = emit_tcl(icm, txns, placement)
        elif args.emit == "tb":
            text = emit_tb(icm, txns, placement)
        else:
            text = emit_txt(txns)
        if args.out:
            with open(args.out, "w") as f:
                f.write(text)
            print(f"\n[emit] wrote {args.emit} -> {args.out}")
        else:
            print("\n" + text)


if __name__ == "__main__":
    main()
