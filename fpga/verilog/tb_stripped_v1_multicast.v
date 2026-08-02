// tb_stripped_v1_multicast.v — genuine multi-target routing: U -> R -> {D1,D2}
// simultaneously (routing_mask targeting South AND East at once). Freezes ONE
// of the two targets (D1) and checks: R must wait for BOTH D1 and D2 to ack
// before its own ready recovers (partial ack from D2 alone must NOT be
// enough) — and the stall must cascade all the way back to U, not just stop
// at R. Then releases D1 and confirms the whole thing drains. Points.md #93.
`timescale 1ns / 1ps

module tb_stripped_v1_multicast;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;
    localparam [9:0] TOPO_NOR = 10'h004;

    reg cfgU=0, cfgR=0, cfgD1=0, cfgD2=0;
    reg [127:0] cfgU_d=0, cfgR_d=0, cfgD1_d=0, cfgD2_d=0;
    reg freezeD1 = 0;

    // ── Seed injection at U's north port ──
    reg [31:0] seed_val = 0;
    reg        seed_arrived = 0;

    wire [31:0] u2r_data, r2d1_data, r2d2_data;
    wire        u2r_fire, r2d1_fire, r2d2_fire;
    wire        rReady, d1Ready, d2Ready;
    wire        u2r_ack, r2d1_ack, r2d2_ack;

    // ── U: feeds R only ──
    reg [31:0] u_data_in_n = 32'h0;
    wire [31:0] u_dout_s; wire u_fs, u_ready;
    unicell_stripped_v1 #(.CELL_ID(16'h0001)) U (
        .clk(clk), .rst(rst), .cfg_valid(cfgU), .cfg_data(cfgU_d),
        .data_in_n(u_data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(seed_arrived), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(u_dout_s), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(u_fs), .fire_e(), .fire_w(),
        .ready_out(u_ready),
        .ready_in_n(1'b1), .ready_in_s(rReady), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(u2r_ack), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(1'b0),

        .hold_in(1'b0)
    );
    // seed uses U's own north input directly (data_in_n tied to seed_val)
    // -- handled via a small always block below overriding data_in_n port;
    // simpler: wire seed straight into a dedicated input.
    assign u2r_data = u_dout_s;
    assign u2r_fire = u_fs;

    // ── R: receives on North (from U), targets BOTH South (D1) and East (D2) ──
    wire [31:0] r_dout_s, r_dout_e; wire r_fs, r_fe, r_ready;
    unicell_stripped_v1 #(.CELL_ID(16'h0002)) R (
        .clk(clk), .rst(rst), .cfg_valid(cfgR), .cfg_data(cfgR_d),
        .data_in_n(u2r_data), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(u2r_fire), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(r_dout_s), .data_out_e(r_dout_e), .data_out_w(),
        .fire_n(), .fire_s(r_fs), .fire_e(r_fe), .fire_w(),
        .ready_out(r_ready),
        .ready_in_n(1'b1), .ready_in_s(d1Ready), .ready_in_e(d2Ready), .ready_in_w(1'b1),
        .ack_out_n(u2r_ack), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(r2d1_ack), .ack_in_e(r2d2_ack), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(1'b0),

        .hold_in(1'b0)
    );
    assign r2d1_data = r_dout_s;
    assign r2d1_fire = r_fs;
    assign r2d2_data = r_dout_e;
    assign r2d2_fire = r_fe;
    assign rReady = r_ready;

    // ── D1: leaf, receives on North -- THIS ONE GETS FROZEN ──
    wire d1_ready;
    unicell_stripped_v1 #(.CELL_ID(16'h0003)) D1 (
        .clk(clk), .rst(rst), .cfg_valid(cfgD1), .cfg_data(cfgD1_d),
        .data_in_n(r2d1_data), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(r2d1_fire), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(),
        .ready_out(d1_ready),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(r2d1_ack), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(freezeD1),   // <── THE FREEZE UNDER TEST

        .hold_in(1'b0)
    );
    assign d1Ready = d1_ready;

    // ── D2: leaf, receives on West -- stays live the whole time ──
    wire d2_ready;
    unicell_stripped_v1 #(.CELL_ID(16'h0004)) D2 (
        .clk(clk), .rst(rst), .cfg_valid(cfgD2), .cfg_data(cfgD2_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(r2d2_data),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(r2d2_fire),
        .data_out_n(), .data_out_s(), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(),
        .ready_out(d2_ready),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(r2d2_ack),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(1'b0),

        .hold_in(1'b0)
    );
    assign d2Ready = d2_ready;

    task seed(input [31:0] v);
        begin
            u_data_in_n = v; seed_arrived = 1;
            @(posedge clk); #1;
            seed_arrived = 0;
        end
    endtask

    task report(input [127:0] label);
        $display("[t=%0t] %0s | U:ready=%b arrived=%b | R:ready=%b arrived=%b | D1:ready=%b frozen=%b | D2:ready=%b",
                  $time, label, u_ready, U.a_arrived, r_ready, R.a_arrived, d1_ready, freezeD1, d2_ready);
    endtask

    initial begin
        $dumpfile("/tmp/tb_stripped_v1_multicast.vcd");
        $dumpvars(0, tb_stripped_v1_multicast);

        rst = 1; repeat(3) @(posedge clk); rst = 0; @(posedge clk);

        cfgU_d=128'h0;  cfgU_d[9:0]=TOPO_NOR;  cfgU_d[69:64]=6'b000010; cfgU=1;  @(posedge clk); #1; cfgU=0;
        cfgR_d=128'h0;  cfgR_d[9:0]=TOPO_NOR;  cfgR_d[69:64]=6'b000110; cfgR=1;  @(posedge clk); #1; cfgR=0;  // S+E
        cfgD1_d=128'h0; cfgD1_d[9:0]=TOPO_NOR; cfgD1_d[69:64]=6'b000000; cfgD1=1; @(posedge clk); #1; cfgD1=0;
        cfgD2_d=128'h0; cfgD2_d[9:0]=TOPO_NOR; cfgD2_d[69:64]=6'b000000; cfgD2=1; @(posedge clk); #1; cfgD2=0;
        @(posedge clk);
        report("config done       ");

        // Round 1 (no freeze): U fires twice into R -> R multicasts ONCE to
        // BOTH D1 and D2 -> confirm BOTH ack and R recovers cleanly.
        seed(32'hAAAA0000);
        seed(32'h0000FFFF);
        repeat(3) @(posedge clk); report("after U fire 1     ");

        seed(32'h11110000);
        seed(32'h0000EEEE);
        repeat(3) @(posedge clk); report("after R multicast 1");

        // Freeze D1 now.
        freezeD1 = 1;
        report("D1 FROZEN          ");

        // Round 2: feed U with TWO FULL fires (4 seeds) so R gets its two
        // round-2 deliveries and actually ATTEMPTS a second multicast --
        // this is the scenario under test, not merely a re-capture.
        seed(32'h55550000);
        seed(32'h0000CCCC);           // U's round-2 fire #1 -> R captures (1st arrival)
        repeat(3) @(posedge clk); report("mid round 2 (R cap)");

        seed(32'h33330000);
        seed(32'h0000DDDD);           // U's round-2 fire #2 -> R's 2nd arrival -> R ATTEMPTS multicast
        repeat(5) @(posedge clk); report("during freeze      ");
        repeat(5) @(posedge clk); report("still frozen       ");

        // Try feeding U yet again while still frozen -- U itself should now
        // be unable to progress either (the cascade reaching all the way
        // back), so this delivery should just sit unconsumed by R.
        seed(32'h77770000);
        seed(32'h0000BBBB);
        repeat(5) @(posedge clk); report("U also stuck?      ");

        // Release D1.
        freezeD1 = 0;
        repeat(5) @(posedge clk); report("D1 RELEASED        ");
        repeat(5) @(posedge clk); report("settled after release");

        // U's own attempted 2nd-arrival (0x0000BBBB) never got retried
        // automatically -- it was a raw testbench pulse, not a real
        // neighboring cell's persistent pending_ack-held offer (#91). Retry
        // it explicitly now that R is genuinely ready, to confirm the fire
        // completes once the actual blocking condition is gone.
        seed(32'h0000BBBB);
        repeat(3) @(posedge clk); report("U retry after release");

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
