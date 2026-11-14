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

module sc_sys_v5 #(
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
    parameter EVB        = 8      // event payload index bits (lines 64.. use ev_pl[id mod 2^EVB])
) (
    input  wire        clk,
    input  wire        rst,
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
    wire [32*S-1:0] a0_v;
    reg  [31:0]     launch_entry;
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

        // ---- private instruction memory (synchronous read)
        reg [31:0] imem_s [0:IMEM_WORDS-1];     // left to the tool: forcing block RAM fails to place beyond 2 slices (only 2 SDPX9 sites usable)
        reg [31:0] id_q;
        integer q;
`ifndef SYNTHESIS
        initial for (q = 0; q < IMEM_WORDS; q = q + 1) imem_s[q] = 32'h0;   // simulation only: the host loads the code
`endif
        always @(posedge clk) begin
            if (imem_we) imem_s[imem_wa[IAW-1:0]] <= imem_wd;
            id_q <= imem_s[ia[IAW-1:0]];
        end
        assign id = id_q;

        // ---- packed register file (2 read ports) and data memory.  Word = register / data word;
        //      digit k of width w lives at bits [k*w +: w].
        // ---- 1-bit register file (two read ports) and data memory, address {word, bit}; synchronous read.
        //      v5 pool: every core is the fixed 1-bit core, so no lanes, masks or shifters.
        // BOARD FINDING (2026-11-14, Tang Nano 20K): the register file in single-port block RAM FAILS on the real chip
        // (tests B and D) although it passes every simulation; the same register file in LUT-RAM (tests A and C) and the
        // data memory in single-port block RAM (test C) both pass.  So: register file = distributed, data memory = block.
        (* ram_style = "distributed" *) reg rf_a [0:1023]; (* ram_style = "distributed" *) reg rf_b [0:1023]; reg rqa_b, rqb_b;
        (* ram_style = "block" *) reg dm [0:DMW*32-1]; reg dq_b;
        wire [9:0] rf_aa = cph ? rwa : ra;
        wire [9:0] rf_ba = cph ? rwa : rb;
        integer zq;
`ifndef SYNTHESIS
        initial begin
            for (zq = 0; zq < 1024; zq = zq + 1) begin rf_a[zq] = 1'b0; rf_b[zq] = 1'b0; end
            for (zq = 0; zq < DMW*32; zq = zq + 1) dm[zq] = 1'b0;
        end
`endif
        always @(posedge clk) begin
            // single-port block RAM per read port: clock 1 of the step writes (address rwa), clock 0 reads (ra / rb)
            if (rwe & cph) begin rf_a[rf_aa] <= rwd; rf_b[rf_ba] <= rwd; end
            rqa_b <= rf_a[rf_aa]; rqb_b <= rf_b[rf_ba];
            if (dwe & cph) dm[da[DAW+4:0]] <= dwd;
            dq_b <= dm[da[DAW+4:0]];
        end
        assign rad = rqa_b;
        assign rbd = rqb_b;
        assign drd = dq_b;

        // ---- start: held until the core leaves HALT (the core only steps when ce=1)
        reg        pend;
        reg [31:0] ent_q;
        reg [2:0]  lw_q;
        always @(posedge clk) begin
            if (rst) pend <= 1'b0;
            else begin
                pend <= start_v[gi] | (pend & h);
                if (start_v[gi]) begin ent_q <= launch_entry; lw_q <= launch_lw; end
            end
        end
        assign pend_v[gi] = pend;

        uc_core_v2s #(.W(1)) core (
            .clk(clk), .rst(rst), .start(pend), .entry(ent_q), .ce(cph),
            .halted(h), .trap(t),
            .imem_addr(ia), .imem_data(id),
            .ra_addr(ra), .ra_data(rad), .rb_addr(rb), .rb_data(rbd),
            .rw_en(rwe), .rw_addr(rwa), .rw_data(rwd),
            .d_addr(da), .d_we(dwe), .d_wdata(dwd), .d_rdata(drd));
        assign halted_v[gi] = h;
        assign trap_v[gi]   = t;

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

    // ------------------------------------------------------------ counters
    reg [31:0] cyc;
    reg [63:0] busy_slice_cycles, waste_blocked, waste_tail, search_cycles;
    reg [31:0] launch_err, dispatches;

    // ------------------------------------------------------------ dispatcher state
    localparam D_SLEEP = 2'd0, D_FIND = 2'd1, D_LAUNCH = 2'd2;
    reg [1:0]  dstate;
    reg        rescan;
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
    reg [15:0] row_any;
    reg        w_found;
    reg [7:0]  w_id;
    reg [3:0]  w_row;
    integer    wi;
    always @* begin
        for (wi = 0; wi < 16; wi = wi + 1) row_any[wi] = |req_tab[wi*16 +: 16];
        w_found = |row_any;
        w_row   = pe16(row_any);
        w_id    = {w_row, pe16(req_tab[w_row*16 +: 16])};
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
            launch_err <= 0; dispatches <= 0;
            dstate <= D_SLEEP; rescan <= 1'b0; ph <= 1'b0; cand <= 0;
            start_v <= {S{1'b0}}; halted_q <= {S{1'b1}};
            launch_entry <= 0; launch_lw <= 0;
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

            // ---- statistics: where do idle slice-cycles go?
            pcnt = 0;
            for (pi = 0; pi < 64; pi = pi + 1) pcnt = pcnt + slice_busy[pi];
            busy_slice_cycles <= busy_slice_cycles + pcnt;
            if (pend_c || pend_b) waste_blocked <= waste_blocked + (S - pcnt);   // idle while work waited
            else if (pcnt != 0)   waste_tail    <= waste_tail    + (S - pcnt);   // idle, nothing left to run
            if (dstate != D_SLEEP) search_cycles <= search_cycles + 1;

            // ---- dispatcher
            first_crit = pend_c && !(pend_b && crit_streak >= GUARD);
            case (dstate)
                D_SLEEP: if (rs && (pend_c || pend_b)) begin
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
                    t_start[cur_tid] <= cyc;
                    t_state[cur_tid] <= 2'd2;
                    t_slot [cur_tid] <= cand;
                    start_v[cand]  <= 1'b1;
                    launch_entry   <= {14'd0, cur_code, 2'b00};
                    launch_lw      <= cur_lw;
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
