// tb_stripped_v1_branch.v — points.md #140's branch mechanism: a
// comparator result (second_val vs held A) selects between 3 different
// routing patterns, genuinely changing WHERE data goes per fire, not just
// what value it produces. Uses hold_in (#116) to keep the threshold (A)
// fixed across multiple comparisons, matching the already-proven
// comparator-holding pattern.
`timescale 1ns / 1ps

module tb_stripped_v1_branch;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    reg         cfg_valid = 0;
    reg [127:0] cfg_data  = 0;
    reg         hold = 0;

    reg [31:0] data_in = 0;
    reg        arrived = 0;

    wire fire_n_w, fire_s_w, fire_e_w, fire_w_w;
    wire ready_w;

    unicell_stripped_v1 #(.CELL_ID(16'h0001), .ENABLE_DYNAMIC_ROUTING(1'b1)) T (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in_n(data_in), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(arrived), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(), .data_out_w(),
        .fire_n(fire_n_w), .fire_s(fire_s_w), .fire_e(fire_e_w), .fire_w(fire_w_w),
        .ready_out(ready_w),
        // Always-ready neighbors on all 4 sides -- we want every branch
        // choice to be able to fire regardless of which direction it picks.
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(1'b0),
        .hold_in(hold),
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

    localparam [9:0] TOPO_NOR = 10'h004;

    task seed(input [31:0] v);
        begin
            data_in = v; arrived = 1;
            @(posedge clk); #1;
            arrived = 0;
        end
    endtask

    task ack_pulse;
        begin
            force T.ack_in_n = 1'b1; force T.ack_in_s = 1'b1;
            force T.ack_in_e = 1'b1; force T.ack_in_w = 1'b1;
            @(posedge clk); #1;
            release T.ack_in_n; release T.ack_in_s;
            release T.ack_in_e; release T.ack_in_w;
        end
    endtask

    task report(input [127:0] label);
        $display("[t=%0t] %0s | fire_n=%b fire_s=%b fire_e=%b fire_w=%b",
                  $time, label, fire_n_w, fire_s_w, fire_e_w, fire_w_w);
    endtask

    initial begin
        rst = 1; repeat(3) @(posedge clk); rst = 0; @(posedge clk);

        // topology=NOR, routing_mask=South (static fallback, unused while
        // dynamic_route_en=1), pattern_low=East(bit2), pattern_equal=
        // North(bit0), pattern_high=West(bit3), dynamic_route_en=1.
        cfg_data = 128'h0;
        cfg_data[9:0]   = TOPO_NOR;
        cfg_data[69:64] = 6'b001111;   // routing_mask = ALL directions open (the AND gate
                                       // with the selected pattern needs each direction
                                       // "open" here too -- routing_mask is the gate,
                                       // the pattern is the choice)
        cfg_data[79:76] = 4'b0100;     // pattern_low   = East  (bit2)
        cfg_data[85:82] = 4'b0001;     // pattern_equal = North (bit0)
        cfg_data[91:88] = 4'b1000;     // pattern_high  = West  (bit3)
        cfg_data[94]    = 1'b1;        // dynamic_route_en = 1
        cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;
        @(posedge clk);

        // Load threshold A=5, hold it.
        seed(32'h00000005);
        hold = 1;
        report("threshold A=5 loaded");

        // B=10 (>5) -> expect cmp_gt -> pattern_high -> fire on WEST only.
        seed(32'h0000000A);
        report("B=10 (>A): expect fire_w only");
        ack_pulse;

        // B=2 (<5) -> expect cmp_lt -> pattern_low -> fire on EAST only.
        seed(32'h00000002);
        report("B=2  (<A): expect fire_e only");
        ack_pulse;

        // B=5 (==5) -> expect neither gt nor lt -> pattern_equal -> fire on NORTH only.
        seed(32'h00000005);
        report("B=5  (=A): expect fire_n only");

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
