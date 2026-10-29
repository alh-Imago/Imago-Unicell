`timescale 1ns/1ps
// hexn_ddr3_port_v1.v -- adapter between the tier's RAM command port (the protocol of hexn_sdram_v1: when cmd_valid and cmd_ready are both 1 at a clock edge the command is taken; cmd_we 1 = write the 32-bit cmd_wdata, cmd_wmask 1 = write that byte; cmd_we 0 = read, answered by one rd_valid pulse with rd_data; cmd_addr is a 21-bit WORD address) and the pipelined Wishbone port of the UberDDR3 controller on the Kintex card (ypcb_00338_1p1: 576-bit data = 512 data bits + 64 ECC-lane bits, 25-bit LINE address, one request accepted when wb_stb and not wb_stall, answers in order with wb_ack, read data with the ack).
// Mapping: word address a -> line a[20:4], lane a[3:0] (16 words of 32 bits in line bits 511:0; bits 575:512 are carried through unchanged).
// A write is READ-MODIFY-WRITE of the whole line, because the card's top file ties the byte strobe (i_wb_sel) to all ones, so only whole lines can be written without changing that file (the controller itself has the strobe: wb_sel, 1 bit per byte). One command at a time, so no ordering problem arises; the tier runs one RAM command at a time anyway.
// Faults are counted, not hidden: n_timeout (an expected ack did not come within TIMEOUT clocks; the command then ends as if answered, a read returning 0), n_noack is the same for writes. init_done follows ddr_ready (the controller's calibration-complete flag).
module hexn_ddr3_port_v1 #(parameter ADDR_BITS = 25, parameter DATA_BITS = 576, parameter TIMEOUT = 4096) (
    input  wire clk, input wire resetn,
    input  wire cmd_valid, input wire cmd_we, input wire [20:0] cmd_addr, input wire [31:0] cmd_wdata, input wire [3:0] cmd_wmask,
    output wire cmd_ready, output reg rd_valid, output reg [31:0] rd_data, output wire init_done,
    input  wire ddr_ready,
    output reg  wb_stb, output reg wb_we, output reg [ADDR_BITS-1:0] wb_addr, output reg [DATA_BITS-1:0] wb_data, input wire wb_stall, input wire wb_ack, input wire [DATA_BITS-1:0] wb_rdata,
    output reg [31:0] n_rd, output reg [31:0] n_wr, output reg [31:0] n_timeout, output reg [31:0] n_noack);
    localparam S_IDLE = 3'd0, S_RQ = 3'd1, S_RA = 3'd2, S_MOD = 3'd3, S_WQ = 3'd4, S_WA = 3'd5;
    reg [2:0] st; reg we_l; reg [20:0] a_l; reg [31:0] wd_l; reg [3:0] wm_l; reg [DATA_BITS-1:0] line_q; reg [15:0] tmo;
    assign init_done = ddr_ready; assign cmd_ready = (st == S_IDLE) && ddr_ready;
    wire [3:0] lane = a_l[3:0];
    reg [DATA_BITS-1:0] merged; integer b;
    always @* begin
        merged = line_q;
        for (b = 0; b < 4; b = b + 1) if (wm_l[b]) merged[32 * lane + 8 * b +: 8] = wd_l[8 * b +: 8];
    end
    always @(posedge clk) begin
        rd_valid <= 1'b0;
        if (!resetn) begin st <= S_IDLE; wb_stb <= 0; wb_we <= 0; wb_addr <= 0; wb_data <= 0; n_rd <= 0; n_wr <= 0; n_timeout <= 0; n_noack <= 0; tmo <= 0; rd_data <= 0; line_q <= 0; end
        else case (st)
            S_IDLE: if (cmd_valid && ddr_ready) begin
                we_l <= cmd_we; a_l <= cmd_addr; wd_l <= cmd_wdata; wm_l <= cmd_wmask;
                wb_stb <= 1'b1; wb_we <= 1'b0; wb_addr <= {{(ADDR_BITS-17){1'b0}}, cmd_addr[20:4]}; st <= S_RQ;      // read the line (for a write this is the read of the read-modify-write)
            end
            S_RQ: if (!wb_stall) begin wb_stb <= 1'b0; tmo <= 0; st <= S_RA; end                                    // request taken at this edge
            S_RA: begin
                tmo <= tmo + 16'd1;
                if (wb_ack) begin
                    line_q <= wb_rdata;
                    if (we_l) st <= S_MOD;
                    else begin rd_data <= wb_rdata[32 * lane +: 32]; rd_valid <= 1'b1; n_rd <= n_rd + 32'd1; st <= S_IDLE; end
                end else if (tmo == TIMEOUT) begin n_timeout <= n_timeout + 32'd1; rd_data <= 32'd0; rd_valid <= !we_l; st <= S_IDLE; end
            end
            S_MOD: begin wb_data <= merged; wb_we <= 1'b1; wb_stb <= 1'b1; st <= S_WQ; end                          // same line address as the read
            S_WQ: if (!wb_stall) begin wb_stb <= 1'b0; wb_we <= 1'b0; tmo <= 0; st <= S_WA; end
            S_WA: begin
                tmo <= tmo + 16'd1;
                if (wb_ack) begin n_wr <= n_wr + 32'd1; st <= S_IDLE; end
                else if (tmo == TIMEOUT) begin n_wr <= n_wr + 32'd1; n_noack <= n_noack + 32'd1; st <= S_IDLE; end
            end
            default: st <= S_IDLE;
        endcase
    end
endmodule
