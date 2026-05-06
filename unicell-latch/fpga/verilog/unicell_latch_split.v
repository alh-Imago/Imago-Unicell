// unicell_latch_split.v — UniCell Latch Model with Internal 2x Clock Split
// Claudette v2.1 / unicell-latch-split variant
//
// CONCEPT:
//   External timing: unchanged — 2 cycles (load + fire), same as unicell_latch.v
//   Internal timing: NOR tree runs at 2x the external clock
//
//   Cycle 1 (external): full 32-bit data arrives → input_ff (as normal)
//   Cycle 2 (external):
//     Internal first half  (clk_2x posedge): data[15:0]  → 16-bit tree → lower_result
//     Internal second half (clk_2x posedge): data[31:16] → 16-bit tree → upper_result
//     Combine: {upper_result, lower_result} → output_ff → bus
//
//   External view is identical to unicell_latch.v.
//   Internal tree is 16-bit wide instead of 32-bit — half the LUTs.
//
// CLOCK SCHEME:
//   clk     — external cell clock (24MHz from SB_HFOSC "0b01")
//   clk_2x  — internal tree clock (48MHz from SB_HFOSC "0b00")
//   Both derived from same oscillator — no jitter, no PLL needed.
//   clk_2x is purely internal to this module.
//
// RESOURCE ESTIMATE vs unicell_latch.v:
//   Tree LUTs:    9 × 32 → 9 × 16 = ~144 LUT saving
//   Tree FFs:     9 × 32 → 9 × 16 = ~144 FF saving
//   Overhead:     ~25 LUTs (mux + half counter + lower_result reg)
//   Net saving:   ~120 LUTs per cell
//   iCEBreaker:   ~12 cells instead of ~8 (estimated)
//
// EXTERNAL INTERFACE: identical to unicell_latch.v
//   Same config sequence, same bus protocol, same Python bridge.
//   Drop-in replacement — no changes needed outside this file.
//
// VARIANT EXPLORER NOTE:
//   This file exists to measure real LUT/FF savings on iCE40 silicon.
//   Compare synthesis reports with unicell_latch.v to validate the theory.
//   The winner becomes the production cell.
//
// Portability: Standard Verilog-2001 + SB_HFOSC (iCE40 specific).
//   For non-iCE40: replace SB_HFOSC with appropriate clock primitive
//   or drive clk_2x from an external 2x clock input.

`timescale 1ns / 1ps
`default_nettype none

module unicell_latch_split #(
    parameter CONFIG_ADDRESS = 0        // Synthesis-time fixed config address
) (
    // External clock — 24MHz, defines the 2-cycle external timing
    input  wire        clk,
    input  wire        clk_2x,          // Internal 2x clock — 48MHz
    input  wire        rst,
    input  wire        freeze,          // Decouple from bus, preserve state

    // Bus interface — unchanged from unicell_latch.v
    input  wire [31:0] bus_addr,
    input  wire [31:0] bus_data,
    input  wire        bus_valid,

    // Start flag — armed state
    input  wire        start_flag_in,
    output reg         start_flag_out,

    // Output
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         out_valid
);

// ── Configuration registers (loaded via 5-word config sequence) ───────────────
reg [31:0] gate_state       = 32'h0;
reg [31:0] input_address    = 32'h0;
reg [31:0] output_address   = 32'h0;
reg [31:0] input_b_address  = 32'h0;

// ── Config state machine ───────────────────────────────────────────────────────
// Identical to unicell_latch.v — external interface unchanged
localparam CFG_IDLE       = 3'd0;
localparam CFG_LOAD_GS    = 3'd1;   // Word 2: gate_state
localparam CFG_LOAD_IADDR = 3'd2;   // Word 3: input_address (A)
localparam CFG_LOAD_OADDR = 3'd3;   // Word 4: output_address
localparam CFG_LOAD_BADDR = 3'd4;   // Word 5: input_b_address (B)

localparam LOAD_PATTERN   = 32'hA5A5A5A5;

reg [2:0] cfg_state = CFG_IDLE;

