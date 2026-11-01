// hexn_scorer_v3.v -- Hex-N: the Tang-side BATCH SCORER, VERSION 3 (new file 1 Nov 2026; clone of hexn_scorer_v2.v, untouched): adds a DUMP walker (Alan, 13:01: dump the judges' weights completely, with a guard). A one-clock pulse on `dump` (taken when the scorer is idle) walks both weight RAMs and the bias and sends them out on dm_valid / dm_data / dm_last, one word per clock, as ordinary LOAD and BIAS words:
//   for address k = 0..127: LOAD class 0 address k, LOAD class 1 address k (256 words, every entry, zeros included), then ONE BIAS word. Replaying those words into any scorer of this size restores it completely (the load format IS the dump format). dm_busy is high meanwhile; no input word is accepted (in_ack low). The weights are read through the scoring read port (raddr), which is idle then.
// v2 text follows.
// hexn_scorer_v2.v -- Hex-N: the Tang-side BATCH SCORER, VERSION 2 (new file 1 Nov 2026; clone of hexn_scorer_v1.v, untouched): adds a CLEAR input. A one-cycle pulse on `clr` (taken when the scorer is idle) zeroes both weight RAMs (128 entries each, one per clock) and the bias; `clr_busy` is high meanwhile and no input word is accepted. Everything else is the same, word for word. (Alan, 21:47: there was a CLEAR in the earlier tier design, 29 Oct.) v1 text: the Tang-side BATCH SCORER (ledger row after 00:35). A flex-style design (one entry lane, one exit) that sits where the CORDIC sits in sd_unit_v1,
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
module hexn_scorer_v3 (
    input  wire        clk,
    input  wire        rst,
    input  wire [31:0] in_data,
    input  wire        in_valid,
    output wire        in_ack,
    output reg  [31:0] out_data,
    output reg         out_valid,
    input  wire        out_ack,
    input  wire        clr,
    output wire        clr_busy,
    input  wire        dump,
    output reg         dm_valid, output reg [31:0] dm_data, output reg dm_last, output wire dm_busy
);
    localparam NS = 8;
    reg signed [7:0] m0 [0:127];
    reg signed [7:0] m1 [0:127];
    integer q; initial for (q = 0; q < 128; q = q + 1) begin m0[q] = 0; m1[q] = 0; end
    reg        cl_run = 0; reg [6:0] cl_a = 0;                       // clear walker: one address per clock
    assign clr_busy = cl_run;
    reg        we0, we1; reg [6:0] wa; reg [7:0] wd;                  // ONE write port per RAM (so the tools can use block RAM)
    reg signed [15:0] bias;
    reg [31:0] bn;
    reg [3:0]  idx;                 // next sensor to issue
    reg        run;
    reg [6:0]  raddr;
    reg        v1, v2;
    reg signed [7:0] rd0, rd1;
    reg signed [11:0] s0, s1;

    reg dm_run = 0; reg [2:0] dm_ph = 0; reg [6:0] dm_k = 0;
    assign dm_busy = dm_run;
    wire accept = in_valid && !run && !out_valid && !cl_run && !dm_run;
    assign in_ack = accept;

    wire is_load = accept && !rst && (in_data[31:28] == 4'd12);
    always @* begin
        we0 = 0; we1 = 0; wa = in_data[22:16]; wd = in_data[7:0];
        if (cl_run) begin we0 = 1; we1 = 1; wa = cl_a; wd = 8'd0; end
        else if (is_load) begin we1 = in_data[24]; we0 = !in_data[24]; end
    end
    always @(posedge clk) begin
        rd0 <= m0[raddr]; rd1 <= m1[raddr];
        if (we0) m0[wa] <= wd;
        if (we1) m1[wa] <= wd;
        if (rst) begin
            dm_run <= 0; dm_valid <= 0; dm_last <= 0; dm_ph <= 0; dm_k <= 0; dm_data <= 0;
            run <= 0; v1 <= 0; v2 <= 0; out_valid <= 0; out_data <= 0; bias <= 0; idx <= 0; s0 <= 0; s1 <= 0; raddr <= 0; bn <= 0; cl_run <= 0; cl_a <= 0;
        end else begin
            dm_valid <= 0; dm_last <= 0;
            if (dump && !run && !out_valid && !cl_run && !dm_run) begin dm_run <= 1; dm_ph <= 0; dm_k <= 0; raddr <= 0; end
            if (dm_run) case (dm_ph)
                3'd0: dm_ph <= 3'd1;                                                           // the RAM read of address dm_k happens at this edge
                3'd1: begin dm_valid <= 1; dm_data <= {4'd12, 3'd0, 1'b0, 1'b0, dm_k, 8'd0, rd0}; dm_ph <= 3'd2; end        // LOAD class 0
                3'd2: begin dm_valid <= 1; dm_data <= {4'd12, 3'd0, 1'b1, 1'b0, dm_k, 8'd0, rd1};
                            if (dm_k == 7'd127) dm_ph <= 3'd3; else begin dm_k <= dm_k + 1'b1; raddr <= dm_k + 1'b1; dm_ph <= 3'd0; end end   // LOAD class 1
                3'd3: begin dm_valid <= 1; dm_last <= 1; dm_data <= {4'd13, 12'd0, bias}; dm_ph <= 3'd4; end                // BIAS
                default: begin dm_run <= 0; dm_ph <= 0; end
            endcase
            if (clr && !run && !out_valid && !cl_run && !dm_run) begin cl_run <= 1; cl_a <= 0; bias <= 0; end
            if (cl_run) begin if (cl_a == 7'd127) cl_run <= 0; cl_a <= cl_a + 1'b1; end
            if (out_valid && out_ack) out_valid <= 0;
            if (accept) begin
                if (in_data[31:28] < 4'd12) begin bn <= in_data; idx <= 0; s0 <= 0; s1 <= 0; run <= 1; end
                else case (in_data[31:28])
                    4'd12: ;                                          // written through the single write port above
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
