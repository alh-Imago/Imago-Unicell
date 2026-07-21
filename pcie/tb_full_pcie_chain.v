`timescale 1ns / 1ps
// tb_full_pcie_chain.v -- elaboration-only check of the complete chain:
// stub Hard IP -> stub PIO bridge -> real pcie_hip_wrapper.v -> real
// pcie_unicell_bridge.v. Confirms every connection across all four modules
// is consistent (no width/name mismatches anywhere in the real RTL), using
// stub blackboxes only for the two components that need a real Quartus
// license to generate.
module tb_full_pcie_chain;

reg  refclk = 0;
reg  npor = 1;
reg  pin_perst = 1;
reg  [7:0] pcie_rx_p = 8'h0;
wire [7:0] pcie_tx_p;

wire app_clk, app_rst;
wire [15:0] rxm_address;
wire [3:0]  rxm_byteenable;
wire [31:0] rxm_writedata;
wire        rxm_write, rxm_read;
wire [31:0] rxm_readdata;
wire        rxm_readdatavalid, rxm_waitrequest;

pcie_hip_wrapper dut_wrapper (
    .refclk(refclk), .npor(npor), .pin_perst(pin_perst),
    .pcie_rx_p(pcie_rx_p), .pcie_tx_p(pcie_tx_p),
    .app_clk(app_clk), .app_rst(app_rst),
    .rxm_address(rxm_address), .rxm_byteenable(rxm_byteenable),
    .rxm_writedata(rxm_writedata), .rxm_write(rxm_write), .rxm_read(rxm_read),
    .rxm_readdata(rxm_readdata), .rxm_readdatavalid(rxm_readdatavalid),
    .rxm_waitrequest(rxm_waitrequest)
);

wire [31:0] cpu_bus, cpu_data;
wire        cpu_valid;

pcie_unicell_bridge dut_bridge (
    .clk(app_clk), .rst(app_rst),
    .avs_address(rxm_address), .avs_byteenable(rxm_byteenable),
    .avs_writedata(rxm_writedata), .avs_write(rxm_write), .avs_read(rxm_read),
    .avs_burstcount(6'd1),
    .avs_readdata(rxm_readdata), .avs_readdatavalid(rxm_readdatavalid),
    .avs_waitrequest(rxm_waitrequest),
    .cpu_bus(cpu_bus), .cpu_data(cpu_data), .cpu_valid(cpu_valid),
    .out_addr(16'h0), .out_data(32'h0), .out_valid(1'b0)
);

initial begin
    #10;
    $display("Full chain (stub HIP -> stub PIO bridge -> real wrapper -> real pcie_unicell_bridge) elaborated cleanly.");
    $finish;
end

endmodule
