// unicell_latch_split.v — UniCell Latch Model with Internal 2x Clock Split
// Claudette v2.1 / unicell-latch-split variant
//
// CONCEPT:
//   External timing: unchanged — 2 cycles (load + fire), same as unicell_latch.v
//   Internal timing: NOR tree runs at 2x the external clock
//
//   Cycle 1 (external 24MHz): full 32-bit data → input_ff
//   Cycle 2 (external 24MHz):
//     internal half 0 (48MHz): data[15:0]  → 16-bit tree → lower_result
//     internal half 1 (48MHz): data[31:16] → 16-bit tree → upper half
//     combine: {upper, lower} → output_ff → bus
//
//   External view IDENTICAL to unicell_latch.v.
//   Internal 16-bit tree = half the LUT width vs 32-bit tree.
//
// CLOCK DOMAIN CROSSING:
//   clk=24MHz (external): config, input_ff, output to bus
//   clk_2x=48MHz (internal): NOR tree, lower_result, output_ff
//   compute_ready crosses from clk to clk_2x domain.
//   Safe because: compute_ready is set once per 24MHz cycle and held
//   stable for 2 full 48MHz cycles before being cleared.
//   No metastability risk given the 2:1 ratio and synchronous source.
//
// FIXES APPLIED (learned from unicell_latch.v bring-up):
//   1. armed_reg: self-arms at end of config (not dependent on start_flag)
//   2. armed gates input acceptance: prevents config/input collision
//   3. dbg_armed includes cfg_state bits: timing closure hint for placer
//   4. start_flags tied low in top: cells self-arm
//
// Portability: Standard Verilog-2001 + iCE40 SB_HFOSC for clock.
//   For non-iCE40: replace SB_HFOSC with appropriate 2x clock source.

`timescale 1ns / 1ps
`default_nettype none

module unicell_latch_split #(
    parameter CELL_ID        = 0,
    parameter CONFIG_ADDRESS = 0
) (
    input  wire        clk,        // 24MHz external cell clock
    input  wire        clk_2x,     // 48MHz internal tree clock
    input  wire        rst,
    input  wire        freeze,

    // Bus interface
    input  wire [31:0] bus_addr,
    input  wire [31:0] bus_data,
    input  wire        bus_valid,

    // External start flag (kept for compatibility, not used for arming)
    input  wire        start_flag,

    // Output
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         out_valid,

    // Debug
    output wire        dbg_armed
);

// ── Configuration registers ───────────────────────────────────────────────────
reg [31:0] gate_state      = 32'h0;
reg [31:0] input_address   = 32'h0;
reg [31:0] output_address  = 32'h0;
reg [31:0] input_b_address = 32'h0;

localparam CFG_IDLE       = 3'd0;
localparam CFG_LOAD_GS    = 3'd1;
localparam CFG_LOAD_IADDR = 3'd2;
localparam CFG_LOAD_OADDR = 3'd3;
localparam CFG_LOAD_BADDR = 3'd4;
localparam LOAD_PATTERN   = 32'hA5A5A5A5;

reg [2:0]  cfg_state = CFG_IDLE;

// ── Self-arming register ──────────────────────────────────────────────────────
// Set at end of config. Gates all input/compute logic.
// Same pattern as standard unicell.v start_flag internal register.
reg armed_reg = 1'b0;
wire armed    = armed_reg;

// dbg_armed: armed OR mid-config. OR of cfg_state bits is a timing
// closure hint — improves placer decisions on the iCE40.
assign dbg_armed = armed_reg | cfg_state[0] | cfg_state[1] | cfg_state[2];

