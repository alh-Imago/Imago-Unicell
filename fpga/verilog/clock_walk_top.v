// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// clock_walk_top.v — THROWAWAY diagnostic bitstream (points.md #30, PLAN Step 2)
// v2 (2026-07-11): expanded from 8 to ALL 32 candidate refclk pins.
//
// GOAL: identify which of the 32 candidate PCIe refclk pins on
// 10AX066H2F34E2SG actually carries the host's 100 MHz reference.
//
// WHY 32, NOT 8: the first version only tested the 8 pins dedicated
// exclusively to refclk (`REFCLK_GXBL1x_CHT/CHB`). A control test proved this
// board design doesn't route refclk to any of those 8 (two independent
// physical cards -- one proven healthy via live PCIe enumeration seconds
// before testing -- both read zero locked across all 8 pins x all 4 legal I/O
// standards; see points.md #30's "CONTROL TEST RESULT"). Intel's own pin
// table for this device (10ax066_1_.xls, "Pin List F34") reveals each
// transceiver bank ALSO has 6 more pins that double as per-channel refclk
// inputs (every RX channel pin doubles as REFCLK0-5 for its bank) -- 24 more
// candidates, previously untested. This version covers all 32.
//
// METHOD (Option B from points.md #30 -- PREFERRED over free-running counters):
// instantiate one IOPLL per candidate refclk pin, read each IOPLL's `locked`
// output over JTAG. A PLL only locks on a genuine, present clock -- a clean,
// level-stable signal, unlike a free-running counter (which needs careful
// two-sample-and-diff handling and can give a false "it changed" read on a
// torn/metastable cross-domain sample). `locked` only needs a simple 2-flop
// synchronizer into the JTAG-adjacent domain, which this file provides.
//
// ALL 32 CANDIDATES (10ax066_1_.xls "Pin List F34", CONFIRMED for this exact
// device/package -- not inferred):
//   bit0  REFCLK_GXBL1C_CHT     PIN_AD28 (p) / PIN_AD27 (n)  [dedicated, tested v1]
//   bit1  GXBL1C_RX_CH0/REFCLK0 PIN_AL30 (p) / PIN_AL29 (n)  [per-channel, NEW]
//   bit2  GXBL1C_RX_CH1/REFCLK1 PIN_AJ30 (p) / PIN_AJ29 (n)  [per-channel, NEW]
//   bit3  GXBL1C_RX_CH2/REFCLK2 PIN_AG30 (p) / PIN_AG29 (n)  [per-channel, NEW]
//   bit4  GXBL1C_RX_CH3/REFCLK3 PIN_AF32 (p) / PIN_AF31 (n)  [per-channel, NEW]
//   bit5  GXBL1C_RX_CH4/REFCLK4 PIN_AE30 (p) / PIN_AE29 (n)  [per-channel, NEW]
//   bit6  GXBL1C_RX_CH5/REFCLK5 PIN_AD32 (p) / PIN_AD31 (n)  [per-channel, NEW]
//   bit7  REFCLK_GXBL1C_CHB     PIN_AF28 (p) / PIN_AF27 (n)  [dedicated, tested v1]
//   bit8  REFCLK_GXBL1D_CHT     PIN_Y28  (p) / PIN_Y27  (n)  [dedicated, tested v1]
//   bit9  GXBL1D_RX_CH0/REFCLK0 PIN_AC30 (p) / PIN_AC29 (n)  [per-channel, NEW]
//   bit10 GXBL1D_RX_CH1/REFCLK1 PIN_AB32 (p) / PIN_AB31 (n)  [per-channel, NEW]
//   bit11 GXBL1D_RX_CH2/REFCLK2 PIN_AA30 (p) / PIN_AA29 (n)  [per-channel, NEW]
//   bit12 GXBL1D_RX_CH3/REFCLK3 PIN_Y32  (p) / PIN_Y31  (n)  [per-channel, NEW]
//   bit13 GXBL1D_RX_CH4/REFCLK4 PIN_W30  (p) / PIN_W29  (n)  [per-channel, NEW]
//   bit14 GXBL1D_RX_CH5/REFCLK5 PIN_V32  (p) / PIN_V31  (n)  [per-channel, NEW]
//   bit15 REFCLK_GXBL1D_CHB     PIN_AB28 (p) / PIN_AB27 (n)  [dedicated, tested v1 --
//                                                             "strongest candidate" that wasn't]
//   bit16 REFCLK_GXBL1E_CHT     PIN_T28  (p) / PIN_T27  (n)  [dedicated, tested v1]
//   bit17 GXBL1E_RX_CH0/REFCLK0 PIN_U30  (p) / PIN_U29  (n)  [per-channel, NEW]
//   bit18 GXBL1E_RX_CH1/REFCLK1 PIN_T32  (p) / PIN_T31  (n)  [per-channel, NEW]
//   bit19 GXBL1E_RX_CH2/REFCLK2 PIN_R30  (p) / PIN_R29  (n)  [per-channel, NEW]
//   bit20 GXBL1E_RX_CH3/REFCLK3 PIN_P32  (p) / PIN_P31  (n)  [per-channel, NEW]
//   bit21 GXBL1E_RX_CH4/REFCLK4 PIN_N30  (p) / PIN_N29  (n)  [per-channel, NEW]
//   bit22 GXBL1E_RX_CH5/REFCLK5 PIN_M32  (p) / PIN_M31  (n)  [per-channel, NEW]
//   bit23 REFCLK_GXBL1E_CHB     PIN_V28  (p) / PIN_V27  (n)  [dedicated, tested v1]
//   bit24 REFCLK_GXBL1F_CHT     PIN_M28  (p) / PIN_M27  (n)  [dedicated, tested v1]
//   bit25 GXBL1F_RX_CH0/REFCLK0 PIN_L30  (p) / PIN_L29  (n)  [per-channel, NEW]
//   bit26 GXBL1F_RX_CH1/REFCLK1 PIN_K32  (p) / PIN_K31  (n)  [per-channel, NEW]
//   bit27 GXBL1F_RX_CH2/REFCLK2 PIN_J30  (p) / PIN_J29  (n)  [per-channel, NEW]
//   bit28 GXBL1F_RX_CH3/REFCLK3 PIN_G30  (p) / PIN_G29  (n)  [per-channel, NEW]
//   bit29 GXBL1F_RX_CH4/REFCLK4 PIN_E30  (p) / PIN_E29  (n)  [per-channel, NEW]
//   bit30 GXBL1F_RX_CH5/REFCLK5 PIN_C30  (p) / PIN_C29  (n)  [per-channel, NEW]
//   bit31 REFCLK_GXBL1F_CHB     PIN_P28  (p) / PIN_P27  (n)  [dedicated, tested v1]
// Pin assignments + I/O standard: fpga/quartus/clock_walk.qsf (companion file).
// Default I/O standard set to HCSL for the 24 new pins (same starting point as
// the original 8-pin sweep) -- if all read dead on HCSL, sweep the same 4
// legal standards (HCSL/LVDS/LVPECL/CML) before concluding anything, same
// caution as before.
//
// IP REUSE -- NO NEW IOPLL IP GENERATION NEEDED: `fpll_ch0` (already generated
// in Platform Designer for v1, proven working) is a plain Verilog module once
// generated -- it can be instantiated repeatedly under different instance
// names, each wired to a different pin, exactly like any other module. All 32
// candidates below reuse the SAME `fpll_ch0` module. No need to generate 24
// more separate IOPLL IP variations.
//
// ISSP: same single instance as v1, just a WIDER PROBE (64 bits instead of 40
// -- locked_bits grows from 8 to 32 bits, cycle_count stays 32 bits). No new
// ISSP channels/instances needed -- widen the existing `issp_clockwalk.qsys`
// probe width parameter from 40 to 64 in Platform Designer and regenerate,
// same step as the v1 8->40 bit widening.

