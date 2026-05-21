// top_kintex7.v — Imago UniCell Top Level for Kintex-7 (YZCA-00338-104)
// openXC7 toolchain — yosys + nextpnr-xilinx
//
// Board: Dual XC7K480T PCIe accelerator card
// Board files: github.com/TiferKing/ypcb_00338_1p1_hack
// Toolchain: openXC7 (yosys 0.44, nextpnr-xilinx)
// Programming: Vivado Hardware Manager via Xilinx Platform USB Cable
//
// Clock: External differential clock from board (see XDC for pin)
//        Using IBUFDS + BUFG, targeting 100-200 MHz
//
// UART: Via board USB/UART pins (see XDC)
//
// Resource estimate at NUM_CELLS=10:
//   ~10 * 100 LUTs per cell = ~1000 LUTs
//   K480T has 297,600 LUTs — 10 cells is <0.01%
//   Headroom for thousands of cells confirmed after first build
//
// NUM_CELLS progression plan:
//   10    — initial bring-up, size measurement
//   256   — equivalent to iCEBreaker full spec
//   1024  — first meaningful array
//   4096  — comfortable K480T usage (~1.4%)
//   16384 — large array (~5.5%)
//   65536 — one full block (~22%)
//   ~270K — estimated maximum single-device fit

`default_nettype none

module top (
    // Clock — differential input (LVDS from board)
    input  wire CLK_P,
    input  wire CLK_N,

    // UART
    input  wire UART_RX,
    output wire UART_TX,

    // Reset button (active low)
    input  wire BTN_RST_N,

    // Status LEDs
    output wire LED0,
    output wire LED1,
    output wire LED2,
    output wire LED3
);

// ── Clock buffer — differential → single ended ────────────────────────────
wire CLK_unbuf;
wire CLK;

IBUFDS #(
    .DIFF_TERM   ("FALSE"),
    .IBUF_LOW_PWR("TRUE"),
    .IOSTANDARD  ("LVDS")
) clk_ibuf (
    .I  (CLK_P),
    .IB (CLK_N),
    .O  (CLK_unbuf)
);

BUFG clk_bufg (
    .I(CLK_unbuf),
    .O(CLK)
);

// ── Reset ─────────────────────────────────────────────────────────────────
wire rst = ~BTN_RST_N;

// ── Wires between bridge and array ───────────────────────────────────────
wire [31:0] cpu_cmd, cpu_addr, cpu_data;
wire        cpu_valid, array_rst_req;
wire [31:0] cmd_bus_w  = cpu_cmd;
wire [31:0] cmd_data_w = cpu_data;
wire        cmd_valid_w = cpu_valid;
wire [31:0] out_addr, out_data;
wire        out_valid;
wire [15:0] armed_count;
wire [31:0] cycle_count;

// ── Cell array — start with 10 cells for size measurement ────────────────
unicell_array #(
    .NUM_CELLS(10)
) array (
    .clk         (CLK),
    .rst         (rst | array_rst_req),
    .cmd_bus     (cmd_bus_w),
    .cmd_data    (cmd_data_w),
    .cmd_valid   (cmd_valid_w),
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
// CLK_FREQ: set to match actual clock frequency from XDC
// Start with 100MHz — adjust after measuring actual clock
uart_bridge #(
    .CLK_FREQ (100_000_000),
    .BAUD_RATE(115_200)
) bridge (
    .clk         (CLK),
    .rst         (rst),
    .uart_rx     (UART_RX),
    .uart_tx     (UART_TX),
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
// LED0: armed indicator (any cells armed)
// LED1: activity (out_valid fires)
// LED2: always on (power/design loaded indicator)
// LED3: spare
reg led0_r = 1'b0;
reg led1_r = 1'b0;
reg led2_r = 1'b1;

always @(posedge CLK) begin
    led0_r <= (armed_count > 0);
    led1_r <= out_valid;
end

assign LED0 = led0_r;
assign LED1 = led1_r;
assign LED2 = led2_r;
assign LED3 = 1'b0;

endmodule
