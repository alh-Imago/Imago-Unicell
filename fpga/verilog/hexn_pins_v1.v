// hexn_pins_v1.v -- Hex-N open unit stage 3: THE PIN MATRIX (new file 1 Nov 2026). A POOL of 16 Tang pins, each a bidirectional pad (internal pull-up), and a routing the ESP32 sets at run time:
//   * 3 logical INPUTS (button 1, 2, 3 of the personalities): each picks one pool pin, 4-bit selector.
//   * 4 logical OUTPUTS (display latch, display clock, display data, buzzer): each picks one pool pin; that pin then drives the signal, every other pool pin stays an input.
// Selectors are stored XOR the default index, so a register value of 0 means the DEFAULT wiring (the pins of docs/hex-n/DEMO_REACT_v1.md): pool index 0..6 = Tang pins 72, 71, 86, 25, 26, 27, 28 = BTN1, BTN2, BTN3, LATCH, CLK, DATA, BUZZER.
// Pool index 7..15 = Tang pins 29, 30, 31, 85, 80, 42, 41, 56, 54 (all free in the pinout). Two outputs picking the same pin: the lower-numbered output drives it (latch, clk, data, buzzer in that order). `levels` is the live level of all 16 pins (also readable by the ESP32, see the top).
// SAFETY: picking a pin that is wired to something else that drives it makes two drivers fight; the default routing never does that. Only route outputs to pins you have wired to an input.
`default_nettype none
module hexn_pins_v1 (
    inout  wire [15:0] pool,
    input  wire [11:0] in_sel,          // {btn3, btn2, btn1}, 4 bits each, XOR default
    input  wire [15:0] out_sel,         // {buzzer, data, clk, latch}, 4 bits each, XOR default
    output wire [2:0]  in_val,          // button 1..3 as seen on their selected pins (active-low buttons keep their meaning)
    input  wire [3:0]  out_val,         // {buzzer, data, clk, latch}
    output wire [15:0] levels
);
    wire [3:0] bsel1 = in_sel[3:0] ^ 4'd0, bsel2 = in_sel[7:4] ^ 4'd1, bsel3 = in_sel[11:8] ^ 4'd2;
    wire [3:0] osel_l = out_sel[3:0] ^ 4'd3, osel_c = out_sel[7:4] ^ 4'd4, osel_d = out_sel[11:8] ^ 4'd5, osel_b = out_sel[15:12] ^ 4'd6;
    wire [15:0] pad = pool;
    assign levels = pad;
    assign in_val = {pad[bsel3], pad[bsel2], pad[bsel1]};
    genvar g;
    generate for (g = 0; g < 16; g = g + 1) begin : P
        wire d_l = (osel_l == g), d_c = (osel_c == g), d_d = (osel_d == g), d_b = (osel_b == g);
        wire oe = d_l | d_c | d_d | d_b;
        wire v = d_l ? out_val[0] : d_c ? out_val[1] : d_d ? out_val[2] : out_val[3];
        assign pool[g] = oe ? v : 1'bz;
    end endgenerate
endmodule
`default_nettype wire
