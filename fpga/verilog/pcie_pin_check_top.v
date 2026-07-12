// SPDX-License-Identifier: CERN-OHL-P-2.0
// pcie_pin_check_top.v -- MINIMAL wrapper, PIN-LEGALITY CHECK ONLY, not a
// functional build. Exposes just enough of pcie_test_1's real ports
// (ref_clk_clk, xcvr_tx_out0-7, xcvr_rx_in0-7) to top level so Quartus's
// Pin Planner / Assignment Editor can report which physical banks/pins are
// actually legal for an x8 PCIe HIP on this device -- same free-information
// technique that already found the legal refclk I/O standards and the
// 16-IOPLL-location limit earlier this project.
//
// The huge hip_pipe_* bus (PIPE-level debug/status signals, ~211 ports) is
// left as internal, undriven wires -- irrelevant to pin legality, not needed
// for this check. Expect Quartus warnings about undriven/unconnected nodes;
// that's fine, this file is never meant to be flashed.

`default_nettype none

module pcie_pin_check_top (
    input wire clk_clk,
    input wire reset_reset_n,
    input wire ref_clk_clk,
    input wire hip_ctl_npor,
    input wire hip_ctl_pin_perst,
    input wire xcvr_rx_in0,
    output wire xcvr_tx_out0,
    input wire xcvr_rx_in1,
    output wire xcvr_tx_out1,
    input wire xcvr_rx_in2,
    output wire xcvr_tx_out2,
    input wire xcvr_rx_in3,
    output wire xcvr_tx_out3,
    input wire xcvr_rx_in4,
    output wire xcvr_tx_out4,
    input wire xcvr_rx_in5,
    output wire xcvr_tx_out5,
    input wire xcvr_rx_in6,
    output wire xcvr_tx_out6,
    input wire xcvr_rx_in7,
    output wire xcvr_tx_out7
);

// Internal-only wires for the hip_pipe_* PIPE debug bus -- undriven,
// irrelevant to this pin-legality check.
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
    .clk_clk (clk_clk),
    .reset_reset_n (reset_reset_n),
    .ref_clk_clk (ref_clk_clk),
    .hip_ctl_npor (hip_ctl_npor),
    .hip_ctl_pin_perst (hip_ctl_pin_perst),
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
    .hip_pipe_rate7 (hip_pipe_rate7),
    .xcvr_rx_in0 (xcvr_rx_in0),
    .xcvr_rx_in1 (xcvr_rx_in1),
    .xcvr_rx_in2 (xcvr_rx_in2),
    .xcvr_rx_in3 (xcvr_rx_in3),
    .xcvr_rx_in4 (xcvr_rx_in4),
    .xcvr_rx_in5 (xcvr_rx_in5),
    .xcvr_rx_in6 (xcvr_rx_in6),
    .xcvr_rx_in7 (xcvr_rx_in7),
    .xcvr_tx_out0 (xcvr_tx_out0),
    .xcvr_tx_out1 (xcvr_tx_out1),
    .xcvr_tx_out2 (xcvr_tx_out2),
    .xcvr_tx_out3 (xcvr_tx_out3),
    .xcvr_tx_out4 (xcvr_tx_out4),
    .xcvr_tx_out5 (xcvr_tx_out5),
    .xcvr_tx_out6 (xcvr_tx_out6),
    .xcvr_tx_out7 (xcvr_tx_out7)
);

endmodule