`timescale 1ns / 1ps
// tb_stub_pcie_a10_hip_0_sim_only.v -- SIMULATION-ONLY stand-in for the IP-
// Catalog-generated pcie_a10_hip_0 (Arria 10 PCIe Hard IP). Real hardware
// simulation of this IP requires Quartus's own encrypted sim libraries
// (the real wrapper instantiates a hardened core,
// pcie_a10_hip_0_altera_pcie_a10_hip_251_szg444q, whose definition is not
// distributed as plain Verilog) -- not reproducible outside a Quartus/
// ModelSim install. This stub exists purely so tb_top_arria10_pcie_mux.v /
// _silent.v can elaborate and run in iverilog without a real Quartus
// install -- it does nothing functionally (every output tied to a constant
// 0, including coreclkout_hip, so the PCIe-side clock domain never
// toggles) and must NEVER be used in a real synthesis run.
//
// Port list is NOT guessed: copied verbatim (names + widths) from the real
// generated pcie_a10_hip_0.v (ACDS 25.1) pulled from the live Quartus
// project on 2026-07-28, so this stub's interface is exactly what the real
// IP presents -- only the behavior (none) is stubbed.

module pcie_a10_hip_0 (
		output wire         clr_st,              //         clr_st.reset
		input  wire [4:0]   hpg_ctrler,          //      config_tl.hpg_ctrler
		output wire [3:0]   tl_cfg_add,          //               .tl_cfg_add
		output wire [31:0]  tl_cfg_ctl,          //               .tl_cfg_ctl
		output wire [52:0]  tl_cfg_sts,          //               .tl_cfg_sts
		input  wire [6:0]   cpl_err,             //               .cpl_err
		input  wire         cpl_pending,         //               .cpl_pending
		output wire         coreclkout_hip,      // coreclkout_hip.clk
		output wire [1:0]   currentspeed,        //   currentspeed.currentspeed
		input  wire [31:0]  test_in,             //       hip_ctrl.test_in
		input  wire         simu_mode_pipe,      //               .simu_mode_pipe
		input  wire         sim_pipe_pclk_in,    //       hip_pipe.sim_pipe_pclk_in
		output wire [1:0]   sim_pipe_rate,       //               .sim_pipe_rate
		output wire [4:0]   sim_ltssmstate,      //               .sim_ltssmstate
		output wire [2:0]   eidleinfersel0,      //               .eidleinfersel0
		output wire [2:0]   eidleinfersel1,      //               .eidleinfersel1
		output wire [2:0]   eidleinfersel2,      //               .eidleinfersel2
		output wire [2:0]   eidleinfersel3,      //               .eidleinfersel3
		output wire [2:0]   eidleinfersel4,      //               .eidleinfersel4
		output wire [2:0]   eidleinfersel5,      //               .eidleinfersel5
		output wire [2:0]   eidleinfersel6,      //               .eidleinfersel6
		output wire [2:0]   eidleinfersel7,      //               .eidleinfersel7
		output wire [1:0]   powerdown0,          //               .powerdown0
		output wire [1:0]   powerdown1,          //               .powerdown1
		output wire [1:0]   powerdown2,          //               .powerdown2
		output wire [1:0]   powerdown3,          //               .powerdown3
		output wire [1:0]   powerdown4,          //               .powerdown4
		output wire [1:0]   powerdown5,          //               .powerdown5
		output wire [1:0]   powerdown6,          //               .powerdown6
		output wire [1:0]   powerdown7,          //               .powerdown7
		output wire         rxpolarity0,         //               .rxpolarity0
		output wire         rxpolarity1,         //               .rxpolarity1
		output wire         rxpolarity2,         //               .rxpolarity2
		output wire         rxpolarity3,         //               .rxpolarity3
		output wire         rxpolarity4,         //               .rxpolarity4
		output wire         rxpolarity5,         //               .rxpolarity5
		output wire         rxpolarity6,         //               .rxpolarity6
		output wire         rxpolarity7,         //               .rxpolarity7
		output wire         txcompl0,            //               .txcompl0
		output wire         txcompl1,            //               .txcompl1
		output wire         txcompl2,            //               .txcompl2
		output wire         txcompl3,            //               .txcompl3
		output wire         txcompl4,            //               .txcompl4
		output wire         txcompl5,            //               .txcompl5
		output wire         txcompl6,            //               .txcompl6
		output wire         txcompl7,            //               .txcompl7
		output wire [31:0]  txdata0,             //               .txdata0
		output wire [31:0]  txdata1,             //               .txdata1
		output wire [31:0]  txdata2,             //               .txdata2
		output wire [31:0]  txdata3,             //               .txdata3
		output wire [31:0]  txdata4,             //               .txdata4
		output wire [31:0]  txdata5,             //               .txdata5
		output wire [31:0]  txdata6,             //               .txdata6
		output wire [31:0]  txdata7,             //               .txdata7
		output wire [3:0]   txdatak0,            //               .txdatak0
		output wire [3:0]   txdatak1,            //               .txdatak1
		output wire [3:0]   txdatak2,            //               .txdatak2
		output wire [3:0]   txdatak3,            //               .txdatak3
		output wire [3:0]   txdatak4,            //               .txdatak4
		output wire [3:0]   txdatak5,            //               .txdatak5
		output wire [3:0]   txdatak6,            //               .txdatak6
		output wire [3:0]   txdatak7,            //               .txdatak7
		output wire         txdetectrx0,         //               .txdetectrx0
		output wire         txdetectrx1,         //               .txdetectrx1
		output wire         txdetectrx2,         //               .txdetectrx2
		output wire         txdetectrx3,         //               .txdetectrx3
		output wire         txdetectrx4,         //               .txdetectrx4
		output wire         txdetectrx5,         //               .txdetectrx5
		output wire         txdetectrx6,         //               .txdetectrx6
		output wire         txdetectrx7,         //               .txdetectrx7
		output wire         txelecidle0,         //               .txelecidle0
		output wire         txelecidle1,         //               .txelecidle1
		output wire         txelecidle2,         //               .txelecidle2
		output wire         txelecidle3,         //               .txelecidle3
		output wire         txelecidle4,         //               .txelecidle4
		output wire         txelecidle5,         //               .txelecidle5
		output wire         txelecidle6,         //               .txelecidle6
		output wire         txelecidle7,         //               .txelecidle7
		output wire         txdeemph0,           //               .txdeemph0
		output wire         txdeemph1,           //               .txdeemph1
		output wire         txdeemph2,           //               .txdeemph2
		output wire         txdeemph3,           //               .txdeemph3
		output wire         txdeemph4,           //               .txdeemph4
		output wire         txdeemph5,           //               .txdeemph5
		output wire         txdeemph6,           //               .txdeemph6
		output wire         txdeemph7,           //               .txdeemph7
		output wire [2:0]   txmargin0,           //               .txmargin0
		output wire [2:0]   txmargin1,           //               .txmargin1
		output wire [2:0]   txmargin2,           //               .txmargin2
		output wire [2:0]   txmargin3,           //               .txmargin3
		output wire [2:0]   txmargin4,           //               .txmargin4
		output wire [2:0]   txmargin5,           //               .txmargin5
		output wire [2:0]   txmargin6,           //               .txmargin6
		output wire [2:0]   txmargin7,           //               .txmargin7
		output wire         txswing0,            //               .txswing0
		output wire         txswing1,            //               .txswing1
		output wire         txswing2,            //               .txswing2
		output wire         txswing3,            //               .txswing3
		output wire         txswing4,            //               .txswing4
		output wire         txswing5,            //               .txswing5
		output wire         txswing6,            //               .txswing6
		output wire         txswing7,            //               .txswing7
		input  wire         phystatus0,          //               .phystatus0
		input  wire         phystatus1,          //               .phystatus1
		input  wire         phystatus2,          //               .phystatus2
		input  wire         phystatus3,          //               .phystatus3
		input  wire         phystatus4,          //               .phystatus4
		input  wire         phystatus5,          //               .phystatus5
		input  wire         phystatus6,          //               .phystatus6
		input  wire         phystatus7,          //               .phystatus7
		input  wire [31:0]  rxdata0,             //               .rxdata0
		input  wire [31:0]  rxdata1,             //               .rxdata1
		input  wire [31:0]  rxdata2,             //               .rxdata2
		input  wire [31:0]  rxdata3,             //               .rxdata3
		input  wire [31:0]  rxdata4,             //               .rxdata4
		input  wire [31:0]  rxdata5,             //               .rxdata5
		input  wire [31:0]  rxdata6,             //               .rxdata6
		input  wire [31:0]  rxdata7,             //               .rxdata7
		input  wire [3:0]   rxdatak0,            //               .rxdatak0
		input  wire [3:0]   rxdatak1,            //               .rxdatak1
		input  wire [3:0]   rxdatak2,            //               .rxdatak2
		input  wire [3:0]   rxdatak3,            //               .rxdatak3
		input  wire [3:0]   rxdatak4,            //               .rxdatak4
		input  wire [3:0]   rxdatak5,            //               .rxdatak5
		input  wire [3:0]   rxdatak6,            //               .rxdatak6
		input  wire [3:0]   rxdatak7,            //               .rxdatak7
		input  wire         rxelecidle0,         //               .rxelecidle0
		input  wire         rxelecidle1,         //               .rxelecidle1
		input  wire         rxelecidle2,         //               .rxelecidle2
		input  wire         rxelecidle3,         //               .rxelecidle3
		input  wire         rxelecidle4,         //               .rxelecidle4
		input  wire         rxelecidle5,         //               .rxelecidle5
		input  wire         rxelecidle6,         //               .rxelecidle6
		input  wire         rxelecidle7,         //               .rxelecidle7
		input  wire [2:0]   rxstatus0,           //               .rxstatus0
		input  wire [2:0]   rxstatus1,           //               .rxstatus1
		input  wire [2:0]   rxstatus2,           //               .rxstatus2
		input  wire [2:0]   rxstatus3,           //               .rxstatus3
		input  wire [2:0]   rxstatus4,           //               .rxstatus4
		input  wire [2:0]   rxstatus5,           //               .rxstatus5
		input  wire [2:0]   rxstatus6,           //               .rxstatus6
		input  wire [2:0]   rxstatus7,           //               .rxstatus7
		input  wire         rxvalid0,            //               .rxvalid0
		input  wire         rxvalid1,            //               .rxvalid1
		input  wire         rxvalid2,            //               .rxvalid2
		input  wire         rxvalid3,            //               .rxvalid3
		input  wire         rxvalid4,            //               .rxvalid4
		input  wire         rxvalid5,            //               .rxvalid5
		input  wire         rxvalid6,            //               .rxvalid6
		input  wire         rxvalid7,            //               .rxvalid7
		input  wire         rxdataskip0,         //               .rxdataskip0
		input  wire         rxdataskip1,         //               .rxdataskip1
		input  wire         rxdataskip2,         //               .rxdataskip2
		input  wire         rxdataskip3,         //               .rxdataskip3
		input  wire         rxdataskip4,         //               .rxdataskip4
		input  wire         rxdataskip5,         //               .rxdataskip5
		input  wire         rxdataskip6,         //               .rxdataskip6
		input  wire         rxdataskip7,         //               .rxdataskip7
		input  wire         rxblkst0,            //               .rxblkst0
		input  wire         rxblkst1,            //               .rxblkst1
		input  wire         rxblkst2,            //               .rxblkst2
		input  wire         rxblkst3,            //               .rxblkst3
		input  wire         rxblkst4,            //               .rxblkst4
		input  wire         rxblkst5,            //               .rxblkst5
		input  wire         rxblkst6,            //               .rxblkst6
		input  wire         rxblkst7,            //               .rxblkst7
		input  wire [1:0]   rxsynchd0,           //               .rxsynchd0
		input  wire [1:0]   rxsynchd1,           //               .rxsynchd1
		input  wire [1:0]   rxsynchd2,           //               .rxsynchd2
		input  wire [1:0]   rxsynchd3,           //               .rxsynchd3
		input  wire [1:0]   rxsynchd4,           //               .rxsynchd4
		input  wire [1:0]   rxsynchd5,           //               .rxsynchd5
		input  wire [1:0]   rxsynchd6,           //               .rxsynchd6
		input  wire [1:0]   rxsynchd7,           //               .rxsynchd7
		output wire [17:0]  currentcoeff0,       //               .currentcoeff0
		output wire [17:0]  currentcoeff1,       //               .currentcoeff1
		output wire [17:0]  currentcoeff2,       //               .currentcoeff2
		output wire [17:0]  currentcoeff3,       //               .currentcoeff3
		output wire [17:0]  currentcoeff4,       //               .currentcoeff4
		output wire [17:0]  currentcoeff5,       //               .currentcoeff5
		output wire [17:0]  currentcoeff6,       //               .currentcoeff6
		output wire [17:0]  currentcoeff7,       //               .currentcoeff7
		output wire [2:0]   currentrxpreset0,    //               .currentrxpreset0
		output wire [2:0]   currentrxpreset1,    //               .currentrxpreset1
		output wire [2:0]   currentrxpreset2,    //               .currentrxpreset2
		output wire [2:0]   currentrxpreset3,    //               .currentrxpreset3
		output wire [2:0]   currentrxpreset4,    //               .currentrxpreset4
		output wire [2:0]   currentrxpreset5,    //               .currentrxpreset5
		output wire [2:0]   currentrxpreset6,    //               .currentrxpreset6
		output wire [2:0]   currentrxpreset7,    //               .currentrxpreset7
		output wire [1:0]   txsynchd0,           //               .txsynchd0
		output wire [1:0]   txsynchd1,           //               .txsynchd1
		output wire [1:0]   txsynchd2,           //               .txsynchd2
		output wire [1:0]   txsynchd3,           //               .txsynchd3
		output wire [1:0]   txsynchd4,           //               .txsynchd4
		output wire [1:0]   txsynchd5,           //               .txsynchd5
		output wire [1:0]   txsynchd6,           //               .txsynchd6
		output wire [1:0]   txsynchd7,           //               .txsynchd7
		output wire         txblkst0,            //               .txblkst0
		output wire         txblkst1,            //               .txblkst1
		output wire         txblkst2,            //               .txblkst2
		output wire         txblkst3,            //               .txblkst3
		output wire         txblkst4,            //               .txblkst4
		output wire         txblkst5,            //               .txblkst5
		output wire         txblkst6,            //               .txblkst6
		output wire         txblkst7,            //               .txblkst7
		output wire         txdataskip0,         //               .txdataskip0
		output wire         txdataskip1,         //               .txdataskip1
		output wire         txdataskip2,         //               .txdataskip2
		output wire         txdataskip3,         //               .txdataskip3
		output wire         txdataskip4,         //               .txdataskip4
		output wire         txdataskip5,         //               .txdataskip5
		output wire         txdataskip6,         //               .txdataskip6
		output wire         txdataskip7,         //               .txdataskip7
		output wire [1:0]   rate0,               //               .rate0
		output wire [1:0]   rate1,               //               .rate1
		output wire [1:0]   rate2,               //               .rate2
		output wire [1:0]   rate3,               //               .rate3
		output wire [1:0]   rate4,               //               .rate4
		output wire [1:0]   rate5,               //               .rate5
		output wire [1:0]   rate6,               //               .rate6
		output wire [1:0]   rate7,               //               .rate7
		input  wire         pld_core_ready,      //        hip_rst.pld_core_ready
		output wire         pld_clk_inuse,       //               .pld_clk_inuse
		output wire         serdes_pll_locked,   //               .serdes_pll_locked
		output wire         reset_status,        //               .reset_status
		output wire         testin_zero,         //               .testin_zero
		input  wire         rx_in0,              //     hip_serial.rx_in0
		input  wire         rx_in1,              //               .rx_in1
		input  wire         rx_in2,              //               .rx_in2
		input  wire         rx_in3,              //               .rx_in3
		input  wire         rx_in4,              //               .rx_in4
		input  wire         rx_in5,              //               .rx_in5
		input  wire         rx_in6,              //               .rx_in6
		input  wire         rx_in7,              //               .rx_in7
		output wire         tx_out0,             //               .tx_out0
		output wire         tx_out1,             //               .tx_out1
		output wire         tx_out2,             //               .tx_out2
		output wire         tx_out3,             //               .tx_out3
		output wire         tx_out4,             //               .tx_out4
		output wire         tx_out5,             //               .tx_out5
		output wire         tx_out6,             //               .tx_out6
		output wire         tx_out7,             //               .tx_out7
		output wire         derr_cor_ext_rcv,    //     hip_status.derr_cor_ext_rcv
		output wire         derr_cor_ext_rpl,    //               .derr_cor_ext_rpl
		output wire         derr_rpl,            //               .derr_rpl
		output wire         dlup,                //               .dlup
		output wire         dlup_exit,           //               .dlup_exit
		output wire         ev128ns,             //               .ev128ns
		output wire         ev1us,               //               .ev1us
		output wire         hotrst_exit,         //               .hotrst_exit
		output wire [3:0]   int_status,          //               .int_status
		output wire         l2_exit,             //               .l2_exit
		output wire [3:0]   lane_act,            //               .lane_act
		output wire [4:0]   ltssmstate,          //               .ltssmstate
		output wire         rx_par_err,          //               .rx_par_err
		output wire [1:0]   tx_par_err,          //               .tx_par_err
		output wire         cfg_par_err,         //               .cfg_par_err
		output wire [7:0]   ko_cpl_spc_header,   //               .ko_cpl_spc_header
		output wire [11:0]  ko_cpl_spc_data,     //               .ko_cpl_spc_data
		input  wire         app_int_sts,         //        int_msi.app_int_sts
		output wire         app_int_ack,         //               .app_int_ack
		input  wire [4:0]   app_msi_num,         //               .app_msi_num
		input  wire         app_msi_req,         //               .app_msi_req
		input  wire [2:0]   app_msi_tc,          //               .app_msi_tc
		output wire         app_msi_ack,         //               .app_msi_ack
		input  wire         npor,                //           npor.npor
		input  wire         pin_perst,           //               .pin_perst
		input  wire         pld_clk,             //        pld_clk.clk
		input  wire         pm_auxpwr,           //     power_mgnt.pm_auxpwr
		input  wire [9:0]   pm_data,             //               .pm_data
		input  wire         pme_to_cr,           //               .pme_to_cr
		input  wire         pm_event,            //               .pm_event
		output wire         pme_to_sr,           //               .pme_to_sr
		input  wire         refclk,              //         refclk.clk
		output wire [7:0]   rx_st_bar,           //         rx_bar.rx_st_bar
		input  wire         rx_st_mask,          //               .rx_st_mask
		output wire [0:0]   rx_st_sop,           //          rx_st.startofpacket
		output wire [0:0]   rx_st_eop,           //               .endofpacket
		output wire [0:0]   rx_st_err,           //               .error
		output wire [0:0]   rx_st_valid,         //               .valid
		input  wire         rx_st_ready,         //               .ready
		output wire [127:0] rx_st_data,          //               .data
		output wire [0:0]   rx_st_empty,         //               .empty
		output wire [11:0]  tx_cred_data_fc,     //        tx_cred.tx_cred_data_fc
		output wire [5:0]   tx_cred_fc_hip_cons, //               .tx_cred_fc_hip_cons
		output wire [5:0]   tx_cred_fc_infinite, //               .tx_cred_fc_infinite
		output wire [7:0]   tx_cred_hdr_fc,      //               .tx_cred_hdr_fc
		input  wire [1:0]   tx_cred_fc_sel,      //               .tx_cred_fc_sel
		input  wire [0:0]   tx_st_sop,           //          tx_st.startofpacket
		input  wire [0:0]   tx_st_eop,           //               .endofpacket
		input  wire [0:0]   tx_st_err,           //               .error
		input  wire [0:0]   tx_st_valid,         //               .valid
		output wire         tx_st_ready,         //               .ready
		input  wire [127:0] tx_st_data,          //               .data
		input  wire [0:0]   tx_st_empty          //               .empty
);

assign clr_st = 1'b0;
assign tl_cfg_add = 4'b0;
assign tl_cfg_ctl = 32'b0;
assign tl_cfg_sts = 53'b0;
assign coreclkout_hip = 1'b0;
assign currentspeed = 2'b0;
assign sim_pipe_rate = 2'b0;
assign sim_ltssmstate = 5'b0;
assign eidleinfersel0 = 3'b0;
assign eidleinfersel1 = 3'b0;
assign eidleinfersel2 = 3'b0;
assign eidleinfersel3 = 3'b0;
assign eidleinfersel4 = 3'b0;
assign eidleinfersel5 = 3'b0;
assign eidleinfersel6 = 3'b0;
assign eidleinfersel7 = 3'b0;
assign powerdown0 = 2'b0;
assign powerdown1 = 2'b0;
assign powerdown2 = 2'b0;
assign powerdown3 = 2'b0;
assign powerdown4 = 2'b0;
assign powerdown5 = 2'b0;
assign powerdown6 = 2'b0;
assign powerdown7 = 2'b0;
assign rxpolarity0 = 1'b0;
assign rxpolarity1 = 1'b0;
assign rxpolarity2 = 1'b0;
assign rxpolarity3 = 1'b0;
assign rxpolarity4 = 1'b0;
assign rxpolarity5 = 1'b0;
assign rxpolarity6 = 1'b0;
assign rxpolarity7 = 1'b0;
assign txcompl0 = 1'b0;
assign txcompl1 = 1'b0;
assign txcompl2 = 1'b0;
assign txcompl3 = 1'b0;
assign txcompl4 = 1'b0;
assign txcompl5 = 1'b0;
assign txcompl6 = 1'b0;
assign txcompl7 = 1'b0;
assign txdata0 = 32'b0;
assign txdata1 = 32'b0;
assign txdata2 = 32'b0;
assign txdata3 = 32'b0;
assign txdata4 = 32'b0;
assign txdata5 = 32'b0;
assign txdata6 = 32'b0;
assign txdata7 = 32'b0;
assign txdatak0 = 4'b0;
assign txdatak1 = 4'b0;
assign txdatak2 = 4'b0;
assign txdatak3 = 4'b0;
assign txdatak4 = 4'b0;
assign txdatak5 = 4'b0;
assign txdatak6 = 4'b0;
assign txdatak7 = 4'b0;
assign txdetectrx0 = 1'b0;
assign txdetectrx1 = 1'b0;
assign txdetectrx2 = 1'b0;
assign txdetectrx3 = 1'b0;
assign txdetectrx4 = 1'b0;
assign txdetectrx5 = 1'b0;
assign txdetectrx6 = 1'b0;
assign txdetectrx7 = 1'b0;
assign txelecidle0 = 1'b0;
assign txelecidle1 = 1'b0;
assign txelecidle2 = 1'b0;
assign txelecidle3 = 1'b0;
assign txelecidle4 = 1'b0;
assign txelecidle5 = 1'b0;
assign txelecidle6 = 1'b0;
assign txelecidle7 = 1'b0;
assign txdeemph0 = 1'b0;
assign txdeemph1 = 1'b0;
assign txdeemph2 = 1'b0;
assign txdeemph3 = 1'b0;
assign txdeemph4 = 1'b0;
assign txdeemph5 = 1'b0;
assign txdeemph6 = 1'b0;
assign txdeemph7 = 1'b0;
assign txmargin0 = 3'b0;
assign txmargin1 = 3'b0;
assign txmargin2 = 3'b0;
assign txmargin3 = 3'b0;
assign txmargin4 = 3'b0;
assign txmargin5 = 3'b0;
assign txmargin6 = 3'b0;
assign txmargin7 = 3'b0;
assign txswing0 = 1'b0;
assign txswing1 = 1'b0;
assign txswing2 = 1'b0;
assign txswing3 = 1'b0;
assign txswing4 = 1'b0;
assign txswing5 = 1'b0;
assign txswing6 = 1'b0;
assign txswing7 = 1'b0;
assign currentcoeff0 = 18'b0;
assign currentcoeff1 = 18'b0;
assign currentcoeff2 = 18'b0;
assign currentcoeff3 = 18'b0;
assign currentcoeff4 = 18'b0;
assign currentcoeff5 = 18'b0;
assign currentcoeff6 = 18'b0;
assign currentcoeff7 = 18'b0;
assign currentrxpreset0 = 3'b0;
assign currentrxpreset1 = 3'b0;
assign currentrxpreset2 = 3'b0;
assign currentrxpreset3 = 3'b0;
assign currentrxpreset4 = 3'b0;
assign currentrxpreset5 = 3'b0;
assign currentrxpreset6 = 3'b0;
assign currentrxpreset7 = 3'b0;
assign txsynchd0 = 2'b0;
assign txsynchd1 = 2'b0;
assign txsynchd2 = 2'b0;
assign txsynchd3 = 2'b0;
assign txsynchd4 = 2'b0;
assign txsynchd5 = 2'b0;
assign txsynchd6 = 2'b0;
assign txsynchd7 = 2'b0;
assign txblkst0 = 1'b0;
assign txblkst1 = 1'b0;
assign txblkst2 = 1'b0;
assign txblkst3 = 1'b0;
assign txblkst4 = 1'b0;
assign txblkst5 = 1'b0;
assign txblkst6 = 1'b0;
assign txblkst7 = 1'b0;
assign txdataskip0 = 1'b0;
assign txdataskip1 = 1'b0;
assign txdataskip2 = 1'b0;
assign txdataskip3 = 1'b0;
assign txdataskip4 = 1'b0;
assign txdataskip5 = 1'b0;
assign txdataskip6 = 1'b0;
assign txdataskip7 = 1'b0;
assign rate0 = 2'b0;
assign rate1 = 2'b0;
assign rate2 = 2'b0;
assign rate3 = 2'b0;
assign rate4 = 2'b0;
assign rate5 = 2'b0;
assign rate6 = 2'b0;
assign rate7 = 2'b0;
assign pld_clk_inuse = 1'b0;
assign serdes_pll_locked = 1'b0;
assign reset_status = 1'b0;
assign testin_zero = 1'b0;
assign tx_out0 = 1'b0;
assign tx_out1 = 1'b0;
assign tx_out2 = 1'b0;
assign tx_out3 = 1'b0;
assign tx_out4 = 1'b0;
assign tx_out5 = 1'b0;
assign tx_out6 = 1'b0;
assign tx_out7 = 1'b0;
assign derr_cor_ext_rcv = 1'b0;
assign derr_cor_ext_rpl = 1'b0;
assign derr_rpl = 1'b0;
assign dlup = 1'b0;
assign dlup_exit = 1'b0;
assign ev128ns = 1'b0;
assign ev1us = 1'b0;
assign hotrst_exit = 1'b0;
assign int_status = 4'b0;
assign l2_exit = 1'b0;
assign lane_act = 4'b0;
assign ltssmstate = 5'b0;
assign rx_par_err = 1'b0;
assign tx_par_err = 2'b0;
assign cfg_par_err = 1'b0;
assign ko_cpl_spc_header = 8'b0;
assign ko_cpl_spc_data = 12'b0;
assign app_int_ack = 1'b0;
assign app_msi_ack = 1'b0;
assign pme_to_sr = 1'b0;
assign rx_st_bar = 8'b0;
assign rx_st_sop = 1'b0;
assign rx_st_eop = 1'b0;
assign rx_st_err = 1'b0;
assign rx_st_valid = 1'b0;
assign rx_st_data = 128'b0;
assign rx_st_empty = 1'b0;
assign tx_cred_data_fc = 12'b0;
assign tx_cred_fc_hip_cons = 6'b0;
assign tx_cred_fc_infinite = 6'b0;
assign tx_cred_hdr_fc = 8'b0;
assign tx_st_ready = 1'b0;

endmodule
