// top_icebreaker.v — Top Level for iCEBreaker (iCE40UP5K)
// Claudette v1.2
//
// iCEBreaker pinout:
//   CLK:     P11 (12MHz)
//   UART_TX: 8   (PMOD connector)
//   UART_RX: 9   (PMOD connector)
//   LED_R:   11  (armed cells indicator)
//   LED_G:   37  (cell fired indicator)
//   BTN:     10  (reset)
//
// Resource usage at 64 cells:
//   LUTs:  ~5120 / 5280 (97% — tight but fits)
//   Regs:  ~2048 / 5280
//   BRAM:  0 / 30
//
// Reduce NUM_CELLS to 32 for comfortable headroom.
// Increase to 256 for Basys 3 / Arty A7.
//
// Build with open source toolchain:
//   yosys -p "synth_ice40 -top top -json top.json" top_icebreaker.v unicell_array.v unicell.v uart_bridge.v
//   nextpnr-ice40 --up5k --package sg48 --json top.json --asc top.asc --pcf icebreaker.pcf
//   icepack top.asc top.bin
//   iceprog top.bin

`timescale 1ns / 1ps

module top (
    input  wire CLK,        // 12MHz system clock
    input  wire BTN_N,      // Reset button (active low)
    input  wire RX,         // UART RX
    output wire TX,         // UART TX
    output wire LEDR_N,     // Red LED (active low) — armed indicator
    output wire LEDG_N      // Green LED (active low) — fired indicator
);

parameter NUM_CELLS = 64;

wire rst = ~BTN_N;

// ── UniCell array ─────────────────────────────────────────────────────────────
wire [31:0] cpu_addr, cpu_data;
wire        cpu_valid, array_rst_req;
wire [31:0] out_addr, out_data;
wire        out_valid;
wire [15:0] armed_count;
wire [31:0] cycle_count;

unicell_array #(
    .NUM_CELLS(NUM_CELLS)
) array (
    .clk        (CLK),
    .rst        (rst | array_rst_req),
    .freeze     (1'b0),             // Freeze driven low for bring-up
                                    // Connect to UART bridge command later
    .cpu_addr   (cpu_addr),
    .cpu_data   (cpu_data),
    .cpu_valid  (cpu_valid),
    .cpu_inject (1'b0),
    .out_addr   (out_addr),
    .out_data   (out_data),
    .out_valid  (out_valid),
    .armed_count(armed_count),
    .cycle_count(cycle_count)
);

// ── UART bridge ───────────────────────────────────────────────────────────────
uart_bridge #(
    .CLK_FREQ (12_000_000),
    .BAUD_RATE(115_200)
) bridge (
    .clk        (CLK),
    .rst        (rst),
    .uart_rx    (RX),
    .uart_tx    (TX),
    .cpu_addr   (cpu_addr),
    .cpu_data   (cpu_data),
    .cpu_valid  (cpu_valid),
    .array_rst  (array_rst_req),
    .out_addr   (out_addr),
    .out_data   (out_data),
    .out_valid  (out_valid),
    .armed_count(armed_count),
    .cycle_count(cycle_count)
);

// ── Status LEDs ───────────────────────────────────────────────────────────────
// Red LED: any cells armed
assign LEDR_N = (armed_count == 0);

// Green LED: a cell fired this cycle (blinks on activity)
reg [23:0] fired_stretch;
always @(posedge CLK) begin
    if (out_valid) fired_stretch <= 24'hFFFFFF;
    else if (fired_stretch > 0) fired_stretch <= fired_stretch - 1;
end
assign LEDG_N = (fired_stretch == 0);

endmodule
