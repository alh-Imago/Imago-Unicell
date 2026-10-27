`timescale 1ns/1ps
// hexn_tang_sdtest_v1.v -- Board test of the SD card tier for Hex-N, reusing the project's proven sd_spi_v1 (fpga/verilog, ledger #1036; not rewritten). Tests a 64 GB SDXC card, which sd_spi_v1 has not been tried with.
// For three regions of the card (low, about 26 GB up, about 51 GB up) it WRITES NB raw blocks of a known pattern, READS them back, counts mismatches and times both phases in 27 MHz clocks.
// WARNING: it overwrites 3 x NB raw 512-byte blocks (default 8 blocks at block 4096, 50,000,000 and 100,000,000). On a FAT-formatted card that can damage a file there; use a spare card or reformat afterwards.
// Serial report (115200 8N1, pin 69; e.g. `stty -F /dev/ttyUSB1 115200 raw; cat /dev/ttyUSB1`), every half second:
//   "SD rdy=1 err=00 cmd=00 rx=00"   card ready flag, error code, command and last byte at the error
//   "R0 err=0000 wr=XXXXXXXX rd=XXXXXXXX"  per region: words that did not match (0000 = all correct), clocks used to write / read NB blocks
// LEDs (lit = true): led0 card ready, led1..3 regions 0..2 clean, led4 finished, led5 card error.
module hexn_tang_sdtest_v1 #(parameter NB = 8, parameter B0 = 4096, parameter B1 = 50_000_000, parameter B2 = 100_000_000, parameter GAP = 13_500_000, parameter INIT_DIV = 34, parameter FAST_DIV = 1) (
    input wire clk27, output wire uart_tx, output wire [5:0] led,
    output wire sd_clk, output wire sd_mosi, input wire sd_miso, output wire sd_cs_n);
    wire clk = clk27;
    reg [7:0] rc = 8'd0; reg rst = 1'b1;
    always @(posedge clk) if (rc != 8'hFF) rc <= rc + 8'd1; else rst <= 1'b0;
    wire ready, error, busy, block_done, w_valid; wire [4:0] err_code; wire [5:0] err_cmd; wire [7:0] err_rx; wire [31:0] w_data; wire [6:0] w_index, src_addr;
    reg rd_req = 0, wr_req = 0; reg [31:0] block = 0; reg [7:0] bi = 8'd0;      // bi: block number inside the region
    function [31:0] pat(input [7:0] b, input [6:0] w, input [1:0] reg_n); pat = ({16'd0, reg_n, b[5:0], w} + 32'd1) * 32'h9E3779B1; endfunction
    reg [1:0] rg = 2'd0;
    wire [31:0] src_data = pat(bi, src_addr, rg);
    sd_spi_v1 #(.INIT_DIV(INIT_DIV), .FAST_DIV(FAST_DIV)) S (.clk(clk), .rst(rst), .sd_clk(sd_clk), .sd_mosi(sd_mosi), .sd_miso(sd_miso), .sd_cs_n(sd_cs_n),
        .ready(ready), .error(error), .err_code(err_code), .err_cmd(err_cmd), .err_rx(err_rx), .busy(busy), .rd_req(rd_req), .wr_req(wr_req), .block(block),
        .block_done(block_done), .w_valid(w_valid), .w_data(w_data), .w_index(w_index), .src_addr(src_addr), .src_data(src_data));
    localparam S_WAIT = 3'd0, S_WR = 3'd1, S_WRW = 3'd2, S_RD = 3'd3, S_RDW = 3'd4, S_NEXT = 3'd5, S_DONE = 3'd6;
    reg [2:0] st = S_WAIT; reg [31:0] tcnt = 0;
    reg [15:0] errv [0:2]; reg [31:0] wrt [0:2]; reg [31:0] rdt [0:2]; reg [2:0] clean = 3'd0; reg [15:0] errs = 16'd0;
    wire [31:0] base = (rg == 2'd0) ? B0 : (rg == 2'd1) ? B1 : B2;
    always @(posedge clk) begin
        rd_req <= 1'b0; wr_req <= 1'b0;
        if (rst) begin st <= S_WAIT; rg <= 2'd0; bi <= 8'd0; errs <= 16'd0; clean <= 3'd0; end
        else case (st)
        S_WAIT: if (ready) begin st <= S_WR; bi <= 8'd0; tcnt <= 32'd0; end
        S_WR: begin block <= base + bi; wr_req <= 1'b1; st <= S_WRW; end
        S_WRW: begin tcnt <= tcnt + 32'd1; if (block_done) begin
                    if (bi == NB - 1) begin wrt[rg] <= tcnt + 32'd1; bi <= 8'd0; tcnt <= 32'd0; errs <= 16'd0; st <= S_RD; end else begin bi <= bi + 8'd1; st <= S_WR; end end end
        S_RD: begin block <= base + bi; rd_req <= 1'b1; st <= S_RDW; end
        S_RDW: begin tcnt <= tcnt + 32'd1;
                if (w_valid && w_data !== pat(bi, w_index, rg)) errs <= errs + 16'd1;
                if (block_done) begin
                    if (bi == NB - 1) begin rdt[rg] <= tcnt + 32'd1; errv[rg] <= errs; clean[rg] <= (errs == 16'd0); st <= S_NEXT; end else begin bi <= bi + 8'd1; st <= S_RD; end end end
        S_NEXT: if (rg == 2'd2) st <= S_DONE; else begin rg <= rg + 2'd1; bi <= 8'd0; tcnt <= 32'd0; st <= S_WR; end
        S_DONE: ;
        endcase
        if (error && st != S_DONE) st <= S_DONE;    // a card error ends the test; the report shows it
    end
    assign led = ~{error, st == S_DONE, clean[2], clean[1], clean[0], ready};
    // ---- serial report: lines 0..3, 36 characters max each ----
    reg tx_send = 1'b0; wire tx_busy; reg [7:0] tx_d = 8'd0;
    hexn_uart_tx_v1 #(.CLKDIV(234)) utx (.clk(clk), .rst(rst), .data(tx_d), .send(tx_send), .txd(uart_tx), .busy(tx_busy));
    reg [1:0] ln = 2'd0; reg [5:0] ps = 6'd0; reg [23:0] gap = 24'd0; reg started = 1'b0;
    function [7:0] hx(input [3:0] v); hx = (v < 4'd10) ? (8'h30 + {4'd0, v}) : (8'h41 + {4'd0, v} - 8'd10); endfunction
    wire [1:0] r = ln - 2'd1;
    wire [15:0] e = errv[r]; wire [31:0] wt = wrt[r], rt = rdt[r];
    reg [7:0] ch; reg last;
    always @* begin
        ch = 8'h20; last = 1'b0;
        if (ln == 2'd0) begin
            case (ps)
            0: ch = "S"; 1: ch = "D"; 3: ch = "r"; 4: ch = "d"; 5: ch = "y"; 6: ch = "="; 7: ch = hx({3'd0, ready});
            9: ch = "e"; 10: ch = "r"; 11: ch = "r"; 12: ch = "="; 13: ch = hx({3'd0, err_code[4]}); 14: ch = hx(err_code[3:0]);
            16: ch = "c"; 17: ch = "m"; 18: ch = "d"; 19: ch = "="; 20: ch = hx({2'd0, err_cmd[5:4]}); 21: ch = hx(err_cmd[3:0]);
            23: ch = "r"; 24: ch = "x"; 25: ch = "="; 26: ch = hx(err_rx[7:4]); 27: ch = hx(err_rx[3:0]);
            28: ch = 8'h0D; 29: begin ch = 8'h0A; last = 1'b1; end default: ch = 8'h20;
            endcase
        end else begin
            case (ps)
            0: ch = "R"; 1: ch = 8'h30 + {6'd0, r};
            3: ch = "e"; 4: ch = "r"; 5: ch = "r"; 6: ch = "="; 7: ch = hx(e[15:12]); 8: ch = hx(e[11:8]); 9: ch = hx(e[7:4]); 10: ch = hx(e[3:0]);
            12: ch = "w"; 13: ch = "r"; 14: ch = "="; 15: ch = hx(wt[31:28]); 16: ch = hx(wt[27:24]); 17: ch = hx(wt[23:20]); 18: ch = hx(wt[19:16]); 19: ch = hx(wt[15:12]); 20: ch = hx(wt[11:8]); 21: ch = hx(wt[7:4]); 22: ch = hx(wt[3:0]);
            24: ch = "r"; 25: ch = "d"; 26: ch = "="; 27: ch = hx(rt[31:28]); 28: ch = hx(rt[27:24]); 29: ch = hx(rt[23:20]); 30: ch = hx(rt[19:16]); 31: ch = hx(rt[15:12]); 32: ch = hx(rt[11:8]); 33: ch = hx(rt[7:4]); 34: ch = hx(rt[3:0]);
            35: ch = 8'h0D; 36: begin ch = 8'h0A; last = 1'b1; end default: ch = 8'h20;
            endcase
        end
    end
    always @(posedge clk) begin
        tx_send <= 1'b0;
        if (st != S_DONE) begin started <= 1'b0; ln <= 2'd0; ps <= 6'd0; gap <= 24'd0; end
        else if (!started) begin if (gap == GAP) begin started <= 1'b1; gap <= 24'd0; end else gap <= gap + 24'd1; end
        else if (!tx_busy && !tx_send) begin
            tx_d <= ch; tx_send <= 1'b1;
            if (last) begin ps <= 6'd0; if (ln == 2'd3) begin ln <= 2'd0; started <= 1'b0; end else ln <= ln + 2'd1; end else ps <= ps + 6'd1;
        end
    end
endmodule
