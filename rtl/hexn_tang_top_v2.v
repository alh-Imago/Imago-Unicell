`default_nettype none
// hexn_tang_top_v2.v -- Clone of hexn_tang_top_v1.v (left untouched); v2 adds command 0x07 DUMP (read back the trained settings for diagnosis) and uses the lattice _v2 modules. Hex-N lattice bank on the Tang Nano 20K with a serial command link (USB serial through the BL616, 8N1). Compile with -DLATMOD=hexn_lattice_<shape>_v1 and -DNCLS=<cells>; 12 input wires.
// Commands (host to board); after each one the board answers, so the host never overruns it:
//   0x01 CLEAR                       -> 0xA5
//   0x02 COUNT  label bits_lo bits_hi -> 0xA5     (every training sample once)
//   0x03 SETW   t                    -> 0xA5     (weights from the counters; t = samples per class / 2)
//   0x04 ACCUM  label bits_lo bits_hi -> 0xA5     (every training sample once more)
//   0x05 FINISH                      -> 0xA5     (thresholds)
//   0x07 DUMP                        -> for each detector k = 0..K-1: wpos_lo wpos_hi wneg_lo wneg_hi thr   (5*K bytes; lane j = bit j)
//   0x06 RUN    bits_lo bits_hi      -> status, c0 .. c(K-1)    (status bit 7 = answer valid, bits 4..0 = class; c = output clocks of each detector in the last window)
// bits are the 12 input wires, wire j = bit j (bits_hi uses its low 4 bits). LEDs (active low): bits 4..0 = class of the last answer, bit 5 = answer valid.
`ifndef NCLS
`define NCLS 7
`endif
`ifndef CLKDIV
`define CLKDIV 234
`endif
module hexn_tang_top_v2 (input wire clk, input wire uart_rx, output wire uart_tx, output wire [5:0] led);
    localparam K = `NCLS; localparam NB = 12; localparam KW = $clog2(K);
    reg [7:0] por = 0; wire rst = ~&por; always @(posedge clk) if (~&por) por <= por + 1'b1;
    wire [7:0] rx_d; wire rx_v; reg [7:0] tx_d; reg tx_s; wire tx_b;
    hexn_uart_rx_v1 #(.CLKDIV(`CLKDIV)) urx(.clk(clk), .rst(rst), .rxd(uart_rx), .data(rx_d), .valid(rx_v));
    hexn_uart_tx_v1 #(.CLKDIV(`CLKDIV)) utx(.clk(clk), .rst(rst), .data(tx_d), .send(tx_s), .txd(uart_tx), .busy(tx_b));
    reg tr_start, run_start; reg [2:0] tr_cmd; reg [NB-1:0] bits; reg [KW-1:0] label; reg [5:0] t_in;
    wire tr_busy, run_busy, run_done, ans_valid; wire [KW-1:0] ans_class; wire [4*K-1:0] cnt; wire [K*NB-1:0] dwp, dwn; wire [K*6-1:0] dthr;
    `LATMOD #(.K(K)) bank(.clk(clk), .rst(rst), .tr_start(tr_start), .tr_cmd(tr_cmd), .tr_busy(tr_busy), .s_bits(bits), .s_label(label), .t_in(t_in),
        .run_start(run_start), .run_busy(run_busy), .run_done(run_done), .ans_valid(ans_valid), .ans_class(ans_class), .cnt_flat(cnt), .dbg_wpos(dwp), .dbg_wneg(dwn), .dbg_thr(dthr));
    localparam [3:0] IDLE = 0, ARG = 1, GO = 2, WAIT = 3, ACK = 4, RUNW = 5, STAT = 6, CNTS = 7, SEND = 8, DUMP = 9;
    reg [3:0] st, after; reg [7:0] cmd; reg [2:0] nargs, got; reg [7:0] a0, a1, a2; reg [$clog2(K+1):0] ci;
    reg [$clog2(K+1):0] dk; reg [2:0] dj; reg [KW-1:0] lastclass; reg lastvalid;
    assign led = ~{lastvalid, {(5-KW){1'b0}}, lastclass};
    always @(posedge clk) begin
        tr_start <= 1'b0; run_start <= 1'b0; tx_s <= 1'b0;
        if (rst) begin st <= IDLE; lastclass <= 0; lastvalid <= 0; t_in <= 0; bits <= 0; label <= 0; end
        else case (st)
            IDLE: if (rx_v) begin
                cmd <= rx_d; got <= 0;
                case (rx_d)
                    8'h01, 8'h05: begin nargs <= 0; st <= GO; end
                    8'h02, 8'h04: begin nargs <= 3; st <= ARG; end
                    8'h03: begin nargs <= 1; st <= ARG; end
                    8'h06: begin nargs <= 2; st <= ARG; end
                    8'h07: begin nargs <= 0; st <= GO; end
                    default: st <= IDLE;
                endcase
            end
            ARG: if (rx_v) begin
                if (got == 0) a0 <= rx_d; else if (got == 1) a1 <= rx_d; else a2 <= rx_d;
                got <= got + 1'b1;
                if (got + 1 == nargs) st <= GO;
            end
            GO: begin
                case (cmd)
                    8'h01: begin tr_cmd <= 3'd1; tr_start <= 1; st <= WAIT; end
                    8'h02: begin label <= a0; bits <= {a2[3:0], a1}; tr_cmd <= 3'd2; tr_start <= 1; st <= WAIT; end
                    8'h03: begin t_in <= a0[5:0]; tr_cmd <= 3'd3; tr_start <= 1; st <= WAIT; end
                    8'h04: begin label <= a0; bits <= {a2[3:0], a1}; tr_cmd <= 3'd4; tr_start <= 1; st <= WAIT; end
                    8'h05: begin tr_cmd <= 3'd5; tr_start <= 1; st <= WAIT; end
                    8'h06: begin bits <= {a1[3:0], a0}; run_start <= 1; st <= RUNW; end
                    8'h07: begin dk <= 0; dj <= 0; st <= DUMP; end
                    default: st <= IDLE;
                endcase
            end
            WAIT: if (!tr_start && !tr_busy) st <= ACK;                                           // tr_busy rises the clock after the start pulse; tr_start is already cleared here
            ACK: begin tx_d <= 8'hA5; tx_s <= 1; st <= SEND; after <= IDLE; end
            RUNW: if (run_done) st <= STAT;
            STAT: if (!run_busy) begin lastvalid <= ans_valid; lastclass <= ans_class; tx_d <= {ans_valid, 2'b00, {(5-KW){1'b0}}, ans_class}; tx_s <= 1; st <= SEND; after <= CNTS; ci <= 0; end
            CNTS: begin
                if (ci == K) st <= IDLE;
                else begin tx_d <= {4'd0, cnt[4*ci +: 4]}; tx_s <= 1; ci <= ci + 1'b1; st <= SEND; after <= CNTS; end
            end
            DUMP: begin
                if (dk == K) st <= IDLE;
                else begin
                    case (dj)
                        3'd0: tx_d <= dwp[dk*NB +: 8];
                        3'd1: tx_d <= {4'd0, dwp[dk*NB + 8 +: 4]};
                        3'd2: tx_d <= dwn[dk*NB +: 8];
                        3'd3: tx_d <= {4'd0, dwn[dk*NB + 8 +: 4]};
                        default: tx_d <= {2'd0, dthr[dk*6 +: 6]};
                    endcase
                    tx_s <= 1; st <= SEND; after <= DUMP;
                    if (dj == 4) begin dj <= 0; dk <= dk + 1'b1; end else dj <= dj + 1'b1;
                end
            end
            SEND: if (!tx_s && !tx_b) st <= after;    // wait for the transmitter to take the byte and finish it
            default: st <= IDLE;
        endcase
    end
endmodule
`default_nettype wire
