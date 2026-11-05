`default_nettype none
`timescale 1ns / 1ps
// hexn_base_ctl_v1 -- BASE controller for a Kintex card holding a JUDGE and up to 4 hex pattern ARRAYS in one bitstream (5 Nov 2026, Alan 10:53: "start with 2 ... a base size of the design ... before, during and after could become just a program state"). NEW file. Not run on any card yet.
// It sits between the JTAG byte port (rx_d/rx_v/tx_d/tx_s/tx_b of hexn_jtag_bridge_v1) and NARR copies of hexn_frame_v6 (one per array), and holds: the SELECTOR (which array the host talks to), a PROGRAM LIBRARY (4 slots of 256 bytes: config-chain images, block RAM), and the JUDGE (hexn_scorer_v3) with a small queue that can feed it the selected array's output words by itself (AFTER mode).
// Commands (opcode byte first). Anything that is not one of these is passed to the selected array's frame unchanged (I W B D G L S of hexn_frame_v6, same replies), so every array test of the single-array design works after 'A n':
//   'A' n            select array n (0..NARR-1)                               -> 'K'
//   'N'              base info                                                -> 6 bytes: id 0x42415345 little endian (45 53 41 42), NARR, 4 (library slots)
//   'P' s lh ll d..  write library slot s (0..3): length = lh*256+ll (<= 256), then that many bytes -> 'K'
//   'Q' s            load the selected array's config chain from library slot s: the controller sends 'B' and the array's chain bytes (CHB bytes) to the frame, 16 clocks apart; the frame answers 'K' as for a host 'B'
//   'J' b0 b1 b2 b3  one word (little endian) to the judge (LOAD / BIAS / SCORE words of hexn_scorer_v3) -> 'K' when the judge has taken it
//   'M' m            mode: bit 0 = AFTER mode (the selected array's output words go to the judge by themselves, each nibble limited to 11 = a bin); bit 1 = empty the queues and counters   -> 'K'
//   'R'              next judge result (oldest first) -> 6 bytes: n (results waiting, before this one is taken), 4 result bytes little endian (0 if none), lost (words the judge queue had to drop, saturating)
//   'C' a b          slot choice table: judge result with pred 0 -> slot a, with pred 1 -> slot b (default 0, 1)  -> 'K'
//   'Z'              CHOOSE AND LOAD (judge BEFORE the run, slot side): takes the oldest judge result, picks the slot from the table by its pred bit (bit 31), and loads that slot into the selected array exactly like 'Q' (the frame answers 'K'); with no result waiting it answers 'E' and does nothing
//   'U'              last choice -> 2 bytes: the slot chosen by the last 'Z', the number of choices made (saturating at 255)
// Commands are taken only when the selected frame is idle and no base command is running; bytes that follow a command are its arguments.
module hexn_base_ctl_v1 #(parameter NARR = 1, parameter [16*4-1:0] CHB = {16'd0, 16'd0, 16'd0, 16'd164}) (
    input wire clk,
    input wire [7:0] rx_d, input wire rx_v, output wire [7:0] tx_d, output wire tx_s, input wire tx_b,
    output wire [NARR-1:0] a_rx_v, output wire [7:0] a_rx_d,
    input wire [8*NARR-1:0] a_tx_d, input wire [NARR-1:0] a_tx_s, input wire [NARR-1:0] a_ov, input wire [32*NARR-1:0] a_od, input wire [NARR-1:0] a_idle);
    // ---------------- selector and state
    reg [1:0] sel = 0;
    localparam IDLE = 0, ARGA = 1, ARGPS = 2, ARGPH = 3, ARGPL = 4, PDATA = 5, ARGQ = 6, QRUN = 7, ARGJ = 8, JWAIT = 9, ARGM = 10, REPLY = 11, ARGC1 = 12, ARGC2 = 13;
    reg [3:0] cs = IDLE;
    wire sel_idle = a_idle[sel];
    wire is_op = (rx_d == 8'h41) || (rx_d == 8'h4e) || (rx_d == 8'h50) || (rx_d == 8'h51) || (rx_d == 8'h4a) || (rx_d == 8'h4d) || (rx_d == 8'h52) || (rx_d == 8'h43) || (rx_d == 8'h5a) || (rx_d == 8'h55);
    wire mine = rx_v && cs == IDLE && sel_idle && is_op;
    // ---------------- replay of a library slot into the selected frame
    reg rp_v = 0; reg [7:0] rp_d = 0;
    assign a_rx_d = rp_v ? rp_d : rx_d;
    genvar g; generate for (g = 0; g < NARR; g = g + 1) begin : rxg
        assign a_rx_v[g] = (sel == g) && ((rx_v && cs == IDLE && !mine) || rp_v);
    end endgenerate
    // ---------------- program library: 4 slots x 256 bytes (block RAM: one write port, one registered read port)
    (* ram_style = "block" *) reg [7:0] lib [0:1023];
    reg [9:0] laddr = 0; reg [7:0] libq = 0; reg lw = 0; reg [9:0] lwa = 0; reg [7:0] lwd = 0;
    always @(posedge clk) begin libq <= lib[laddr]; if (lw) lib[lwa] <= lwd; end
    reg [1:0] pslot = 0; reg [15:0] plen = 0; reg [7:0] pi = 0;
    reg [1:0] qslot = 0; reg [8:0] qi = 0; reg [4:0] rc = 0; reg qb = 0; wire [15:0] chb_sel = CHB[16*sel +: 16];
    // ---------------- judge and its queues
    reg [31:0] jw = 0; reg [1:0] jn = 0; reg jhost = 0;
    reg [31:0] af [0:3]; reg [2:0] afn = 0; reg [1:0] afr = 0, afw = 0; reg [7:0] lost = 0;           // words from the array waiting for the judge
    reg [31:0] rq [0:7]; reg [3:0] rqn = 0; reg [2:0] rqr = 0, rqw = 0;                              // judge results waiting for the host
    reg automode = 0; reg [1:0] ch0 = 0, ch1 = 1, lastslot = 0; reg [7:0] nchoice = 0; reg [1:0] cnew;      // slot choice table and the last choice
    wire [31:0] raw = a_od[32*sel +: 32]; wire ovs = a_ov[sel];
    function [31:0] clampbins(input [31:0] x);
        integer i; begin for (i = 0; i < 8; i = i + 1) clampbins[4*i +: 4] = (x[4*i +: 4] > 4'd11) ? 4'd11 : x[4*i +: 4]; end
    endfunction
    wire j_ack, j_ov; wire [31:0] j_od; wire j_clrb, j_dmv, j_dml, j_dmb; wire [31:0] j_dmd;
    wire j_in_v = jhost | (afn != 0); wire [31:0] j_in_d = jhost ? jw : af[afr];
    reg [3:0] por = 4'hf; always @(posedge clk) if (por != 0) por <= por - 1'b1;                       // power-on reset of the judge (its registers have no initial values)
    hexn_scorer_v3 judge (.clk(clk), .rst(por != 0), .in_data(j_in_d), .in_valid(j_in_v), .in_ack(j_ack), .out_data(j_od), .out_valid(j_ov), .out_ack(1'b1),
                          .clr(1'b0), .clr_busy(j_clrb), .dump(1'b0), .dm_valid(j_dmv), .dm_data(j_dmd), .dm_last(j_dml), .dm_busy(j_dmb));
    // ---------------- reply path of the controller
    reg [47:0] rbuf = 0; reg [2:0] rn = 0, ri = 0; reg c_go = 0; reg [7:0] c_d = 0;
    assign tx_s = c_go | (|a_tx_s); assign tx_d = c_go ? c_d : a_tx_d[8*sel +: 8];
    task reply_k; begin rbuf[7:0] <= 8'h4b; rn <= 1; ri <= 0; cs <= REPLY; end endtask
    always @(posedge clk) begin
        c_go <= 1'b0; rp_v <= 1'b0; lw <= 1'b0;
        // judge side: results in, words from the array in (AFTER mode)
        if (por == 0) begin       // not before the judge has been reset (its outputs are unknown until then)
        if (j_ov) begin if (rqn < 8) begin rq[rqw] <= j_od; rqw <= rqw + 1'b1; end end
            if (automode && ovs) begin
                if (afn < 4) begin af[afw] <= clampbins(raw); afw <= afw + 1'b1; end else if (lost != 8'hff) lost <= lost + 1'b1;
            end
            if (j_ack && !jhost && afn != 0) begin afr <= afr + 1'b1; end
            afn <= afn + ((automode && ovs && afn < 4) ? 3'd1 : 3'd0) - ((j_ack && !jhost && afn != 0) ? 3'd1 : 3'd0);
            rqn <= rqn + ((j_ov && rqn < 8) ? 4'd1 : 4'd0);
        end
        case (cs)
            IDLE: if (mine) case (rx_d)
                8'h41: cs <= ARGA;
                8'h4e: begin rbuf <= {8'd4, NARR[7:0], 8'h42, 8'h41, 8'h53, 8'h45}; rn <= 6; ri <= 0; cs <= REPLY; end
                8'h50: cs <= ARGPS;
                8'h51: cs <= ARGQ;
                8'h4a: begin jn <= 0; cs <= ARGJ; end
                8'h4d: cs <= ARGM;
                8'h43: cs <= ARGC1;
                8'h55: begin rbuf <= {32'd0, nchoice, 6'd0, lastslot}; rn <= 2; ri <= 0; cs <= REPLY; end
                8'h5a: begin
                    if (rqn == 0) begin rbuf[7:0] <= 8'h45; rn <= 1; ri <= 0; cs <= REPLY; end
                    else begin
                        cnew = rq[rqr][31] ? ch1 : ch0; lastslot <= cnew; if (nchoice != 8'hff) nchoice <= nchoice + 1'b1;
                        rqr <= rqr + 1'b1; rqn <= rqn - 1'b1 + ((j_ov && rqn < 8) ? 4'd1 : 4'd0);
                        qslot <= cnew; qi <= 0; qb <= 0; rc <= 0; laddr <= {cnew, 8'd0}; cs <= QRUN;
                    end
                end
                8'h52: begin
                    rbuf <= {lost, (rqn != 0) ? rq[rqr] : 32'd0, 4'd0, rqn};
                    if (rqn != 0) begin rqr <= rqr + 1'b1; rqn <= rqn - 1'b1 + ((j_ov && rqn < 8) ? 4'd1 : 4'd0); end
                    rn <= 6; ri <= 0; cs <= REPLY;
                end
                default: ;
            endcase
            ARGC1: if (rx_v) begin ch0 <= rx_d[1:0]; cs <= ARGC2; end
            ARGC2: if (rx_v) begin ch1 <= rx_d[1:0]; reply_k; end
            ARGA: if (rx_v) begin if (rx_d < NARR) sel <= rx_d[1:0]; reply_k; end
            ARGPS: if (rx_v) begin pslot <= rx_d[1:0]; cs <= ARGPH; end
            ARGPH: if (rx_v) begin plen[15:8] <= rx_d; cs <= ARGPL; end
            ARGPL: if (rx_v) begin plen[7:0] <= rx_d; pi <= 0; if ({plen[15:8], rx_d} == 16'd0) reply_k; else cs <= PDATA; end
            PDATA: if (rx_v) begin
                lw <= 1'b1; lwa <= {pslot, pi}; lwd <= rx_d; pi <= pi + 1'b1; plen <= plen - 1'b1;
                if (plen == 16'd1) reply_k;
            end
            ARGQ: if (rx_v) begin qslot <= rx_d[1:0]; qi <= 0; qb <= 0; rc <= 0; laddr <= {rx_d[1:0], 8'd0}; cs <= QRUN; end
            QRUN: begin
                if (rc != 0) rc <= rc - 1'b1;
                else if (!qb) begin rp_v <= 1'b1; rp_d <= 8'h42; qb <= 1'b1; rc <= 5'd15; end
                else if (qi < chb_sel) begin rp_v <= 1'b1; rp_d <= libq; qi <= qi + 1'b1; laddr <= {qslot, qi[7:0] + 8'd1}; rc <= 5'd15; end
                else cs <= IDLE;
            end
            ARGJ: if (rx_v) begin jw[8*jn +: 8] <= rx_d; jn <= jn + 1'b1; if (jn == 2'd3) cs <= JWAIT; end
            JWAIT: begin jhost <= 1'b1; if (j_ack && jhost) begin jhost <= 1'b0; reply_k; end end
            ARGM: if (rx_v) begin
                automode <= rx_d[0];
                if (rx_d[1]) begin afn <= 0; afr <= 0; afw <= 0; rqn <= 0; rqr <= 0; rqw <= 0; lost <= 0; end
                reply_k;
            end
            REPLY: if (!tx_b && !c_go) begin
                c_d <= rbuf[8*ri +: 8]; c_go <= 1'b1;
                if (ri == rn - 1) cs <= IDLE; else ri <= ri + 1'b1;
            end
            default: cs <= IDLE;
        endcase
    end
endmodule
`default_nettype wire
