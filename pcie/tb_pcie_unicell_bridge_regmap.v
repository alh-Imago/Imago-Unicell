`timescale 1ns / 1ps
module tb_pcie_unicell_bridge_regmap;

reg         clk = 0;
reg         rst = 1;
reg  [15:0] avs_address = 16'h0;
reg  [3:0]  avs_byteenable = 4'hF;
reg  [31:0] avs_writedata = 32'h0;
reg         avs_write = 0;
reg         avs_read = 0;
wire [31:0] avs_readdata;
wire        avs_readdatavalid;
wire        avs_waitrequest;
wire [31:0] cpu_bus, cpu_data;
wire        cpu_valid;
reg  [15:0] out_addr = 16'h0;
reg  [31:0] out_data = 32'h0;
reg         out_valid = 1'b0;

always #5 clk = ~clk;

pcie_unicell_bridge dut (
    .clk(clk), .rst(rst),
    .avs_address(avs_address), .avs_byteenable(avs_byteenable),
    .avs_writedata(avs_writedata), .avs_write(avs_write), .avs_read(avs_read),
    .avs_burstcount(6'd1),
    .avs_readdata(avs_readdata), .avs_readdatavalid(avs_readdatavalid),
    .avs_waitrequest(avs_waitrequest),
    .cpu_bus(cpu_bus), .cpu_data(cpu_data), .cpu_valid(cpu_valid),
    .out_addr(out_addr), .out_data(out_data), .out_valid(out_valid)
);

integer errors = 0;
task check(input [255:0] label, input cond);
    begin
        if (!cond) begin
            $display("FAIL: %0s", label);
            errors = errors + 1;
        end else begin
            $display("PASS: %0s", label);
        end
    end
endtask

task write_reg(input [15:0] addr, input [31:0] data);
    begin
        @(posedge clk);
        #1;
        avs_address = addr; avs_writedata = data; avs_write = 1'b1;
        @(posedge clk);
        #1;
        avs_write = 1'b0;
    end
endtask

task read_reg(input [15:0] addr);
    begin
        @(posedge clk);
        avs_address = addr; avs_read = 1'b1;
        @(posedge clk);
        avs_read = 1'b0;
        @(posedge clk);
    end
endtask

initial begin
    #12 rst = 0;

    write_reg(16'h0, 32'hDEADBEEF);
    #1;
    check("CMD_DATA write does not fire cpu_valid", cpu_valid === 1'b0);

    @(posedge clk);
    write_reg(16'h4, 32'hCAFEF00D);
    #1;
    check("CMD_BUS write fires cpu_valid", cpu_valid === 1'b1);
    check("cpu_bus == the CMD_BUS write value", cpu_bus === 32'hCAFEF00D);
    check("cpu_data == the previously-staged CMD_DATA value", cpu_data === 32'hDEADBEEF);

    @(posedge clk); #1;
    check("cpu_valid deasserts the cycle after firing (one-shot pulse)", cpu_valid === 1'b0);

    read_reg(16'h0);
    check("CMD_DATA readback echoes last-staged value", avs_readdata === 32'hDEADBEEF);
    check("readdatavalid asserted on the read", avs_readdatavalid === 1'b1);

    read_reg(16'h4);
    check("CMD_BUS readback echoes last-written value", avs_readdata === 32'hCAFEF00D);

    out_addr = 16'h1234; out_valid = 1'b1;
    read_reg(16'h8);
    check("STATUS_ADDR_VALID readback: addr bits correct", avs_readdata[15:0] === 16'h1234);
    check("STATUS_ADDR_VALID readback: valid bit correct", avs_readdata[16] === 1'b1);

    out_data = 32'hFEEDFACE;
    read_reg(16'hC);
    check("STATUS_DATA readback reflects out_data", avs_readdata === 32'hFEEDFACE);

    write_reg(16'h8, 32'hFFFFFFFF);
    #1;
    check("STATUS register write does not fire cpu_valid", cpu_valid === 1'b0);
    read_reg(16'h8);
    check("STATUS_ADDR_VALID unaffected by the write attempt", avs_readdata[15:0] === 16'h1234);

    $display("");
    if (errors == 0)
        $display("ALL CHECKS PASSED (0 errors)");
    else
        $display("%0d CHECK(S) FAILED", errors);
    $finish;
end

endmodule
