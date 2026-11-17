// sc_k7_v2.v - sc_k7_v1.v with the pool sc_top_k7_v3 (fixed host link jtag_link_v2).  Build with:  make -f Makefile.v2
// sc_k7_v1.v - the small top that openXC7.mk wants (module top, file named after the project).  Sets the build sizes and instantiates the S-Core pool for the
// Kintex card.  Change S (slices) here.  All other design files are staged into rtl/ as .sv by stage.sh.
module top (input SYS_CLK, output [2:0] led);
    sc_top_k7_v3 #(.S(4), .QD(16), .IMEM_WORDS(128), .DMW(16), .DSH(256), .SHL(14), .FAR_AW(16), .JK(32), .RXGAP(512)) u (.SYS_CLK(SYS_CLK), .led(led));
endmodule
