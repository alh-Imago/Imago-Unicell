// jtag_link_v1.v - a byte link between the PC and the host bridge through the FPGA's JTAG user register 1 (Xilinx BSCANE2).
// It replaces the UART on the Kintex card, which has no serial port.  Same byte-stream interface the UART gave the bridge:
//   rb_data / rb_valid  bytes from the PC (one-clock valid pulse)        tb_data / tb_send / tb_busy  bytes to the PC (send is ignored while busy)
// Everything runs in the system clock.  The JTAG signals (DRCK, CAPTURE, SHIFT, SEL, TDI) are treated as slow data, two-flop synchronised and
// edge detected, so there is no second clock domain.  Only BSCANE2 outputs the open toolchain is known to route are used (DRCK, CAPTURE, SHIFT, SEL, TDI;
// no UPDATE, no TCK).  The system clock must be at least 4 times faster than the JTAG clock (the host keeps TCK at 6 MHz or less).
//
// One scan of the user register is W = 16 + 8*K bits, shifted LSB first in both directions:
//   host -> design: [7:0] ntx = payload bytes sent (0..K)   [8] ack = clear the outbox (the host has taken the bytes it was shown)   [15:12] must be 4'hA
//                   [16+8i +: 8] payload byte i
//   design -> host: [7:0] nout = payload bytes in this window (0..K)   [8] ready = the design can take K more bytes   [15:12] = 4'h5
//                   [16+8i +: 8] payload byte i
// A scan's host word is acted on at the START of the next scan (at CAPTURE), so a scan whose marker is not 4'hA (nothing was shifted in) is ignored.
// A window with bytes, once shown, stays the same until acked (two banks: the other one fills meanwhile), so nothing is lost or repeated.
// An ack is acted on at the NEXT capture, so the response that comes back in the very scan that carries the ack is the old window again:
// THE HOST MUST IGNORE THE PAYLOAD OF THE RESPONSE TO ANY SCAN IT SENT AN ACK IN.  Two scans per K bytes received.  See jtagport.py.
module jtag_link_v1 #(
    parameter K = 32,                 // payload bytes per scan and direction
    parameter RXGAP = 512,            // clocks between bytes handed to the bridge (the UART gave one byte per 4340 clocks at 115200 baud, 50 MHz)
    parameter FAW = 9                 // FIFO depth 2**FAW bytes
) (
    input  wire       clk,
    input  wire       rst,
    // BSCANE2 side
    input  wire       j_drck, j_capture, j_shift, j_sel, j_tdi,
    output wire       j_tdo,
    // bridge side
    output reg  [7:0] rb_data,
    output reg        rb_valid,
    input  wire [7:0] tb_data,
    input  wire       tb_send,
    output wire       tb_busy,
    output reg        act                 // pulses while the link is in use (for an LED)
);
    localparam W = 16 + 8*K;
    localparam CW = $clog2(K + 1);

    // ---- synchronisers and edge detection
    reg [2:0] s_drck = 0, s_cap = 0, s_shift = 0, s_sel = 0, s_tdi = 0;
    always @(posedge clk) begin
        s_drck <= {s_drck[1:0], j_drck};   s_cap <= {s_cap[1:0], j_capture};   s_shift <= {s_shift[1:0], j_shift};
        s_sel  <= {s_sel[1:0], j_sel};     s_tdi <= {s_tdi[1:0], j_tdi};
    end
    wire drck_rise = (s_drck[2:1] == 2'b01);
    wire cap_rise  = (s_cap[2:1] == 2'b01) && s_sel[1];
    wire shifting  = s_shift[1] && s_sel[1];

    // ---- shift register: the response goes out, the host word comes in
    reg [W-1:0] sr = {W{1'b0}};
    assign j_tdo = sr[0];

    // ---- receive FIFO (PC -> bridge) and transmit FIFO (bridge -> PC)
    reg [7:0] rxf [0:(1<<FAW)-1];  reg [FAW:0] rx_w = 0, rx_r = 0;
    reg [7:0] txf [0:(1<<FAW)-1];  reg [FAW:0] tx_w = 0, tx_r = 0;
    wire [FAW:0] rx_cnt = rx_w - rx_r;
    wire [FAW:0] tx_cnt = tx_w - tx_r;
    wire rx_ready = (rx_cnt <= (1<<FAW) - 2*K - 2);              // room for the next window
    assign tb_busy = (tx_cnt >= (1<<FAW) - 4);
    always @(posedge clk) if (tb_send && !tb_busy) begin txf[tx_w[FAW-1:0]] <= tb_data; tx_w <= tx_w + 1'b1; end

    // ---- outbox: two banks of up to K bytes.  The bank being shown (cur) is sealed once a window with bytes has been shown; the other bank fills from the
    //      transmit FIFO in the meantime.  An ack (processed at the next CAPTURE) empties the shown bank and switches to the other one at once.
    localparam [CW-1:0] KK = K;
    reg [8*K-1:0] obk0 = 0, obk1 = 0; reg [CW-1:0] obn0 = 0, obn1 = 0; reg cur = 0; reg sealed = 0;
    wire fb = sealed ? ~cur : cur;                                   // the bank the FIFO is being drained into
    wire [CW-1:0] fbn = fb ? obn1 : obn0;
    // ---- word taken from the shift register at CAPTURE
    reg [W-1:0] rxw = 0; reg rxw_pend = 0; reg [CW-1:0] rxw_i = 0; reg [CW-1:0] rxw_n = 0;
    reg [15:0] gap = 0; reg [9:0] actc = 0;
    wire        host_ok  = (sr[15:12] == 4'hA);
    wire        ack_now  = host_ok && sr[8];
    wire        show     = ack_now ? ~cur : cur;                     // bank shown in this response
    wire [CW-1:0] nshow  = show ? obn1 : obn0;
    wire [8*K-1:0] bshow = show ? obk1 : obk0;
    always @(posedge clk) begin
        rb_valid <= 1'b0;
        if (rst) begin
            rx_w <= 0; rx_r <= 0; tx_r <= 0; obn0 <= 0; obn1 <= 0; cur <= 0; sealed <= 0; rxw_pend <= 0; sr <= {W{1'b0}}; gap <= 0; act <= 0; actc <= 0;
        end else begin
            // shift on every DRCK rising edge while shifting
            if (drck_rise && shifting) sr <= {s_tdi[1], sr[W-1:1]};
            if (cap_rise) begin
                // act on the host word now (only if its marker is right): the ack empties the shown bank and moves on, the payload is queued
                rxw <= sr;
                if (ack_now) begin
                    if (cur) obn1 <= 0; else obn0 <= 0;
                    cur <= ~cur;
                end
                sealed <= (nshow != 0);                              // a window with bytes has been shown: keep it until acked
                if (host_ok) begin
                    rxw_n <= (sr[7:0] > K) ? KK : sr[CW-1:0];
                    rxw_i <= 0; rxw_pend <= (sr[7:0] != 0) && rx_ready;
                end
                sr <= {bshow, 4'h5, 3'b000, rx_ready, 8'd0 | nshow};
                act <= 1'b1; actc <= 10'h3FF;
            end
            if (actc != 0) actc <= actc - 1'b1; else act <= 1'b0;
            // queue payload bytes into the receive FIFO, one per clock
            if (rxw_pend) begin
                rxf[rx_w[FAW-1:0]] <= rxw[16 + 8*rxw_i +: 8]; rx_w <= rx_w + 1'b1;
                if (rxw_i + 1 >= rxw_n) rxw_pend <= 1'b0; else rxw_i <= rxw_i + 1'b1;
            end
            // drain the transmit FIFO into the filling bank
            if (tx_cnt != 0 && fbn < KK && !cap_rise) begin
                if (fb) begin obk1[8*obn1 +: 8] <= txf[tx_r[FAW-1:0]]; obn1 <= obn1 + 1'b1; end
                else    begin obk0[8*obn0 +: 8] <= txf[tx_r[FAW-1:0]]; obn0 <= obn0 + 1'b1; end
                tx_r <= tx_r + 1'b1;
            end
            // hand bytes to the bridge at a fixed pace
            if (gap != 0) gap <= gap - 1'b1;
            else if (rx_cnt != 0) begin rb_data <= rxf[rx_r[FAW-1:0]]; rb_valid <= 1'b1; rx_r <= rx_r + 1'b1; gap <= RXGAP; end
        end
    end
endmodule
