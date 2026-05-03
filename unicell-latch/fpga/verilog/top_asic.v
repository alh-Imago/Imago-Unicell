// top_asic.v — Top Level for ASIC / Custom Silicon
// Claudette v2.1 / unicell-latch variant
//
// ASIC-facing top-level for the latch model. Board-specific constraints
// (pin names, clock frequency, UART baud) are the ONLY things that differ
// from the FPGA top files. The cell and array below are identical to the
// FPGA build.
//
// The latch model is the recommended variant for initial ASIC tapeout:
//   - Purely combinational gate tree (no negedge flip-flops)
//   - Single clock domain — simpler timing closure
//   - chain_latency(n) = n+1 ticks (predictable pipeline depth)
//   - No GS_FALL_EDGE / GS_OUT_POSEDGE edge-sensitivity concerns
//   - Cleanest timing report — gate tree between two FF banks only
//
// Intended for:
//   SKY130 open PDK (Tiny Tapeout 130nm) — recommended first tapeout
//   GF180 open PDK
//   Any 28nm–3nm foundry process via standard cell library
//
// Interface:
//   clk      — system clock (any frequency; parameterise CLK_FREQ below)
//   rst      — synchronous active-high reset
//   rx / tx  — UART host interface (replaceable with AXI-Lite, SPI, etc)
//
// The UART bridge is included as the default host interface because it
// requires no vendor IP and works from a simple serial connection. For
// production ASIC the bridge module can be swapped for AXI-Lite, PCIe,
// or any other bus protocol — the unicell_array_latch interface is unchanged.
//
// Parameterisation:
//   NUM_CELLS    — array size. Scale to fit die area.
//                  SKY130 Tiny Tapeout target: 8–32 cells.
//                  Full production ASIC: tens of thousands of cells.
//   BASE_ADDRESS — config address base (cells: BASE_ADDRESS..BASE_ADDRESS+N-1)
//   CLK_FREQ     — system clock frequency in Hz. Sets UART baud divisor.
//   BAUD_RATE    — UART baud rate. 115200 default.
//
// No vendor-specific primitives. Standard Verilog-2001 only.
//
// Tiny Tapeout 130nm estimate (latch model, per cell):
//   Standard cell area: ~1700 μm² per unicell_latch at 130nm
//   (slightly larger than standard variant due to two FF banks)
//   8-cell array: ~14,000 μm² (~0.014 mm²) — fits 1 tile
//   32-cell array: ~54,000 μm² (~0.054 mm²) — fits 2 tiles
//
// Bring-up sequence (matches MIGRATION_TODO iCEBreaker sequence):
//   1. LED blink via armed_count — verifies clock and reset
//   2. UART loopback — verifies host communication
//   3. 8 cells, NOT gate — verifies single cell compute
//   4. Two-input AND (SYNC_WAIT) — verifies B-input path
//   5. Bridge pair — verifies pond isolation
//   6. Scale to full array

`timescale 1ns / 1ps

module top_asic #(
    parameter NUM_CELLS    = 8,            // Scale for die area. 8 = SKY130 1-tile target.
    parameter BASE_ADDRESS = 0,            // Config address base
    parameter CLK_FREQ     = 50_000_000,   // 50MHz default; set to actual PLL output
    parameter BAUD_RATE    = 115_200       // UART baud rate
) (
    input  wire clk,        // System clock (single domain — latch model is cleanest here)
    input  wire rst,        // Synchronous reset (active high)

    // UART host interface — replace with AXI-Lite / SPI / custom for production
    input  wire rx,         // UART RX from host
    output wire tx,         // UART TX to host

    // Status outputs — connect to bond pads or leave unconnected
    output wire [15:0] armed_count,   // Number of armed cells
    output wire [31:0] cycle_count    // Execution cycle counter
);

// ── Internal wires ────────────────────────────────────────────────────────────
wire [31:0] cpu_addr, cpu_data;
wire        cpu_valid;
wire        array_rst_req, array_freeze_req;
wire [31:0] out_addr, out_data;
wire        out_valid;

// Start flags: the UART bridge drives these via SET_FLAGS command.
// In simulation the fpga_bridge drives start_flags_in directly.
// Width = NUM_CELLS. The bridge must be extended to expose this bus
// for production ASIC — current uart_bridge.v drives start_flag via
// the cell config sequence; the latch array exposes it as a port.
//
// For initial bring-up: tie start_flags_in to all-ones (all cells always
// armed) and verify cell behaviour before integrating flag control.
wire [NUM_CELLS-1:0] start_flags_in;
wire [NUM_CELLS-1:0] start_flags_out;

// TODO: connect start_flags_in to UART bridge flag control output.
// For bring-up stub: all cells armed. Replace with bridge output when
// uart_bridge.v is extended to support the latch model's flag bus.
assign start_flags_in = {NUM_CELLS{1'b1}};   // bring-up default: all armed

// ── UniCell latch array ───────────────────────────────────────────────────────
unicell_array_latch #(
    .NUM_CELLS   (NUM_CELLS),
    .BASE_ADDRESS(BASE_ADDRESS)
) array_inst (
    .clk            (clk),
    .rst            (rst | array_rst_req),
    .freeze         (array_freeze_req),
    .cpu_addr       (cpu_addr),
    .cpu_data       (cpu_data),
    .cpu_valid      (cpu_valid),
    .start_flags_in (start_flags_in),
    .start_flags_out(start_flags_out),
    .out_addr       (out_addr),
    .out_data       (out_data),
    .out_valid      (out_valid),
    .armed_count    (armed_count),
    .cycle_count    (cycle_count)
);

// ── UART bridge ───────────────────────────────────────────────────────────────
// Current uart_bridge.v is shared with standard/edge variants and uses the
// start_flag-via-config-sequence model. It remains usable for initial bring-up
// (cells are configured and armed via the config sequence).
// For full latch-model flag bus support, extend uart_bridge.v with a
// SET_FLAGS command that drives start_flags_in directly.
uart_bridge #(
    .CLK_FREQ (CLK_FREQ),
    .BAUD_RATE(BAUD_RATE)
) bridge_inst (
    .clk          (clk),
    .rst          (rst),
    .uart_rx      (rx),
    .uart_tx      (tx),
    .cpu_addr     (cpu_addr),
    .cpu_data     (cpu_data),
    .cpu_valid    (cpu_valid),
    .array_rst    (array_rst_req),
    .array_freeze (array_freeze_req),
    .out_addr     (out_addr),
    .out_data     (out_data),
    .out_valid    (out_valid),
    .armed_count  (armed_count),
    .cycle_count  (cycle_count)
);

endmodule
