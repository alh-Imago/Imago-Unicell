// host_bridge_v4.v - host_bridge_v3 plus the shared data RAM commands (the V reply reports version 7):
//   'M' addr(2) data(4)     write one word of the shared data RAM
//   'L' addr(2)             -> 4 bytes: the word at that address of the shared data RAM
//   'X' prog(1) base(2) len(2)   shared window of program class prog: words [base, base+len) of the shared data RAM (cleared by R)
//   'Z'                     -> 4 bytes: DSH(2) words of shared RAM, SHL(1) (window starts at data word index 2^SHL), log2(DSH)(1)
// Cloned from host_bridge_v3.v (left as proven).
// host_bridge_v3.v - host_bridge_v2 plus the B (region) command; the V reply reports version 6. Cloned from host_bridge_v2.v.
// host_bridge_v2.v - host_bridge plus H (hold) and G (go) commands; the V reply reports version 5. Cloned from host_bridge.v (left as proven).
// host_bridge.v - byte protocol between a PC (UART) and the sc_sys_v4 host ports.
// All multi-byte fields are little-endian.
//   'V'                              -> 8 bytes: 'S','C',6, S, IMEM_WORDS(2), DMW(2)   (link / build check)
//   'W' addr(2) data(4)              write one instruction word (broadcast to every slice)
//   'P' tid(2) code(2) lw(1) flags(1) prog(1)    submit a task.  flags bit0 = critical.
//   'Q' tid(2)                       -> 22 bytes: start(4) end(4) a0(4) arrival(4) pred(4) {state,trap}(1) slot(1)
//   'C'                              -> 56 bytes: cyc(4) done(4) launch_err(4) dispatches(4) busy(8) blocked(8)
//                                       tail(8) search(8) busy_leaders(8).  Read after the run: only cyc moves when idle.
//   'H'                              hold: tasks are accepted and queued but none is started (v2)
//   'G'                              go: release the hold; the queued tasks are placed together (v2)
//   'B' prog(1) cbase(2) clen(2) dlen(2)   set the region of program class prog: code words [cbase, cbase+clen) of the shared store, data words [0, dlen) (v3; cleared by R)
//   'R'                              reset the array (scheduler state and cores; the duration profile is kept)
module host_bridge_v4 #(parameter DIV = 234, parameter S = 8, parameter IMEM_WORDS = 256, parameter DMW = 64, parameter DSH = 256, parameter SHL = 14) (
    input  wire        clk,
    input  wire        rx,
    output wire        tx,
    // to sc_sys_v4
    output reg         h_push,
    output reg  [15:0] h_tid, h_code,
    output reg  [2:0]  h_lw,
    output reg         h_crit,
    output reg  [5:0]  h_prog,
    output reg         imem_we,
    output reg  [15:0] imem_wa,
    output reg  [31:0] imem_wd,
    output reg  [15:0] q_tid,
    output reg         soft_rst,
    output reg         hold,
    output reg         rg_we,
    output reg  [5:0]  rg_prog,
    output reg  [15:0] rg_cbase, rg_clen, rg_dlen,
    output reg         rs_we,
    output reg  [5:0]  rs_prog,
    output reg  [15:0] rs_base, rs_len,
    output reg         dh_we, dh_rd,
    output reg  [15:0] dh_a,
    output reg  [31:0] dh_wd,
    input  wire [31:0] dh_q,
    input  wire        dh_qv,
    input  wire        dh_busy,
    input  wire [31:0] q_start, q_end, q_a0, q_arr,
    input  wire        q_trap,
    input  wire [1:0]  q_state,
    input  wire [5:0]  q_slot,
    input  wire [24:0] q_pred,
    input  wire [31:0] o_cyc, o_done, o_lerr, o_disp,
    input  wire [63:0] o_busy, o_blocked, o_tail, o_search,
    input  wire [S-1:0] o_busy_l,
    output reg         act_rx, act_tx
);
    wire [7:0] rb; wire rv;
    uart_rx #(.DIV(DIV)) urx (.clk(clk), .rx(rx), .data(rb), .valid(rv));
    reg  [7:0] tb = 0; reg tsend = 0; wire tbusy;
    uart_tx #(.DIV(DIV)) utx (.clk(clk), .data(tb), .send(tsend), .tx(tx), .busy(tbusy));

    localparam IDLE = 0, ARGS = 1, EXEC = 2, REPLY = 3, WAITD = 4;
    reg [2:0]  st = IDLE;
    reg [31:0] dsave = 0;
    reg [7:0]  cmd = 0;
    reg [3:0]  need = 0, got = 0;
    reg [7:0]  a [0:6];
    reg [6:0]  rlen = 0, ridx = 0;
    reg [31:0] cyc_s = 0;
    reg [3:0]  rstcnt = 0;
    reg [23:0] stx = 0, srx = 0;

    function [7:0] rbyte(input [7:0] c, input [6:0] i);
        reg [63:0] w;
        begin
            w = 64'd0;
            if (c == "Q") begin
                case (i[6:2])
                    0: w = q_start;  1: w = q_end;  2: w = q_a0;  3: w = q_arr;  4: w = {7'b0, q_pred};
                    default: w = 64'd0;
                endcase
                if (i < 20) rbyte = w >> (8 * i[1:0]);
                else if (i == 20) rbyte = {5'b0, q_state, q_trap};
                else rbyte = {2'b0, q_slot};
            end else if (c == "C") begin
                case (i[6:2])
                    0: rbyte = cyc_s >> (8 * i[1:0]);
                    1: rbyte = o_done >> (8 * i[1:0]);
                    2: rbyte = o_lerr >> (8 * i[1:0]);
                    3: rbyte = o_disp >> (8 * i[1:0]);
                    4,5:   rbyte = o_busy    >> (8 * (i - 16));
                    6,7:   rbyte = o_blocked >> (8 * (i - 24));
                    8,9:   rbyte = o_tail    >> (8 * (i - 32));
                    10,11: rbyte = o_search  >> (8 * (i - 40));
                    default: rbyte = ({{(64-S){1'b0}}, o_busy_l}) >> (8 * (i - 48));
                endcase
            end else if (c == "L") begin
                rbyte = dsave >> (8 * i[1:0]);
            end else if (c == "Z") begin
                case (i[1:0])
                    0: rbyte = DSH[7:0]; 1: rbyte = DSH[15:8]; 2: rbyte = SHL; default: rbyte = $clog2(DSH);
                endcase
            end else begin                            // 'V'
                case (i)
                    0: rbyte = "S"; 1: rbyte = "C"; 2: rbyte = 8'd7; 3: rbyte = S;
                    4: rbyte = IMEM_WORDS[7:0]; 5: rbyte = IMEM_WORDS[15:8];
                    6: rbyte = DMW[7:0]; default: rbyte = DMW[15:8];
                endcase
            end
        end
    endfunction

    always @(posedge clk) begin
        h_push <= 1'b0; rg_we <= 1'b0; rs_we <= 1'b0; dh_we <= 1'b0; dh_rd <= 1'b0; imem_we <= 1'b0; tsend <= 1'b0;
        stx <= (tsend) ? 24'hFFFFFF : (stx != 0 ? stx - 1'b1 : 24'd0);
        srx <= (rv)    ? 24'hFFFFFF : (srx != 0 ? srx - 1'b1 : 24'd0);
        act_tx <= (stx != 0); act_rx <= (srx != 0);
        if (rstcnt != 0) begin rstcnt <= rstcnt - 1'b1; if (rstcnt == 1) soft_rst <= 1'b0; end
        case (st)
            IDLE: if (rv) begin
                cmd <= rb; got <= 0;
                case (rb)
                    "H": hold <= 1'b1;
                    "G": hold <= 1'b0;
                    "V": begin rlen <= 8;  ridx <= 0; st <= REPLY; end
                    "C": begin rlen <= 56; ridx <= 0; cyc_s <= o_cyc; st <= REPLY; end
                    "R": begin soft_rst <= 1'b1; rstcnt <= 8; end
                    "W": begin need <= 6; st <= ARGS; end
                    "P": begin need <= 7; st <= ARGS; end
                    "B": begin need <= 7; st <= ARGS; end
                    "M": begin need <= 6; st <= ARGS; end
                    "L": begin need <= 2; st <= ARGS; end
                    "X": begin need <= 5; st <= ARGS; end
                    "Z": begin rlen <= 4; ridx <= 0; st <= REPLY; end
                    "Q": begin need <= 2; st <= ARGS; end
                    default: ;
                endcase
            end
            ARGS: if (rv) begin
                a[got] <= rb; got <= got + 1'b1;
                if (got + 1'b1 == need) st <= EXEC;
            end
            EXEC: begin
                case (cmd)
                    "W": begin imem_we <= 1'b1; imem_wa <= {a[1], a[0]}; imem_wd <= {a[5], a[4], a[3], a[2]}; st <= IDLE; end
                    "P": begin h_push <= 1'b1; h_tid <= {a[1], a[0]}; h_code <= {a[3], a[2]}; h_lw <= a[4][2:0];
                               h_crit <= a[5][0]; h_prog <= a[6][5:0]; st <= IDLE; end
                    "B": begin rg_we <= 1'b1; rg_prog <= a[0][5:0]; rg_cbase <= {a[2], a[1]}; rg_clen <= {a[4], a[3]}; rg_dlen <= {a[6], a[5]}; st <= IDLE; end
                    "Q": begin q_tid <= {a[1], a[0]}; rlen <= 22; ridx <= 0; st <= REPLY; end
                    "M": if (!dh_busy) begin dh_we <= 1'b1; dh_a <= {a[1], a[0]}; dh_wd <= {a[5], a[4], a[3], a[2]}; st <= IDLE; end
                    "X": begin rs_we <= 1'b1; rs_prog <= a[0][5:0]; rs_base <= {a[2], a[1]}; rs_len <= {a[4], a[3]}; st <= IDLE; end
                    "L": if (!dh_busy) begin dh_rd <= 1'b1; dh_a <= {a[1], a[0]}; st <= WAITD; end
                    default: st <= IDLE;
                endcase
            end
            WAITD: if (dh_qv) begin dsave <= dh_q; rlen <= 4; ridx <= 0; st <= REPLY; end
            REPLY: if (!tbusy && !tsend) begin
                if (ridx == rlen) st <= IDLE;
                else begin tb <= rbyte(cmd, ridx); tsend <= 1'b1; ridx <= ridx + 1'b1; end
            end
        endcase
    end
    initial begin rs_we = 0; dh_we = 0; dh_rd = 0; dh_a = 0; dh_wd = 0; rs_prog = 0; rs_base = 0; rs_len = 0; rg_we = 0; hold = 0; h_push = 0; imem_we = 0; soft_rst = 0; q_tid = 0; end
endmodule
