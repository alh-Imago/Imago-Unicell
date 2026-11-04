`default_nettype none
`timescale 1ns / 1ps
// hexn_frame_v3 -- (4 Nov 2026: clone of hexn_frame_v2; ONLY change: led[5:3] now show PATTERN_ID[2:0] (active low) so a person can see which pattern is loaded after a hop; the UART behaviour is identical) the HOST-LINK FRAME around a generated Hex-N pattern (3 Nov 2026, Alan 10:07 "a full end to end run"). A small UART command port (8N1, CLKDIV clocks per bit) and the pattern with the serial<->parallel crossing on every row (hexn_xtop_v2).
// It is the SIMPLEST frame that lets a PC load a program, wipe, present parallel words and read back parallel words WITH THEIR TICKS; it is NOT the spi_bridge_v3 frame of the scoping note (no scratch RAM, no judges, no SPI, no ESP32 link yet).
// Commands (one byte opcode, then arguments; every command except I and L answers with the one byte 'K' when done):
//   'I'            -> 4 bytes PATTERN_ID (little endian), 1 byte ROWS.
//   'W'            -> wipe: clear is held for WIPE_CLOCKS (>= 130) clocks.
//   'B' + NB bytes -> the config chain, NB = ceil(CHAIN_BITS/8): chain bit i (i = 0 is shifted in first) is bit (i mod 8) of byte (i div 8). Exactly CHAIN_BITS bits are shifted, one per clock, then 'K'.
//   'D' row b0 b1 b2 b3 -> parallel input word of that row (little endian), held until changed.
//   'G' mask       -> one-clock valid on the rows in mask (bit r = row r), all at the same clock; clears the output log and restarts the tick counter. The tick of an output is the number of clocks from the clock in which the valid was high.
//   'L'            -> log of output words since 'G': 1 byte count n (max 16), then n x 7 bytes: row, 4 data bytes (little endian), 2 tick bytes (little endian, saturating); the log is then cleared.
module hexn_frame_v3 #(parameter ROWS = 7, parameter CHAIN_BITS = 8, parameter CLKDIV = 234, parameter [31:0] PATTERN_ID = 32'd0, parameter WIPE_CLOCKS = 160) (
    input wire clk, input wire rx, output wire tx, output wire [5:0] led);
    // ---- uart receiver
    reg [1:0] rxs = 2'b11; always @(posedge clk) rxs <= {rxs[0], rx};
    reg rx_busy = 0; reg [15:0] rx_cnt = 0; reg [3:0] rx_n = 0; reg [7:0] rx_sh = 0; reg rx_v = 0; reg [7:0] rx_b = 0;
    always @(posedge clk) begin
        rx_v <= 1'b0;
        if (!rx_busy) begin
            if (!rxs[1]) begin rx_busy <= 1'b1; rx_cnt <= 0; rx_n <= 0; end
        end else begin
            rx_cnt <= rx_cnt + 1;
            if (rx_n == 0) begin
                if (rx_cnt == CLKDIV / 2) begin rx_cnt <= 0; if (rxs[1]) rx_busy <= 1'b0; else rx_n <= 1; end
            end else if (rx_cnt == CLKDIV - 1) begin
                rx_cnt <= 0;
                if (rx_n <= 8) begin rx_sh <= {rxs[1], rx_sh[7:1]}; rx_n <= rx_n + 1; end
                else begin rx_busy <= 1'b0; rx_v <= rxs[1]; rx_b <= rx_sh; end
            end
        end
    end
    // ---- uart transmitter
    reg [9:0] tx_sh = 10'h3ff; reg [15:0] tx_cnt = 0; reg [3:0] tx_n = 0; reg tx_busy = 0; reg tx_go = 0; reg [7:0] tx_d = 0;
    assign tx = tx_sh[0];
    always @(posedge clk) begin
        if (!tx_busy) begin
            if (tx_go) begin tx_sh <= {1'b1, tx_d, 1'b0}; tx_busy <= 1'b1; tx_cnt <= 0; tx_n <= 0; end
        end else begin
            tx_cnt <= tx_cnt + 1;
            if (tx_cnt == CLKDIV - 1) begin tx_cnt <= 0; tx_sh <= {1'b1, tx_sh[9:1]}; tx_n <= tx_n + 1; if (tx_n == 9) tx_busy <= 1'b0; end
        end
    end
    // ---- the pattern
    reg clear = 0, cfg_en = 0, cfg_in = 0; reg [ROWS-1:0] iv = 0; reg [32*ROWS-1:0] idat = 0;
    wire [ROWS-1:0] ibusy, ov; wire [32*ROWS-1:0] od; wire co;
    hexn_xtop_v2 #(.ROWS(ROWS)) pat (.clk(clk), .clear(clear), .in_data(idat), .in_valid(iv), .in_busy(ibusy), .out_data(od), .out_valid(ov), .cfg_en(cfg_en), .cfg_in(cfg_in), .cfg_out(co));
    // ---- output log
    reg [2:0] lrow [0:15]; reg [31:0] ldat [0:15]; reg [15:0] ltick [0:15]; reg [4:0] ln = 0; reg [15:0] tick = 0; reg trun = 0; integer r;
    reg [ROWS-1:0] pend = 0; reg [15:0] tsn [0:ROWS-1]; reg [2:0] psel; reg [31:0] odsel; integer q;
    always_comb begin psel = 3'd0; for (q = ROWS - 1; q >= 0; q = q - 1) if (pend[q]) psel = q[2:0]; odsel = od[32 * psel +: 32]; end
    // ---- command state machine
    localparam IDLE = 0, CFGB = 1, CFGS = 2, WIPE = 3, DROW = 4, DBYT = 5, GMSK = 6, REPLY = 7, WAITTX = 8;
    reg [3:0] st = IDLE; reg [31:0] left = 0; reg [7:0] sh = 0; reg [3:0] nb = 0; reg [7:0] wcnt = 0; reg [2:0] drow = 0; reg [1:0] dn = 0;
    reg [1:0] rk = 0; reg [7:0] ri = 0; reg [3:0] re = 0; reg [2:0] rf = 0; reg [3:0] rpend = 0;       // reply kind: 0 K, 1 I, 2 L ; ri byte index ; re/rf = entry / field for L
    reg [3:0] rret = IDLE; reg [4:0] lcount = 0; reg [7:0] rbyte; reg rlast;
    always_comb begin
        rbyte = 8'h4b; rlast = 1'b1;
        if (rk == 1) begin rlast = (ri == 4); rbyte = ri == 0 ? PATTERN_ID[7:0] : ri == 1 ? PATTERN_ID[15:8] : ri == 2 ? PATTERN_ID[23:16] : ri == 3 ? PATTERN_ID[31:24] : ROWS[7:0]; end
        else if (rk == 2) begin
            rlast = (ri != 0) && (re == lcount - 1) && (rf == 6) || (ri == 0 && lcount == 0);
            if (ri == 0) rbyte = {3'b0, lcount};
            else case (rf)
                0: rbyte = {5'b0, lrow[re]}; 1: rbyte = ldat[re][7:0]; 2: rbyte = ldat[re][15:8]; 3: rbyte = ldat[re][23:16]; 4: rbyte = ldat[re][31:24]; 5: rbyte = ltick[re][7:0]; default: rbyte = ltick[re][15:8];
            endcase
        end
    end
    always @(posedge clk) begin
        tx_go <= 1'b0; iv <= 0;
        // log capture (blocking temp so several rows in one clock are all kept)
        if (trun && tick != 16'hffff) tick <= tick + 1;
        for (r = 0; r < ROWS; r = r + 1) if (ov[r] && trun) begin pend[r] <= 1'b1; tsn[r] <= tick; end
        if (|pend) begin
            pend[psel] <= 1'b0;
            if (ln < 16) begin lrow[ln[3:0]] <= psel; ldat[ln[3:0]] <= odsel; ltick[ln[3:0]] <= tsn[psel]; ln <= ln + 1; end
        end
        case (st)
            IDLE: if (rx_v) case (rx_b)
                8'h49: begin rk <= 1; ri <= 0; st <= REPLY; end
                8'h57: begin clear <= 1'b1; wcnt <= 0; pend <= 0; st <= WIPE; end
                8'h42: begin left <= CHAIN_BITS; st <= CFGB; end
                8'h44: st <= DROW;
                8'h47: st <= GMSK;
                8'h4c: begin rk <= 2; ri <= 0; re <= 0; rf <= 0; lcount <= ln; st <= REPLY; end
                default: ;
            endcase
            CFGB: if (rx_v) begin sh <= rx_b; nb <= (left >= 8) ? 4'd8 : left[3:0]; st <= CFGS; end
            CFGS: begin
                if (nb != 0) begin cfg_en <= 1'b1; cfg_in <= sh[0]; sh <= {1'b0, sh[7:1]}; nb <= nb - 1; left <= left - 1; end
                else begin cfg_en <= 1'b0; if (left == 0) begin rk <= 0; ri <= 0; st <= REPLY; end else st <= CFGB; end
            end
            WIPE: begin wcnt <= wcnt + 1; if (wcnt == WIPE_CLOCKS) begin clear <= 1'b0; ln <= 0; trun <= 1'b0; rk <= 0; ri <= 0; st <= REPLY; end end
            DROW: if (rx_v) begin drow <= rx_b[2:0]; dn <= 0; st <= DBYT; end
            DBYT: if (rx_v) begin idat[32*drow + 8*dn +: 8] <= rx_b; dn <= dn + 1; if (dn == 3) begin rk <= 0; ri <= 0; st <= REPLY; end end
            GMSK: if (rx_v) begin iv <= rx_b[ROWS-1:0]; tick <= 0; trun <= 1'b1; ln <= 0; pend <= 0; rk <= 0; ri <= 0; st <= REPLY; end
            REPLY: begin tx_d <= rbyte; tx_go <= 1'b1; st <= WAITTX; end
            WAITTX: if (!tx_busy && !tx_go) begin
                if (rlast) begin st <= IDLE; if (rk == 2) ln <= 0; end
                else begin
                    st <= REPLY; ri <= ri + 1;
                    if (rk == 2 && ri != 0) begin if (rf == 6) begin rf <= 0; re <= re + 1; end else rf <= rf + 1; end
                end
            end
            default: st <= IDLE;
        endcase
    end
    assign led = ~{PATTERN_ID[2:0], (st != IDLE), (ln != 0), clear};
endmodule
