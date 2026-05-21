// top_kintex7.v — Imago UniCell Top Level for Kintex-7 (YZCA-00338-104)
// openXC7 toolchain — yosys + nextpnr-xilinx
//
// Board:    Dual XC7K480T PCIe accelerator (xc7k480tffg1156-2)
// Clock:    50MHz single-ended AA28 (LVCMOS18)
// Reset:    R28 SW_RESET (active low, LVCMOS18)
// LEDs:     P30=Red, M30=Green, N30=Yellow (LVCMOS18)
// UART:     No dedicated UART pins — card is PCIe-only
//           Future: Xilinx PCIe DMA IP (see Xilinx Answer 65444)
//           For now: UART internally tied, not exposed as ports
//
// IIC pins N24/N25 connect to LM73 temperature sensor — NOT usable as UART
//
// NUM_CELLS=10: initial bring-up and resource measurement
// K480T has 74,650 slices / 477,760 logic cells
//
// Resource estimate progression (per cell ~100 LUTs):
//   10     → ~1,000 LUTs  (<0.01%)
//   1,000  → ~100K  LUTs  (~0.3%)
//   65,536 → one full 65K block (~22%)
//   ~270K  → estimated maximum single device

`default_nettype none

module top (
    input  wire CLK,
    input  wire BTN_RST_N,
    output wire LED0,        // Red    P30
    output wire LED1,        // Green  M30
    output wire LED2         // Yellow N30
);

// ── Reset ─────────────────────────────────────────────────────────────────
wire rst = ~BTN_RST_N;

// ── Clock buffer ──────────────────────────────────────────────────────────
wire CLK_buf;
BUFG clk_bufg (.I(CLK), .O(CLK_buf));

// ── UART stub — no physical pins on this card ─────────────────────────────
wire uart_rx_stub = 1'b1;  // idle high
wire uart_tx_stub;

// ── Wires between bridge and array ───────────────────────────────────────
wire [31:0] cpu_cmd, cpu_addr, cpu_data;
wire        cpu_valid, array_rst_req;
wire [31:0] out_addr, out_data;
wire        out_valid;
wire [15:0] armed_count;
wire [31:0] cycle_count;

// ── Cell array ────────────────────────────────────────────────────────────
unicell_array #(
    .NUM_CELLS(4180)
) array (
    .clk         (CLK_buf),
    .rst         (rst | array_rst_req),
    .cmd_bus     (cpu_cmd),
    .cmd_data    (cpu_data),
    .cmd_valid   (cpu_valid),
    .cpu_addr    (cpu_addr),
    .cpu_data    (cpu_data),
    .cpu_valid   (cpu_valid),
    .out_addr    (out_addr),
    .out_data    (out_data),
    .out_valid   (out_valid),
    .armed_count (armed_count),
    .cycle_count (cycle_count)
);

// ── UART bridge ───────────────────────────────────────────────────────────
uart_bridge #(
    .CLK_FREQ (50_000_000),
    .BAUD_RATE(115_200)
) bridge (
    .clk         (CLK_buf),
    .rst         (rst),
    .uart_rx     (uart_rx_stub),
    .uart_tx     (uart_tx_stub),
    .cpu_cmd     (cpu_cmd),
    .cpu_addr    (cpu_addr),
    .cpu_data    (cpu_data),
    .cpu_valid   (cpu_valid),
    .array_rst   (array_rst_req),
    .array_freeze(),
    .out_addr    (out_addr),
    .out_data    (out_data),
    .out_valid   (out_valid),
    .armed_count (armed_count),
    .cycle_count (cycle_count)
);

// ── Status LEDs ───────────────────────────────────────────────────────────
// LED0 Red:    any cells armed
// LED1 Green:  always on (design loaded)
// LED2 Yellow: output activity
reg led0_r = 1'b0;
reg led2_r = 1'b0;

always @(posedge CLK_buf) begin
    led0_r <= (armed_count > 0);
    led2_r <= out_valid;
end

assign LED0 = led0_r;
assign LED1 = 1'b1;
assign LED2 = led2_r;

endmodule
