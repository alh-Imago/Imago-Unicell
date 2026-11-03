`default_nettype none
// hexn_rcore_flag_v3 = hexn_rcore_flag_v2 (untouched) (3 Nov 2026, Alan 09:50 'the general wipe command'): adds a CLEAR input - while clear is 1 every state register goes to its idle value (words in flight, FIFO 'have' flags, counters, carries, routed registers). Hold it for at least 130 clocks if the pattern has RAM hold cells (their delay line is wiped one address per clock). The config chain is NOT touched. 
// hexn_rcore_flag_v3 = hexn_rcore_flag_v1 (untouched) + POWER-UP ZEROES on the output registers (3 Nov 2026: unknown values circulate for ever round routes that feed each other; the same fix as hexn_tile_v2). Same ports, same logic, same size.
module hexn_rcore_flag_v3 #(parameter FACES = 4) (
    input wire clk, input wire clear, input wire [FACES-1:0] fi_d, input wire [FACES-1:0] fi_f,
    output reg [FACES-1:0] fo_d, output reg [FACES-1:0] fo_f,
    input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam CW = 3 * FACES;
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    initial begin fo_d = 0; fo_f = 0; end
    wire [7:0] dx = {{(8-FACES){1'b0}}, fi_d}; wire [7:0] fx = {{(8-FACES){1'b0}}, fi_f}; integer j;
    always @(posedge clk) for (j = 0; j < FACES; j = j + 1) begin fo_d[j] <= clear ? 1'b0 : dx[cfg[3 * j +: 3]]; fo_f[j] <= clear ? 1'b0 : fx[cfg[3 * j +: 3]]; end
endmodule
