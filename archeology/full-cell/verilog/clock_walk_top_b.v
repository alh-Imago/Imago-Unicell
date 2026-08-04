// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// clock_walk_top_b.v — THROWAWAY diagnostic bitstream, BUILD B of 2
// (points.md #30, PLAN Step 2)
//
// Companion to clock_walk_top_a.v -- see that file's header for the full
// backstory (32-at-once build failed to fit: this device has exactly 16
// total IOPLL-capable hard-block locations, die-wide).
//
// THIS BUILD (B): the 12 per-channel candidates from banks 1E and 1F.
//
// BUILD B CANDIDATES (10ax066_1_.xls "Pin List F34"):
//   bit0  GXBL1E_RX_CH0/REFCLK0 PIN_U30  (p) / PIN_U29  (n)
//   bit1  GXBL1E_RX_CH1/REFCLK1 PIN_T32  (p) / PIN_T31  (n)
//   bit2  GXBL1E_RX_CH2/REFCLK2 PIN_R30  (p) / PIN_R29  (n)
//   bit3  GXBL1E_RX_CH3/REFCLK3 PIN_P32  (p) / PIN_P31  (n)
//   bit4  GXBL1E_RX_CH4/REFCLK4 PIN_N30  (p) / PIN_N29  (n)
//   bit5  GXBL1E_RX_CH5/REFCLK5 PIN_M32  (p) / PIN_M31  (n)
//   bit6  GXBL1F_RX_CH0/REFCLK0 PIN_L30  (p) / PIN_L29  (n)
//   bit7  GXBL1F_RX_CH1/REFCLK1 PIN_K32  (p) / PIN_K31  (n)
//   bit8  GXBL1F_RX_CH2/REFCLK2 PIN_J30  (p) / PIN_J29  (n)
//   bit9  GXBL1F_RX_CH3/REFCLK3 PIN_G30  (p) / PIN_G29  (n)
//   bit10 GXBL1F_RX_CH4/REFCLK4 PIN_E30  (p) / PIN_E29  (n)
//   bit11 GXBL1F_RX_CH5/REFCLK5 PIN_C30  (p) / PIN_C29  (n)
// Pin assignments + I/O standard: fpga/quartus/clock_walk_b.qsf (companion).
// All default to HCSL to start -- if all 12 read dead, sweep the same 4 legal
// standards (HCSL/LVDS/LVPECL/CML) before concluding anything.
//
// IP REUSE: `fpll_ch0` reused 12 times, no new IOPLL IP generation needed.
// ISSP probe: 32-bit cycle_count + 12-bit locked_bits = 44 bits (same width
// as Build A -- can reuse the same issp_clockwalk.qsys if built in a separate
// project, or the same one if swapping top-level entities in one project).

`default_nettype none
`timescale 1ns / 1ps

module clock_walk_top_b (
    input  wire refclk_1e_rx0,   // PIN_U30/U29 -- bit0
    input  wire refclk_1e_rx1,   // PIN_T32/T31 -- bit1
    input  wire refclk_1e_rx2,   // PIN_R30/R29 -- bit2
    input  wire refclk_1e_rx3,   // PIN_P32/P31 -- bit3
    input  wire refclk_1e_rx4,   // PIN_N30/N29 -- bit4
    input  wire refclk_1e_rx5,   // PIN_M32/M31 -- bit5
    input  wire refclk_1f_rx0,   // PIN_L30/L29 -- bit6
    input  wire refclk_1f_rx1,   // PIN_K32/K31 -- bit7
    input  wire refclk_1f_rx2,   // PIN_J30/J29 -- bit8
    input  wire refclk_1f_rx3,   // PIN_G30/G29 -- bit9
    input  wire refclk_1f_rx4,   // PIN_E30/E29 -- bit10
    input  wire refclk_1f_rx5,   // PIN_C30/C29 -- bit11

    input  wire CLK_100M,       // board ref (PIN_E23) -- JTAG/ISSP domain only
    output wire LED0_N,         // lit (active low) once ANY candidate locks
    output wire LED1_N          // heartbeat blink -- confirms domain alive
);

reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire CLK = div_cnt[1];   // 25 MHz

reg [3:0] por_sr = 4'b0000;
always @(posedge CLK) por_sr <= {por_sr[2:0], 1'b1};
wire pll_rst_n = por_sr[3];   // active-low RST_N, real net (not a bare constant)

wire [11:0] locked_pll;

fpll_ch0 u_fpll0  (.refclk(refclk_1e_rx0), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[0]));
fpll_ch0 u_fpll1  (.refclk(refclk_1e_rx1), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[1]));
fpll_ch0 u_fpll2  (.refclk(refclk_1e_rx2), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[2]));
fpll_ch0 u_fpll3  (.refclk(refclk_1e_rx3), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[3]));
fpll_ch0 u_fpll4  (.refclk(refclk_1e_rx4), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[4]));
fpll_ch0 u_fpll5  (.refclk(refclk_1e_rx5), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[5]));
fpll_ch0 u_fpll6  (.refclk(refclk_1f_rx0), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[6]));
fpll_ch0 u_fpll7  (.refclk(refclk_1f_rx1), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[7]));
fpll_ch0 u_fpll8  (.refclk(refclk_1f_rx2), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[8]));
fpll_ch0 u_fpll9  (.refclk(refclk_1f_rx3), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[9]));
fpll_ch0 u_fpll10 (.refclk(refclk_1f_rx4), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[10]));
fpll_ch0 u_fpll11 (.refclk(refclk_1f_rx5), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[11]));

reg [11:0] locked_raw, locked_sync1, locked_sync2;
always @(posedge CLK) begin
    locked_raw   <= locked_pll;
    locked_sync1 <= locked_raw;
    locked_sync2 <= locked_sync1;
end
wire [11:0] locked_bits = locked_sync2;

reg [31:0] cycle_count = 32'h0;
always @(posedge CLK) cycle_count <= cycle_count + 32'h1;

wire [43:0] probe_word = {cycle_count, locked_bits};  // [43:12]=cycle_count, [11:0]=locked_bits
wire [0:0] source_unused;

issp_clockwalk clockwalk_issp (
    .source (source_unused),
    .probe  (probe_word)
);

reg [23:0] hb = 24'h0;
always @(posedge CLK) hb <= hb + 1'b1;
assign LED0_N = ~(|locked_bits);
assign LED1_N = ~hb[21];

endmodule
