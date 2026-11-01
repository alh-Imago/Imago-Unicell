// hexn_raw_engine_v5.v -- Hex-N open unit stage 6 (new file 1 Nov 2026; clone of hexn_raw_engine_v4.v, untouched): adds the NEURAL JUDGE (rtl/hexn_neural_v1.v, 7 weights + bias, 16 bits each) with its own guarded SAVE and RESTORE as control words in the raw stream (Alan, 16:47: 'the save and restore of the weights ... rounds out most of the work to a saved file').
// Everything in v4 is unchanged (its description follows). New words: top nibble 15, bit 0 = 0, bit 2 = 1 (before, such words were ignored). The low four bits of the word: bit 2 = 0 -> the batch judges as in v4 (0xF0000000/2 dump A/B, 0xF0000008/A restore into A/B); bit 2 = 1 -> the NEURAL judge, with {bit 3, bit 1}:
//   0xF0000004 = NJ DUMP:   writes an 11-word RECORD at the result position (not counted in nres): word 0 {16'h4E4A 'NJ', 4'd1 version, 4'd0, 8'd8 values}; word 1 geometry {8'd7 inputs, 8'd6 input bits, 8'd14 weight fraction bits, 8'd16 weight width}; words 2..8 the 7 weights and word 9 the bias, each {16'd0, value}; word 10 = the 32-bit sum of words 0..9.
//   0xF000000C = NJ RESTORE: the NEXT 11 words are a record, CHECKED FIRST: 1 bad magic or value count, 2 wrong geometry, 3 bad checksum, 4 short (fewer than 11 words left) or a value word whose upper 16 bits are not 0. One status word is written (0 ok; counted in nres). A good record replaces all 8 values; a refused one is skipped whole and the judge is NOT touched.
//   0xF0000006 = NJ EVAL, 0xF000000E = NJ LEARN: the NEXT 2 words are the inputs: word a = x[31:0]; word b = {11'd0, m2, t[9:0], x[41:32]} (x = 7 inputs of 6 bits, input i at bits 6i+5:6i; t = teacher x256 as 10-bit two's complement; m2 = doubled step). One result word per command (counted): y sign-extended to 32 bits.
// The neural judge has its own reset input `nrst` (the global reset only), so its weights survive leaving the raw-stream mode, as the scorer's tables do. The scratch RAM write port is shared with SPI: no SPI writes while busy.
// ---- the v4 description ----
// Everything in v3 is unchanged (batch interface, two judges, jc, CONTROL word with CLEAR). Top nibble 15 is now used (bit 0 must be 0, otherwise the word is ignored as before):
//   0xF0000000 = DUMP judge A,  0xF0000002 = DUMP judge B:  writes a RECORD of 260 words at the current result position (they are not counted in nres):
//        word 0  header  {16'h4857 'HW', 4'd1 version, 4'd judge (0 A, 1 B), 8'd2 classes}
//        word 1  geometry {8'd8 sensors, 8'd16 bin slots, 16'd256 entries}
//        words 2..257  256 LOAD words: for address k = 0..127: class 0 then class 1 (every entry, zeros included)
//        word 258 a BIAS word
//        word 259 checksum = the 32-bit sum of words 0..258
//   0xF0000008 = RESTORE into judge A,  0xF000000A = RESTORE into judge B:  the NEXT 260 words of the stream are a record. The whole record is CHECKED FIRST (nothing is written to the judge until it passes):
//        1 bad magic/version/class count (the judge number in the header is ignored: a record from A may be restored into B), 2 wrong array size (sensors, bin slots, entries), 3 bad checksum, 4 malformed or short (a body word that is not the expected LOAD word for its position: class and address must run in order; the bias word; or fewer than 260 words left in the stream).
//      One status word is written at the result position (counted in nres): 0 = restored, 1..4 = refused with that reason. A refused record is skipped (all 260 words) and the judge is NOT touched. A good record replaces ALL 256 entries and the bias.
// The scratch RAM write port is shared with SPI: no SPI writes while busy.
`default_nettype none
module hexn_raw_engine_v5 (
    input  wire clk, input wire rst, input wire nrst,
    input  wire [31:0] ctl, input wire [31:0] go, input wire [2:0] jc_in,
    output reg  [9:0] ra, input wire [31:0] rd,
    output wire we, output wire [9:0] wa, output reg [31:0] wd,
    output wire busy, output reg [7:0] nres
);
    localparam S_IDLE = 0, S_A = 1, S_B = 2, S_C = 3, S_F = 4, S_D = 5, S_E = 6, S_N = 7, S_CL = 8, S_CX = 9, S_CY = 10, S_CW = 11,
               S_H0 = 12, S_H1 = 13, S_DS = 14, S_DW = 15, S_CK = 16, S_RA = 17, S_RB = 18, S_RC = 19, S_RD = 20, S_RW = 21,
               S_JX = 22, S_QA = 23, S_QB = 24, S_QC = 25, S_QD = 26, S_QW = 27, S_PA = 28, S_PB = 29, S_PC = 30, S_PE = 31, S_EA = 32, S_EB = 33, S_EC = 34, S_ED = 35, S_EE = 36, S_EG = 37, S_EW = 38, S_EY = 39;
    localparam [31:0] H1 = {8'd8, 8'd16, 16'd256};
    localparam [19:0] MAGIC = {16'h4857, 4'd1};
    localparam RECN = 260;
    localparam [19:0] MAGICN = {16'h4E4A, 4'd1};
    localparam [31:0] H1N = {8'd7, 8'd6, 8'd14, 8'd16};
    reg [5:0] st = S_IDLE; reg [1:0] cmask = 0; reg clr_a = 0, clr_b = 0; reg [31:0] go_q = 0; reg [15:0] cnt, i; reg [11:0] ob; reg [9:0] o; reg [2:0] jc, jc_sv; reg [1:0] mask; reg cur, is_score;
    reg [31:0] in_data; reg in_valid;
    reg dj, dump_a_r, dump_b_r; reg [31:0] ck, rck; reg [8:0] j; reg [2:0] rcode; reg [8:0] rep_n; reg rt_sel;
    // ---- the neural judge (rtl/hexn_neural_v1.v) ----
    reg n_ge = 0, n_gl = 0, n_ww = 0, nm2 = 0, nlearn = 0; reg [41:0] nx = 0; reg signed [9:0] nt = 0; reg [3:0] n_wa = 0, jn = 0, pk = 0; reg signed [15:0] n_wd = 0;
    wire signed [9:0] ny; wire ndone; wire [127:0] nw;
    hexn_neural_v1 NJ (.clk(clk), .rst(nrst), .go_eval(n_ge), .go_learn(n_gl), .x(nx), .t(nt), .m2(nm2), .w_wr(n_ww), .w_addr(n_wa), .w_data(n_wd), .y(ny), .done(ndone), .w_flat(nw));
    wire [3:0] jm = jn - 4'd2; wire [15:0] wsel = nw[{jm, 4'd0} +: 16];
    wire ack_a, ack_b, ov_a, ov_b, cb_a, cb_b; wire [31:0] oa, ob_w;
    wire dmv_a, dml_a, dmb_a, dmv_b, dml_b, dmb_b; wire [31:0] dmd_a, dmd_b;
    hexn_scorer_v3 SA (.clk(clk), .rst(rst), .in_data(in_data), .in_valid(in_valid && !cur), .in_ack(ack_a), .out_data(oa),   .out_valid(ov_a), .out_ack(st == S_E && !cur), .clr(clr_a), .clr_busy(cb_a),
                       .dump(dump_a_r), .dm_valid(dmv_a), .dm_data(dmd_a), .dm_last(dml_a), .dm_busy(dmb_a));
    hexn_scorer_v3 SB (.clk(clk), .rst(rst), .in_data(in_data), .in_valid(in_valid &&  cur), .in_ack(ack_b), .out_data(ob_w), .out_valid(ov_b), .out_ack(st == S_E &&  cur), .clr(clr_b), .clr_busy(cb_b),
                       .dump(dump_b_r), .dm_valid(dmv_b), .dm_data(dmd_b), .dm_last(dml_b), .dm_busy(dmb_b));
    wire dmv = dj ? dmv_b : dmv_a, dml = dj ? dml_b : dml_a; wire [31:0] dmd = dj ? dmd_b : dmd_a;
    assign busy = (st != S_IDLE);
    assign we = ((st == S_E) && (cur ? ov_b : ov_a)) || (st == S_H0) || (st == S_H1) || (st == S_CK) || (st == S_RW) || (st == S_JX) || (st == S_QW) || (st == S_EY) || ((st == S_DW) && dmv);
    assign wa = ob[9:0] + o;
    always @* case (st)
        S_H0: wd = {MAGIC, 3'd0, dj, 8'd2}; S_H1: wd = H1; S_DW: wd = dmd; S_CK: wd = ck; S_RW: wd = {29'd0, rcode}; S_QW: wd = {29'd0, rcode}; S_EY: wd = {{22{ny[9]}}, ny};
        S_JX: wd = (jn == 4'd0) ? {MAGICN, 4'd0, 8'd8} : (jn == 4'd1) ? H1N : (jn == 4'd10) ? ck : {16'd0, wsel};
        default: wd = cur ? ob_w : oa;
    endcase
    // the body word expected at record position j (2..257): LOAD, class = (j-2)[0], address = (j-2)[7:1], weight free
    wire [8:0] m = j - 9'd2;
    wire body_ok = (rd[31:28] == 4'd12) && (rd[27:25] == 3'd0) && (rd[24] == m[0]) && (rd[23] == 1'b0) && (rd[22:16] == m[7:1]) && (rd[15:8] == 8'd0);
    always @(posedge clk) begin
        go_q <= go; dump_a_r <= 1'b0; dump_b_r <= 1'b0; n_ge <= 1'b0; n_gl <= 1'b0; n_ww <= 1'b0;
        if (rst) begin st <= S_IDLE; in_valid <= 0; nres <= 0; cur <= 0; clr_a <= 0; clr_b <= 0; rep_n <= 0; end
        else case (st)
            S_IDLE: if (go != go_q) begin cnt <= ctl[15:0]; ob <= ctl[27:16]; i <= 0; o <= 0; nres <= 0; jc <= jc_in; rep_n <= 0; if (ctl[15:0] != 0) st <= S_A; end
            S_A: begin ra <= i[9:0]; st <= S_B; end
            S_B: st <= S_C;                                         // the RAM read happens at this edge
            S_C: begin
                in_data <= rd; is_score <= (rd[31:28] < 4'd12);
                if (rd[31:28] == 4'd14) begin                                                              // CONTROL word: judge control (+ optional clear), no result
                    jc <= rd[2:0]; mask <= 2'b00;
                    if (rd[3]) begin cmask <= (rd[2:1] == 2'd0) ? 2'b01 : (rd[2:1] == 2'd1) ? 2'b10 : 2'b11; st <= S_CL; end else st <= S_N;
                end
                else if (rd[31:28] == 4'd15) begin                                                         // DUMP / RESTORE (judge in bits 2:1: 0 A, 1 B), bit 0 must be 0
                    mask <= 2'b00;
                    if (rd[0]) st <= S_N;                                                                  // not a defined word: ignored as in v3
                    else if (rd[2]) begin                                                                  // the neural judge: {bit 3, bit 1} = 00 dump, 10 restore, 01 eval, 11 learn
                        case ({rd[3], rd[1]})
                            2'b00: begin jn <= 4'd0; ck <= 32'd0; st <= S_JX; end
                            2'b10: begin jn <= 4'd0; rck <= 32'd0; rcode <= 3'd0; st <= S_QA; end
                            default: begin nlearn <= rd[3]; st <= S_EA; end
                        endcase
                    end
                    else if (!rd[3]) begin dj <= rd[1]; st <= S_H0; end
                    else begin rt_sel <= rd[1]; j <= 0; rck <= 0; rcode <= 0; st <= S_RA; end
                end
                else begin mask <= (rd[31:28] < 4'd12) ? (jc[0] ? 2'b11 : 2'b01) : (jc[2:1] == 2'd0 ? 2'b01 : jc[2:1] == 2'd1 ? 2'b10 : 2'b11); st <= S_F; end
            end
            S_F: begin cur <= !mask[0]; in_valid <= 1; st <= S_D; end                                    // lowest remaining judge first (A, then B)
            S_D: if (cur ? ack_b : ack_a) begin
                    in_valid <= 0; mask[cur] <= 1'b0;
                    st <= is_score ? S_E : S_N;
                 end
            S_E: if (cur ? ov_b : ov_a) begin                       // the result is written this cycle (we)
                    o <= o + 1'b1; if (nres != 8'hFF) nres <= nres + 1'b1; st <= S_N;
                 end
            S_N: if (mask != 2'b00) st <= S_F;                      // the same word goes to the next judge
                 else if (rep_n != 0) begin                          // replaying a checked record: bias is the last body word, the checksum word after it is skipped
                    rep_n <= rep_n - 1'b1;
                    if (rep_n == 9'd1) begin jc <= jc_sv; if (i + 2 >= cnt) st <= S_IDLE; else begin i <= i + 2; st <= S_A; end end
                    else begin i <= i + 1'b1; st <= S_A; end
                 end
                 else if (i + 1 >= cnt) st <= S_IDLE; else begin i <= i + 1'b1; st <= S_A; end
            S_CL: begin clr_a <= cmask[0]; clr_b <= cmask[1]; st <= S_CX; end                      // one-cycle clear pulse to the chosen judge(s)
            S_CX: begin clr_a <= 1'b0; clr_b <= 1'b0; st <= S_CY; end
            S_CY: st <= S_CW;                                                                         // one more clock so clr_busy has risen
            S_CW: if (!cb_a && !cb_b) st <= S_N;
            // ---- DUMP: header, geometry, then the judge's own walk, then the checksum
            S_H0: begin ck <= {MAGIC, 3'd0, dj, 8'd2}; o <= o + 1'b1; st <= S_H1; end
            S_H1: begin ck <= ck + H1; o <= o + 1'b1; st <= S_DS; end
            S_DS: begin dump_a_r <= !dj; dump_b_r <= dj; st <= S_DW; end
            S_DW: if (dmv) begin o <= o + 1'b1; ck <= ck + dmd; if (dml) st <= S_CK; end
            S_CK: begin o <= o + 1'b1; st <= S_N; end
            // ---- GUARDED RESTORE: read and check the whole record before the judge is touched
            S_RA: begin ra <= i[9:0] + 10'd1 + {1'b0, j}; st <= S_RB; end
            S_RB: st <= S_RC;
            S_RC: begin
                if (i + 16'd261 > cnt) begin rcode <= 3'd4; st <= S_RD; end                                 // fewer than 260 words left
                else begin
                    if (j == 9'd0 && (rd[31:12] != MAGIC || rd[7:0] != 8'd2) && rcode == 0) rcode <= 3'd1;
                    if (j == 9'd1 && rd != H1 && rcode == 0) rcode <= 3'd2;
                    if (j >= 9'd2 && j <= 9'd257 && !body_ok && rcode == 0) rcode <= 3'd4;
                    if (j == 9'd258 && !(rd[31:28] == 4'd13 && rd[27:16] == 12'd0) && rcode == 0) rcode <= 3'd4;
                    if (j == 9'd259 && rd != rck && rcode == 0) rcode <= 3'd3;
                    if (j != 9'd259) rck <= rck + rd;
                    if (j == 9'd259) st <= S_RD; else begin j <= j + 1'b1; st <= S_RA; end
                end
            end
            S_RD: st <= S_RW;
            S_RW: begin                                                                                   // the status word is written this cycle (we)
                o <= o + 1'b1; if (nres != 8'hFF) nres <= nres + 1'b1;
                if (rcode == 3'd0) begin jc_sv <= jc; jc <= {rt_sel ? 2'b01 : 2'b00, 1'b0}; rep_n <= 9'd257; i <= i + 16'd3; st <= S_A; end    // replay the body (words 2..258) into the chosen judge
                else begin i <= i + 16'd260; st <= S_N; end                                                // skip the refused record
            end
            // ---- NEURAL JUDGE: dump (11 words), guarded restore, eval and learn
            S_JX: begin o <= o + 1'b1; if (jn != 4'd10) ck <= ck + wd; if (jn == 4'd10) st <= S_N; else jn <= jn + 1'b1; end
            S_QA: begin ra <= i[9:0] + 10'd1 + {6'd0, jn}; st <= S_QB; end
            S_QB: st <= S_QC;
            S_QC: begin
                if (i + 16'd12 > cnt) begin rcode <= 3'd4; st <= S_QD; end                                  // fewer than 11 words left
                else begin
                    if (jn == 4'd0 && (rd[31:12] != MAGICN || rd[7:0] != 8'd8) && rcode == 0) rcode <= 3'd1;
                    if (jn == 4'd1 && rd != H1N && rcode == 0) rcode <= 3'd2;
                    if (jn >= 4'd2 && jn <= 4'd9 && rd[31:16] != 16'd0 && rcode == 0) rcode <= 3'd4;
                    if (jn == 4'd10 && rd != rck && rcode == 0) rcode <= 3'd3;
                    if (jn != 4'd10) rck <= rck + rd;
                    if (jn == 4'd10) st <= S_QD; else begin jn <= jn + 1'b1; st <= S_QA; end
                end
            end
            S_QD: st <= S_QW;
            S_QW: begin                                                                                   // the status word is written this cycle (we)
                o <= o + 1'b1; if (nres != 8'hFF) nres <= nres + 1'b1;
                if (rcode == 3'd0) begin pk <= 4'd0; st <= S_PA; end else begin i <= i + 16'd11; st <= S_N; end
            end
            S_PA: begin ra <= i[9:0] + 10'd3 + {6'd0, pk}; st <= S_PB; end
            S_PB: st <= S_PC;
            S_PC: begin n_ww <= 1'b1; n_wa <= pk; n_wd <= rd[15:0]; if (pk == 4'd7) begin i <= i + 16'd11; st <= S_PE; end else begin pk <= pk + 1'b1; st <= S_PA; end end
            S_PE: st <= S_N;
            S_EA: begin ra <= i[9:0] + 10'd1; st <= S_EB; end
            S_EB: st <= S_EC;
            S_EC: begin nx[31:0] <= rd; ra <= i[9:0] + 10'd2; st <= S_ED; end
            S_ED: st <= S_EE;
            S_EE: begin nx[41:32] <= rd[9:0]; nt <= rd[19:10]; nm2 <= rd[20]; st <= S_EG; end
            S_EG: begin n_ge <= !nlearn; n_gl <= nlearn; st <= S_EW; end
            S_EW: if (ndone) st <= S_EY;
            S_EY: begin o <= o + 1'b1; if (nres != 8'hFF) nres <= nres + 1'b1; i <= i + 16'd2; st <= S_N; end   // y is written this cycle (we)
            default: st <= S_IDLE;
        endcase
    end
endmodule
`default_nettype wire
