`timescale 1ns/1ps
// hexn_tang_sdramtest_v1.v -- Board self-test of our SDRAM controller (rtl/hexn_sdram_v1.v) on the Tang Nano 20K's embedded SDRAM; no host needed, the result shows on the six LEDs. New file; written for Hex-N from public sources, not from NESTang.
// Clocks: the PLL takes the 27 MHz board clock and gives CLKOUT (27 MHz, the core clock) and CLKOUTP (the same clock shifted 180 degrees, the SDRAM clock). PLL values: IDIV_SEL 0, FBDIV_SEL 0, ODIV_SEL 32 (VCO 864 MHz) as the open-source Apycula `gowin_pll` tool gives for 27 -> 27 MHz; PSDA_SEL 1000 (8 steps of 22.5 degrees = 180) is a first guess to be proven on the board.
// Test: after start-up, write 256 words (pattern from the index, over all four banks), then read all 256 back three times, once for each read-sampling setting rdlat = 2, 3, 4, and count mismatches.
// LEDs (the Tang's LEDs are lit by a 0, so the outputs are inverted here: lit = true): led[0] read-back clean with rdlat 2, led[1] clean with rdlat 3, led[2] clean with rdlat 4, led[3] SDRAM start-up done, led[4] test finished, led[5] PLL locked. Expected on a working board: led[3], led[4], led[5] lit and at least one of led[0..2] lit (the one or two settings that sample inside the data window). Nothing lit but led[5] means the SDRAM never finished start-up; led[3] and led[4] lit with none of led[0..2] means start-up works but reads come back wrong (clock phase, or the part's timing).
module hexn_tang_sdramtest_v1 (
    input  wire clk27, output wire [5:0] led,
    output wire O_sdram_clk, output wire O_sdram_cke, output wire O_sdram_cs_n, output wire O_sdram_cas_n, output wire O_sdram_ras_n, output wire O_sdram_wen_n,
    output wire [3:0] O_sdram_dqm, output wire [10:0] O_sdram_addr, output wire [1:0] O_sdram_ba, inout wire [31:0] IO_sdram_dq);
    wire clk, clk_sdram, lock;
    rPLL #(.FCLKIN("27"), .IDIV_SEL(0), .FBDIV_SEL(0), .ODIV_SEL(32), .PSDA_SEL("1000"), .DUTYDA_SEL("1000"), .CLKOUT_FT_DIR(1'b1), .CLKOUTP_FT_DIR(1'b1), .CLKOUT_DLY_STEP(0), .CLKOUTP_DLY_STEP(0), .CLKFB_SEL("internal"), .DYN_SDIV_SEL(2), .DEVICE("GW2AR-18C"))
        pll (.CLKIN(clk27), .CLKFB(1'b0), .RESET(1'b0), .RESET_P(1'b0), .FBDSEL(6'b0), .IDSEL(6'b0), .ODSEL(6'b0), .PSDA(4'b0), .DUTYDA(4'b0), .FDLY(4'b0), .CLKOUT(clk), .CLKOUTP(clk_sdram), .CLKOUTD(), .CLKOUTD3(), .LOCK(lock));
    reg [7:0] rcnt = 8'd0; reg resetn = 1'b0;
    always @(posedge clk) begin if (!lock) begin rcnt <= 8'd0; resetn <= 1'b0; end else if (rcnt != 8'hFF) rcnt <= rcnt + 8'd1; else resetn <= 1'b1; end
    reg cmd_valid = 0, cmd_we = 0; reg [20:0] cmd_addr = 0; reg [31:0] cmd_wdata = 0; reg [2:0] rdlat = 3'd3;
    wire cmd_ready, rd_valid, init_done; wire [31:0] rd_data;
    hexn_sdram_v1 #(.FREQ(27_000_000), .CL(3'd2)) sdram (.clk(clk), .clk_sdram(clk_sdram), .resetn(resetn), .rdlat(rdlat), .cmd_valid(cmd_valid), .cmd_we(cmd_we), .cmd_addr(cmd_addr), .cmd_wdata(cmd_wdata), .cmd_wmask(4'b1111), .cmd_ready(cmd_ready), .rd_valid(rd_valid), .rd_data(rd_data), .init_done(init_done),
        .O_sdram_clk(O_sdram_clk), .O_sdram_cke(O_sdram_cke), .O_sdram_cs_n(O_sdram_cs_n), .O_sdram_ras_n(O_sdram_ras_n), .O_sdram_cas_n(O_sdram_cas_n), .O_sdram_wen_n(O_sdram_wen_n), .IO_sdram_dq(IO_sdram_dq), .O_sdram_addr(O_sdram_addr), .O_sdram_ba(O_sdram_ba), .O_sdram_dqm(O_sdram_dqm));
    function [20:0] adr(input [8:0] k); adr = {k[1:0], 2'b00, k[8:0], k[7:0] ^ 8'hA5}; endfunction
    function [31:0] pat(input [8:0] k); pat = ({23'd0, k} + 32'd1) * 32'h9E3779B1; endfunction
    localparam S_INIT = 3'd0, S_WR = 3'd1, S_RD = 3'd2, S_WAIT = 3'd3, S_NEXT = 3'd4, S_DONE = 3'd5;
    reg [2:0] st = S_INIT; reg [8:0] i = 9'd0; reg [15:0] errs = 16'd0; reg [2:0] clean = 3'b000; reg [3:0] wdog = 4'd0;
    always @(posedge clk) begin
        if (!resetn) begin st <= S_INIT; i <= 9'd0; cmd_valid <= 1'b0; clean <= 3'b000; rdlat <= 3'd2; errs <= 16'd0; end
        else case (st)
        S_INIT: if (init_done) begin st <= S_WR; i <= 9'd0; end
        S_WR: begin
            if (!cmd_valid) begin cmd_valid <= 1'b1; cmd_we <= 1'b1; cmd_addr <= adr(i); cmd_wdata <= pat(i); end
            else if (cmd_ready) begin cmd_valid <= 1'b0; if (i == 9'd255) begin i <= 9'd0; st <= S_RD; rdlat <= 3'd2; errs <= 16'd0; end else i <= i + 9'd1; end
        end
        S_RD: begin
            if (!cmd_valid) begin cmd_valid <= 1'b1; cmd_we <= 1'b0; cmd_addr <= adr(i); end
            else if (cmd_ready) begin cmd_valid <= 1'b0; st <= S_WAIT; wdog <= 4'd0; end
        end
        S_WAIT: begin
            wdog <= wdog + 4'd1;
            if (rd_valid) begin if (rd_data !== pat(i)) errs <= errs + 16'd1; st <= S_NEXT; end
            else if (wdog == 4'd15) begin errs <= errs + 16'd1; st <= S_NEXT; end
        end
        S_NEXT: begin
            if (i == 9'd255) begin
                clean[rdlat - 3'd2] <= (errs == 16'd0);
                i <= 9'd0; errs <= 16'd0;
                if (rdlat == 3'd4) st <= S_DONE; else begin rdlat <= rdlat + 3'd1; st <= S_RD; end
            end else begin i <= i + 9'd1; st <= S_RD; end
        end
        S_DONE: ;
        endcase
    end
    assign led = ~{lock, st == S_DONE, init_done, clean[2], clean[1], clean[0]};
endmodule
