`default_nettype none
// hexn_glue_v1.v -- Hex-N GLUE BUFFER between the detector bank and a full cell (Alan 22 Oct 2026: "a buffer like the cell glue bridge: absorb the first, drip it, then fire the second as required").
// New file. One lane per detector. CAPTURE: while cap_en is high, a 3-bit counter per lane counts the clocks the detector's tx is high (0..7 = the burst length = the detector's margin+1, i.e. its confidence); clr empties all counters.
// A stale burst sent outside the capture window (the detector replays its previous result in the first window of a run) is never captured. REPLAY: when play pulses, every lane loads its captured length into a down counter and drives
// out high for that many clocks, starting the clock after the pulse (so clock 0 of the receiving cell's window stays quiet, as for a detector's own burst). The captured value is kept after replay, so it can be replayed again.
module hexn_glue_v1 #(parameter K = 19) (
    input  wire         clk, input wire rst,
    input  wire         clr, input wire cap_en, input wire play,
    input  wire [K-1:0] tx,
    output wire [K-1:0] out,
    output wire [3*K-1:0] cap_flat
);
    reg [2:0] cap [0:K-1]; reg [2:0] rep [0:K-1];
    genvar g;
    generate for (g = 0; g < K; g = g + 1) begin : L
        always @(posedge clk) begin
            if (rst || clr) begin cap[g] <= 0; rep[g] <= 0; end
            else begin
                if (cap_en && tx[g] && cap[g] != 3'd7) cap[g] <= cap[g] + 1'b1;
                if (play) rep[g] <= cap[g]; else if (rep[g] != 0) rep[g] <= rep[g] - 1'b1;
            end
        end
        assign out[g] = (rep[g] != 0);
        assign cap_flat[3*g +: 3] = cap[g];
    end endgenerate
endmodule
`default_nettype wire
