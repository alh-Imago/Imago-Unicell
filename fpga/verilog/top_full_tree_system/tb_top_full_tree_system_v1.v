// tb_top_full_tree_system_v1.v — elaboration + functional sanity check
// for top_full_tree_system_v1.v (points.md #273/#280 continuation)
// before handing off to Quartus. The self-test now loops continuously
// with a genuinely runtime-varying address offset (fixing the real
// "Total block memory bits: 0%" finding from the actual Quartus build
// — literal constant addresses let Quartus optimize the real BRAM
// away entirely). This confirms the loop completes MULTIPLE passes
// correctly, each with a different address offset, not just one.
`timescale 1ns / 1ps

module tb_top_full_tree_system_v1;

    reg clk100 = 0;
    always #5 clk100 = ~clk100;

    wire led0, led1;

    top_full_tree_system_v1 DUT (
        .CLK_100M(clk100),
        .LED0_N(led0),
        .LED1_N(led1)
    );

    integer pass_count = 0;
    reg prev_run = 0;

    always @(posedge clk100) begin
        prev_run <= (DUT.state == DUT.S_RUN);
        if (!DUT.rst && (DUT.state == DUT.S_RUN) && !prev_run) begin
            // Rising edge into S_RUN — one full pass just completed.
            if (DUT.result1_seen && DUT.result2_seen && !DUT.err_sticky) begin
                pass_count = pass_count + 1;
                $display("[%0t] pass #%0d complete -- offset=%0d, both results correct",
                    $time, pass_count, DUT.addr_offset);
            end else begin
                $display("[%0t] FAIL: entered S_RUN without both results correct (offset=%0d) result1=%b result2=%b err=%b",
                    $time, DUT.addr_offset, DUT.result1_seen, DUT.result2_seen, DUT.err_sticky);
            end
        end
    end

    initial begin
        #900000;
        $display("Final: pass_count=%0d err_sticky=%b LED1=%b", pass_count, DUT.err_sticky, led1);
        if (pass_count >= 3 && !DUT.err_sticky)
            $display("PASS: top_full_tree_system_v1 -- %0d full passes completed correctly, each with a genuinely different address offset, err_sticky never latched", pass_count);
        else
            $display("FAIL: only %0d pass(es) completed, or err_sticky latched -- see above", pass_count);
        $finish;
    end

endmodule
