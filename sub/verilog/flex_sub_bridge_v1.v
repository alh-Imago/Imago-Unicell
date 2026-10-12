// flex_sub_bridge_v1.v -- ledger #1112 (Alan, 12 Oct 2026): the HELD word at a sub block's measure point is the interface between the fixed-latency sub family (no ack, no flow control) and the
// handshake (flex) family. Two small modules, each a registered stage:
//   flex_to_sub_v1 : a flex word (valid/ack) is taken ONLY when the sub section is idle (one word in flight; a sub block cannot refuse or queue a word), acked in that same clock, and presented
//                    to the sub entry as a ONE-clock valid pulse with its data (registered: +1 clock).
//   sub_to_flex_v1 : the sub block's output pulse is CAUGHT and HELD (data + a level `held`); the level is the flex valid, the held data is what a flex cell compares / checks / stores, and the flex
//                    ack releases it and pulses `done`, which re-opens flex_to_sub_v1 for the next word. This register IS the measure point of #1111: the sub section can never push a second word into
//                    a holder that is still full, because no new word is admitted before `done`.
// Measured fixed cost of the crossing pair: see tests/vm/test_flex_sub_bridge_v1.py (ledger #1112).
`default_nettype none
`timescale 1ns / 1ps
module flex_to_sub_v1 #(parameter WIDTH = 32) (
    input  wire clk, input wire rst,
    input  wire [WIDTH-1:0] in_data, input wire in_valid, output wire in_ack,      // flex side (a flex cell's data_out / valid_out, ack_in)
    output reg  [WIDTH-1:0] sub_data, output reg sub_valid,                         // sub side: data + one-clock valid
    input  wire done                                                                // from sub_to_flex_v1: the previous word has left
);
    reg busy;
    assign in_ack = in_valid & ~busy & ~rst;
    always @(posedge clk) begin
        if (rst) begin busy <= 1'b0; sub_valid <= 1'b0; sub_data <= {WIDTH{1'b0}}; end
        else begin
            sub_valid <= in_ack;
            if (in_ack) begin sub_data <= in_data; busy <= 1'b1; end
            else if (done) busy <= 1'b0;
        end
    end
endmodule

module sub_to_flex_v1 #(parameter WIDTH = 32) (
    input  wire clk, input wire rst,
    input  wire [WIDTH-1:0] sub_data, input wire sub_valid,                          // sub side: a one-clock valid with the word (or the measure point's own valid)
    output wire [WIDTH-1:0] out_data, output wire out_valid, input wire out_ack,    // flex side: valid is a LEVEL while the word is held
    output wire done
);
    reg [WIDTH-1:0] held_data; reg held;
    assign out_data = held_data; assign out_valid = held;
    assign done = held & out_ack;
    always @(posedge clk) begin
        if (rst) begin held <= 1'b0; held_data <= {WIDTH{1'b0}}; end
        else if (sub_valid) begin held_data <= sub_data; held <= 1'b1; end
        else if (held & out_ack) held <= 1'b0;
    end
endmodule
