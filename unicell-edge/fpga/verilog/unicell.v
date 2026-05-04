// unicell.v — Imago UniCell — Single Cell Implementation
// Claudette v1.2
//
// A single NOR-universal compute cell.
// Each cell watches the shared bus. When data arrives at its input_address
// it passes the value through the active NOR gate topology and writes
// the result to its output_address.
//
// Configuration addressing (Claudette v1.2):
//   Each cell has a FIXED configuration address = CONFIG_ADDRESS (default: CELL_ID).
//   This is a synthesis-time parameter — it never changes at runtime.
//   The runtime input_address register is for DATA routing only.
//   This separation prevents address-zero collisions on reset and ensures
//   no cell can accidentally intercept another cell's configuration sequence.
//
// Configuration sequence:
//   1. Send LOAD_PATTERN (0xA5A5A5A5) to the cell's CONFIG_ADDRESS
//   2. Next bus value loads gate_state
//   3. Next bus value loads input_address  (runtime data listen address)
//   4. Next bus value loads output_address (runtime data write address)
//   Cell arms automatically after step 4.
//
// Edge separation (GS_FALL_EDGE, bit 24):
//   When set, the cell asserts its output on the FALLING clock edge rather
//   than the rising edge. This separates two cells writing to the same
//   address in the same clock cycle without pad cells.
//   The compiler assigns this automatically — never user-visible.
//
// Freeze line:
//   When asserted, the cell is fully decoupled from the bus.
//   Internal state is preserved. No outputs. No config changes.
//   Used for pond migration, system snapshots, and fault isolation.
//
// Resource usage (approximate):
//   iCE40:   ~82 LUTs per cell
//   Artix-7: ~47 LUTs per cell
//   ECP5:    ~52 LUTs per cell
//
// A 32-cell array is safe for bring-up on iCEBreaker (iCE40UP5K: 5280 LUTs)
// A 64-cell array fits at ~97% utilisation

