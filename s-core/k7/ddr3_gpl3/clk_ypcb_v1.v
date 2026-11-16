// clk_ypcb_v1.v - clocks for the DDR3 build: one PLL from the 50 MHz pin.  Derived from upstream/example_demo/ypcb_00338_1p1/clk_wiz.v (UberDDR3,
// Angelo Jacobo, GPL-3.0) with two more outputs added, so this file is GPL-3.0 and lives in ddr3_gpl3/ (see README.md).  Not generated: edit by hand.
//   VCO = 50 MHz x 20 = 1000 MHz
//   cclk        83.333 MHz  (/12)            controller clock (UberDDR3 CONTROLLER_CLK_PERIOD 12000 ps)
//   ddr3_clk   333.333 MHz  (/3,  0 degrees) DDR3 clock (DDR3_CLK_PERIOD 3000 ps = DDR3-667)
//   ref_clk    200.000 MHz  (/5)             IDELAYCTRL reference
//   ddr3_clk_90 333.333 MHz (/3, 90 degrees)
//   ck_clk     333.333 MHz  (/3, 60 degrees) the DDR3 CK output's own clock (the fixed offset that suits all nine chips, measured by sirmick on this card)
//   pool_clk    50.000 MHz  (/20)            the S-Core pool's clock, from the same PLL so all clocks come up together (the pin feeds only the PLL)
`timescale 1ps/1ps
module clk_ypcb_v1 (
    input  wire clk_in,
    input  wire reset,
    output wire cclk, ddr3_clk, ref_clk, ddr3_clk_90, ck_clk, pool_clk,
    output wire locked
);
    wire c0, c1, c2, c3, c4, c5, fb;
    PLLE2_ADV #(
        .BANDWIDTH("OPTIMIZED"), .COMPENSATION("INTERNAL"), .STARTUP_WAIT("FALSE"),
        .DIVCLK_DIVIDE(1), .CLKFBOUT_MULT(20), .CLKFBOUT_PHASE(0.000),
        .CLKOUT0_DIVIDE(12), .CLKOUT0_PHASE(0.000),  .CLKOUT0_DUTY_CYCLE(0.500),
        .CLKOUT1_DIVIDE(3),  .CLKOUT1_PHASE(0.000),  .CLKOUT1_DUTY_CYCLE(0.500),
        .CLKOUT2_DIVIDE(5),  .CLKOUT2_PHASE(0.000),  .CLKOUT2_DUTY_CYCLE(0.500),
        .CLKOUT3_DIVIDE(3),  .CLKOUT3_PHASE(90.000), .CLKOUT3_DUTY_CYCLE(0.500),
        .CLKOUT4_DIVIDE(3),  .CLKOUT4_PHASE(60.000), .CLKOUT4_DUTY_CYCLE(0.500),
        .CLKOUT5_DIVIDE(20), .CLKOUT5_PHASE(0.000),  .CLKOUT5_DUTY_CYCLE(0.500),
        .CLKIN1_PERIOD(20.000)
    ) pll (
        .CLKFBOUT(fb), .CLKOUT0(c0), .CLKOUT1(c1), .CLKOUT2(c2), .CLKOUT3(c3), .CLKOUT4(c4), .CLKOUT5(c5),
        .CLKFBIN(fb), .CLKIN1(clk_in), .LOCKED(locked), .RST(reset));
    BUFG b0 (.O(cclk),        .I(c0));
    BUFG b1 (.O(ddr3_clk),    .I(c1));
    BUFG b2 (.O(ref_clk),     .I(c2));
    BUFG b3 (.O(ddr3_clk_90), .I(c3));
    BUFG b4 (.O(ck_clk),      .I(c4));
    BUFG b5 (.O(pool_clk),    .I(c5));
endmodule
