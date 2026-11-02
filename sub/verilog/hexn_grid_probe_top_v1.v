`default_nettype none
// hexn_grid_probe_top_v1 -- wrapper so the UCC v2 grid prototype can be placed and routed on its own for a TIMING reading (2 Nov 2026): the many inputs come from one shift register (serial in), the outputs go to one XOR flip-flop, so the pins do not decide anything.
module hexn_grid_probe_top_v1 #(parameter R = 4, parameter C = 4) (input wire clk, input wire sin, output wire sout);
    localparam NI = R * C * 6 + 1 + 16 + 7 + 1;
    reg [NI-1:0] sh = 0; always @(posedge clk) sh <= {sh[NI-2:0], sin};
    wire [R*C-1:0] o; reg x = 0; always @(posedge clk) x <= ^o; assign sout = x;
    hexn_grid_v1 #(.R(R), .C(C)) G (.clk(clk), .cfg_we(sh[0]), .cfg_cell(sh[16:1]), .cfg_addr(sh[23:17]), .cfg_data(sh[24]), .ext_in(sh[NI-1:25]), .o(o));
endmodule
