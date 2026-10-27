`timescale 1ns/1ps
// hexn_sdram_v1.v -- Our own word-wide SDR SDRAM controller for the Tang Nano 20K's embedded 64 Mbit (2K rows x 256 columns x 4 banks x 32 bits) SDRAM. Written from the public Micron SDR SDRAM datasheet (command codes, mode register, start-up order, refresh) and NOT from the NESTang source (GPL v3); its timing is deliberately RELAXED (every operation takes 8 clocks, about 300 ns at 27 MHz, about 13 MB/s) because Hex-N needs no cycle-exact bus.
// User side: when cmd_ready is 1 and cmd_valid is 1 at a clock edge, the command is taken: cmd_we 1 = write the 32-bit cmd_wdata (cmd_wmask 1 = write that byte), cmd_we 0 = read; cmd_addr is a 21-bit WORD address {bank[1:0], row[10:0], column[7:0]}. A read answers with rd_valid for one clock and rd_data, RDLAT+... clocks later (see the testbench for the measured figure). cmd_ready drops while an operation or a refresh runs.
// Chip side: SDRAM clock is clk_sdram, which must be the core clock shifted by 180 degrees (a PLL output on the board; the inverted clock in simulation). Commands change on the rising edge of clk and are sampled by the chip half a clock later. Read and write both use auto-precharge, burst length 1, CAS latency CL (2).
// Start-up: 200 us wait, PRECHARGE ALL, 8 AUTO REFRESH, LOAD MODE REGISTER, wait, ready. Refresh: one AUTO REFRESH every 7.5 us (the chip needs 4,096 per 64 ms on the NESTang note and 8,192 per 64 ms on the Micron 256 Mbit part; 7.5 us gives 8,533 per 64 ms), taken between operations.
// rdlat (input, 2 to 5, 3 in simulation) is the number of clocks after the READ command's clock edge at which the data bus is sampled: it depends on the board's clock phase and trace delay, so it is an input to tune in bring-up; hold it steady while an operation runs.
module hexn_sdram_v1 #(parameter FREQ = 27_000_000, parameter [2:0] CL = 3'd2) (
    input  wire        clk, input wire clk_sdram, input wire resetn, input wire [2:0] rdlat,
    input  wire        cmd_valid, input wire cmd_we, input wire [20:0] cmd_addr, input wire [31:0] cmd_wdata, input wire [3:0] cmd_wmask,
    output wire        cmd_ready, output reg rd_valid, output reg [31:0] rd_data, output reg init_done,
    output wire        O_sdram_clk, output wire O_sdram_cke, output wire O_sdram_cs_n,
    output reg         O_sdram_ras_n, output reg O_sdram_cas_n, output reg O_sdram_wen_n,
    inout  wire [31:0] IO_sdram_dq, output reg [10:0] O_sdram_addr, output reg [1:0] O_sdram_ba, output reg [3:0] O_sdram_dqm);
    localparam INIT_CYC = FREQ / 5000;                    // 200 us in clocks
    localparam REFI = FREQ / 100000 * 75 / 100;            // 7.5 us in clocks
    localparam S_WAIT = 3'd0, S_PRE = 3'd1, S_REF = 3'd2, S_MRS = 3'd3, S_IDLE = 3'd4, S_OP = 3'd5, S_RF = 3'd6;
    reg [2:0] st; reg [15:0] c; reg [3:0] nref; reg [15:0] tcnt; reg ref_due;
    reg we_l; reg [20:0] addr_l; reg [31:0] wdata_l; reg [3:0] wmask_l;
    reg dq_oe; reg [31:0] dq_out;
    assign IO_sdram_dq = dq_oe ? dq_out : 32'bz;
    assign O_sdram_clk = clk_sdram; assign O_sdram_cke = 1'b1; assign O_sdram_cs_n = 1'b0;
    assign cmd_ready = (st == S_IDLE) && !ref_due;
    task nop; begin O_sdram_ras_n <= 1'b1; O_sdram_cas_n <= 1'b1; O_sdram_wen_n <= 1'b1; end endtask
    always @(posedge clk) begin
        nop; rd_valid <= 1'b0; O_sdram_dqm <= 4'b0000; dq_oe <= 1'b0;
        if (st < S_IDLE) ref_due <= 1'b0;
        else if (tcnt == REFI - 1) ref_due <= 1'b1;
        tcnt <= (tcnt == REFI - 1) ? 16'd0 : tcnt + 16'd1;
        case (st)
        S_WAIT: begin c <= c + 16'd1; init_done <= 1'b0; if (c == INIT_CYC - 1) begin st <= S_PRE; c <= 16'd0; end end
        S_PRE: begin
            if (c == 0) begin O_sdram_ras_n <= 1'b0; O_sdram_cas_n <= 1'b1; O_sdram_wen_n <= 1'b0; O_sdram_addr <= 11'h400; O_sdram_ba <= 2'b00; end   // PRECHARGE all banks (A10 = 1)
            c <= c + 16'd1; if (c == 3) begin st <= S_REF; c <= 16'd0; nref <= 4'd0; end
        end
        S_REF: begin
            if (c == 0) begin O_sdram_ras_n <= 1'b0; O_sdram_cas_n <= 1'b0; O_sdram_wen_n <= 1'b1; end                                                   // AUTO REFRESH
            c <= c + 16'd1;
            if (c == 5) begin c <= 16'd0; nref <= nref + 4'd1; if (nref == 4'd7) st <= S_MRS; end
        end
        S_MRS: begin
            if (c == 0) begin O_sdram_ras_n <= 1'b0; O_sdram_cas_n <= 1'b0; O_sdram_wen_n <= 1'b0; O_sdram_addr <= {4'b0000, CL, 4'b0000}; O_sdram_ba <= 2'b00; end   // LOAD MODE REGISTER: burst 1, sequential, CL, normal
            c <= c + 16'd1; if (c == 3) begin st <= S_IDLE; init_done <= 1'b1; end
        end
        S_IDLE: begin
            if (ref_due) begin O_sdram_ras_n <= 1'b0; O_sdram_cas_n <= 1'b0; O_sdram_wen_n <= 1'b1; st <= S_RF; c <= 16'd1; ref_due <= 1'b0; end
            else if (cmd_valid) begin
                we_l <= cmd_we; addr_l <= cmd_addr; wdata_l <= cmd_wdata; wmask_l <= cmd_wmask;
                O_sdram_ras_n <= 1'b0; O_sdram_cas_n <= 1'b1; O_sdram_wen_n <= 1'b1; O_sdram_ba <= cmd_addr[20:19]; O_sdram_addr <= cmd_addr[18:8];     // ACTIVE
                st <= S_OP; c <= 16'd1;
            end
        end
        S_OP: begin
            c <= c + 16'd1;
            if (c == 2) begin                                                                                                      // READ or WRITE with auto-precharge, 2 clocks after ACTIVE
                O_sdram_ras_n <= 1'b1; O_sdram_cas_n <= 1'b0; O_sdram_wen_n <= ~we_l; O_sdram_ba <= addr_l[20:19]; O_sdram_addr <= {1'b1, 2'b00, addr_l[7:0]};
                if (we_l) begin dq_oe <= 1'b1; dq_out <= wdata_l; O_sdram_dqm <= ~wmask_l; end
            end
            if (!we_l && c == 2 + rdlat) begin rd_data <= IO_sdram_dq; rd_valid <= 1'b1; end
            if (c == 8) st <= S_IDLE;
        end
        S_RF: begin c <= c + 16'd1; if (c == 5) st <= S_IDLE; end
        default: st <= S_WAIT;
        endcase
        if (!resetn) begin st <= S_WAIT; c <= 16'd0; tcnt <= 16'd0; ref_due <= 1'b0; init_done <= 1'b0; rd_valid <= 1'b0; dq_oe <= 1'b0; O_sdram_dqm <= 4'b0000; nop; end
    end
endmodule
