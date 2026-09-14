`timescale 1ns / 1ps
// tb_stub_issp_sentinel_gather_v1.v -- SIMULATION-ONLY stand-in for the
// real IP-Catalog-generated `issp_sentinel_gather` (altsource_probe)
// component used by `host_bridge_sentinel_gather_v1.v`. Same purpose
// and discipline as this project's existing ISSP stubs -- kept as a
// SEPARATE file since the real IP itself must be generated per-instance
// with fixed widths. `issp_sentinel_gather.qsys` itself is deliberately
// NOT committed to git -- regenerate locally before any real Quartus
// build. This stub does nothing functionally and must NEVER be used in
// a real synthesis run.
//
// Port widths must match `host_bridge_sentinel_gather_v1.v`'s own real
// SRC_W=91 / PRB_W=158 parameters exactly.
module issp_sentinel_gather (
    output reg  [90:0]  source,
    input  wire [157:0] probe,
    input  wire         source_clk
);
    initial source = 91'h0;
endmodule
