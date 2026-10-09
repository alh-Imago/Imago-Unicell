// spi_bridge_v1.v -- ledger #1036: an SPI SLAVE (mode 0, MSB first) so an ESP32 (or any SPI master) can drive the small unit: set registers, start the SD loads/saves and the playout, read
// status, and read the captured results. Everything runs in the system clock domain (SCLK / CS / MOSI are synchronised), so there are no clock-domain tricks -- but SCLK must be SLOWER than
// clk/16 (27 MHz -> at most ~1.6 MHz; a breadboard is happier at 1 MHz or less anyway).
//
// Transaction = CS low ... CS high. All multi-byte values are big-endian. byte 0 is the command:
//   0x01 WR_REG   : addr, d3 d2 d1 d0                      write a register
//   0x02 RD_REG   : addr, pad, then 4 more clocks return d3 d2 d1 d0   (send any 4 bytes while reading)
//   0x03 WR_WORDS : addrHi addrLo, then 4-byte words (auto-increment)  into the PLAYOUT RAM until CS rises
//   0x04 RD_WORDS : addrHi addrLo, pad, then 4-byte words (auto-increment) from the CAPTURE RAM until CS rises
// Registers: 0 ID (ro, 0x57320001) | 1 STATUS (ro) | 2 CONTROL (wo, pulses) | 3 START_BLOCK | 4 NBLOCKS | 5 PLAY_COUNT | 6 CAP_COUNT (ro) | 7 SCRATCH | 10 DESIGN_ID (ro, set by the generator per design; 0 = none)
//   8 MAX_OUT (pacing: at most this many results outstanding, 0 = unlimited) | 9 RPI (results per item, default 1). Pacing is for designs that hold ONE item at a time; clear the capture first (CONTROL bit 3).
//   STATUS: [0] sd_ready [1] sd_error [2] sd_busy [3] play_busy [4] sd_done (sticky) [5] play_done (sticky) [6] capture non-empty [12:8] sd err_code [21:16] command that failed [31:24] last byte the card sent. CONTROL [5] = re-run the SD start-up (no reload needed)
//   CONTROL: [0] sd_load [1] sd_save [2] play_start [3] capture_clear [4] clear the two sticky done bits (they also clear when an op starts)
`default_nettype none
module spi_bridge_v1 #(
    parameter AW = 10,
    parameter [31:0] DESIGN_ID = 32'h0     // which design is wrapped (register 10); the generator sets it, 0 = not set
) (
    input  wire            clk,
    input  wire            rst,
    input  wire            sclk,
    input  wire            cs_n,
    input  wire            mosi,
    output wire            miso,
    output reg             ctl_sd_load,
    output reg             ctl_sd_save,
    output reg             ctl_play_start,
    output reg             ctl_cap_clear,
    output reg             ctl_sd_reinit,
    output reg  [31:0]     start_block,
    output reg  [15:0]     nblocks,
    output reg  [AW:0]     play_count,
    output reg  [AW:0]     max_out,
    output reg  [AW:0]     rpi,
    input  wire            sd_ready,
    input  wire            sd_error,
    input  wire            sd_busy,
    input  wire            play_busy,
    input  wire [4:0]      err_code,
    input  wire [5:0]      err_cmd,
    input  wire [7:0]      err_rx,
    input  wire            sd_done_pulse,
    input  wire            play_done_pulse,
    input  wire [AW:0]     cap_count,
    output reg             pl_wr_en,
    output reg  [AW-1:0]   pl_wr_addr,
    output reg  [31:0]     pl_wr_data,
    output reg  [AW-1:0]   cap_rd_addr,
    input  wire [31:0]     cap_rd_data
);
    localparam [31:0] ID = 32'h57320001;
    reg [2:0] sclk_q, cs_q; reg [1:0] mosi_q;
    always @(posedge clk) begin sclk_q <= {sclk_q[1:0], sclk}; cs_q <= {cs_q[1:0], cs_n}; mosi_q <= {mosi_q[0], mosi}; end
    wire active = ~cs_q[1];
    wire rise = sclk_q[1] & ~sclk_q[2];
    wire fall = ~sclk_q[1] & sclk_q[2];

    reg [7:0] shin, tx_sh, tx_next;
    reg [2:0] bit_cnt;
    reg       strobe;
    reg [7:0] rxb;
    assign miso = tx_sh[7];

    reg [7:0]  bidx, cmd, raddr;
    reg [31:0] wdata, rv, word_cur, scratch;
    reg [AW-1:0] wr_ptr, rd_ptr;
    reg [7:0]  hi;
    reg        sd_done_seen, play_done_seen;
    wire [7:0] bsel = (bidx >= 8'd3) ? ((bidx - 8'd3) & 8'd3) : 8'd0;

    function [31:0] regread(input [7:0] a);
        case (a)
            8'd0: regread = ID;
            8'd1: regread = {err_rx, 2'b0, err_cmd, 3'b0, err_code, 1'b0, (cap_count != 0), play_done_seen, sd_done_seen, play_busy, sd_busy, sd_error, sd_ready};
            8'd3: regread = start_block;
            8'd4: regread = {16'b0, nblocks};
            8'd5: regread = {{(31-AW){1'b0}}, play_count};
            8'd6: regread = {{(31-AW){1'b0}}, cap_count};
            8'd7: regread = scratch;
            8'd8: regread = {{(31-AW){1'b0}}, max_out};
            8'd9: regread = {{(31-AW){1'b0}}, rpi};
            8'd10: regread = DESIGN_ID;
            default: regread = 32'h0;
        endcase
    endfunction

    // shift register side (bit level)
    always @(posedge clk) begin
        strobe <= 1'b0;
        if (rst || !active) begin bit_cnt <= 3'd0; tx_sh <= 8'h00; shin <= 8'h00; end
        else begin
            if (rise) begin
                shin <= {shin[6:0], mosi_q[1]};
                bit_cnt <= bit_cnt + 1'b1;
                if (bit_cnt == 3'd7) begin rxb <= {shin[6:0], mosi_q[1]}; strobe <= 1'b1; end
            end
            if (fall) begin
                if (bit_cnt == 3'd0) tx_sh <= tx_next; else tx_sh <= {tx_sh[6:0], 1'b0};
            end
        end
    end

    // byte level: one decision per received byte; the byte AFTER it (tx_next) is prepared here, in the many clock cycles before the next byte starts
    always @(posedge clk) begin
        ctl_sd_load <= 1'b0; ctl_sd_save <= 1'b0; ctl_play_start <= 1'b0; ctl_cap_clear <= 1'b0; ctl_sd_reinit <= 1'b0; pl_wr_en <= 1'b0;
        if (sd_done_pulse) sd_done_seen <= 1'b1;
        if (play_done_pulse) play_done_seen <= 1'b1;
        if (rst) begin
            bidx <= 0; cmd <= 0; tx_next <= 0; start_block <= 0; nblocks <= 0; play_count <= 0; max_out <= 0; rpi <= 1; scratch <= 0; wdata <= 0; rv <= 0; word_cur <= 0;
            sd_done_seen <= 0; play_done_seen <= 0; wr_ptr <= 0; rd_ptr <= 0; cap_rd_addr <= 0; pl_wr_addr <= 0; pl_wr_data <= 0; raddr <= 0; hi <= 0;
        end else if (!active) begin
            bidx <= 0; cmd <= 0; tx_next <= 8'h00;
        end else if (strobe) begin
            bidx <= (bidx == 8'hFF) ? bidx : bidx + 1'b1;
            tx_next <= 8'h00;
            if (bidx == 0) cmd <= rxb;
            else case (cmd)
                8'h01: begin                                                         // WR_REG: addr, then 4 data bytes
                    if (bidx == 1) raddr <= rxb;
                    else begin
                        wdata <= {wdata[23:0], rxb};
                        if (bidx == 5) begin
                            case (raddr)
                                8'd2: begin
                                    if ({wdata[23:0], rxb} & 32'h1) begin ctl_sd_load <= 1'b1; sd_done_seen <= 1'b0; end
                                    if ({wdata[23:0], rxb} & 32'h2) begin ctl_sd_save <= 1'b1; sd_done_seen <= 1'b0; end
                                    if ({wdata[23:0], rxb} & 32'h4) begin ctl_play_start <= 1'b1; play_done_seen <= 1'b0; end
                                    if ({wdata[23:0], rxb} & 32'h8) ctl_cap_clear <= 1'b1;
                                    if ({wdata[23:0], rxb} & 32'h20) ctl_sd_reinit <= 1'b1;
                                    if ({wdata[23:0], rxb} & 32'h10) begin sd_done_seen <= 1'b0; play_done_seen <= 1'b0; end
                                end
                                8'd3: start_block <= {wdata[23:0], rxb};
                                8'd4: nblocks <= {wdata[7:0], rxb};
                                8'd5: play_count <= {wdata[23:0], rxb};
                                8'd7: scratch <= {wdata[23:0], rxb};
                                8'd8: max_out <= {wdata[23:0], rxb};
                                8'd9: rpi <= {wdata[23:0], rxb};
                                default: ;
                            endcase
                        end
                    end
                end
                8'h02: begin                                                         // RD_REG: addr, pad, 4 data bytes out
                    if (bidx == 1) begin raddr <= rxb; rv <= regread(rxb); end
                    else if (bidx == 2) tx_next <= rv[31:24];
                    else if (bidx == 3) tx_next <= rv[23:16];
                    else if (bidx == 4) tx_next <= rv[15:8];
                    else if (bidx == 5) tx_next <= rv[7:0];
                end
                8'h03: begin                                                         // WR_WORDS: addrHi, addrLo, then words
                    if (bidx == 1) hi <= rxb;
                    else if (bidx == 2) wr_ptr <= {hi, rxb};
                    else begin
                        wdata <= {wdata[23:0], rxb};
                        if (bsel[1:0] == 2'd3) begin
                            pl_wr_en <= 1'b1; pl_wr_addr <= wr_ptr; pl_wr_data <= {wdata[23:0], rxb}; wr_ptr <= wr_ptr + 1'b1;
                        end
                    end
                end
                8'h04: begin                                                         // RD_WORDS: addrHi, addrLo, pad, then words out
                    if (bidx == 1) hi <= rxb;
                    else if (bidx == 2) begin rd_ptr <= {hi, rxb}; cap_rd_addr <= {hi, rxb}; end
                    else case (bsel[1:0])
                        2'd0: begin word_cur <= cap_rd_data; tx_next <= cap_rd_data[31:24]; rd_ptr <= rd_ptr + 1'b1; cap_rd_addr <= rd_ptr + 1'b1; end
                        2'd1: tx_next <= word_cur[23:16];
                        2'd2: tx_next <= word_cur[15:8];
                        2'd3: tx_next <= word_cur[7:0];
                    endcase
                end
                default: ;
            endcase
        end
    end
endmodule
`default_nettype wire