`default_nettype none
`timescale 1ns / 1ps

module clock_walk_top (
    // Bank 1C (8 pins: 1 dedicated CHT + 6 per-channel + 1 dedicated CHB)
    input  wire refclk_1c_cht,   // PIN_AD28/AD27 -- bit0
    input  wire refclk_1c_rx0,   // PIN_AL30/AL29 -- bit1  NEW
    input  wire refclk_1c_rx1,   // PIN_AJ30/AJ29 -- bit2  NEW
    input  wire refclk_1c_rx2,   // PIN_AG30/AG29 -- bit3  NEW
    input  wire refclk_1c_rx3,   // PIN_AF32/AF31 -- bit4  NEW
    input  wire refclk_1c_rx4,   // PIN_AE30/AE29 -- bit5  NEW
    input  wire refclk_1c_rx5,   // PIN_AD32/AD31 -- bit6  NEW
    input  wire refclk_1c_chb,   // PIN_AF28/AF27 -- bit7

    // Bank 1D
    input  wire refclk_1d_cht,   // PIN_Y28/Y27   -- bit8
    input  wire refclk_1d_rx0,   // PIN_AC30/AC29 -- bit9  NEW
    input  wire refclk_1d_rx1,   // PIN_AB32/AB31 -- bit10 NEW
    input  wire refclk_1d_rx2,   // PIN_AA30/AA29 -- bit11 NEW
    input  wire refclk_1d_rx3,   // PIN_Y32/Y31   -- bit12 NEW
    input  wire refclk_1d_rx4,   // PIN_W30/W29   -- bit13 NEW
    input  wire refclk_1d_rx5,   // PIN_V32/V31   -- bit14 NEW
    input  wire refclk_1d_chb,   // PIN_AB28/AB27 -- bit15 ("strongest candidate" that wasn't)

    // Bank 1E
    input  wire refclk_1e_cht,   // PIN_T28/T27   -- bit16
    input  wire refclk_1e_rx0,   // PIN_U30/U29   -- bit17 NEW
    input  wire refclk_1e_rx1,   // PIN_T32/T31   -- bit18 NEW
    input  wire refclk_1e_rx2,   // PIN_R30/R29   -- bit19 NEW
    input  wire refclk_1e_rx3,   // PIN_P32/P31   -- bit20 NEW
    input  wire refclk_1e_rx4,   // PIN_N30/N29   -- bit21 NEW
    input  wire refclk_1e_rx5,   // PIN_M32/M31   -- bit22 NEW
    input  wire refclk_1e_chb,   // PIN_V28/V27   -- bit23

    // Bank 1F
    input  wire refclk_1f_cht,   // PIN_M28/M27   -- bit24
    input  wire refclk_1f_rx0,   // PIN_L30/L29   -- bit25 NEW
    input  wire refclk_1f_rx1,   // PIN_K32/K31   -- bit26 NEW
    input  wire refclk_1f_rx2,   // PIN_J30/J29   -- bit27 NEW
    input  wire refclk_1f_rx3,   // PIN_G30/G29   -- bit28 NEW
    input  wire refclk_1f_rx4,   // PIN_E30/E29   -- bit29 NEW
    input  wire refclk_1f_rx5,   // PIN_C30/C29   -- bit30 NEW
    input  wire refclk_1f_chb,   // PIN_P28/P27   -- bit31

    input  wire CLK_100M,       // board ref (PIN_E23) -- drives the ISSP/JTAG domain only,
                                // completely independent of all 32 candidates under test
    output wire LED0_N,         // lit (active low) once ANY candidate locks
    output wire LED1_N          // heartbeat blink -- confirms this domain is alive at all
);

