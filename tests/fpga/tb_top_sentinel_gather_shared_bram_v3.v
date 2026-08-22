// tb_top_sentinel_gather_shared_bram_v3.v — points.md #430's own queue
// item 2, extension to the full mechanism: sim-first verification that
// a REAL HOST (simulated here via direct source-word injection, same
// technique as `tb_top_bram_icm_hostbridge_v1.v`) can drive the entire
// v2 mechanism (`top_sentinel_gather_shared_bram_v3.v`) end to end --
// ICM_LOAD all 4 cells, BRAM_WRITE the real preload data, UNFREEZE all
// 3 chains, then 12 real ADVANCE-driven rounds -- and get the EXACT
// SAME real results v2's own self-test FSM already proved
// (`points.md` #436), this time driven entirely by simulated "host"
// commands instead of a fixed internal state machine.
`timescale 1ns / 1ps

module tb_top_sentinel_gather_shared_bram_v3;

    reg CLK_100M = 0;
    always #5 CLK_100M = ~CLK_100M;   // 100 MHz

    wire LED0_N, LED1_N;

    top_sentinel_gather_shared_bram_v3 DUT (
        .CLK_100M(CLK_100M), .LED0_N(LED0_N), .LED1_N(LED1_N)
    );

    reg [90:0] stim_source = 91'h0;
    always @(*) force DUT.BRIDGE.source = stim_source;

    integer errors = 0;

    localparam [2:0] OP_NOP        = 3'd0;
    localparam [2:0] OP_BRAM_READ  = 3'd1;
    localparam [2:0] OP_BRAM_WRITE = 3'd2;
    localparam [2:0] OP_ICM_LOAD   = 3'd3;
    localparam [2:0] OP_UNFREEZE   = 3'd4;
    localparam [2:0] OP_ADVANCE    = 3'd5;

    // Same real SUPER_LATCH values v2's own proven self-test FSM used --
    // CFG_H1/H2/H3 (accumulators, inc_dir=N, downstream_mask=S/N/E
    // respectively) and CFG_Q (RAM core, matching v2's own real CFG_Q).
    localparam [79:0] CFG_H1 = {13'b0, 20'b0, 30'b0, {4'b0010, 4'b0000, 4'b0001}, 5'd3};
    localparam [79:0] CFG_H2 = {13'b0, 20'b0, 30'b0, {4'b0001, 4'b0000, 4'b0001}, 5'd3};
    localparam [79:0] CFG_H3 = {13'b0, 20'b0, 30'b0, {4'b0100, 4'b0000, 4'b0001}, 5'd3};
    localparam [79:0] CFG_Q  = {22'b0, {32'h0, 1'b0, 1'b0, 4'b1000, 4'b0001}, 5'd1};

    task send_cmd(input [2:0] opcode, input [1:0] target, input [3:0] addr, input [79:0] data);
        begin
            stim_source[79:0]  = data;
            stim_source[83:80] = addr;
            stim_source[85:84] = target;
            stim_source[88:86] = opcode;
            stim_source[89]    = 1'b0;
            @(posedge DUT.clk); #1;
            stim_source[89] = 1'b1;
            @(posedge DUT.clk); #1;
            stim_source[89] = 1'b0;
            @(posedge DUT.clk); #1;
        end
    endtask

    task snap_and_read(output [157:0] result);
        begin
            stim_source[90] = 1'b0;
            @(posedge DUT.clk); #1;
            stim_source[90] = 1'b1;
            @(posedge DUT.clk); #1;
            stim_source[90] = 1'b0;
            @(posedge DUT.clk); #1;
            result = DUT.BRIDGE.probe;
        end
    endtask

    reg [157:0] snap;

    // Matches v2's own proven expected_sum(visit) function exactly.
    function [31:0] expected_sum(input [1:0] visit);
        case (visit)
            2'd0: expected_sum = 32'd1;
            2'd1: expected_sum = 32'd2;
            2'd2: expected_sum = 32'd3;
            2'd3: expected_sum = 32'd4;
            default: expected_sum = 32'd0;
        endcase
    endfunction

    integer round_idx;

    initial begin
        #500;   // clear the real reset shift-register chain

        // ── Real "host" sequence: config every cell first ──
        send_cmd(OP_ICM_LOAD, 2'd0, 4'd0, CFG_H1);
        send_cmd(OP_ICM_LOAD, 2'd1, 4'd0, CFG_H2);
        send_cmd(OP_ICM_LOAD, 2'd2, 4'd0, CFG_H3);
        send_cmd(OP_ICM_LOAD, 2'd3, 4'd0, CFG_Q);
        snap_and_read(snap);
        if (!snap[42]) begin
            errors = errors + 1;
            $display("FAIL: icm_load_done not observed after real ICM_LOAD sequence");
        end else begin
            $display("PASS: all 4 cells ICM_LOAD'd, icm_load_done confirmed");
        end

        // ── Real preload: chain 1's block at addr 0-3 (100-103), chain
        // 2's at 4-7 (200-203), chain 3's at 8-11 (300-303) -- matching
        // v2's own proven block-partitioned addressing exactly. ──
        for (round_idx = 0; round_idx < 4; round_idx = round_idx + 1) begin
            send_cmd(OP_BRAM_WRITE, 2'd0, round_idx[3:0],       {40'h0, 40'd100 + round_idx});
            send_cmd(OP_BRAM_WRITE, 2'd0, round_idx[3:0] + 4'd4, {40'h0, 40'd200 + round_idx});
            send_cmd(OP_BRAM_WRITE, 2'd0, round_idx[3:0] + 4'd8, {40'h0, 40'd300 + round_idx});
        end
        $display("PASS: real preload of all 12 BRAM addresses issued");

        // ── Real per-chain unfreeze -- kicks off the freeze/unfreeze
        // state machine, matching v2's own proven sequence. ──
        send_cmd(OP_UNFREEZE, 2'd0, 4'd0, 80'h0);
        send_cmd(OP_UNFREEZE, 2'd1, 4'd0, 80'h0);
        send_cmd(OP_UNFREEZE, 2'd2, 4'd0, 80'h0);
        snap_and_read(snap);
        if (!snap[43]) begin
            errors = errors + 1;
            $display("FAIL: unfreeze_done not observed after real UNFREEZE sequence");
        end else begin
            $display("PASS: all 3 chains UNFREEZE'd, unfreeze_done confirmed");
        end

        // ── Real 12 rounds -- one ADVANCE per round, matching v2's own
        // proven 4-visits-per-chain round-robin exactly. Wait generously
        // between rounds (real fabric completion is a handful of
        // cycles; real JTAG round-trip latency in practice is orders of
        // magnitude slower, so this margin reflects real usage, not an
        // artificial sim convenience). ──
        for (round_idx = 0; round_idx < 12; round_idx = round_idx + 1) begin
            send_cmd(OP_ADVANCE, 2'd0, 4'd0, 80'h0);
            repeat (60) @(posedge DUT.clk);   // real round completion margin
            snap_and_read(snap);
            if (snap[93:62] !== expected_sum(round_idx / 3)) begin
                errors = errors + 1;
                $display("FAIL: round %0d -- q_data_out_n=%0d, expected %0d",
                          round_idx, snap[93:62], expected_sum(round_idx / 3));
            end
        end
        if (errors == 0) $display("PASS: all 12 real rounds produced the correct running result");

        // ── Real, direct sentinel-flag confirmation -- every chain
        // must have genuinely completed its own block and reported it,
        // same real check v2's own self-test FSM made internally. ──
        if (!snap[50] || !snap[54] || !snap[58]) begin
            errors = errors + 1;
            $display("FAIL: not every chain's own need_data flag set at completion");
        end
        if (!snap[51] || !snap[55] || !snap[59]) begin
            errors = errors + 1;
            $display("FAIL: not every chain's own results_ready flag set at completion");
        end
        if (snap[53] || snap[57] || snap[61]) begin
            errors = errors + 1;
            $display("FAIL: at least one chain reports a real error at completion");
        end
        if (errors == 0) begin
            $display("PASS: all 3 chains report real, correct completion status (need_data/results_ready set, no errors)");
        end

        if (errors == 0) begin
            $display("PASS: real host-driven full mechanism (v3) -- all checks passed");
        end else begin
            $display("FAIL: %0d error(s) found", errors);
        end
        $finish;
    end

endmodule
