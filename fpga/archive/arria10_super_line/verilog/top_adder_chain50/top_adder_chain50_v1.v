// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_adder_chain50_v1.v — points.md #248 (task 2): FIRST REAL-SILICON
// SIZE/TIMING CHECK for adder_cell_v1.v. NOT YET BUILT — prepared
// project, same discipline as top_ram_chain50_v1.v (#249): iverilog sim
// confirmed the logic (tb_adder_cell_v1.v), this turns it into a real
// Quartus ALM count and Fmax, at the same 50-cell scale as both the
// compute cell's own baseline (#148) and the RAM cell's own baseline
// (#249/#250), for a direct three-way ALM/cell comparison.
//
// TOPOLOGY: a 50-cell running-accumulator chain. Each cell's A operand
// is the running sum arriving from its West neighbor (cell 0's West is
// fed by a top-level seed generator instead of a neighbor); each cell's
// B operand is a periodic, broadcast, time-varying "tick" value arriving
// on its North port simultaneously across all 50 cells. Both directions
// share upstream_mask=W|N on every cell — identical config across the
// whole chain, only cell 0's West WIRING differs (top-level stimulus
// instead of a neighbor's data_out_e), mirroring exactly how
// top_ram_chain50_v1.v's R0 differed only in wiring, not config.
//
// Cell logic doesn't distinguish "which port is A" — same as
// unicell_stripped_v1.v's own two-arrival model, whichever direction
// arrives FIRST becomes A regardless of N/S/E/W. The broadcast North
// tick and the cascading West relay race genuinely, which is fine for a
// sizing/timing check (real logic exercised repeatedly, not a specific
// algorithmic result being graded) — tb_adder_cell_v1.v already covers
// the correctness question for a single cell.
//
// Consumer (embedded in top, same role as top_ram_chain50_v1.v's own)
// continuously acks whenever the last cell offers a sum, keeping the
// chain's ready/ack fabric genuinely exercised end to end.
`default_nettype none
`timescale 1ns / 1ps

module top_adder_chain50_v1 (
    input  wire CLK_100M,   // 100 MHz board ref, PIN_E23 (same as existing projects)
    output wire LED0_N,     // toggles on live consumes
    output wire LED1_N      // slow blink: design alive/clocking
);

localparam CELLS = 50;
localparam MID    = CELLS - 2;   // 48 middle cells (C1..C48)

// ── Clock/reset — same convention as every other stripped-cell top ──────
reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk = div_cnt[1];   // CLK_100M / 4 = 25 MHz

reg [3:0] rst_sr = 4'hF;
always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

