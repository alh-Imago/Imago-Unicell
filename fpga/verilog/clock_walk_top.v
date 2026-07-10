// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// clock_walk_top.v — THROWAWAY diagnostic bitstream (points.md #30, PLAN Step 2)
//
// GOAL: identify which of the 8 candidate PCIe refclk pin pairs on
// 10AX066H2F34E2SG actually carries the host's 100 MHz reference. Exactly one
// should be alive (IEI ties the other 7 to GND per PCG-01017); if ALL EIGHT
// read dead, the conclusion is "check the I/O standard" (see header note
// below), NOT "none of them are wired" (docs/PCIE_ARRIA10_NOTES.md, points.md
// #30 -- both explicitly warn about this false-negative mode).
//
// METHOD (Option B from points.md #30 -- PREFERRED over free-running counters):
// instantiate one fPLL per candidate refclk pin, read each fPLL's `locked`
// output over JTAG. A PLL only locks on a genuine, present clock -- this is a
// clean, level-stable signal (unlike a free-running counter, which needs
// careful two-sample-and-diff handling and can give a false "it changed" read
// on a torn/metastable cross-domain sample). `locked` only needs a simple
// 2-flop synchronizer into the JTAG-adjacent domain, which this file provides.
//
// THE 8 CANDIDATES (docs/PCIE_ARRIA10_NOTES.md, CONFIRMED on the actual
// 10AX066H2F34E2SG via Quartus's own device database -- not inferred):
//   bit0  REFCLK_GXBL1C_CHT   PIN_AD28 (p) / PIN_AD27 (n)
//   bit1  REFCLK_GXBL1C_CHB   PIN_AF28 (p) / PIN_AF27 (n)
//   bit2  REFCLK_GXBL1D_CHT   PIN_Y28  (p) / PIN_Y27  (n)
//   bit3  REFCLK_GXBL1D_CHB   PIN_AB28 (p) / PIN_AB27 (n)  <- strongest single
//                                                             candidate (AN 750's
//                                                             natural-placement
//                                                             evidence, see notes)
//   bit4  REFCLK_GXBL1E_CHT   PIN_T28  (p) / PIN_T27  (n)
//   bit5  REFCLK_GXBL1E_CHB   PIN_V28  (p) / PIN_V27  (n)
//   bit6  REFCLK_GXBL1F_CHT   PIN_M28  (p) / PIN_M27  (n)
//   bit7  REFCLK_GXBL1F_CHB   PIN_P28  (p) / PIN_P27  (n)
// Pin assignments + HCSL I/O standard: fpga/quartus/clock_walk.qsf (companion file).
//
// CRITICAL -- GENERATE THE 8 fPLL IPs (IP Catalog -> PLL -> fPLL Intel FPGA IP,
// one per refclk, e.g. named fpll_ch0..fpll_ch7):
//   * Reference clock frequency = 100 MHz (the expected PCIe refclk rate)
//   * No output clock actually needs to be USED -- only `locked` matters. Pick
//     any legal output frequency (e.g. 100 MHz passthrough) to satisfy the IP
//     generator; it is never connected to anything downstream here.
//   * Do NOT wire refclk to an internal clk_0 source (same caution as the PCIe
//     HIP notes) -- it must be the actual candidate pin, or the test is
//     meaningless by construction.
//   * The generated module's ports are typically `refclk`, `locked`, `outclk_0`
//     (+ `rst`). RECONCILE the 8 instantiations below against whatever Quartus
//     actually generates -- port names drift slightly by IP version, same
//     caveat as unicell_issp_bridge.v's `issp` instance.
//
// This file deliberately has NO dependency on the unicell fabric (cell/array/
// zone) -- it is a standalone throwaway bitstream, built and flashed
// separately from the UniCell builds, purely to answer one board-wiring
// question over JTAG.

`default_nettype none
`timescale 1ns / 1ps

module clock_walk_top (
    input  wire refclk_1c_cht,  // PIN_AD28/AD27
    input  wire refclk_1c_chb,  // PIN_AF28/AF27
    input  wire refclk_1d_cht,  // PIN_Y28/Y27
    input  wire refclk_1d_chb,  // PIN_AB28/AB27 -- strongest single candidate
    input  wire refclk_1e_cht,  // PIN_T28/T27
    input  wire refclk_1e_chb,  // PIN_V28/V27
    input  wire refclk_1f_cht,  // PIN_M28/M27
    input  wire refclk_1f_chb,  // PIN_P28/P27
    input  wire CLK_100M,       // board ref (PIN_E23) -- drives the ISSP/JTAG domain only,
                                // completely independent of the 8 candidates under test
    output wire LED0_N,         // lit (active low) once ANY candidate locks -- a fast visual check
                                // before even opening quartus_stp
    output wire LED1_N          // heartbeat blink -- confirms this domain is alive at all
);

// ── JTAG/probe-side clock: same /4 divider pattern as every other top file ──
reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire CLK = div_cnt[1];   // 25 MHz, used only to clock the synchronizers + ISSP

// ── 8 fPLL instances, one per candidate. `locked` is the ONLY signal used. ──
// TEMPLATE -- reconcile port names against the actual Quartus-generated IP.
wire locked0, locked1, locked2, locked3, locked4, locked5, locked6, locked7;

fpll_ch0 u_fpll0 (.refclk(refclk_1c_cht), .rst(1'b0), .outclk_0(), .locked(locked0));
fpll_ch1 u_fpll1 (.refclk(refclk_1c_chb), .rst(1'b0), .outclk_0(), .locked(locked1));
fpll_ch2 u_fpll2 (.refclk(refclk_1d_cht), .rst(1'b0), .outclk_0(), .locked(locked2));
fpll_ch3 u_fpll3 (.refclk(refclk_1d_chb), .rst(1'b0), .outclk_0(), .locked(locked3));
fpll_ch4 u_fpll4 (.refclk(refclk_1e_cht), .rst(1'b0), .outclk_0(), .locked(locked4));
fpll_ch5 u_fpll5 (.refclk(refclk_1e_chb), .rst(1'b0), .outclk_0(), .locked(locked5));
fpll_ch6 u_fpll6 (.refclk(refclk_1f_cht), .rst(1'b0), .outclk_0(), .locked(locked6));
fpll_ch7 u_fpll7 (.refclk(refclk_1f_chb), .rst(1'b0), .outclk_0(), .locked(locked7));

// ── 2-flop synchronizer per locked bit into the CLK domain ──────────────────
// `locked` is a stable level once true (not a free-running value like a
// counter), so a simple double-flop is sufficient -- no Gray-coding/handshake
// needed, unlike Option A's counter-diff approach.
reg [7:0] locked_raw, locked_sync1, locked_sync2;
always @(posedge CLK) begin
    locked_raw   <= {locked7, locked6, locked5, locked4, locked3, locked2, locked1, locked0};
    locked_sync1 <= locked_raw;
    locked_sync2 <= locked_sync1;
end
wire [7:0] locked_bits = locked_sync2;  // bit N = candidate N above, stable in the CLK domain

// ── Minimal ISSP: probe-only, 8 bits. No source needed -- these are read-only. ──
// Generated as a Qsys system (issp_clockwalk.qsys) -- its instantiation
// template exposes ONLY `source`/`probe`, no external `source_clk` port (it
// clocks itself internally off the JTAG chain, unlike the raw `issp`
// megafunction used elsewhere in this repo). locked_bits is already
// double-flop-synchronized into the CLK domain above, so this is fine either
// way -- the bits are stable levels by the time they reach the probe.
wire [7:0] probe_word = locked_bits;
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
