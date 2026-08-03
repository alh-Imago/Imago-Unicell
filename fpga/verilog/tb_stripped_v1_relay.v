// tb_stripped_v1_relay.v — A (computes, NOR) -> B (PURE RELAY, cardinal_edge
// tags its North input as relay -- never touches its own gate/a_arrived) ->
// C (leaf consumer). Confirms: (1) B forwards A's raw computed value
// UNCHANGED, single-arrival, immediately -- not waiting for a second arrival
// like a compute cell would; (2) B's own a_arrived NEVER moves, proving it
// genuinely never entered the two-arrival gate; (3) relay still respects
// backpressure -- freezing C should back B up exactly like a compute fire
// would, not bypass it. Points.md #94.
`timescale 1ns / 1ps

module tb_stripped_v1_relay;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;
    localparam [9:0] TOPO_NOR = 10'h004;

    reg cfgA=0, cfgB=0, cfgC=0;
    reg [127:0] cfgA_d=0, cfgB_d=0, cfgC_d=0;
    reg freezeC = 0;

    reg [31:0] seed_val = 0;
    reg        seed_arrived = 0;

    wire [31:0] a2b_data, b2c_data;
    wire        a2b_fire, b2c_fire;
    wire        bReady, cReady;
    wire        a2b_ack, b2c_ack;

    wire [31:0] a_dout_s; wire a_fs, a_ready;
    unicell_stripped_v1 #(.CELL_ID(16'h0001)) A (
        .clk(clk), .rst(rst), .cfg_valid(cfgA), .cfg_data(cfgA_d),
        .data_in_n(seed_val), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(seed_arrived), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(a_dout_s), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(a_fs), .fire_e(), .fire_w(),
        .ready_out(a_ready),
        .ready_in_n(1'b1), .ready_in_s(bReady), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
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





        .program_done()
    );
    assign a2b_data = a_dout_s;
    assign a2b_fire = a_fs;

    // ── B: PURE RELAY. cardinal_edge[0]=1 (North=relay). routing_mask=South. ──
    wire [31:0] b_dout_s; wire b_fs, b_ready;
    unicell_stripped_v1 #(.CELL_ID(16'h0002)) B (
        .clk(clk), .rst(rst), .cfg_valid(cfgB), .cfg_data(cfgB_d),
        .data_in_n(a2b_data), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(a2b_fire), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(b_dout_s), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(b_fs), .fire_e(), .fire_w(),
        .ready_out(b_ready),
        .ready_in_n(1'b1), .ready_in_s(cReady), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(a2b_ack), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(b2c_ack), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(1'b0),

        .hold_in(1'b0),


        .fb_internal_in(1'b0),



        .a_reemit_in(1'b0),



        .a_update_in(1'b0),




        .a_self_update_in(1'b0),





        .program_in(1'b0),





        .program_done()
    );
    assign b2c_data = b_dout_s;
    assign b2c_fire = b_fs;
    assign bReady = b_ready;

    wire c_ready;
    unicell_stripped_v1 #(.CELL_ID(16'h0003)) C (
        .clk(clk), .rst(rst), .cfg_valid(cfgC), .cfg_data(cfgC_d),
        .data_in_n(b2c_data), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(b2c_fire), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(),
        .ready_out(c_ready),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(b2c_ack), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(freezeC),   // <── freeze the final consumer, check relay still stalls

        .hold_in(1'b0),


        .fb_internal_in(1'b0),



        .a_reemit_in(1'b0),



        .a_update_in(1'b0),




        .a_self_update_in(1'b0),





        .program_in(1'b0),





        .program_done()
    );
    assign cReady = c_ready;

    task seed(input [31:0] v);
        begin
            seed_val = v; seed_arrived = 1;
            @(posedge clk); #1;
            seed_arrived = 0;
        end
    endtask

    task report(input [127:0] label);
        $display("[t=%0t] %0s | A:ready=%b out=%h | B:ready=%b arrived=%b(should stay 0!) out=%h | C:ready=%b frozen=%b",
                  $time, label, a_ready, a_dout_s, b_ready, B.a_arrived, b_dout_s, c_ready, freezeC);
    endtask

    initial begin
        $dumpfile("/tmp/tb_stripped_v1_relay.vcd");
        $dumpvars(0, tb_stripped_v1_relay);

        rst = 1; repeat(3) @(posedge clk); rst = 0; @(posedge clk);

        cfgA_d=128'h0; cfgA_d[9:0]=TOPO_NOR; cfgA_d[69:64]=6'b000010; cfgA=1; @(posedge clk); #1; cfgA=0;
        // B: routing_mask = South (bit1). cardinal_edge[0]=1 -> North input = RELAY.
        cfgB_d=128'h0; cfgB_d[69:64]=6'b000010; cfgB_d[75:70]=6'b000001; cfgB=1; @(posedge clk); #1; cfgB=0;
        cfgC_d=128'h0; cfgC_d[9:0]=TOPO_NOR; cfgC_d[69:64]=6'b000000; cfgC=1; @(posedge clk); #1; cfgC=0;
        @(posedge clk);
        report("config done        ");

        // A fires once (2 seeds) -> B should relay it to C IMMEDIATELY,
        // single-arrival, WITHOUT touching its own a_arrived at all.
        seed(32'hAAAA0000); seed(32'h0000FFFF);   // A computes NOR = 0x55550000
        repeat(3) @(posedge clk);
        report("after A fire 1     ");  // expect B.out == 0x55550000, B.arrived stayed 0

        // A fires a second, DIFFERENT value -> confirm B relays THIS one too,
        // immediately, still never touching a_arrived (repeatable, not a
        // one-shot fluke).
        seed(32'h11110000); seed(32'h0000EEEE);   // A computes NOR = 0xEEEE1111
        repeat(3) @(posedge clk);
        report("after A fire 2     ");  // expect B.out == 0xEEEE1111, B.arrived still 0

        // ── Now freeze C and confirm relay respects backpressure -- it must
        // NOT bypass the ready/ack mechanism just because it's a pass-through. ──
        freezeC = 1;
        report("C FROZEN           ");

        seed(32'h33330000); seed(32'h0000DDDD);   // A computes NOR = 0xCCCC3333
        repeat(5) @(posedge clk);
        report("during freeze      ");   // expect B.ready stuck at 0 -- relay backed up
        repeat(5) @(posedge clk);
        report("still frozen       ");

        freezeC = 0;
        repeat(5) @(posedge clk);
        report("C RELEASED         ");   // expect B.ready recovers, B.out == 0xCCCC3333 by now

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
