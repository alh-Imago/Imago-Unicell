// tb_top_sentinel_gather_v1.v — sim-first verification of
// top_sentinel_gather_v1.v before Quartus. Drives CLK_100M only, runs
// the fully autonomous self-test to completion, checks LED1_N never
// lights (active-low error).
`timescale 1ns / 1ps

module tb;
    reg clk = 0;
    always #5 clk = ~clk;   // 100 MHz

    wire led0_n, led1_n;

    top_sentinel_gather_v1 DUT (
        .CLK_100M(clk),
        .LED0_N(led0_n),
        .LED1_N(led1_n)
    );

    integer i;
    integer error_seen;
    reg [5:0] last_state = 6'd63;
    integer print_budget;
    always @(posedge DUT.clk) begin
        if (DUT.state !== last_state) begin
            $display("t=%0t state=%0d round=%0d seq_index=%0d q_out=%0d h1_wrap=%b h2_wrap=%b h3_wrap=%b h1_safe=%b h2_safe=%b h3_safe=%b err=%b",
                $time, DUT.state, DUT.round_idx, DUT.seq_index, DUT.q_data_out_n,
                DUT.h1_out_wrap_pulse, DUT.h2_out_wrap_pulse, DUT.h3_out_wrap_pulse,
                DUT.h1_safe, DUT.h2_safe, DUT.h3_safe, DUT.err_sticky);
            last_state <= DUT.state;
        end
    end

    initial begin
        print_budget = 0;
        error_seen = 0;
        for (i = 0; i < 30000; i = i + 1) begin
            @(posedge clk);
            if (led1_n === 1'b0) error_seen = 1;
        end

        if (DUT.state !== DUT.S_DONE) begin
            $display("FAIL: FSM never reached S_DONE (stuck at state=%0d)", DUT.state);
            error_seen = 1;
        end else begin
            $display("PASS: FSM reached S_DONE");
        end

        if (error_seen) begin
            $display("FAIL: err_sticky / LED1_N indicated a real error at some point");
        end else begin
            $display("PASS: zero errors across the full self-test sequence");
        end

        $display("Final err_sticky = %b", DUT.err_sticky);
        $finish;
    end
endmodule