// ── cfg_data field map, per adder_cell_v1.v's own header ────────────────
//   [3:0] downstream_mask  [7:4] upstream_mask  [63:8] reserved
localparam [3:0] DIR_N = 4'b0001, DIR_E = 4'b0100, DIR_W = 4'b1000;
localparam [63:0] CFG_ALL = {56'h0, (DIR_N | DIR_W), DIR_E};  // identical on all 50 cells

// ── One-shot power-on autoconfig — pulses cfg_valid/cfg_data for all 50
// cells in turn, one per clk cycle. Same registered-alongside-the-pulse
// fix #249 needed for the RAM chain (cfg_data must be tied to the exact
// pre-increment step, not a live read of the already-advanced counter)
// — trivial here since CFG_ALL is a single constant, but kept as an
// explicit registered value for consistency/future-proofing. ──
reg [5:0]       cfg_step   = 6'h0;
reg             cfg_active = 1'b1;
reg [CELLS-1:0] cfg_valid_vec = {CELLS{1'b0}};

always @(posedge clk) begin
    if (rst) begin
        cfg_step      <= 6'h0;
        cfg_active    <= 1'b1;
        cfg_valid_vec <= {CELLS{1'b0}};
    end else if (cfg_active) begin
        cfg_valid_vec           <= {CELLS{1'b0}};
        cfg_valid_vec[cfg_step] <= 1'b1;
        if (cfg_step == CELLS-1) begin
            cfg_active <= 1'b0;
        end else begin
            cfg_step <= cfg_step + 6'd1;
        end
    end else begin
        cfg_valid_vec <= {CELLS{1'b0}};
    end
end

// ── Stimulus: cell 0's West seed (genuinely varying, avoids constant
// propagation) and the broadcast North "tick" shared by all 50 cells. ──
reg [31:0] stim_cnt = 32'h0;
always @(posedge clk) if (!rst) stim_cnt <= stim_cnt + 32'h1;

wire        seed_pulse_w = !cfg_active && (stim_cnt[5:0]  == 6'h00);  // 1-in-64
wire [31:0] seed_data_w  = {stim_cnt[15:0], stim_cnt[31:16]};

wire        tick_pulse_n = !cfg_active && (stim_cnt[6:0]  == 7'h40);  // 1-in-128, offset from seed
wire [31:0] tick_data_n  = stim_cnt ^ 32'hA5A5_5A5A;

// ── Chain wiring ──────────────────────────────────────────────────────
wire [31:0] chain_data [0:CELLS-1];   // cell i's east data-out
wire        chain_fire [0:CELLS-1];   // cell i's east fire
wire        chain_ready[0:CELLS-1];   // cell i's ready_out
wire        ack_w      [0:CELLS-1];   // cell i's own ack_out_w (see top_ram_chain50_v1.v note on ack direction)

// C0 — West fed by top-level seed, North fed by the broadcast tick.
adder_cell_v1 #(.CELL_ID(16'h0000)) C0 (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid_vec[0]), .cfg_data(CFG_ALL),
    .data_in_n(tick_data_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(seed_data_w),
    .arrived_n(tick_pulse_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(seed_pulse_w),
    .data_out_n(), .data_out_s(), .data_out_e(chain_data[0]), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(chain_fire[0]), .fire_w(),
    .ready_out(chain_ready[0]),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(chain_ready[1]), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(ack_w[0]),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_w[1]), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid(), .status_a_arrived()
);

// C1..C48 — West from previous cell, North from the same broadcast tick.
genvar gk;
generate
    for (gk = 1; gk <= MID; gk = gk + 1) begin : CMID
        adder_cell_v1 #(.CELL_ID(16'h0000 + gk)) CC (
            .clk(clk), .rst(rst), .cfg_valid(cfg_valid_vec[gk]), .cfg_data(CFG_ALL),
            .data_in_n(tick_data_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(chain_data[gk-1]),
            .arrived_n(tick_pulse_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(chain_fire[gk-1]),
            .data_out_n(), .data_out_s(), .data_out_e(chain_data[gk]), .data_out_w(),
            .fire_n(), .fire_s(), .fire_e(chain_fire[gk]), .fire_w(),
            .ready_out(chain_ready[gk]),
            .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(chain_ready[gk+1]), .ready_in_w(1'b1),
            .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(ack_w[gk]),
            .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_w[gk+1]), .ack_in_w(1'b0),
            .freeze_in(1'b0), .status_data_valid(), .status_a_arrived()
        );
    end
endgenerate

// ── Consumer (embedded in top) — continuously acks whenever the last
// cell offers a sum. ──
reg        cons_ack     = 1'b0;
reg  [1:0] cons_state    = 2'h0;
reg [31:0] consume_count = 32'h0;

wire last_fire_e = chain_fire[CELLS-1];

always @(posedge clk) begin
    cons_ack <= 1'b0;
    if (rst) begin
        cons_state    <= 2'h0;
        consume_count <= 32'h0;
    end else begin
        case (cons_state)
            2'h0: if (last_fire_e) cons_state <= 2'h1;
            2'h1: begin
                cons_ack      <= 1'b1;
                consume_count <= consume_count + 32'h1;
                cons_state    <= 2'h2;
            end
            2'h2: cons_state <= 2'h0;
            default: cons_state <= 2'h0;
        endcase
    end
end

// C49 (index CELLS-1) — East side wired to this top's own consumer.
adder_cell_v1 #(.CELL_ID(16'h0000 + CELLS - 1)) CLAST (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid_vec[CELLS-1]), .cfg_data(CFG_ALL),
    .data_in_n(tick_data_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(chain_data[CELLS-2]),
    .arrived_n(tick_pulse_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(chain_fire[CELLS-2]),
    .data_out_n(), .data_out_s(), .data_out_e(chain_data[CELLS-1]), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(chain_fire[CELLS-1]), .fire_w(),
    .ready_out(chain_ready[CELLS-1]),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(ack_w[CELLS-1]),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid(), .status_a_arrived()
);

assign LED0_N = ~consume_count[3];   // toggles quickly whenever consumes are landing
assign LED1_N = ~stim_cnt[23];       // slow heartbeat blink

endmodule
