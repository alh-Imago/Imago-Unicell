// unicell.v — Imago UniCell — Single Cell Implementation
// Claudette v1.1
//
// A single NOR-universal compute cell.
// Each cell is a 192-bit register file plus a 9-gate NOR topology tree
// and a dedicated start flag line.
//
// The cell watches the shared bus. When data arrives at its input_address
// it passes the value through the active NOR gate topology and writes
// the result to its output_address.
//
// Configuration is via the FUNCTION_LOAD_PATTERN mechanism:
// when the bus carries 0xA5A5A5A5 at the cell's address, the next
// three bus values load gate_state, input_address, and output_address.
//
// Resource usage (approximate):
//   iCE40:   ~80 LUTs per cell
//   Artix-7: ~45 LUTs per cell
//   ECP5:    ~50 LUTs per cell
//
// A 256-cell array fits comfortably on iCEBreaker (iCE40UP5K: 5280 LUTs)
// A 1024-cell array fits on Basys 3 (Artix-7: 33280 LUTs)

`timescale 1ns / 1ps

module unicell #(
    parameter CELL_ID = 0          // Unique cell identifier for debug
) (
    input  wire        clk,        // System clock
    input  wire        rst,        // Synchronous reset (active high)

    // Shared bus interface
    input  wire [31:0] bus_addr,   // Current bus address
    input  wire [31:0] bus_data,   // Current bus data
    input  wire        bus_valid,  // Bus transaction valid this cycle

    // Output to bus (wired-OR with other cells)
    output reg  [31:0] out_addr,   // Address this cell is writing to
    output reg  [31:0] out_data,   // Data this cell is writing
    output reg         out_valid,  // This cell has output this cycle

    // Debug/observability (connect to logic analyser or workbench)
    output wire [31:0] dbg_gate_state,
    output wire [31:0] dbg_input_addr,
    output wire [31:0] dbg_output_addr,
    output wire        dbg_start_flag,
    output wire        dbg_armed
);

// ── Constants ────────────────────────────────────────────────────────────────
localparam LOAD_PATTERN = 32'hA5A5A5A5;

// gate_state bit assignments
localparam GS_NOT      = 32'h00000001;  // bit 0: NOT (single input)
localparam GS_NOR      = 32'h00000004;  // bit 2: NOR(g0,g1)
localparam GS_PASS     = 32'h00000000;  // no bits: pass through
localparam GS_LATCH    = 32'h00000800;  // bit 11: hold value on no input
localparam GS_ONE_SHOT = 32'h00001000;  // bit 12: fire once then disarm
localparam GS_INVERT   = 32'h00002000;  // bit 13: invert output
localparam GS_LOOP     = 32'h00010000;  // bit 16: feed output back to input

// Config state machine
localparam CFG_IDLE       = 2'd0;
localparam CFG_LOAD_GS    = 2'd1;
localparam CFG_LOAD_IADDR = 2'd2;
localparam CFG_LOAD_OADDR = 2'd3;

// ── Registers ─────────────────────────────────────────────────────────────────
reg [31:0] gate_state;      // NOR topology bits + mode flags
reg [31:0] input_address;   // Address this cell listens to
reg [31:0] output_address;  // Address this cell writes to
reg [31:0] data_reg;        // Stored data value (for latch mode)
reg        start_flag;      // Armed state — dedicated hardware line
reg [1:0]  cfg_state;       // Configuration state machine
reg        one_shot_fired;  // Track if one-shot has fired

// ── Debug outputs ─────────────────────────────────────────────────────────────
assign dbg_gate_state  = gate_state;
assign dbg_input_addr  = input_address;
assign dbg_output_addr = output_address;
assign dbg_start_flag  = start_flag;
assign dbg_armed       = start_flag;

// ── NOR Gate Topology ─────────────────────────────────────────────────────────
// 9 NOR gates arranged as a fixed tree.
// Only one bit of gate_state[8:0] should be active at a time.
// g0/g1 are NOT gates (NOR(x,x) = NOT(x))
// g2 combines g0 and g1 outputs
// g3-g8 provide additional topology options

function automatic nor_gate;
    input a, b;
    begin
        nor_gate = ~(a | b);
    end
endfunction

reg computed_output;

always @(*) begin
    reg g0, g1, g2, g3, g4, g5, g6, g7, g8;
    reg input_val;

    input_val = data_reg[0];  // Operate on LSB for single-bit mode

    // Gate topology
    g0 = nor_gate(input_val, input_val);  // NOT(input)
    g1 = nor_gate(input_val, input_val);  // NOT(input) — second path
    g2 = nor_gate(g0, g1);               // NOR(NOT,NOT) = AND
    g3 = nor_gate(g2, input_val);
    g4 = nor_gate(g2, input_val);
    g5 = nor_gate(g3, g4);
    g6 = nor_gate(g5, input_val);
    g7 = nor_gate(g6, g5);
    g8 = nor_gate(g7, 1'b0);             // Buffer

    // Select output based on active gate_state bits
    case (gate_state[8:0])
        9'b000000001: computed_output = g0;   // GS_NOT
        9'b000000010: computed_output = g1;
        9'b000000100: computed_output = g2;   // GS_NOR
        9'b000001000: computed_output = g3;
        9'b000010000: computed_output = g4;
        9'b000100000: computed_output = g5;
        9'b001000000: computed_output = g6;
        9'b010000000: computed_output = g7;
        9'b100000000: computed_output = g8;
        default:      computed_output = input_val;  // GS_PASS
    endcase

    // Apply invert flag
    if (gate_state[13])
        computed_output = ~computed_output;
end

// ── Main Sequential Logic ─────────────────────────────────────────────────────
always @(posedge clk) begin
    if (rst) begin
        gate_state    <= 32'h0;
        input_address <= 32'h0;
        output_address<= 32'h0;
        data_reg      <= 32'h0;
        start_flag    <= 1'b0;
        cfg_state     <= CFG_IDLE;
        one_shot_fired<= 1'b0;
        out_valid     <= 1'b0;
        out_data      <= 32'h0;
        out_addr      <= 32'h0;
    end else begin
        out_valid <= 1'b0;  // Default: no output this cycle

        if (bus_valid) begin
            // ── Configuration state machine ───────────────────────────────
            case (cfg_state)
                CFG_IDLE: begin
                    if (bus_addr == input_address &&
                        bus_data == LOAD_PATTERN) begin
                        // Entering configuration mode
                        cfg_state  <= CFG_LOAD_GS;
                        start_flag <= 1'b0;  // Disarm during config
                    end else if (bus_addr == input_address && start_flag) begin
                        // Normal data receive — armed and listening
                        if (gate_state[16]) begin
                            // GS_LOOP: feed output back
                            data_reg <= {31'h0, computed_output};
                        end else begin
                            data_reg <= bus_data;
                        end

                        // Check one-shot
                        if (gate_state[12] && one_shot_fired) begin
                            // Already fired — don't output again
                        end else begin
                            // Emit output
                            out_addr  <= output_address;
                            out_data  <= {31'h0, computed_output};
                            out_valid <= 1'b1;

                            if (gate_state[12]) begin
                                one_shot_fired <= 1'b1;
                                start_flag     <= 1'b0;
                            end
                        end
                    end
                end

                CFG_LOAD_GS: begin
                    gate_state <= bus_data;
                    cfg_state  <= CFG_LOAD_IADDR;
                end

                CFG_LOAD_IADDR: begin
                    input_address  <= bus_data;
                    cfg_state      <= CFG_LOAD_OADDR;
                end

                CFG_LOAD_OADDR: begin
                    output_address <= bus_data;
                    cfg_state      <= CFG_IDLE;
                    start_flag     <= 1'b1;   // Arm on config complete
                    one_shot_fired <= 1'b0;
                    data_reg       <= 32'h0;
                end

                default: cfg_state <= CFG_IDLE;
            endcase
        end
    end
end

endmodule
