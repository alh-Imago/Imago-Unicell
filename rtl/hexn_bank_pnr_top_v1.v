`default_nettype none
// hexn_bank_pnr_top_v1.v -- wrapper that lets the whole bank (hexn_bank_v1) be placed and routed on a board with few pins: a serial load register carries the sample, label, threshold-count and the command bits in; the answer comes out on a few pins.
// The load register is only for this test (about NB+KW+12 flip-flops); a real bank would sit behind its own interface. Load: shift bits in on sin (one per clock, MSB first), then pulse ld for one clock.
// Field order, MSB first: s_bits[NB], s_label[KW], t_in[CB], tr_cmd[3], tr_start, run_start.
module hexn_bank_pnr_top_v1 #(parameter K = 4, parameter NB = 12, parameter AW = 6, parameter S = 16, parameter CB = 6) (
    input  wire clk, input wire rst, input wire sin, input wire ld,
    output wire ans_valid, output wire [$clog2(K)-1:0] ans_class, output wire tr_busy, output wire run_busy
);
    localparam KW = $clog2(K);
    localparam FW = NB + KW + CB + 3 + 2;
    reg [FW-1:0] sh; reg [NB-1:0] s_bits; reg [KW-1:0] s_label; reg [CB-1:0] t_in; reg [2:0] tr_cmd; reg tr_start, run_start;
    always @(posedge clk) begin
        sh <= {sh[FW-2:0], sin};
        tr_start <= 1'b0; run_start <= 1'b0;
        if (ld) begin
            {s_bits, s_label, t_in, tr_cmd} <= sh[FW-1:2];
            tr_start <= sh[1]; run_start <= sh[0];
        end
    end
    wire run_done;
    hexn_bank_v1 #(.K(K), .NB(NB), .AW(AW), .S(S), .CB(CB)) bank(.clk(clk), .rst(rst), .tr_start(tr_start), .tr_cmd(tr_cmd), .tr_busy(tr_busy), .s_bits(s_bits), .s_label(s_label), .t_in(t_in),
        .run_start(run_start), .run_busy(run_busy), .run_done(run_done), .ans_valid(ans_valid), .ans_class(ans_class), .cnt_flat());
endmodule
`default_nettype wire
