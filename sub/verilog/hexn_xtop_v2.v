`default_nettype none
// hexn_xtop_v2 -- a generated hexn_pattern_top with the SERIAL<->PARALLEL CROSSING (hexn_cross_v1.v) on every row (3 Nov 2026, Alan 10:07): one hexn_p2s_v2 drives each west pad, one hexn_s2p_v2 reads each east pad.
// The UniCell / sub side sees 32-bit words with a one-clock valid: in_data[32*r +: 32] with in_valid[r] (accepted when in_busy[r] is low), out_data[32*r +: 32] with out_valid[r] (one clock, data held). `clear` wipes pattern and crossing.
// Timing, measured in tests/vm/test_hexn_cross_v1.py: a word with in_valid in clock t is on the pad (flag) in clock t+1; an output word whose flag is on the east pad in clock u has out_valid in clock u+32 (u+33 in the tick convention of hexn_cross_verify_v1, whose print is taken one clock after the registered valid).
module hexn_xtop_v2 #(parameter ROWS = 7) (
    input wire clk, input wire clear,
    input wire [32*ROWS-1:0] in_data, input wire [ROWS-1:0] in_valid, output wire [ROWS-1:0] in_busy,
    output wire [32*ROWS-1:0] out_data, output wire [ROWS-1:0] out_valid,
    input wire cfg_en, input wire cfg_in, output wire cfg_out);
    wire [ROWS-1:0] wd, wf, ed, ef; wire [ROWS-1:0] dn;
    hexn_pattern_top core (.clk(clk), .clear(clear), .w_d(wd), .w_f(wf), .e_d(ed), .e_f(ef), .cfg_en(cfg_en), .cfg_in(cfg_in), .cfg_out(cfg_out));
    genvar r;
    generate for (r = 0; r < ROWS; r = r + 1) begin : row
        hexn_p2s_v2 p (.clk(clk), .clear(clear), .data(in_data[32*r +: 32]), .valid(in_valid[r]), .busy(in_busy[r]), .ds(wd[r]), .fs(wf[r]), .done(dn[r]));
        hexn_s2p_v2 s (.clk(clk), .clear(clear), .ds(ed[r]), .fs(ef[r]), .data(out_data[32*r +: 32]), .valid(out_valid[r]));
    end endgenerate
endmodule
