// sc_sys.v - S-Core array: S slices, runtime-width cores, queues, dedicated dispatcher
//
//   host --push--> [submission queue] --> DISPATCHER --start--> core(leader slice b, width w)
//                                             ^                        |
//                                             |                    halted=1
//                  [completion queue] <-- frees slices <---------------+
//
// - There is NO interrupt anywhere.  Cores run a task to completion (EBREAK) and go idle.
//   The host polls the completion queue.
// - A core of width w occupies w aligned slices [b, b+w), b % w == 0 (buddy-style).
//   Core instance b exists for every slice b but can only be started at widths that divide b.
// - Each core instance has its own private register file and data memory (window by core id).
//   Code is a shared read-only image (imem); a task's entry is a word address into it.
// - The dispatcher is a small dedicated FSM: pop a descriptor, find the lowest aligned free
//   group in ONE cycle, mark it busy, pulse start.  Completions are freed one per cycle.
//   Policy: strict FIFO (a head task that does not fit waits; later tasks do not overtake).

module sc_sys #(
    parameter S          = 32,        // slices in the pool (<= 64)
    parameter QD         = 256,       // queue depth (host must not exceed it)
    parameter IMEM_WORDS = 8192
) (
    input  wire        clk,
    input  wire        rst,
    // host submit port
    input  wire        h_push,
    input  wire [15:0] h_tid,
    input  wire [15:0] h_code,        // entry as a word address in imem
    input  wire [2:0]  h_lw           // requested width = 2^h_lw slices
);
    reg [31:0] imem [0:IMEM_WORDS-1];

    // ------------------------------------------------------------ queues
    reg [15:0] sq_tid  [0:QD-1];
    reg [15:0] sq_code [0:QD-1];
    reg [2:0]  sq_lw   [0:QD-1];
    reg [31:0] sq_wr, sq_rd;

    reg [15:0] cq_tid   [0:QD-1];
    reg [31:0] cq_a0    [0:QD-1];
    reg [31:0] cq_start [0:QD-1];
    reg [31:0] cq_end   [0:QD-1];
    reg [2:0]  cq_lw    [0:QD-1];
    reg        cq_trap  [0:QD-1];
    reg [31:0] cq_wr;

    // ------------------------------------------------------------ cores
    reg  [S-1:0]    start_v;
    reg  [S-1:0]    halted_q;
    wire [S-1:0]    halted_v, trap_v;
    wire [32*S-1:0] a0_v;
    reg  [31:0]     launch_entry;
    reg  [2:0]      launch_lw;

    genvar gi;
    generate for (gi = 0; gi < S; gi = gi + 1) begin : slot
        wire        h, t;
        wire [2:0]  lwc;
        wire [29:0] ia;
        wire [31:0] id = imem[ia[12:0]];
        wire [9:0]  ra, rb, rwa;
        wire [31:0] rad, rbd, rwd;
        wire        rwe;
        wire [34:0] da;
        wire        dwe;
        wire [31:0] dwd, drd;
        reg  [31:0] rf [0:1023];
        reg  [31:0] dm [0:32767];
        integer q;
        initial begin
            for (q = 0; q < 1024;  q = q + 1) rf[q] = 0;
            for (q = 0; q < 32768; q = q + 1) dm[q] = 0;
        end
        assign rad = rf[ra];
        assign rbd = rf[rb];
        always @(posedge clk) if (rwe) rf[rwa] <= rwd;
        assign drd = dm[da[14:0]];
        always @(posedge clk) if (dwe) dm[da[14:0]] <= dwd;

        uc_core_rw core (
            .clk(clk), .rst(rst), .start(start_v[gi]), .entry(launch_entry), .lw_in(launch_lw),
            .halted(h), .trap(t), .lw_cur(lwc),
            .imem_addr(ia), .imem_data(id),
            .ra_addr(ra), .ra_data(rad), .rb_addr(rb), .rb_data(rbd),
            .rw_en(rwe), .rw_addr(rwa), .rw_data(rwd),
            .d_addr(da), .d_we(dwe), .d_wdata(dwd), .d_rdata(drd));
        assign halted_v[gi] = h;
        assign trap_v[gi]   = t;

        // snapshot of a0 (x10), re-assembled from its digits; registered, stable long before halt
        reg [31:0] a0s;
        reg [31:0] acc;
        integer dd;
        reg [5:0] wbits;
        always @(posedge clk) if (h) begin       // only needed once the task has finished
            wbits = 6'd1 << lwc;
            acc = 0;
            for (dd = 0; dd < 32; dd = dd + 1)
                if (dd < (32 >> lwc))
                    acc = acc | ((rf[{5'd10, dd[4:0]}] & ((lwc == 3'd5) ? 32'hFFFF_FFFF : ((32'd1 << wbits) - 32'd1))) << (dd * wbits));
            a0s <= acc;
        end
        assign a0_v[gi*32 +: 32] = a0s;
    end endgenerate

    // ------------------------------------------------------------ dispatcher state
    reg [63:0]  slice_busy;
    reg [S-1:0] busy_l;
    reg [15:0]  own_tid [0:S-1];
    reg [31:0]  own_start [0:S-1];
    reg [2:0]   own_lw [0:S-1];

    reg [31:0] cyc;
    reg [63:0] busy_slice_cycles;
    reg [31:0] dispatches;

    localparam D_IDLE = 2'd0, D_FIND = 2'd1, D_LAUNCH = 2'd2;
    reg [1:0]  dstate;
    reg [15:0] cur_tid, cur_code;
    reg [2:0]  cur_lw;
    reg [5:0]  cand;

    wire [5:0]  cur_w   = 6'd1 << cur_lw;
    wire [63:0] cur_gm  = (64'd1 << cur_w) - 64'd1;

    // one-cycle search: lowest aligned free group for the current descriptor
    reg        fit_found;
    reg [5:0]  fit_base;
    integer    b;
    always @* begin
        fit_found = 1'b0;
        fit_base  = 6'd0;
        for (b = S - 1; b >= 0; b = b - 1) begin
            if (((b & (cur_w - 1)) == 0) && (b + cur_w <= S) &&
                (((slice_busy >> b) & cur_gm) == 64'd0)) begin
                fit_found = 1'b1;
                fit_base  = b[5:0];
            end
        end
    end

    // completion: lowest leader that is busy and halted
    reg        done_found;
    reg [5:0]  done_idx;
    integer    c;
    always @* begin
        done_found = 1'b0;
        done_idx   = 6'd0;
        for (c = S - 1; c >= 0; c = c - 1)
            if (busy_l[c] && halted_v[c] && halted_q[c] && !start_v[c]) begin done_found = 1'b1; done_idx = c[5:0]; end
    end

    reg [63:0] nb;
    reg [5:0]  wfree;
    integer    pc_i, bb;
    always @(posedge clk) begin
        if (rst) begin
            slice_busy <= 64'd0; busy_l <= {S{1'b0}};
            sq_wr <= 0; sq_rd <= 0; cq_wr <= 0; cyc <= 0; busy_slice_cycles <= 0; dispatches <= 0;
            dstate <= D_IDLE; start_v <= {S{1'b0}}; halted_q <= {S{1'b1}};
            launch_entry <= 0; launch_lw <= 0; cand <= 0;
            cur_tid <= 0; cur_code <= 0; cur_lw <= 0;
        end else begin
            cyc <= cyc + 1;
            halted_q <= halted_v;
            pc_i = 0;
            for (bb = 0; bb < 64; bb = bb + 1) pc_i = pc_i + slice_busy[bb];
            busy_slice_cycles <= busy_slice_cycles + pc_i;

            // host push
            if (h_push) begin
                sq_tid [sq_wr % QD] <= h_tid;
                sq_code[sq_wr % QD] <= h_code;
                sq_lw  [sq_wr % QD] <= h_lw;
                sq_wr <= sq_wr + 1;
            end

            nb = slice_busy;
            start_v <= {S{1'b0}};

            // completion: free one finished core per cycle
            if (done_found) begin
                wfree = 6'd1 << own_lw[done_idx];
                nb = nb & ~(((64'd1 << wfree) - 64'd1) << done_idx);
                busy_l[done_idx] <= 1'b0;
                cq_tid  [cq_wr % QD] <= own_tid[done_idx];
                cq_a0   [cq_wr % QD] <= a0_v[done_idx*32 +: 32];
                cq_start[cq_wr % QD] <= own_start[done_idx];
                cq_end  [cq_wr % QD] <= cyc;
                cq_lw   [cq_wr % QD] <= own_lw[done_idx];
                cq_trap [cq_wr % QD] <= trap_v[done_idx];
                cq_wr <= cq_wr + 1;
            end

            // dispatcher
            case (dstate)
                D_IDLE: if (sq_wr != sq_rd) begin
                    cur_tid  <= sq_tid [sq_rd % QD];
                    cur_code <= sq_code[sq_rd % QD];
                    cur_lw   <= sq_lw  [sq_rd % QD];
                    dstate   <= D_FIND;
                end
                D_FIND: begin
                    if (fit_found) begin cand <= fit_base; dstate <= D_LAUNCH; end
                    // else: head task does not fit yet; search again next cycle (strict FIFO)
                end
                D_LAUNCH: begin
                    nb = nb | (cur_gm << cand);
                    busy_l[cand]    <= 1'b1;
                    own_tid[cand]   <= cur_tid;
                    own_start[cand] <= cyc;
                    own_lw[cand]    <= cur_lw;
                    start_v[cand]   <= 1'b1;
                    launch_entry    <= {14'd0, cur_code, 2'b00};
                    launch_lw       <= cur_lw;
                    sq_rd           <= sq_rd + 1;
                    dispatches      <= dispatches + 1;
                    dstate          <= D_IDLE;
                end
            endcase
            slice_busy <= nb;
        end
    end
endmodule
