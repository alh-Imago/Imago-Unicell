`timescale 1ns/1ps
// rpll_model.v -- simulation stand-in for the Gowin rPLL primitive (our own, for hexn_tang_sdramtest_v1 only): CLKOUT follows CLKIN, CLKOUTP is the inverted clock (an ideal 180 degree shift), LOCK rises after 2 us. The real PLL's settings are not modelled.
module rPLL #(parameter FCLKIN = "27", parameter IDIV_SEL = 0, parameter FBDIV_SEL = 0, parameter ODIV_SEL = 2, parameter PSDA_SEL = "0000", parameter DUTYDA_SEL = "1000", parameter CLKOUT_FT_DIR = 1'b1, parameter CLKOUTP_FT_DIR = 1'b1, parameter CLKOUT_DLY_STEP = 0, parameter CLKOUTP_DLY_STEP = 0, parameter CLKFB_SEL = "internal", parameter DYN_SDIV_SEL = 2, parameter DEVICE = "GW2A-18")
    (input CLKIN, input CLKFB, input RESET, input RESET_P, input [5:0] FBDSEL, input [5:0] IDSEL, input [5:0] ODSEL, input [3:0] PSDA, input [3:0] DUTYDA, input [3:0] FDLY, output CLKOUT, output CLKOUTP, output CLKOUTD, output CLKOUTD3, output reg LOCK);
    assign CLKOUT = CLKIN; assign CLKOUTP = ~CLKIN; assign CLKOUTD = 1'b0; assign CLKOUTD3 = 1'b0;
    initial begin LOCK = 0; #2000 LOCK = 1; end
endmodule
