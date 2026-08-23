`timescale 1ns / 1ps
// tb_stub_alterafpf_add_single_v1.v -- SIMULATION-ONLY stand-in for the
// real Intel/Altera `alterafpf_add_single` megafunction used by
// `dsp_add_wrapper_v1.v`. Real, confirmed latency (#462, checked
// against Intel's own documentation): 3 clock cycles. This stub
// reproduces that REAL TIMING exactly, but deliberately does NOT
// perform real IEEE-754 floating-point arithmetic -- that requires the
// real hard DSP silicon to confirm, not something a behavioral Verilog
// stub can honestly claim. Instead it computes a simple, deterministic,
// non-floating-point operation (bitwise XOR) purely so
// `dsp_add_wrapper_v1.v`'s own real protocol logic (dual-operand
// capture, the real 3-cycle wait, held-fire-until-ack, re-arming for a
// second real operation) can be verified independently of the actual
// arithmetic result. Must NEVER be used in a real synthesis run --
// the real `alterafpf_add_single` IP must be generated locally via IP
// Catalog before any real Quartus build, matching this project's own
// standing IP-generation discipline (see `dsp_add_wrapper_v1.v`'s own
// header for the real, stated port-name uncertainty this stub also
// deliberately mirrors, not resolves).
module alterafpf_add_single (
    input  wire [31:0] dataa,
    input  wire [31:0] datab,
    input  wire        clock,
    output reg  [31:0] result
);
    reg [31:0] stage1, stage2;
    always @(posedge clock) begin
        stage1 <= dataa ^ datab;   // NOT real IEEE-754 addition -- see header
        stage2 <= stage1;
        result <= stage2;
    end
endmodule
