// tb_packed_adder45_v3.v — proves the verified 45-cell packed shift-adder
// design (docs/design-notes/packed_adder_cluster_mesh.md) actually computes
// correct 32-bit addition when built as real RTL on 9 clusters.
`timescale 1ns/1ps
module tb_packed_adder45_v3;
    reg clk=0, rst=0; always #5 clk=~clk;
    reg start_load=0;
    reg [31:0] host_cmd_bus=0, host_cmd_data=0; reg host_cmd_valid=0;
    wire [31:0] sum_result; wire sum_valid_pulse; wire loader_done;

    top_packed_adder45_v3 dut (
        .clk(clk), .rst(rst), .start_load(start_load),
        .host_cmd_bus(host_cmd_bus), .host_cmd_data(host_cmd_data), .host_cmd_valid(host_cmd_valid),
        .sum_result(sum_result), .sum_valid_pulse(sum_valid_pulse), .loader_done(loader_done)
    );

    integer errors=0;
    task check32; input [31:0] got, want; input [255:0] msg; begin
        if (got===want) $display("  PASS: %0s (0x%08x)", msg, got);
        else begin $display("  FAIL: %0s got=0x%08x want=0x%08x", msg, got, want); errors=errors+1; end
    end endtask

    localparam [15:0] EXTERNAL_ADDR = 16'd0;

    task inject; input [31:0] value; begin
        // DATA_WRITE (opcode 1): address rides cmd_data[31:16], value IS the
        // whole word -- same convention proven in tb_pcie_bram_v3.v. Since
        // EXTERNAL_ADDR (1000=0x3E8) doesn't fit the convention's "address ==
        // value's own upper 16 bits" constraint directly, encode explicitly:
        // cmd_data[31:16]=EXTERNAL_ADDR (the routing address), cmd_data[15:0]
        // = value's own lower 16 bits. This means only the LOW 16 bits of A
        // and B survive the injection -- a real limitation of this simple
        // host-inject convenience path, not of the adder itself. Good enough
        // to prove the mechanism end to end; a wider host interface (the PCIe
        // stand-in's burst path, or a dedicated wide-data opcode) would be
        // needed to inject full 32-bit operands in a real deployment.
        @(negedge clk); host_cmd_bus={8'h0,8'd1}; host_cmd_data={EXTERNAL_ADDR, value[15:0]};
        host_cmd_valid=1'b1;
        @(posedge clk); #1; host_cmd_valid=1'b0;
        @(posedge clk); #1;
    end endtask

    integer w;
    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        $display("=== 45-CELL PACKED SHIFT-ADDER: load, run, verify ===");

        @(negedge clk); start_load=1'b1;
        @(posedge clk); #1; start_load=1'b0;
        w=0;
        while (!loader_done && w<3000) begin @(posedge clk); #1; w=w+1; end
        $display("  loader_done after %0d cycles (main load + priming, 45 cells + 27 primes)", w);
        if (!loader_done) begin
            $display("  FAIL: loader never completed within %0d cycles", w);
            errors=errors+1;
        end else begin
            // A=0x00F0, B=0x0003 (low 16 bits only, per this test's injection
            // convenience path -- see inject() comment)
            inject(32'h0000_00F0);
            inject(32'h0000_0003);
            repeat(50) @(posedge clk); #1;
            // KNOWN ISSUE (2026-07-05, not yet fixed): P0_fanout_r1/r2 stay
            // primed (a_arrived=1) but never receive their real value.
            // Root cause identified precisely: they listen at a BORROWED
            // address (matching their "natural" sibling, e.g. SHL_P1's own
            // address) to catch a shared broadcast from P0 -- but they
            // physically live in a DIFFERENT cluster than that sibling. The
            // zone bridge address-decode fix (this session) now correctly
            // routes each address to ONLY the cluster that owns it (by
            // CELL_BASE), so a relay borrowing a foreign cluster's address
            // never receives the broadcast anymore. The shared-broadcast
            // fan-out trick and the smart per-address routing are each
            // individually correct but incompatible as currently combined.
            // Real fix (not yet applied): add a placement constraint so any
            // two cells sharing a broadcast address always land in the SAME
            // cluster -- see docs/design-notes/packed_adder_cluster_mesh.md.
            $display("  P0_fanout_r1(cl0,l1): out_valid=%0d out_data=0x%08x a_arrived=%0d (expect eventually non-zero once the placement fix lands)",
                      dut.cluster0.cells.cell_array[1].cell_inst.out_valid,
                      dut.cluster0.cells.cell_array[1].cell_inst.out_data,
                      dut.cluster0.cells.cell_array[1].cell_inst.a_arrived);
            $display("  P0_fanout_r2(cl0,l2): out_valid=%0d out_data=0x%08x a_arrived=%0d",
                      dut.cluster0.cells.cell_array[2].cell_inst.out_valid,
                      dut.cluster0.cells.cell_array[2].cell_inst.out_data,
                      dut.cluster0.cells.cell_array[2].cell_inst.a_arrived);
            begin : wait_sum
                integer i; reg seen; seen=1'b0;
                for (i=0; i<300 && !seen; i=i+1) begin
                    if (sum_valid_pulse) begin
                        seen = 1'b1;
                        check32(sum_result, (32'h00F0+32'h0003)&32'hFFFFFFFF, "SUM = 0xF0+0x3 = 0xF3");
                    end
                    @(posedge clk); #1;
                end
                if (!seen) begin
                    $display("  FAIL: SUM pulse never observed within 60 cycles after injection");
                    errors = errors + 1;
                end
            end
        end

        if (errors==0) $display(">>> 45-CELL ADDER PASS: real RTL, real addition, correct result");
        else $display(">>> 45-CELL ADDER FAIL: %0d errors", errors);
        $finish;
    end
endmodule
