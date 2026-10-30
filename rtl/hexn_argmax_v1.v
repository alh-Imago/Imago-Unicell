`default_nettype none
// hexn_argmax_v1.v -- the controller's answer stage for the signed detectors (30 Oct 2026): the index of the LARGEST of K signed margins, ties to the lowest index (a priority chain). Combinational.
// SIZING AND REFERENCE MODULE; the old controller (unique strict maximum of K burst counters above zero) is in hexn_bank_v9.v and later.
module hexn_argmax_v1 #(parameter K = 8, parameter MW = 10) (input wire signed [K*MW-1:0] m, output reg [$clog2(K)-1:0] win);
    integer k; reg signed [MW-1:0] best;
    always @* begin
        best = m[MW-1:0]; win = 0;
        for (k = 1; k < K; k = k + 1) if ($signed(m[k*MW +: MW]) > best) begin best = $signed(m[k*MW +: MW]); win = k; end
    end
endmodule
`default_nettype wire
