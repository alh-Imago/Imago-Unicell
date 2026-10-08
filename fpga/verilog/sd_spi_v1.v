// sd_spi_v1.v -- ledger #1036: an SD card in SPI mode, RAW 512-byte blocks (no filesystem). Reads a block into 128 little-endian 32-bit words and writes 128 words to a block.
// Tang Nano 20K slot, SPI-mode use of the SDIO pins: CLK=83, CMD=MOSI=82, DAT0=MISO=84, DAT3=CS=81 (DAT1/DAT2 unused). The board file lists no pull-ups on these pins: check before relying on it.
// Bring-up: 80 clocks, CMD0, CMD8, CMD55+ACMD41 until ready, CMD58 (CCS: block vs byte addressing), then the clock speeds up. `ready` goes high when the card is usable.
// Use: pulse rd_req or wr_req with `block`; `busy` is high until `block_done` pulses. Read words come out as w_valid/w_index/w_data; a write pulls words by src_addr (data wanted within 2 cycles).
// SPI mode 0, MSB first. INIT_DIV/FAST_DIV are clocks per SPI half-period (27 MHz: INIT_DIV=34 -> ~400 kHz; FAST_DIV=1 -> 13.5 MHz).
`default_nettype none
module sd_spi_v1 #(
    parameter INIT_DIV      = 34,
    parameter FAST_DIV      = 1,
    parameter TOKEN_WAIT    = 65535,
    parameter ACMD41_TRIES  = 4000,
    parameter BUSY_WAIT     = 1000000
) (
    input  wire        clk,
    input  wire        rst,
    output reg         sd_clk,
    output wire        sd_mosi,
    input  wire        sd_miso,
    output reg         sd_cs_n,
    output reg         ready,
    output reg         error,
    output reg  [4:0]  err_code,
    output reg  [5:0]  err_cmd,      // the command (CMD index) being sent when the error happened
    output reg  [7:0]  err_rx,       // the last byte the card sent before the error (FF = line idle high, 00 = stuck low)
    output reg         busy,
    input  wire        rd_req,
    input  wire        wr_req,
    input  wire [31:0] block,
    output reg         block_done,
    output reg         w_valid,
    output reg  [31:0] w_data,
    output reg  [6:0]  w_index,
    output wire [6:0]  src_addr,
    input  wire [31:0] src_data
);
    // ---- byte-level SPI master ----
    reg        fast;
    reg        xb_busy, xb_done, xb_go;
    reg  [7:0] xb_tx, xb_rx, tx_sh;
    reg  [2:0] bit_cnt;
    reg  [15:0] div_cnt;
    reg        mosi_r;
    assign sd_mosi = mosi_r;
    wire [15:0] div = fast ? FAST_DIV : INIT_DIV;
    always @(posedge clk) begin
        xb_done <= 1'b0;
        if (rst) begin
            xb_busy <= 1'b0; sd_clk <= 1'b0; mosi_r <= 1'b1; bit_cnt <= 3'd0; div_cnt <= 16'd0; xb_rx <= 8'hFF; tx_sh <= 8'hFF;
        end else if (xb_busy) begin
            if (div_cnt == 0) begin
                div_cnt <= div - 1'b1;
                if (!sd_clk) begin
                    sd_clk <= 1'b1;
                    xb_rx  <= {xb_rx[6:0], sd_miso};
                end else begin
                    sd_clk <= 1'b0;
                    if (bit_cnt == 3'd7) begin xb_busy <= 1'b0; xb_done <= 1'b1; mosi_r <= 1'b1; end
                    else begin bit_cnt <= bit_cnt + 1'b1; mosi_r <= tx_sh[6]; tx_sh <= {tx_sh[6:0], 1'b0}; end
                end
            end else div_cnt <= div_cnt - 1'b1;
        end else if (xb_go) begin
            xb_busy <= 1'b1; tx_sh <= xb_tx; mosi_r <= xb_tx[7]; bit_cnt <= 3'd0; div_cnt <= div - 1'b1;
        end
    end

    // ---- sequencer ----
    localparam [5:0]
        ST_BOOT = 0, ST_PWR = 1, ST_WAIT = 2, ST_I1 = 3, ST_I2 = 4, ST_I3 = 5, ST_I4 = 6, ST_I5 = 7, ST_IDLE = 8, ST_I6 = 9,
        C_SEND = 10, C_RESP0 = 11, C_RESP = 12, C_RESP2 = 13, C_EXT = 14, C_EXT2 = 15, C_FIN = 16, C_END = 17,
        ST_RD1 = 20, ST_RDTOK = 21, ST_RDTOK2 = 22, ST_RDD = 23, ST_RDD2 = 24, ST_RDCRC = 25, ST_RDCRC2 = 26,
        ST_WR1 = 30, ST_WR2 = 31, ST_WR3 = 32, ST_WR4 = 33, ST_WR5 = 34, ST_WR6 = 35, ST_WR7 = 36, ST_WR8 = 37, ST_WR9 = 38, ST_WRB = 39, ST_WRB2 = 40,
        ST_DONE = 50, ST_ERR = 51;
    reg [5:0]  st, nxt, ret;
    reg [5:0]  cmd_idx;
    reg [31:0] cmd_arg, ext;
    reg [7:0]  cmd_crc, r1;
    reg [2:0]  cmd_n, extra_n;
    reg        keep_cs, ccs, v2;
    reg [4:0]  poll;
    reg [8:0]  byte_i;
    reg [23:0] wacc;
    reg [23:0] cnt;
    assign src_addr = byte_i[8:2];

    task start_cmd(input [5:0] idx, input [31:0] arg, input [7:0] crc, input [2:0] extra, input keep, input [5:0] ret_to);
        begin cmd_idx <= idx; cmd_arg <= arg; cmd_crc <= crc; extra_n <= extra; keep_cs <= keep; ret <= ret_to; cmd_n <= 3'd0; st <= C_SEND; end
    endtask
    task send(input [7:0] b, input [5:0] next);
        begin xb_tx <= b; xb_go <= 1'b1; st <= ST_WAIT; nxt <= next; end
    endtask
    task fail(input [4:0] code);
        begin err_code <= code; err_cmd <= cmd_idx; err_rx <= xb_rx; st <= ST_ERR; end
    endtask
    wire [31:0] blk_addr = ccs ? block : {block[22:0], 9'b0};
    reg  [31:0] blk_l;

    always @(posedge clk) begin
        xb_go <= 1'b0; w_valid <= 1'b0; block_done <= 1'b0;
        if (rst) begin
            st <= ST_BOOT; ready <= 1'b0; error <= 1'b0; err_code <= 5'd0; err_cmd <= 6'd0; err_rx <= 8'd0; busy <= 1'b1; sd_cs_n <= 1'b1; fast <= 1'b0; ccs <= 1'b0; v2 <= 1'b0; cnt <= 0;
            w_data <= 0; w_index <= 0; wacc <= 0; byte_i <= 0; cmd_n <= 0; poll <= 0; ext <= 0; r1 <= 8'hFF; nxt <= ST_BOOT; ret <= ST_BOOT;
            cmd_idx <= 0; cmd_arg <= 0; cmd_crc <= 0; extra_n <= 0; keep_cs <= 0; blk_l <= 0;
        end else case (st)
            ST_BOOT: begin cnt <= 0; st <= ST_PWR; end
            ST_PWR:  if (cnt == 10) begin cnt <= 0; start_cmd(6'd0, 32'h0, 8'h95, 3'd0, 1'b0, ST_I1); end
                     else begin cnt <= cnt + 1'b1; send(8'hFF, ST_PWR); end
            ST_WAIT: if (xb_done) st <= nxt;

            // ---- generic command: 6 bytes out, R1 (+ extra bytes) back ----
            C_SEND: begin
                sd_cs_n <= 1'b0;
                cmd_n <= cmd_n + 1'b1;
                case (cmd_n)
                    3'd0: send({2'b01, cmd_idx}, C_SEND);
                    3'd1: send(cmd_arg[31:24], C_SEND);
                    3'd2: send(cmd_arg[23:16], C_SEND);
                    3'd3: send(cmd_arg[15:8],  C_SEND);
                    3'd4: send(cmd_arg[7:0],   C_SEND);
                    default: send(cmd_crc, C_RESP0);
                endcase
            end
            C_RESP0: begin poll <= 0; st <= C_RESP; end
            C_RESP:  send(8'hFF, C_RESP2);
            C_RESP2: if (!xb_rx[7]) begin r1 <= xb_rx; cmd_n <= 3'd0; ext <= 32'h0; st <= (extra_n != 0) ? C_EXT : C_FIN; end
                     else if (poll == 5'd15) fail(5'd2);
                     else begin poll <= poll + 1'b1; st <= C_RESP; end
            C_EXT:   if (cmd_n == extra_n) st <= C_FIN; else send(8'hFF, C_EXT2);
            C_EXT2:  begin ext <= {ext[23:0], xb_rx}; cmd_n <= cmd_n + 1'b1; st <= C_EXT; end
            C_FIN:   st <= keep_cs ? ret : C_END;
            C_END:   begin sd_cs_n <= 1'b1; send(8'hFF, ret); end

            // ---- initialisation ----
            ST_I1: if (r1 != 8'h01) fail(5'd3); else start_cmd(6'd8, 32'h000001AA, 8'h87, 3'd4, 1'b0, ST_I2);
            ST_I2: begin cnt <= 0; v2 <= !r1[2]; start_cmd(6'd55, 32'h0, 8'h65, 3'd0, 1'b0, ST_I3); end     // an SD 1.x card answers CMD8 "illegal command" (R1 bit 2)
            ST_I3: start_cmd(6'd41, v2 ? 32'h40000000 : 32'h0, 8'h77, 3'd0, 1'b0, ST_I4);                 // HCS only for a v2 card
            ST_I4: if (r1 == 8'h00) start_cmd(6'd58, 32'h0, 8'hFD, 3'd4, 1'b0, ST_I5);
                   else if (cnt >= ACMD41_TRIES) fail(5'd4);
                   else begin cnt <= cnt + 1'b1; start_cmd(6'd55, 32'h0, 8'h65, 3'd0, 1'b0, ST_I3); end
            ST_I5: begin ccs <= ext[30];
                         if (ext[30]) begin fast <= 1'b1; ready <= 1'b1; busy <= 1'b0; st <= ST_IDLE; end
                         else start_cmd(6'd16, 32'd512, 8'hFF, 3'd0, 1'b0, ST_I6);                        // a byte-addressed card: fix the block length at 512
                     end
            ST_I6: if (r1 != 8'h00) fail(5'd11); else begin fast <= 1'b1; ready <= 1'b1; busy <= 1'b0; st <= ST_IDLE; end

            // ---- idle: take a request ----
            ST_IDLE: if (rd_req) begin busy <= 1'b1; blk_l <= blk_addr; start_cmd(6'd17, blk_addr, 8'hFF, 3'd0, 1'b1, ST_RD1); end
                     else if (wr_req) begin busy <= 1'b1; start_cmd(6'd24, blk_addr, 8'hFF, 3'd0, 1'b1, ST_WR1); end

            // ---- read one block ----
            ST_RD1:    if (r1 != 8'h00) fail(5'd5); else begin cnt <= 0; st <= ST_RDTOK; end
            ST_RDTOK:  send(8'hFF, ST_RDTOK2);
            ST_RDTOK2: if (xb_rx == 8'hFE) begin byte_i <= 0; st <= ST_RDD; end
                       else if (xb_rx != 8'hFF) fail(5'd6);
                       else if (cnt >= TOKEN_WAIT) fail(5'd7);
                       else begin cnt <= cnt + 1'b1; st <= ST_RDTOK; end
            ST_RDD:    send(8'hFF, ST_RDD2);
            ST_RDD2:   begin
                           wacc <= {xb_rx, wacc[23:8]};                          // bytes arrive lowest first: after 4 the first is at the bottom
                           if (byte_i[1:0] == 2'b11) begin w_data <= {xb_rx, wacc[23:0]}; w_index <= byte_i[8:2]; w_valid <= 1'b1; end
                           byte_i <= byte_i + 1'b1;
                           if (byte_i == 9'd511) begin cnt <= 0; st <= ST_RDCRC; end else st <= ST_RDD;
                       end
            ST_RDCRC:  if (cnt == 2) begin ret <= ST_DONE; st <= C_END; end else begin cnt <= cnt + 1'b1; send(8'hFF, ST_RDCRC); end

            // ---- write one block ----
            ST_WR1: if (r1 != 8'h00) fail(5'd8); else send(8'hFF, ST_WR2);
            ST_WR2: begin byte_i <= 0; send(8'hFE, ST_WR3); end
            ST_WR3: st <= ST_WR4;                                                // src_addr is valid now; the word arrives next cycle
            ST_WR4: st <= ST_WR5;
            ST_WR5: send(src_data[8*byte_i[1:0] +: 8], ST_WR6);
            ST_WR6: begin byte_i <= byte_i + 1'b1; if (byte_i == 9'd511) begin cnt <= 0; st <= ST_WR7; end else st <= ST_WR3; end
            ST_WR7: if (cnt == 2) st <= ST_WR8; else begin cnt <= cnt + 1'b1; send(8'hFF, ST_WR7); end   // two CRC bytes (not checked in SPI mode)
            ST_WR8: send(8'hFF, ST_WR9);                                        // the card's data response
            ST_WR9: if (xb_rx[4:0] != 5'b00101) fail(5'd9); else begin cnt <= 0; st <= ST_WRB; end
            ST_WRB: send(8'hFF, ST_WRB2);                                       // busy: the card holds MISO low until it has programmed the block
            ST_WRB2: if (xb_rx == 8'hFF) begin ret <= ST_DONE; st <= C_END; end
                     else if (cnt >= BUSY_WAIT) fail(5'd10);
                     else begin cnt <= cnt + 1'b1; st <= ST_WRB; end

            ST_DONE: begin block_done <= 1'b1; busy <= 1'b0; st <= ST_IDLE; end
            ST_ERR:  begin error <= 1'b1; busy <= 1'b0; sd_cs_n <= 1'b1; end
            default: st <= ST_ERR;
        endcase
    end
endmodule
`default_nettype wire
