`timescale 1ns/1ps
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg clear = 0, rst = 0; reg [31:0] in_data = 0; reg in_valid = 0; wire in_ack;
    wire [31:0] sd; wire sv, busy, ds, fs, done, v2; wire [31:0] d2; wire [31:0] out_data; wire out_valid; reg out_ack = 0; wire bdone;
    flex_to_sub_v1 #(.WIDTH(32)) a (.clk(clk), .rst(rst), .in_data(in_data), .in_valid(in_valid), .in_ack(in_ack), .sub_data(sd), .sub_valid(sv), .done(bdone));
    hexn_p2s_v1 p (.clk(clk), .clear(clear), .data(sd), .valid(sv), .busy(busy), .ds(ds), .fs(fs), .done(done));
    hexn_s2p_v1 s (.clk(clk), .clear(clear), .ds(ds), .fs(fs), .data(d2), .valid(v2));
    sub_to_flex_v1 #(.WIDTH(32)) b (.clk(clk), .rst(rst), .sub_data(d2), .sub_valid(v2), .out_data(out_data), .out_valid(out_valid), .out_ack(out_ack), .done(bdone));
    integer errs = 0, t = 0, t_in = 0, t_fs = -1, t_v = -1, t_ov = -1; always @(posedge clk) begin t <= t + 1; if (fs && t_fs < 0) t_fs <= t; if (v2 && t_v < 0) t_v <= t; if (out_valid && t_ov < 0) t_ov <= t; end
    task send(input [31:0] w); begin
        @(negedge clk); in_data = w; in_valid = 1; t_in = t; t_fs = -1; t_v = -1; t_ov = -1;
        @(negedge clk); in_valid = 0;
        wait (out_valid); @(negedge clk);
        if (out_data !== w) begin errs = errs + 1; $display("FAIL word %h got %h", w, out_data); end
        out_ack = 1; @(negedge clk); out_ack = 0; repeat (2) @(negedge clk);
    end endtask
    initial begin #200000; $display("TIMEOUT"); $finish; end
    initial begin
        rst = 1; repeat (3) @(negedge clk); rst = 0; @(negedge clk);
        send(32'h00000001); send(32'h80000000); send(32'hdeadbeef); send(32'h00000000); send(32'hffffffff); send(32'h12345678);
        // latency of the serial leg: accepted at t_in, flag out at t_fs, parallel valid at t_v
        $display("LAT in->flag %0d, flag->valid %0d, in->held %0d", t_fs - t_in, t_v - t_fs, t_ov - t_in);
        // wipe mid word
        @(negedge clk); in_data = 32'hcafef00d; in_valid = 1; @(negedge clk); in_valid = 0; repeat (10) @(negedge clk);
        clear = 1; repeat (3) @(negedge clk); clear = 0; rst = 1; @(negedge clk); rst = 0; repeat (60) @(negedge clk);
        if (v2 !== 0 || busy !== 0) begin errs = errs + 1; $display("FAIL wipe: v2=%b busy=%b", v2, busy); end
        if (errs == 0) $display("PASS"); else $display("ERRORS %0d", errs);
        $finish;
    end
endmodule
