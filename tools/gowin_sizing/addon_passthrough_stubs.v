// SCRATCH pass-through stand-ins for the addon chain: same ports, output = input. Measures each cell's CORE alone.
module invert_addon_v1 (input wire invert_en, input wire [31:0] data_in, output wire [31:0] data_out);
  assign data_out = data_in;
endmodule
module nibble_mask_addon_v1 (input wire mask_en, input wire [7:0] nibble_mask, input wire [31:0] data_in, output wire [31:0] data_out);
  assign data_out = data_in;
endmodule
module shift_lane_addon_v1 (input wire direction, input wire shift_en, input wire [4:0] shift_amt, input wire [2:0] lane_cut, input wire [31:0] data_in, output wire [31:0] data_out);
  assign data_out = data_in;
endmodule
module shift_fine_addon_v1 (input wire direction, input wire shift_en, input wire [1:0] shift_amount, input wire [31:0] data_in, output wire [31:0] data_out, output wire [1:0] shift_amount_out);
  assign data_out = data_in; assign shift_amount_out = shift_amount;
endmodule
