// tb_top_bram_icm_hostbridge_v1.v — points.md #430's own queue item 2:
// sim-first verification of `host_bridge_bram_icm_v1.v` +
// `top_bram_icm_hostbridge_v1.v` before any real Quartus build, per
// this project's own standing "sim-first, then silicon" discipline.
// Drives the DUT's own `source` wire directly via `force`, exactly as
// `tb_sentinel_issp_bridge_v1.v` already does for the existing bridge.
`timescale 1ns / 1ps

module tb_top_bram_icm_hostbridge_v1;

    reg CLK_100M = 0;
    always #5 CLK_100M = ~CLK_100M;   // 100 MHz

    wire LED0_N, LED1_N;

    top_bram_icm_hostbridge_v1 DUT (
        .CLK_100M(CLK_100M), .LED0_N(LED0_N), .LED1_N(LED1_N)
    );

    // ── Drive the bridge's own "source" side directly, same technique
    // as `tb_sentinel_issp_bridge_v1.v`. ──
    reg [90:0] stim_source = 91'h0;
    always @(*) force DUT.BRIDGE.source = stim_source;

    integer errors = 0;

    localparam [2:0] OP_NOP        = 3'd0;
    localparam [2:0] OP_BRAM_READ  = 3'd1;
    localparam [2:0] OP_BRAM_WRITE = 3'd2;
    localparam [2:0] OP_ICM_LOAD   = 3'd3;

    task send_cmd(input [2:0] opcode, input [3:0] addr, input [79:0] data);
        begin
            stim_source[79:0]  = data;
            stim_source[83:80] = addr;
            stim_source[85:84] = 2'd0;
            stim_source[88:86] = opcode;
            stim_source[89]    = 1'b0;
            @(posedge DUT.clk); #1;
            stim_source[89] = 1'b1;   // cmd_go rising edge
            @(posedge DUT.clk); #1;
            stim_source[89] = 1'b0;
            @(posedge DUT.clk); #1;
        end
    endtask

    task snap_and_read(output [111:0] result);
        begin
            stim_source[90] = 1'b0;
            @(posedge DUT.clk); #1;
            stim_source[90] = 1'b1;   // snap_req rising edge
            @(posedge DUT.clk); #1;
            stim_source[90] = 1'b0;
            @(posedge DUT.clk); #1;
            result = DUT.BRIDGE.probe;
        end
    endtask

    reg [111:0] snap;

    initial begin
        // Hold reset through the real reset shift-register chain (4
        // cycles at the divided clk, plus div_cnt itself needs to
        // toggle -- give it generous margin).
        #500;

        // ── PART 1: real BRAM write then read-back, confirming the
        // write genuinely landed at the written address and nowhere
        // else (write addr 5, value 0xABCD; also touch addr 6 with a
        // different value to catch any address-decode bug). ──
        send_cmd(OP_BRAM_WRITE, 4'd5, {40'h0, 40'hABCD});
        send_cmd(OP_BRAM_WRITE, 4'd6, {40'h0, 40'h1234});

        send_cmd(OP_BRAM_READ, 4'd5, 80'h0);
        snap_and_read(snap);
        if (snap[39:0] !== 40'hABCD || snap[40] !== 1'b1) begin
            errors = errors + 1;
            $display("FAIL: BRAM read addr 5 -- got rdata=%h valid=%b, expected 0xABCD/1", snap[39:0], snap[40]);
        end else begin
            $display("PASS: BRAM read addr 5 correct (0x%h)", snap[39:0]);
        end

        send_cmd(OP_BRAM_READ, 4'd6, 80'h0);
        snap_and_read(snap);
        if (snap[39:0] !== 40'h1234 || snap[40] !== 1'b1) begin
            errors = errors + 1;
            $display("FAIL: BRAM read addr 6 -- got rdata=%h valid=%b, expected 0x1234/1", snap[39:0], snap[40]);
        end else begin
            $display("PASS: BRAM read addr 6 correct (0x%h)", snap[39:0]);
        end

        // Confirm write_done was real too (checked on the write's own
        // immediate snap, not the later read's).
        send_cmd(OP_BRAM_WRITE, 4'd7, {40'h0, 40'hFEED});
        snap_and_read(snap);
        if (snap[41] !== 1'b1) begin
            errors = errors + 1;
            $display("FAIL: bram_write_done not observed after a real write");
        end else begin
            $display("PASS: bram_write_done observed correctly");
        end

        // ── PART 2: real ICM load -- configure the driven cell as the
        // accumulator core (SEL_ACC=3), confirm status_core_select
        // reads back correctly. Matches the real SUPER_LATCH layout
        // already proven in `top_sentinel_gather_shared_bram_v2.v`'s
        // own CFG_H1 (core_select in bits [4:0]). ──
        send_cmd(OP_ICM_LOAD, 4'd0, {75'h0, 5'd3});   // core_select = SEL_ACC
        snap_and_read(snap);
        if (snap[42] !== 1'b1) begin
            errors = errors + 1;
            $display("FAIL: icm_load_done not observed after a real ICM_LOAD");
        end else begin
            $display("PASS: icm_load_done observed correctly");
        end
        if (snap[47:43] !== 5'd3) begin
            errors = errors + 1;
            $display("FAIL: status_core_select readback -- got %0d, expected 3 (SEL_ACC)", snap[47:43]);
        end else begin
            $display("PASS: status_core_select readback correct (SEL_ACC=3)");
        end

        // Real second load, switching to a different core (SEL_LATCH=5),
        // confirming the channel isn't a one-shot fluke.
        send_cmd(OP_ICM_LOAD, 4'd0, {75'h0, 5'd5});
        snap_and_read(snap);
        if (snap[47:43] !== 5'd5) begin
            errors = errors + 1;
            $display("FAIL: second ICM_LOAD readback -- got %0d, expected 5 (SEL_LATCH)", snap[47:43]);
        end else begin
            $display("PASS: second ICM_LOAD readback correct (SEL_LATCH=5)");
        end

        // ── PART 3: real cmd_count sanity -- confirms the command
        // channel counts every real command issued so far (6 total:
        // 3 BRAM writes, 2 BRAM reads, 2 ICM loads = 7). ──
        if (snap[79:48] !== 32'd7) begin
            errors = errors + 1;
            $display("FAIL: cmd_count -- got %0d, expected 7", snap[79:48]);
        end else begin
            $display("PASS: cmd_count correct (7)");
        end

        if (errors == 0) begin
            $display("PASS: all real BRAM and ICM host-bridge checks passed");
        end else begin
            $display("FAIL: %0d error(s) found", errors);
        end
        $finish;
    end

endmodule
