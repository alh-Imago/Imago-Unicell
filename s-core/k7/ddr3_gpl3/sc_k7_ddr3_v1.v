// sc_k7_ddr3_v1.v - S-Core pool on the Kintex-7 card with its far RAM in DDR3 channel 0 (UberDDR3).  Top level, module name "top" (openXC7.mk).
//
// LICENCE NOTE: this build contains GPL-3.0 code (UberDDR3, copies in upstream/ and mod/) and is therefore a GPL-3.0 combined work; see README.md.
// The BRAM build (k7/sc_k7_v1) contains none.
//
// Clocks: the 50 MHz pin feeds only the PLL (clk_ypcb_v1); the pool runs on pool_clk (50 MHz from that PLL), the controller on cclk (83.33 MHz).
// Pool: sc_top_k7_v2 (far RAM brought out).  Far RAM: farram_ddr3_v1 (clock crossing + 576-bit line gather) -> ddr3_top.  One DDR3 channel, 9 byte lanes
// (72 bits, ECC lane present but unused), DDR3-667, no write leveling (fixed CK phase, see make_mod.py).
// Ready: the controller's calibration has finished and its built-in test has reached state 23 (the condition sirmick's designs use).
//   LED0 red     pool launch error or a job trapped
//   LED1 green   heartbeat of the pool clock (about 1.5 Hz), so the PLL is running
//   LED2 yellow  steady on = DDR3 calibrated and ready (this differs from the BRAM build, where yellow shows JTAG activity)
`timescale 1ps/1ps
module top (
    input  wire        SYS_CLK,
    output wire [2:0]  led,
    output wire [0:0]  ddr3_ck_p, ddr3_ck_n,
    output wire        ddr3_reset_n,
    output wire [0:0]  ddr3_cke, ddr3_cs_n,
    output wire        ddr3_ras_n, ddr3_cas_n, ddr3_we_n,
    output wire [14:0] ddr3_addr,
    output wire [2:0]  ddr3_ba,
    inout  wire [71:0] ddr3_dq,
    inout  wire [8:0]  ddr3_dqs_p, ddr3_dqs_n,
    output wire [0:0]  ddr3_odt
);
    localparam integer BYTE_LANES = 9;
    localparam integer WB_ADDR_BITS = 15 + 10 + 3 - 3;
    localparam integer WB_DATA_BITS = 8 * BYTE_LANES * 8;

    wire cclk, ddr3_clk, ref_clk, ddr3_clk_90, ck_clk, pool_clk, locked;
    clk_ypcb_v1 clks (.clk_in(SYS_CLK), .reset(1'b0), .cclk(cclk), .ddr3_clk(ddr3_clk), .ref_clk(ref_clk), .ddr3_clk_90(ddr3_clk_90),
                      .ck_clk(ck_clk), .pool_clk(pool_clk), .locked(locked));

    // the one IDELAYCTRL, held in reset for 64 reference cycles after the PLL locks
    reg [6:0] idc_rst_cnt = 7'd0;
    always @(posedge ref_clk) if (!locked) idc_rst_cnt <= 7'd0; else if (!idc_rst_cnt[6]) idc_rst_cnt <= idc_rst_cnt + 1'b1;
    wire idelayctrl_rdy;
    (* IODELAY_GROUP = "DDR3-GROUP" *)
    IDELAYCTRL idelayctrl_inst (.RDY(idelayctrl_rdy), .REFCLK(ref_clk), .RST(!idc_rst_cnt[6]));

    wire calib_complete;
    wire [31:0] debug1;
    wire [BYTE_LANES-1:0] ddr3_dm_unused;
    wire wb_cyc, wb_stb, wb_we, wb_stall, wb_ack;
    wire [WB_ADDR_BITS-1:0] wb_addr;
    wire [WB_DATA_BITS-1:0] wb_wdata, wb_rdata;
    wire [WB_DATA_BITS/8-1:0] wb_sel;

    ddr3_top #(
        .CONTROLLER_CLK_PERIOD(12_000), .DDR3_CLK_PERIOD(3_000), .ROW_BITS(15), .COL_BITS(10), .BA_BITS(3),
        .BYTE_LANES(BYTE_LANES), .AUX_WIDTH(4), .WB2_ADDR_BITS(32), .WB2_DATA_BITS(32), .DUAL_RANK_DIMM(0),
        .MICRON_SIM(0), .ODELAY_SUPPORTED(0), .SECOND_WISHBONE(0), .DLL_OFF(0), .WB_ERROR(0), .BIST_MODE(1),
        .BIST_TEST_DATAMASK(0), .ECC_ENABLE(0), .SPEED_BIN(1), .SDRAM_CAPACITY(4)
    ) ddr3_top_inst (
        .i_controller_clk(cclk), .i_ddr3_clk(ddr3_clk), .i_ref_clk(ref_clk), .i_ddr3_clk_90(ddr3_clk_90),
        .i_ck_clk(ck_clk), .i_idelayctrl_rdy(idelayctrl_rdy), .i_rst_n(locked),
        .i_wb_cyc(wb_cyc), .i_wb_stb(wb_stb), .i_wb_we(wb_we), .i_wb_addr(wb_addr), .i_wb_data(wb_wdata),
        .i_wb_sel(wb_sel), .i_aux(4'b0), .o_wb_stall(wb_stall), .o_wb_ack(wb_ack), .o_wb_err(), .o_wb_data(wb_rdata), .o_aux(),
        .i_wb2_cyc(1'b0), .i_wb2_stb(1'b0), .i_wb2_we(1'b0), .i_wb2_addr(32'b0), .i_wb2_data(32'b0), .i_wb2_sel(4'b0),
        .o_wb2_stall(), .o_wb2_ack(), .o_wb2_data(),
        .o_ddr3_clk_p(ddr3_ck_p), .o_ddr3_clk_n(ddr3_ck_n), .o_ddr3_reset_n(ddr3_reset_n), .o_ddr3_cke(ddr3_cke),
        .o_ddr3_cs_n(ddr3_cs_n), .o_ddr3_ras_n(ddr3_ras_n), .o_ddr3_cas_n(ddr3_cas_n), .o_ddr3_we_n(ddr3_we_n),
        .o_ddr3_addr(ddr3_addr), .o_ddr3_ba_addr(ddr3_ba), .io_ddr3_dq(ddr3_dq), .io_ddr3_dqs(ddr3_dqs_p),
        .io_ddr3_dqs_n(ddr3_dqs_n), .o_ddr3_dm(ddr3_dm_unused), .o_ddr3_odt(ddr3_odt),
        .o_calib_complete(calib_complete), .o_debug1(debug1), .i_user_self_refresh(1'b0), .uart_tx()
    );
    // calibrated, and the controller's built-in self-test finished (state 23)
    wire ram_ready = calib_complete && (debug1[4:0] == 5'd23);

    // ---- pool and far RAM
    wire        fr_v, fr_we, fr_rdy, fr_ackv, fr_init, fr_busy, por_ok;
    wire [20:0] fr_a;
    wire [31:0] fr_wd, fr_ackd;
    wire [2:0]  pool_led;
    sc_top_k7_v2 #(.S(4), .FAR_AW(16), .JK(32), .RXGAP(512)) pool (
        .SYS_CLK(pool_clk), .led(pool_led),
        .fr_v(fr_v), .fr_we(fr_we), .fr_a(fr_a), .fr_wd(fr_wd), .fr_rdy(fr_rdy), .fr_ackv(fr_ackv), .fr_ackd(fr_ackd),
        .fr_init(fr_init), .fr_busy(fr_busy), .por_ok(por_ok));

    farram_ddr3_v1 #(.LANES(BYTE_LANES), .WBA(WB_ADDR_BITS)) far (
        .clk(pool_clk), .rst(!por_ok), .cfg_cl(2'd0), .cfg_dly(2'd0), .cfg_inv(1'b0), .reinit(1'b0),
        .req_v(fr_v), .req_we(fr_we), .req_a(fr_a), .req_wd(fr_wd), .req_rdy(fr_rdy), .ack_v(fr_ackv), .ack_d(fr_ackd),
        .init_done(fr_init), .busy(fr_busy),
        .cclk(cclk), .crst_n(locked), .calib_complete(ram_ready),
        .wb_cyc(wb_cyc), .wb_stb(wb_stb), .wb_we(wb_we), .wb_addr(wb_addr), .wb_data(wb_wdata), .wb_sel(wb_sel),
        .wb_stall(wb_stall), .wb_ack(wb_ack), .wb_rdata(wb_rdata));

    assign led = {fr_init, pool_led[1], pool_led[0]};
endmodule
