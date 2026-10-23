// hexn_jtag_bridge_v1.v -- host link over JTAG for boards that have no UART (the Kintex-7 card YPCB-00338-1P1). Carries the same byte stream as the serial link of the Tang top, so hexn_core_v1 and every host suite run unchanged on top of it (tools/hexn_jtag_host_v1.py).
// Physical: one Xilinx BSCANE2 (USER chain CHAIN, default USER1 = IR 0x02, as designs/hello of the ypcb-00338-1p1 repo). One scan = one FRAME of 160 bits, bit 0 shifted out first:
//   host -> card (what the update takes): [7:0] nsend (0..14 data bytes in this frame), [15:8] ack (the host's count of bytes received so far, mod 256), [23:16] seq, [31:24] 0, [47:32] CRC16, [159:48] 14 data bytes (byte i at [48+8i +: 8]).
//   card -> host (what the capture gives, a snapshot of the card's state taken BEFORE this frame's update): [7:0] nvalid (bytes from the card in this frame, up to 14, the head of the output queue), [15:8] pop_total (bytes ever dropped from the queue, mod 256, = the abs index of data byte 0), [23:16] seq of the last frame accepted, [31:24] rx_free (14 when the card can take a frame with data, else 0), [47:32] CRC16, [159:48] 14 data bytes.
//   CRC16 = CCITT (poly 0x1021, init 0xFFFF) over the 144 bits {bits[31:0], bits[159:48]}, most significant bit first (the 144-bit number as written, bit 143 first).
// Rules: a frame with a wrong CRC is ignored. The ack is idempotent (the card drops bytes up to the acked count; it never drops more than it holds). A frame with data (nsend > 0) is taken only if its seq differs from the last accepted seq AND the card's input buffer is empty (rx_free = 14); the host repeats it until the echoed seq matches, so every byte arrives exactly once. Frames with nsend = 0 (polls) are always harmless. The host's capture is checked by its CRC (the capture crosses from the 50 MHz clock to TCK; a torn read fails the CRC and the host just reads again).
// Timing assumptions (documented, not enforced): TCK <= 12.5 MHz (the ypcb openocd.cfg uses 10 MHz) so the UPDATE pulse is seen by the 3-stage synchronizer and the frame is applied before the next capture.
// Core side (matches hexn_core_v1): rx_d/rx_v to the core (one byte every FSPACING clocks, as the UART delivered them), tx_d/tx_s from the core (a pulse per byte), tx_b busy.
`default_nettype none
module hexn_jtag_bridge_v1 #(parameter CHAIN = 1, parameter FSPACING = 128) (
    input  wire clk, input wire rst,
    output reg [7:0] rx_d, output reg rx_v,
    input  wire [7:0] tx_d, input wire tx_s, output wire tx_b);
    function [15:0] crc16(input [143:0] d);
        integer i; reg [15:0] c; reg fb;
        begin c = 16'hFFFF; for (i = 143; i >= 0; i = i - 1) begin fb = c[15] ^ d[i]; c = {c[14:0], 1'b0}; if (fb) c = c ^ 16'h1021; end crc16 = c; end
    endfunction
    // ---------------- TCK side: the 160-bit shift register (as designs/hello) ----------------
    wire capture, drck, sel, shift, tdi, update;
    reg [159:0] sr = 0; wire [159:0] snap;
    BSCANE2 #(.JTAG_CHAIN(CHAIN)) bscan (.CAPTURE(capture), .DRCK(drck), .RESET(), .RUNTEST(), .SEL(sel), .SHIFT(shift), .TCK(), .TDI(tdi), .TMS(), .UPDATE(update), .TDO(sr[0]));
    always @(posedge drck) if (capture) sr <= snap; else if (shift) sr <= {tdi, sr[159:1]};
    // ---------------- clock side ----------------
    reg [2:0] us = 0; always @(posedge clk) us <= {us[1:0], update};
    wire upd = us[1] & ~us[2];
    // output queue (core -> host): 32 bytes, circular (one 256-bit vector, so that plain always @* and plain Verilog readers see every bit)
    reg [255:0] qv = 0; reg [4:0] rd = 0, wr = 0; reg [5:0] cnt = 0; reg [7:0] pop_total = 0, last_seq = 0;
    reg pend_v = 0; reg [7:0] pend_d = 0;
    assign tx_b = tx_s | pend_v | (cnt >= 6'd28);
    // input buffer (host -> core): one frame at a time
    reg [111:0] rxbuf = 0; reg [3:0] rxn = 0, rxi = 0; reg [7:0] fd = 0;
    // frame application
    reg [159:0] rf = 0; reg ap = 0;
    wire [15:0] rf_crc = crc16({rf[31:0], rf[159:48]}); wire rf_ok = (rf_crc == rf[47:32]);
    wire [7:0] f_nsend = rf[7:0], f_ack = rf[15:8], f_seq = rf[23:16];
    wire [7:0] delta = f_ack - pop_total;
    wire do_pop = ap & rf_ok & (delta != 0) & (delta <= {2'b00, cnt});
    wire do_push = pend_v & (cnt < 6'd32);
    always @(posedge clk) begin
        rx_v <= 1'b0; ap <= 1'b0;
        if (rst) begin rd <= 0; wr <= 0; cnt <= 0; pop_total <= 0; last_seq <= 0; pend_v <= 0; rxn <= 0; rxi <= 0; fd <= 0; end
        else begin
            if (tx_s) begin pend_v <= 1'b1; pend_d <= tx_d; end
            if (do_push) begin qv[8*wr +: 8] <= pend_d; wr <= wr + 1'b1; if (!tx_s) pend_v <= 1'b0; end
            if (do_pop) begin rd <= rd + delta[4:0]; pop_total <= f_ack; end
            cnt <= cnt - (do_pop ? {1'b0, delta[4:0]} : 6'd0) + (do_push ? 6'd1 : 6'd0);
            if (upd) begin rf <= sr; ap <= 1'b1; end
            if (ap & rf_ok & (f_nsend != 0) & (f_nsend <= 8'd14) & (f_seq != last_seq) & (rxn == 0)) begin rxbuf <= rf[159:48]; rxn <= f_nsend[3:0]; rxi <= 0; last_seq <= f_seq; end
            if (rxn != 0) begin
                if (fd == 0) begin rx_d <= rxbuf[8*rxi +: 8]; rx_v <= 1'b1; rxi <= rxi + 1'b1; rxn <= rxn - 1'b1; fd <= FSPACING; end else fd <= fd - 1'b1;
            end
        end
    end
    // snapshot for the host (refreshed every clock; consistent because header, data and CRC are made from the same registers in the same cycle)
    function [111:0] headbytes(input [255:0] v, input [4:0] r, input [5:0] n);
        integer k; begin for (k = 0; k < 14; k = k + 1) headbytes[8*k +: 8] = (k < n) ? v[8*((r + k) & 31) +: 8] : 8'd0; end
    endfunction
    wire [111:0] sdata = headbytes(qv, rd, cnt);
    wire [31:0]  shdr  = {(rxn == 0) ? 8'd14 : 8'd0, last_seq, pop_total, (cnt > 6'd14) ? 8'd14 : {2'b00, cnt}};
    reg [159:0] snap_r = 0; always @(posedge clk) snap_r <= {sdata, crc16({shdr, sdata}), shdr};
    assign snap = snap_r;
endmodule
`default_nettype wire
