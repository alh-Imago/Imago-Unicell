`default_nettype none
// hexn_ramroute_probe_v1 -- MEASUREMENT PROTOTYPE (2 Nov 2026, Alan 07:35): the routing core with the UniCell RAM cell modes added, one per routing position (1 to 1).
//   Six faces in, six registered faces out (as hexn_rcore_v1). One memory of DEPTH bits and three modes:
//   mode 0 PASS   : plain routing (the memory is idle).
//   mode 1 HOLD   : the stream picked by hsel is written into a circular memory and read back dly clocks later onto face hout (a stored delay of 1..DEPTH-1 clocks); the other faces still route.
//   mode 2 REPEAT : the first len bits of the stream are recorded, then replayed over and over onto face hout.
//   NOT function-tested: counts only (yosys 0.69, -nowidelut). 'Hold until requested' as a request signal is not included; here the release time is the delay.
module hexn_ramroute_probe_v1 #(parameter DEPTH = 64, parameter AW = 6) (input wire clk, input wire [5:0] fi, output reg [5:0] fo, input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam CW = 18 + 2 + 3 + 3 + AW + AW;
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    wire [1:0] mode = cfg[19:18]; wire [2:0] hsel = cfg[22:20]; wire [2:0] hout = cfg[25:23];
    wire [AW-1:0] dly = cfg[25+AW:26]; wire [AW-1:0] len = cfg[25+2*AW:26+AW];
    wire [7:0] fx = {2'b00, fi}; wire din = fx[hsel];
    reg mem [0:DEPTH-1]; reg [AW-1:0] wp = 0, rp = 0; reg q = 1'b0; reg rec = 1'b1;
    always @(posedge clk) begin
        if (mode == 2'd1) begin mem[wp] <= din; wp <= wp + 1'b1; rp <= wp - dly; q <= mem[rp]; end
        else if (mode == 2'd2) begin
            if (rec) begin mem[wp] <= din; wp <= wp + 1'b1; if (wp == len - 1'b1) begin rec <= 1'b0; rp <= 0; end end
            else begin q <= mem[rp]; rp <= (rp == len - 1'b1) ? {AW{1'b0}} : rp + 1'b1; end
        end else begin wp <= 0; rp <= 0; rec <= 1'b1; end
    end
    integer j;
    always @(posedge clk) for (j = 0; j < 6; j = j + 1) fo[j] <= (mode != 2'd0 && hout == j) ? q : fx[cfg[3 * j +: 3]];
endmodule
