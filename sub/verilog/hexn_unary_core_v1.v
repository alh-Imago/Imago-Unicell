`default_nettype none
// hexn_unary_core_v1 -- the ONE-INPUT serial work cores (2 Nov 2026, Alan 09:19 and 09:35): no FIFO, no join, they read the stream off the link; af marks bit 0 of the word.
//   op 0 cp    : copy (one register).                      op 3 mask : keep nibble lanes: bit i is kept when mask[i/4] (8 lanes of 4 bits, as the UniCell mask cell).
//   op 1 shl k : shift left by k (0..31): delay line, zero fill.   op 4 inv  : bitwise NOT of the 32-bit word.
//   op 2 shr k : shift right by k: the result starts k clocks later (bit j = input bit j+k), zero fill at the top.
//   op 5 acc   : running total: result = input + total, total = result (32-bit ring); 'clear' (pulse) sets the total to 0.
//   rs marks bit 0 of the result word. Function-tested by tests/hexn_unary_core_v1_tb.v.
module hexn_unary_core_v1 (input wire clk, input wire [2:0] op, input wire [4:0] k, input wire [7:0] mask, input wire clear, input wire a, input wire af, output reg r, output reg rs);
    reg [5:0] cnt = 6'd63; wire [5:0] cc = af ? 6'd0 : cnt;
    reg [31:0] sr = 0; reg [31:0] ring = 0; reg c = 1'b0;
    wire win = (cc < 6'd32);
    wire sumb = a ^ ring[0] ^ (af ? 1'b0 : c);
    wire cn = (a & ring[0]) | (a & (af ? 1'b0 : c)) | (ring[0] & (af ? 1'b0 : c));
    wire shl_b = (k == 0) ? a : sr[k - 1];
    always @(posedge clk) begin
        if (cc != 6'd63) cnt <= cc + 1'b1; else cnt <= cc;
        sr <= {sr[30:0], a};
        rs <= 1'b0; r <= 1'b0;
        if (clear) begin ring <= 32'd0; c <= 1'b0; end
        case (op)
            3'd0: begin r <= a; rs <= af; end
            3'd1: begin r <= win ? shl_b : 1'b0; rs <= (cc == 6'd0) && (cnt != 6'd63 || af); end
            3'd2: begin r <= (cc >= {1'b0, k} && cc < 6'd32) ? a : 1'b0; rs <= (cc == {1'b0, k}) && (cnt != 6'd63 || af); end
            3'd3: begin r <= win ? (a & mask[cc[4:2]]) : 1'b0; rs <= af; end
            3'd4: begin r <= win ? ~a : 1'b0; rs <= af; end
            default: if (win && (cnt != 6'd63 || af)) begin r <= sumb; ring <= {sumb, ring[31:1]}; c <= cn; rs <= (cc == 6'd0); end
        endcase
    end
    initial begin r = 1'b0; rs = 1'b0; end
endmodule
