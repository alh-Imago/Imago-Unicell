`timescale 1ns / 1ps
// tb_stub_issp_sim_only.v -- SIMULATION-ONLY stand-in for the IP-Catalog-
// generated `issp` (altsource_probe) component. issp.qsys is deliberately
// NOT committed to git (see docs/HARDWARE_SETUP.md / points.md -- it must
// be regenerated locally via IP Catalog before any real Quartus build).
// This stub exists purely so tb_top_arria10_pcie_mux.v / _silent.v can
// elaborate and run in iverilog without a real Quartus install -- it does
// nothing functionally and must NEVER be used in a real synthesis run.
// Port directions match real altsource_probe semantics: source is
// host-to-fabric (issp drives it, hence an output here); probe is
// fabric-to-host (the wrapper drives it, hence an input here).
module issp (
    output reg  [65:0]  source,
    input  wire [112:0] probe,
    input  wire         source_clk
);
    initial source = 66'h0;
endmodule
