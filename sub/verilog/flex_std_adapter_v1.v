// flex_std_adapter_v1.v -- ledger #1160: the handshake adapters between the FLEX family (valid level + ack) and the STANDARD / CARRIER family (v4 / v4c faces: arrived pulse in, fire level + ack_in out,
// ready_out). Both are pure wiring, no state, no extra clock: the same wiring that tb_std_sub_bridge_v1.v used at its ends (#1113), now as named modules.
//   flex_to_std_v1 : a flex cell's data_out / valid_out / ack_in  ->  a std cell's data_in_<face> / arrived_<face>. The std cell is ready (ready_out) when it can take a word; the word moves in the clock where
//                    the flex valid and the std ready are both high: arrived is that one-clock pulse, and the same ready is the flex ack, so the flex cell clears in the clock the std cell takes it.
//   std_to_flex_v1 : a std cell's data_out_<face> / fire_<face> / ack_in_<face>  ->  a flex cell's data_in / valid_in / ack_out. fire is a level while the std cell offers the word; the flex ack is
//                    returned as a one-clock std ack_in pulse (fire & flex ack: the clock the flex cell takes the word), so the std cell drops fire after.
// Neither adapter holds a word: a std cell that has been given a word and a flex cell that has accepted one each hold it themselves. One face per adapter; 32 bits by default.
`timescale 1ns/1ps
module flex_to_std_v1 #(parameter WIDTH = 32) (
    input  wire [WIDTH-1:0] flex_data, input wire flex_valid, output wire flex_ack,
    input  wire             std_ready,
    output wire [WIDTH-1:0] std_data,  output wire std_arrived
);
    assign std_data    = flex_data;
    assign std_arrived = flex_valid & std_ready;
    assign flex_ack    = std_ready;
endmodule

module std_to_flex_v1 #(parameter WIDTH = 32) (
    input  wire [WIDTH-1:0] std_data, input wire std_fire, output wire std_ack,
    input  wire             flex_ack,
    output wire [WIDTH-1:0] flex_data, output wire flex_valid
);
    assign flex_data  = std_data;
    assign flex_valid = std_fire;
    assign std_ack    = std_fire & flex_ack;      // a ONE-CLOCK pulse in the clock the flex cell takes the word (a std cell reads ack_in as an event; held high it never fires)
endmodule
