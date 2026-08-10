// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_bram_controller_test_v1.v — points.md #259/#260 continuation:
// FIRST REAL-SILICON SIZE/TIMING/INFERENCE CHECK for bram_controller_v1.v
// at its real 40-bit width. NOT YET BUILT — prepared project.
//
// A single bram_controller_v1 instance (ADDR_WIDTH=16, DATA_WIDTH=40 —
// 64K x 40 = 2,621,440 bits, roughly 128 M20K blocks worth), driven by
// a small free-running self-test FSM: writes a genuinely varying
// pattern (not constant, same reasoning as every other stimulus in this
// project — avoids Quartus optimizing anything away) to a rolling
// window of addresses, reads them back, and sticky-latches an error LED
// if any mismatch is ever seen. Confirms real M20K inference (watch
// "Total block memory bits" in the fit report — should be nonzero and
// roughly track 2,621,440 bits, not 0) and gives a real ALM/Fmax number
// for the controller alone, decoupled from any cell-shell overhead.
`default_nettype none
`timescale 1ns / 1ps

module top_bram_controller_test_v1 (
    input  wire CLK_100M,   // 100 MHz board ref, PIN_E23
    output wire LED0_N,     // heartbeat: self-test actively running
    output wire LED1_N      // sticky error — should NEVER light if this build is correct
);

// ── Clock/reset — same convention as every other project here ──────────
reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk = div_cnt[1];   // 25 MHz

reg [3:0] rst_sr = 4'hF;
always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

localparam OP_READ = 1'b0, OP_WRITE = 1'b1;
localparam ADDR_WIDTH = 16;
localparam WINDOW     = 16'd64;   // rolling window of addresses exercised

reg         cmd_valid = 0;
reg         cmd_op    = 0;
reg  [15:0] cmd_addr  = 0;
reg  [39:0] cmd_wdata = 0;

wire        rdata_valid;
wire [39:0] rdata;
wire        write_done;

bram_controller_v1 #(.ADDR_WIDTH(ADDR_WIDTH), .DATA_WIDTH(40)) DUT (
    .clk(clk), .rst(rst),
    .cmd_valid(cmd_valid), .cmd_op(cmd_op), .cmd_addr(cmd_addr), .cmd_wdata(cmd_wdata),
    .rdata_valid(rdata_valid), .rdata(rdata), .write_done(write_done)
);

// ── Self-test FSM: WRITE a varying pattern across WINDOW addresses,
// then READ each back and check. Loops forever, re-seeding with a new
// pattern each pass (free-running counter folded in) so the values
// genuinely change over time, not a static constant. ──
reg [2:0]  state = 0;
localparam S_WRITE = 0, S_WRITE_WAIT = 1, S_READ = 2, S_READ_WAIT = 3, S_CHECK = 4, S_NEXT = 5;

reg [15:0] idx        = 0;
reg [31:0] pass_seed  = 0;
reg        err_sticky = 0;
reg [23:0] heartbeat   = 0;

wire [39:0] expected_word = {idx[7:0] ^ pass_seed[7:0], pass_seed ^ {16'h0, idx}};

always @(posedge clk) begin
    cmd_valid <= 1'b0;
    heartbeat <= heartbeat + 24'h1;
    if (rst) begin
        state      <= S_WRITE;
        idx        <= 16'h0;
        pass_seed  <= 32'hA5A5_5A5A;
        err_sticky <= 1'b0;
    end else begin
        case (state)
            S_WRITE: begin
                cmd_valid <= 1'b1;
                cmd_op    <= OP_WRITE;
                cmd_addr  <= idx;
                cmd_wdata <= expected_word;
                state     <= S_WRITE_WAIT;
            end
            S_WRITE_WAIT: begin
                if (write_done) begin
                    if (idx == WINDOW - 1) begin
                        idx   <= 16'h0;
                        state <= S_READ;
                    end else begin
                        idx   <= idx + 16'h1;
                        state <= S_WRITE;
                    end
                end
            end
            S_READ: begin
                cmd_valid <= 1'b1;
                cmd_op    <= OP_READ;
                cmd_addr  <= idx;
                state     <= S_READ_WAIT;
            end
            S_READ_WAIT: begin
                if (rdata_valid) state <= S_CHECK;
            end
            S_CHECK: begin
                if (rdata !== expected_word) err_sticky <= 1'b1;
                state <= S_NEXT;
            end
            S_NEXT: begin
                if (idx == WINDOW - 1) begin
                    idx       <= 16'h0;
                    pass_seed <= pass_seed + 32'h1;   // new pattern next pass
                    state     <= S_WRITE;
                end else begin
                    idx   <= idx + 16'h1;
                    state <= S_READ;
                end
            end
            default: state <= S_WRITE;
        endcase
    end
end

assign LED0_N = ~heartbeat[20];   // steady heartbeat while self-test runs
assign LED1_N = ~err_sticky;      // active-low convention: LIT means error latched

endmodule
