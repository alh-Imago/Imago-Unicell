// hexn_raw_engine_v1.v -- Hex-N open unit stage 4a: RAW WORD STREAM (new file 1 Nov 2026). Mode 3. The ESP32 writes a batch of 32-bit scorer words (SCORE, LOAD or BIAS words in ANY mix) into the scratch RAM at address 0..count-1,
// then changes the 'go' register. The engine feeds the words one by one to its own scorer (hexn_scorer_v1) and writes each SCORE result back into the scratch RAM at out_base, out_base+1, ... in order. LOAD and BIAS words give no result.
// So loading a table and streaming sensor data are the same act: both are words in the stream. The scorer's weights are NOT cleared by a reset or a mode change (only its bias is), so a table loaded once stays until overwritten.
// ctl = {out_base[27:16], count[15:0]}; go = any change starts a run; busy is high during a run; nres = number of results written (saturates at 255).
// The scratch RAM has ONE write port, shared with the SPI writes: do not write over SPI while busy. Reads over SPI are fine at any time.
`default_nettype none
module hexn_raw_engine_v1 (
    input  wire clk, input wire rst,
    input  wire [31:0] ctl, input wire [31:0] go,
    output reg  [9:0] ra, input wire [31:0] rd,                 // scratch read: address ra, data rd two cycles later
    output wire we, output reg [9:0] wa, output reg [31:0] wd,   // scratch write
    output wire busy, output reg [7:0] nres
);
    localparam S_IDLE = 0, S_A = 1, S_B = 2, S_C = 3, S_D = 4, S_E = 5;
    reg [2:0] st = S_IDLE; reg [31:0] go_q = 0; reg [15:0] cnt, i; reg [11:0] ob; reg [9:0] o;
    reg [31:0] in_data; reg in_valid; wire in_ack, out_valid; wire [31:0] out_data;
    hexn_scorer_v1 SC (.clk(clk), .rst(rst), .in_data(in_data), .in_valid(in_valid), .in_ack(in_ack), .out_data(out_data), .out_valid(out_valid), .out_ack(st == S_E));
    assign busy = (st != S_IDLE);
    assign we = (st == S_E) && out_valid;
    always @* begin wa = ob[9:0] + o; wd = out_data; end
    always @(posedge clk) begin
        go_q <= go;
        if (rst) begin st <= S_IDLE; in_valid <= 0; nres <= 0; end
        else case (st)
            S_IDLE: if (go != go_q) begin cnt <= ctl[15:0]; ob <= ctl[27:16]; i <= 0; o <= 0; nres <= 0; if (ctl[15:0] != 0) st <= S_A; end
            S_A: begin ra <= i[9:0]; st <= S_B; end
            S_B: st <= S_C;                                         // the RAM read happens at this edge
            S_C: begin in_data <= rd; in_valid <= 1; st <= S_D; end
            S_D: if (in_ack) begin
                    in_valid <= 0;
                    if (in_data[31:28] < 4'd12) st <= S_E;          // a SCORE word: wait for its result
                    else if (i + 1 >= cnt) st <= S_IDLE; else begin i <= i + 1'b1; st <= S_A; end
                 end
            S_E: if (out_valid) begin                               // the result is written this cycle (we)
                    o <= o + 1'b1; if (nres != 8'hFF) nres <= nres + 1'b1;
                    if (i + 1 >= cnt) st <= S_IDLE; else begin i <= i + 1'b1; st <= S_A; end
                 end
            default: st <= S_IDLE;
        endcase
    end
endmodule
`default_nettype wire
