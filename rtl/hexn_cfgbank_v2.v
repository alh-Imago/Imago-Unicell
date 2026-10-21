`default_nettype none
// hexn_cfgbank_v2.v -- clone of hexn_cfgbank_v1.v (left untouched). Same job (the settings of K run-time detectors) but loaded as a SHIFT CHAIN instead of by address: the training bank writes lane settings in ascending address order, once each
// (command SETW), and thresholds for detector 0..K-1 in order (FINISH), so each write just shifts the chain by one place; after the full pass every setting sits in its own place. No address decoder. The write addresses are ignored (kept as ports so it is a drop-in).
module hexn_cfgbank_v2 #(parameter K = 4, parameter NB = 12, parameter AW = 6) (
    input  wire clk, input wire rst,
    input  wire w_we, input wire [$clog2(K*NB+1)-1:0] w_ad, input wire wp, input wire wn,
    input  wire t_we, input wire [$clog2(K)-1:0] t_k, input wire [AW-1:0] t_val,
    output wire [K*NB-1:0] w_pos, output wire [K*NB-1:0] w_neg, output wire [K*AW-1:0] thr_flat);
    reg [K*NB-1:0] p_r, n_r; reg [K*AW-1:0] t_r;
    assign w_pos = p_r; assign w_neg = n_r; assign thr_flat = t_r;
    always @(posedge clk) begin
        if (rst) begin p_r <= 0; n_r <= 0; t_r <= 0; end
        else begin
            if (w_we) begin p_r <= {wp, p_r[K*NB-1:1]}; n_r <= {wn, n_r[K*NB-1:1]}; end
            if (t_we) t_r <= {t_val, t_r[K*AW-1:AW]};
        end
    end
endmodule
`default_nettype wire
