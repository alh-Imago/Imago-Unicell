`timescale 1ns / 1ps
// tb_stub_issp_bram_icm_v1.v -- SIMULATION-ONLY stand-in for the real
// IP-Catalog-generated `issp_bram_icm` (altsource_probe) component used
// by `host_bridge_bram_icm_v1.v`. Same purpose and discipline as this
// project's existing `tb_stub_issp_sim_only.v` (66/113-bit stub for the
// sentinel bridge) -- kept as a SEPARATE file, not a shared/parameterized
// one, because the real IP itself must be generated per-instance with
// specific fixed widths via IP Catalog; a single generic stub module
// name can't stand in for two differently-sized real IP instances at
// once. `issp_bram_icm.qsys` itself is deliberately NOT committed to
// git (see `docs/HARDWARE_SETUP.md`/`TOOLCHAIN_SETUP.md`) -- regenerate
// locally before any real Quartus build. This stub does nothing
// functionally and must NEVER be used in a real synthesis run.
//
// Port widths must match `host_bridge_bram_icm_v1.v`'s own real
// SRC_W=91 / PRB_W=112 parameters exactly.
module issp_bram_icm (
    output reg  [90:0]  source,
    input  wire [111:0] probe,
    input  wire         source_clk
);
    initial source = 91'h0;
endmodule
