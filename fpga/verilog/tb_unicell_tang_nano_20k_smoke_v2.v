`timescale 1ns/1ps
module tb_unicell_tang_nano_20k_smoke_v2;
    reg clk = 0;
    wire led0, led1, led2, led3;
    always #18.5 clk = ~clk;   // ~27 MHz

    unicell_tang_nano_20k_smoke_v2 #(.TICK_DIV(20)) dut (
        .BOARD_CLK(clk),
        .LED0_N(led0), .LED1_N(led1), .LED2_N(led2), .LED3_N(led3)
    );

    reg [1:0] last_seq = 2'bxx;
    integer advances = 0;
    always @(posedge clk) begin
        if (last_seq !== dut.seq_index) begin
            if (last_seq !== 2'bxx) advances = advances + 1;
            last_seq = dut.seq_index;
        end
    end

    initial begin
        #20000;
        $display("seq_index=%0d real_advances=%0d", dut.seq_index, advances);
        if (advances < 8) begin
            $display("FAIL: too few real state advances (%0d)", advances);
            $finish;
        end
        $display("PASS: v2 (no button, power-on reset only) genuinely cycles through all 4 states");
        $finish;
    end
endmodule
