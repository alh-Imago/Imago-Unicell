`timescale 1ns/1ps
// hexn_tang_ctxstore_v1.v -- Tang Nano 20K board harness for the SDRAM-backed context store (rtl/hexn_ctxstore_v1.v) with our SDRAM controller (rtl/hexn_sdram_v1.v). Driven from the PC over the USB serial port (pin 69 out, pin 70 in), binary protocol:
//   'W' k0 k1 k2 k3 fid  -> OBS(key, fid), key little-endian (bit 31 ignored); reply 'k'
//   'R' k0 k1 k2 k3      -> RD(key); reply 'r', found (0/1), then the 14 slots as 28 bytes (slot 0 first, each as weight byte first then follower id byte, i.e. the little-endian 16-bit {fid, weight})
//   'S' n                -> counter n (0..8: ops, cache_hit, filter_skip, sd_probe, sd_rd, sd_wr, created, slot_evict, overflow); reply 's' and 4 bytes little-endian
//   'I'                  -> reply 'i' and one status byte (bit 0 ready, bit 1 error)
// Right after power-up the store clears its table (2^BB buckets, about 40 ms for BB = 17) and then reports ready. LEDs (lit = true): led0 ready, led1 error, led2 PLL locked, led3 flips on each operation, led4/led5 unused.
module hexn_tang_ctxstore_v1 #(parameter BB = 17, parameter CB = 8, parameter CLKDIV = 234) (
    input wire clk27, input wire uart_rx, output wire uart_tx, output wire [5:0] led,
    output wire O_sdram_clk, output wire O_sdram_cke, output wire O_sdram_cs_n, output wire O_sdram_cas_n, output wire O_sdram_ras_n, output wire O_sdram_wen_n,
    output wire [3:0] O_sdram_dqm, output wire [10:0] O_sdram_addr, output wire [1:0] O_sdram_ba, inout wire [31:0] IO_sdram_dq);
    wire clk, clk_sdram, lock;
    rPLL #(.FCLKIN("27"), .IDIV_SEL(0), .FBDIV_SEL(0), .ODIV_SEL(32), .PSDA_SEL("1000"), .DUTYDA_SEL("1000"), .CLKOUT_FT_DIR(1'b1), .CLKOUTP_FT_DIR(1'b1), .CLKOUT_DLY_STEP(0), .CLKOUTP_DLY_STEP(0), .CLKFB_SEL("internal"), .DYN_SDIV_SEL(2), .DEVICE("GW2AR-18C"))
        pll (.CLKIN(clk27), .CLKFB(1'b0), .RESET(1'b0), .RESET_P(1'b0), .FBDSEL(6'b0), .IDSEL(6'b0), .ODSEL(6'b0), .PSDA(4'b0), .DUTYDA(4'b0), .FDLY(4'b0), .CLKOUT(clk), .CLKOUTP(clk_sdram), .CLKOUTD(), .CLKOUTD3(), .LOCK(lock));
    reg [7:0] rcnt = 8'd0; reg resetn = 1'b0;
    always @(posedge clk) begin if (!lock) begin rcnt <= 8'd0; resetn <= 1'b0; end else if (rcnt != 8'hFF) rcnt <= rcnt + 8'd1; else resetn <= 1'b1; end
    wire sv, swe, sready, srv, sinit; wire [20:0] sa; wire [31:0] sw, sr;
    reg cs_valid = 0, cs_obs = 0; reg [30:0] cs_key = 0; reg [7:0] cs_fid = 0; wire cs_ready, cs_done, cs_found, cs_rdy, cs_err; wire [223:0] cs_slots; reg [3:0] cs_sel = 0; wire [31:0] cs_val;
    hexn_ctxstore_v1 #(.BB(BB), .CB(CB)) cs (.clk(clk), .rst(~resetn), .cmd_valid(cs_valid), .cmd_obs(cs_obs), .cmd_key(cs_key), .cmd_fid(cs_fid), .cmd_ready(cs_ready), .done(cs_done), .found(cs_found), .slots_out(cs_slots), .ready(cs_rdy), .err(cs_err),
        .cnt_sel(cs_sel), .cnt_val(cs_val), .sd_cmd_valid(sv), .sd_cmd_we(swe), .sd_cmd_addr(sa), .sd_cmd_wdata(sw), .sd_cmd_ready(sready), .sd_rd_valid(srv), .sd_rd_data(sr), .sd_init_done(sinit));
    hexn_sdram_v1 #(.FREQ(27_000_000), .CL(3'd2)) sdc (.clk(clk), .clk_sdram(clk_sdram), .resetn(resetn), .rdlat(3'd3), .cmd_valid(sv), .cmd_we(swe), .cmd_addr(sa), .cmd_wdata(sw), .cmd_wmask(4'b1111), .cmd_ready(sready), .rd_valid(srv), .rd_data(sr), .init_done(sinit),
        .O_sdram_clk(O_sdram_clk), .O_sdram_cke(O_sdram_cke), .O_sdram_cs_n(O_sdram_cs_n), .O_sdram_ras_n(O_sdram_ras_n), .O_sdram_cas_n(O_sdram_cas_n), .O_sdram_wen_n(O_sdram_wen_n), .IO_sdram_dq(IO_sdram_dq), .O_sdram_addr(O_sdram_addr), .O_sdram_ba(O_sdram_ba), .O_sdram_dqm(O_sdram_dqm));
    // ---- serial ----
    wire [7:0] rx_d; wire rx_v; reg tx_send = 0; reg [7:0] tx_d = 0; wire tx_busy;
    hexn_uart_rx_v1 #(.CLKDIV(CLKDIV)) urx (.clk(clk), .rst(~resetn), .rxd(uart_rx), .data(rx_d), .valid(rx_v));
    hexn_uart_tx_v1 #(.CLKDIV(CLKDIV)) utx (.clk(clk), .rst(~resetn), .data(tx_d), .send(tx_send), .txd(uart_tx), .busy(tx_busy));
    localparam H_CMD = 3'd0, H_ARG = 3'd1, H_EXEC = 3'd2, H_WAIT = 3'd3, H_REPLY = 3'd4, H_CNT = 3'd5;
    reg [2:0] hs = H_CMD; reg [7:0] cmd = 0; reg [2:0] need = 0; reg [39:0] args = 0; reg [239:0] rep = 0; reg [5:0] rlen = 0; reg led3 = 0;
    always @(posedge clk) begin
        tx_send <= 1'b0;
        if (!resetn) begin hs <= H_CMD; cs_valid <= 1'b0; end
        else case (hs)
        H_CMD: if (rx_v) begin
            cmd <= rx_d; args <= 40'd0;
            case (rx_d) "W": begin need <= 3'd5; hs <= H_ARG; end "R": begin need <= 3'd4; hs <= H_ARG; end "S": begin need <= 3'd1; hs <= H_ARG; end
            "I": begin rep <= {cs_err, cs_rdy, 8'h69}; rlen <= 6'd2; hs <= H_REPLY; end default: hs <= H_CMD; endcase
        end
        H_ARG: if (rx_v) begin
            args <= {rx_d, args[39:8]}; need <= need - 3'd1;
            if (need == 3'd1) hs <= (cmd == "S") ? H_CNT : H_EXEC;
        end
        H_CNT: begin cs_sel <= args[39:32] > 8'd8 ? 4'd8 : args[35:32]; hs <= H_WAIT; rlen <= 6'd1; end      // one cycle for cnt_val to settle, then reply
        H_EXEC: begin
            // args holds the bytes in arrival order, first byte at the lowest end after the shifts: W has 5 bytes (k0..k3, fid) in args[39:0]; R has 4 (k0..k3) in args[39:8]
            if (!cs_valid) begin
                cs_valid <= 1'b1; cs_obs <= (cmd == "W");
                cs_key <= (cmd == "W") ? args[30:0] : args[38:8]; cs_fid <= args[39:32];
            end else if (cs_ready) begin cs_valid <= 1'b0; led3 <= ~led3; hs <= H_WAIT; end
        end
        H_WAIT: begin
            if (cmd == "S") begin rep <= {cs_val, 8'h73}; rlen <= 6'd5; hs <= H_REPLY; end
            else if (cs_done) begin
                if (cmd == "W") begin rep <= {232'd0, 8'h6B}; rlen <= 6'd1; end
                else begin rep <= {cs_slots, 7'd0, cs_found, 8'h72}; rlen <= 6'd30; end
                hs <= H_REPLY;
            end
        end
        H_REPLY: if (rlen == 6'd0) hs <= H_CMD; else if (!tx_busy && !tx_send) begin tx_d <= rep[7:0]; tx_send <= 1'b1; rep <= {8'd0, rep[239:8]}; rlen <= rlen - 6'd1; end
        endcase
    end
    assign led = ~{1'b0, 1'b0, led3, lock, cs_err, cs_rdy};
endmodule
