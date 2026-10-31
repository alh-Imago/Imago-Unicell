// hexn_raw_engine_v3.v -- Hex-N open unit stage 4c: as v2 (two judges; clone, v2 untouched) PLUS a CLEAR control: in a CONTROL word (top nibble 14) bit 3 = clear, aimed by bits 2:1 (0 judge A, 1 judge B, 2 or 3 both): both weight tables and the bias of the chosen judge(s) are zeroed (about 130 clocks each, run together), and the new jc applies afterwards. 0xE000000C = clear both. Uses hexn_scorer_v2. v2 text: the RAW WORD STREAM with TWO JUDGES (clone of hexn_raw_engine_v1.v, untouched). Two scorers, A and B, each with its own weight table (the SECOND TABLE).
// Same batch interface as v1 (words in the scratch RAM at 0..count-1, ctl = {out_base, count}, change go to start, results written from out_base).
// JUDGE CONTROL jc[2:0]: bit 0 = TWO JUDGES (a SCORE word is scored by A, then by B: two result words, A first, then B); bits 2:1 = where LOAD and BIAS words go: 0 judge A, 1 judge B, 2 both.
// jc starts each run at `jc_in` (a register or a preset) and can be changed INSIDE the stream by a CONTROL word: top nibble 14, jc in bits 2:0 (no result). So one stream can load table A, switch, load table B, switch, then stream data.
// Top nibble 15 is still reserved (ignored). Weights are not cleared by a reset (only each bias). The scratch RAM write port is shared with SPI: no SPI writes while busy.
`default_nettype none
module hexn_raw_engine_v3 (
    input  wire clk, input wire rst,
    input  wire [31:0] ctl, input wire [31:0] go, input wire [2:0] jc_in,
    output reg  [9:0] ra, input wire [31:0] rd,
    output wire we, output wire [9:0] wa, output wire [31:0] wd,
    output wire busy, output reg [7:0] nres
);
    localparam S_IDLE = 0, S_A = 1, S_B = 2, S_C = 3, S_F = 4, S_D = 5, S_E = 6, S_N = 7, S_CL = 8, S_CX = 9, S_CY = 10, S_CW = 11;
    reg [3:0] st = S_IDLE; reg [1:0] cmask = 0; reg clr_a = 0, clr_b = 0; reg [31:0] go_q = 0; reg [15:0] cnt, i; reg [11:0] ob; reg [9:0] o; reg [2:0] jc; reg [1:0] mask; reg cur, is_score;
    reg [31:0] in_data; reg in_valid;
    wire ack_a, ack_b, ov_a, ov_b, cb_a, cb_b; wire [31:0] oa, ob_w;
    hexn_scorer_v2 SA (.clk(clk), .rst(rst), .in_data(in_data), .in_valid(in_valid && !cur), .in_ack(ack_a), .out_data(oa),   .out_valid(ov_a), .out_ack(st == S_E && !cur), .clr(clr_a), .clr_busy(cb_a));
    hexn_scorer_v2 SB (.clk(clk), .rst(rst), .in_data(in_data), .in_valid(in_valid &&  cur), .in_ack(ack_b), .out_data(ob_w), .out_valid(ov_b), .out_ack(st == S_E &&  cur), .clr(clr_b), .clr_busy(cb_b));
    assign busy = (st != S_IDLE);
    assign we = (st == S_E) && (cur ? ov_b : ov_a);
    assign wa = ob[9:0] + o; assign wd = cur ? ob_w : oa;
    always @(posedge clk) begin
        go_q <= go;
        if (rst) begin st <= S_IDLE; in_valid <= 0; nres <= 0; cur <= 0; clr_a <= 0; clr_b <= 0; end
        else case (st)
            S_IDLE: if (go != go_q) begin cnt <= ctl[15:0]; ob <= ctl[27:16]; i <= 0; o <= 0; nres <= 0; jc <= jc_in; if (ctl[15:0] != 0) st <= S_A; end
            S_A: begin ra <= i[9:0]; st <= S_B; end
            S_B: st <= S_C;                                         // the RAM read happens at this edge
            S_C: begin
                in_data <= rd; is_score <= (rd[31:28] < 4'd12);
                if (rd[31:28] == 4'd14) begin                                                              // CONTROL word: judge control (+ optional clear), no result
                    jc <= rd[2:0]; mask <= 2'b00;
                    if (rd[3]) begin cmask <= (rd[2:1] == 2'd0) ? 2'b01 : (rd[2:1] == 2'd1) ? 2'b10 : 2'b11; st <= S_CL; end else st <= S_N;
                end
                else if (rd[31:28] == 4'd15) begin st <= S_N; mask <= 2'b00; end                           // reserved: ignored
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
                 else if (i + 1 >= cnt) st <= S_IDLE; else begin i <= i + 1'b1; st <= S_A; end
            S_CL: begin clr_a <= cmask[0]; clr_b <= cmask[1]; st <= S_CX; end                      // one-cycle clear pulse to the chosen judge(s)
            S_CX: begin clr_a <= 1'b0; clr_b <= 1'b0; st <= S_CY; end
            S_CY: st <= S_CW;                                                                         // one more clock so clr_busy has risen
            S_CW: if (!cb_a && !cb_b) st <= S_N;
            default: st <= S_IDLE;
        endcase
    end
endmodule
`default_nettype wire
