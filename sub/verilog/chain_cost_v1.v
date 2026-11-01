`default_nettype none
// chain_cost_v1.v -- MEASUREMENT PROTOTYPE (1 Nov 2026, Alan 19:15: 'let's see if we can fit enough on the board'): N gated Hex-N units (config_gate_v3 -> arith_block_v9 W18 -> sub_to_flex_v1, exactly the three parts of hexn_unit_v1 without its engine) in a chain, to find the cost of ONE more unit. The second operand of every stage is a copy of its first (wiring only, so the stage count and not the data decides the size). Each stage has its own config word input. Not a design: it has no routing, no bypass, no pass-through.
module chain_cost_v1 #(parameter N = 4, parameter W = 18) (
    input wire clk, input wire rst,
    input wire [W-1:0] in_data, input wire in_valid, output wire in_ack,
    output wire [W-1:0] out_data, output wire out_valid, input wire out_ack,
    input wire [N-1:0] cfg_req, input wire [32*N-1:0] cfg_words, output wire [N-1:0] any_status
);
    wire [W-1:0] d [0:N]; wire v [0:N]; wire ack [0:N]; assign d[0] = in_data; assign v[0] = in_valid; assign in_ack = ack[0]; assign ack[N] = out_ack;
    genvar i;
    generate for (i = 0; i < N; i = i + 1) begin : S
        wire cfg_v, region_valid, done, cfg_done, cfg_busy, fault, dead, blocked, region_rst, o_valid, bv; wire [1:0] cfg_err; wire [7:0] resets, lost; wire [31:0] cfg_d; wire [2*W-1:0] region_data; wire [W-1:0] bo, od;
        wire rr = rst | region_rst;
        config_gate_v3 #(.WIDTH(2*W), .CFG_W(32), .SETTLE(1), .DRAIN_TIMEOUT(64), .WATCHDOG(100), .MAX_RETRY(2), .GOOD_WORDS(16)) G (
            .clk(clk), .rst(rst), .in_data({d[i], d[i]}), .in_valid(v[i]), .in_ack(ack[i]), .region_data(region_data), .region_valid(region_valid),
            .done(done), .res_valid(o_valid), .cfg_req(cfg_req[i]), .cfg_word_in(cfg_words[32*i +: 32]), .cfg_valid(cfg_v), .cfg_data(cfg_d), .cfg_busy(cfg_busy), .cfg_done(cfg_done), .cfg_err(cfg_err),
            .region_rst(region_rst), .fault(fault), .dead(dead), .blocked(blocked), .resets(resets), .lost(lost));
        arith_block_v9 #(.WIDTH(W)) B (.clk(clk), .rst(rr), .cfg_valid(cfg_v), .cfg_data(cfg_d), .in_a(region_data[2*W-1:W]), .in_b(region_data[W-1:0]), .valid_in(region_valid), .data_out(bo), .valid_out(bv));
        sub_to_flex_v1 #(.WIDTH(W)) O (.clk(clk), .rst(rr), .sub_data(bo), .sub_valid(bv), .out_data(od), .out_valid(o_valid), .out_ack(ack[i+1]), .done(done));
        assign d[i+1] = od; assign v[i+1] = o_valid;
        assign any_status[i] = fault | dead | blocked | cfg_busy | cfg_done | (|cfg_err) | (|resets) | (|lost);
    end endgenerate
    assign out_data = d[N]; assign out_valid = v[N];
endmodule
