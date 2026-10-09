`timescale 1ns / 1ps
// tb_stub_issp_dsp_v1.v -- SIMULATION-ONLY stand-in for the real
// IP-Catalog-generated `issp_dsp` (altsource_probe) component used by
// host_bridge_dsp_v1.v. Same discipline as every other ISSP stub in
// this project. Port widths must match host_bridge_dsp_v1.v's own
// real SRC_W=37 / PRB_W=114 parameters exactly.
module issp_dsp (
    output reg  [36:0]  source,
    input  wire [113:0] probe,
    input  wire         source_clk
);
    initial source = 37'h0;
endmodule
