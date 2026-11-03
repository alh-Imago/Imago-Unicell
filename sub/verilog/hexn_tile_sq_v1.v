`default_nettype none
// hexn_tile_sq_v1 -- a HEX-N TILE WITH THE SEQUENCER CORE hexn_seq_core_v2 (3 Nov 2026, Alan 10:07): routing cell with flag lane + the serial sequencer. The ADVANCE input is the FLAG lane of face SEL (the start flag of a word arriving there is the rising edge); the data of that word is not used.
// ONE output (the next stored value) to the faces in RMASK. CONFIG CHAIN word, LSB = bit 0, width 3*FACES + 3 + FACES + 3 + 128 (150 at four faces): ROUTE 3 bits per output | SEL 3 | RMASK FACES | LEN 3 | VALS 128 (four 32-bit values, value 0 in the low bits).
module hexn_tile_sq_v1 #(parameter FACES = 4) (
    input wire clk, input wire clear,
    input wire [FACES-1:0] fi_d, input wire [FACES-1:0] fi_f,
    output wire [FACES-1:0] fo_d, output wire [FACES-1:0] fo_f,
    input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam RW = 3 * FACES;
    localparam CW = RW + 3 + FACES + 3 + 128;
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    wire [2:0] sel = cfg[RW +: 3];
    wire [FACES-1:0] rmask = cfg[RW + 3 +: FACES];
    wire [2:0] len = cfg[RW + 3 + FACES +: 3];
    wire [127:0] vals = cfg[RW + 6 + FACES +: 128];
    wire [7:0] dx = {{(8-FACES){1'b0}}, fi_d}; wire [7:0] fx = {{(8-FACES){1'b0}}, fi_f};
    wire r, rs;
    hexn_seq_core_v2 core (.clk(clk), .clear(clear), .cfgload(cfg_en | clear), .vals(vals), .len(len), .adv(fx[sel]), .r(r), .rs(rs));
    reg [FACES-1:0] ro_d = 0, ro_f = 0; integer j;
    always @(posedge clk) for (j = 0; j < FACES; j = j + 1) begin
        ro_d[j] <= clear ? 1'b0 : dx[cfg[3 * j +: 3]];
        ro_f[j] <= clear ? 1'b0 : fx[cfg[3 * j +: 3]];
    end
    genvar g;
    generate for (g = 0; g < FACES; g = g + 1) begin : o
        assign fo_d[g] = rmask[g] ? r  : ro_d[g];
        assign fo_f[g] = rmask[g] ? rs : ro_f[g];
    end endgenerate
endmodule
