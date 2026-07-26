// pcie_hip_wrapper.v -- instantiates and wires together pcie_a10_hip_0 (the
// raw PCIe Hard IP, Avalon-ST application interface) and pio_bridge_0 (the
// Intel "PIO AVST" bridge, translating that raw ST/conduit interface into a
// genuine Avalon-MM master -- hprxm) so top_arria10_zone1_v3.v only needs to
// instantiate ONE clean module, rather than wiring two raw qsys components
// (and their ~250 combined ports) directly into the fabric top-level.
//
// Both pcie_a10_hip_0 and pio_bridge_0 were generated via Quartus's IP
// Catalog "New Component" wizard (same category as issp -- NOT Platform-
// Designer-nested systems), so this wraps them the same way
// unicell_issp_bridge.v wraps issp: plain Verilog instantiation and wiring,
// no qsys system nesting needed or possible.
//
// Every port connection and WIDTH below is taken directly from the real,
// Quartus-generated _inst.v / .cmp files for both components -- not
// inferred from .sopcinfo interface names or typical/standard values. A
// first draft of this file got several conduit widths wrong by assuming
// standard values; re-checked directly against pcie_a10_hip_0.cmp /
// pio_bridge_0.cmp (2026-07-21) and corrected before this version.
//
// The exposed Avalon-MM interface (rxm_*) is intentionally narrow -- 16-bit
// address, 32-bit data, 4-bit byteenable, no burstcount -- matching what
// pio_bridge_0's hprxm interface actually provides (confirmed via
// pio_bridge_0.cmp), NOT the wider 64-bit/128-bit/16-bit interface the
// ORIGINAL pcie_test_1 reference's rxm_bar0 had. pcie_unicell_bridge.v has
// already been rewritten to match this narrower interface (see its own
// header for the register map). A wider "DMA"-style Avalon-MM variant may
// exist separately and could replace this path later if throughput ever
// needs it -- deliberately deferred, not pursued now, per "confirm PCIe
// works first."

module pcie_hip_wrapper (
    input  wire         refclk,       // 100MHz PCIe reference clock (board input)
    input  wire         npor,         // power-on reset (board input, active low per Hard IP convention)
    input  wire         pin_perst,    // PCIe PERST# (board input)

    // Physical PCIe serial lanes (x8) -- connect directly to the board's
    // PCIe edge connector pins in the .qsf pin assignments.
    input  wire [7:0]   pcie_rx_p,
    output wire [7:0]   pcie_tx_p,

    // The fabric's own clock/reset -- needed to instantiate pcie_cdc_bridge
    // internally, so rxm_* below is already correctly synchronized to this
    // domain, not the Hard IP's own 250MHz coreclkout_hip. See points.md
    // #46 (the flagged CDC gap) and pcie_cdc_bridge.v for why this is
    // needed: coreclkout_hip and the fabric clock are different, fully
    // asynchronous domains.
    input  wire         slow_clk,
    input  wire         slow_rst,

    // Clean outputs for the fabric side: the Hard IP's own generated
    // application clock/reset, exposed for anything that might want them
    // directly (not currently used by top_arria10_zone1_v3.v -- see its
    // own comment on app_clk/app_rst -- deliberately out of scope for
    // "get PCIe confirmed working" first pass).
    output wire         app_clk,
    output wire         app_rst,

    // The real Avalon-MM master interface -- ALREADY SYNCHRONIZED to
    // slow_clk via the internal pcie_cdc_bridge instance below. Widths
    // confirmed directly from pio_bridge_0.cmp: 16-bit address, 32-bit
    // data, 4-bit byteenable, no burstcount. Matches pcie_unicell_bridge.v's
    // avs_* ports exactly -- connect these directly, clocked by the SAME
    // slow_clk this module was given.
    output wire [15:0]  rxm_address,
    output wire [3:0]   rxm_byteenable,
    output wire [31:0]  rxm_writedata,
    output wire         rxm_write,
    output wire         rxm_read,
    input  wire [31:0]  rxm_readdata,
    input  wire         rxm_readdatavalid,
    input  wire         rxm_waitrequest
);

// ── Internal wiring between pcie_a10_hip_0 and pio_bridge_0 ──────────────────
// Every width below confirmed directly from pcie_a10_hip_0.cmp /
// pio_bridge_0.cmp.
wire        w_clr_st;
wire        w_coreclkout_hip;

