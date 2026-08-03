// tb_stripped_v1_ring.v — A GENUINE 3-CELL RING (A->B->C->A, South-to-North
// all the way around, closing the loop), with a freeze applied mid-flight to
// one cell (B) — checking that it backs up everything behind it, and that
// releasing it lets the whole ring drain and continue. Points.md #92.
// NOT yet run at file-creation time — this is the actual measurement.
`timescale 1ns / 1ps

module tb_stripped_v1_ring;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [9:0] TOPO_NOR = 10'h004;

    // ── Config ports ──
    reg cfgA=0, cfgB=0, cfgC=0;
    reg [127:0] cfgA_d=0, cfgB_d=0, cfgC_d=0;

    // ── Freeze control ──
    reg freezeB = 0;

    // ── Ring interconnect: A.south -> B.north, B.south -> C.north,
    // C.south -> A.north (closes the loop). ──
    wire [31:0] a2b_data, b2c_data, c2a_data;
    wire        a2b_fire, b2c_fire, c2a_fire;
    wire        aR,bR,cR;                 // ready_out of A/B/C
    wire        a2b_ack, b2c_ack, c2a_ack; // ack_out_n of B/C/A, fed back upstream

    // ── Seed injection at A's north port: force/release used to prime the
    // ring with initial values, then hand control back to the ring's own
    // feedback (c2a_data/c2a_fire) once seeding is done. ──
    reg  [31:0] seed_val = 0;
    reg         seed_arrived = 0;
    wire [31:0] a_data_in_n = seed_arrived ? seed_val  : c2a_data;
    wire        a_arrived_n = seed_arrived ? 1'b1      : c2a_fire;

    wire [31:0] a_dout_n,a_dout_s,a_dout_e,a_dout_w;
    wire a_fn,a_fs,a_fe,a_fw, a_ready, a_ackn,a_acks,a_acke,a_ackw;

    unicell_stripped_v1 #(.CELL_ID(16'h0001)) A (
        .clk(clk), .rst(rst), .cfg_valid(cfgA), .cfg_data(cfgA_d),
        .data_in_n(a_data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(a_arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(a_dout_n), .data_out_s(a_dout_s), .data_out_e(a_dout_e), .data_out_w(a_dout_w),
        .fire_n(a_fn), .fire_s(a_fs), .fire_e(a_fe), .fire_w(a_fw),
        .ready_out(a_ready),
        .ready_in_n(1'b1), .ready_in_s(bR), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(a_ackn), .ack_out_s(a_acks), .ack_out_e(a_acke), .ack_out_w(a_ackw),
        .ack_in_n(1'b0), .ack_in_s(a2b_ack), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(1'b0),

        .hold_in(1'b0),


        .fb_internal_in(1'b0),



        .a_reemit_in(1'b0),



        .a_update_in(1'b0),




        .a_self_update_in(1'b0),





        .program_in(1'b0),





        .program_done(),






        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),







        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),







        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );
    assign a2b_data = a_dout_s;
    assign a2b_fire = a_fs;
    assign aR = a_ready;

    wire [31:0] b_dout_n,b_dout_s,b_dout_e,b_dout_w;
    wire b_fn,b_fs,b_fe,b_fw, b_ready, b_ackn,b_acks,b_acke,b_ackw;

    unicell_stripped_v1 #(.CELL_ID(16'h0002)) B (
        .clk(clk), .rst(rst), .cfg_valid(cfgB), .cfg_data(cfgB_d),
        .data_in_n(a2b_data), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(a2b_fire), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(b_dout_n), .data_out_s(b_dout_s), .data_out_e(b_dout_e), .data_out_w(b_dout_w),
        .fire_n(b_fn), .fire_s(b_fs), .fire_e(b_fe), .fire_w(b_fw),
        .ready_out(b_ready),
        .ready_in_n(1'b1), .ready_in_s(cR), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(b_ackn), .ack_out_s(b_acks), .ack_out_e(b_acke), .ack_out_w(b_ackw),
        .ack_in_n(1'b0), .ack_in_s(b2c_ack), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(freezeB),   // <── THE FREEZE UNDER TEST

        .hold_in(1'b0),


        .fb_internal_in(1'b0),



        .a_reemit_in(1'b0),



        .a_update_in(1'b0),




        .a_self_update_in(1'b0),





        .program_in(1'b0),





        .program_done(),






        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),







        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),







        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );
    assign b2c_data = b_dout_s;
    assign b2c_fire = b_fs;
    assign bR = b_ready;
    assign a2b_ack = b_ackn;   // B acking A's delivery on its north port

    wire [31:0] c_dout_n,c_dout_s,c_dout_e,c_dout_w;
    wire c_fn,c_fs,c_fe,c_fw, c_ready, c_ackn,c_acks,c_acke,c_ackw;

    unicell_stripped_v1 #(.CELL_ID(16'h0003)) C (
        .clk(clk), .rst(rst), .cfg_valid(cfgC), .cfg_data(cfgC_d),
        .data_in_n(b2c_data), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(b2c_fire), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(c_dout_n), .data_out_s(c_dout_s), .data_out_e(c_dout_e), .data_out_w(c_dout_w),
        .fire_n(c_fn), .fire_s(c_fs), .fire_e(c_fe), .fire_w(c_fw),
        .ready_out(c_ready),
        .ready_in_n(1'b1), .ready_in_s(aR), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(c_ackn), .ack_out_s(c_acks), .ack_out_e(c_acke), .ack_out_w(c_ackw),
        .ack_in_n(1'b0), .ack_in_s(c2a_ack), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(1'b0),

        .hold_in(1'b0),


        .fb_internal_in(1'b0),



        .a_reemit_in(1'b0),



        .a_update_in(1'b0),




        .a_self_update_in(1'b0),





        .program_in(1'b0),





        .program_done(),






        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),







        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),







        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );
    assign c2a_data = c_dout_s;
    assign c2a_fire = c_fs;
    assign cR = c_ready;
    assign b2c_ack = c_ackn;   // C acking B's delivery
    assign c2a_ack = a_ackn;   // A acking C's delivery (closes the ring)

    task seed(input [31:0] v);
        begin
            seed_val = v; seed_arrived = 1;
            @(posedge clk); #1;
            seed_arrived = 0;
        end
    endtask

    task report(input [127:0] label);
        $display("[t=%0t] %0s | A: ready=%b arrived=%b out=%h | B: ready=%b arrived=%b out=%h frozen=%b | C: ready=%b arrived=%b out=%h",
                  $time, label, a_ready, a_arrived_n_dbg, a_dout_s, b_ready, a2b_fire, b_dout_s, freezeB, c_ready, b2c_fire, c_dout_s);
    endtask

    // debug tap (a_arrived is internal, expose via hierarchical ref for display only)
    wire a_arrived_n_dbg = A.a_arrived;

    initial begin
        $dumpfile("/tmp/tb_stripped_v1_ring.vcd");
        $dumpvars(0, tb_stripped_v1_ring);

        rst = 1; repeat(3) @(posedge clk); rst = 0; @(posedge clk);

        cfgA_d = 128'h0; cfgA_d[9:0]=TOPO_NOR; cfgA_d[69:64]=6'b000010; cfgA=1; @(posedge clk); #1; cfgA=0;
        cfgB_d = 128'h0; cfgB_d[9:0]=TOPO_NOR; cfgB_d[69:64]=6'b000010; cfgB=1; @(posedge clk); #1; cfgB=0;
        cfgC_d = 128'h0; cfgC_d[9:0]=TOPO_NOR; cfgC_d[69:64]=6'b000010; cfgC=1; @(posedge clk); #1; cfgC=0;
        @(posedge clk);
        report("config done ");

        // Seed A with 2 pairs (4 values) -- enough for A to fire TWICE,
        // giving B its 2 required arrivals to fire ONCE toward C.
        seed(32'hAAAA0000); seed(32'h0000FFFF);   // A's 1st fire -> B captures
        repeat(3) @(posedge clk); report("after A fire 1");

        seed(32'h11110000); seed(32'h0000EEEE);   // A's 2nd fire -> B fires -> C captures
        repeat(3) @(posedge clk); report("after A fire 2 / B fire");

        // ── Freeze B now, THEN keep feeding A. A will fire again (A itself
        // isn't frozen), but B (frozen) must NOT consume/ack it — A should
        // back up and STAY backed up for as long as B stays frozen. ──
        freezeB = 1;
        report("B FROZEN       ");

        seed(32'h55550000); seed(32'h0000CCCC);   // A's 3rd fire attempt
        repeat(5) @(posedge clk);
        report("during freeze  ");
        repeat(5) @(posedge clk);
        report("still frozen   ");

        // ── Release B. The delivery A's been holding (level-held via
        // pending_ack, per #91) should still be there — B should finally
        // consume it, ack A (A recovers), and fire on to C. ──
        freezeB = 0;
        repeat(5) @(posedge clk);
        report("B RELEASED     ");

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
