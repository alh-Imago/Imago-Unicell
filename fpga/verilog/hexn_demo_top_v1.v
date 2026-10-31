// hexn_demo_top_v1.v -- Hex-N (new file 1 Nov 2026): a REACTION GAME that runs on the Tang alone (no ESP32, no SPI, no SD card), on the HW-262 shield (three buttons, 4-digit display, buzzer).
// Round: all buttons up -> wait a random 1.0 to 3.0 s (display blank) -> a target 1, 2 or 3 appears (that LED lights, the display shows 000t) and a 1 ms counter starts -> press the matching button -> the
// counter stops (the TIME dimension: a free-running 1 ms tick from the 27 MHz clock) -> the reaction time becomes a layer-1 bin (floor(log2 ms), 0..11) and, with right/wrong-button, goes to the scorer
// (hexn_scorer_v1, table loaded from a ROM at power-up) -> display shows the time in ms as four decimal digits (a wrong button shows E and the first three digits), LED 4 lights and the buzzer beeps for a GOOD HIT
// (right button and under 256 ms with the starting table). Press any button to start the next round. Pressing before the target is ignored. No press within 9.999 s counts as a wrong button.
// LEDs (lit = true): 0 heartbeat, 1 / 2 / 3 target, 4 good hit, 5 table loaded. Tang S1 restarts the unit. Shield: A1 -> Tang 72, A2 -> 71, A3 -> 86 (a proposal; see docs/hex-n/DEMO_REACT_v1.md).
`default_nettype none
module hexn_demo_top_v1 #(
    parameter TICK = 27000,        // clock cycles per millisecond
    parameter DEBMS = 10,          // release must be stable this many ms
    parameter RSTW = 16
) (
    input  wire BOARD_CLK, input wire KEY_S1,
    input  wire BTN1_N, input wire BTN2_N, input wire BTN3_N,      // shield buttons A1, A2, A3 (low = pressed)
    output wire DISP_LATCH, output wire DISP_CLK, output wire DISP_DATA, output wire BUZZER,
    output wire [5:0] LED_N
);
    wire clk = BOARD_CLK;
    reg [RSTW-1:0] rcnt = 0; wire rst = ~&rcnt;
    reg [1:0] key_q = 2'b00; always @(posedge clk) key_q <= {key_q[0], KEY_S1};
    always @(posedge clk) if (key_q[1]) rcnt <= 0; else if (rst) rcnt <= rcnt + 1'b1;

    reg [15:0] tc = 0; reg ms = 0;                                             // 1 ms tick
    always @(posedge clk) begin if (tc == TICK - 1) begin tc <= 0; ms <= 1; end else begin tc <= tc + 1'b1; ms <= 0; end end

    // ---- buttons: sync; raw press edges (for timing); debounced level (for release)
    reg [1:0] q1 = 2'b11, q2 = 2'b11, q3 = 2'b11; reg [2:0] prev = 3'b111;
    always @(posedge clk) begin q1 <= {q1[0], BTN1_N}; q2 <= {q2[0], BTN2_N}; q3 <= {q3[0], BTN3_N}; prev <= {q3[1], q2[1], q1[1]}; end
    wire [2:0] raw = ~{q3[1], q2[1], q1[1]};                                   // 1 = down
    wire [2:0] press = prev & ~{q3[1], q2[1], q1[1]};                          // was up, now down
    reg any_dn = 0; reg [7:0] dc = 0;                                          // debounced 'some button is down'
    always @(posedge clk) if (ms) begin
        if ((|raw) == any_dn) dc <= 0; else if (dc >= DEBMS - 1) begin any_dn <= |raw; dc <= 0; end else dc <= dc + 1'b1;
    end

    // ---- random numbers: a 16-bit LFSR stepped every clock (the human's timing makes the seed)
    reg [15:0] lf = 16'hACE1; always @(posedge clk) lf <= {lf[14:0], lf[15] ^ lf[13] ^ lf[12] ^ lf[10]};

    // ---- the game
    localparam S_LOAD = 0, S_REL = 1, S_DELAY = 2, S_WAIT = 3, S_SCORE = 4, S_RESULT = 5;
    reg [2:0] st = S_LOAD; reg [11:0] dly = 0; reg [1:0] tgt = 1; reg right = 0; reg [3:0] n3 = 0, n2 = 0, n1 = 0, n0 = 0; reg [13:0] msv = 0;
    reg [7:0] ra = 0; wire [31:0] rd; reg rom_v = 0, live_v = 0; reg [31:0] live_w = 0; reg pred = 0; reg beep = 0; reg [7:0] beepc = 0;
    hexn_demo_rom_v1 ROM (.addr(ra), .data(rd));
    wire [31:0] in_data = (st == S_LOAD) ? rd : live_w; wire in_valid = (st == S_LOAD) ? rom_v : live_v; wire in_ack;
    wire [31:0] out_data; wire out_valid;
    hexn_scorer_v1 SC (.clk(clk), .rst(rst), .in_data(in_data), .in_valid(in_valid), .in_ack(in_ack), .out_data(out_data), .out_valid(out_valid), .out_ack(1'b1));
    function [3:0] logbin(input [13:0] v);
        integer k; reg [11:0] c; begin c = (v > 14'd4095) ? 12'hFFF : v[11:0]; logbin = 0; for (k = 0; k < 12; k = k + 1) if (c[k]) logbin = k; end
    endfunction
    always @(posedge clk) begin
        if (rst) begin st <= S_LOAD; ra <= 0; rom_v <= 1; live_v <= 0; pred <= 0; beep <= 0; dly <= 0; end
        else begin
            if (live_v && in_ack) live_v <= 0;
            case (st)
                S_LOAD: if (in_ack) begin if (ra == 8'd192) begin rom_v <= 0; st <= S_REL; end else ra <= ra + 1'b1; end
                S_REL:  if (!any_dn && !(|raw)) begin st <= S_DELAY; dly <= 12'd1000 + {1'b0, lf[10:0]} / 2 + {2'b0, lf[9:0]}; end   // about 1.0 to 3.0 s (random)
                S_DELAY: begin
                    if (ms) begin if (dly == 0) begin tgt <= (lf[7:0] % 3); st <= S_WAIT; msv <= 0; n3 <= 0; n2 <= 0; n1 <= 0; n0 <= 0; end else dly <= dly - 1'b1; end
                end
                S_WAIT: begin
                    if (|press) begin right <= ((press[0] ? 2'd0 : press[1] ? 2'd1 : 2'd2) == tgt); st <= S_SCORE; end
                    else if (ms) begin
                        if (msv == 14'd9999) begin right <= 0; st <= S_SCORE; end
                        else begin
                            msv <= msv + 1'b1;
                            if (n0 == 9) begin n0 <= 0; if (n1 == 9) begin n1 <= 0; if (n2 == 9) begin n2 <= 0; n3 <= n3 + 1'b1; end else n2 <= n2 + 1'b1; end else n1 <= n1 + 1'b1; end else n0 <= n0 + 1'b1;
                        end
                    end
                end
                S_SCORE: begin
                    live_w <= {20'h00000, 4'd0, 4'd0, logbin(msv), right ? 4'd11 : 4'd0}; live_v <= 1; st <= S_RESULT; pred <= 0; beep <= 0;
                end
                S_RESULT: begin
                    if (out_valid) begin pred <= out_data[31]; if (out_data[31]) begin beep <= 1; beepc <= 0; end end
                    if (beep && ms) begin if (beepc == 8'd200) beep <= 0; else beepc <= beepc + 1'b1; end
                    if (|press && !live_v) st <= S_REL;
                end
                default: st <= S_LOAD;
            endcase
        end
    end
    wire showing_t = (st == S_WAIT); wire blank = (st == S_LOAD) || (st == S_REL) || (st == S_DELAY) || (st == S_SCORE);
    wire [15:0] val2 = showing_t ? {12'h000, {2'b00, tgt} + 4'd1} : right ? {n3, n2, n1, n0} : {4'hE, n2, n1, n0};
    hw262_shield_v1 SH (.clk(clk), .rst(rst), .enable(!blank), .value(val2), .buzz(beep), .latch(DISP_LATCH), .sclk(DISP_CLK), .sdata(DISP_DATA), .buzzer(BUZZER));
    reg [24:0] hb = 0; always @(posedge clk) hb <= hb + 1'b1;
    wire [2:0] tled = showing_t ? (3'b001 << tgt) : 3'b000;
    assign LED_N = ~{(st != S_LOAD), (st == S_RESULT) & pred, tled, hb[24]};
endmodule
`default_nettype wire