// rx_st (Hard IP source) <-> rx_st_hip (bridge sink) -- 128-bit ST datapath
wire [127:0] w_rx_st_data;
wire         w_rx_st_sop, w_rx_st_eop, w_rx_st_err, w_rx_st_valid, w_rx_st_ready;
wire         w_rx_st_empty;

// tx_st_hip (bridge source) <-> tx_st (Hard IP sink)
wire [127:0] w_tx_st_data;
wire         w_tx_st_sop, w_tx_st_eop, w_tx_st_err, w_tx_st_valid, w_tx_st_ready;
wire         w_tx_st_empty;

// rx_bar conduit
wire [7:0]   w_rx_st_bar;
wire         w_rx_st_mask;

// tx_cred conduit
wire [11:0]  w_tx_cred_data_fc;
wire [5:0]   w_tx_cred_fc_hip_cons;
wire [5:0]   w_tx_cred_fc_infinite;
wire [7:0]   w_tx_cred_hdr_fc;
wire [1:0]   w_tx_cred_fc_sel;

// config_tl conduit
wire [3:0]   w_tl_cfg_add;
wire [31:0]  w_tl_cfg_ctl;
wire [52:0]  w_tl_cfg_sts;
wire         w_cpl_pending;
wire [4:0]   w_hpg_ctrler;
wire [6:0]   w_cpl_err;

// power_mgnt conduit
wire         w_pm_auxpwr, w_pm_event, w_pme_to_cr, w_pme_to_sr;
wire [9:0]   w_pm_data;

// hip_status conduit (subset pio_bridge_0 actually consumes)
wire [1:0]   w_currentspeed;
wire [4:0]   w_ltssmstate;
wire [3:0]   w_lane_act;
wire         w_derr_cor_ext_rcv, w_derr_cor_ext_rpl, w_derr_rpl;
wire         w_dlup, w_dlup_exit, w_ev128ns, w_ev1us, w_hotrst_exit;
wire [3:0]   w_int_status;
wire         w_l2_exit, w_rx_par_err, w_cfg_par_err;
wire [1:0]   w_tx_par_err;
wire [7:0]   w_ko_cpl_spc_header;
wire [11:0]  w_ko_cpl_spc_data;

// hip_rst conduit (subset)
wire         w_pld_core_ready, w_pld_clk_inuse, w_serdes_pll_locked;
wire         w_reset_status, w_testin_zero;

// int_msi conduit
wire         w_app_int_sts, w_app_int_ack, w_app_msi_req, w_app_msi_ack;
wire [4:0]   w_app_msi_num;
wire [2:0]   w_app_msi_tc;

// Raw fast-domain (coreclkout_hip) Avalon-MM master signals from
// pio_bridge_0, BEFORE clock-domain-crossing -- fed into pcie_cdc_bridge
// below, not exposed directly as this module's own outputs.
wire [15:0]  w_fast_rxm_address;
wire [3:0]   w_fast_rxm_byteenable;
wire [31:0]  w_fast_rxm_writedata;
wire         w_fast_rxm_write;
wire         w_fast_rxm_read;
wire [31:0]  w_fast_rxm_readdata;
wire         w_fast_rxm_readdatavalid;
wire         w_fast_rxm_waitrequest;

assign app_clk = w_coreclkout_hip;
assign app_rst = w_clr_st;

