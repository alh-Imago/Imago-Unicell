// tb_pcie_bram_v3.v — PCIe stand-in (behavioural): burst-load a program into BRAM,
// let it run briefly, burst-read the result back out. The real PCIe hard IP only
// exists in Quartus's IP catalog (nothing to simulate in iverilog); this models
// the INTERFACE SHAPE a DMA engine presents -- address+data+valid, back-to-back,
// no per-word host round-trip -- so the protocol proves out now and the real IP
// swaps in later without touching it.
//
// Three phases, one cell, through the real top-level transport (mirrored, same
// as tb_bram_loader_v3.v):
//   1. BURST WRITE  -- stream the icmP config (SET_TARGET, SET_OUTPUT_ADDR,
//      LOAD_AT+start_flag, methodology pad, LOAD_DONE) into BRAM in one go,
//      one word per cycle, no settle gaps -- the throughput case a real DMA
//      buys you, contrasted with the one-word-then-settle style used in the
//      first loader test.
//   2. RUN -- preload operand A (CMD_SWAP_AB, already confirmed usable in RUN
//      state), inject operand B (DATA_WRITE), let the two-arrival XOR fire.
//   3. BURST READ -- a "PCIe capture" watches the zone's fired output landing
//      at a chosen capture address, writes it into a results BRAM; the test
//      then burst-reads that results BRAM back to the "host" side.
`timescale 1ns/1ps
module tb_pcie_bram_v3;
    reg clk=0, rst=0; always #5 clk=~clk;
    reg [31:0] cpu_bus=0, cpu_data=0; reg cpu_valid=0;

    // ── mirror of top_arria10_zone1_v3's target-latch transport (post-fix) ───
    localparam [7:0] OP_SET_TARGET     = 8'd24;
    localparam [7:0] OP_LOAD_AT        = 8'd23;
    localparam [7:0] OP_SET_OUTPUT_ADDR= 8'd3;
    localparam [7:0] OP_LOAD_DONE      = 8'd27;
    localparam [7:0] OP_SWAP_AB        = 8'd18;
    localparam [7:0] METH_SET_LANE     = 8'd33;
    reg [15:0] load_target = 16'h0;
    always @(posedge clk) if (cpu_valid && cpu_bus[7:0]==OP_SET_TARGET) load_target <= cpu_data[15:0];
    wire [15:0] cpu_addr_w = (cpu_bus[7:0]==8'd1)              ? cpu_data[31:16] // DATA_WRITE
                           : (cpu_bus[7:0]==OP_LOAD_AT)        ? load_target
                           : (cpu_bus[7:0]==8'd2)              ? load_target     // SET_INPUT_ADDR
                           : (cpu_bus[7:0]==OP_SET_OUTPUT_ADDR)? load_target
                           : (cpu_bus[7:0]==8'd30)             ? load_target     // METH_SET_MASK
                           : (cpu_bus[7:0]==8'd31)             ? load_target     // METH_SET_SHIFT_IN
                           : (cpu_bus[7:0]==8'd32)             ? load_target     // METH_SET_SHIFT_OUT
                           : (cpu_bus[7:0]==METH_SET_LANE)     ? load_target
                           : (cpu_bus[7:0]==OP_LOAD_DONE)      ? load_target
                           : cpu_data[15:0];
    wire preload_act = (cpu_bus[18:17]!=2'b00);
    wire cmd_valid_w = cpu_valid && (cpu_bus[7:0]!=8'd1) && ((cpu_bus[7:0]!=8'd0)||preload_act);

    // ── one zone ───────────────────────────────────────────────────────────
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

    // ── PCIe capture: watches the zone's fired output land at CAPTURE_ADDR, ──
    // writes it into a results BRAM -- this is the "DMA read" side, entirely
    // passive from the fabric's point of view (no cell at this address).
    localparam [15:0] CAPTURE_ADDR = 16'h1000;
    localparam NRESULTS = 8;
    reg [31:0] results_bram [0:NRESULTS-1];
    integer result_wr_ptr;
    initial result_wr_ptr = 0;
    always @(posedge clk) begin
        if (zov && zoa==CAPTURE_ADDR && result_wr_ptr < NRESULTS) begin
            results_bram[result_wr_ptr] <= zod;
            result_wr_ptr <= result_wr_ptr + 1;
        end
    end

    // ── config BRAM (icmP): SET_TARGET, SET_OUTPUT_ADDR(capture), ────────────
    // LOAD_AT (topology=XOR, start_flag=1 so the cell is armed), methodology
    // pad, LOAD_DONE. One cell (CELL_ID=0).
    localparam NCONF = 5;
    reg [63:0] config_bram [0:NCONF-1];
    initial begin
        config_bram[0] = {{8'h0, OP_SET_TARGET},      32'h0000_0000};
        config_bram[1] = {{8'h0, OP_SET_OUTPUT_ADDR}, {16'h0, CAPTURE_ADDR}};
        config_bram[2] = {{8'h0, OP_LOAD_AT},          32'h0000_0800 | 32'h0000_00BC}; // start_flag(bit11)=1, topology=XOR(0x0BC)
        config_bram[3] = {{8'h0, METH_SET_LANE},       32'h0};
        config_bram[4] = {{8'h0, OP_LOAD_DONE},        32'h0};
    end

    integer errors=0;
    task check32; input [31:0] got, want; input [127:0] msg; begin
        if (got===want) $display("  PASS: %0s (0x%08x)", msg, got);
        else begin $display("  FAIL: %0s got=0x%08x want=0x%08x", msg, got, want); errors=errors+1; end
    end endtask

    // ── PCIe-style burst write: back-to-back, one word per cycle, no settle ──
    // gap between words -- the throughput case (contrast with the first loader
    // test's word-then-settle style). Relies on the addressing fix from last
    // commit: SET_TARGET's own cycle already updates bus_addr, so the very
    // next cycle's word sees the correct (1-cycle-registered) address.
    integer bi;
    task pcie_burst_write; input integer n; input integer base_idx; begin
        for (bi = 0; bi < n; bi = bi + 1) begin
            @(negedge clk);
            cpu_bus  = config_bram[base_idx+bi][63:32];
            cpu_data = config_bram[base_idx+bi][31:0];
            cpu_valid = 1'b1;
        end
        @(negedge clk); cpu_valid = 1'b0; // one cycle after the last word to drop valid cleanly
    end endtask

    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        $display("=== PCIe STAND-IN: burst-load, run, burst-read-back ===");

        // ── PHASE 1: burst write the whole config in one streaming pass ──────
        pcie_burst_write(NCONF, 0);
        repeat(4) @(posedge clk); #1; // let LOAD_DONE's completion pulse (1-2 cyc buffered) land
        check32({16'h0,emitc}, 16'd1, "phase1: one completion pulse (cell 0 confirmed)");
        check32(z.cells.cell_array[0].cell_inst.cmd_latch[9:0], 10'h0BC, "phase1: cell0 topology = XOR");
        check32({31'h0,z.cells.cell_array[0].cell_inst.cmd_latch[22]}, 32'h1, "phase1: cell0 armed (start_flag)");
        check32({16'h0,z.cells.cell_array[0].cell_inst.output_address}, {16'h0,CAPTURE_ADDR}, "phase1: cell0 output_address = capture address");

        // ── PHASE 2: run it -- preload A via CMD_SWAP_AB, inject B via DATA_WRITE ──
        // A = 0x0A5 (13-bit payload of SWAP_AB), targeted at cell 0 via the normal
        // run-mode addr_match (input_address, default = CELL_ID = 0 here).
        @(negedge clk); cpu_bus = {8'h0, OP_SWAP_AB}; cpu_data = 32'h0000_00A5; cpu_valid = 1'b1;
        @(posedge clk); #1; cpu_valid = 1'b0;
        repeat(2) @(posedge clk); #1;
        check32(z.cells.cell_array[0].cell_inst.a_data, 32'h0000_00A5, "phase2: A preloaded via CMD_SWAP_AB");
        check32({31'h0,z.cells.cell_array[0].cell_inst.a_arrived}, 32'h1, "phase2: a_arrived set after preload");

        // B = 0x00F0, DATA_WRITE targets input_address=0 (address rides cpu_data[31:16]=0,
        // so the injected value's own upper 16 bits are necessarily 0 -- existing convention).
        @(negedge clk); cpu_bus = {8'h0, 8'h01}; cpu_data = 32'h0000_00F0; cpu_valid = 1'b1;
        @(posedge clk); #1; cpu_valid = 1'b0;
        // Fire propagates: two-arrival trigger -> cell out_valid (cyc N) -> array
        // wired-OR bus (same cyc) -> zone's registered out_valid (cyc N+1). Wait
        // enough cycles for the registered zone-level out_valid to land.
        repeat(8) @(posedge clk); #1;

        // ── PHASE 3: burst-read the result back ("host" side) ────────────────
        check32({16'h0,result_wr_ptr}, 32'h1, "phase3: exactly one result captured at CAPTURE_ADDR");
        check32(results_bram[0], (32'h0A5 ^ 32'h0F0), "phase3: captured result = XOR(0xA5,0xF0) = 0x55");

        if (errors==0) $display(">>> PCIe STAND-IN PASS: burst-load -> run -> burst-read-back, all correct");
        else $display(">>> PCIe STAND-IN FAIL: %0d errors", errors);
        $finish;
    end
endmodule
