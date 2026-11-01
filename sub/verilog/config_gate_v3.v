`default_nettype none
`timescale 1ns / 1ps
// config_gate_v3 = config_gate_v2 plus the FAULT POLICY of Project doc claude/config-gate-fault-policy.md (1 Nov 2026). v1, v2 untouched.
// A cell fault = bridge busy for WATCHDOG clocks with NO result in the output hold (res_valid = 0).
//   - result present but not taken (res_valid = 1): not a cell fault, only the level `blocked`.
//   - fault: up to MAX_RETRY consecutive times: close, pulse region_rst (RST_CLOCKS clocks), count 1 LOST word, replay the last accepted config, reopen.
//   - retries are forgiven after GOOD_WORDS completed words.
//   - retries used up: DEAD (sticky) -- door stays closed, counters kept, only rst clears it.
// Outputs for the host / a judge: fault (sticky), dead (sticky), blocked (level), resets[7:0], lost[7:0].
// region_rst must be OR-ed into the region's AND the output hold's reset by the caller.
module config_gate_v3 #(
    parameter WIDTH         = 32,
    parameter CFG_W         = 32,
    parameter SETTLE        = 1,
    parameter DRAIN_TIMEOUT = 64,
    parameter WATCHDOG      = 100,   // below 256
    parameter MAX_RETRY     = 2,
    parameter GOOD_WORDS    = 16,
    parameter RST_CLOCKS    = 2
) (
    input  wire clk, input wire rst,
    input  wire [WIDTH-1:0] in_data, input wire in_valid, output wire in_ack,
    output reg  [WIDTH-1:0] region_data, output reg region_valid,
    input  wire done, input wire res_valid,
    input  wire cfg_req, input wire [CFG_W-1:0] cfg_word_in,
    output wire cfg_valid, output wire [CFG_W-1:0] cfg_data,
    output wire cfg_busy, output reg cfg_done, output reg [1:0] cfg_err,
    output wire region_rst,
    output reg fault, output reg dead, output wire blocked,
    output reg [7:0] resets, output reg [7:0] lost
);
    localparam OPEN = 3'd0, CLOSING = 3'd1, PROGRAM = 3'd2, SETTLING = 3'd3, REC_RST = 3'd4, REC_CFG = 3'd5, DEAD = 3'd6;
    reg [2:0] state;
    reg busy;
    reg [CFG_W-1:0] cfg_hold; reg have_cfg;
    reg [15:0] cnt;
    reg [7:0] wd;
    reg [7:0] retry; reg [7:0] good;

    wire req_ok = cfg_req && (state == OPEN);
    wire closed = req_ok || (state != OPEN);
    assign in_ack     = in_valid & ~busy & ~closed & ~rst;
    assign cfg_valid  = (state == PROGRAM) || (state == REC_CFG);
    assign cfg_data   = cfg_hold;
    assign cfg_busy   = (state != OPEN);
    assign region_rst = (state == REC_RST);
    assign blocked    = busy && res_valid && (wd >= WATCHDOG);
    wire fault_event  = ((state == OPEN) || (state == CLOSING)) && busy && !done && !res_valid && (wd >= WATCHDOG);

    always @(posedge clk) begin
        if (rst) begin
            state <= OPEN; busy <= 1'b0; region_valid <= 1'b0; region_data <= {WIDTH{1'b0}};
            cfg_hold <= {CFG_W{1'b0}}; have_cfg <= 1'b0; cnt <= 16'd0; cfg_done <= 1'b0; cfg_err <= 2'b00; wd <= 8'd0;
            fault <= 1'b0; dead <= 1'b0; resets <= 8'd0; lost <= 8'd0; retry <= 8'd0; good <= 8'd0;
        end else begin
            region_valid <= in_ack;
            cfg_done     <= 1'b0;
            if (in_ack) begin region_data <= in_data; busy <= 1'b1; end
            else if (done) busy <= 1'b0;

            if (!busy || done) wd <= 8'd0; else if (wd != 8'd255) wd <= wd + 8'd1;
            if (done && state == OPEN) begin
                if (good >= GOOD_WORDS - 1) begin retry <= 8'd0; good <= 8'd0; end else good <= good + 8'd1;
            end
            if (cfg_req && state != OPEN) cfg_err[1] <= 1'b1;

            if (fault_event) begin
                fault <= 1'b1; good <= 8'd0; cnt <= 16'd0;
                if (retry < MAX_RETRY) begin
                    state <= REC_RST; retry <= retry + 8'd1; resets <= resets + 8'd1; lost <= lost + 8'd1;
                end else begin
                    state <= DEAD; dead <= 1'b1; lost <= lost + 8'd1;
                end
            end else case (state)
                OPEN: if (cfg_req) begin
                    cfg_hold <= cfg_word_in; have_cfg <= 1'b1; cfg_err <= 2'b00; cnt <= 16'd0;
                    state <= CLOSING;
                end
                CLOSING: begin
                    if (!busy || done) state <= PROGRAM;
                    else if (cnt >= DRAIN_TIMEOUT) begin cfg_err[0] <= 1'b1; cfg_done <= 1'b1; state <= OPEN; end
                    cnt <= cnt + 16'd1;
                end
                PROGRAM: begin
                    cnt <= 16'd1;
                    if (SETTLE == 0) begin cfg_done <= 1'b1; state <= OPEN; end else state <= SETTLING;
                end
                SETTLING: begin
                    if (cnt >= SETTLE) begin cfg_done <= 1'b1; state <= OPEN; end
                    cnt <= cnt + 16'd1;
                end
                REC_RST: begin
                    busy <= 1'b0; wd <= 8'd0; region_valid <= 1'b0;
                    cnt <= cnt + 16'd1;
                    if (cnt + 16'd1 >= RST_CLOCKS) begin
                        cnt <= 16'd1;
                        if (have_cfg) state <= REC_CFG; else state <= OPEN;
                    end
                end
                REC_CFG: begin cnt <= 16'd1; state <= (SETTLE == 0) ? OPEN : SETTLING; cfg_done <= (SETTLE == 0); end
                default: ;   // DEAD: stays until rst
            endcase
        end
    end
endmodule
