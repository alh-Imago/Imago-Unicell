// tb_stripped_v1_hold.v — points.md #115's hold_in mechanism, first test.
// Single cell: load a threshold as the first-arrival value, assert hold_in,
// feed SEVERAL different second-arrival values in succession, confirm the
// held threshold (data_reg) never changes across fires and each new value
// correctly produces a fresh gate result against the SAME held value.
// Then release hold_in and confirm normal auto-clear resumes.
`timescale 1ns / 1ps

module tb_stripped_v1_hold;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    reg         cfg_valid = 0;
    reg [127:0] cfg_data  = 0;
    reg [31:0]  data_in_n = 0;
    reg         arrived_n = 0;
    reg         hold = 0;

    wire [31:0] dout_n;
    wire        fire_n_w, ready_w;

    unicell_stripped_v1 #(.CELL_ID(16'h0001)) DUT (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(dout_n), .data_out_s(), .data_out_e(), .data_out_w(),
        .fire_n(fire_n_w), .fire_s(), .fire_e(), .fire_w(),
        .ready_out(ready_w),
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
            data_in_n = v; arrived_n = 1;
            @(posedge clk); #1;
            arrived_n = 0;
        end
    endtask

    task report(input [127:0] label);
        $display("[t=%0t] %0s | data_reg(held threshold)=%h a_arrived=%b out=%h hold=%b",
                  $time, label, DUT.data_reg, DUT.a_arrived, dout_n, hold);
    endtask

    initial begin
        rst = 1; repeat(3) @(posedge clk); rst = 0; @(posedge clk);

        cfg_data = 128'h0; cfg_data[9:0] = TOPO_NOR; cfg_data[69:64] = 6'b000000; // no routing needed, just watch data_reg/out_buffer directly
        cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;
        @(posedge clk);

        // Load the "threshold" as the first-arrival value.
        seed(32'hAAAA0000);
        repeat(2) @(posedge clk);
        report("threshold loaded  ");   // expect data_reg=AAAA0000, a_arrived=1

        // Hold BEFORE the next arrival fires.
        hold = 1;
        report("hold asserted     ");

        seed(32'h11110000);
        repeat(2) @(posedge clk);
        report("fire 1 (held)     ");   // expect data_reg STILL AAAA0000, a_arrived STILL 1
                                          // out = NOR(AAAA0000,11110000) = ~(BBBB0000) = 44444FFF... compute by hand below

        seed(32'h22220000);
        repeat(2) @(posedge clk);
        report("fire 2 (held)     ");   // expect data_reg STILL AAAA0000

        seed(32'h33330000);
        repeat(2) @(posedge clk);
        report("fire 3 (held)     ");   // expect data_reg STILL AAAA0000

        // Release.
        hold = 0;
        report("hold released     ");

        seed(32'h44440000);   // this fire commits with hold=0 now -> a_arrived clears after it
        repeat(2) @(posedge clk);
        report("fire 4 (release fire)");  // expect data_reg STILL AAAA0000 (this fire), but a_arrived should clear AFTER

        seed(32'h55550000);   // should now be treated as a FRESH capture, not a fire
        repeat(2) @(posedge clk);
        report("fresh capture after release"); // expect data_reg = 55550000 (NEW value, proving release worked)

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
