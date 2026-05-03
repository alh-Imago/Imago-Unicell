// unicell_array_latch.v — Imago UniCell Array — Latch Model
// Claudette v2.1 / unicell-latch variant
//
// Array wrapper for unicell_latch cells. Implements the 3-phase tick
// matching unicell_array.py tick_drain() semantics:
//
//   Phase 1: Drain — each cell drives its output_ff onto the bus.
//            All cells see the updated bus simultaneously.
//   Phase 2: Load  — cells whose input_address matches the bus address
//            load the data into their input_ff. (Handled inside unicell_latch.)
//   Phase 3: Compute — cells with input_ff_valid fire the gate tree.
//            Result → output_ff for next tick's drain.
//
// In RTL, Phases 1 and 2 collapse into the same posedge clk edge:
//   - Cell A drains output_ff → out_addr/out_data/out_valid
//   - The array OR-combines all cell outputs onto the bus
//   - The same clock edge's bus_valid propagates to all cells
//   - Cell B (listening to A's output address) loads its input_ff
// This is why chain_latency(n) = n+1 (not n*2).
//
// Start flags:
//   start_flag is a direct input to each cell — not a bus transaction.
//   The host sets start_flags via the start_flags_in register.
//   In a full system: fpga_bridge.py writes to start_flags_in via
//   a dedicated UART command. The array exposes start_flags_out so
//   the host can read current armed state.
//
// Freeze:
//   Global freeze line freezes all cells simultaneously. State is preserved.
//   Used for pond migration and snapshots. When freeze is deasserted, the
//   array continues exactly where it left off — output_ff contents are
//   drained on the first tick after thaw.
//
// Parameters:
//   NUM_CELLS    — array size (default 32)
//   BASE_ADDRESS — config address base (cells: BASE_ADDRESS..BASE_ADDRESS+N-1)
//
// Resource estimate:
//   iCE40:   ~95 LUTs/cell + ~50 LUTs array overhead
//   32 cells: ~3090 LUTs (58% of iCE40UP5K) — comfortable bring-up target
//   64 cells: ~6130 LUTs — fits ECP5 and Artix-7 easily
//
// Portability: Standard Verilog-2001. No vendor primitives.

