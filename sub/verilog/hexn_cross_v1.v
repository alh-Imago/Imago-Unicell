`default_nettype none
`timescale 1ns / 1ps
// hexn_cross_v1 -- the SERIAL <-> PARALLEL CROSSING between Hex-N (serial 32-bit words, LSB first, start flag on bit 0, 1 clock per hop) and the UniCell / sub side (a 32-bit word with a ONE-clock valid pulse), 3 Nov 2026, Alan 10:07.
// Two small modules, each with the general `clear` (wipe) input, composed with the EXISTING flex_to_sub_v1 / sub_to_flex_v1 handshake bridge (flex_sub_bridge_v1.v), not a new handshake.
//   hexn_p2s_v1 : parallel -> serial. A one-clock `valid` with `data` loads the word (accepted only when idle; `busy` is high from the clock after the load until the last bit has left). The serial pad shows bit 0 with flag 1 one clock after the
//                 valid clock (registered, +1), then bits 1..31 with flag 0. `done` pulses for one clock when bit 31 has been sent (wire it to flex_to_sub_v1.done). A valid that arrives while busy is IGNORED.
//   hexn_s2p_v1 : serial -> parallel. The flag marks bit 0; the 32 bits are shifted in; one clock after bit 31 was seen `valid` pulses for ONE clock with `data` (held until the next word). A new flag while a word is still arriving restarts the capture.
module hexn_p2s_v1 (input wire clk, input wire clear, input wire [31:0] data, input wire valid, output reg busy, output reg ds, output reg fs, output reg done);
    reg [31:0] sh; reg [4:0] cnt;
    always @(posedge clk) begin
        ds <= 1'b0; fs <= 1'b0; done <= 1'b0;
        if (clear) begin busy <= 1'b0; sh <= 32'd0; cnt <= 5'd0; end
        else if (!busy) begin
            if (valid) begin busy <= 1'b1; ds <= data[0]; fs <= 1'b1; sh <= {1'b0, data[31:1]}; cnt <= 5'd1; end         // bit 0 leaves in the load clock (visible one clock after `valid`)
        end else begin
            ds <= sh[0]; sh <= {1'b0, sh[31:1]}; cnt <= cnt + 5'd1;
            if (cnt == 5'd31) begin busy <= 1'b0; done <= 1'b1; end
        end
    end
    initial begin busy = 1'b0; ds = 1'b0; fs = 1'b0; done = 1'b0; sh = 32'd0; cnt = 5'd0; end
endmodule

module hexn_s2p_v1 (input wire clk, input wire clear, input wire ds, input wire fs, output reg [31:0] data, output reg valid);
    reg [31:0] sh; reg [4:0] cnt; reg act;
    always @(posedge clk) begin
        valid <= 1'b0;
        if (clear) begin act <= 1'b0; sh <= 32'd0; cnt <= 5'd0; data <= 32'd0; end
        else if (fs) begin                                  // bit 0
            sh <= 32'd0; sh[0] <= ds; cnt <= 5'd1; act <= 1'b1;
        end else if (act) begin
            sh[cnt] <= ds; cnt <= cnt + 5'd1;
            if (cnt == 5'd31) begin act <= 1'b0; data <= {ds, sh[30:0]}; valid <= 1'b1; end
        end
    end
    initial begin data = 32'd0; valid = 1'b0; sh = 32'd0; cnt = 5'd0; act = 1'b0; end
endmodule
