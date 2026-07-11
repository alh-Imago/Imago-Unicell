// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// clock_walk_top_a.v — THROWAWAY diagnostic bitstream, BUILD A of 2
// (points.md #30, PLAN Step 2)
//
// v3 (2026-07-11): the all-32-at-once build (v2) FAILED to fit --
// "Attempted to fit 32 IOPLL merge groups in 16 locations" (Quartus Fitter
// error 18218). This device (10AX066H2F34E2SG) has exactly 16 total
// IOPLL-capable hard-block locations, die-wide -- a genuine hardware resource
// limit, not a settings mistake. Confirmed and logged: points.md #30.
//
// Split into two builds of 12 (comfortable margin under 16) covering the 24
// NEW per-channel RX/REFCLKn candidates. The 8 already-tested dedicated
// CHT/CHB pins are deliberately excluded -- already exhaustively dead on all
// 4 legal I/O standards, on two independent physical cards (see points.md
// #30's "CONTROL TEST RESULT") -- no need to spend IOPLL locations re-testing
// them.
//
// THIS BUILD (A): the 12 per-channel candidates from banks 1C and 1D.
// BUILD B (clock_walk_top_b.v): the 12 per-channel candidates from banks 1E
// and 1F. Run both; only one of the two builds needs to find a lock.
//
// BUILD A CANDIDATES (10ax066_1_.xls "Pin List F34"):
//   bit0  GXBL1C_RX_CH0/REFCLK0 PIN_AL30 (p) / PIN_AL29 (n)
//   bit1  GXBL1C_RX_CH1/REFCLK1 PIN_AJ30 (p) / PIN_AJ29 (n)
//   bit2  GXBL1C_RX_CH2/REFCLK2 PIN_AG30 (p) / PIN_AG29 (n)
//   bit3  GXBL1C_RX_CH3/REFCLK3 PIN_AF32 (p) / PIN_AF31 (n)
//   bit4  GXBL1C_RX_CH4/REFCLK4 PIN_AE30 (p) / PIN_AE29 (n)
//   bit5  GXBL1C_RX_CH5/REFCLK5 PIN_AD32 (p) / PIN_AD31 (n)
//   bit6  GXBL1D_RX_CH0/REFCLK0 PIN_AC30 (p) / PIN_AC29 (n)
//   bit7  GXBL1D_RX_CH1/REFCLK1 PIN_AB32 (p) / PIN_AB31 (n)
//   bit8  GXBL1D_RX_CH2/REFCLK2 PIN_AA30 (p) / PIN_AA29 (n)
//   bit9  GXBL1D_RX_CH3/REFCLK3 PIN_Y32  (p) / PIN_Y31  (n)
//   bit10 GXBL1D_RX_CH4/REFCLK4 PIN_W30  (p) / PIN_W29  (n)
//   bit11 GXBL1D_RX_CH5/REFCLK5 PIN_V32  (p) / PIN_V31  (n)
// Pin assignments + I/O standard: fpga/quartus/clock_walk_a.qsf (companion).
// All default to HCSL to start -- if all 12 read dead, sweep the same 4 legal
// standards (HCSL/LVDS/LVPECL/CML) before concluding anything.
//
// IP REUSE: `fpll_ch0` (already generated, proven working) reused 12 times,
// no new IOPLL IP generation needed. ISSP probe: 32-bit cycle_count + 12-bit
// locked_bits = 44 bits (regenerate issp_clockwalk with probe width 44).
//
// v3.1 UPDATE (2026-07-11): Fitter rejected ALL 12 of these pins, not just
// one or two -- "Could not find a location with: IO_FUNCTION of GPIO" on
// every candidate. See points.md #30 for the full reassessment: this looks
// like a SYSTEMATIC limitation, not a couple of bad pin picks -- these
// per-channel RX/REFCLKn pins most likely only function as a refclk source
// WITHIN a real transceiver channel context (feeding that channel's own
// internal reference mux via Native PHY), not as a generic differential
// input a plain user-instantiated IOPLL can bind to directly. This build is
// PAUSED pending that reassessment -- do not spend more time on per-pin
// workarounds until the underlying approach is reconsidered.

`default_nettype none
`timescale 1ns / 1ps

module clock_walk_top_a (
    input  wire refclk_1c_rx0,   // PIN_AL30/AL29 -- bit0
    input  wire refclk_1c_rx1,   // PIN_AJ30/AJ29 -- bit1
    input  wire refclk_1c_rx2,   // PIN_AG30/AG29 -- bit2
    input  wire refclk_1c_rx3,   // PIN_AF32/AF31 -- bit3
    input  wire refclk_1c_rx4,   // PIN_AE30/AE29 -- bit4
    input  wire refclk_1c_rx5,   // PIN_AD32/AD31 -- bit5
    input  wire refclk_1d_rx0,   // PIN_AC30/AC29 -- bit6
    input  wire refclk_1d_rx1,   // PIN_AB32/AB31 -- bit7
    input  wire refclk_1d_rx2,   // PIN_AA30/AA29 -- bit8
    input  wire refclk_1d_rx3,   // PIN_Y32/Y31   -- bit9
    input  wire refclk_1d_rx4,   // PIN_W30/W29   -- bit10
    input  wire refclk_1d_rx5,   // PIN_V32/V31   -- bit11

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

fpll_ch0 u_fpll0  (.refclk(refclk_1c_rx0), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[0]));
fpll_ch0 u_fpll1  (.refclk(refclk_1c_rx1), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[1]));
fpll_ch0 u_fpll2  (.refclk(refclk_1c_rx2), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[2]));
fpll_ch0 u_fpll3  (.refclk(refclk_1c_rx3), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[3]));
fpll_ch0 u_fpll4  (.refclk(refclk_1c_rx4), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[4]));
fpll_ch0 u_fpll5  (.refclk(refclk_1c_rx5), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[5]));
fpll_ch0 u_fpll6  (.refclk(refclk_1d_rx0), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[6]));
fpll_ch0 u_fpll7  (.refclk(refclk_1d_rx1), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[7]));
fpll_ch0 u_fpll8  (.refclk(refclk_1d_rx2), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[8]));
fpll_ch0 u_fpll9  (.refclk(refclk_1d_rx3), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[9]));
fpll_ch0 u_fpll10 (.refclk(refclk_1d_rx4), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[10]));
fpll_ch0 u_fpll11 (.refclk(refclk_1d_rx5), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[11]));

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