`timescale 1ns / 1ps

module unicell_array_latch #(
    parameter NUM_CELLS    = 32,   // Array size. 32 = safe iCEBreaker bring-up.
    parameter BASE_ADDRESS = 0     // Config address offset
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze,          // Global freeze — all cells decouple

    // CPU/host interface — drives bus directly
    input  wire [31:0] cpu_addr,
    input  wire [31:0] cpu_data,
    input  wire        cpu_valid,

    // Start flag bus — controller sets armed state per cell
    // In a full system this is written via UART command + cell_index field.
    // Width = NUM_CELLS, bit i = start_flag for cell i.
    input  wire [NUM_CELLS-1:0] start_flags_in,
    output wire [NUM_CELLS-1:0] start_flags_out,   // Echo for observability

    // Output to host (first cell that fires this cycle)
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         out_valid,

    // Status
    output wire [15:0] armed_count,
    output wire [31:0] cycle_count
);

// ── Cell I/O arrays ───────────────────────────────────────────────────────────
wire [31:0] cell_out_addr   [0:NUM_CELLS-1];
wire [31:0] cell_out_data   [0:NUM_CELLS-1];
wire        cell_out_valid  [0:NUM_CELLS-1];

// Debug wires (not connected to ports — available for chipscope/SignalTap)
wire [31:0] cell_dbg_gs     [0:NUM_CELLS-1];
wire [31:0] cell_dbg_ia     [0:NUM_CELLS-1];
wire [31:0] cell_dbg_oa     [0:NUM_CELLS-1];
wire        cell_dbg_armed  [0:NUM_CELLS-1];
wire        cell_dbg_frozen [0:NUM_CELLS-1];
wire        cell_dbg_iv     [0:NUM_CELLS-1];   // input_ff_valid
wire        cell_dbg_ov     [0:NUM_CELLS-1];   // output_ff_valid
wire        cell_dbg_bv     [0:NUM_CELLS-1];   // input_b_ff_valid

// ── Internal bus ──────────────────────────────────────────────────────────────
// The bus is the single shared medium. All cells see it every tick.
// In Phases 1+2:
//   - If any cell fired (or_valid): put that cell's output on the bus
//   - If the host is writing (cpu_valid): host overrides
// Priority: cpu overrides cell output (host can inject at any time).
reg  [31:0] bus_addr;
reg  [31:0] bus_data;
reg         bus_valid;

// ── Wired-OR combiner ────────────────────────────────────────────────────────
// Combines all cell outputs in the combinational domain.
// Multiple cells writing the same address: data is OR'd (wired-OR bus).
// Multiple cells writing different addresses: last-writer wins for address.
// The compiler ensures only one cell writes per address per tick.
reg [31:0] or_addr;
reg [31:0] or_data;
reg        or_valid;

integer i;
always @(*) begin
    or_addr  = 32'h0;
    or_data  = 32'h0;
    or_valid = 1'b0;
    for (i = 0; i < NUM_CELLS; i = i + 1) begin
        if (cell_out_valid[i]) begin
            or_addr = cell_out_addr[i];
            or_data = or_data | cell_out_data[i];
            or_valid = 1'b1;
        end
    end
end

// ── Counters ──────────────────────────────────────────────────────────────────
reg [31:0] cycles;
assign cycle_count = cycles;

reg [15:0] armed;
assign armed_count = armed;

always @(*) begin
    armed = 0;
    for (i = 0; i < NUM_CELLS; i = i + 1)
        if (cell_dbg_armed[i]) armed = armed + 16'd1;
end

// start_flags_out: echo current start_flag state (directly from start_flags_in
// since start_flag is a combinational input to each cell)
assign start_flags_out = start_flags_in;

// ── Main clock process ────────────────────────────────────────────────────────
// Sequencing:
//   Each posedge clk:
//     1. Cells drain output_ff → cell_out_addr/data/valid (happens inside cells)
//     2. OR combiner assembles wired-OR result (combinational, already done)
//     3. This always block decides what goes on the bus NEXT cycle
//     4. Bus is registered — cells see it on NEXT posedge clk
//
// The cell's always block and this block both fire on posedge clk.
// Nonblocking assignments mean: cells drain THIS tick, bus is updated THIS tick,
// and cells load the NEW bus values from it — all on the same edge.
// Downstream cells therefore receive the upstream cell's output immediately.

always @(posedge clk) begin
    if (rst) begin
        bus_addr  <= 32'h0;
        bus_data  <= 32'h0;
        bus_valid <= 1'b0;
        out_valid <= 1'b0;
        out_addr  <= 32'h0;
        out_data  <= 32'h0;
        cycles    <= 32'h0;
    end else if (freeze) begin
        bus_valid <= 1'b0;
        out_valid <= 1'b0;
        // Do not increment cycles during freeze — makes cycle_count meaningful
    end else begin
        cycles    <= cycles + 1;
        out_valid <= 1'b0;

        if (cpu_valid) begin
            // Host injects directly — takes priority over cell output
            bus_addr  <= cpu_addr;
            bus_data  <= cpu_data;
            bus_valid <= 1'b1;
            // Host traffic is also forwarded to downstream (cpu_inject intended use)
        end else if (or_valid) begin
            // Cell output: drive bus so downstream cells can receive it
            bus_addr  <= or_addr;
            bus_data  <= or_data;
            bus_valid <= 1'b1;
            // Forward to host for observability
            out_addr  <= or_addr;
            out_data  <= or_data;
            out_valid <= 1'b1;
        end else begin
            bus_valid <= 1'b0;
        end
    end
end

// ── Cell instantiation ────────────────────────────────────────────────────────
// Each cell:
//   - sees the shared bus (bus_addr, bus_data, bus_valid)
//   - has its start_flag driven directly from start_flags_in[c]
//   - has a fixed CONFIG_ADDRESS = BASE_ADDRESS + c (synthesis-time only)
//   - outputs on cell_out_addr[c] / cell_out_data[c] / cell_out_valid[c]
//
// The start_flag is a dedicated hardware line (not a bus write).
// In a full FPGA system, fpga_bridge.py drives start_flags_in via a
// UART_SET_FLAGS command, asserting/clearing individual cell flags by index.

genvar c;
generate
    for (c = 0; c < NUM_CELLS; c = c + 1) begin : cell_array
        unicell_latch #(
            .CELL_ID        (c),
            .CONFIG_ADDRESS (BASE_ADDRESS + c)
        ) cell_inst (
            .clk        (clk),
            .rst        (rst),
            .freeze     (freeze),
            .bus_addr   (bus_addr),
            .bus_data   (bus_data),
            .bus_valid  (bus_valid),
            .start_flag (start_flags_in[c]),
            .out_addr   (cell_out_addr[c]),
            .out_data   (cell_out_data[c]),
            .out_valid  (cell_out_valid[c]),
            .dbg_gate_state   (cell_dbg_gs[c]),
            .dbg_input_addr   (cell_dbg_ia[c]),
            .dbg_output_addr  (cell_dbg_oa[c]),
            .dbg_input_b_addr (),
            .dbg_armed        (cell_dbg_armed[c]),
            .dbg_frozen       (cell_dbg_frozen[c]),
            .dbg_input_valid  (cell_dbg_iv[c]),
            .dbg_output_valid (cell_dbg_ov[c]),
            .dbg_b_valid      (cell_dbg_bv[c])
        );
    end
endgenerate

endmodule