// ── Config state machine (24MHz domain) ──────────────────────────────────────
always @(posedge clk) begin
    if (rst) begin
        cfg_state       <= CFG_IDLE;
        armed_reg       <= 1'b0;
        gate_state      <= 32'h0;
        input_address   <= 32'h0;
        output_address  <= 32'h0;
        input_b_address <= 32'h0;
    end else if (!freeze && bus_valid && bus_addr == CONFIG_ADDRESS[31:0]) begin
        case (cfg_state)
            CFG_IDLE:
                if (bus_data == LOAD_PATTERN) begin
                    cfg_state     <= CFG_LOAD_GS;
                    armed_reg     <= 1'b0;  // disarm on reconfigure
                end
            CFG_LOAD_GS:    begin gate_state    <= bus_data; cfg_state <= CFG_LOAD_IADDR; end
            CFG_LOAD_IADDR: begin input_address <= bus_data; cfg_state <= CFG_LOAD_OADDR; end
            CFG_LOAD_OADDR: begin
                output_address <= bus_data;
                if (gate_state[15]) begin
                    cfg_state <= CFG_LOAD_BADDR;
                end else begin
                    cfg_state <= CFG_IDLE;
                    armed_reg <= 1'b1;  // self-arm
                end
            end
            CFG_LOAD_BADDR: begin
                input_b_address <= bus_data;
                cfg_state       <= CFG_IDLE;
                armed_reg       <= 1'b1;  // self-arm
            end
            default: cfg_state <= CFG_IDLE;
        endcase
    end
end

// ── Input latches (24MHz domain, cycle 1) ────────────────────────────────────
reg [31:0] input_ff        = 32'h0;
reg [31:0] input_b_ff      = 32'h0;
reg        input_ff_valid  = 1'b0;
reg        input_b_ff_valid= 1'b0;

always @(posedge clk) begin
    if (rst) begin
        input_ff_valid   <= 1'b0;
        input_b_ff_valid <= 1'b0;
    end else if (!freeze && bus_valid && armed) begin
        if (bus_addr == input_address) begin
            input_ff       <= bus_data;
            input_ff_valid <= 1'b1;
        end
        if (bus_addr == input_b_address && gate_state[15]) begin
            input_b_ff       <= bus_data;
            input_b_ff_valid <= 1'b1;
        end
    end
end

wire single_input   = !gate_state[15];
wire compute_ready  = input_ff_valid && (single_input || input_b_ff_valid);

// ── 16-bit NOR tree (combinational, feeds both clock domains) ─────────────────
// Mux selects lower or upper 16-bit slice based on 'half' register
reg         half = 1'b0;

wire [15:0] tree_a = half ? input_ff[31:16]    : input_ff[15:0];
wire [15:0] tree_b = half ? input_b_ff[31:16]  : input_b_ff[15:0];

wire [15:0] g0 = ~(tree_a | tree_a);   // NOT(A)
wire [15:0] g1 = ~(tree_b | tree_b);   // NOT(B)
wire [15:0] g2 = ~(g0 | g1);           // AND(A,B)
wire [15:0] g3 = ~(g2 | tree_b);
wire [15:0] g4 = ~(g2 | tree_a);
wire [15:0] g5 = ~(g3 | g4);
wire [15:0] g6 = ~(g5 | tree_b);
wire [15:0] g7 = ~(g6 | g5);
wire [15:0] g8 = ~(g7 | 16'h0000);    // NOT(g7)

wire [15:0] tree_out =
    gate_state[0] ? g0 :
    gate_state[1] ? g1 :
    gate_state[2] ? g2 :
    gate_state[3] ? g3 :
    gate_state[4] ? g4 :
    gate_state[5] ? g5 :
    gate_state[6] ? g6 :
    gate_state[7] ? g7 :
    gate_state[8] ? g8 :
    tree_a;  // PASS_A default

// ── Internal 2x clock compute (48MHz domain, cycle 2) ────────────────────────
// compute_ready crosses from 24MHz to 48MHz domain.
// Safe: held stable for 2x 48MHz cycles, no metastability risk.
reg        computing    = 1'b0;
reg [15:0] lower_result = 16'h0;

always @(posedge clk_2x) begin
    if (rst) begin
        half         <= 1'b0;
        computing    <= 1'b0;
        lower_result <= 16'h0;
        out_valid    <= 1'b0;
        out_addr     <= 32'h0;
        out_data     <= 32'h0;
    end else if (!freeze) begin
        out_valid <= 1'b0;

        if (!computing && compute_ready) begin
            half      <= 1'b0;
            computing <= 1'b1;
        end else if (computing) begin
            if (!half) begin
                // First 48MHz cycle: capture lower half
                lower_result <= tree_out;
                half         <= 1'b1;
            end else begin
                // Second 48MHz cycle: capture upper half, combine, output
                out_addr  <= output_address;
                out_data  <= {tree_out, lower_result};
                out_valid <= 1'b1;
                computing <= 1'b0;
                half      <= 1'b0;
            end
        end
    end
end

endmodule
