// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// pcie_hip_test_top.v -- REAL hardware attempt (points.md #30 / PLAN Step 2)
//
// Wraps pcie_test_1 (the correctly-targeted, genuine hardware-mode PCIe Hard
// IP system -- confirmed real xcvr_tx_out/xcvr_rx_in serial pins, not a
// simulation stub) with the EXACT pin assignments Quartus's own Fitter
// already discovered when left unconstrained (see pcie_pin_check_top.v's
// result, points.md #30): refclk on PIN_AB28/AB27 (bank 1D, CML), lanes
// split across banks 1C (channels 0,1) and 1D (channels 2-7). Locked in
// explicitly via pcie_hip_test.qsf rather than left to auto-placement, so a
// future recompile can't silently pick something different.
//
// RESET: hip_ctl_npor / hip_ctl_pin_perst / reset_reset_n are all active-low
// (deasserted = HIGH) per their naming convention and PCIe's own PERST#
// polarity. Uses a real power-on-reset shift register, NOT a bare constant --
// the same lesson learned twice already this project (clock_walk_top.v's PLL
// reset): a constant-tied reset net gets optimized away and can be flagged
// as "not properly connected", or worse, silently do nothing useful. This one
// asserts reset for a few cycles after configuration, then releases and
// stays released.
//
// clk_clk is pcie_test_1's general/Avalon-side system clock, distinct from
// ref_clk_clk (the actual SERDES reference, a real differential pin). No PLL
// built for this first attempt -- clk_clk fed directly from the same proven
// CLK_100M input everything else in this project already uses.
//
// hip_pipe_* (the ~211-signal PIPE-level debug/observability bus) is left as
// plain undriven internal wires -- confirmed to compile cleanly against the
// REAL vendor IP this way already (pcie_pin_check_top.v). Genuine
// uncertainty, stated honestly: not fully confirmed whether any of these are
// true required inputs needing a specific non-floating value for correct
// real-hardware operation (as opposed to pure observability outputs) -- if
// the real hardware test behaves oddly, this bus is the first place to look.

module pcie_hip_test_top (
    input  wire CLK_100M,       // board ref, PIN_E23 -- proven pin, used all project
    input  wire ref_clk_clk,    // real PCIe refclk pin, PIN_AB28/AB27 (bank 1D), CML
    output wire LED0_N,         // heartbeat -- confirms this domain alive
    input  wire xcvr_rx_in0,
    input  wire xcvr_rx_in1,
    input  wire xcvr_rx_in2,
    input  wire xcvr_rx_in3,
    input  wire xcvr_rx_in4,
    input  wire xcvr_rx_in5,
    input  wire xcvr_rx_in6,
    input  wire xcvr_rx_in7,
    output wire xcvr_tx_out0,
    output wire xcvr_tx_out1,
    output wire xcvr_tx_out2,
    output wire xcvr_tx_out3,
    output wire xcvr_tx_out4,
    output wire xcvr_tx_out5,
    output wire xcvr_tx_out6,
    output wire xcvr_tx_out7
);

// ── Power-on-reset generator: real net, not a bare constant (see header). ──
reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire CLK = div_cnt[1];   // 25 MHz -- used for the reset generator + heartbeat only

