// hexn_scorer_v1.v -- Hex-N: the Tang-side BATCH SCORER (new file 1 Nov 2026; ledger row after 00:35). A flex-style design (one entry lane, one exit) that sits where the CORDIC sits in sd_unit_v1,
// so the SPI bridge, playout RAM and capture RAM are reused unchanged. It holds a two-class weight table in block RAM and scores layer-1 bin words: score_c = sum over sensors of W[c][sensor][bin].
// Input word. The top nibble [31:28] is both sensor 7's bin and the word type: layer 1 has 12 bins (0..11), so the values 12 and 13 are free to mean 'command':
//   top nibble 0..11 : SCORE. Sensor i's bin (0..11) sits in bits 4i+3 : 4i (NS = 8 sensors; sensor 7 is the top nibble). One result word comes out per SCORE word.
//   top nibble 12    : LOAD  [24] class (0/1), [22:16] address = {sensor[2:0], bin[3:0]}, [7:0] signed 8-bit weight. No result.
//   top nibble 13    : BIAS  [15:0] signed bias added to class 1's score before the decision (the 'bias step'). No result.
//   top nibble 14, 15: reserved (ignored, no result).
// Result word: [31] pred (1 if score1 + bias > score0), [27:16] score1 (signed 12), [11:0] score0 (signed 12); the rest 0. Scores fit: 8 * 127 = 1016 (12 bits signed holds +-2047).
// One word is taken at a time (about NS + 4 cycles per SCORE word); the entry lane is not acked while a score is running or the result is waiting, so nothing is lost.
// The weights are the table-refresh log-likelihoods rounded to whole numbers (the host does the quantising). The RAMs are plain synchronous arrays (BSRAM on Gowin).
`default_nettype none
module hexn_scorer_v1 (
    input  wire        clk,
    input  wire        rst,
    input  wire [31:0] in_data,
    input  wire        in_valid,
    output wire        in_ack,
    output reg  [31:0] out_data,
    output reg         out_valid,
    input  wire        out_ack
);
    localparam NS = 8;
    reg signed [7:0] m0 [0:127];
    reg signed [7:0] m1 [0:127];
    integer q; initial for (q = 0; q < 128; q = q + 1) begin m0[q] = 0; m1[q] = 0; end
    reg signed [15:0] bias;
    reg [31:0] bn;
    reg [3:0]  idx;                 // next sensor to issue
    reg        run;
    reg [6:0]  raddr;
    reg        v1, v2;
    reg signed [7:0] rd0, rd1;
    reg signed [11:0] s0, s1;

    wire accept = in_valid && !run && !out_valid;
    assign in_ack = accept;

    always @(posedge clk) begin
        rd0 <= m0[raddr]; rd1 <= m1[raddr];
        if (rst) begin
            run <= 0; v1 <= 0; v2 <= 0; out_valid <= 0; out_data <= 0; bias <= 0; idx <= 0; s0 <= 0; s1 <= 0; raddr <= 0; bn <= 0;
        end else begin
            if (out_valid && out_ack) out_valid <= 0;
            if (accept) begin
                if (in_data[31:28] < 4'd12) begin bn <= in_data; idx <= 0; s0 <= 0; s1 <= 0; run <= 1; end
                else case (in_data[31:28])
                    4'd12: begin if (in_data[24]) m1[in_data[22:16]] <= in_data[7:0]; else m0[in_data[22:16]] <= in_data[7:0]; end
                    4'd13: bias <= in_data[15:0];
                    default: ;
                endcase
            end
            if (run) begin
                v1 <= 0;
                if (idx < NS) begin raddr <= {idx[2:0], bn[idx*4 +: 4]}; v1 <= 1; idx <= idx + 1'b1; end
                v2 <= v1;
                if (v2) begin s0 <= s0 + rd0; s1 <= s1 + rd1; end
                if (idx == NS && !v1 && !v2) begin
                    run <= 0; out_valid <= 1;
                    out_data <= {((s1 + bias) > s0), 3'b000, s1[11:0], 4'b0000, s0[11:0]};
                end
            end
        end
    end
endmodule
`default_nettype wire