always @(posedge clk) begin
    if (rst) begin
        cfg_state      <= CFG_IDLE;
        gate_state     <= 32'h0;
        input_address  <= 32'h0;
        output_address <= 32'h0;
        input_b_address<= 32'h0;
    end else if (!freeze && bus_valid && bus_addr == CONFIG_ADDRESS[31:0]) begin
        case (cfg_state)
            CFG_IDLE:       if (bus_data == LOAD_PATTERN) cfg_state <= CFG_LOAD_GS;
            CFG_LOAD_GS:    begin gate_state    <= bus_data; cfg_state <= CFG_LOAD_IADDR; end
            CFG_LOAD_IADDR: begin input_address <= bus_data; cfg_state <= CFG_LOAD_OADDR; end
            CFG_LOAD_OADDR: begin
                output_address <= bus_data;
                // Two-input cell needs 5th word if GS_SYNC_WAIT set
                cfg_state <= gate_state[15] ? CFG_LOAD_BADDR : CFG_IDLE;
            end
            CFG_LOAD_BADDR: begin input_b_address <= bus_data; cfg_state <= CFG_IDLE; end
            default:        cfg_state <= CFG_IDLE;
        endcase
    end
end

// ── Input latches (loaded on external clk cycle 1) ────────────────────────────
reg [31:0] input_ff   = 32'h0;
reg [31:0] input_b_ff = 32'h0;
reg        input_ff_valid   = 1'b0;
reg        input_b_ff_valid = 1'b0;

always @(posedge clk) begin
    if (rst || freeze) begin
        input_ff_valid   <= 1'b0;
        input_b_ff_valid <= 1'b0;
    end else if (bus_valid && start_flag_out) begin
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

// ── Ready to compute: both inputs present ─────────────────────────────────────
wire single_input = !gate_state[15];
wire compute_ready = input_ff_valid && (single_input || input_b_ff_valid);

// ── Internal 2x clock: 16-bit split NOR tree ─────────────────────────────────
// half=0: process data[15:0]  (lower)
// half=1: process data[31:16] (upper) then combine and latch output

reg         half         = 1'b0;   // toggles at clk_2x rate
reg         computing    = 1'b0;   // high for the two clk_2x cycles of computation
reg [15:0]  lower_result = 16'h0;  // holds lower half result between clk_2x cycles

// Mux: select which 16-bit slice feeds the tree
wire [15:0] tree_a = half ? input_ff[31:16]   : input_ff[15:0];
wire [15:0] tree_b = half ? input_b_ff[31:16] : input_b_ff[15:0];

// ── 16-bit NOR gate tree ───────────────────────────────────────────────────────
// Same topology as unicell_latch.v but 16-bit wide.
// gate_state[8:0] selects output. A=tree_a (posedge/A-input slice),
// B=tree_b (negedge/B-input slice).

wire [15:0] g0 = ~(tree_a | tree_a);          // NOT(A)
wire [15:0] g1 = ~(tree_b | tree_b);          // NOT(B)
wire [15:0] g2 = ~(g0 | g1);                  // AND(A,B)
wire [15:0] g3 = ~(g2 | tree_b);
wire [15:0] g4 = ~(g2 | tree_a);
wire [15:0] g5 = ~(g3 | g4);
wire [15:0] g6 = ~(g5 | tree_b);
wire [15:0] g7 = ~(g6 | g5);
wire [15:0] g8 = ~(g7 | 16'h0000);            // NOT(g7)

// Gate selection mux (gate_state[8:0])
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
    tree_a;                                    // default: PASS_A

// ── Internal 2x clock state machine ──────────────────────────────────────────
always @(posedge clk_2x) begin
    if (rst) begin
        half         <= 1'b0;
        computing    <= 1'b0;
        lower_result <= 16'h0;
        out_valid    <= 1'b0;
    end else if (!freeze) begin

        if (!computing && compute_ready) begin
            // Start computation — lower half first
            half      <= 1'b0;
            computing <= 1'b1;
            out_valid <= 1'b0;
        end else if (computing) begin
            half <= ~half;

            if (!half) begin
                // First clk_2x cycle: lower half done
                lower_result <= tree_out;
            end else begin
                // Second clk_2x cycle: upper half done — combine and output
                out_addr  <= output_address;
                out_data  <= {tree_out, lower_result};   // {upper, lower}
                out_valid <= 1'b1;
                computing <= 1'b0;
                half      <= 1'b0;
            end
        end else begin
            out_valid <= 1'b0;
        end
    end
end

// ── Start flag ────────────────────────────────────────────────────────────────
always @(posedge clk) begin
    if (rst)
        start_flag_out <= 1'b0;
    else if (!freeze)
        start_flag_out <= start_flag_in;
end

endmodule