reg [7:0] por_sr = 8'h00;
always @(posedge CLK) por_sr <= {por_sr[6:0], 1'b1};
wire released = por_sr[7];   // HIGH once released

// hip_ctl_npor, hip_ctl_pin_perst, reset_reset_n: all active-low, deasserted=HIGH
wire rst_n = released;

// Internal-only wires for the hip_pipe_* PIPE debug bus -- undriven,
// see header for the honest caveat on this.
wire hip_pipe_sim_pipe_pclk_in, hip_pipe_sim_pipe_rate, hip_pipe_sim_ltssmstate, hip_pipe_eidleinfersel0;
wire hip_pipe_eidleinfersel1, hip_pipe_eidleinfersel2, hip_pipe_eidleinfersel3, hip_pipe_eidleinfersel4;
wire hip_pipe_eidleinfersel5, hip_pipe_eidleinfersel6, hip_pipe_eidleinfersel7, hip_pipe_powerdown0;
wire hip_pipe_powerdown1, hip_pipe_powerdown2, hip_pipe_powerdown3, hip_pipe_powerdown4;
wire hip_pipe_powerdown5, hip_pipe_powerdown6, hip_pipe_powerdown7, hip_pipe_rxpolarity0;
wire hip_pipe_rxpolarity1, hip_pipe_rxpolarity2, hip_pipe_rxpolarity3, hip_pipe_rxpolarity4;
wire hip_pipe_rxpolarity5, hip_pipe_rxpolarity6, hip_pipe_rxpolarity7, hip_pipe_txcompl0;
wire hip_pipe_txcompl1, hip_pipe_txcompl2, hip_pipe_txcompl3, hip_pipe_txcompl4;
wire hip_pipe_txcompl5, hip_pipe_txcompl6, hip_pipe_txcompl7, hip_pipe_txdata0;
wire hip_pipe_txdata1, hip_pipe_txdata2, hip_pipe_txdata3, hip_pipe_txdata4;
wire hip_pipe_txdata5, hip_pipe_txdata6, hip_pipe_txdata7, hip_pipe_txdatak0;
wire hip_pipe_txdatak1, hip_pipe_txdatak2, hip_pipe_txdatak3, hip_pipe_txdatak4;
wire hip_pipe_txdatak5, hip_pipe_txdatak6, hip_pipe_txdatak7, hip_pipe_txdetectrx0;
wire hip_pipe_txdetectrx1, hip_pipe_txdetectrx2, hip_pipe_txdetectrx3, hip_pipe_txdetectrx4;
wire hip_pipe_txdetectrx5, hip_pipe_txdetectrx6, hip_pipe_txdetectrx7, hip_pipe_txelecidle0;
wire hip_pipe_txelecidle1, hip_pipe_txelecidle2, hip_pipe_txelecidle3, hip_pipe_txelecidle4;
wire hip_pipe_txelecidle5, hip_pipe_txelecidle6, hip_pipe_txelecidle7, hip_pipe_txdeemph0;
wire hip_pipe_txdeemph1, hip_pipe_txdeemph2, hip_pipe_txdeemph3, hip_pipe_txdeemph4;
wire hip_pipe_txdeemph5, hip_pipe_txdeemph6, hip_pipe_txdeemph7, hip_pipe_txmargin0;
wire hip_pipe_txmargin1, hip_pipe_txmargin2, hip_pipe_txmargin3, hip_pipe_txmargin4;
wire hip_pipe_txmargin5, hip_pipe_txmargin6, hip_pipe_txmargin7, hip_pipe_txswing0;
wire hip_pipe_txswing1, hip_pipe_txswing2, hip_pipe_txswing3, hip_pipe_txswing4;
wire hip_pipe_txswing5, hip_pipe_txswing6, hip_pipe_txswing7, hip_pipe_phystatus0;
wire hip_pipe_phystatus1, hip_pipe_phystatus2, hip_pipe_phystatus3, hip_pipe_phystatus4;
wire hip_pipe_phystatus5, hip_pipe_phystatus6, hip_pipe_phystatus7, hip_pipe_rxdata0;
wire hip_pipe_rxdata1, hip_pipe_rxdata2, hip_pipe_rxdata3, hip_pipe_rxdata4;
wire hip_pipe_rxdata5, hip_pipe_rxdata6, hip_pipe_rxdata7, hip_pipe_rxdatak0;
wire hip_pipe_rxdatak1, hip_pipe_rxdatak2, hip_pipe_rxdatak3, hip_pipe_rxdatak4;
wire hip_pipe_rxdatak5, hip_pipe_rxdatak6, hip_pipe_rxdatak7, hip_pipe_rxelecidle0;
wire hip_pipe_rxelecidle1, hip_pipe_rxelecidle2, hip_pipe_rxelecidle3, hip_pipe_rxelecidle4;
wire hip_pipe_rxelecidle5, hip_pipe_rxelecidle6, hip_pipe_rxelecidle7, hip_pipe_rxstatus0;
wire hip_pipe_rxstatus1, hip_pipe_rxstatus2, hip_pipe_rxstatus3, hip_pipe_rxstatus4;
wire hip_pipe_rxstatus5, hip_pipe_rxstatus6, hip_pipe_rxstatus7, hip_pipe_rxvalid0;
wire hip_pipe_rxvalid1, hip_pipe_rxvalid2, hip_pipe_rxvalid3, hip_pipe_rxvalid4;
wire hip_pipe_rxvalid5, hip_pipe_rxvalid6, hip_pipe_rxvalid7, hip_pipe_rxdataskip0;
wire hip_pipe_rxdataskip1, hip_pipe_rxdataskip2, hip_pipe_rxdataskip3, hip_pipe_rxdataskip4;
wire hip_pipe_rxdataskip5, hip_pipe_rxdataskip6, hip_pipe_rxdataskip7, hip_pipe_rxblkst0;
wire hip_pipe_rxblkst1, hip_pipe_rxblkst2, hip_pipe_rxblkst3, hip_pipe_rxblkst4;
wire hip_pipe_rxblkst5, hip_pipe_rxblkst6, hip_pipe_rxblkst7, hip_pipe_rxsynchd0;
wire hip_pipe_rxsynchd1, hip_pipe_rxsynchd2, hip_pipe_rxsynchd3, hip_pipe_rxsynchd4;
wire hip_pipe_rxsynchd5, hip_pipe_rxsynchd6, hip_pipe_rxsynchd7, hip_pipe_currentcoeff0;
wire hip_pipe_currentcoeff1, hip_pipe_currentcoeff2, hip_pipe_currentcoeff3, hip_pipe_currentcoeff4;
wire hip_pipe_currentcoeff5, hip_pipe_currentcoeff6, hip_pipe_currentcoeff7, hip_pipe_currentrxpreset0;
wire hip_pipe_currentrxpreset1, hip_pipe_currentrxpreset2, hip_pipe_currentrxpreset3, hip_pipe_currentrxpreset4;
wire hip_pipe_currentrxpreset5, hip_pipe_currentrxpreset6, hip_pipe_currentrxpreset7, hip_pipe_txsynchd0;
wire hip_pipe_txsynchd1, hip_pipe_txsynchd2, hip_pipe_txsynchd3, hip_pipe_txsynchd4;
wire hip_pipe_txsynchd5, hip_pipe_txsynchd6, hip_pipe_txsynchd7, hip_pipe_txblkst0;
wire hip_pipe_txblkst1, hip_pipe_txblkst2, hip_pipe_txblkst3, hip_pipe_txblkst4;
wire hip_pipe_txblkst5, hip_pipe_txblkst6, hip_pipe_txblkst7, hip_pipe_txdataskip0;
wire hip_pipe_txdataskip1, hip_pipe_txdataskip2, hip_pipe_txdataskip3, hip_pipe_txdataskip4;
wire hip_pipe_txdataskip5, hip_pipe_txdataskip6, hip_pipe_txdataskip7, hip_pipe_rate0;
wire hip_pipe_rate1, hip_pipe_rate2, hip_pipe_rate3, hip_pipe_rate4;
wire hip_pipe_rate5, hip_pipe_rate6, hip_pipe_rate7;

pcie_test_1 u0 (
    .clk_clk           (CLK_100M),
    .reset_reset_n     (rst_n),
    .ref_clk_clk       (ref_clk_clk),
    .hip_ctl_npor      (rst_n),
    .hip_ctl_pin_perst (rst_n),
    .xcvr_rx_in0      (xcvr_rx_in0),
    .xcvr_rx_in1      (xcvr_rx_in1),
    .xcvr_rx_in2      (xcvr_rx_in2),
    .xcvr_rx_in3      (xcvr_rx_in3),
    .xcvr_rx_in4      (xcvr_rx_in4),
    .xcvr_rx_in5      (xcvr_rx_in5),
    .xcvr_rx_in6      (xcvr_rx_in6),
    .xcvr_rx_in7      (xcvr_rx_in7),
    .xcvr_tx_out0     (xcvr_tx_out0),
    .xcvr_tx_out1     (xcvr_tx_out1),
    .xcvr_tx_out2     (xcvr_tx_out2),
    .xcvr_tx_out3     (xcvr_tx_out3),
    .xcvr_tx_out4     (xcvr_tx_out4),
    .xcvr_tx_out5     (xcvr_tx_out5),
    .xcvr_tx_out6     (xcvr_tx_out6),
    .xcvr_tx_out7     (xcvr_tx_out7),
    .hip_pipe_sim_pipe_pclk_in (hip_pipe_sim_pipe_pclk_in),
    .hip_pipe_sim_pipe_rate (hip_pipe_sim_pipe_rate),
    .hip_pipe_sim_ltssmstate (hip_pipe_sim_ltssmstate),
    .hip_pipe_eidleinfersel0 (hip_pipe_eidleinfersel0),
    .hip_pipe_eidleinfersel1 (hip_pipe_eidleinfersel1),
    .hip_pipe_eidleinfersel2 (hip_pipe_eidleinfersel2),
    .hip_pipe_eidleinfersel3 (hip_pipe_eidleinfersel3),
    .hip_pipe_eidleinfersel4 (hip_pipe_eidleinfersel4),
    .hip_pipe_eidleinfersel5 (hip_pipe_eidleinfersel5),
    .hip_pipe_eidleinfersel6 (hip_pipe_eidleinfersel6),
    .hip_pipe_eidleinfersel7 (hip_pipe_eidleinfersel7),
    .hip_pipe_powerdown0 (hip_pipe_powerdown0),
    .hip_pipe_powerdown1 (hip_pipe_powerdown1),
    .hip_pipe_powerdown2 (hip_pipe_powerdown2),
    .hip_pipe_powerdown3 (hip_pipe_powerdown3),
    .hip_pipe_powerdown4 (hip_pipe_powerdown4),
    .hip_pipe_powerdown5 (hip_pipe_powerdown5),
    .hip_pipe_powerdown6 (hip_pipe_powerdown6),
    .hip_pipe_powerdown7 (hip_pipe_powerdown7),
    .hip_pipe_rxpolarity0 (hip_pipe_rxpolarity0),
    .hip_pipe_rxpolarity1 (hip_pipe_rxpolarity1),
    .hip_pipe_rxpolarity2 (hip_pipe_rxpolarity2),
    .hip_pipe_rxpolarity3 (hip_pipe_rxpolarity3),
    .hip_pipe_rxpolarity4 (hip_pipe_rxpolarity4),
    .hip_pipe_rxpolarity5 (hip_pipe_rxpolarity5),
    .hip_pipe_rxpolarity6 (hip_pipe_rxpolarity6),
    .hip_pipe_rxpolarity7 (hip_pipe_rxpolarity7),
    .hip_pipe_txcompl0 (hip_pipe_txcompl0),
    .hip_pipe_txcompl1 (hip_pipe_txcompl1),
    .hip_pipe_txcompl2 (hip_pipe_txcompl2),
    .hip_pipe_txcompl3 (hip_pipe_txcompl3),
    .hip_pipe_txcompl4 (hip_pipe_txcompl4),
    .hip_pipe_txcompl5 (hip_pipe_txcompl5),
    .hip_pipe_txcompl6 (hip_pipe_txcompl6),
    .hip_pipe_txcompl7 (hip_pipe_txcompl7),
    .hip_pipe_txdata0 (hip_pipe_txdata0),
    .hip_pipe_txdata1 (hip_pipe_txdata1),
    .hip_pipe_txdata2 (hip_pipe_txdata2),
    .hip_pipe_txdata3 (hip_pipe_txdata3),
    .hip_pipe_txdata4 (hip_pipe_txdata4),
    .hip_pipe_txdata5 (hip_pipe_txdata5),
    .hip_pipe_txdata6 (hip_pipe_txdata6),
    .hip_pipe_txdata7 (hip_pipe_txdata7),
    .hip_pipe_txdatak0 (hip_pipe_txdatak0),
    .hip_pipe_txdatak1 (hip_pipe_txdatak1),
    .hip_pipe_txdatak2 (hip_pipe_txdatak2),
    .hip_pipe_txdatak3 (hip_pipe_txdatak3),
    .hip_pipe_txdatak4 (hip_pipe_txdatak4),
    .hip_pipe_txdatak5 (hip_pipe_txdatak5),
    .hip_pipe_txdatak6 (hip_pipe_txdatak6),
    .hip_pipe_txdatak7 (hip_pipe_txdatak7),
    .hip_pipe_txdetectrx0 (hip_pipe_txdetectrx0),
    .hip_pipe_txdetectrx1 (hip_pipe_txdetectrx1),
    .hip_pipe_txdetectrx2 (hip_pipe_txdetectrx2),
    .hip_pipe_txdetectrx3 (hip_pipe_txdetectrx3),
    .hip_pipe_txdetectrx4 (hip_pipe_txdetectrx4),
    .hip_pipe_txdetectrx5 (hip_pipe_txdetectrx5),
    .hip_pipe_txdetectrx6 (hip_pipe_txdetectrx6),
    .hip_pipe_txdetectrx7 (hip_pipe_txdetectrx7),
    .hip_pipe_txelecidle0 (hip_pipe_txelecidle0),
    .hip_pipe_txelecidle1 (hip_pipe_txelecidle1),
    .hip_pipe_txelecidle2 (hip_pipe_txelecidle2),
    .hip_pipe_txelecidle3 (hip_pipe_txelecidle3),
    .hip_pipe_txelecidle4 (hip_pipe_txelecidle4),
    .hip_pipe_txelecidle5 (hip_pipe_txelecidle5),
    .hip_pipe_txelecidle6 (hip_pipe_txelecidle6),
    .hip_pipe_txelecidle7 (hip_pipe_txelecidle7),
    .hip_pipe_txdeemph0 (hip_pipe_txdeemph0),
    .hip_pipe_txdeemph1 (hip_pipe_txdeemph1),
    .hip_pipe_txdeemph2 (hip_pipe_txdeemph2),
    .hip_pipe_txdeemph3 (hip_pipe_txdeemph3),
    .hip_pipe_txdeemph4 (hip_pipe_txdeemph4),
    .hip_pipe_txdeemph5 (hip_pipe_txdeemph5),
    .hip_pipe_txdeemph6 (hip_pipe_txdeemph6),
    .hip_pipe_txdeemph7 (hip_pipe_txdeemph7),
    .hip_pipe_txmargin0 (hip_pipe_txmargin0),
    .hip_pipe_txmargin1 (hip_pipe_txmargin1),
    .hip_pipe_txmargin2 (hip_pipe_txmargin2),
    .hip_pipe_txmargin3 (hip_pipe_txmargin3),
    .hip_pipe_txmargin4 (hip_pipe_txmargin4),
    .hip_pipe_txmargin5 (hip_pipe_txmargin5),
    .hip_pipe_txmargin6 (hip_pipe_txmargin6),
    .hip_pipe_txmargin7 (hip_pipe_txmargin7),
    .hip_pipe_txswing0 (hip_pipe_txswing0),
    .hip_pipe_txswing1 (hip_pipe_txswing1),
    .hip_pipe_txswing2 (hip_pipe_txswing2),
    .hip_pipe_txswing3 (hip_pipe_txswing3),
    .hip_pipe_txswing4 (hip_pipe_txswing4),
    .hip_pipe_txswing5 (hip_pipe_txswing5),
    .hip_pipe_txswing6 (hip_pipe_txswing6),
    .hip_pipe_txswing7 (hip_pipe_txswing7),
    .hip_pipe_phystatus0 (hip_pipe_phystatus0),
    .hip_pipe_phystatus1 (hip_pipe_phystatus1),
    .hip_pipe_phystatus2 (hip_pipe_phystatus2),
    .hip_pipe_phystatus3 (hip_pipe_phystatus3),
    .hip_pipe_phystatus4 (hip_pipe_phystatus4),
    .hip_pipe_phystatus5 (hip_pipe_phystatus5),
    .hip_pipe_phystatus6 (hip_pipe_phystatus6),
    .hip_pipe_phystatus7 (hip_pipe_phystatus7),
    .hip_pipe_rxdata0 (hip_pipe_rxdata0),
    .hip_pipe_rxdata1 (hip_pipe_rxdata1),
    .hip_pipe_rxdata2 (hip_pipe_rxdata2),
    .hip_pipe_rxdata3 (hip_pipe_rxdata3),
    .hip_pipe_rxdata4 (hip_pipe_rxdata4),
    .hip_pipe_rxdata5 (hip_pipe_rxdata5),
    .hip_pipe_rxdata6 (hip_pipe_rxdata6),
    .hip_pipe_rxdata7 (hip_pipe_rxdata7),
    .hip_pipe_rxdatak0 (hip_pipe_rxdatak0),
    .hip_pipe_rxdatak1 (hip_pipe_rxdatak1),
    .hip_pipe_rxdatak2 (hip_pipe_rxdatak2),
    .hip_pipe_rxdatak3 (hip_pipe_rxdatak3),
    .hip_pipe_rxdatak4 (hip_pipe_rxdatak4),
    .hip_pipe_rxdatak5 (hip_pipe_rxdatak5),
    .hip_pipe_rxdatak6 (hip_pipe_rxdatak6),
    .hip_pipe_rxdatak7 (hip_pipe_rxdatak7),
    .hip_pipe_rxelecidle0 (hip_pipe_rxelecidle0),
    .hip_pipe_rxelecidle1 (hip_pipe_rxelecidle1),
    .hip_pipe_rxelecidle2 (hip_pipe_rxelecidle2),
    .hip_pipe_rxelecidle3 (hip_pipe_rxelecidle3),
    .hip_pipe_rxelecidle4 (hip_pipe_rxelecidle4),
    .hip_pipe_rxelecidle5 (hip_pipe_rxelecidle5),
    .hip_pipe_rxelecidle6 (hip_pipe_rxelecidle6),
    .hip_pipe_rxelecidle7 (hip_pipe_rxelecidle7),
    .hip_pipe_rxstatus0 (hip_pipe_rxstatus0),
    .hip_pipe_rxstatus1 (hip_pipe_rxstatus1),
    .hip_pipe_rxstatus2 (hip_pipe_rxstatus2),
    .hip_pipe_rxstatus3 (hip_pipe_rxstatus3),
    .hip_pipe_rxstatus4 (hip_pipe_rxstatus4),
    .hip_pipe_rxstatus5 (hip_pipe_rxstatus5),
    .hip_pipe_rxstatus6 (hip_pipe_rxstatus6),
    .hip_pipe_rxstatus7 (hip_pipe_rxstatus7),
    .hip_pipe_rxvalid0 (hip_pipe_rxvalid0),
    .hip_pipe_rxvalid1 (hip_pipe_rxvalid1),
    .hip_pipe_rxvalid2 (hip_pipe_rxvalid2),
    .hip_pipe_rxvalid3 (hip_pipe_rxvalid3),
    .hip_pipe_rxvalid4 (hip_pipe_rxvalid4),
    .hip_pipe_rxvalid5 (hip_pipe_rxvalid5),
    .hip_pipe_rxvalid6 (hip_pipe_rxvalid6),
    .hip_pipe_rxvalid7 (hip_pipe_rxvalid7),
    .hip_pipe_rxdataskip0 (hip_pipe_rxdataskip0),
    .hip_pipe_rxdataskip1 (hip_pipe_rxdataskip1),
    .hip_pipe_rxdataskip2 (hip_pipe_rxdataskip2),
    .hip_pipe_rxdataskip3 (hip_pipe_rxdataskip3),
    .hip_pipe_rxdataskip4 (hip_pipe_rxdataskip4),
    .hip_pipe_rxdataskip5 (hip_pipe_rxdataskip5),
    .hip_pipe_rxdataskip6 (hip_pipe_rxdataskip6),
    .hip_pipe_rxdataskip7 (hip_pipe_rxdataskip7),
    .hip_pipe_rxblkst0 (hip_pipe_rxblkst0),
    .hip_pipe_rxblkst1 (hip_pipe_rxblkst1),
    .hip_pipe_rxblkst2 (hip_pipe_rxblkst2),
    .hip_pipe_rxblkst3 (hip_pipe_rxblkst3),
    .hip_pipe_rxblkst4 (hip_pipe_rxblkst4),
    .hip_pipe_rxblkst5 (hip_pipe_rxblkst5),
    .hip_pipe_rxblkst6 (hip_pipe_rxblkst6),
    .hip_pipe_rxblkst7 (hip_pipe_rxblkst7),
    .hip_pipe_rxsynchd0 (hip_pipe_rxsynchd0),
    .hip_pipe_rxsynchd1 (hip_pipe_rxsynchd1),
    .hip_pipe_rxsynchd2 (hip_pipe_rxsynchd2),
    .hip_pipe_rxsynchd3 (hip_pipe_rxsynchd3),
    .hip_pipe_rxsynchd4 (hip_pipe_rxsynchd4),
    .hip_pipe_rxsynchd5 (hip_pipe_rxsynchd5),
    .hip_pipe_rxsynchd6 (hip_pipe_rxsynchd6),
    .hip_pipe_rxsynchd7 (hip_pipe_rxsynchd7),
    .hip_pipe_currentcoeff0 (hip_pipe_currentcoeff0),
    .hip_pipe_currentcoeff1 (hip_pipe_currentcoeff1),
    .hip_pipe_currentcoeff2 (hip_pipe_currentcoeff2),
    .hip_pipe_currentcoeff3 (hip_pipe_currentcoeff3),
    .hip_pipe_currentcoeff4 (hip_pipe_currentcoeff4),
    .hip_pipe_currentcoeff5 (hip_pipe_currentcoeff5),
    .hip_pipe_currentcoeff6 (hip_pipe_currentcoeff6),
    .hip_pipe_currentcoeff7 (hip_pipe_currentcoeff7),
    .hip_pipe_currentrxpreset0 (hip_pipe_currentrxpreset0),
    .hip_pipe_currentrxpreset1 (hip_pipe_currentrxpreset1),
    .hip_pipe_currentrxpreset2 (hip_pipe_currentrxpreset2),
    .hip_pipe_currentrxpreset3 (hip_pipe_currentrxpreset3),
    .hip_pipe_currentrxpreset4 (hip_pipe_currentrxpreset4),
    .hip_pipe_currentrxpreset5 (hip_pipe_currentrxpreset5),
    .hip_pipe_currentrxpreset6 (hip_pipe_currentrxpreset6),
    .hip_pipe_currentrxpreset7 (hip_pipe_currentrxpreset7),
    .hip_pipe_txsynchd0 (hip_pipe_txsynchd0),
    .hip_pipe_txsynchd1 (hip_pipe_txsynchd1),
    .hip_pipe_txsynchd2 (hip_pipe_txsynchd2),
    .hip_pipe_txsynchd3 (hip_pipe_txsynchd3),
    .hip_pipe_txsynchd4 (hip_pipe_txsynchd4),
    .hip_pipe_txsynchd5 (hip_pipe_txsynchd5),
    .hip_pipe_txsynchd6 (hip_pipe_txsynchd6),
    .hip_pipe_txsynchd7 (hip_pipe_txsynchd7),
    .hip_pipe_txblkst0 (hip_pipe_txblkst0),
    .hip_pipe_txblkst1 (hip_pipe_txblkst1),
    .hip_pipe_txblkst2 (hip_pipe_txblkst2),
    .hip_pipe_txblkst3 (hip_pipe_txblkst3),
    .hip_pipe_txblkst4 (hip_pipe_txblkst4),
    .hip_pipe_txblkst5 (hip_pipe_txblkst5),
    .hip_pipe_txblkst6 (hip_pipe_txblkst6),
    .hip_pipe_txblkst7 (hip_pipe_txblkst7),
    .hip_pipe_txdataskip0 (hip_pipe_txdataskip0),
    .hip_pipe_txdataskip1 (hip_pipe_txdataskip1),
    .hip_pipe_txdataskip2 (hip_pipe_txdataskip2),
    .hip_pipe_txdataskip3 (hip_pipe_txdataskip3),
    .hip_pipe_txdataskip4 (hip_pipe_txdataskip4),
    .hip_pipe_txdataskip5 (hip_pipe_txdataskip5),
    .hip_pipe_txdataskip6 (hip_pipe_txdataskip6),
    .hip_pipe_txdataskip7 (hip_pipe_txdataskip7),
    .hip_pipe_rate0 (hip_pipe_rate0),
    .hip_pipe_rate1 (hip_pipe_rate1),
    .hip_pipe_rate2 (hip_pipe_rate2),
    .hip_pipe_rate3 (hip_pipe_rate3),
    .hip_pipe_rate4 (hip_pipe_rate4),
    .hip_pipe_rate5 (hip_pipe_rate5),
    .hip_pipe_rate6 (hip_pipe_rate6),
    .hip_pipe_rate7 (hip_pipe_rate7)
);

reg [23:0] hb = 24'h0;
always @(posedge CLK) hb <= hb + 1'b1;
assign LED0_N = ~hb[21];   // ~12 Hz heartbeat

endmodule