// ── Raw PCIe Hard IP ─────────────────────────────────────────────────────────
// SERDES/PHY-level per-lane tuning ports (eidleinfersel*, powerdown*,
// rxpolarity*, txdeemph*, txmargin*, txswing*, rate*, phystatus*, txdata*,
// rxdata*, etc.) intentionally left unconnected -- native x8 endpoint
// default behaviour, same as an equivalent Platform-Designer-generated top
// level would leave them. TODO at the real Quartus machine: confirm none
// of the omitted ports produce a warning that actually matters for this
// configuration.
pcie_a10_hip_0 u_pcie_hip (
    .npor                (npor),
    .pin_perst           (pin_perst),

    // ── hip_ctrl conduit ────────────────────────────────────────────────────
    // Found 2026-07-26 by diffing this wrapper against Intel's own generated
    // PIO example (pcie_example_design.qsys): every other DUT<->APPS conduit
    // is connected internally, but `hip_ctrl` is EXPORTED
    //   <interface name="hip_ctrl" internal="DUT.hip_ctrl" .. dir="end" />
    // i.e. Intel expects the level above the Qsys system to drive it. Its
    // exported ports (pcie_example_design.cmp) are:
    //   hip_ctrl_test_in        : in std_logic_vector(31 downto 0)
    //   hip_ctrl_simu_mode_pipe : in std_logic
    // This wrapper previously left both unconnected, so synthesis tied them
    // to 0 -- the ONLY structural divergence from a configuration known to
    // work on real silicon.
    //
    // Value from the Design Example User Guide (UG-20039 / doc 683065),
    // Table 2, which maps devkit_ctrl onto test_in and gives the typical
    // settings:
    //   test_in[0]    = 1'b0        -> bit  0 clear (0 = hardware, not sim)
    //   test_in[4:1]  = 4'b0100     -> bit  3 set
    //   test_in[6:5]  = 2'b01       -> bit  5 set
    //   test_in[31:7] = 25'h3       -> bits 7 and 8 set
    // Assembled: bits 3,5,7,8 -> 32'h0000_01A8.
    //
    // HONEST CAVEAT: Intel documents these as test/compliance signals without
    // a public bit-by-bit breakdown, so it is NOT established that a zero
    // test_in is what holds the application interface in reset. This is
    // "match the known-good reference", not "understood mechanism". If this
    // turns out not to be the fix, do not assume the value is wrong -- it
    // matches Intel's documented typical settings either way.
    .test_in             (32'h000001A8),
    .simu_mode_pipe      (1'b0),

    .refclk              (refclk),
    .pld_clk             (w_coreclkout_hip),   // Hard IP's own generated clock, fed back to itself
    .coreclkout_hip      (w_coreclkout_hip),
    .clr_st              (w_clr_st),

    .rx_in0(pcie_rx_p[0]), .rx_in1(pcie_rx_p[1]), .rx_in2(pcie_rx_p[2]), .rx_in3(pcie_rx_p[3]),
    .rx_in4(pcie_rx_p[4]), .rx_in5(pcie_rx_p[5]), .rx_in6(pcie_rx_p[6]), .rx_in7(pcie_rx_p[7]),
    .tx_out0(pcie_tx_p[0]), .tx_out1(pcie_tx_p[1]), .tx_out2(pcie_tx_p[2]), .tx_out3(pcie_tx_p[3]),
    .tx_out4(pcie_tx_p[4]), .tx_out5(pcie_tx_p[5]), .tx_out6(pcie_tx_p[6]), .tx_out7(pcie_tx_p[7]),

    .rx_st_data(w_rx_st_data), .rx_st_sop(w_rx_st_sop), .rx_st_eop(w_rx_st_eop),
    .rx_st_err(w_rx_st_err), .rx_st_valid(w_rx_st_valid), .rx_st_ready(w_rx_st_ready),
    .rx_st_empty(w_rx_st_empty), .rx_st_bar(w_rx_st_bar), .rx_st_mask(w_rx_st_mask),

    .tx_st_data(w_tx_st_data), .tx_st_sop(w_tx_st_sop), .tx_st_eop(w_tx_st_eop),
    .tx_st_err(w_tx_st_err), .tx_st_valid(w_tx_st_valid), .tx_st_ready(w_tx_st_ready),
    .tx_st_empty(w_tx_st_empty),

    .tx_cred_data_fc(w_tx_cred_data_fc), .tx_cred_fc_hip_cons(w_tx_cred_fc_hip_cons),
    .tx_cred_fc_infinite(w_tx_cred_fc_infinite), .tx_cred_hdr_fc(w_tx_cred_hdr_fc),
    .tx_cred_fc_sel(w_tx_cred_fc_sel),

    .hpg_ctrler(w_hpg_ctrler), .tl_cfg_add(w_tl_cfg_add), .tl_cfg_ctl(w_tl_cfg_ctl),
    .tl_cfg_sts(w_tl_cfg_sts), .cpl_err(w_cpl_err), .cpl_pending(w_cpl_pending),

    .currentspeed(w_currentspeed),

    .pm_auxpwr(w_pm_auxpwr), .pm_data(w_pm_data), .pme_to_cr(w_pme_to_cr),
    .pm_event(w_pm_event), .pme_to_sr(w_pme_to_sr),

    .ltssmstate(w_ltssmstate), .lane_act(w_lane_act),
    .derr_cor_ext_rcv(w_derr_cor_ext_rcv), .derr_cor_ext_rpl(w_derr_cor_ext_rpl),
    .derr_rpl(w_derr_rpl), .dlup(w_dlup), .dlup_exit(w_dlup_exit),
    .ev128ns(w_ev128ns), .ev1us(w_ev1us), .hotrst_exit(w_hotrst_exit),
    .int_status(w_int_status), .l2_exit(w_l2_exit),
    .rx_par_err(w_rx_par_err), .tx_par_err(w_tx_par_err), .cfg_par_err(w_cfg_par_err),
    .ko_cpl_spc_header(w_ko_cpl_spc_header), .ko_cpl_spc_data(w_ko_cpl_spc_data),

    // ── DIAGNOSTIC EXPERIMENT (2026-07-26) -- NOT a settled design change ────
    // Testing the reset-deadlock hypothesis. Measured state: link is fully
    // healthy (ltssmstate = 0x0F = L0, config space works, Gen2 x8) but the
    // application interface is stuck -- reset_status reads 1 and rx_st_ready
    // reads 0 at rest, and rxstvalid never asserts for any host access.
    //
    // The suspected loop: pio_bridge_0 drives pld_core_ready (confirmed an
    // OUTPUT in pio_bridge_0.cmp), but pio_bridge_0 is itself reset by clr_st,
    // and the Hard IP won't release clr_st/reset_status until pld_core_ready
    // asserts. If the bridge's pld_core_ready is registered and cleared by its
    // own reset, nothing ever starts.
    //
    // This breaks the loop by driving pld_core_ready from w_serdes_pll_locked
    // instead: a Hard IP output that comes up with the transceivers and sits
    // entirely outside the application reset domain, so it cannot participate
    // in the deadlock. It's also Intel's documented tie for this signal.
    //
    // The bridge's own pld_core_ready output is left dangling below (see the
    // pio_bridge_0 instantiation) -- two drivers on one net would be an error.
    //
    // IF THIS WORKS: the deadlock is proven, but decide the proper fix
    // deliberately rather than keeping this as-is -- the bridge presumably has
    // a reason to gate that signal, and bypassing it may just be masking a
    // reset-sequencing problem elsewhere.
    // IF IT DOESN'T: revert to `.pld_core_ready(w_pld_core_ready)` on both
    // sides, and go read pio_ed's generated source (in pio_ed_251/) to find
    // out how rx_st_ready and pld_core_ready are actually produced.
    .pld_core_ready(w_serdes_pll_locked), .pld_clk_inuse(w_pld_clk_inuse),
    .serdes_pll_locked(w_serdes_pll_locked), .reset_status(w_reset_status),
    .testin_zero(w_testin_zero),

    .app_int_sts(w_app_int_sts), .app_int_ack(w_app_int_ack),
    .app_msi_num(w_app_msi_num), .app_msi_req(w_app_msi_req),
    .app_msi_tc(w_app_msi_tc), .app_msi_ack(w_app_msi_ack)
);

// ── PIO Avalon-ST-to-Avalon-MM bridge ────────────────────────────────────────
pio_bridge_0 u_pio_bridge (
    .Clk_i(w_coreclkout_hip),
    .clr_st(w_clr_st),

    .HipRxStData_i(w_rx_st_data), .HipRxStSop_i(w_rx_st_sop), .HipRxStEop_i(w_rx_st_eop),
    .HipRxStErr_i(w_rx_st_err), .HipRxStValid_i(w_rx_st_valid), .HipRxStEmpty_i(w_rx_st_empty),
    .HipRxStReady_o(w_rx_st_ready),
    .HipRxStBarDec1_i(w_rx_st_bar), .HipRxStMask_o(w_rx_st_mask),

    .HipTxStData_o(w_tx_st_data), .HipTxStSop_o(w_tx_st_sop), .HipTxStEop_o(w_tx_st_eop),
    .HipTxStError_o(w_tx_st_err), .HipTxStValid_o(w_tx_st_valid), .HipTxStEmpty_o(w_tx_st_empty),
    .HipTxStReady_i(w_tx_st_ready),

    .AvRxmWrite_0_o(w_fast_rxm_write), .AvRxmAddress_0_o(w_fast_rxm_address),
    .AvRxmWriteData_0_o(w_fast_rxm_writedata), .AvRxmByteEnable_0_o(w_fast_rxm_byteenable),
    .AvRxmWaitRequest_0_i(w_fast_rxm_waitrequest), .AvRxmRead_0_o(w_fast_rxm_read),
    .AvRxmReadData_0_i(w_fast_rxm_readdata), .AvRxmReadDataValid_0_i(w_fast_rxm_readdatavalid),

    .HipCfgAddr_i(w_tl_cfg_add), .HipCfgCtl_i(w_tl_cfg_ctl), .TLCfgSts_i(w_tl_cfg_sts),
    .cpl_err_o(w_cpl_err), .cpl_pending_o(w_cpl_pending), .hpg_ctrler_o(w_hpg_ctrler),

    .pm_auxpwr(w_pm_auxpwr), .pm_data(w_pm_data), .pme_to_cr(w_pme_to_cr),
    .pm_event(w_pm_event), .pme_to_sr(w_pme_to_sr),

    .CurrentSpeed_i(w_currentspeed),
    .Ltssm_i(w_ltssmstate), .LaneAct_i(w_lane_act),
    .derr_cor_ext_rcv(w_derr_cor_ext_rcv), .derr_cor_ext_rpl(w_derr_cor_ext_rpl),
    .derr_rpl(w_derr_rpl), .dlup_exit(w_dlup_exit), .ev128ns(w_ev128ns), .ev1us(w_ev1us),
    .hotrst_exit(w_hotrst_exit), .int_status(w_int_status), .l2_exit(w_l2_exit),
    .dlup(w_dlup), .rx_par_err(w_rx_par_err), .tx_par_err(w_tx_par_err), .cfg_par_err(w_cfg_par_err),
    .ko_cpl_spc_header(w_ko_cpl_spc_header), .ko_cpl_spc_data(w_ko_cpl_spc_data),

    // pld_core_ready deliberately left DANGLING as part of the diagnostic
    // experiment described at the Hard IP instantiation above -- the Hard IP's
    // input is driven from w_serdes_pll_locked instead. Restore this to
    // `.pld_core_ready(w_pld_core_ready)` (and the Hard IP side likewise) to
    // return to Intel's reference wiring.
    .pld_clk_inuse(w_pld_clk_inuse), .pld_core_ready(),
    .reset_status(w_reset_status), .serdes_pll_locked(w_serdes_pll_locked),
    .testin_zero(w_testin_zero),

    .tx_cred_data_fc(w_tx_cred_data_fc), .tx_cred_fc_hip_cons(w_tx_cred_fc_hip_cons),
    .tx_cred_fc_infinite(w_tx_cred_fc_infinite), .tx_cred_hdr_fc(w_tx_cred_hdr_fc),
    .tx_cred_fc_sel(w_tx_cred_fc_sel),

    .app_int_ack(w_app_int_ack), .app_int_sts(w_app_int_sts),
    .app_msi_ack(w_app_msi_ack), .app_msi_num(w_app_msi_num),
    .app_msi_req(w_app_msi_req), .app_msi_tc(w_app_msi_tc)
);

// ── Clock-domain crossing: coreclkout_hip (fast, 250MHz) -> slow_clk ────────
// (fabric, currently 25MHz, target 50MHz -- see points.md #46). Resolves
// the CDC gap flagged when this wrapper was first built: pio_bridge_0's
// AvRxm* signals are registered on coreclkout_hip internally, but
// pcie_unicell_bridge.v needs a stable interface in the fabric's OWN clock
// domain. See pcie_cdc_bridge.v for the design (frequency-ratio-
// independent by construction) and its own testbench for verification at
// both plausible fabric rates.
pcie_cdc_bridge u_cdc (
    .fast_clk(w_coreclkout_hip), .fast_rst(w_clr_st),
    .fast_address(w_fast_rxm_address), .fast_byteenable(w_fast_rxm_byteenable),
    .fast_writedata(w_fast_rxm_writedata), .fast_write(w_fast_rxm_write),
    .fast_read(w_fast_rxm_read), .fast_readdata(w_fast_rxm_readdata),
    .fast_readdatavalid(w_fast_rxm_readdatavalid), .fast_waitrequest(w_fast_rxm_waitrequest),

    .slow_clk(slow_clk), .slow_rst(slow_rst),
    .slow_address(rxm_address), .slow_byteenable(rxm_byteenable),
    .slow_writedata(rxm_writedata), .slow_write(rxm_write), .slow_read(rxm_read),
    .slow_readdata(rxm_readdata), .slow_readdatavalid(rxm_readdatavalid),
    .slow_waitrequest(rxm_waitrequest)
);

endmodule
