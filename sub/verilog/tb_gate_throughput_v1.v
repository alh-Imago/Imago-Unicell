`default_nettype none
`timescale 1ns / 1ps
// Words per clock through [producer -> bridge or gate -> adder_cell_v4s -> sub_to_flex -> consumer], producer always ready, consumer takes a result as soon as it sees it.
// Compared with the adder cell fed directly (one word every clock). 1 Nov 2026.
module tb_gate_throughput_v1;
    parameter GATED = 1, N = 200;
    reg clk = 0, rst = 1; always #5 clk = ~clk;
    integer qi = 0, nres = 0, t0 = 0, t1 = 0, cyc = 0;
    wire in_ack, done, region_valid; wire [63:0] region_data; wire [31:0] ao, oo; wire av, ov; reg oack = 0;
    wire [63:0] in_data = {32'd5, 32'd3}; reg go = 0; wire in_valid = (qi < N) && !rst && go;
    wire cfgv; reg cfg_req = 0;
    generate if (GATED) begin : g
        config_gate_v1 #(.WIDTH(64), .CFG_W(32), .SETTLE(1)) G (.clk(clk), .rst(rst), .in_data(in_data), .in_valid(in_valid), .in_ack(in_ack), .region_data(region_data), .region_valid(region_valid), .done(done),
            .cfg_req(cfg_req), .cfg_word_in(32'h0), .cfg_valid(cfgv), .cfg_data(), .cfg_busy(), .cfg_done(), .cfg_err());
    end else begin : b
        flex_to_sub_v1 #(.WIDTH(64)) F (.clk(clk), .rst(rst), .in_data(in_data), .in_valid(in_valid), .in_ack(in_ack), .sub_data(region_data), .sub_valid(region_valid), .done(done));
        assign cfgv = 1'b0;
    end endgenerate
    reg armed_cfg = 1; reg rawcfg = 0;
    adder_cell_v4s A (.clk(clk), .rst(rst), .cfg_valid(cfgv | rawcfg), .cfg_data(32'h0), .in_a(region_data[63:32]), .in_b(region_data[31:0]), .valid_in(region_valid), .data_out(ao), .valid_out(av));
    sub_to_flex_v1 #(.WIDTH(32)) O (.clk(clk), .rst(rst), .sub_data(ao), .sub_valid(av), .out_data(oo), .out_valid(ov), .out_ack(oack), .done(done));
    always @(posedge clk) begin
        armed_cfg <= 1; oack <= ov && !oack; cyc <= cyc + 1;
        if (!rst && in_ack) begin qi <= qi + 1; if (qi == 0) t0 <= cyc; end
        if (ov && oack) begin nres <= nres + 1; if (nres == N - 1) t1 <= cyc; end
    end
    initial begin
        repeat (3) @(negedge clk); rst = 0;
        @(negedge clk); if (GATED) cfg_req = 1; else rawcfg = 1; @(negedge clk); cfg_req = 0; rawcfg = 0; repeat (6) @(negedge clk); go = 1;
        repeat (200 * 12) @(negedge clk);
        $display("GATED=%0d: %0d words, %0d results, %0d clocks first admission to last result = %0d clocks per word", GATED, qi, nres, t1 - t0, (t1 - t0) / (N - 1));
        $finish;
    end
endmodule
