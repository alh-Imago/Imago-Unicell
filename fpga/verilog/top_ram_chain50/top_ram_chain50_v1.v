// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_ram_chain50_v1.v — points.md #248 (task 1): FIRST REAL-SILICON
// SIZE/TIMING CHECK for ram_cell_v1.v. NOT YET BUILT — prepared project,
// same sequencing discipline as every other primitive here: iverilog sim
// confirmed the logic (#235), this turns it into a real Quartus ALM count
// and Fmax, matching the 50-cell scale already used as the compute cell's
// own base figure (top_stripped_zone50_v1.v, #148) for a direct,
// apples-to-apples ALM/cell comparison between the two cell types.
//
// TOPOLOGY: a straight 50-cell West<-East chain, same shape as
// tb_ram_cell_v1_chain.v (#231/#235) but synthesizable and self-sustaining
// on real hardware instead of testbench-driven:
//   R0 (upstream=N, fed by a free-running on-die stimulus, NOT a fixed
//       constant — avoids the risk of Quartus constant-propagating a
//       static value through the whole chain and understating real cost)
//   -> R1..R48 (49 flowing cells, upstream=W, downstream=E)
//   -> R49 (upstream=W, downstream=E, but E connects to THIS top module's
//       own free-running consumer logic, not another cell — the same
//       role tb_ram_cell_v1_chain.v's testbench-side consumer played,
//       just synthesized instead of simulated)
// All 50 cells are genuinely live and structurally connected in one
// chain — deliberately NOT isolated instances, avoiding the #171 pruning
// trap (22/25 cells silently dead in that earlier baseline).
//
// ACK DIRECTION, stated explicitly since it bit an earlier draft of this
// file: ack flows OPPOSITE the data direction. Cell i's ack_out_w means
// "I just consumed what arrived from my west neighbor" and is what cell
// i-1 needs on its ack_in_e — a genuinely separate signal from cell i-1's
// own ack_out_e (which stays permanently 0 here, since no cell in this
// chain has upstream_mask=E set). One wire array (ack_w[i] = cell i's
// own ack_out_w) is sufficient; nothing needs a second array.
//
// Consumer continuously acks whenever R49 offers a value, which — per
// ram_cell_v1.v's own pull mechanism (ready_out = !data_valid, no
// dedicated request signal) — cascades a pull backward through the whole
// chain indefinitely, so every cell fires repeatedly for the whole run,
// not just once at boot. LED0 toggles on live consumes; LED1 is a slow
// heartbeat confirming the design is alive at all.
`default_nettype none
`timescale 1ns / 1ps

module top_ram_chain50_v1 (
    input  wire CLK_100M,   // 100 MHz board ref, PIN_E23 (same as existing projects)
    output wire LED0_N,     // toggles on live consumes
    output wire LED1_N      // slow blink: design alive/clocking
);

localparam CELLS = 50;
localparam MID    = CELLS - 2;   // 48 flowing middle cells (R1..R48)

// ── Clock/reset — same convention as every other stripped-cell top ──────
reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk = div_cnt[1];   // CLK_100M / 4 = 25 MHz, matching existing fabric clock

reg [3:0] rst_sr = 4'hF;
always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

// ── cfg_data field map, per ram_cell_v1.v's own header ──────────────────
//   [3:0] downstream_mask  [7:4] upstream_mask  [8] fixed_mode
//   [9] load_data_valid    [41:10] init_data     [63:42] reserved
// bit order N/S/E/W = bit0/1/2/3, matching unicell_stripped_v1.v convention.
localparam [3:0] DIR_N = 4'b0001, DIR_E = 4'b0100, DIR_W = 4'b1000;

