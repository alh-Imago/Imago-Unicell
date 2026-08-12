// tb_top_full_tree_system_v1.v — elaboration + functional sanity check
// for top_full_tree_system_v1.v (points.md #273 continuation) before
// handing off to Quartus. Confirms the real synthesizable self-test
// FSM actually reaches S_RUN with both results correctly seen, not
// just that it elaborates.
`timescale 1ns / 1ps

module tb_top_full_tree_system_v1;

    reg clk100 = 0;
    always #5 clk100 = ~clk100;

    wire led0, led1;

    top_full_tree_system_v1 DUT (
        .CLK_100M(clk100),
        .LED0_N(led0),
        .LED1_N(led1)
    );

    initial begin
        #300000;
        $display("state=%0d result1_seen=%b result2_seen=%b err_sticky=%b LED1=%b",
            DUT.state, DUT.result1_seen, DUT.result2_seen, DUT.err_sticky, led1);
        if (DUT.state == DUT.S_RUN && DUT.result1_seen && DUT.result2_seen && !DUT.err_sticky)
            $display("PASS: top_full_tree_system_v1 reached S_RUN with both results correct, LED1 stays dark");
        else
            $display("FAIL: did not reach clean S_RUN state -- see values above");
        $finish;
    end

    always @(posedge clk100) begin
        if (!DUT.rst) begin
            if (DUT.rb2_fire_e) $display("[%0t] RB2 fired (data=%h)", $time, DUT.rb2_data_out_e);
            if (DUT.rc_fire_e) $display("[%0t] RC fired (data=%h)", $time, DUT.rc_data_out_e);
            if (DUT.ADDER2.can_fire) $display("[%0t] ADDER2 can_fire", $time);
            if (DUT.mchild_fire_n) $display("[%0t] MUX_CHILD fired N (->RB2)", $time);
            if (DUT.mchild_fire_s) $display("[%0t] MUX_CHILD fired S (->RC)", $time);
            if (DUT.root_fire_e) $display("[%0t] MUX_ROOT fired E (->MUX_CHILD)", $time);
        end
    end

endmodule
