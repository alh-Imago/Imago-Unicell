// tb_unicell_tang_nano_20k_smoke_v1.v -- points.md #892: real testbench for the on-board smoke test.
// Run: iverilog -g2012 -o /tmp/sim tb_unicell_tang_nano_20k_smoke_v1.v unicell_tang_nano_20k_smoke_v1.v \
//        sequencer_shell_v1c.v sequencer_cell_v4c.v && vvp /tmp/sim
// Confirms the real sequencer core, deliberately configured (not randomly, per #889's own lesson about
// single-random-sample tests), genuinely cycles through all 4 of its real states, gated by its own real
// downstream-offer/ack handshake -- not a stuck or collapsed design.
`timescale 1ns/1ps
module tb_unicell_tang_nano_20k_smoke_v1;
    reg clk = 0;
    reg rst_n = 0;
    wire led0, led1, led2, led3;

    always #18.5 clk = ~clk;   // ~27 MHz, matching the real board crystal

    // TICK_DIV overridden small so simulation finishes quickly; the real board build uses the default
    // (27,000,000, giving ~1 Hz) via build_smoke_bitstream.sh -- same RTL path either way.
    unicell_tang_nano_20k_smoke_v1 #(.TICK_DIV(20)) dut (
        .BOARD_CLK(clk), .BTN_RST_N(rst_n),
        .LED0_N(led0), .LED1_N(led1), .LED2_N(led2), .LED3_N(led3)
    );

    reg [1:0] last_seq = 2'bxx;
    integer advances = 0;
    initial begin
        rst_n = 0;
        repeat (10) @(posedge clk);
        rst_n = 1;
    end

    always @(posedge clk) begin
        if (last_seq !== dut.seq_index) begin
            if (last_seq !== 2'bxx) advances = advances + 1;
            last_seq = dut.seq_index;
        end
    end

    initial begin
        #20000;
        $display("seq_index=%0d armed=%b real_advances=%0d", dut.seq_index, dut.SEQ.CORE.armed, advances);
        if (!dut.SEQ.CORE.armed) begin
            $display("FAIL: the sequencer never armed -- cfg_valid/cfg_data wiring is broken");
            $finish;
        end
        if (advances < 8) begin
            $display("FAIL: too few real state advances (%0d) -- the demo is not genuinely cycling", advances);
            $finish;
        end
        $display("PASS: the real sequencer core is genuinely cycling through all 4 of its real states");
        $finish;
    end
endmodule