// ── JTAG/probe-side clock: same /4 divider pattern as every other top file ──
reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire CLK = div_cnt[1];   // 25 MHz, used only to clock the synchronizers + ISSP

// ── Power-on-reset generator (real net, not a constant -- see v1 history: a
// constant-tied reset gets optimized away and is still flagged "not properly
// connected" by Quartus's PLL connectivity checker). RST_N is active-low
// despite the plain `rst` port name. ──
reg [3:0] por_sr = 4'b0000;
always @(posedge CLK) por_sr <= {por_sr[2:0], 1'b1};
wire pll_rst_n = por_sr[3];

// ── 32 IOPLL instances, ALL reusing the single already-generated `fpll_ch0`
// module (see header -- no new IP generation needed). `locked` is the ONLY
// signal used from each. ──
wire [31:0] locked_pll;

fpll_ch0 u_fpll0  (.refclk(refclk_1c_cht), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[0]));
fpll_ch0 u_fpll1  (.refclk(refclk_1c_rx0), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[1]));
fpll_ch0 u_fpll2  (.refclk(refclk_1c_rx1), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[2]));
fpll_ch0 u_fpll3  (.refclk(refclk_1c_rx2), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[3]));
fpll_ch0 u_fpll4  (.refclk(refclk_1c_rx3), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[4]));
fpll_ch0 u_fpll5  (.refclk(refclk_1c_rx4), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[5]));
fpll_ch0 u_fpll6  (.refclk(refclk_1c_rx5), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[6]));
fpll_ch0 u_fpll7  (.refclk(refclk_1c_chb), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[7]));

