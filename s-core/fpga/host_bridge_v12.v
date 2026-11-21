// host_bridge_v12.v - host_bridge_v11 with the status reading moved out (ledger #1457): the per-block replies of Q C T U E N A now come as ONE BYTE (rd_byte) from
//   blk_rd_v1 in the selected block (the byte function and the snapshots live there).  Outputs rd_cmd, rd_idx, rd_snap, rd_lat drive it; they are combinational from
//   the same registers v11 used, so reply bytes and their timing are as in v11.  Removed: the wide status inputs q_*, o_*, st_*, f_done/f_ign/f_err/f_moved/f_clocks, s_*.
//   Kept: dh_q dh_qv dh_busy, f_busy f_init, fh_acc fh_ackv fh_ackd.  Cloned from host_bridge_v11.v (left as proven).
// host_bridge_v11.v - host_bridge_v10 for SEVERAL BLOCKS (ledger #1347).  New: parameter NB (default 1) and the command
//   'O' blk(1)   select block blk (0..NB-1; a value >= NB is ignored).  Power-up: block 0.  Every command after it (P B X Y W M L F D J A N T U E C Q ...
//                and w / r / K) goes to, and every reply comes from, the selected block; R resets the selected block only.
// Hold is now kept per block (H / G act on the selected block; output hold_o), and D also pulses d_we so that each block can keep its own copy window.
// With NB = 1 and no 'O' command everything behaves as in v10.  Cloned from host_bridge_v10.v (left as proven).
// host_bridge_v10.v - host_bridge_v9 with the UART taken out: the bridge now talks to a byte link (jtag_link_v1.v) through rb_data/rb_valid (in) and
// tb_data/tb_send/tb_busy (out).  Commands and replies are unchanged.  Cloned from host_bridge_v9.v; v9 is untouched.  The clock-counter fields of A are in
// units of the system clock (27 MHz on the Tang, 50 MHz on the Kintex card).
// host_bridge_v9.v - host_bridge_v8 with a longer A reply (the V reply reports version 12): the sequencer's clock counters and its current step.
//   'A'  -> 24 bytes: flags(1: bit0 busy, bit1 done), err(1), steps executed(2), end tag(4), clocks total(4), clocks in copies(4), clocks waiting for jobs(4),
//           current step far address(3), current opcode(1).   Clocks are 27 MHz board clocks.   (v8 answered 8 bytes.)
// Cloned from host_bridge_v8.v (left as proven).
// host_bridge_v8.v - host_bridge_v7 plus the BATCH SEQUENCER commands (the V reply reports version 11).  The sequencer (batch_seq.v) runs a script held in far RAM.
//   'J' addr(3)    start the script whose first step is at far word addr.  Ignored while one is running.
//   'A'            -> 8 bytes: flags(1: bit0 busy, bit1 done), err(1: 0 ok, 1..5 copy engine, 6 wait timed out, 7 code change with jobs in flight, 8 bad opcode, 9 step limit),
//                     steps executed(2), end tag(4)
// While the sequencer runs, do not send P, B, X, Y, F, w or r (it owns them); poll A until done.
// Cloned from host_bridge_v7.v (left as proven).
// host_bridge_v7.v - host_bridge_v6 plus the FAR RAM commands (the V reply reports version 10).  Far RAM = the onboard 8 MB SDRAM (2M words of 32 bits,
// word address 0..0x1FFFFF).  The cores never see it; a copy engine (far_copy.v) moves blocks between it and the cores' RAM.
//   'F' dir(1) near(2) far(3) count(2)   start a copy of count words.  dir 0: shared RAM -> far, 1: far -> shared RAM, 2: far -> shared CODE store.
//                                        Refused (nothing moved, error code in N) if the far range is outside the allowed window or the near range is past the end.
//   'N'            -> 12 bytes: flags(1: bit0 busy, bit1 done, bit2 a start was ignored because one was running), err(1), init_done(1), 0(1), words_moved(4), clocks(4)
//                     err: 0 none, 1 far range outside the allowed window, 2 near range past the end, 3 far RAM not ready, 4 bad direction, 5 timeout
//   'D' base(3) len(3)   the window of far RAM that copies may touch: words [base, base+len).  Default after power-up: length 0 = nothing allowed.
//                        Not cleared by R (the far RAM and its window survive a core reset).
//   'w' addr(3) data(4)  write one far word directly      'r' addr(3) -> 4 bytes   (both refused while a copy runs; 'r' then answers 0xDEADBEEF)
//   'I' -> 4 bytes: init_done, cl, dly, inv       'K' cl dly inv   set the far RAM read settings and run its power-up again (default 2 1 0, proven on the card)
// While a copy runs, do not send M or L (they wait for the copy and the UART does not buffer); poll N until done.
// Cloned from host_bridge_v6.v (left as proven).
// host_bridge_v6.v - host_bridge_v5 plus three read-only commands (the V reply reports version 9):
//   'T'            -> 8+4*S bytes.  The header is a snapshot taken when the command arrives, the slice records are read as they are sent:
//                       qc(2) qb(2) busy_slices(1) leaders(1) hold(1) 0(1)       waiting critical tasks, waiting bulk tasks, slices allocated, tasks running, hold flag
//                       then per slice: flags(1) class(1) tid(2)                 flags bit0 allocated, bit1 leader of a running task; class/tid are 0xFF/0xFFFF when not a leader
//   'U'            -> 8+8*S bytes: cyc(4) 0(4) taken when the command arrives, then per slice 8 bytes: the number of clocks it was allocated to a task
//                       (40 bits, little-endian, the other 3 bytes 0).  Each 40-bit count is latched whole when its first byte is sent, so it cannot tear.
//   'E' tid(2)     -> 5 bytes: cause(1) addr(4).  cause 0 none, 1 code region, 2 private data limit, 3 shared window, 4 shared access with no window,
//                       5 other core trap.  addr = low 16 bits of the word index of the access (of the fetch word address for cause 1)
// Cloned from host_bridge_v5.v (left as proven).
// host_bridge_v5.v - host_bridge_v4 plus the Y (library window) command; the V reply reports version 8.
//   'Y' base(2) len(2)      code words [base, base+len) of the shared store may be executed by every program class (cleared by R)
// Cloned from host_bridge_v4.v (left as proven).
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
module host_bridge_v12 #(parameter NB = 1, parameter DIV = 234, parameter S = 8, parameter IMEM_WORDS = 256, parameter DMW = 64, parameter DSH = 256, parameter SHL = 14) (
    input  wire        clk,
    input  wire [7:0]  rb_data,           // byte link (jtag_link_v1) instead of the UART
    input  wire        rb_valid,
    output wire [7:0]  tb_data,
    output wire        tb_send,
    input  wire        tb_busy,
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
    output wire [NB-1:0] hold_o,
    output reg  [3:0]  blk,
    output reg         d_we,
    output reg         rg_we,
    output reg  [5:0]  rg_prog,
    output reg  [15:0] rg_cbase, rg_clen, rg_dlen,
    output reg         rs_we,
    output reg  [5:0]  rs_prog,
    output reg  [15:0] rs_base, rs_len,
    output reg         lb_we,
    output reg  [15:0] lb_base, lb_len,
    output reg         dh_we, dh_rd,
    output reg  [15:0] dh_a,
    output reg  [31:0] dh_wd,
    input  wire [31:0] dh_q,
    input  wire        dh_qv,
    input  wire        dh_busy,
    // v7: far RAM
    output reg         f_start,
    output reg  [1:0]  f_dir,
    output reg  [15:0] f_near,
    output reg  [20:0] f_far,
    output reg  [15:0] f_cnt,
    output reg  [20:0] f_lbase,
    output reg  [21:0] f_llen,
    input  wire        f_busy, f_init,
    output wire [1:0]  f_cl, f_dly,
    output wire        f_inv,
    // v8: batch sequencer
    output reg         s_start,
    output reg  [20:0] s_addr,
    output reg         f_reinit,
    output reg         fh_v, fh_we,
    output reg  [20:0] fh_a,
    output reg  [31:0] fh_wd,
    input  wire        fh_acc, fh_ackv,
    input  wire [31:0] fh_ackd,
    output reg         act_rx, act_tx,
    // v12: the per-block status reader (blk_rd_v1)
    input  wire [7:0]  rd_byte,
    output wire [7:0]  rd_cmd,
    output wire [9:0]  rd_idx,
    output wire        rd_snap,
    output wire        rd_lat
);
    wire [7:0] rb = rb_data; wire rv = rb_valid;
    reg  [7:0] tb = 0; reg tsend = 0; wire tbusy = tb_busy;
    assign tb_data = tb; assign tb_send = tsend;

    localparam IDLE = 0, ARGS = 1, EXEC = 2, REPLY = 3, WAITD = 4, FACC = 5, FACK = 6;
    reg [2:0]  st = IDLE;
    reg [31:0] dsave = 0;
    reg [7:0]  cmd = 0;
    reg [3:0]  need = 0, got = 0;
    reg [7:0]  a [0:15];
    reg [31:0] fsave = 0;
    // The far RAM settings are stored XOR their defaults (2, 1, 0): a register that powers up as zero then means the defaults.  (Non-zero initial values
    // are not applied on the real chip - found on the card 2026-11-16, the settings came up 0/0/0.)
    reg [1:0]  cfg_cl_x = 0, cfg_dly_x = 0; reg cfg_inv_x = 0;
    assign f_cl = cfg_cl_x ^ 2'd2; assign f_dly = cfg_dly_x ^ 2'd1; assign f_inv = cfg_inv_x;
    reg [9:0]  rlen = 0, ridx = 0;
    reg [NB-1:0] hold_v = 0;
    assign hold_o = hold_v;
    wire hold = hold_v[blk];
    reg [3:0]  rstcnt = 0;
    reg [23:0] stx = 0, srx = 0;

    function [7:0] rbyte(input [7:0] c, input [9:0] i);
        reg [63:0] w;
        begin
            w = 64'd0;
            if (c == "L") begin
                rbyte = dsave >> (8 * i[1:0]);
            end else if (c == "r") begin
                rbyte = fsave >> (8 * i[1:0]);
            end else if (c == "I") begin
                case (i[1:0]) 0: rbyte = {7'd0, f_init}; 1: rbyte = {6'd0, f_cl}; 2: rbyte = {6'd0, f_dly}; default: rbyte = {7'd0, f_inv}; endcase
            end else if (c == "Z") begin
                case (i[1:0])
                    0: rbyte = DSH[7:0]; 1: rbyte = DSH[15:8]; 2: rbyte = SHL; default: rbyte = $clog2(DSH);
                endcase
            end else begin                            // 'V'
                case (i)
                    0: rbyte = "S"; 1: rbyte = "C"; 2: rbyte = 8'd12; 3: rbyte = S;
                    4: rbyte = IMEM_WORDS[7:0]; 5: rbyte = IMEM_WORDS[15:8];
                    6: rbyte = DMW[7:0]; default: rbyte = DMW[15:8];
                endcase
            end
        end
    endfunction

    // v12: which commands are answered by the block's reader, and the strobes that drive it (combinational, from the registers v11 used)
    wire rd_cls = (cmd == "Q") || (cmd == "C") || (cmd == "T") || (cmd == "U") || (cmd == "E") || (cmd == "N") || (cmd == "A");
    assign rd_cmd  = cmd;
    assign rd_idx  = ridx;
    assign rd_snap = (st == IDLE) && rv && (rb == "C" || rb == "U" || rb == "T");
    assign rd_lat  = (st == REPLY) && !tbusy && !tsend && (ridx != rlen) && (cmd == "U") && (ridx >= 8) && (ridx[2:0] == 0);

    always @(posedge clk) begin
        h_push <= 1'b0; rg_we <= 1'b0; rs_we <= 1'b0; lb_we <= 1'b0; dh_we <= 1'b0; dh_rd <= 1'b0; imem_we <= 1'b0; tsend <= 1'b0; f_start <= 1'b0; f_reinit <= 1'b0; s_start <= 1'b0; d_we <= 1'b0;
        stx <= (tsend) ? 24'hFFFFFF : (stx != 0 ? stx - 1'b1 : 24'd0);
        srx <= (rv)    ? 24'hFFFFFF : (srx != 0 ? srx - 1'b1 : 24'd0);
        act_tx <= (stx != 0); act_rx <= (srx != 0);
        if (rstcnt != 0) begin rstcnt <= rstcnt - 1'b1; if (rstcnt == 1) soft_rst <= 1'b0; end
        case (st)
            IDLE: if (rv) begin
                cmd <= rb; got <= 0;
                case (rb)
                    "H": hold_v[blk] <= 1'b1;
                    "G": hold_v[blk] <= 1'b0;
                    "V": begin rlen <= 8;  ridx <= 0; st <= REPLY; end
                    "C": begin rlen <= 56; ridx <= 0; st <= REPLY; end
                    "R": begin soft_rst <= 1'b1; rstcnt <= 8; end
                    "W": begin need <= 6; st <= ARGS; end
                    "P": begin need <= 7; st <= ARGS; end
                    "B": begin need <= 7; st <= ARGS; end
                    "M": begin need <= 6; st <= ARGS; end
                    "L": begin need <= 2; st <= ARGS; end
                    "X": begin need <= 5; st <= ARGS; end
                    "Z": begin rlen <= 4; ridx <= 0; st <= REPLY; end
                    "T": begin rlen <= 8 + 4*S; ridx <= 0; st <= REPLY; end
                    "U": begin rlen <= 8 + 8*S; ridx <= 0; st <= REPLY; end
                    "E": begin need <= 2; st <= ARGS; end
                    "Y": begin need <= 4; st <= ARGS; end
                    "Q": begin need <= 2; st <= ARGS; end
                    "F": begin need <= 8; st <= ARGS; end
                    "D": begin need <= 6; st <= ARGS; end
                    "w": begin need <= 7; st <= ARGS; end
                    "r": begin need <= 3; st <= ARGS; end
                    "K": begin need <= 3; st <= ARGS; end
                    "A": begin rlen <= 24;  ridx <= 0; st <= REPLY; end
                    "J": begin need <= 3; st <= ARGS; end
                    "O": begin need <= 1; st <= ARGS; end
                    "N": begin rlen <= 12; ridx <= 0; st <= REPLY; end
                    "I": begin rlen <= 4;  ridx <= 0; st <= REPLY; end
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
                    "E": begin q_tid <= {a[1], a[0]}; rlen <= 5; ridx <= 0; st <= REPLY; end
                    "M": if (!dh_busy) begin dh_we <= 1'b1; dh_a <= {a[1], a[0]}; dh_wd <= {a[5], a[4], a[3], a[2]}; st <= IDLE; end
                    "Y": begin lb_we <= 1'b1; lb_base <= {a[1], a[0]}; lb_len <= {a[3], a[2]}; st <= IDLE; end
                    "X": begin rs_we <= 1'b1; rs_prog <= a[0][5:0]; rs_base <= {a[2], a[1]}; rs_len <= {a[4], a[3]}; st <= IDLE; end
                    "L": if (!dh_busy) begin dh_rd <= 1'b1; dh_a <= {a[1], a[0]}; st <= WAITD; end
                    "F": begin f_start <= 1'b1; f_dir <= a[0][1:0]; f_near <= {a[2], a[1]}; f_far <= {a[5][4:0], a[4], a[3]}; f_cnt <= {a[7], a[6]}; st <= IDLE; end
                    "J": begin s_start <= 1'b1; s_addr <= {a[2][4:0], a[1], a[0]}; st <= IDLE; end
                    "O": begin if (a[0] < NB) blk <= a[0][3:0]; st <= IDLE; end
                    "D": begin d_we <= 1'b1; f_lbase <= {a[2][4:0], a[1], a[0]}; f_llen <= {a[5][5:0], a[4], a[3]}; st <= IDLE; end
                    "K": begin cfg_cl_x <= a[0][1:0] ^ 2'd2; cfg_dly_x <= a[1][1:0] ^ 2'd1; cfg_inv_x <= a[2][0]; f_reinit <= 1'b1; st <= IDLE; end
                    "w": if (f_busy || !f_init) st <= IDLE; else begin fh_v <= 1'b1; fh_we <= 1'b1; fh_a <= {a[2][4:0], a[1], a[0]}; fh_wd <= {a[6], a[5], a[4], a[3]}; st <= FACC; end
                    "r": if (f_busy || !f_init) begin fsave <= 32'hDEADBEEF; rlen <= 4; ridx <= 0; st <= REPLY; end
                         else begin fh_v <= 1'b1; fh_we <= 1'b0; fh_a <= {a[2][4:0], a[1], a[0]}; st <= FACC; end
                    default: st <= IDLE;
                endcase
            end
            FACC: if (fh_acc) begin fh_v <= 1'b0; st <= FACK; end
            FACK: if (fh_ackv) begin
                if (cmd == "r") begin fsave <= fh_ackd; rlen <= 4; ridx <= 0; st <= REPLY; end else st <= IDLE;
            end
            WAITD: if (dh_qv) begin dsave <= dh_q; rlen <= 4; ridx <= 0; st <= REPLY; end
            REPLY: if (!tbusy && !tsend) begin
                if (ridx == rlen) st <= IDLE;
                else begin
                    tb <= rd_cls ? rd_byte : rbyte(cmd, ridx); tsend <= 1'b1; ridx <= ridx + 1'b1;
                end
            end
        endcase
    end
    initial begin s_start = 0; s_addr = 0; f_start = 0; f_dir = 0; f_near = 0; f_far = 0; f_cnt = 0; f_lbase = 0; f_llen = 0; f_reinit = 0; fh_v = 0; fh_we = 0; fh_a = 0; fh_wd = 0; lb_we = 0; lb_base = 0; lb_len = 0; rs_we = 0; dh_we = 0; dh_rd = 0; dh_a = 0; dh_wd = 0; rs_prog = 0; rs_base = 0; rs_len = 0; rg_we = 0; d_we = 0; blk = 0; h_push = 0; imem_we = 0; soft_rst = 0; q_tid = 0; end
endmodule
