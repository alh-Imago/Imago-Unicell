`default_nettype none
`timescale 1ns / 1ps
// join_v1: the TWO-ARRIVAL front stage (1 Nov 2026, Alan 05:26 and 05:38). Operands A and B arrive separately, each on a flex hand-off (valid LEVEL held until acked).
// The unit holds the first operand and fires when the second has arrived: the output is one flex hand-off carrying {A, B}, ready to feed config_gate_v3 (in_data = {A, B}).
// STICKY_B = 0: pair mode. Each A pairs with the next B; both slots are cleared when the pair is taken.
// STICKY_B = 1: the nano-cell behaviour. B is a HELD value (like load_hold): it stays after use and fires with EVERY later A, until a new B replaces it.
//               (A new B is accepted only while no pair is waiting to be taken, so a pair never changes under the consumer.)
// A and B are 32-bit. out_valid is a level and out_data is stable until out_ack. Reset clears both slots.
module join_v1 #(parameter STICKY_B = 0) (
    input  wire clk, input wire rst,
    input  wire [31:0] a_data, input wire a_valid, output wire a_ack,
    input  wire [31:0] b_data, input wire b_valid, output wire b_ack,
    output wire [63:0] out_data, output wire out_valid, input wire out_ack
);
    reg [31:0] ra, rb; reg have_a, have_b;
    assign out_valid = have_a & have_b;
    assign out_data  = {ra, rb};
    assign a_ack = a_valid & ~have_a & ~rst;
    assign b_ack = b_valid & ~rst & (STICKY_B ? ~out_valid : ~have_b);
    always @(posedge clk) begin
        if (rst) begin have_a <= 1'b0; have_b <= 1'b0; ra <= 32'h0; rb <= 32'h0; end
        else begin
            if (a_ack) begin ra <= a_data; have_a <= 1'b1; end
            if (b_ack) begin rb <= b_data; have_b <= 1'b1; end
            if (out_valid & out_ack) begin have_a <= 1'b0; if (!STICKY_B) have_b <= 1'b0; end
        end
    end
endmodule
