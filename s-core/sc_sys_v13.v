// sc_sys_v13.v - sc_sys_v12 with the watcher split into three clocks (see the comment at the watcher).  Nothing else changed: same ports, same
// scheduling and checks, same host commands.  Why: on the Kintex card the clock limit at S=16 (50.52 MHz) is one path in the dispatcher: request table ->
// watcher -> task-start table -> adders -> profile table, all in one clock (ledger #1340).  The only difference the host can see is timing: a
// finished slice is reported and freed 2 clocks later than in v12, so clock counts of whole runs move by a few clocks per task.
// Cloned from sc_sys_v12.v (which stays as proven).
//
// sc_sys_v11.v - sc_sys_v10 plus a shared code LIBRARY window.  One window of the shared code store ([lb_base, lb_base+lb_len), host
// command Y) may be executed by every program class, in addition to the class's own code window.  Library code runs under the CALLER's
// limits (its private data limit and its shared-data window), so a library function can only touch what the calling task may touch.
// Calls are ordinary jal / jalr; the stack lives in the caller's data (private memory or its shared window).  See sclink.py.
// Cloned from sc_sys_v10.v (left as proven).
//
// sc_sys_v10.v - sc_sys_v9 plus a SHARED DATA RAM and per-class windows into it.
// Data word indices below 2^SHL are the slice's private memory exactly as in v9 (limit check unchanged).  Word indices from 2^SHL up
// (byte address 4*2^SHL = 0x10000 with SHL=14) are the SHARED window: shared word s = index - 2^SHL.  Per program class the host sets
// {base, length} (command X): s must be < length, and the physical word is base + s of one DSH-word RAM that every slice can reach.
// Classes whose windows overlap share data; disjoint windows are private.  A class with no X entry has length 0 = no shared access
// (any access to the window traps).  Violations abort the core as a trap, exactly like the v9 region checks.
// The shared RAM is ONE single-port 32-bit-wide block RAM.  A slot counter gives each slice one clock in S: in its slot a slice
// either writes its finished store word (the write accumulator is held until then) or reads the word a LOAD needs into a per-slice
// word register (the core is stalled with ce until it is there; about S/2 clocks on average).  The host (commands M, L) takes the port
// whenever it asks; a slice whose clock it took simply tries again in its next slot.  Cloned from sc_sys_v9.v (v9 left as proven);
// core = uc_core_v2v.
//
// sc_sys_v9.v - sc_sys_v8 plus REGIONS (base / limit checks).  Per program class the host can set a code region (base, length in
// words of the shared code store) and a data limit (words of the slice's private data memory).  At task start the slice latches them;
//   - every instruction fetch outside [code base, code end) (or outside the store) aborts the core as a trap,
//   - every load/store word index >= the data limit aborts the core as a trap (the store is blocked),
// so a runaway jump or a wild pointer ends the task with the trap flag set instead of aliasing into other code or data.
// A class with no entry gets the whole store and all physical data words, i.e. exactly v8.  Entries are cleared by reset (R).
// The write counters are cleared at task start, so a task aborted mid-pass cannot corrupt the next task on that slice.
// Cloned from sc_sys_v8.v (v8 left as proven); core = uc_core_v2u.
//
// sc_sys_v8.v - sc_sys_v7 with ONE shared code store instead of a private copy of the code in every slice.
// Each slice keeps a 32-bit fetch register; a slot counter lets the slices load it from the shared memory in turn
// (one clock per slot, no arbitration). The next sequential instruction is fetched ahead, so only a branch or jump
// waits (at most S clocks). The core is stalled with its own ce input; core = uc_core_v2t (v2s + `fetching` output).
// Cloned from sc_sys_v7.v; v7 is left as proven.
//
// sc_sys_v7.v - sc_sys_v6 plus a HOLD input.  While hold = 1 the host can submit tasks (they are queued, arrival time stamped)
// but the dispatcher starts none; when hold falls the dispatcher wakes and places the whole queue in its normal order.
// Everything else is v6 unchanged.  Cloned from sc_sys_v6.v; v6 is left as proven.
//
// sc_sys_v6.v - sc_sys_v5 (pool of fixed 1-bit cores) with the register file and data memory in 32-bit-WIDE block RAM.
// BOARD FINDING (2026-11-14, Tang Nano 20K, fpga/bram_char_top.v): single-port block RAM of width 1, 4, 9, 16 and 18
// returns wrong data on silicon (the plain write-all/read-all test fails with no core involved) while the 32-bit-wide
// shape passes every test.  So here every memory is one 32-bit word per entry:
//   read : the whole word is read every step (clock 0 of the step) and bit k is picked by a 32:1 multiplexer
//   write: the 32 result bits of an instruction are collected in a 32-bit accumulator as they arrive; the 32nd write
//          of a pass stores the finished word (clock 1 of the step), so the core sees exactly the v5 behaviour
//          (every register write is one full 32-bit pass; reads inside the pass see the old word, as before).
// Scheduler, core and durations are unchanged from v5.
// sc_sys_v5.v - the v4 scheduler with a POOL of fixed 1-bit cores (uc_core_v2s, W=1) instead of the masked 32-bit
// runtime-width model.  Every task runs at 1 bit per cycle whatever its lw (h_lw should be 0: no fusion in this version).
// Memories are plain 1-bit RAMs (register file 1024 x 1 per read port, data memory DMW*32 x 1).  Scheduler unchanged.
// sc_sys_v4.v - FPGA build of sc_sys_v3 (same scheduler; memories, core and host port changed).
//   - cores are uc_core_fp, stepped every second clock (ce); all RAM reads are synchronous
//   - register file and data memory are bit-packed 32-bit words built from 1-bit lanes (a 1 Kbit
//     register file per slice instead of 1024 x 32); DMW = data words per slice
//   - instruction memory is a private copy per slice (IMEM_WORDS words), written through one broadcast port
//   - host ports: imem write, task-table read (q_*), counters (o_*); event payload table is EVP entries
//   One core step = 2 clocks, so every duration (start/end/profile) is counted in clocks.
//
// (below: the v3 header, still accurate for the scheduler)
// sc_sys_v3.v - S-Core array v3: request table + watcher, task table, priority dispatcher
//
//  producers                      tables                          units
//  ---------                      ------                          -----
//  core finished  --set-->  [16x16 REQUEST TABLE] --scan--> WATCHER (specialist)
//  peripheral line --set-->        (set-only by                 - clears the flag
//  (payload written first)          producers,                  - core-done: frees the slices,
//                                   clear-only by watcher)        stamps the task's end time/result
//                                                               - peripheral: logs {line, payload,
//                                                                 cycle} to the event queue
//  host --push--> [TASK TABLE]  (arrival, start, end, a0, state, width, class)
//             \-> [critical queue] / [bulk queue]  (task ids)
//                                  |
//                                  v
//                            DISPATCHER  reads: queues + idle table (slice_busy)
//                                        writes: start time, SETS busy bits, pulses start
//                            (sleeps until a push or a freed core wakes it: no per-cycle polling)
//
// Rules kept from the earlier design: no interrupts, no preemption, a task runs to EBREAK.
// Request-table line numbers: 0..63 = "core with leader slice n has finished"; 64..255 = peripheral
// lines.  A peripheral must write its payload BEFORE raising its line and must not reuse the line
// until the watcher has logged it (one outstanding event per line).
//
// Parameters
//   PRIO    1: critical tasks are queued separately and served first; 0: one FIFO (class ignored)
//   BESTFIT 1: place a task in the smallest free aligned block that holds it (keeps big blocks
//              free for wide tasks); 0: lowest-address first fit
//   GUARD   after this many critical launches in a row a waiting bulk task gets a forced turn
//   MAXPASS after this many bulk launches over a blocked critical head, bulk is held back

