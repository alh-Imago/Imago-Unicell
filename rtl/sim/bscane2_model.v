// Simulation stand-in for the Xilinx BSCANE2 primitive (NOT for synthesis: the real tools use the primitive). The testbench drives the TAP signals by hierarchical assignment to r_* and reads TDO.
module BSCANE2 #(parameter JTAG_CHAIN = 1, parameter DISABLE_JTAG = "FALSE") (output CAPTURE, output DRCK, output RESET, output RUNTEST, output SEL, output SHIFT, output TCK, output TDI, output TMS, output UPDATE, input TDO);
    reg r_capture = 0, r_drck = 0, r_sel = 0, r_shift = 0, r_tdi = 0, r_update = 0;
    assign CAPTURE = r_capture; assign DRCK = r_drck; assign SEL = r_sel; assign SHIFT = r_shift; assign TDI = r_tdi; assign UPDATE = r_update;
    assign RESET = 0; assign RUNTEST = 0; assign TCK = r_drck; assign TMS = 0;
endmodule
