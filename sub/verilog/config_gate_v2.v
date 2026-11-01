`default_nettype none
`timescale 1ns / 1ps
// config_gate_v2 = config_gate_v1 plus a WATCHDOG: busy for more than WATCHDOG clocks (a word that never gets its result taken) sets the sticky output `fault` until reset.
// (1 Nov 2026; v1 left as it was.) Original header: config_gate_v1: a flex_to_sub_v1 bridge with a "closed" input and a small
// sequencer, so a region of sub/flex cells can be reconfigured while the
// design runs without losing or corrupting a word.
// Specification: Project doc claude/config-gate-spec.md (draft 1, 1 Nov 2026).
// New file; flex_sub_bridge_v1.v is untouched.
//
// Flex side in: in_data / in_valid (LEVEL, held by the producer until acked) / in_ack.
// Region side out: region_data / region_valid (one-clock pulse), as flex_to_sub_v1.
// done: from sub_to_flex_v1, the previous result has been taken.
// cfg_req: one-clock pulse; cfg_word_in is sampled on that clock.
// cfg_valid / cfg_data: the region's config port, driven ONLY by this gate.
// cfg_done: one-clock pulse when the gate is open again (also after a timeout,
//           in which case cfg_err[0] is set and the OLD config is kept).
// cfg_err[0] drain timeout, cfg_err[1] a request arrived while busy (ignored).
//          Both clear when the next request is accepted.
module config_gate_v2 #(
    parameter WIDTH         = 32,
    parameter CFG_W         = 32,
    parameter SETTLE        = 1,     // clocks closed after the config clock
    parameter DRAIN_TIMEOUT = 64,    // clocks to wait for done
    parameter WATCHDOG      = 200    // clocks busy before `fault` (must be below 256)
) (
    input  wire clk, input wire rst,
    input  wire [WIDTH-1:0] in_data, input wire in_valid, output wire in_ack,
    output reg  [WIDTH-1:0] region_data, output reg region_valid,
    input  wire done,
    input  wire cfg_req, input wire [CFG_W-1:0] cfg_word_in,
    output wire cfg_valid, output wire [CFG_W-1:0] cfg_data,
    output wire cfg_busy, output reg cfg_done, output reg [1:0] cfg_err,
    output reg fault
);
    localparam OPEN = 2'd0, CLOSING = 2'd1, PROGRAM = 2'd2, SETTLING = 2'd3;
    reg [1:0] state;
    reg busy;                          // one word in flight, as the bridge
    reg [CFG_W-1:0] cfg_hold;
    reg [15:0] cnt;
    reg [7:0] wd;

    // closed in the SAME clock as an accepted request: no word is admitted on it
    wire req_ok  = cfg_req && (state == OPEN);
    wire closed  = req_ok || (state != OPEN);
    assign in_ack    = in_valid & ~busy & ~closed & ~rst;
    assign cfg_valid = (state == PROGRAM);
    assign cfg_data  = cfg_hold;
    assign cfg_busy  = (state != OPEN);

    always @(posedge clk) begin
        if (rst) begin
            state <= OPEN; busy <= 1'b0; region_valid <= 1'b0; region_data <= {WIDTH{1'b0}};
            cfg_hold <= {CFG_W{1'b0}}; cnt <= 16'd0; cfg_done <= 1'b0; cfg_err <= 2'b00; wd <= 8'd0; fault <= 1'b0;
        end else begin
            region_valid <= in_ack;
            cfg_done     <= 1'b0;
            if (in_ack) begin region_data <= in_data; busy <= 1'b1; end
            else if (done) busy <= 1'b0;

            if (!busy || done) wd <= 8'd0; else if (wd != 8'd255) wd <= wd + 8'd1;
            if (busy && !done && wd >= WATCHDOG) fault <= 1'b1;
            if (cfg_req && state != OPEN) cfg_err[1] <= 1'b1;   // rejected, not queued

            case (state)
                OPEN: if (cfg_req) begin
                    cfg_hold <= cfg_word_in; cfg_err <= 2'b00; cnt <= 16'd0;
                    state <= CLOSING;
                end
                CLOSING: begin
                    if (!busy || done) begin state <= PROGRAM; end
                    else if (cnt >= DRAIN_TIMEOUT) begin
                        cfg_err[0] <= 1'b1; cfg_done <= 1'b1; state <= OPEN;
                    end
                    cnt <= cnt + 16'd1;
                end
                PROGRAM: begin
                    cnt <= 16'd1;
                    if (SETTLE == 0) begin cfg_done <= 1'b1; state <= OPEN; end
                    else state <= SETTLING;
                end
                SETTLING: begin
                    if (cnt >= SETTLE) begin cfg_done <= 1'b1; state <= OPEN; end
                    cnt <= cnt + 16'd1;
                end
            endcase
        end
    end
endmodule
