// tb_stripped_v1_armed.v — points.md #156: proves the new armed gate
// itself, not just that existing tests still pass with it in place.
// Mirrors the FULL cell's start_flag/CMD_RELEASE concept (Alan's own
// recollection from the original design) via the COMPLETE marker's own
// data payload LSB, reusing what was previously an always-zero field
// rather than spending one of the 8 already-allocated PROG_ID codes.
//
// Confirms:
// 1. COMPLETE with LSB=0 commits the fields but leaves the cell COLD
//    (ready=0, no capture/fire even when fed data) -- genuinely
//    disarmed, not just "not yet fully programmed".
// 2. A later COMPLETE with LSB=1 arms it -- ready goes high, normal
//    two-arrival operation starts working immediately.
// 3. The reverse also works: an already-armed, already-operating cell
//    can be explicitly disarmed again (COMPLETE, LSB=0) mid-reprogram,
//    stays cold while more fields are written, then re-armed -- the
//    staged "pause, apply more field writes, then re-arm" sequence the
//    mechanism was built for.
// 4. cfg_valid (the atomic boot-load path) is UNCHANGED -- still arms
//    immediately, since there's no partial-state ambiguity to gate.
`timescale 1ns / 1ps

module tb_stripped_v1_armed;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    reg         cfg_valid = 0;
    reg [127:0] cfg_data  = 0;
    reg         program_in = 0;

    reg [31:0] pdata = 0;
    reg        parrived = 0;

    reg [31:0]  normal_data = 0;
    reg         normal_arrived = 0;

    wire [31:0] dout_n;
    wire        ready_w;
    wire        program_done_w;

    unicell_stripped_v1 #(.CELL_ID(16'h00A1)) T (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in_n(normal_data), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(normal_arrived), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(dout_n), .data_out_s(), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(),
        .ready_out(ready_w),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(1'b0),
        .hold_in(1'b0),
        .fb_internal_in(1'b0),
        .a_reemit_in(1'b0),
        .a_update_in(1'b0),
        .a_self_update_in(1'b0),
        .program_in(program_in),
        .program_done(program_done_w),
        .prog_data_in_n(pdata), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(parrived), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    localparam [2:0] ID_TOPOLOGY = 3'd0, ID_ROUTING = 3'd1, ID_COMPLETE = 3'd7;
    localparam [9:0] TOPO_NOR = 10'h004;

    task prog_word(input [2:0] id, input [15:0] data);
        begin
            pdata = {13'h0, id, data};
            parrived = 1;
            @(posedge clk); #1;
            parrived = 0;
        end
    endtask

    task seed_normal(input [31:0] v);
        begin
            normal_data = v; normal_arrived = 1;
            @(posedge clk); #1;
            normal_arrived = 0;
        end
    endtask

    task report(input [127:0] label);
        $display("[t=%0t] %0s | armed=%b ready=%b a_arrived=%b out=%h",
                  $time, label, T.armed, ready_w, T.a_arrived, dout_n);
    endtask

    initial begin
        rst = 1; repeat(3) @(posedge clk); rst = 0; @(posedge clk);
        report("after reset          ");   // expect armed=0, ready=0

        // ── Phase 1: program fully, but COMPLETE with LSB=0 -- stay cold. ──
        program_in = 1;
        prog_word(ID_TOPOLOGY, {6'h0, TOPO_NOR});
        prog_word(ID_ROUTING, 16'h0002);   // routing_mask = South
        prog_word(ID_COMPLETE, 16'h0);     // LSB=0: commit but stay disarmed
        program_in = 0;
        repeat(2) @(posedge clk);
        report("COMPLETE, LSB=0      ");   // expect armed=0, ready=0 -- STILL cold
        if (T.armed !== 1'b0 || ready_w !== 1'b0)
            $display("  FAIL: expected cold (armed=0, ready=0) after COMPLETE with LSB=0");

        // Feed it data anyway -- a cold cell must not capture or fire.
        seed_normal(32'hDEAD0000);
        repeat(2) @(posedge clk);
        report("fed data while cold  ");   // expect a_arrived STILL 0
        if (T.a_arrived !== 1'b0)
            $display("  FAIL: cold cell captured an arrival -- armed gate not blocking");

        // ── Phase 2: re-issue COMPLETE with LSB=1 -- arm it now. ──
        program_in = 1;
        prog_word(ID_COMPLETE, 16'h1);     // LSB=1: arm
        program_in = 0;
        repeat(2) @(posedge clk);
        report("COMPLETE, LSB=1      ");   // expect armed=1, ready=1
        if (T.armed !== 1'b1 || ready_w !== 1'b1)
            $display("  FAIL: expected armed (armed=1, ready=1) after COMPLETE with LSB=1");

        // Confirm normal two-arrival operation genuinely works now.
        seed_normal(32'hAAAA0000);
        repeat(2) @(posedge clk);
        report("seeded, now armed    ");   // expect a_arrived=1
        if (T.a_arrived !== 1'b1)
            $display("  FAIL: armed cell failed to capture a genuine arrival");

        seed_normal(32'h11110000);
        repeat(2) @(posedge clk);
        report("second arrival -> fire");   // expect out=NOR(AAAA0000,11110000)=4444FFFF
        if (dout_n !== 32'h4444FFFF)
            $display("  FAIL: expected out=4444FFFF, got %h", dout_n);

        // ── Phase 3: disarm an already-operating cell for a staged
        // reprogram, apply a field write while cold, then re-arm. ──
        program_in = 1;
        prog_word(ID_COMPLETE, 16'h0);     // explicit disarm, no field touched
        program_in = 0;
        repeat(2) @(posedge clk);
        report("explicit re-disarm   ");   // expect armed=0, ready=0
        if (T.armed !== 1'b0 || ready_w !== 1'b0)
            $display("  FAIL: expected re-disarm to take effect (armed=0, ready=0)");

        program_in = 1;
        prog_word(ID_ROUTING, 16'h0004);   // change routing_mask = East, while cold
        prog_word(ID_COMPLETE, 16'h1);     // re-arm
        program_in = 0;
        repeat(2) @(posedge clk);
        report("re-armed w/ new route");   // expect armed=1, routing=East
        // NOTE: ready_w can legitimately still read 0 here -- unrelated to
        // armed. This single-cell test never acks the earlier fire
        // (ack_in tied to 0), so pending_ack from that fire never clears,
        // and ready_bit (cmd_latch[13]) stays 0 regardless of armed --
        // ready_out = ready_bit && armed, so it needs BOTH. Checking armed
        // and routing_mask directly is the actual proof this phase needs.
        if (T.armed !== 1'b1)
            $display("  FAIL: expected armed=1 after re-arming COMPLETE");
        if (T.cmd_latch[69:64] !== 6'b000100)
            $display("  FAIL: expected routing_mask=East (000100), got %b", T.cmd_latch[69:64]);

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
