`default_nettype none
// hexn_cfgbank_v1.v -- the SETTINGS of K run-time detectors (hexn_det_v2): per detector NB lane settings (+1 flag, -1 flag) and one threshold, written one lane / one threshold at a time by the training bank's write port.
// In a real bank each detector simply owns its settings; this module only gathers them so the training bank can be sized and simulated with them. Outputs plug into hexn_det_v2 (w_pos, w_neg, cfg_thr).
module hexn_cfgbank_v1 #(parameter K = 4, parameter NB = 12, parameter AW = 6) (
    input  wire clk, input wire rst,
    input  wire w_we, input wire [$clog2(K*NB+1)-1:0] w_ad, input wire wp, input wire wn,
    input  wire t_we, input wire [$clog2(K)-1:0] t_k, input wire [AW-1:0] t_val,
    output wire [K*NB-1:0] w_pos, output wire [K*NB-1:0] w_neg, output wire [K*AW-1:0] thr_flat);
    reg [K*NB-1:0] p_r, n_r; reg [AW-1:0] t_r [0:K-1];
    assign w_pos = p_r; assign w_neg = n_r;
    genvar g; generate for (g = 0; g < K; g = g + 1) begin : TF assign thr_flat[g*AW +: AW] = t_r[g]; end endgenerate
    integer i;
    always @(posedge clk) begin
        if (rst) begin p_r <= 0; n_r <= 0; for (i = 0; i < K; i = i + 1) t_r[i] <= 0; end
        else begin
            if (w_we) begin p_r[w_ad] <= wp; n_r[w_ad] <= wn; end
            if (t_we) t_r[t_k] <= t_val;
        end
    end
endmodule
`default_nettype wire