// sc_sys_v12.v - sc_sys_v11 plus read-out for the host (no change to how tasks are scheduled or checked):
//   - status snapshot ports: per-slice {task id, class, leader, busy}, critical / bulk queue length
//   - per-slice busy counters (40 bits, clocks the slice was allocated to a task)
//   - trap cause and address per task: 1 code region, 2 private data limit, 3 shared window, 4 shared access with no window,
//     5 other core trap (not from the region checks); the address is the word index (fetch address for code)
// Cloned from sc_sys_v11.v (left as proven).
module sc_sys_v13 #(
    parameter S          = 32,
    parameter QD         = 256,
    parameter IMEM_WORDS = 8192,
    parameter PRIO       = 1,
    parameter BESTFIT    = 1,
    parameter GUARD      = 8,
    parameter MAXPASS    = 8,
    parameter LONGEST    = 0,     // 1: bulk queue is 8 duration buckets, longest predicted first
    parameter FINE       = 0,     // 1: 15 half-octave duration buckets (+unknown) instead of 7 whole-octave ones
    parameter PROF       = 512,   // duration-profile store: 64 program classes x 8 widths
    parameter DMW        = 1024,  // data words (32-bit) per slice, power of 2
    parameter DSH        = 256,   // v10: words (32-bit) of the SHARED data RAM, power of 2 (>= 32); one block RAM
    parameter SHL        = 14,    // v10: the shared window starts at data word index 2^SHL (byte address 4*2^SHL); 2^SHL >= DSH
    parameter EVB        = 8      // event payload index bits (lines 64.. use ev_pl[id mod 2^EVB])
) (
    input  wire        clk,
    input  wire        rst,
    // v9: region table, one entry per program class (h_prog).  Set by the host while the array is idle; cleared by reset.
    input  wire        rg_we,
    input  wire [5:0]  rg_prog,
    input  wire [15:0] rg_cbase, rg_clen,      // code region: first word address and length in words (shared code store)
    input  wire [15:0] rg_dlen,                // data region: words the task may touch (its private data memory starts at word 0)
    // v11: shared code LIBRARY window: code words [lb_base, lb_base+lb_len) that every program class may execute (in addition to its own window)
    input  wire        lb_we,
    input  wire [15:0] lb_base, lb_len,
    // v10: shared-data region table, one entry per program class: window [rs_base, rs_base+rs_len) of the shared data RAM
    input  wire        rs_we,
    input  wire [5:0]  rs_prog,
    input  wire [15:0] rs_base, rs_len,
    // v10: host access to the shared data RAM (one word per request; a slice's access in the same clock is retried)
    input  wire        dh_we,
    input  wire        dh_rd,
    input  wire [15:0] dh_a,
    input  wire [31:0] dh_wd,
    output reg  [31:0] dh_q,
    output reg         dh_qv,
    output wire        dh_busy,       // a host request is waiting for a free RAM clock: do not send the next one yet
    input  wire        hold,          // v7: 1 = accept and queue tasks but start none; the falling edge wakes the dispatcher
    // host submit port
    input  wire        h_push,
    input  wire [15:0] h_tid,
    input  wire [15:0] h_code,
    input  wire [2:0]  h_lw,
    input  wire        h_crit,
    // host: instruction memory write (broadcast to every slice's private copy)
    input  wire        imem_we,
    input  wire [15:0] imem_wa,
    input  wire [31:0] imem_wd,
    // host: task-table read (combinational on q_tid)
    input  wire [15:0] q_tid,
    output wire [31:0] q_start, q_end, q_a0, q_arr,
    output wire        q_trap,
    output wire [1:0]  q_state,
    output wire [5:0]  q_slot,
    output wire [24:0] q_pred,
    // host: counters
    output wire [31:0] o_cyc, o_done, o_lerr, o_disp,
    output wire [63:0] o_busy, o_blocked, o_tail, o_search,
    output wire [S-1:0] o_busy_l,
    output reg  [32*S-1:0] st_sl,          // per slice: {task id(16), class(8), flags(8)}; flags bit0 = slice allocated, bit1 = leader of a running task
    output reg  [15:0] st_qc, st_qb,       // tasks waiting: critical queue, bulk queues
    output wire [40*S-1:0] st_bs,          // per slice: clocks allocated to a task
    output wire [2:0]  q_cause,            // trap cause of the task read through q_tid
    output wire [15:0] q_taddr,
    // peripheral request lines
    input  wire        ev_pl_we,
    input  wire [5:0]  h_prog,        // program-class id given by the submitter (profile key)
    input  wire [7:0]  ev_pl_id,
    input  wire [31:0] ev_pl_data,
    input  wire        ev_set,
    input  wire [7:0]  ev_set_id
);
    localparam IAW = $clog2(IMEM_WORDS);
    localparam DAW = $clog2(DMW);
    localparam SW  = (S > 1) ? $clog2(S) : 1;
    localparam DMD_G = (DMW < 32) ? 32 : DMW;       // physical data words per slice (the block-RAM shape needs at least 32)
    localparam DWA_G = $clog2(DMD_G);
    localparam DWS   = $clog2(DSH);                  // v10: shared data RAM address bits
    initial if (SHL < DWS + 2) $display("sc_sys_v10: SHL must be at least log2(DSH)+2");

    // ------------------------------------------------------------ shared-data region table (v10)
    reg [DWS-1:0] rs_sb [0:63];
    reg [DWS:0]   rs_sl [0:63];
    reg [63:0]    rs_v;
    wire [16:0]   rs_bc   = (rs_base >= DSH) ? DSH : {1'b0, rs_base};
    wire [16:0]   rs_room = DSH - rs_bc;
    always @(posedge clk) begin
        if (rst) rs_v <= 64'd0;
        else if (rs_we) begin
            rs_sb[rs_prog] <= rs_bc[DWS-1:0];
            rs_sl[rs_prog] <= (rs_len > rs_room) ? rs_room[DWS:0] : rs_len[DWS:0];
            rs_v[rs_prog]  <= 1'b1;
        end
    end
    reg [DWS-1:0] launch_sb;
    reg [DWS:0]   launch_sl;

    // ------------------------------------------------------------ region table (v9)
    // A task's program class (h_prog) selects {code base, code end, data limit}.  A class with no entry gets the whole
    // code store and the whole physical data memory (= v8 behaviour).  The host sets entries while the array is idle.
    reg [IAW-1:0] rg_cb [0:63];
    reg [IAW:0]   rg_ce [0:63];
    reg [DWA_G:0] rg_dl [0:63];
    // v11: the library window (global; set by the host while the array is idle; cleared by reset = no library)
    reg           lb_v;
    reg [IAW-1:0] lb_b;
    reg [IAW:0]   lb_e;
    wire [16:0]   lb_sum = {1'b0, lb_base} + {1'b0, lb_len};
    always @(posedge clk) begin
        if (rst) lb_v <= 1'b0;
        else if (lb_we) begin
            lb_b <= lb_base[IAW-1:0];
            lb_e <= (lb_sum > IMEM_WORDS) ? IMEM_WORDS : lb_sum[IAW:0];
            lb_v <= (lb_base < IMEM_WORDS) && (lb_len != 0);
        end
    end
    reg [63:0]    rg_v;
    wire [16:0]   rg_sum = {1'b0, rg_cbase} + {1'b0, rg_clen};
    always @(posedge clk) begin
        if (rst) rg_v <= 64'd0;
        else if (rg_we) begin
            rg_cb[rg_prog] <= rg_cbase[IAW-1:0];
            rg_ce[rg_prog] <= (rg_sum > IMEM_WORDS) ? IMEM_WORDS : rg_sum[IAW:0];
            rg_dl[rg_prog] <= (rg_dlen > DMD_G) ? DMD_G : rg_dlen[DWA_G:0];
            rg_v[rg_prog]  <= 1'b1;
        end
    end

    // ------------------------------------------------------------ SHARED code store (v8)
    // One copy of the code for all slices (v7 had one per slice).  Asynchronous read, so a slot is one clock:
    // a free-running slot counter gives slice 0, 1, ... S-1 in turn the right to load its fetch register `fw` with
    // the word at its target address.  No arbitration: a slice waits at most S-1 clocks for its turn.
    (* ram_style = "distributed" *) reg [31:0] imem_sh [0:IMEM_WORDS-1];
`ifndef SYNTHESIS
    integer q_;
    initial for (q_ = 0; q_ < IMEM_WORDS; q_ = q_ + 1) imem_sh[q_] = 32'h0;   // simulation only: the host loads the code
`endif
    always @(posedge clk) if (imem_we) imem_sh[imem_wa[IAW-1:0]] <= imem_wd;
    reg  [SW-1:0]    slot_cnt;
    always @(posedge clk) slot_cnt <= (rst || slot_cnt == S - 1) ? {SW{1'b0}} : slot_cnt + 1'b1;
    wire [S*IAW-1:0] tgt_all;
    wire [IAW-1:0]   sh_a = tgt_all[slot_cnt*IAW +: IAW];
    wire [31:0]      sh_q = imem_sh[sh_a];

    // ------------------------------------------------------------ SHARED data RAM (v10)
    // One block RAM, one access per clock.  Slice requests are served in the slice's slot; the host goes first.
    (* ram_style = "block" *) reg [31:0] shd [0:DSH-1];
`ifndef SYNTHESIS
    integer sz_;
    initial for (sz_ = 0; sz_ < DSH; sz_ = sz_ + 1) shd[sz_] = 32'h0;
`endif
    // Every slice presents ONE registered request (rq): valid, write/read, physical address.  In a slice's slot its request is served.
    // The host never takes a clock a slice wants: its request waits (dh_busy) for a slot whose owner has no request.
    wire [S*DWS-1:0] rqa_all;
    wire [S*32-1:0]  pdat_all;
    wire [S-1:0]     rqv_all, rqw_all;
    reg              hp_v, hp_we;                              // host request waiting
    reg  [DWS-1:0]   hp_a;
    reg  [31:0]      hp_wd;
    wire             sl_rq    = rqv_all[slot_cnt];
    wire             host_use = hp_v & ~sl_rq;                 // this clock goes to the host
    always @(posedge clk) begin
        if (rst) hp_v <= 1'b0;
        else if ((dh_we | dh_rd) && !hp_v) begin hp_v <= 1'b1; hp_we <= dh_we; hp_a <= dh_a[DWS-1:0]; hp_wd <= dh_wd; end
        else if (host_use) hp_v <= 1'b0;
    end
    assign dh_busy = hp_v;
    wire             gnt      = ~host_use;                     // 1: this clock belongs to the slice in its slot
    wire [DWS-1:0]   sl_adr   = rqa_all[slot_cnt*DWS +: DWS];
    wire             sl_w     = rqw_all[slot_cnt];
    wire [31:0]      sl_wd    = pdat_all[slot_cnt*32 +: 32];
    wire [DWS-1:0]   p_adr    = host_use ? hp_a  : sl_adr;
    wire             p_we     = host_use ? hp_we : (sl_rq & sl_w);
    wire [31:0]      p_wd     = host_use ? hp_wd : sl_wd;
    wire             p_rd     = host_use ? ~hp_we : (sl_rq & ~sl_w);
    // block-RAM inputs re-registered on the falling edge (same hold-time measure as the register files)
    reg  [DWS-1:0]   p_adr_n;
    reg              p_we_n;
    reg  [31:0]      p_wd_n;
    always @(negedge clk) begin p_adr_n <= p_adr; p_we_n <= p_we; p_wd_n <= p_wd; end
    reg  [31:0]      sdq;
    reg              rd_gv, rd_gh;                            // a read was issued last clock; 1 = by the host
    reg  [SW-1:0]    rd_gid;                                  // ... for this slice
    always @(posedge clk) begin
        if (p_we_n) shd[p_adr_n] <= p_wd_n;
        sdq    <= shd[p_adr_n];
        rd_gv  <= p_rd & ~rst;
        rd_gh  <= host_use;
        rd_gid <= slot_cnt;
        dh_qv  <= rd_gv & rd_gh;
        if (rd_gv & rd_gh) dh_q <= sdq;
    end
    initial begin hp_v = 0; hp_we = 0; hp_a = 0; hp_wd = 0; rd_gv = 0; rd_gh = 0; rd_gid = 0; dh_qv = 0; dh_q = 0; sdq = 0; end

    // ------------------------------------------------------------ task table (index = task id)
    reg [15:0] t_code  [0:QD-1];
    reg [2:0]  t_lw    [0:QD-1];
    reg        t_crit  [0:QD-1];
    reg [31:0] t_arr   [0:QD-1];
    reg [31:0] t_start [0:QD-1];
    reg [31:0] t_end   [0:QD-1];
    reg [31:0] t_a0    [0:QD-1];
    reg        t_trap  [0:QD-1];
    reg [1:0]  t_state [0:QD-1];       // 0 empty, 1 waiting, 2 running, 3 done
    reg [5:0]  t_slot  [0:QD-1];       // leader slice the task ran on
    reg [5:0]  t_prog  [0:QD-1];
    reg [2:0]  t_cause [0:QD-1];
    reg [15:0] t_taddr [0:QD-1];
    reg [24:0] t_pred  [0:QD-1];       // {known, predicted duration} captured at submit
    reg [31:0] done_count;

    // ------------------------------------------------------------ queues (task ids)
    reg [15:0] qc [0:QD-1];
    // bulk class = NB duration buckets, each its own FIFO of task ids (bucket 0 only when LONGEST=0)
    localparam NB = FINE ? 16 : 8;
    reg [15:0] qk [0:NB*QD-1];
    reg [31:0] kwr [0:NB-1];
    reg [31:0] krd [0:NB-1];
    reg [31:0] qc_wr, qc_rd;

    // ------------------------------------------------------------ duration-profile store (dedicated RAM)
    // key = {program class, width}; value = {known, running average of measured durations (cycles)}
    reg [24:0] prof [0:PROF-1];
    integer pz;
    initial for (pz = 0; pz < PROF; pz = pz + 1) prof[pz] = 25'd0;   // power-up value; a reset keeps the profile
    function [8:0] pkey(input [5:0] prog, input [2:0] lw);
        pkey = {prog, lw} % PROF;      // PROF=64 on the FPGA: program classes 0..7 only
    endfunction
    // bucket from predicted duration: unknown -> 7 (run first, to learn), else clamp(log2(d)-8, 0, 6)
    function [3:0] bucket_of(input [24:0] p);
        reg [23:0] d; integer k; reg [4:0] lg; reg [5:0] ix;      // lg is 5 bits: it was 4 and wrapped for durations >= 65536 (fixed with FINE)
        begin
            d = p[23:0]; lg = 0;
            for (k = 0; k < 24; k = k + 1) if (d[k]) lg = k;
            if (FINE) begin   // half-octave steps: bucket = 2*(log2(d)-8) + next lower bit, 0..14; unknown -> 15
                if (!p[24])        bucket_of = 4'd15;
                else if (lg < 8)   bucket_of = 4'd0;
                else begin ix = 2 * (lg - 8) + d[lg - 1]; bucket_of = (ix > 14) ? 4'd14 : ix[3:0]; end
            end else begin    // whole-octave steps, 0..6; unknown -> 7
                if (!p[24])        bucket_of = 4'd7;
                else if (lg < 8)   bucket_of = 4'd0;
                else if (lg > 14)  bucket_of = 4'd6;
                else               bucket_of = lg - 8;
            end
        end
    endfunction

    // ------------------------------------------------------------ request table, payloads, event log
    reg [255:0] req_tab;
    reg [31:0]  ev_pl   [0:(1<<EVB)-1];
    reg [7:0]   ev_id   [0:QD-1];
    reg [31:0]  ev_data [0:QD-1];
    reg [31:0]  ev_cyc  [0:QD-1];
    reg [31:0]  ev_cnt;

    // ------------------------------------------------------------ cores
    reg  [S-1:0]    start_v, halted_q, fin_sent;
    wire [S-1:0]    pend_v;
    reg             cph;               // core clock-enable phase: cores step when 1
    wire [S-1:0]    halted_v, trap_v;
    wire [3*S-1:0]  tcause_v;
    wire [16*S-1:0] taddr_v;
    wire [32*S-1:0] a0_v;
    reg  [31:0]     launch_entry;
    reg  [IAW-1:0]  launch_cb;           // v9: code region of the task being launched
    reg  [IAW:0]    launch_ce;
    reg  [DWA_G:0]  launch_dl;
    reg  [2:0]      launch_lw;

    genvar gi;
    generate for (gi = 0; gi < S; gi = gi + 1) begin : slot
        wire        h, t;
        wire [29:0] ia;
        wire [31:0] id;
        wire [9:0]  ra, rb, rwa;
        wire        rad, rbd, rwd;
        wire        rwe;
        wire [34:0] da;
        wire        dwe;
        wire        dwd, drd;

        // ---- instruction fetch register (v8): the word for this slice, loaded from the shared store in its slot.
        //      While the core is in FETCH it needs the word at its pc; at all other times (when running) the word for the
        //      NEXT instruction (cur_a + 1) is fetched ahead, so a straight-line fetch finds it already here and does not
        //      wait.  A branch/jump (different address) makes the core wait, at most S clocks, for its slot.
        wire          fetching;
        wire [IAW-1:0] ia_l = ia[IAW-1:0];
        // ---- region checks (v9): latched at task start; a violation aborts the core as a trap
        reg  [IAW-1:0] cb_q;
        reg  [IAW:0]   ce_q;
        reg  [DWA_G:0] dl_q;
        reg  [DWS-1:0] sb_q;                         // v10: shared window of this task: base and length
        reg  [DWS:0]   sl_q;
        wire           dact, dldr;
        wire           own_bad = (ia[IAW-1:0] < cb_q) || ({1'b0, ia[IAW-1:0]} >= ce_q);
        wire           lib_bad = !lb_v || (ia[IAW-1:0] < lb_b) || ({1'b0, ia[IAW-1:0]} >= lb_e);   // v11: a fetch is also fine inside the library window
        wire           cviol = fetching && ((ia[29:IAW] != 0) || (own_bad && lib_bad));
        wire           sh_sel  = da[5+SHL];                                   // v10: the access is in the shared window
        wire           p_viol  = (|da[34:6+DWA_G]) || (da[5+DWA_G:5] >= dl_q);
        wire           s_viol  = (|da[34:6+SHL]) || (|da[5+SHL-1:6+DWS]) || (da[5+DWS:5] >= sl_q);
        wire           dviol = dact && (sh_sel ? s_viol : p_viol);   // word index >= data limit (high bits split off: a 6-bit compare plus an OR instead of a 30-bit compare)
        wire           abort = cviol | dviol;
        reg  [IAW-1:0] cur_a;                       // address of the instruction being executed (pc itself rotates mid-instruction)
        reg  [31:0]    fw;
        reg  [IAW-1:0] fw_a;
        reg            fw_v;
        wire [IAW-1:0] tgt   = fetching ? ia_l : cur_a + 1'b1;
        wire           have  = fw_v && (fw_a == tgt);
        wire           stall_i = fetching && !(fw_v && fw_a == ia_l);
        // ---- shared data word (v10): a load waits here until its word is in dcw
        reg  [31:0]    racc, dacc;
        reg  [4:0]     rcnt, dcnt;
        reg            dc_v, infl, dpend;
        wire [DWS-1:0] sidx    = da[5+DWS-1:5];
        wire           need_rd = dldr && sh_sel && !dviol && !dc_v;      // dc_v is cleared whenever no load is live, so no address tag is needed
        wire           stall_d = need_rd;
        reg            rq_v, rq_w;                    // the slice's registered request (see the port logic)
        reg  [DWS-1:0] rq_a;
        wire           g_me    = rq_v && (slot_cnt == gi);                          // the port is mine this clock
        wire           g_rd    = g_me && !rq_w;
        wire           g_wr    = g_me &&  rq_w;
        wire           capt    = rd_gv && !rd_gh && (rd_gid == gi) && infl;
        assign rqa_all[gi*DWS +: DWS] = rq_a;
        assign rqv_all[gi]  = rq_v;
        assign rqw_all[gi]  = rq_w;
        assign pdat_all[gi*32 +: 32] = dacc;
        wire           want  = !have && (fetching || !h);
        assign tgt_all[gi*IAW +: IAW] = tgt;
        always @(posedge clk) begin
            if (fetching) cur_a <= ia_l;
            if (rst || imem_we) fw_v <= 1'b0;       // a code write invalidates the prefetched word
            else if (want && slot_cnt == gi) begin fw <= sh_q; fw_a <= tgt; fw_v <= 1'b1; end
        end
        initial begin cur_a = 0; fw = 0; fw_a = 0; fw_v = 0; end
        assign id = fw;
        wire ce_g = cph & ~stall_i & ~stall_d;

        // ---- register file (two read ports) and data memory in 32-bit-wide block RAM, one word per register / data word.
        //      One single-port block per read port; the address is time-shared: clock 1 of a step writes, clock 0 reads.
        localparam DMD = (DMW < 32) ? 32 : DMW;                  // the proven block shape is 32 words x 32 bits
        localparam DWA = $clog2(DMD);
        (* ram_style = "block" *) reg [31:0] rf_a [0:31];
        (* ram_style = "block" *) reg [31:0] rf_b [0:31];
        (* ram_style = "block" *) reg [31:0] dmw  [0:DMD-1];
        reg [31:0] rqa_w, rqb_w, dq_w;
        integer zq;
`ifndef SYNTHESIS
        initial begin
            for (zq = 0; zq < 32; zq = zq + 1) begin rf_a[zq] = 32'h0; rf_b[zq] = 32'h0; end
            for (zq = 0; zq < DMD; zq = zq + 1) dmw[zq] = 32'h0;
        end
`endif
        // write accumulators: bit k of the pass lands in acc[k]; the 32nd write of a pass flushes the finished word
        wire        rw_now = rwe & ce_g;          // v10: ce_g, not cph - a load waiting for its shared word must not write its register yet
        wire        dw_now = dwe & ~dviol & ce_g;
        wire [31:0] rnext  = (racc & ~(32'd1 << rwa[4:0])) | ({31'b0, rwd} << rwa[4:0]);
        wire [31:0] dnext  = (dacc & ~(32'd1 << da[4:0]))  | ({31'b0, dwd} << da[4:0]);
        wire        rflush = rw_now & (rcnt == 5'd31);
        wire        dflush = dw_now & (dcnt == 5'd31);
        wire        dflush_p = dflush & ~sh_sel;      // private word: block RAM of the slice (v9 path)
        wire        dflush_s = dflush &  sh_sel;      // shared word: held in dacc until the slice's slot
        always @(posedge clk) begin
            if (rst || start_v[gi]) begin rcnt <= 5'd0; dcnt <= 5'd0; end   // v9: a task that was aborted mid-pass must not leave a half-counted write behind
            else begin
                if (rw_now) begin racc <= rnext; rcnt <= rcnt + 1'b1; end
                if (dw_now) begin dacc <= dnext; dcnt <= dcnt + 1'b1; end
                else if (capt) dacc <= sdq;                 // v10: a word read from the shared RAM lands here
            end
        end
        wire [4:0] rf_aa = cph ? rwa[9:5] : ra[9:5];
        wire [4:0] rf_ba = cph ? rwa[9:5] : rb[9:5];
        wire [DWA-1:0] dm_a = da[DWA+4:5];
        // Every block-RAM input is re-registered on the FALLING clock edge: the inputs are then stable for half a cycle
        // around the rising edge that samples them.  (nextpnr reports hold violations of about 0.1 ns on block-RAM
        // address pins driven straight from flops; the signals settle well inside half a cycle.)
        reg [4:0]      rf_aa_n, rf_ba_n;
        reg [DWA-1:0]  dm_a_n;
        reg            rflush_n, dflush_n;
        reg [31:0]     rnext_n, dnext_n;
        always @(negedge clk) begin
            rf_aa_n <= rf_aa; rf_ba_n <= rf_ba; dm_a_n <= dm_a;
            rflush_n <= rflush; dflush_n <= dflush_p; rnext_n <= rnext; dnext_n <= dnext;
        end
        always @(posedge clk) begin
            if (rflush_n) begin rf_a[rf_aa_n] <= rnext_n; rf_b[rf_ba_n] <= rnext_n; end
            rqa_w <= rf_a[rf_aa_n]; rqb_w <= rf_b[rf_ba_n];
            if (dflush_n) dmw[dm_a_n] <= dnext_n;
            dq_w <= dmw[dm_a_n];
        end
        // bit select (the bit index is stable for the whole step, so it is still valid when the core consumes the word)
        assign rad = rqa_w[ra[4:0]];
        assign rbd = rqb_w[rb[4:0]];
        assign drd = sh_sel ? dacc[da[4:0]] : dq_w[da[4:0]];     // v10: a shared word is held in the (otherwise idle) write accumulator

        // ---- shared word handshake (v10)
        always @(posedge clk) begin
            if (rst) begin infl <= 1'b0; dc_v <= 1'b0; dpend <= 1'b0; rq_v <= 1'b0; rq_w <= 1'b0; end
            else begin
                if (g_rd) infl <= 1'b1; else if (capt) infl <= 1'b0;
                if (!dldr) dc_v <= 1'b0; else if (capt) dc_v <= 1'b1;
                if (dflush_s)                                 begin rq_v <= 1'b1; rq_w <= 1'b1; rq_a <= sb_q + sidx; dpend <= 1'b1; end   // the finished word waits in dacc
                else if (g_wr)                                begin rq_v <= 1'b0; dpend <= 1'b0; end
                else if (need_rd && !infl && !dpend && !rq_v) begin rq_v <= 1'b1; rq_w <= 1'b0; rq_a <= sb_q + sidx; end
                else if (g_rd)                                rq_v <= 1'b0;
            end
        end
        initial begin dc_v = 0; infl = 0; dpend = 0; rq_v = 0; rq_w = 0; rq_a = 0; sb_q = 0; sl_q = 0; end
`ifndef SYNTHESIS
        always @(posedge clk) if (!rst && dpend && dw_now && sh_sel) $display("sc_sys_v10: slice %0d stored again before its shared write was served", gi);
`endif

        // ---- start: held until the core leaves HALT (the core only steps when ce=1)
        reg        pend;
        reg [31:0] ent_q;
        reg [2:0]  lw_q;
        always @(posedge clk) begin
            if (rst) pend <= 1'b0;
            else begin
                pend <= start_v[gi] | (pend & h);
                if (start_v[gi]) begin ent_q <= launch_entry; lw_q <= launch_lw; cb_q <= launch_cb; ce_q <= launch_ce; dl_q <= launch_dl; sb_q <= launch_sb; sl_q <= launch_sl; end
            end
        end
        assign pend_v[gi] = pend;

        uc_core_v2v #(.W(1)) core (
            .clk(clk), .rst(rst), .start(pend), .entry(ent_q), .ce(ce_g),
            .halted(h), .trap(t), .fetching(fetching), .abort(abort), .dmem_act(dact), .dmem_ld(dldr),
            .imem_addr(ia), .imem_data(id),
            .ra_addr(ra), .ra_data(rad), .rb_addr(rb), .rb_data(rbd),
            .rw_en(rwe), .rw_addr(rwa), .rw_data(rwd),
            .d_addr(da), .d_we(dwe), .d_wdata(dwd), .d_rdata(drd));
        assign halted_v[gi] = h;
        assign trap_v[gi]   = t;
        // v12: why the check fired (first one wins, cleared when a task starts on this slice)
        reg [2:0]  tc_q; reg [15:0] ta_q;
        wire [2:0] tc_new = cviol ? 3'd1 : dviol ? (sh_sel ? ((sl_q == 0) ? 3'd4 : 3'd3) : 3'd2) : 3'd0;
        always @(posedge clk)
            if (rst || start_v[gi]) begin tc_q <= 3'd0; ta_q <= 16'd0; end
            else if (tc_q == 3'd0 && tc_new != 3'd0) begin tc_q <= tc_new; ta_q <= cviol ? ia[15:0] : da[20:5]; end
        assign tcause_v[gi*3 +: 3] = tc_q;
        assign taddr_v[gi*16 +: 16] = ta_q;

        // a0 (x10) is shadowed from the write stream: same bits the packed register file holds
        reg [31:0] a0s;
        always @(posedge clk) if (rwe & cph & (rwa[9:5] == 5'd10)) a0s[rwa[4:0]] <= rwd;
        initial a0s = 32'h0;
        assign a0_v[gi*32 +: 32] = a0s;
    end endgenerate

    // ------------------------------------------------------------ idle table + per-core info
    reg [63:0]  slice_busy;          // 1 = slice allocated.  Dispatcher SETs, watcher CLEARs.
    reg [S-1:0] busy_l;              // leader slices that currently run a task
    reg [15:0]  own_tid [0:S-1];
    reg [2:0]   own_lw  [0:S-1];
    reg [5:0]   own_cls [0:S-1];

    // ------------------------------------------------------------ counters
    reg [31:0] cyc;
    reg [63:0] busy_slice_cycles, waste_blocked, waste_tail, search_cycles;
    reg [31:0] launch_err, dispatches;

    // ------------------------------------------------------------ dispatcher state
    localparam D_SLEEP = 2'd0, D_FIND = 2'd1, D_LAUNCH = 2'd2;
    reg [1:0]  dstate;
    reg        rescan;
    reg        hold_q;
    reg        ph;                    // 0 = first candidate, 1 = second candidate
    reg        cur_is_crit;
    reg [15:0] cur_tid, cur_code;
    reg [2:0]  cur_lw;
    reg [5:0]  cand;
    reg [31:0] crit_streak, bulk_pass;

    wire pend_c = (qc_wr != qc_rd);
    reg        pend_b;
    reg [3:0]  hb;                    // highest non-empty bulk bucket
    integer    hi_;
    always @* begin
        pend_b = 1'b0; hb = 3'd0;
        for (hi_ = 0; hi_ < NB; hi_ = hi_ + 1)
            if (kwr[hi_] != krd[hi_]) begin pend_b = 1'b1; hb = hi_[3:0]; end
    end
    wire [15:0] bhead = qk[hb*QD + (krd[hb] % QD)];
    reg  [3:0]  cur_bk;
    wire [5:0]  cur_w  = 6'd1 << cur_lw;
    wire [63:0] cur_gm = (64'd1 << cur_w) - 64'd1;

    function [63:0] gmask(input [6:0] w);
        gmask = (64'd1 << w) - 64'd1;
    endfunction

    // one-cycle placement search over the idle table
    reg        fit_found;
    reg [5:0]  fit_base;
    reg [6:0]  best_sz, bsz, blk;
    reg [5:0]  bbase;
    integer    bi, kk;
    always @* begin
        fit_found = 1'b0; fit_base = 6'd0; best_sz = 7'd127; bsz = 7'd0; blk = 7'd0; bbase = 6'd0;
        for (bi = 0; bi < S; bi = bi + 1) begin
            if (((bi & (cur_w - 1)) == 0) && (bi + cur_w <= S) && (((slice_busy >> bi) & cur_gm) == 64'd0)) begin
                bsz = {1'b0, cur_w};
                if (BESTFIT) begin
                    for (kk = 0; kk <= 5; kk = kk + 1) begin
                        blk = 7'd1 << kk;
                        if (blk >= cur_w) begin
                            bbase = bi & ~(blk - 1);
                            if ((bbase + blk <= S) && (((slice_busy >> bbase) & gmask(blk)) == 64'd0)) bsz = blk;
                        end
                    end
                end
                if (!fit_found || (BESTFIT && bsz < best_sz)) begin
                    fit_found = 1'b1; fit_base = bi[5:0]; best_sz = bsz;
                end
            end
        end
    end

    // ------------------------------------------------------------ watcher: next request to service
    // Lowest set line of the 256-line table, as a tree (16 rows x 16 columns) so the path is about 10 LUT
    // levels instead of a 256-long chain.  Same choice as the v3 loop (lowest index first).
    function [3:0] pe16(input [15:0] x);      // index of the lowest set bit (0 if none)
        reg b3, b2, b1; reg [7:0] x8; reg [3:0] x4; reg [1:0] x2;
        begin
            b3 = ~(|x[7:0]);  x8 = b3 ? x[15:8] : x[7:0];
            b2 = ~(|x8[3:0]); x4 = b2 ? x8[7:4] : x8[3:0];
            b1 = ~(|x4[1:0]); x2 = b1 ? x4[3:2] : x4[1:0];
            pe16 = {b3, b2, b1, ~x2[0]};
        end
    endfunction
    // v13: the watcher takes three clocks per request instead of one (v12: one clock from the request table all the way to the profile table).
    //   wph 0: look at the 16 rows; if any line is set, register which row is the lowest one that has one (w_row_q)
    //   wph 1: pick the lowest set line inside that row, register it (w_id_q)
    //   wph 2: service it, exactly as v12 did in its one clock (w_found = 1, w_id = w_id_q): clear the line, free the slice, write the task
    //          table and the profile table.
    // Request lines are only set by the producers and only cleared in wph 2, so the row found in wph 0 still has its line set in wph 1 and
    // the line picked in wph 1 is still set in wph 2.  The cores keep their results (a0, trap, cause, address) until a new task starts on
    // the slice, and the slice stays busy until wph 2 frees it, so reading them in wph 2 gives what v12 read.
    // Cost: a request is serviced up to 3 clocks later than in v12, and at most one request per 3 clocks; a slice is free again 2 clocks later.
    reg [15:0] row_any;
    reg [1:0]  wph;
    reg [3:0]  w_row_q;
    reg [7:0]  w_id_q;
    wire       w_found = (wph == 2'd2);
    wire [7:0] w_id    = w_id_q;
    integer    wi;
    always @* for (wi = 0; wi < 16; wi = wi + 1) row_any[wi] = |req_tab[wi*16 +: 16];
    always @(posedge clk) begin
        if (rst) begin wph <= 2'd0; w_row_q <= 4'd0; w_id_q <= 8'd0; end
        else case (wph)
            2'd0:    if (|row_any) begin w_row_q <= pe16(row_any); wph <= 2'd1; end
            2'd1:    begin w_id_q <= {w_row_q, pe16(req_tab[w_row_q*16 +: 16])}; wph <= 2'd2; end
            default: wph <= 2'd0;
        endcase
    end

    // ------------------------------------------------------------ main clocked block
    reg [63:0]  nb;
    reg [255:0] rq;
    reg         rs;
    reg [5:0]   wfree;
    reg [5:0]   wb;
    reg [3:0]   pb;
    reg [8:0]   pk;
    reg [23:0]  dur;
    reg [24:0]  davg;                    // average of old and new sample (v4.1: kept apart so the known bit is not truncated away)
    integer     pcnt, pi, fi;
    reg         first_crit, second_crit, second_avail, second_ok;

    always @(posedge clk) cph <= rst ? 1'b0 : ~cph;

    always @(posedge clk) begin
        if (rst) begin
            slice_busy <= 64'd0; busy_l <= {S{1'b0}}; req_tab <= 256'd0; fin_sent <= {S{1'b0}};
            qc_wr <= 0; qc_rd <= 0; done_count <= 0; ev_cnt <= 0;
            cyc <= 0; busy_slice_cycles <= 0; waste_blocked <= 0; waste_tail <= 0; search_cycles <= 0;
            launch_err <= 0; dispatches <= 0; hold_q <= 1'b0;
            dstate <= D_SLEEP; rescan <= 1'b0; ph <= 1'b0; cand <= 0;
            start_v <= {S{1'b0}}; halted_q <= {S{1'b1}};
            launch_entry <= 0; launch_lw <= 0; launch_cb <= 0; launch_ce <= IMEM_WORDS; launch_dl <= DMD_G; launch_sb <= 0; launch_sl <= 0;
            cur_is_crit <= 0; cur_tid <= 0; cur_code <= 0; cur_lw <= 0;
            crit_streak <= 0; bulk_pass <= 0; cur_bk <= 0;
            for (fi = 0; fi < NB; fi = fi + 1) begin kwr[fi] <= 0; krd[fi] <= 0; end
        end else begin
            cyc      <= cyc + 1;
            halted_q <= halted_v;
            start_v  <= {S{1'b0}};
            nb = slice_busy;
            rq = req_tab;
            rs = rescan;
            hold_q <= hold;
            if (hold_q && !hold) rs = 1'b1;            // v7: release -> look at the queues again

            // ---- statistics: where do idle slice-cycles go?
            pcnt = 0;
            for (pi = 0; pi < 64; pi = pi + 1) pcnt = pcnt + slice_busy[pi];
            busy_slice_cycles <= busy_slice_cycles + pcnt;
            if (hold) ;                                                          // v7: waiting for go is not waste
            else if (pend_c || pend_b) waste_blocked <= waste_blocked + (S - pcnt);   // idle while work waited
            else if (pcnt != 0)   waste_tail    <= waste_tail    + (S - pcnt);   // idle, nothing left to run
            if (dstate != D_SLEEP) search_cycles <= search_cycles + 1;

            // ---- dispatcher
            first_crit = pend_c && !(pend_b && crit_streak >= GUARD);
            case (dstate)
                D_SLEEP: if (rs && !hold && (pend_c || pend_b)) begin
                    rs = 1'b0;
                    cur_is_crit <= first_crit;
                    cur_tid     <= first_crit ? qc[qc_rd % QD] : bhead;
                    cur_code    <= t_code[first_crit ? qc[qc_rd % QD] : bhead];
                    cur_lw      <= t_lw  [first_crit ? qc[qc_rd % QD] : bhead];
                    cur_bk      <= hb;
                    ph          <= 1'b0;
                    dstate      <= D_FIND;
                end
                D_FIND: begin
                    if (fit_found) begin cand <= fit_base; dstate <= D_LAUNCH; end
                    else begin
                        // head does not fit: try the other class's head once, then sleep until something frees
                        second_crit  = !cur_is_crit;
                        second_avail = second_crit ? pend_c : pend_b;
                        second_ok    = second_crit ? 1'b1 : (bulk_pass < MAXPASS);
                        if (!ph && second_avail && second_ok) begin
                            cur_is_crit <= second_crit;
                            cur_tid     <= second_crit ? qc[qc_rd % QD] : bhead;
                            cur_code    <= t_code[second_crit ? qc[qc_rd % QD] : bhead];
                            cur_lw      <= t_lw  [second_crit ? qc[qc_rd % QD] : bhead];
                            cur_bk      <= hb;
                            ph          <= 1'b1;
                        end else dstate <= D_SLEEP;
                    end
                end
                D_LAUNCH: begin
                    if ((slice_busy & (cur_gm << cand)) != 64'd0 || (cand & (cur_w - 1)) != 0 || cand + cur_w > S)
                        launch_err <= launch_err + 1;
                    nb = nb | (cur_gm << cand);
                    busy_l[cand]   <= 1'b1;
                    own_tid[cand]  <= cur_tid;
                    own_lw[cand]   <= cur_lw;
                    own_cls[cand]  <= t_prog[cur_tid];
                    t_start[cur_tid] <= cyc;
                    t_state[cur_tid] <= 2'd2;
                    t_slot [cur_tid] <= cand;
                    start_v[cand]  <= 1'b1;
                    launch_entry   <= {14'd0, cur_code, 2'b00};
                    launch_lw      <= cur_lw;
                    launch_cb      <= rg_v[t_prog[cur_tid]] ? rg_cb[t_prog[cur_tid]] : {IAW{1'b0}};
                    launch_ce      <= rg_v[t_prog[cur_tid]] ? rg_ce[t_prog[cur_tid]] : IMEM_WORDS;
                    launch_dl      <= rg_v[t_prog[cur_tid]] ? rg_dl[t_prog[cur_tid]] : DMD_G;
                    launch_sb      <= rs_v[t_prog[cur_tid]] ? rs_sb[t_prog[cur_tid]] : {DWS{1'b0}};
                    launch_sl      <= rs_v[t_prog[cur_tid]] ? rs_sl[t_prog[cur_tid]] : {(DWS+1){1'b0}};
                    if (cur_is_crit) begin
                        qc_rd       <= qc_rd + 1;
                        crit_streak <= pend_b ? crit_streak + 1 : 0;
                        bulk_pass   <= 0;
                    end else begin
                        krd[cur_bk] <= krd[cur_bk] + 1;
                        crit_streak <= 0;
                        bulk_pass   <= pend_c ? bulk_pass + 1 : 0;
                    end
                    dispatches <= dispatches + 1;
                    rs     = 1'b1;               // try the next task straight away
                    dstate <= D_SLEEP;
                end
                default: dstate <= D_SLEEP;
            endcase

            // ---- host push: task table entry, then the right queue
            if (h_push) begin
                pb = LONGEST ? bucket_of(prof[pkey(h_prog, h_lw)]) : 4'd0;
                t_code [h_tid] <= h_code;
                t_lw   [h_tid] <= h_lw;
                t_crit [h_tid] <= h_crit;
                t_arr  [h_tid] <= cyc;
                t_state[h_tid] <= 2'd1;
                if (PRIO && h_crit) begin qc[qc_wr % QD] <= h_tid; qc_wr <= qc_wr + 1; end
                else begin
                    qk[pb*QD + (kwr[pb] % QD)] <= h_tid; kwr[pb] <= kwr[pb] + 1;
                end
                t_pred[h_tid] <= prof[pkey(h_prog, h_lw)];
                t_prog[h_tid] <= h_prog;                rs = 1'b1;
            end

            // ---- watcher: service one request per cycle (clear first, then apply new sets)
            if (w_found) begin
                rq[w_id] = 1'b0;
                if (w_id < 8'd64) begin
                    wb    = w_id[5:0];
                    wfree = 6'd1 << own_lw[wb];
                    nb    = nb & ~(gmask({1'b0, wfree}) << wb);
                    busy_l[wb]   <= 1'b0;
                    fin_sent[wb] <= 1'b0;
                    t_end  [own_tid[wb]] <= cyc;
                    t_a0   [own_tid[wb]] <= a0_v[wb*32 +: 32];
                    t_trap [own_tid[wb]] <= trap_v[wb];
                    t_cause[own_tid[wb]] <= (tcause_v[wb*3 +: 3] != 3'd0) ? tcause_v[wb*3 +: 3] : (trap_v[wb] ? 3'd5 : 3'd0);
                    t_taddr[own_tid[wb]] <= taddr_v[wb*16 +: 16];
                    t_state[own_tid[wb]] <= 2'd3;
                    pk  = pkey(t_prog[own_tid[wb]], t_lw[own_tid[wb]]);
                    dur = cyc[23:0] - t_start[own_tid[wb]][23:0];
                    // first sample is stored as is; later ones are averaged with the old value
                    davg = ({1'b0, prof[pk][23:0]} + {1'b0, dur}) >> 1;
                    prof[pk] <= prof[pk][24] ? {1'b1, davg[23:0]} : {1'b1, dur};   // v4.1 fix: the old form lost the known bit on every 2nd sample
                    done_count <= done_count + 1;
                    rs = 1'b1;                   // capacity changed: wake the dispatcher
                end else begin
                    ev_id  [ev_cnt % QD] <= w_id;
                    ev_data[ev_cnt % QD] <= ev_pl[w_id[EVB-1:0]];
                    ev_cyc [ev_cnt % QD] <= cyc;
                    ev_cnt <= ev_cnt + 1;
                end
            end

            // ---- producers set request lines (set wins over a clear in the same cycle)
            for (fi = 0; fi < S; fi = fi + 1)
                if (busy_l[fi] && halted_v[fi] && halted_q[fi] && !start_v[fi] && !pend_v[fi] && !fin_sent[fi]) begin
                    rq[fi] = 1'b1;
                    fin_sent[fi] <= 1'b1;
                end
            if (ev_pl_we) ev_pl[ev_pl_id[EVB-1:0]] <= ev_pl_data;
            if (ev_set && ev_set_id >= 8'd64) rq[ev_set_id] = 1'b1;

            req_tab    <= rq;
            slice_busy <= nb;
            rescan     <= rs;
        end
    end

    // ------------------------------------------------------------ host read-out
    assign q_start = t_start[q_tid % QD];
    assign q_end   = t_end  [q_tid % QD];
    assign q_a0    = t_a0   [q_tid % QD];
    assign q_arr   = t_arr  [q_tid % QD];
    assign q_trap  = t_trap [q_tid % QD];
    assign q_state = t_state[q_tid % QD];
    assign q_slot  = t_slot [q_tid % QD];
    assign q_pred  = t_pred [q_tid % QD];
    assign q_cause = t_cause[q_tid % QD];
    assign q_taddr = t_taddr[q_tid % QD];

    // ---- v12 status read-out
    reg [40*S-1:0] sbc_v;
    integer si_;
    always @(posedge clk)
        for (si_ = 0; si_ < S; si_ = si_ + 1)
            if (rst) sbc_v[si_*40 +: 40] <= 40'd0;
            else if (slice_busy[si_]) sbc_v[si_*40 +: 40] <= sbc_v[si_*40 +: 40] + 40'd1;
    assign st_bs = sbc_v;
    integer sj_;
    always @* begin
        for (sj_ = 0; sj_ < S; sj_ = sj_ + 1)
            st_sl[sj_*32 +: 32] = { busy_l[sj_] ? own_tid[sj_] : 16'hFFFF, busy_l[sj_] ? {2'b00, own_cls[sj_]} : 8'hFF, 6'b0, busy_l[sj_], slice_busy[sj_] };
        st_qc = {10'd0, qc_wr[5:0] - qc_rd[5:0]};                                  // a queue holds at most QD (<= 32) task ids
        st_qb = 16'd0;
        for (sj_ = 0; sj_ < NB; sj_ = sj_ + 1) st_qb = st_qb + {10'd0, kwr[sj_][5:0] - krd[sj_][5:0]};
    end
    assign o_cyc = cyc; assign o_done = done_count; assign o_lerr = launch_err; assign o_disp = dispatches;
    assign o_busy = busy_slice_cycles; assign o_blocked = waste_blocked; assign o_tail = waste_tail; assign o_search = search_cycles;
    assign o_busy_l = busy_l;
endmodule

// pk_ram: NW words x 32 bits, built from 32 one-bit lanes so a write can touch any subset of bits.
// Synchronous read (old data on a same-address write), write enable per bit lane.
module pk_ram #(parameter NW = 32, parameter AW = 5) (
    input  wire          clk,
    input  wire          we,
    input  wire [AW-1:0] wa,
    input  wire [31:0]   wdata,
    input  wire [31:0]   wen,
    input  wire [AW-1:0] ra,
    output reg  [31:0]   rq
);
    genvar l;
    generate for (l = 0; l < 32; l = l + 1) begin : lane
        reg m [0:NW-1];
        integer z;
`ifndef SYNTHESIS
        initial for (z = 0; z < NW; z = z + 1) m[z] = 1'b0;   // simulation only: block/LUT RAM powers up as 0 anyway
`endif
        always @(posedge clk) begin
            if (we && wen[l]) m[wa] <= wdata[l];
            rq[l] <= m[ra];
        end
    end endgenerate
endmodule
