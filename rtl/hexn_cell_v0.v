// hexn_cell_v0.v -- Hex-N cell, first behavioural RTL (scoping prototype, NOT a decision). Follows docs/hex-n/cell-internals-v0.1.md:
//   FACES faces, CH channels per face (channel = one in/out pair), one window tick shared by the whole mesh.
//   At each tick: sample `in` (masked by the channel's ACTIVE bit), popcount per face, fire = popcount >= thr[face],
//   out[c] <= GATE[c](fire, in[c]) -- registered, so a channel's output only ever depends on LAST window's inputs (no combinational loop).
// Assumptions the note leaves open (each is a parameter or a marked line, see docs/hex-n/walkthrough-v0.2.md):
//   NOT_OF_IN=0: gate code 3 = NOT(fire); 1: NOT(in). An inactive channel contributes 0 to the popcount and drives 0.
//   The 16-bit shared bias is NOT applied here (its arithmetic is undecided): `bias` is an input that is ignored, kept so the port list is stable.
`default_nettype none
module hexn_cell_v0 #(
    parameter FACES = 6, parameter CH = 4, parameter TW = 3, parameter NOT_OF_IN = 0
) (
    input  wire                      clk,
    input  wire                      rst,
    input  wire                      tick,                       // one pulse per window, shared by all cells
    input  wire [FACES*CH-1:0]       in_bus,                     // face-major: face f, channel c = bit f*CH+c
    output reg  [FACES*CH-1:0]       out_bus,
    output reg  [FACES-1:0]          fire,
    input  wire [FACES*CH-1:0]       cfg_active,
    input  wire [2*FACES*CH-1:0]     cfg_gate,                   // 2 bits per channel: 0 AND, 1 OR, 2 XOR, 3 NOT
    input  wire [FACES*TW-1:0]       cfg_thr,                    // per-face threshold
    input  wire [15:0]               bias                        // reserved, unused
);
    integer f, c;
    reg [3:0] pc;
    reg       fr, a, g;
    reg [1:0] gs;
    always @(posedge clk) begin
        if (rst) begin out_bus <= 0; fire <= 0; end
        else if (tick) begin
            for (f = 0; f < FACES; f = f + 1) begin
                pc = 0;
                for (c = 0; c < CH; c = c + 1) pc = pc + (in_bus[f*CH+c] & cfg_active[f*CH+c]);
                fr = (pc >= cfg_thr[f*TW +: TW]);
                fire[f] <= fr;
                for (c = 0; c < CH; c = c + 1) begin
                    gs = cfg_gate[2*(f*CH+c) +: 2]; a = in_bus[f*CH+c];
                    case (gs)
                        2'd0: g = fr & a;
                        2'd1: g = fr | a;
                        2'd2: g = fr ^ a;
                        default: g = NOT_OF_IN ? ~a : ~fr;
                    endcase
                    out_bus[f*CH+c] <= g & cfg_active[f*CH+c];
                end
            end
        end
    end
endmodule
`default_nettype wire
