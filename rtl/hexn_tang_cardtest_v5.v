`timescale 1ns/1ps
// hexn_tang_cardtest_v5.v -- Board test of the three-level tier with the v5 card log (hexn_tier_v5) for the Tang Nano 20K. New file. Not yet run on a board.
// SAFETY FIRST: the tier is held in reset until a READ-ONLY probe has read all 2^LB blocks SD_BASE .. SD_BASE + 2^LB - 1 of the card and found every word zero. If any word is not zero, or the card gives an error, the tier is never started, nothing is ever written to the card, and the report says which block was not empty. Blocks outside that region are never touched.
// After the probe passes: PUT N keys; UPDATE every 7th; GET all N (value must be the latest); GET M never-seen keys (must be 'not found') -> counters snapshot 0 is taken after SAVE (everything in the fast table and SDRAM is written down into the card log).
// Then the tier is reset (power-loss emulation: the FPGA side loses everything it held; the SDRAM chip and the SD card keep their contents), RESTORE rebuilds the index from the card by scanning the log (snapshot 1), and the same GETs are repeated (snapshot 2): every known key must come back with its latest value.
// Honest scope: this is a reset of the FPGA logic with the card still powered, not a true power cut. A true power cycle needs the second stage (restore and verify straight after power-up), not in this file.
// Serial report (USB serial port 2 of the BL616, pin 69, 115200 8N1), repeated every 0.5 s once the test finished or stopped: 97 lines "<type><2 hex>=<8 hex>":
//  H00 probe state (0 running, 1 REFUSED region not empty, 2 card error during probe, 3 passed)  H01 non-zero words found by the probe  H02 first non-empty block (FFFFFFFF none)  H03 card error word {flag, err_code, err_cmd, err_rx} (0 none)
//  H04 test finished (1)  H05 errors after restore (H06+H07+H08)  H06 wrong value  H07 known key not found  H08 never-seen key reported found  H09 errors before the power-loss emulation (H0A+H0B+H0C)  H0A wrong  H0B not found  H0C never-seen found
//  H0D clocks until the tier was ready  H0E clocks for the whole test  H0F SD_BASE
//  C00..C1A counters after SAVE (v5's 27 counters, order as in tools/hexn_tier_ref_v5.py NAMES)  C1B..C35 after RESTORE  C36..C50 after the final GETs   (C-lines are numbered in hex: set*27 + counter)
// tools/hexn_tang_cardtest_check_v5.py compares them with the bit-true reference. LEDs (lit = true): led0 PLL locked, led1 probe passed (region empty), led2 tier ready, led3 finished, led4 finished with no error at all, led5 stopped (refused, or card error).
module hexn_tang_cardtest_v5 #(parameter KW = 18, parameter VW = 18, parameter FB = 6, parameter RAMB = 8, parameter LB = 6, parameter LOW = 4, parameter VOL = 1, parameter SD_BASE = 4608,
    parameter N = 1500, parameter M = 500, parameter GAP = 13_500_000, parameter CLKDIV = 234, parameter INIT_DIV = 34, parameter FAST_DIV = 1) (
    input  wire clk27, output wire uart_tx, output wire [5:0] led,
    output wire O_sdram_clk, output wire O_sdram_cke, output wire O_sdram_cs_n, output wire O_sdram_cas_n, output wire O_sdram_ras_n, output wire O_sdram_wen_n,
    output wire [3:0] O_sdram_dqm, output wire [10:0] O_sdram_addr, output wire [1:0] O_sdram_ba, inout wire [31:0] IO_sdram_dq,
    output wire sd_clk, output wire sd_mosi, input wire sd_miso, output wire sd_cs_n);
    wire clk, clk_sdram, lock;
    rPLL #(.FCLKIN("27"), .IDIV_SEL(0), .FBDIV_SEL(0), .ODIV_SEL(32), .PSDA_SEL("1000"), .DUTYDA_SEL("1000"), .CLKOUT_FT_DIR(1'b1), .CLKOUTP_FT_DIR(1'b1), .CLKOUT_DLY_STEP(0), .CLKOUTP_DLY_STEP(0), .CLKFB_SEL("internal"), .DYN_SDIV_SEL(2), .DEVICE("GW2AR-18C"))
        pll (.CLKIN(clk27), .CLKFB(1'b0), .RESET(1'b0), .RESET_P(1'b0), .FBDSEL(6'b0), .IDSEL(6'b0), .ODSEL(6'b0), .PSDA(4'b0), .DUTYDA(4'b0), .FDLY(4'b0), .CLKOUT(clk), .CLKOUTP(clk_sdram), .CLKOUTD(), .CLKOUTD3(), .LOCK(lock));
    reg [7:0] rcnt = 8'd0; reg resetn = 1'b0;
    always @(posedge clk) begin if (!lock) begin rcnt <= 8'd0; resetn <= 1'b0; end else if (rcnt != 8'hFF) rcnt <= rcnt + 8'd1; else resetn <= 1'b1; end

    // ---------------- read-only probe of the target region (its own SD controller; it has no write path: wr_req is tied to 0) ----------------
    localparam [31:0] LBLK = 32'd1 << LB;
    reg own = 1'b0;                        // 1 = the probe passed and the tier owns the card pins
    wire p_ready, p_error, p_busy, p_done, p_wv; wire [4:0] p_ec; wire [5:0] p_ecmd; wire [7:0] p_erx; wire [31:0] p_wd; wire [6:0] p_wi, p_sa;
    reg p_rd = 1'b0; reg [31:0] p_blk = 32'd0;
    wire p_clk, p_mosi, p_cs;
    sd_spi_v1 #(.INIT_DIV(INIT_DIV), .FAST_DIV(FAST_DIV)) probe (.clk(clk), .rst(~resetn | own), .sd_clk(p_clk), .sd_mosi(p_mosi), .sd_miso(sd_miso), .sd_cs_n(p_cs),
        .ready(p_ready), .error(p_error), .err_code(p_ec), .err_cmd(p_ecmd), .err_rx(p_erx), .busy(p_busy), .rd_req(p_rd), .wr_req(1'b0), .block(p_blk),
        .block_done(p_done), .w_valid(p_wv), .w_data(p_wd), .w_index(p_wi), .src_addr(p_sa), .src_data(32'd0));
    localparam P_WAIT = 0, P_ISS = 1, P_RW = 2, P_END = 3;
    reg [1:0] pst = P_WAIT; reg [31:0] pi = 32'd0, nz = 32'd0, first_nz = 32'hFFFFFFFF; reg [1:0] pstate = 2'd0;   // pstate 0 running, 1 refused, 2 card error, 3 passed
    reg [31:0] p_errw = 32'd0;
    always @(posedge clk) begin
        p_rd <= 1'b0;
        if (!resetn) begin pst <= P_WAIT; pi <= 32'd0; nz <= 32'd0; first_nz <= 32'hFFFFFFFF; pstate <= 2'd0; own <= 1'b0; p_errw <= 32'd0; end
        else case (pst)
            P_WAIT: if (p_error) begin pstate <= 2'd2; p_errw <= {1'b1, 2'd0, p_ec, p_ecmd, p_erx}; pst <= P_END; end else if (p_ready) pst <= P_ISS;
            P_ISS:  begin p_blk <= SD_BASE + pi; p_rd <= 1'b1; pst <= P_RW; end
            P_RW: begin
                if (p_wv && p_wd != 32'd0) begin nz <= nz + 32'd1; if (first_nz == 32'hFFFFFFFF) first_nz <= SD_BASE + pi; end
                if (p_error) begin pstate <= 2'd2; p_errw <= {1'b1, 2'd0, p_ec, p_ecmd, p_erx}; pst <= P_END; end
                else if (p_done) begin if (pi == LBLK - 1) pst <= P_END; else begin pi <= pi + 32'd1; pst <= P_ISS; end end
            end
            P_END: if (pstate == 2'd0) begin
                if (nz == 32'd0) begin pstate <= 2'd3; own <= 1'b1; end else pstate <= 2'd1;   // the only place where the tier is allowed to start
            end
        endcase
    end

    // ---------------- the tier (held in reset unless the probe passed) ----------------
    reg pl = 1'b0;   // power-loss emulation: tier reset
    wire tresetn = resetn & own & ~pl;
    reg cmd_valid = 0, cmd_we = 0, cmd_save = 0, cmd_restore = 0; reg [KW-1:0] key = 0; reg [VW-1:0] wdata = 0;
    wire busy, done, found, ready, sd_error; wire [VW-1:0] rdata; wire [32*27-1:0] cnts;
    wire t_clk, t_mosi, t_cs;
    hexn_tier_v5 #(.KW(KW), .VW(VW), .FB(FB), .RAMB(RAMB), .LB(LB), .LOW(LOW), .VOL(VOL), .SD_BASE(SD_BASE), .FREQ(27_000_000), .INIT_DIV(INIT_DIV), .FAST_DIV(FAST_DIV)) tier (
        .clk(clk), .clk_sdram(clk_sdram), .resetn(tresetn), .rdlat(3'd3),
        .cmd_valid(cmd_valid), .cmd_we(cmd_we), .cmd_flush(1'b0), .cmd_save(cmd_save), .cmd_restore(cmd_restore), .key(key), .wdata(wdata), .busy(busy), .done(done), .found(found), .rdata(rdata), .ready(ready), .cnts(cnts), .sd_error(sd_error),
        .O_sdram_clk(O_sdram_clk), .O_sdram_cke(O_sdram_cke), .O_sdram_cs_n(O_sdram_cs_n), .O_sdram_ras_n(O_sdram_ras_n), .O_sdram_cas_n(O_sdram_cas_n), .O_sdram_wen_n(O_sdram_wen_n),
        .IO_sdram_dq(IO_sdram_dq), .O_sdram_addr(O_sdram_addr), .O_sdram_ba(O_sdram_ba), .O_sdram_dqm(O_sdram_dqm),
        .sd_clk(t_clk), .sd_mosi(t_mosi), .sd_miso(sd_miso), .sd_cs_n(t_cs));
    assign sd_clk = own ? t_clk : p_clk; assign sd_mosi = own ? t_mosi : p_mosi; assign sd_cs_n = own ? t_cs : p_cs;

    // ---------------- test sequence ----------------
    localparam [15:0] N16 = N; localparam [31:0] MK = (32'd1 << KW) - 32'd1, MV = (32'd1 << VW) - 32'd1;
    function [KW-1:0] kof(input [15:0] i); reg [31:0] m; begin m = ({16'd0, i} + 32'd1) * 32'h2545F491; kof = m & MK; end endfunction
    function [VW-1:0] vof(input [15:0] i); reg [31:0] m; begin m = ({16'd0, i} + 32'd1) * 32'h85EBCA6B; vof = (m >> 7) & MV; end endfunction
    function [VW-1:0] uof(input [15:0] i); uof = vof(i) ^ ({VW{1'b1}} & 32'h2AAAA); endfunction
    localparam T_RDY = 0, T_ISS = 1, T_HOLD = 2, T_WAIT = 3, T_NEXT = 4, T_SAVE = 5, T_SNAP = 6, T_PL = 7, T_PLW = 8, T_RES = 9, T_END = 10;
    reg [3:0] ts = T_RDY; reg [2:0] ph = 0; reg [15:0] i = 0; reg [2:0] m7 = 0; reg [1:0] snapset = 0; reg [6:0] snapk = 0; reg [7:0] plc = 0; reg [3:0] after_snap = 0;
    reg [31:0] e_val = 0, e_lost = 0, e_ff = 0, q_val = 0, q_lost = 0, q_ff = 0, c_init = 0, c_run = 0; reg finished = 0, ever_ready = 0, stopped = 0;
    reg [31:0] snap [0:80]; reg [31:0] sd_errw = 32'd0; integer zi; initial for (zi = 0; zi < 81; zi = zi + 1) snap[zi] = 32'd0;
    wire [VW-1:0] want = (m7 == 3'd0) ? uof(i) : vof(i);
    // phases: 0 PUT, 1 UPDATE every 7th, 2 GET known (before power-loss emulation), 3 GET never-seen (before), 4 GET known (after restore), 5 GET never-seen (after restore)
    always @(posedge clk) begin
        if (!resetn || !own) begin
            ts <= T_RDY; ph <= 0; i <= 0; m7 <= 0; cmd_valid <= 0; cmd_save <= 0; cmd_restore <= 0; pl <= 0; snapset <= 0; snapk <= 0; plc <= 0;
            e_val <= 0; e_lost <= 0; e_ff <= 0; q_val <= 0; q_lost <= 0; q_ff <= 0; c_init <= 0; c_run <= 0; finished <= 0; ever_ready <= 0; stopped <= 0; sd_errw <= 32'd0;
        end else begin
            if (!ever_ready) c_init <= c_init + 32'd1; else if (!finished && !stopped) c_run <= c_run + 32'd1;
            if (ready) ever_ready <= 1'b1;
            if (sd_error && !stopped && !finished) begin stopped <= 1; sd_errw <= {1'b1, 2'd0, 5'd0, 6'd0, 8'd0}; end
            case (ts)
            T_RDY: if (ready) begin ts <= T_ISS; ph <= 0; i <= 0; end
            T_ISS: begin
                cmd_valid <= 1; cmd_we <= (ph < 3'd2); cmd_save <= 0; cmd_restore <= 0;
                key <= (ph == 3'd3 || ph == 3'd5) ? kof(i + N16) : kof(i);
                wdata <= (ph == 3'd1) ? uof(i) : vof(i);
                ts <= T_HOLD;
            end
            T_HOLD: begin cmd_valid <= 0; cmd_save <= 0; cmd_restore <= 0; ts <= T_WAIT; end
            T_WAIT: if (done) begin
                if (ph == 3'd2) begin if (!found) q_lost <= q_lost + 32'd1; else if (rdata !== want) q_val <= q_val + 32'd1; end
                if (ph == 3'd3) begin if (found) q_ff <= q_ff + 32'd1; end
                if (ph == 3'd4) begin if (!found) e_lost <= e_lost + 32'd1; else if (rdata !== want) e_val <= e_val + 32'd1; end
                if (ph == 3'd5) begin if (found) e_ff <= e_ff + 32'd1; end
                ts <= T_NEXT;
            end
            T_NEXT: begin
                ts <= T_ISS;
                case (ph)
                3'd0: if (i == N - 1) begin ph <= 3'd1; i <= 0; end else i <= i + 16'd1;
                3'd1: if (i + 16'd7 >= N) begin ph <= 3'd2; i <= 0; m7 <= 0; end else i <= i + 16'd7;
                3'd2: begin m7 <= (m7 == 3'd6) ? 3'd0 : m7 + 3'd1; if (i == N - 1) begin ph <= 3'd3; i <= 0; end else i <= i + 16'd1; end
                3'd3: if (i == M - 1) begin ts <= T_SAVE; end else i <= i + 16'd1;
                3'd4: begin m7 <= (m7 == 3'd6) ? 3'd0 : m7 + 3'd1; if (i == N - 1) begin ph <= 3'd5; i <= 0; end else i <= i + 16'd1; end
                3'd5: if (i == M - 1) begin ts <= T_SNAP; after_snap <= T_END; end else i <= i + 16'd1;
                default: ts <= T_END;
                endcase
            end
            T_SAVE: begin cmd_valid <= 1; cmd_save <= 1; cmd_we <= 0; ts <= T_HOLD; after_snap <= T_PL; ph <= 3'd6; end   // ph 6 = no per-key checks while the save runs
            T_SNAP: begin   // copy the 27 counters into snapshot set `snapset` (one per clock)
                snap[snapset * 27 + snapk] <= cnts[32*snapk +: 32];
                if (snapk == 7'd26) begin snapk <= 0; snapset <= snapset + 2'd1; ts <= after_snap; end else snapk <= snapk + 7'd1;
            end
            T_PL: begin pl <= 1; plc <= plc + 8'd1; if (plc == 8'd63) begin pl <= 0; plc <= 0; ts <= T_PLW; end end
            T_PLW: begin plc <= plc + 8'd1; if (plc > 8'd32 && ready) begin plc <= 0; ts <= T_RES; end end
            T_RES: begin cmd_valid <= 1; cmd_restore <= 1; cmd_we <= 0; ts <= T_HOLD; after_snap <= T_ISS; ph <= 3'd7; end
            T_END: if (!stopped) finished <= 1;
            endcase
            // the end of SAVE and RESTORE (ph 6 and 7): leave T_WAIT through the snapshot
            if (ts == T_WAIT && done && ph == 3'd6) begin ts <= T_SNAP; ph <= 3'd0; end
            if (ts == T_WAIT && done && ph == 3'd7) begin ts <= T_SNAP; ph <= 3'd4; i <= 0; m7 <= 0; after_snap <= T_ISS; end
            if (stopped) begin ts <= T_END; end
        end
    end
    wire [31:0] e_tot = e_val + e_lost + e_ff, q_tot = q_val + q_lost + q_ff;
    wire stop_all = (pstate == 2'd1) || (pstate == 2'd2) || stopped;
    assign led = ~{stop_all, finished && !stopped && e_tot == 32'd0 && q_tot == 32'd0, finished, ever_ready, pstate == 2'd3, lock};
    // ---------------- serial report ----------------
    wire rep_go = finished || stop_all;
    reg tx_send = 1'b0; wire tx_busy; reg [7:0] tx_d = 8'd0;
    hexn_uart_tx_v1 #(.CLKDIV(CLKDIV)) utx (.clk(clk), .rst(~resetn), .data(tx_d), .send(tx_send), .txd(uart_tx), .busy(tx_busy));
    reg [6:0] ln = 7'd0; reg [3:0] ps = 4'd0; reg [24:0] gap = 25'd0; reg started = 1'b0;
    function [7:0] hx(input [3:0] v); hx = (v < 4'd10) ? (8'h30 + {4'd0, v}) : (8'h41 + {4'd0, v} - 8'd10); endfunction
    reg [31:0] val; wire [6:0] cn = ln - 7'd16;
    always @* begin
        if (ln >= 7'd16) val = snap[cn];
        else case (ln[3:0])
        4'h0: val = {30'd0, pstate}; 4'h1: val = nz; 4'h2: val = first_nz; 4'h3: val = (pstate == 2'd2) ? p_errw : sd_errw;
        4'h4: val = {31'd0, finished}; 4'h5: val = e_tot; 4'h6: val = e_val; 4'h7: val = e_lost; 4'h8: val = e_ff; 4'h9: val = q_tot; 4'hA: val = q_val; 4'hB: val = q_lost; 4'hC: val = q_ff;
        4'hD: val = c_init; 4'hE: val = c_run; default: val = SD_BASE;
        endcase
    end
    wire [6:0] lnum = (ln >= 7'd16) ? cn : ln;
    reg [7:0] ch;
    always @* begin
        case (ps)
        4'd0: ch = (ln >= 7'd16) ? "C" : "H"; 4'd1: ch = hx({1'b0, lnum[6:4]}); 4'd2: ch = hx(lnum[3:0]); 4'd3: ch = "=";
        4'd4: ch = hx(val[31:28]); 4'd5: ch = hx(val[27:24]); 4'd6: ch = hx(val[23:20]); 4'd7: ch = hx(val[19:16]);
        4'd8: ch = hx(val[15:12]); 4'd9: ch = hx(val[11:8]); 4'd10: ch = hx(val[7:4]); 4'd11: ch = hx(val[3:0]);
        4'd12: ch = 8'h0D; default: ch = 8'h0A;
        endcase
    end
    always @(posedge clk) begin
        tx_send <= 1'b0;
        if (!rep_go) begin started <= 1'b0; ln <= 7'd0; ps <= 4'd0; gap <= 25'd0; end
        else if (!started) begin if (gap == GAP) begin started <= 1'b1; gap <= 25'd0; end else gap <= gap + 25'd1; end
        else if (!tx_busy && !tx_send) begin
            tx_d <= ch; tx_send <= 1'b1;
            if (ps == 4'd13) begin ps <= 4'd0; if (ln == 7'd96) begin ln <= 7'd0; started <= 1'b0; end else ln <= ln + 7'd1; end else ps <= ps + 4'd1;
        end
    end
endmodule
