`timescale 1ns / 1ps
// tb_top_arria10_pcie_mux.v -- verifies the NEW 3-way cpu_bus arbitration
// mux (UART + JTAG + PCIe) added when pcie_unicell_bridge was wired into
// top_arria10_zone1_v3.v. Forces each master's valid/bus/data directly via
// hierarchical paths (bypassing the real bridge modules, which aren't the
// thing under test here) and checks cpu_bus/cpu_data/cpu_valid come out
// matching the documented priority: JTAG > PCIe > UART.
module tb_top_arria10_pcie_mux;

reg CLK_100M = 0;
reg UART_RX = 1;
wire UART_TX, LED0_N, LED1_N;

always #5 CLK_100M = ~CLK_100M;

top_arria10_zone1 dut (
    .CLK_100M(CLK_100M),
    .UART_RX(UART_RX),
    .UART_TX(UART_TX),
    .LED0_N(LED0_N),
    .LED1_N(LED1_N)
);

integer errors = 0;

task check(input [31:0] exp_bus, input [31:0] exp_data, input exp_valid, input [127:0] label);
    begin
        if (dut.cpu_bus !== exp_bus || dut.cpu_data !== exp_data || dut.cpu_valid !== exp_valid) begin
            $display("FAIL [%0s]: expected bus=%h data=%h valid=%b, got bus=%h data=%h valid=%b",
                      label, exp_bus, exp_data, exp_valid, dut.cpu_bus, dut.cpu_data, dut.cpu_valid);
            errors = errors + 1;
        end else begin
            $display("PASS [%0s]: bus=%h data=%h valid=%b", label, dut.cpu_bus, dut.cpu_data, dut.cpu_valid);
        end
    end
endtask

initial begin
    // Ensure all three masters start deasserted (matches real reset state)
    force dut.u_valid = 0; force dut.j_valid = 0; force dut.p_valid = 0;
    force dut.u_bus = 32'h0; force dut.u_data = 32'h0;
    force dut.j_bus = 32'h0; force dut.j_data = 32'h0;
    force dut.p_bus = 32'h0; force dut.p_data = 32'h0;
    #20;
    check(32'h0, 32'h0, 1'b0, "all idle");

    // UART only
    force dut.u_valid = 1; force dut.u_bus = 32'hAAAA0001; force dut.u_data = 32'h11111111;
    #1;
    check(32'hAAAA0001, 32'h11111111, 1'b1, "UART only");

    // JTAG asserts too -- JTAG must win (highest priority)
    force dut.j_valid = 1; force dut.j_bus = 32'hBBBB0002; force dut.j_data = 32'h22222222;
    #1;
    check(32'hBBBB0002, 32'h22222222, 1'b1, "JTAG beats UART");

    // PCIe also asserts -- JTAG must STILL win (JTAG is top priority)
    force dut.p_valid = 1; force dut.p_bus = 32'hCCCC0003; force dut.p_data = 32'h33333333;
    #1;
    check(32'hBBBB0002, 32'h22222222, 1'b1, "JTAG beats UART+PCIe");

    // JTAG deasserts -- PCIe must now win over UART
    force dut.j_valid = 0;
    #1;
    check(32'hCCCC0003, 32'h33333333, 1'b1, "PCIe beats UART (JTAG gone)");

    // PCIe deasserts too -- back to UART only
    force dut.p_valid = 0;
    #1;
    check(32'hAAAA0001, 32'h11111111, 1'b1, "back to UART only");

    // Only PCIe asserts, nothing else -- PCIe must drive cpu_bus alone.
    // (cpu_bus/cpu_data fall through to whatever the lowest-priority
    // master's bus happens to hold when nothing is valid -- this is the
    // SAME pre-existing contract the original 2-way mux already had
    // (cpu_bus = j_valid ? j_bus : u_bus, never gated by u_valid either);
    // only cpu_valid is the real, meaningful signal, so only that's
    // checked here, not bus/data, which are legitimately don't-care.)
    force dut.u_valid = 0;
    #1;
    if (dut.cpu_valid !== 1'b0) begin
        $display("FAIL [all deasserted again]: expected cpu_valid=0, got %b", dut.cpu_valid);
        errors = errors + 1;
    end else begin
        $display("PASS [all deasserted again]: cpu_valid=0 (bus/data don't-care, as expected)");
    end
    force dut.p_valid = 1; force dut.p_bus = 32'hDDDD0004; force dut.p_data = 32'h44444444;
    #1;
    check(32'hDDDD0004, 32'h44444444, 1'b1, "PCIe alone");

    // Only JTAG asserts, nothing else
    force dut.p_valid = 0;
    force dut.j_valid = 1; force dut.j_bus = 32'hEEEE0005; force dut.j_data = 32'h55555555;
    #1;
    check(32'hEEEE0005, 32'h55555555, 1'b1, "JTAG alone");

    $display("");
    if (errors == 0)
        $display("ALL CHECKS PASSED (0 errors)");
    else
        $display("%0d CHECK(S) FAILED", errors);

    $finish;
end

endmodule
