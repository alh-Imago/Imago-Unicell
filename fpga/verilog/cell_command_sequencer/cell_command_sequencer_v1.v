// cell_command_sequencer_v1.v — a real command-cell module matching
// the CURRENT program_in/prog_data_in_*/prog_arrived_in_*/program_done
// interface (points.md #390), unlike the two earlier, now-superseded
// command-cell candidates checked and ruled out in #392
// (cell_command_v1.v shares data through ordinary data_in ports;
// cell_cardinal_cmd_v1.v uses a full atomic cfg_valid/cfg_data reload
// -- neither matches the dedicated PROG_ID-word interface this file
// actually built and tested).
//
// The real, new capability #392 identified as missing: cycling through
// MULTIPLE cardinal_edge values over time (the collector cell's own
// real use case, points.md #381/#382 -- N, then S, then E, then back
// to N...), not applying one static value once. A compile-time-fixed
// sequence of up to 4 values, advanced by a real external trigger
// (matching #381/#382's own counter-driven advancement design), not
// self-timed -- the counter cell that watches data flow through the
// collector decides WHEN to advance, this module only knows HOW.
//
// Protocol, matching #390's own real, verified two-word sequence
// exactly: hold program_out high, send the PROG_ID_CARDINAL_EDGE word
// (pulsing prog_arrived_out for one cycle), then the PROG_ID_COMPLETE
// word (pulsing prog_arrived_out again), then release program_out.
// Sequence index auto-advances (wrapping) once program_done_in
// confirms the target actually completed -- not blindly assumed.

module cell_command_sequencer_v1 #(
    parameter [3:0] VALUE_0 = 4'b0000,
    parameter [3:0] VALUE_1 = 4'b0000,
    parameter [3:0] VALUE_2 = 4'b0000,
    parameter [3:0] VALUE_3 = 4'b0000,
    parameter [1:0] SEQUENCE_LEN = 2'd1   // how many of the 4 values are real (1-4)
)(
    input  wire        clk,
    input  wire        rst,

    input  wire        advance_trigger,   // pulse: start programming the NEXT value
    input  wire        program_done_in,   // from the target -- confirms completion

    output reg         program_out,
    output reg  [31:0] prog_data_out,
    output reg         prog_arrived_out,
    output reg  [1:0]  seq_index          // debug tap: which value is currently active
);

    localparam [2:0] PROG_ID_CARDINAL_EDGE = 3'd2;
    localparam [2:0] PROG_ID_COMPLETE      = 3'd7;

    localparam [1:0] S_IDLE         = 2'd0;
    localparam [1:0] S_SEND_FIELD   = 2'd1;
    localparam [1:0] S_SEND_COMPLETE= 2'd2;
    localparam [1:0] S_WAIT_DONE    = 2'd3;

    reg [1:0] state;

    function [3:0] value_for_index(input [1:0] idx);
        case (idx)
            2'd0: value_for_index = VALUE_0;
            2'd1: value_for_index = VALUE_1;
            2'd2: value_for_index = VALUE_2;
            default: value_for_index = VALUE_3;
        endcase
    endfunction

    always @(posedge clk) begin
        if (rst) begin
            state <= S_IDLE;
            seq_index <= 2'd0;
            program_out <= 1'b0;
            prog_arrived_out <= 1'b0;
            prog_data_out <= 32'h0;
        end else begin
            case (state)
                S_IDLE: begin
                    prog_arrived_out <= 1'b0;
                    if (advance_trigger) begin
                        program_out <= 1'b1;
                        prog_data_out <= {13'b0, PROG_ID_CARDINAL_EDGE, 12'b0, value_for_index(seq_index)};
                        prog_arrived_out <= 1'b1;
                        state <= S_SEND_FIELD;
                    end
                end
                S_SEND_FIELD: begin
                    // one-cycle pulse already sent -- move to the COMPLETE word
                    prog_data_out <= {13'b0, PROG_ID_COMPLETE, 15'b0, 1'b1};
                    prog_arrived_out <= 1'b1;
                    state <= S_SEND_COMPLETE;
                end
                S_SEND_COMPLETE: begin
                    prog_arrived_out <= 1'b0;
                    program_out <= 1'b0;
                    state <= S_WAIT_DONE;
                end
                S_WAIT_DONE: begin
                    if (program_done_in) begin
                        seq_index <= (seq_index == SEQUENCE_LEN - 1) ? 2'd0 : seq_index + 2'd1;
                        state <= S_IDLE;
                    end
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