`timescale 1ns / 1ps

module unicell #(
    parameter CELL_ID        = 0,           // Unique cell identifier for debug
    parameter CONFIG_ADDRESS = CELL_ID      // Fixed config address — synthesis-time only.
                                            // Separated from runtime input_address so:
                                            //   - No address-zero collision on reset
                                            //   - No cell intercepts another's config
                                            //   - Data routing and config are independent
) (
    input  wire        clk,        // System clock (rising edge — data path)
    input  wire        clk_n,      // Inverted clock  (falling edge — GS_FALL_EDGE path)
    input  wire        rst,        // Synchronous reset (active high)
    input  wire        freeze,     // Freeze line — decouples cell from bus entirely

    // Shared bus interface
    input  wire [31:0] bus_addr,   // Current bus address
    input  wire [31:0] bus_data,   // Current bus data
    input  wire        bus_valid,  // Bus transaction valid this cycle

    // Output to bus (wired-OR with other cells)
    output wire [31:0] out_addr,   // Address this cell is writing to
    output wire [31:0] out_data,   // Data this cell is writing
    output wire        out_valid   // This cell has output this cycle

    // Debug/observability
    output wire [31:0] dbg_gate_state,
    output wire [31:0] dbg_input_addr,
    output wire [31:0] dbg_output_addr,
    output wire        dbg_start_flag,
    output wire        dbg_armed,
    output wire        dbg_frozen
);

// ── Constants ──────────────────────────────────────────────────────────────────
localparam LOAD_PATTERN = 32'hA5A5A5A5;

// gate_state bit assignments (matching gate_states.py)
localparam GS_NOT       = 32'h00000001;  // bit 0:  NOT
localparam GS_NOR       = 32'h00000004;  // bit 2:  NOR(g0,g1)
localparam GS_PASS      = 32'h00000000;  // pass through
localparam GS_LATCH     = 32'h00000800;  // bit 11: hold + re-emit each tick
localparam GS_ONE_SHOT  = 32'h00001000;  // bit 12: fire once then disarm
localparam GS_INVERT    = 32'h00002000;  // bit 13: invert output
localparam GS_LOOP      = 32'h00010000;  // bit 16: feed output back to input
localparam GS_FALL_EDGE = 32'h01000000;  // bit 24: assert on falling clock edge
localparam GS_LATCH_IN   = 32'h02000000;  // bit 25: input-side latch
localparam GS_OUT_POSEDGE = 32'h04000000; // bit 26: output buffer releases on rising edge
                                          //   0 (default): negedge of cycle N+1
                                          //   1:           posedge of cycle N+1
                                          //   rising edge: store new bus data in input_latch
                                          //   falling edge: if no new data, re-evaluate
                                          //                 using input_latch value
                                          //   enables single-cell counter with LOOP_MODE

// Config state machine states
localparam CFG_IDLE       = 2'd0;
localparam CFG_LOAD_GS    = 2'd1;
localparam CFG_LOAD_IADDR = 2'd2;
localparam CFG_LOAD_OADDR = 2'd3;

// ── Registers ──────────────────────────────────────────────────────────────────
reg [31:0] gate_state;      // NOR topology + mode flags
reg [31:0] input_address;   // Runtime data listen address (NOT config address)
reg [31:0] output_address;  // Address this cell writes results to
reg [31:0] data_reg;        // Stored value (latch mode)
reg        start_flag;      // Armed — dedicated hardware line, separate from bus
reg [1:0]  cfg_state;       // Config state machine
reg        one_shot_fired;  // GS_ONE_SHOT tracking

// Output buffer registers (UniCell-edge model)
// Cell computes on negedge (when B arrives). Result is held here and
// released to the bus at the next posedge (GS_OUT_POSEDGE=1) or
// next negedge (GS_OUT_POSEDGE=0, default).
reg        out_buf_valid;     // output buffer holds a result
reg [31:0] out_buf_data;      // buffered result data
reg [31:0] out_buf_addr;      // buffered output address
reg        out_buf_posedge;   // release on posedge (1) or negedge (0)

// Falling edge staging registers (legacy GS_FALL_EDGE path)
reg        fall_edge_pending;
reg [31:0] fall_edge_data;
reg [31:0] fall_edge_addr;

// Input latch (GS_LATCH_IN, bit 25)
// Holds last bus value received. Re-used on falling edge if no new data.
reg [31:0] input_latch;
reg        input_latch_valid;   // 1 once first value received

// ── Per-domain output registers ────────────────────────────────────────────────
// Each clock domain drives its own set of output registers.
// The module ports are wired-OR of both domains — only one domain fires per
// cycle so there is never a real collision, and Yosys sees a single driver
// for each output port.
reg        pos_valid; reg [31:0] pos_data; reg [31:0] pos_addr;
reg        neg_valid; reg [31:0] neg_data; reg [31:0] neg_addr;

assign out_valid = pos_valid | neg_valid;
assign out_data  = pos_valid ? pos_data : neg_data;
assign out_addr  = pos_valid ? pos_addr : neg_addr;

// ── Debug outputs ──────────────────────────────────────────────────────────────
assign dbg_gate_state  = gate_state;
assign dbg_input_addr  = input_address;
assign dbg_output_addr = output_address;
assign dbg_start_flag  = start_flag;
assign dbg_armed       = start_flag;
assign dbg_frozen      = freeze;

// ── NOR Gate Topology ──────────────────────────────────────────────────────────
// 9 NOR gates. gate_state[8:0] selects output. One bit active at a time.
//
//   g0 = NOT(input)     g1 = NOT(input)     g2 = AND(input,input) = NOR(NOT,NOT)
//   g3..g8 = extended topology options

function automatic nor_gate;
    input a, b;
    begin
        nor_gate = ~(a | b);
    end
endfunction

reg computed_output;

// Intermediate gate signals — module-scope for Verilog-2001 compatibility.
// Declared here, driven by the combinational always @(*) block below.
// Synthesises identically to local declarations — no registers inferred.
reg g0, g1, g2, g3, g4, g5, g6, g7, g8;
reg input_val;

always @(*) begin
    input_val = data_reg[0];

    g0 = nor_gate(input_val, input_val);
    g1 = nor_gate(input_val, input_val);
    g2 = nor_gate(g0, g1);
    g3 = nor_gate(g2, input_val);
    g4 = nor_gate(g2, input_val);
    g5 = nor_gate(g3, g4);
    g6 = nor_gate(g5, input_val);
    g7 = nor_gate(g6, g5);
    g8 = nor_gate(g7, 1'b0);

    case (gate_state[8:0])
        9'b000000001: computed_output = g0;
        9'b000000010: computed_output = g1;
        9'b000000100: computed_output = g2;
        9'b000001000: computed_output = g3;
        9'b000010000: computed_output = g4;
        9'b000100000: computed_output = g5;
        9'b001000000: computed_output = g6;
        9'b010000000: computed_output = g7;
        9'b100000000: computed_output = g8;
        default:      computed_output = input_val;
    endcase

    if (gate_state[13])
        computed_output = ~computed_output;
end

// ── Rising edge — main data path ───────────────────────────────────────────────
always @(posedge clk) begin
    if (rst) begin
        gate_state        <= 32'h0;
        input_address     <= 32'h0;
        output_address    <= 32'h0;
        data_reg          <= 32'h0;
        start_flag        <= 1'b0;
        cfg_state         <= CFG_IDLE;
        one_shot_fired    <= 1'b0;
        pos_valid         <= 1'b0;
        pos_data          <= 32'h0;
        pos_addr          <= 32'h0;
        out_buf_valid     <= 1'b0;
        out_buf_data      <= 32'h0;
        out_buf_addr      <= 32'h0;
        out_buf_posedge   <= 1'b0;
        fall_edge_pending <= 1'b0;
        fall_edge_data    <= 32'h0;
        fall_edge_addr    <= 32'h0;
        input_latch       <= 32'h0;
        input_latch_valid <= 1'b0;

    end else if (freeze) begin
        // Cell fully decoupled — preserve state, no outputs
        pos_valid         <= 1'b0;
        out_buf_valid     <= 1'b0;
        fall_edge_pending <= 1'b0;

    end else begin
        pos_valid         <= 1'b0;
        fall_edge_pending <= 1'b0;
        // Output buffer: release on posedge if GS_OUT_POSEDGE is set
        if (out_buf_valid && out_buf_posedge) begin
            pos_addr      <= out_buf_addr;
            pos_data      <= out_buf_data;
            pos_valid     <= 1'b1;
            out_buf_valid <= 1'b0;
        end

        if (bus_valid) begin
            case (cfg_state)
                CFG_IDLE: begin
                    // Config check uses CONFIG_ADDRESS — fixed synthesis parameter.
                    // Data check uses input_address — runtime register.
                    // These are intentionally separate. Config can never be
                    // accidentally triggered by data traffic.
                    if (bus_addr == CONFIG_ADDRESS[31:0] &&
                        bus_data == LOAD_PATTERN) begin
                        cfg_state  <= CFG_LOAD_GS;
                        start_flag <= 1'b0;

                    end else if (bus_addr == input_address && start_flag) begin
                        // Data received at runtime listen address
                        // GS_LATCH_IN: store in input latch for falling-edge re-use
                        if (gate_state[25]) begin
                            input_latch       <= bus_data;
                            input_latch_valid <= 1'b1;
                        end
                        if (gate_state[16])
                            data_reg <= {31'h0, computed_output};  // GS_LOOP
                        else
                            data_reg <= bus_data;

                        if (!(gate_state[12] && one_shot_fired)) begin
                            // Load output buffer — released next cycle
                            // GS_OUT_POSEDGE (bit 26): release on posedge N+1
                            // Default (bit clear):      release on negedge N+1
                            out_buf_addr    <= output_address;
                            out_buf_data    <= {31'h0, computed_output};
                            out_buf_valid   <= 1'b1;
                            out_buf_posedge <= gate_state[26];
                            // GS_FALL_EDGE (bit 24) is superseded by output buffer
                            // but kept for legacy compat — maps to negedge release
                            if (gate_state[24])
                                out_buf_posedge <= 1'b0;

                            if (gate_state[12]) begin
                                one_shot_fired <= 1'b1;
                                start_flag     <= 1'b0;
                            end
                        end

                        // GS_LATCH — update stored value
                        if (gate_state[11])
                            data_reg <= {31'h0, computed_output};

                    end else if (gate_state[11] && start_flag && !gate_state[24]) begin
                        // GS_LATCH re-emission on rising edge (no new data)
                        pos_addr  <= output_address;
                        pos_data  <= data_reg;
                        pos_valid <= 1'b1;
                    end
                end

                CFG_LOAD_GS: begin
                    gate_state <= bus_data;
                    cfg_state  <= CFG_LOAD_IADDR;
                end

                CFG_LOAD_IADDR: begin
                    input_address <= bus_data;   // Runtime data address
                    cfg_state     <= CFG_LOAD_OADDR;
                end

                CFG_LOAD_OADDR: begin
                    output_address <= bus_data;
                    cfg_state      <= CFG_IDLE;
                    start_flag     <= 1'b1;
                    one_shot_fired <= 1'b0;
                    data_reg       <= 32'h0;
                end

                default: cfg_state <= CFG_IDLE;
            endcase
        end
    end
end

// ── Falling edge — output buffer drain + GS_LATCH_IN re-evaluation ───────────
// Two jobs on negedge:
//
// 1. Drain output buffer (GS_OUT_POSEDGE=0, default):
//    Result was computed and latched into out_buf at the previous negedge.
//    It is now released to the bus ~41ns later (negedge N+1).
//    GS_OUT_POSEDGE=1 cells are drained on posedge instead (handled above).
//
// 2. GS_LATCH_IN (bit 25): if no new data arrived this tick, re-evaluate
//    using the input latch value. Result goes into output buffer for N+1.
//    With LOOP_MODE this enables the single-cell counter pattern.
always @(negedge clk) begin
    if (freeze || rst) begin
        neg_valid     <= 1'b0;
        out_buf_valid <= 1'b0;
    end else begin
        neg_valid <= 1'b0;

        // Drain output buffer for negedge-release cells
        if (out_buf_valid && !out_buf_posedge) begin
            neg_addr      <= out_buf_addr;
            neg_data      <= out_buf_data;
            neg_valid     <= 1'b1;
            out_buf_valid <= 1'b0;
        end

        // GS_LATCH_IN re-evaluation: compute on negedge using latched input,
        // load result into output buffer for release next cycle
        if (gate_state[25] && input_latch_valid && start_flag && !out_buf_valid) begin
            out_buf_addr    <= output_address;
            out_buf_data    <= {31'h0, computed_output};
            out_buf_valid   <= 1'b1;
            out_buf_posedge <= gate_state[26];
        end
    end
end

endmodule
