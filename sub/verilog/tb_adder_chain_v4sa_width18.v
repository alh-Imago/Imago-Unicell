// tb_adder_chain_v4sa_width18.v -- points.md #910: real 4-stage chain
// correctness at the native 18-bit width, same discipline as #908's 32-bit
// proof -- a Python-computed reference, not hand arithmetic.
`timescale 1ns/1ps
module tb_adder_chain_v4sa_width18;
    localparam W = 18;
    localparam N = 4;
    reg clk = 0;
    reg rst = 1;
    reg freeze_in = 0;
    reg cfg_valid = 0;
    reg [W-1:0] chain_in = 0;
    reg chain_valid_in = 0;
    reg chain_ack_in = 0;
    reg [31:0] lfsr = 32'hA5A51234;   // held fixed for this correctness test,
                                       // same reasoning as #908's own 32-bit version
    wire chain_ack_out;
    wire [W-1:0] chain_out;
    wire chain_valid_out;

    always #5 clk = ~clk;

    adder_chain_v4sa #(.NSTAGES(N), .WIDTH(W)) CHAIN (
        .clk(clk), .rst(rst), .freeze_in(freeze_in),
        .cfg_valid(cfg_valid),
        .chain_in(chain_in), .chain_valid_in(chain_valid_in), .chain_ack_out(chain_ack_out),
        .chain_out(chain_out), .chain_valid_out(chain_valid_out), .chain_ack_in(chain_ack_in),
        .lfsr(lfsr)
    );

    integer errors = 0;
    task check_cond(input cond, input [255:0] label);
        begin
            if (!cond) begin $display("FAIL: %0s", label); errors = errors + 1; end
            else $display("PASS: %0s", label);
        end
    endtask

    integer k;
    initial begin
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);
        cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;

        chain_ack_in = 1;
        chain_in = 18'd5; chain_valid_in = 1;
        for (k = 0; k < N + 2; k = k + 1) @(posedge clk);
        #1;
        check_cond(chain_out === 18'h18226, "4-stage 18-bit chain sum matches the real Python-computed value");
        check_cond(chain_valid_out === 1'b1, "chain_valid_out asserted once the real result has arrived");

        if (errors == 0) $display("ALL PASS");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
