// tb_top_unicell_super_test_v2.v — sim-first verification of
// top_unicell_super_test_v2.v (points.md #421/#422) before Quartus.
// Confirms all 7 cores (the original 6, unchanged, plus the new
// SEL_SEQ sequencer core) are correctly reachable and correct through
// the real, synthesizable top-level self-test FSM.
`timescale 1ns / 1ps
module tb;
    reg clk = 0;
    always #5 clk = ~clk;
    wire led0_n, led1_n;

    top_unicell_super_test_v2 DUT (
        .CLK_100M(clk), .LED0_N(led0_n), .LED1_N(led1_n)
    );

    integer i;
    integer error_seen = 0;
    reg [5:0] last_state = 6'd63;

    always @(posedge DUT.clk) begin
        if (DUT.state !== last_state) begin
            $display("t=%0t state=%0d err=%b data_out_e=%0d", $time, DUT.state, DUT.err_sticky, DUT.data_out_e);
            last_state <= DUT.state;
        end
    end

    initial begin
        for (i = 0; i < 20000; i = i + 1) begin
            @(posedge clk);
            if (led1_n === 1'b0) error_seen = 1;
        end
        if (DUT.state !== DUT.S_DONE) begin
            $display("FAIL: never reached S_DONE (stuck at %0d)", DUT.state);
        end else if (error_seen) begin
            $display("FAIL: err_sticky set at some point");
        end else begin
            $display("PASS: all 7 cores (including new SEL_SEQ) verified correctly through unicell_super_v2");
        end
        $finish;
    end
endmodule
