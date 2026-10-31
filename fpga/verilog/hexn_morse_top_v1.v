// hexn_morse_top_v1.v -- Hex-N (new file 1 Nov 2026): a MORSE KEY on the Tang alone, with the HW-262 shield. Button A1 is the key (the buzzer sounds while it is down); button A2 clears the display.
// The time dimension: a 1 ms counter measures how long the key is DOWN (the press length) and how long it is UP (the space length). Each length becomes a layer-1 bin (floor(log2 ms), 0..11) in its own sensor slot of ONE
// scorer table (hexn_scorer_v1, loaded from a ROM at power-up): slot 0 judges the press (class 1 = dash), slot 1 the space (class 1 = letter gap or longer), slot 2 the space (class 1 = word gap). The unused slots carry the
// neutral bin 15. The decoder collects dots and dashes (up to 5) and, when the scorer calls a letter gap, turns them into a character; a word gap adds a space. The display shows the last four characters
// (a decimal point on the right-hand digit while symbols of the next letter are pending; digits show with their own point). With the starting table: dot under 256 ms, dash 256 ms or more, letter gap 256 ms or more, word gap 1024 ms or more
// (so a dot of about 150 to 200 ms, a dash three times that, a letter gap three units and a word gap seven units). LEDs (lit = true): 0 heartbeat, 1 key down, 2 last symbol was a dash, 3 letter gap seen, 4 word gap seen, 5 table loaded.
`default_nettype none
module hexn_morse_top_v1 #(
    parameter TICK = 27000, parameter DEBMS = 10, parameter RSTW = 16
) (
    input  wire BOARD_CLK, input wire KEY_S1,
    input  wire BTN1_N, input wire BTN2_N,
    output wire DISP_LATCH, output wire DISP_CLK, output wire DISP_DATA, output wire BUZZER,
    output wire [5:0] LED_N
);
    wire clk = BOARD_CLK;
    reg [RSTW-1:0] rcnt = 0; wire rst = ~&rcnt;
    reg [1:0] key_q = 2'b00; always @(posedge clk) key_q <= {key_q[0], KEY_S1};
    always @(posedge clk) if (key_q[1]) rcnt <= 0; else if (rst) rcnt <= rcnt + 1'b1;
    reg [15:0] tc = 0; reg ms = 0; always @(posedge clk) begin if (tc == TICK - 1) begin tc <= 0; ms <= 1; end else begin tc <= tc + 1'b1; ms <= 0; end end

    // ---- the key (A1) debounced; A2 (clear) synchronised
    reg [1:0] q1 = 2'b11, q2 = 2'b11; always @(posedge clk) begin q1 <= {q1[0], BTN1_N}; q2 <= {q2[0], BTN2_N}; end
    reg d1 = 0, d1_q = 0; reg [7:0] dc = 0;
    always @(posedge clk) begin
        d1_q <= d1;
        if (ms) begin if (~q1[1] == d1) dc <= 0; else if (dc >= DEBMS - 1) begin d1 <= ~q1[1]; dc <= 0; end else dc <= dc + 1'b1; end
    end
    wire key_dn = d1 & ~d1_q, key_up = ~d1 & d1_q; wire clear = ~q2[1];

    // ---- lengths: plen counts while down, gap counts while up
    reg [11:0] plen = 0, gap = 0;
    always @(posedge clk) begin
        if (key_dn) plen <= 0; if (key_up) gap <= 0;
        if (ms) begin if (d1 && plen != 12'hFFF) plen <= plen + 1'b1; if (!d1 && gap != 12'hFFF) gap <= gap + 1'b1; end
    end
    function [3:0] logbin(input [11:0] v); integer k; begin logbin = 0; for (k = 0; k < 12; k = k + 1) if (v[k]) logbin = k; end endfunction

    // ---- scorer, fed by the ROM and then by the jobs
    localparam J_P = 0, J_L = 1, J_W = 2;
    reg [7:0] ra = 0; wire [31:0] rd; wire [7:0] last; reg loaded = 0, rom_v = 0; reg [31:0] live_w = 0; reg live_v = 0;
    hexn_morse_rom_v1 ROM (.addr(ra), .data(rd), .last(last));
    wire [31:0] in_data = loaded ? live_w : rd; wire in_valid = loaded ? live_v : rom_v; wire in_ack; wire [31:0] out_data; wire out_valid;
    hexn_scorer_v1 SC (.clk(clk), .rst(rst), .in_data(in_data), .in_valid(in_valid), .in_ack(in_ack), .out_data(out_data), .out_valid(out_valid), .out_ack(1'b1));
    function [31:0] jobword(input [1:0] job, input [3:0] b);
        jobword = {4'd0, 4'hF, 4'hF, 4'hF, 4'hF, (job == J_W) ? b : 4'hF, (job == J_L) ? b : 4'hF, (job == J_P) ? b : 4'hF};
    endfunction

    // ---- decoder state
    reg [2:0] slen = 0; reg [4:0] sbits = 0; reg lflag = 0, wflag = 0, armed = 0, preq = 0, last_dash = 0; reg [3:0] pbin = 0;
    reg [1:0] busy = 0; reg [1:0] job = 0;           // busy: 0 idle, 1 sending, 2 waiting for the result
    reg [5:0] c0 = 62, c1 = 62, c2 = 62, c3 = 62;     // the last four characters, c3 newest
    wire [5:0] dch; hexn_morse_dec_v1 DEC (.len(slen), .bits(sbits), .ch(dch));
    wire gap_eval = ms && armed && !d1 && !wflag && !preq;
    always @(posedge clk) begin
        if (rst) begin loaded <= 0; ra <= 0; rom_v <= 1; live_v <= 0; busy <= 0; slen <= 0; sbits <= 0; lflag <= 0; wflag <= 0; armed <= 0; preq <= 0; c0 <= 62; c1 <= 62; c2 <= 62; c3 <= 62; end
        else if (!loaded) begin if (in_ack) begin if (ra == last) begin rom_v <= 0; loaded <= 1; end else ra <= ra + 1'b1; end end
        else begin
            if (clear) begin c0 <= 62; c1 <= 62; c2 <= 62; c3 <= 62; slen <= 0; sbits <= 0; armed <= 0; lflag <= 0; wflag <= 0; end
            if (key_dn) begin lflag <= 0; wflag <= 0; end
            if (key_up) begin pbin <= logbin(plen); preq <= 1; armed <= 1; end
            if (live_v && in_ack) begin live_v <= 0; busy <= 2; end
            if (busy == 0) begin
                if (preq) begin live_w <= jobword(J_P, pbin); live_v <= 1; job <= J_P; busy <= 1; preq <= 0; end
                else if (gap_eval) begin job <= lflag ? J_W : J_L; live_w <= jobword(lflag ? J_W : J_L, logbin(gap)); live_v <= 1; busy <= 1; end
            end
            if (busy == 2 && out_valid) begin
                busy <= 0;
                case (job)
                    J_P: begin last_dash <= out_data[31]; if (slen < 6) begin slen <= slen + 1'b1; sbits <= {sbits[3:0], out_data[31]}; end end
                    J_L: if (out_data[31] && !d1) begin
                            lflag <= 1;
                            if (slen != 0) begin c0 <= c1; c1 <= c2; c2 <= c3; c3 <= dch; slen <= 0; sbits <= 0; end
                         end
                    default: if (out_data[31] && !d1) begin wflag <= 1; armed <= 0; if (c3 != 6'd62) begin c0 <= c1; c1 <= c2; c2 <= c3; c3 <= 6'd62; end end
                endcase
            end
        end
    end
    wire [7:0] g0, g1, g2, g3;
    hexn_glyph_v1 G0 (.ch(c0), .pend(1'b0), .seg(g0)); hexn_glyph_v1 G1 (.ch(c1), .pend(1'b0), .seg(g1)); hexn_glyph_v1 G2 (.ch(c2), .pend(1'b0), .seg(g2)); hexn_glyph_v1 G3 (.ch(c3), .pend(slen != 0), .seg(g3));
    hw262_shield_v2 SH (.clk(clk), .rst(rst), .enable(loaded), .segs({g0, g1, g2, g3}), .buzz(d1), .latch(DISP_LATCH), .sclk(DISP_CLK), .sdata(DISP_DATA), .buzzer(BUZZER));
    reg [24:0] hb = 0; always @(posedge clk) hb <= hb + 1'b1;
    assign LED_N = ~{loaded, wflag, lflag, last_dash, d1, hb[24]};
endmodule
`default_nettype wire
