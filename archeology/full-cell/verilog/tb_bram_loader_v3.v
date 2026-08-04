// tb_bram_loader_v3.v — first BRAM-driven loader proof (icmP format, one zone).
//
// Smallest-test-first before scaling to 2 zones / real BRAM timing / PCIe: prove
// that a sequence of (SET_TARGET, CMD_LOAD_AT, CMD_SET_METHOD, CMD_LOAD_DONE)
// words, read out of a behavioural "BRAM" one at a time and driven through the
// SAME top-level transport logic top_arria10_zone1_v3.v uses (load_target latch
// + cpu_addr_w mux — mirrored here, not duplicated by accident: this mirror is
// what caught the missing opcode-27 case in the real top file this session),
// loads several DIFFERENT cells with DIFFERENT topologies, and that the loader's
// write-counter only advances to the next cell on the REAL completion pulse
// (zone.emit_count incrementing after CMD_LOAD_DONE) — not a fixed delay.
//
// Deliberately simple BRAM model: zero read latency, one behavioural array.
// Modelling BRAM's registered read latency + the bridge-out-triggered read
// pipeline from last session is the NEXT test, once this one proves the
// sequencing and completion-gating are correct in principle.
`timescale 1ns/1ps
module tb_bram_loader_v3;
    reg clk=0, rst=0; always #5 clk=~clk;
    reg [31:0] cpu_bus=0, cpu_data=0; reg cpu_valid=0;

    // ── mirror of top_arria10_zone1_v3's target-latch transport ──────────────
    localparam [7:0] OP_SET_TARGET  = 8'd24;
    localparam [7:0] OP_LOAD_AT     = 8'd23;
    localparam [7:0] OP_LOAD_DONE   = 8'd27;
    localparam [7:0] METH_SET_LANE  = 8'd33; // used as the harmless "no methodology needed" cycle-2 pad below
    reg [15:0] load_target = 16'h0;
    always @(posedge clk) if (cpu_valid && cpu_bus[7:0]==OP_SET_TARGET) load_target <= cpu_data[15:0];
    // Mirrors the FIXED top_arria10_zone1_v3.v mux: cycle-2 words dispatch on the raw,
    // self-describing METH_SET_* opcodes (30-33) directly -- NOT a CMD_SET_METHOD(25)
    // wrapper, which has no case match in the v3.1 cell any more. Missing 30-33 here
    // was the actual bug: any opcode not in this whitelist falls through to
    // cpu_data[15:0], which SILENTLY CLOBBERS the held target address the next time
    // any host transaction (even a "no-op" cycle-2 pad) is issued.
    wire [15:0] cpu_addr_w = (cpu_bus[7:0]==8'd1)          ? cpu_data[31:16]
                           : (cpu_bus[7:0]==OP_LOAD_AT)    ? load_target
                           : (cpu_bus[7:0]==8'd2)          ? load_target // SET_INPUT_ADDR
                           : (cpu_bus[7:0]==8'd3)          ? load_target // SET_OUTPUT_ADDR
                           : (cpu_bus[7:0]==8'd30)         ? load_target // METH_SET_MASK
                           : (cpu_bus[7:0]==8'd31)         ? load_target // METH_SET_SHIFT_IN
                           : (cpu_bus[7:0]==8'd32)         ? load_target // METH_SET_SHIFT_OUT
                           : (cpu_bus[7:0]==8'd33)         ? load_target // METH_SET_LANE
                           : (cpu_bus[7:0]==OP_LOAD_DONE)  ? load_target
                           : cpu_data[15:0];
    wire preload_act = (cpu_bus[18:17]!=2'b00);
    wire cmd_valid_w = cpu_valid && (cpu_bus[7:0]!=8'd1) && ((cpu_bus[7:0]!=8'd0)||preload_act);

    // ── one zone, small cell count for a fast sim ─────────────────────────────
    localparam NUM_CELLS = 4;
    wire [1:0] tv=0; wire [31:0] ta=0, td=0;
    wire [15:0] zoa; wire [31:0] zod; wire zov;
    wire [15:0] armed,arrived,outset,emitc;
    wire [31:0] dbg_cl,dbg_ia,dbg_oa,dbg_ad,cyc;

    unicell_zone64_v3 #(.NUM_CELLS(NUM_CELLS), .NUM_BRIDGES(2), .ZONE_ID(0)) z (
        .clk(clk), .rst(rst),
        .cmd_bus(cpu_bus), .cmd_data(cpu_data), .cmd_valid(cmd_valid_w),
        .cpu_addr(cpu_addr_w), .cpu_data(cpu_data), .cpu_valid(cpu_valid),
        .out_addr(zoa), .out_data(zod), .out_valid(zov),
        .armed_count(armed), .arrived_count(arrived), .output_set_count(outset), .emit_count(emitc),
        .dbg0_cmd_latch(dbg_cl), .dbg0_input_addr(dbg_ia), .dbg0_output_addr(dbg_oa), .dbg0_a_data(dbg_ad),
        .cycle_count(cyc),
        .bridge_n_in_valid(tv), .bridge_n_in_addr(ta), .bridge_n_in_data(td),
        .bridge_n_out_valid(), .bridge_n_out_addr(), .bridge_n_out_data(),
        .bridge_s_in_valid(tv), .bridge_s_in_addr(ta), .bridge_s_in_data(td),
        .bridge_s_out_valid(), .bridge_s_out_addr(), .bridge_s_out_data(),
        .bridge_e_in_valid(tv), .bridge_e_in_addr(ta), .bridge_e_in_data(td),
        .bridge_e_out_valid(), .bridge_e_out_addr(), .bridge_e_out_data(),
        .bridge_w_in_valid(tv), .bridge_w_in_addr(ta), .bridge_w_in_data(td),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data()
    );

    // ── behavioural BRAM: icmP-style record stream, one 64-bit word (cmd_bus,cmd_data) ──
    // Layout per cell: [TARGET, CYCLE1(LOAD_AT), CYCLE2(SET_METHOD/NOP), CYCLE3(LOAD_DONE)]
    localparam NREC = 12; // 3 cells x 4 words
    reg [63:0] bram [0:NREC-1];
    localparam [31:0] AUTH_BUS = 32'h0; // auth_boot open (fresh cells, mask==0) -- no token needed

    task set_rec; input integer idx; input [31:0] cb, cd; begin
        bram[idx] = {cb, cd};
    end endtask

    initial begin
        // Cell 0: target=0, topology=XOR(0x0BC), cycle2=METH_SET_LANE(0) pad, done
        set_rec(0,  {8'h0, OP_SET_TARGET}, 32'h0000_0000);
        set_rec(1,  {8'h0, OP_LOAD_AT},    32'h0000_00BC);
        set_rec(2,  {8'h0, METH_SET_LANE}, 32'h0);              // lane_cut=0, no enable bit -- harmless pad
        set_rec(3,  {8'h0, OP_LOAD_DONE},  32'h0);
        // Cell 1: target=1, topology=AND(0x007)
        set_rec(4,  {8'h0, OP_SET_TARGET}, 32'h0000_0001);
        set_rec(5,  {8'h0, OP_LOAD_AT},    32'h0000_0007);
        set_rec(6,  {8'h0, METH_SET_LANE}, 32'h0);
        set_rec(7,  {8'h0, OP_LOAD_DONE},  32'h0);
        // Cell 2: target=2, topology=OR(0x024)
        set_rec(8,  {8'h0, OP_SET_TARGET}, 32'h0000_0002);
        set_rec(9,  {8'h0, OP_LOAD_AT},    32'h0000_0024);
        set_rec(10, {8'h0, METH_SET_LANE}, 32'h0);
        set_rec(11, {8'h0, OP_LOAD_DONE},  32'h0);
    end

    integer errors=0;
    task check32; input [31:0] got, want; input [127:0] msg; begin
        if (got===want) $display("  PASS: %0s (0x%08x)", msg, got);
        else begin $display("  FAIL: %0s got=0x%08x want=0x%08x", msg, got, want); errors=errors+1; end
    end endtask

    // ── loader FSM (behavioural task, not synthesisable — this is the sim proof
    //    that the SEQUENCE + completion-gating are right; the synthesisable FSM
    //    is the next build once this is confirmed) ──────────────────────────────
    integer ridx;
    reg [15:0] emit_before;
    integer wait_cycles;
    task issue_word; input [63:0] w; begin
        @(negedge clk); cpu_bus = w[63:32]; cpu_data = w[31:0]; cpu_valid = 1'b1;
        @(posedge clk); #1; cpu_valid = 1'b0;
        @(posedge clk); #1; // one settle cycle between words
    end endtask

    task load_one_cell; input integer base; input integer cellnum; begin
        issue_word(bram[base]);
        issue_word(bram[base+1]);
        issue_word(bram[base+2]);
        emit_before = emitc;
        issue_word(bram[base+3]);
        wait_cycles = 0;
        while (emitc == emit_before && wait_cycles < 20) begin
            @(posedge clk); #1; wait_cycles = wait_cycles + 1;
        end
        if (emitc == emit_before) begin
            $display("  FAIL: cell %0d never confirmed (emit_count did not advance)", cellnum);
            errors = errors + 1;
        end else begin
            case (cellnum)
                0: $display("  cell 0 confirmed after %0d cycle(s) (emit_count %0d -> %0d), latch52=%0d",
                             wait_cycles, emit_before, emitc, z.cells.cell_array[0].cell_inst.cmd_latch[52]);
                1: $display("  cell 1 confirmed after %0d cycle(s) (emit_count %0d -> %0d), latch52=%0d",
                             wait_cycles, emit_before, emitc, z.cells.cell_array[1].cell_inst.cmd_latch[52]);
                2: $display("  cell 2 confirmed after %0d cycle(s) (emit_count %0d -> %0d), latch52=%0d",
                             wait_cycles, emit_before, emitc, z.cells.cell_array[2].cell_inst.cmd_latch[52]);
            endcase
        end
    end endtask

    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        $display("=== BRAM LOADER (icmP, one zone, %0d cells) ===", NUM_CELLS);

        load_one_cell(0, 0);
        load_one_cell(4, 1);
        load_one_cell(8, 2);

        // ── verify each cell's topology landed on the RIGHT cell (hierarchical peek —
        //    sim-only introspection, same pattern the project's other testbenches use
        //    via dut.cmd_latch; here reaching through zone -> array -> per-cell) ──────
        check32(z.cells.cell_array[0].cell_inst.cmd_latch[9:0], 10'h0BC, "cell0 topology = XOR");
        check32(z.cells.cell_array[1].cell_inst.cmd_latch[9:0], 10'h007, "cell1 topology = AND");
        check32(z.cells.cell_array[2].cell_inst.cmd_latch[9:0], 10'h024, "cell2 topology = OR");
        check32(z.cells.cell_array[0].cell_inst.cmd_latch[52], 1'b1, "cell0 load-confirmed bit set");
        check32(z.cells.cell_array[1].cell_inst.cmd_latch[52], 1'b1, "cell1 load-confirmed bit set");
        check32(z.cells.cell_array[2].cell_inst.cmd_latch[52], 1'b1, "cell2 load-confirmed bit set");
        check32({16'h0,emitc}, 16'd3, "emit_count == 3 (one confirm per cell, no extras)");

        if (errors==0) $display(">>> BRAM LOADER PASS: 3 heterogeneous cells loaded through the real top-level transport, completion-gated");
        else $display(">>> BRAM LOADER FAIL: %0d errors", errors);
        $finish;
    end
endmodule
