`timescale 1ns/1ps
// hexn_tang_tiertest_v1.v -- Board test of the native-18 RAM tier (hexn_tier_v2: fast table + presence bitmap + the Tang's embedded SDRAM) for the Tang Nano 20K. New file. Not yet run on a board.
// Sequence (all keys/values made by arithmetic from an index, so no list is stored): PUT N keys; UPDATE every 7th; GET all N known keys (value must equal the latest); GET M never-seen keys (must be 'not found'). Keys are DISTINCT: key(i) = ((i+1) * 32'h2545F491) mod 2^KW (odd multiplier).
// Serial report (USB serial port 2 of the BL616, pin 69, 115200 8N1; `stty -F /dev/ttyUSB1 115200 raw; cat /dev/ttyUSB1`), repeated every 0.5 s once the test is done: 16 lines "R<hex digit>=<8 hex digits>":
//  R0 errors total (R1+R2+R3, must be 0)   R1 wrong value on a known key   R2 known key not found (puts dropped on SDRAM probe overflow)   R3 never-seen key reported found
//  R4 clocks from reset to ready (the SDRAM clear sweep)   R5 clocks for the whole test after ready   R6 fast_put  R7 sd_put  R8 overflow  R9 fast_hit  RA skip  RB sd_get  RC fp  RD sd_rd  RE sd_wr  RF found
// R6..RF are the tier's counters; tools/hexn_tier_ref_v2.py computes what they must be (tests/test_hexn_tiertest_v1.py shows how). Clock 27 MHz.
// LEDs (lit = true; outputs inverted for the board): led0 PLL locked, led1 tier ready (SDRAM started and cleared), led2 test finished, led3 finished with R0 = 0, led4 finished with every known key found (R2 = 0), led5 finished with no never-seen key reported found (R3 = 0).
module hexn_tang_tiertest_v1 #(parameter KW = 18, parameter VW = 18, parameter FB = 11, parameter BMB = 16, parameter RAMB = 18, parameter P = 8, parameter N = 6000, parameter M = 3000, parameter GAP = 13_500_000, parameter CLKDIV = 234) (
    input  wire clk27, output wire uart_tx, output wire [5:0] led,
    output wire O_sdram_clk, output wire O_sdram_cke, output wire O_sdram_cs_n, output wire O_sdram_cas_n, output wire O_sdram_ras_n, output wire O_sdram_wen_n,
    output wire [3:0] O_sdram_dqm, output wire [10:0] O_sdram_addr, output wire [1:0] O_sdram_ba, inout wire [31:0] IO_sdram_dq);
    wire clk, clk_sdram, lock;
    rPLL #(.FCLKIN("27"), .IDIV_SEL(0), .FBDIV_SEL(0), .ODIV_SEL(32), .PSDA_SEL("1000"), .DUTYDA_SEL("1000"), .CLKOUT_FT_DIR(1'b1), .CLKOUTP_FT_DIR(1'b1), .CLKOUT_DLY_STEP(0), .CLKOUTP_DLY_STEP(0), .CLKFB_SEL("internal"), .DYN_SDIV_SEL(2), .DEVICE("GW2AR-18C"))
        pll (.CLKIN(clk27), .CLKFB(1'b0), .RESET(1'b0), .RESET_P(1'b0), .FBDSEL(6'b0), .IDSEL(6'b0), .ODSEL(6'b0), .PSDA(4'b0), .DUTYDA(4'b0), .FDLY(4'b0), .CLKOUT(clk), .CLKOUTP(clk_sdram), .CLKOUTD(), .CLKOUTD3(), .LOCK(lock));
    reg [7:0] rcnt = 8'd0; reg resetn = 1'b0;
    always @(posedge clk) begin if (!lock) begin rcnt <= 8'd0; resetn <= 1'b0; end else if (rcnt != 8'hFF) rcnt <= rcnt + 8'd1; else resetn <= 1'b1; end
    reg cmd_valid = 0, cmd_we = 0; reg [KW-1:0] key = 0; reg [VW-1:0] wdata = 0;
    wire busy, done, found, ready; wire [VW-1:0] rdata;
    wire [31:0] n_fast_put, n_sd_put, n_overflow, n_fast_hit, n_skip, n_sd_get, n_fp, n_sd_rd, n_sd_wr, n_found, n_notfound;
    hexn_tier_v2 #(.KW(KW), .VW(VW), .FB(FB), .BMB(BMB), .RAMB(RAMB), .P(P), .FREQ(27_000_000)) tier (.clk(clk), .clk_sdram(clk_sdram), .resetn(resetn), .rdlat(3'd3),
        .cmd_valid(cmd_valid), .cmd_we(cmd_we), .key(key), .wdata(wdata), .busy(busy), .done(done), .found(found), .rdata(rdata), .ready(ready),
        .n_fast_put(n_fast_put), .n_sd_put(n_sd_put), .n_overflow(n_overflow), .n_fast_hit(n_fast_hit), .n_skip(n_skip), .n_sd_get(n_sd_get), .n_fp(n_fp), .n_sd_rd(n_sd_rd), .n_sd_wr(n_sd_wr), .n_found(n_found), .n_notfound(n_notfound),
        .O_sdram_clk(O_sdram_clk), .O_sdram_cke(O_sdram_cke), .O_sdram_cs_n(O_sdram_cs_n), .O_sdram_ras_n(O_sdram_ras_n), .O_sdram_cas_n(O_sdram_cas_n), .O_sdram_wen_n(O_sdram_wen_n),
        .IO_sdram_dq(IO_sdram_dq), .O_sdram_addr(O_sdram_addr), .O_sdram_ba(O_sdram_ba), .O_sdram_dqm(O_sdram_dqm));
    localparam [15:0] N16 = N; localparam [31:0] MK = (32'd1 << KW) - 32'd1, MV = (32'd1 << VW) - 32'd1;
    function [KW-1:0] kof(input [15:0] i); reg [31:0] m; begin m = ({16'd0, i} + 32'd1) * 32'h2545F491; kof = m & MK; end endfunction
    function [VW-1:0] vof(input [15:0] i); reg [31:0] m; begin m = ({16'd0, i} + 32'd1) * 32'h85EBCA6B; vof = (m >> 7) & MV; end endfunction
    function [VW-1:0] uof(input [15:0] i); uof = vof(i) ^ ({VW{1'b1}} & 32'h2AAAA); endfunction
    localparam T_RDY = 0, T_ISS = 1, T_HOLD = 2, T_WAIT = 3, T_NEXT = 4, T_END = 5;
    reg [2:0] ts = T_RDY; reg [1:0] ph = 0; reg [15:0] i = 0; reg [2:0] m7 = 0;
    reg [31:0] e_val = 0, e_lost = 0, e_ff = 0, c_init = 0, c_run = 0; reg finished = 0;
    wire [31:0] e_tot = e_val + e_lost + e_ff;
    wire [VW-1:0] want = (m7 == 3'd0) ? uof(i) : vof(i);
    always @(posedge clk) begin
        if (!resetn) begin ts <= T_RDY; ph <= 0; i <= 0; m7 <= 0; cmd_valid <= 0; e_val <= 0; e_lost <= 0; e_ff <= 0; c_init <= 0; c_run <= 0; finished <= 0; end
        else begin
            if (!ready) c_init <= c_init + 32'd1;
            else if (!finished) c_run <= c_run + 32'd1;
            case (ts)
            T_RDY: if (ready) begin ts <= T_ISS; ph <= 0; i <= 0; end
            T_ISS: begin
                cmd_valid <= 1; cmd_we <= (ph < 2'd2);
                key <= (ph == 2'd3) ? kof(i + N16) : kof(i);
                wdata <= (ph == 2'd1) ? uof(i) : vof(i);
                ts <= T_HOLD;
            end
            T_HOLD: begin cmd_valid <= 0; ts <= T_WAIT; end
            T_WAIT: if (done) begin
                if (ph == 2'd2) begin if (!found) e_lost <= e_lost + 32'd1; else if (rdata !== want) e_val <= e_val + 32'd1; end
                if (ph == 2'd3) begin if (found) e_ff <= e_ff + 32'd1; end
                ts <= T_NEXT;
            end
            T_NEXT: begin
                ts <= T_ISS;
                case (ph)
                2'd0: if (i == N - 1) begin ph <= 2'd1; i <= 0; end else i <= i + 16'd1;
                2'd1: if (i + 16'd7 >= N) begin ph <= 2'd2; i <= 0; m7 <= 0; end else i <= i + 16'd7;
                2'd2: begin m7 <= (m7 == 3'd6) ? 3'd0 : m7 + 3'd1; if (i == N - 1) begin ph <= 2'd3; i <= 0; end else i <= i + 16'd1; end
                2'd3: if (i == M - 1) begin ts <= T_END; finished <= 1; end else i <= i + 16'd1;
                endcase
            end
            T_END: ;
            endcase
        end
    end
    assign led = ~{finished && (e_ff == 32'd0), finished && (e_lost == 32'd0), finished && (e_tot == 32'd0), finished, ready, lock};
    // ---- serial report ----
    reg tx_send = 1'b0; wire tx_busy; reg [7:0] tx_d = 8'd0;
    hexn_uart_tx_v1 #(.CLKDIV(CLKDIV)) utx (.clk(clk), .rst(~resetn), .data(tx_d), .send(tx_send), .txd(uart_tx), .busy(tx_busy));
    reg [3:0] ln = 4'd0; reg [3:0] ps = 4'd0; reg [24:0] gap = 25'd0; reg started = 1'b0;
    function [7:0] hx(input [3:0] v); hx = (v < 4'd10) ? (8'h30 + {4'd0, v}) : (8'h41 + {4'd0, v} - 8'd10); endfunction
    reg [31:0] val;
    always @* begin
        case (ln)
        4'h0: val = e_tot; 4'h1: val = e_val; 4'h2: val = e_lost; 4'h3: val = e_ff; 4'h4: val = c_init; 4'h5: val = c_run;
        4'h6: val = n_fast_put; 4'h7: val = n_sd_put; 4'h8: val = n_overflow; 4'h9: val = n_fast_hit; 4'hA: val = n_skip; 4'hB: val = n_sd_get; 4'hC: val = n_fp; 4'hD: val = n_sd_rd; 4'hE: val = n_sd_wr; default: val = n_found;
        endcase
    end
    reg [7:0] ch;
    always @* begin
        case (ps)
        4'd0: ch = "R"; 4'd1: ch = hx(ln); 4'd2: ch = "=";
        4'd3: ch = hx(val[31:28]); 4'd4: ch = hx(val[27:24]); 4'd5: ch = hx(val[23:20]); 4'd6: ch = hx(val[19:16]);
        4'd7: ch = hx(val[15:12]); 4'd8: ch = hx(val[11:8]); 4'd9: ch = hx(val[7:4]); 4'd10: ch = hx(val[3:0]);
        4'd11: ch = 8'h0D; default: ch = 8'h0A;
        endcase
    end
    always @(posedge clk) begin
        tx_send <= 1'b0;
        if (!finished) begin started <= 1'b0; ln <= 4'd0; ps <= 4'd0; gap <= 25'd0; end
        else if (!started) begin if (gap == GAP) begin started <= 1'b1; gap <= 25'd0; end else gap <= gap + 25'd1; end
        else if (!tx_busy && !tx_send) begin
            tx_d <= ch; tx_send <= 1'b1;
            if (ps == 4'd12) begin ps <= 4'd0; if (ln == 4'd15) begin ln <= 4'd0; started <= 1'b0; end else ln <= ln + 4'd1; end else ps <= ps + 4'd1;
        end
    end
endmodule
