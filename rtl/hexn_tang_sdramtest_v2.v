`timescale 1ns/1ps
// hexn_tang_sdramtest_v2.v -- Board self-test of our SDRAM controller, second version (new file; v1 left untouched). v1 lit all six LEDs on Alan's board (clean read-back at rdlat 2, 3 AND 4), which the simulation did not predict (there only rdlat 3 is clean), so v2 is sharper and reports numbers:
//  - scans rdlat 1 to 6 (read-back of 256 words each) and ALSO runs a NEGATIVE CONTROL: rdlat 3 read-back compared against the WRONG pattern (pattern xor 1); the control must show 256 errors, otherwise the test itself is not discriminating.
//  - sends the result as text on the USB serial port (115200 8N1, pin 69, the BL616's second port, e.g. `stty -F /dev/ttyUSB1 115200 raw; cat /dev/ttyUSB1`) every half second, one line per setting:  "L<setting> err=<4 hex digits> d0=<8 hex digits>". err is how many of the 256 read-backs did not match (0000 = all correct, 0100 = all 256 wrong) and d0 is what was read back at word 0. A correct read of word 0 is 9E3779B1. Lines are L1 to L6 (rdlat 1 to 6) and LN (the negative control).
// LEDs as v1 (lit = true, inverted for the board): led0..2 clean at rdlat 2..4, led3 start-up done, led4 finished, led5 PLL locked.
module hexn_tang_sdramtest_v2 #(parameter GAP = 13_500_000) (   // GAP: clocks between two reports (0.5 s at 27 MHz); the testbench shortens it
    input  wire clk27, output wire uart_tx, output wire [5:0] led,
    output wire O_sdram_clk, output wire O_sdram_cke, output wire O_sdram_cs_n, output wire O_sdram_cas_n, output wire O_sdram_ras_n, output wire O_sdram_wen_n,
    output wire [3:0] O_sdram_dqm, output wire [10:0] O_sdram_addr, output wire [1:0] O_sdram_ba, inout wire [31:0] IO_sdram_dq);
    wire clk, clk_sdram, lock;
    rPLL #(.FCLKIN("27"), .IDIV_SEL(0), .FBDIV_SEL(0), .ODIV_SEL(32), .PSDA_SEL("1000"), .DUTYDA_SEL("1000"), .CLKOUT_FT_DIR(1'b1), .CLKOUTP_FT_DIR(1'b1), .CLKOUT_DLY_STEP(0), .CLKOUTP_DLY_STEP(0), .CLKFB_SEL("internal"), .DYN_SDIV_SEL(2), .DEVICE("GW2AR-18C"))
        pll (.CLKIN(clk27), .CLKFB(1'b0), .RESET(1'b0), .RESET_P(1'b0), .FBDSEL(6'b0), .IDSEL(6'b0), .ODSEL(6'b0), .PSDA(4'b0), .DUTYDA(4'b0), .FDLY(4'b0), .CLKOUT(clk), .CLKOUTP(clk_sdram), .CLKOUTD(), .CLKOUTD3(), .LOCK(lock));
    reg [7:0] rcnt = 8'd0; reg resetn = 1'b0;
    always @(posedge clk) begin if (!lock) begin rcnt <= 8'd0; resetn <= 1'b0; end else if (rcnt != 8'hFF) rcnt <= rcnt + 8'd1; else resetn <= 1'b1; end
    reg cmd_valid = 0, cmd_we = 0; reg [20:0] cmd_addr = 0; reg [31:0] cmd_wdata = 0; reg [2:0] rdlat = 3'd1;
    wire cmd_ready, rd_valid, init_done; wire [31:0] rd_data;
    hexn_sdram_v1 #(.FREQ(27_000_000), .CL(3'd2)) sdram (.clk(clk), .clk_sdram(clk_sdram), .resetn(resetn), .rdlat(rdlat), .cmd_valid(cmd_valid), .cmd_we(cmd_we), .cmd_addr(cmd_addr), .cmd_wdata(cmd_wdata), .cmd_wmask(4'b1111), .cmd_ready(cmd_ready), .rd_valid(rd_valid), .rd_data(rd_data), .init_done(init_done),
        .O_sdram_clk(O_sdram_clk), .O_sdram_cke(O_sdram_cke), .O_sdram_cs_n(O_sdram_cs_n), .O_sdram_ras_n(O_sdram_ras_n), .O_sdram_cas_n(O_sdram_cas_n), .O_sdram_wen_n(O_sdram_wen_n), .IO_sdram_dq(IO_sdram_dq), .O_sdram_addr(O_sdram_addr), .O_sdram_ba(O_sdram_ba), .O_sdram_dqm(O_sdram_dqm));
    function [20:0] adr(input [8:0] k); adr = {k[1:0], 2'b00, k[8:0], k[7:0] ^ 8'hA5}; endfunction
    function [31:0] pat(input [8:0] k); pat = ({23'd0, k} + 32'd1) * 32'h9E3779B1; endfunction
    localparam S_INIT = 3'd0, S_WR = 3'd1, S_RD = 3'd2, S_WAIT = 3'd3, S_NEXT = 3'd4, S_DONE = 3'd5;
    reg [2:0] st = S_INIT; reg [8:0] i = 9'd0; reg [2:0] sel = 3'd0; reg [15:0] errs = 16'd0; reg [3:0] wdog = 4'd0;
    reg [15:0] errv [0:6]; reg [31:0] d0v [0:6]; reg [6:0] okv = 7'd0;
    wire [31:0] want = (sel == 3'd6) ? (pat(i) ^ 32'h1) : pat(i);
    always @(posedge clk) begin
        if (!resetn) begin st <= S_INIT; i <= 9'd0; cmd_valid <= 1'b0; okv <= 7'd0; rdlat <= 3'd1; sel <= 3'd0; errs <= 16'd0; end
        else case (st)
        S_INIT: if (init_done) begin st <= S_WR; i <= 9'd0; end
        S_WR: begin
            if (!cmd_valid) begin cmd_valid <= 1'b1; cmd_we <= 1'b1; cmd_addr <= adr(i); cmd_wdata <= pat(i); end
            else if (cmd_ready) begin cmd_valid <= 1'b0; if (i == 9'd255) begin i <= 9'd0; st <= S_RD; sel <= 3'd0; rdlat <= 3'd1; errs <= 16'd0; end else i <= i + 9'd1; end
        end
        S_RD: begin
            if (!cmd_valid) begin cmd_valid <= 1'b1; cmd_we <= 1'b0; cmd_addr <= adr(i); end
            else if (cmd_ready) begin cmd_valid <= 1'b0; st <= S_WAIT; wdog <= 4'd0; end
        end
        S_WAIT: begin
            wdog <= wdog + 4'd1;
            if (rd_valid) begin if (rd_data !== want) errs <= errs + 16'd1; if (i == 9'd0) d0v[sel] <= rd_data; st <= S_NEXT; end
            else if (wdog == 4'd15) begin errs <= errs + 16'd1; st <= S_NEXT; end
        end
        S_NEXT: begin
            if (i == 9'd255) begin
                errv[sel] <= errs; okv[sel] <= (errs == 16'd0);
                i <= 9'd0; errs <= 16'd0;
                if (sel == 3'd6) st <= S_DONE;
                else begin sel <= sel + 3'd1; rdlat <= (sel == 3'd5) ? 3'd3 : rdlat + 3'd1; st <= S_RD; end   // after setting 6 comes the negative control at rdlat 3
            end else begin i <= i + 9'd1; st <= S_RD; end
        end
        S_DONE: ;
        endcase
    end
    assign led = ~{lock, st == S_DONE, init_done, okv[3], okv[2], okv[1]};
    // ---- serial report: 7 lines of 25 characters, repeated every 0.5 s once the test is done ----
    reg tx_send = 1'b0; wire tx_busy; reg [7:0] tx_d = 8'd0;
    hexn_uart_tx_v1 #(.CLKDIV(234)) utx (.clk(clk), .rst(~resetn), .data(tx_d), .send(tx_send), .txd(uart_tx), .busy(tx_busy));
    reg [2:0] ln = 3'd0; reg [4:0] ps = 5'd0; reg [23:0] gap = 24'd0; reg started = 1'b0;
    function [7:0] hx(input [3:0] v); hx = (v < 4'd10) ? (8'h30 + {4'd0, v}) : (8'h41 + {4'd0, v} - 8'd10); endfunction
    wire [15:0] e = errv[ln]; wire [31:0] dd = d0v[ln];
    reg [7:0] ch;
    always @* begin
        case (ps)
        5'd0: ch = "L"; 5'd1: ch = (ln == 3'd6) ? "N" : (8'h31 + {5'd0, ln}); 5'd2: ch = " ";
        5'd3: ch = "e"; 5'd4: ch = "r"; 5'd5: ch = "r"; 5'd6: ch = "=";
        5'd7: ch = hx(e[15:12]); 5'd8: ch = hx(e[11:8]); 5'd9: ch = hx(e[7:4]); 5'd10: ch = hx(e[3:0]);
        5'd11: ch = " "; 5'd12: ch = "d"; 5'd13: ch = "0"; 5'd14: ch = "=";
        5'd15: ch = hx(dd[31:28]); 5'd16: ch = hx(dd[27:24]); 5'd17: ch = hx(dd[23:20]); 5'd18: ch = hx(dd[19:16]);
        5'd19: ch = hx(dd[15:12]); 5'd20: ch = hx(dd[11:8]); 5'd21: ch = hx(dd[7:4]); 5'd22: ch = hx(dd[3:0]);
        5'd23: ch = 8'h0D; default: ch = 8'h0A;
        endcase
    end
    always @(posedge clk) begin
        tx_send <= 1'b0;
        if (st != S_DONE) begin started <= 1'b0; ln <= 3'd0; ps <= 5'd0; gap <= 24'd0; end
        else if (!started) begin if (gap == GAP) begin started <= 1'b1; gap <= 24'd0; end else gap <= gap + 24'd1; end
        else if (!tx_busy && !tx_send) begin
            tx_d <= ch; tx_send <= 1'b1;
            if (ps == 5'd24) begin ps <= 5'd0; if (ln == 3'd6) begin ln <= 3'd0; started <= 1'b0; end else ln <= ln + 3'd1; end else ps <= ps + 5'd1;
        end
    end
endmodule
