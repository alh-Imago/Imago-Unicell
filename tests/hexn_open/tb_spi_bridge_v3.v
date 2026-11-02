`timescale 1ns/1ps
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg rst = 1; initial begin repeat (6) @(negedge clk); rst = 0; end
    wire miso; wire [16*32-1:0] cfg;
    wire pl_en; wire [9:0] pl_a, cap_a; wire [31:0] pl_d;
//MASTER//
    spi_bridge_v3 #(.AW(10), .PATTERN_ID(32'h00A10003)) BR (
        .clk(clk), .rst(rst), .sclk(sclk), .cs_n(cs_n), .mosi(mosi), .miso(miso),
        .ctl_sd_load(), .ctl_sd_save(), .ctl_play_start(), .ctl_cap_clear(), .ctl_sd_reinit(), .start_block(), .nblocks(), .play_count(), .max_out(), .rpi(),
        .sd_ready(1'b0), .sd_error(1'b0), .sd_busy(1'b0), .play_busy(1'b0), .err_code(5'd0), .err_cmd(6'd0), .err_rx(8'd0), .sd_done_pulse(1'b0), .play_done_pulse(1'b0), .cap_count(11'd0),
        .pl_wr_en(pl_en), .pl_wr_addr(pl_a), .pl_wr_data(pl_d), .cap_rd_addr(cap_a), .cap_rd_data(32'h0), .cfg_flat(cfg), .status_in(32'h0000000A));
    integer fails = 0;
    task check(input cond, input [255:0] what); begin if (!cond) begin $display("FAIL %0s", what); fails = fails + 1; end else $display("ok %0s", what); end endtask
    initial begin
        repeat (40) @(negedge clk);
        rd_reg(8'd0);  check(rv === 32'h57320002, "ID word unchanged");
        rd_reg(8'd11); check(rv === 32'h00A10003, "register 11 = pattern type 00A1, version 0003");
        wr_reg(8'd11, 32'hFFFFFFFF); rd_reg(8'd11); check(rv === 32'h00A10003, "register 11 is read-only");
        rd_reg(8'd10); check(rv === 32'h0000000A, "status register 10 unchanged");
        wr_reg(8'd20, 32'hDEADBEEF); rd_reg(8'd20); check(rv === 32'hDEADBEEF, "config register still reads back");
        rd_reg(8'd11); check(rv === 32'h00A10003, "register 11 still intact after other writes");
        if (fails == 0) $display("PASS"); else $display("FAIL %0d", fails);
        $finish;
    end
    initial begin repeat (2000000) @(posedge clk); $display("TIMEOUT"); $finish; end
endmodule
