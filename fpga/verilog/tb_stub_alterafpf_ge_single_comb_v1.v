`timescale 1ns / 1ps
// tb_stub_alterafpf_ge_single_comb_v1.v -- SIMULATION-ONLY stand-in for
// the real, CONFIRMED comparison IP entity dsp_compare_wrapper_v1.v now
// instantiates (points.md #496, real ground truth from Alan's own
// generated `alterafpf_ge_single_comb.qsys`). Real, confirmed port
// list: dataa/datab/n/result ONLY -- no clk, no clk_en, no reset, the
// real IP is genuinely, purely combinational, more so than the earlier
// reasoned placeholder assumed. Deliberately NOT real IEEE-754
// comparison semantics -- a simple, deterministic placeholder purely
// for verifying this wrapper's own real protocol timing. Must NEVER be
// used in a real synthesis run.
module alterafpf_ge_single_comb (
    input  wire [31:0] dataa,
    input  wire [31:0] datab,
    input  wire [7:0]  n,
    output wire         result
);
    // Combinational, matching the real IP's own zero-clock port list --
    // NOT real IEEE-754 comparison, see header.
    assign result = (dataa != datab);
endmodule
