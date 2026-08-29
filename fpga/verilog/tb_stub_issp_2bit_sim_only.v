`timescale 1ns / 1ps
// tb_stub_issp_2bit_sim_only.v -- SIMULATION-ONLY stand-in for the
// IP-Catalog-generated `issp` (altsource_probe) component, matching
// Alan's own real generated config exactly (probe_width=2,
// source_width=1, create_source_clock=false -- confirmed directly
// from the uploaded issp.qsys, not assumed). A DIFFERENT real
// configuration from tb_stub_issp_sim_only.v's own 66-bit/113-bit,
// source_clk-equipped stub (the older sentinel-bridge ISSP channel) --
// kept in a SEPARATE file specifically so the two are never compiled
// together (same module name `issp`, genuinely different port lists,
// would collide). This stub does nothing functionally and must NEVER
// be used in a real synthesis run -- issp.qsys itself (or Alan's own
// real generated HDL from it) is what a real Quartus build uses.
module issp (
    output reg  [0:0] source,
    input  wire [1:0] probe
);
    initial source = 1'b0;
endmodule