localparam [63:0] CFG_R0  = {54'h0, DIR_N, DIR_E};  // upstream=N, downstream=E
localparam [63:0] CFG_MID = {54'h0, DIR_W, DIR_E};  // upstream=W, downstream=E

// ── One-shot power-on autoconfig — pulses cfg_valid/cfg_data for all 50
// cells in turn right after reset, same stand-in pattern as
// top_stripped_ring_test_v1.v (#88) ahead of eventual loader_fsm_v3.v
// integration. Sequenced one cell per cycle — 50 cycles total, trivial
// at 25MHz. ──
reg [5:0]       cfg_step      = 6'h0;
reg             cfg_active    = 1'b1;
reg [CELLS-1:0] cfg_valid_vec = {CELLS{1'b0}};
reg [63:0]      cfg_data_common = CFG_R0;

// cfg_data_common is REGISTERED alongside cfg_valid_vec, both driven from
// the SAME pre-increment cfg_step value in the same always block. An
// earlier draft derived cfg_data_common combinationally from cfg_step
// directly -- since cfg_step advances in this same block, that read the
// NEXT cell's step by the time cfg_valid_vec[i] was actually sampled by
// cell i one cycle later, silently configuring R0 as a middle cell
// (upstream=W instead of N) and stalling the whole chain at boot. Fixed
// by capturing cfg_data_common as a registered value tied to the exact
// step it corresponds to, not a live read of the already-advanced counter.
always @(posedge clk) begin
    if (rst) begin
        cfg_step        <= 6'h0;
        cfg_active      <= 1'b1;
        cfg_valid_vec   <= {CELLS{1'b0}};
        cfg_data_common <= CFG_R0;
    end else if (cfg_active) begin
        cfg_valid_vec           <= {CELLS{1'b0}};
        cfg_valid_vec[cfg_step] <= 1'b1;
        cfg_data_common         <= (cfg_step == 6'h0) ? CFG_R0 : CFG_MID;
        if (cfg_step == CELLS-1) begin
            cfg_active <= 1'b0;
        end else begin
            cfg_step <= cfg_step + 6'd1;
        end
    end else begin
        cfg_valid_vec <= {CELLS{1'b0}};
    end
end

// ── Free-running stimulus into R0's north port — a genuinely varying
// value, same reasoning as top_stripped_ring_test_v1.v: prevents Quartus
// from constant-propagating a static source value through 50 cells and
// understating real chain cost. ──
reg [31:0] stim_cnt = 32'h0;
always @(posedge clk) if (!rst) stim_cnt <= stim_cnt + 32'h1;
wire        seed_pulse = !cfg_active && (stim_cnt[5:0] == 6'h00);   // one cycle in 64
wire [31:0] seed_data  = {stim_cnt[15:0], stim_cnt[31:16]};

// ── Chain wiring ──────────────────────────────────────────────────────
wire [31:0] chain_data [0:CELLS-1];   // cell i's east data-out
wire        chain_fire [0:CELLS-1];   // cell i's east fire
wire        chain_ready[0:CELLS-1];   // cell i's ready_out
wire        ack_w      [0:CELLS-1];   // cell i's own ack_out_w (see header note)
wire        status_dv  [0:CELLS-1];

// R0 — no west input, ack_out_w left unconnected (never meaningfully driven).
ram_cell_v1 #(.CELL_ID(16'h0000)) R0 (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid_vec[0]), .cfg_data(cfg_data_common),
    .data_in_n(seed_data), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(seed_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(chain_data[0]), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(chain_fire[0]), .fire_w(),
    .ready_out(chain_ready[0]),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(chain_ready[1]), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_w[1]), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid(status_dv[0])
);

// R1..R48 — 48 identical flowing middle cells
genvar gk;
generate
    for (gk = 1; gk <= MID; gk = gk + 1) begin : RMID
        ram_cell_v1 #(.CELL_ID(16'h0000 + gk)) RC (
            .clk(clk), .rst(rst), .cfg_valid(cfg_valid_vec[gk]), .cfg_data(cfg_data_common),
            .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(chain_data[gk-1]),
            .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(chain_fire[gk-1]),
            .data_out_n(), .data_out_s(), .data_out_e(chain_data[gk]), .data_out_w(),
            .fire_n(), .fire_s(), .fire_e(chain_fire[gk]), .fire_w(),
            .ready_out(chain_ready[gk]),
            .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(chain_ready[gk+1]), .ready_in_w(1'b1),
            .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(ack_w[gk]),
            .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_w[gk+1]), .ack_in_w(1'b0),
            .freeze_in(1'b0), .status_data_valid(status_dv[gk])
        );
    end
endgenerate

// ── Consumer (embedded in top, plays the role tb_ram_cell_v1_chain.v's
// testbench-side consumer played) — continuously acks whenever R(CELLS-1)
// offers a value, driving the backward-cascading pull indefinitely. ──
reg        cons_ack      = 1'b0;
reg  [1:0] cons_state     = 2'h0;
reg [31:0] consume_count  = 32'h0;

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

// R49 (index CELLS-1) — last real cell; east side wired to this top's own
// consumer signals instead of another cell.
ram_cell_v1 #(.CELL_ID(16'h0000 + CELLS - 1)) RLAST (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid_vec[CELLS-1]), .cfg_data(cfg_data_common),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(chain_data[CELLS-2]),
    .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(chain_fire[CELLS-2]),
    .data_out_n(), .data_out_s(), .data_out_e(chain_data[CELLS-1]), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(chain_fire[CELLS-1]), .fire_w(),
    .ready_out(chain_ready[CELLS-1]),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(ack_w[CELLS-1]),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid(status_dv[CELLS-1])
);

assign LED0_N = ~consume_count[3];   // toggles quickly whenever consumes are landing
assign LED1_N = ~stim_cnt[23];       // slow heartbeat blink

endmodule
