`default_nettype none
// hexn_ramhold_v1 -- the RAM ROUTING CELL at four faces with the flag lane (3 Nov 2026, Alan 09:50 'apply the ram side'): a routing cell (hexn_rcore_flag_v2's route table) in which ONE output can be HELD, i.e. its stream (data bit AND start flag
// together, so the marker rides with the bit as the planner assumes) is delayed by DLY more clocks than the normal one-clock hop. This is exactly the planner's hold (hexn_wrgrid_v18: a deque of h on the wire (cell, out)), h = 2..96; the delay line is a
// 128 x 2-bit circular memory. No word logic: it works on any stream, including several words and flags in flight.
// CONFIG CHAIN word, LSB = bit 0 (shifted in MSB first, farthest first), 22 bits at four faces: ROUTE 3 bits per output [3*j +: 3] (FACES or more reads 0) | HOUT 3 (the held output face; 7 = no hold) | DLY 7.
// clear = 1 forces every register and writes zeros into the memory at the running address, so holding clear for at least 128 clocks wipes the whole delay line (the general wipe uses this).
module hexn_ramhold_v1 #(parameter FACES = 4) (
    input wire clk, input wire clear,
    input wire [FACES-1:0] fi_d, input wire [FACES-1:0] fi_f,
    output wire [FACES-1:0] fo_d, output wire [FACES-1:0] fo_f,
    input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam RW = 3 * FACES;
    localparam CW = RW + 3 + 7;
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    wire [2:0] hout = cfg[RW +: 3];
    wire [6:0] dly = cfg[RW + 3 +: 7];
    wire [7:0] dx = {{(8-FACES){1'b0}}, fi_d}; wire [7:0] fx = {{(8-FACES){1'b0}}, fi_f};
    reg [FACES-1:0] ro_d = 0, ro_f = 0; integer j;
    always @(posedge clk) for (j = 0; j < FACES; j = j + 1) begin
        ro_d[j] <= clear ? 1'b0 : dx[cfg[3 * j +: 3]];
        ro_f[j] <= clear ? 1'b0 : fx[cfg[3 * j +: 3]];
    end
    wire [7:0] ox = {{(8-FACES){1'b0}}, ro_d}; wire [7:0] ofx = {{(8-FACES){1'b0}}, ro_f};
    wire xd = ox[hout], xf = ofx[hout];                       // the routed value of the held output, one clock after the inputs
    reg [1:0] mem [0:127]; reg [6:0] wp = 7'd0; reg hd = 1'b0, hf = 1'b0;
    wire [6:0] ra = wp - (dly - 7'd1);                         // dly >= 2 so the read never meets the address being written
    integer k; initial begin for (k = 0; k < 128; k = k + 1) mem[k] = 2'b00; end
    always @(posedge clk) begin
        mem[wp] <= clear ? 2'b00 : {xd, xf}; wp <= wp + 7'd1;
        {hd, hf} <= clear ? 2'b00 : mem[ra];
    end
    genvar g;
    generate for (g = 0; g < FACES; g = g + 1) begin : o
        assign fo_d[g] = (hout == g) ? hd : ro_d[g];
        assign fo_f[g] = (hout == g) ? hf : ro_f[g];
    end endgenerate
endmodule