fpll_ch0 u_fpll8  (.refclk(refclk_1d_cht), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[8]));
fpll_ch0 u_fpll9  (.refclk(refclk_1d_rx0), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[9]));
fpll_ch0 u_fpll10 (.refclk(refclk_1d_rx1), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[10]));
fpll_ch0 u_fpll11 (.refclk(refclk_1d_rx2), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[11]));
fpll_ch0 u_fpll12 (.refclk(refclk_1d_rx3), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[12]));
fpll_ch0 u_fpll13 (.refclk(refclk_1d_rx4), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[13]));
fpll_ch0 u_fpll14 (.refclk(refclk_1d_rx5), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[14]));
fpll_ch0 u_fpll15 (.refclk(refclk_1d_chb), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[15]));

fpll_ch0 u_fpll16 (.refclk(refclk_1e_cht), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[16]));
fpll_ch0 u_fpll17 (.refclk(refclk_1e_rx0), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[17]));
fpll_ch0 u_fpll18 (.refclk(refclk_1e_rx1), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[18]));
fpll_ch0 u_fpll19 (.refclk(refclk_1e_rx2), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[19]));
fpll_ch0 u_fpll20 (.refclk(refclk_1e_rx3), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[20]));
fpll_ch0 u_fpll21 (.refclk(refclk_1e_rx4), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[21]));
fpll_ch0 u_fpll22 (.refclk(refclk_1e_rx5), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[22]));
fpll_ch0 u_fpll23 (.refclk(refclk_1e_chb), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[23]));

fpll_ch0 u_fpll24 (.refclk(refclk_1f_cht), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[24]));
fpll_ch0 u_fpll25 (.refclk(refclk_1f_rx0), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[25]));
fpll_ch0 u_fpll26 (.refclk(refclk_1f_rx1), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[26]));
fpll_ch0 u_fpll27 (.refclk(refclk_1f_rx2), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[27]));
fpll_ch0 u_fpll28 (.refclk(refclk_1f_rx3), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[28]));
fpll_ch0 u_fpll29 (.refclk(refclk_1f_rx4), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[29]));
fpll_ch0 u_fpll30 (.refclk(refclk_1f_rx5), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[30]));
fpll_ch0 u_fpll31 (.refclk(refclk_1f_chb), .rst(pll_rst_n), .outclk_0(), .locked(locked_pll[31]));

// ── 2-flop synchronizer per locked bit into the CLK domain ──────────────────
reg [31:0] locked_raw, locked_sync1, locked_sync2;
always @(posedge CLK) begin
    locked_raw   <= locked_pll;
    locked_sync1 <= locked_raw;
    locked_sync2 <= locked_sync1;
end
wire [31:0] locked_bits = locked_sync2;  // bit N = candidate N per the header table

// ── Free-running cycle counter -- liveness check, read twice ~80ms apart
// (same idiom as every zone1_*.tcl script's "snapshot: cycle X -> Y OK"
// check). Not part of the refclk hunt itself. ──
reg [31:0] cycle_count = 32'h0;
always @(posedge CLK) cycle_count <= cycle_count + 32'h1;

// ── Minimal ISSP: 32 locked bits + 32-bit cycle counter = 64-bit probe. ────
// Same single instance as v1 -- WIDER PROBE, not more instances. No source
// needed (read-only). Regenerate issp_clockwalk.qsys with probe width = 64.
wire [63:0] probe_word = {cycle_count, locked_bits};  // [63:32]=cycle_count, [31:0]=locked_bits
wire [0:0] source_unused;

issp_clockwalk clockwalk_issp (
    .source (source_unused),
    .probe  (probe_word)
);

// ── Status LEDs -- a locked candidate is visible without even opening JTAG ──
reg [23:0] hb = 24'h0;
always @(posedge CLK) hb <= hb + 1'b1;
assign LED0_N = ~(|locked_bits);   // lit (low) once ANY bit locks
assign LED1_N = ~hb[21];           // ~12 Hz heartbeat -- confirms CLK_100M/div chain alive

endmodule
