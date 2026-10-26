`default_nettype none
// hexn_loader_v1.v -- Hex-N SETTINGS LOADER, new file (design: docs/hex-n/CARD_SLICE_v1.md). Writes the stored settings of ONE detector into the shift-chain settings store (hexn_cfgbank_v2.v) through the same kind of write ports the training bank uses.
// One start pulse with wp / wn (one bit per lane, lane j = bit j; same layout as the DUMP bytes) and thr: the loader then writes NB lane pairs (lane 0 first), then the threshold, one write per clock, and drops busy.
// Because the store is a shift chain (the address is ignored), a full load = this operation for detector 0, then 1, ... K-1, in that order, with nothing else writing the store in between. K sequential loads always replace the whole chain, whatever was in it before.
module hexn_loader_v1 #(parameter NB = 18, parameter AW = 7) (
    input  wire clk, input wire rst,
    input  wire start, input wire [NB-1:0] wp, input wire [NB-1:0] wn, input wire [AW-1:0] thr,
    output wire busy,
    output wire w_we, output wire w_wp, output wire w_wn, output wire t_we, output wire [AW-1:0] t_val
);
    localparam [1:0] IDLE = 0, LANE = 1, THR = 2;
    reg [1:0] st; reg [$clog2(NB)-1:0] j; reg [NB-1:0] d_wp, d_wn; reg [AW-1:0] d_thr;
    assign busy  = (st != IDLE) | start;
    assign w_we  = (st == LANE); assign w_wp = d_wp[j]; assign w_wn = d_wn[j];
    assign t_we  = (st == THR);  assign t_val = d_thr;
    always @(posedge clk) begin
        if (rst) begin st <= IDLE; j <= 0; end
        else case (st)
            IDLE: if (start) begin d_wp <= wp; d_wn <= wn; d_thr <= thr; j <= 0; st <= LANE; end
            LANE: if (j == NB - 1) st <= THR; else j <= j + 1'b1;
            THR:  st <= IDLE;
            default: st <= IDLE;
        endcase
    end
endmodule
`default_nettype wire
