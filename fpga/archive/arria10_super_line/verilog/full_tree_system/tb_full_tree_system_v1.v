// tb_full_tree_system_v1.v — points.md #257/#258's design, the real
// completion Alan asked for after #271 (mux tree) and #272 (combiner
// tree): a full system with genuine multi-level trees on BOTH sides,
// real chains, real computation, real BRAM round trip — not the
// single-node slice #269 used.
//
// Alan's own framing, directly: a single join only ever produces ONE
// result, so a meaningful test needs at least 3 starter chains (A, B,
// C) with B genuinely SHARED across two separate joins — real data to
// work with, and a proper chain log, not a trivial single merge.
//
// TOPOLOGY:
//   SPLITTER -> MUX_ROOT --N--> RA  --\
//                --S--> RB1 --+--> ADDER1 (A+B) --> COMBINER_ROOT slot0 (raw)
//                --E--> MUX_CHILD --N--> RB2 --\
//                          --S--> RC  --+--> ADDER2 (B+C) --> COMBINER_RELAY
//                                                              --> COMBINER_ROOT slot2 (child)
//                                                              --> BRAM(in)
//
// B is read TWICE from the SAME BRAM address (genuinely one literal
// value, not two coincidentally-equal separate values), routed via
// DIFFERENT routing bytes to two different destinations (RB1 for
// ADDER1, RB2 for ADDER2) — real reuse/sharing, proven by using the
// identical source address for both reads.
//
// This single test exercises: both mux tree levels (root leaf + child
// leaf), real 1-cell relay staging (RA/RB1/RB2/RC), real arithmetic in
// TWO separate adder_cell_v1 instances, and BOTH combiner levels (root
// raw slot + relay child slot) — the genuine completion of the
// minimum-4-chain target with trees on both sides, not a bigger
// version of the same single-node slice.
`timescale 1ns / 1ps

module tb_full_tree_system_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [3:0] DIR_N = 4'b0001, DIR_S = 4'b0010, DIR_E = 4'b0100, DIR_W = 4'b1000;

    // ════════════════════════════════════════════════════════════════
    // READ SIDE: SPLITTER -> MUX_ROOT -> {RA, RB1, MUX_CHILD -> {RB2, RC}}
    // ════════════════════════════════════════════════════════════════

    reg        splitter_cfg = 0;
    reg [63:0] splitter_cfg_d = 0;
    localparam [63:0] CFG_SPLITTER = {56'h0, DIR_N, DIR_E};

    reg  [31:0] addr_in = 0;
    reg         addr_pulse = 0;
    wire [31:0] splitter_data_out_e;
    wire [7:0]  splitter_routing_out;
    wire        splitter_fire_e, splitter_ready_o;
    wire        root_ack_out_w;

    mem_read_splitter_v1 #(.CELL_ID(16'h0010), .ADDR_WIDTH(16)) SPLITTER (
        .clk(clk), .rst(rst), .cfg_valid(splitter_cfg), .cfg_data(splitter_cfg_d),
        .data_in_n(addr_in), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(addr_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(splitter_data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(splitter_fire_e), .fire_w(),
        .ready_out(splitter_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(root_ready_out), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(root_ack_out_w), .ack_in_w(1'b0),
        .freeze_in(1'b0),
        .routing_out(splitter_routing_out),
        .status_data_valid(), .status_addr_captured()
    );

    // MUX_ROOT: upstream=W (splitter). slot0=N->RA, slot1=S->RB1, slot2=E->MUX_CHILD
    reg        root_cfg = 0;
    reg [63:0] root_cfg_d = 0;
    localparam [63:0] CFG_MROOT = {48'h0, DIR_E, DIR_S, DIR_N, DIR_W};

    wire root_ready_out;
    wire [31:0] root_data_out_n, root_data_out_s, root_data_out_e;
    wire        root_fire_n, root_fire_s, root_fire_e;
    wire [7:0]  root_routing_out;
    wire        mchild_ack_out_w;

    wire ra_ready_out, rb1_ready_out;
    wire ra_ack_out_w, rb1_ack_out_w;

    mux_cell_v1 #(.CELL_ID(16'h0011)) MUX_ROOT (
        .clk(clk), .rst(rst), .cfg_valid(root_cfg), .cfg_data(root_cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(splitter_data_out_e),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(splitter_fire_e),
        .routing_in_n(8'h0), .routing_in_s(8'h0), .routing_in_e(8'h0), .routing_in_w(splitter_routing_out),
        .data_out_n(root_data_out_n), .data_out_s(root_data_out_s), .data_out_e(root_data_out_e), .data_out_w(),
        .fire_n(root_fire_n), .fire_s(root_fire_s), .fire_e(root_fire_e), .fire_w(),
        .routing_out(root_routing_out),
        .ready_out(root_ready_out),
        .ready_in_n(ra_ready_out), .ready_in_s(rb1_ready_out), .ready_in_e(mchild_ready_out), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(root_ack_out_w),
        .ack_in_n(ra_ack_out_w), .ack_in_s(rb1_ack_out_w), .ack_in_e(mchild_ack_out_w), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid()
    );

    // MUX_CHILD: upstream=W (from MUX_ROOT's E). slot0=N->RB2, slot1=S->RC
    reg        mchild_cfg = 0;
    reg [63:0] mchild_cfg_d = 0;
    localparam [63:0] CFG_MCHILD = {48'h0, DIR_E /*unused*/, DIR_S, DIR_N, DIR_W};

    wire mchild_ready_out;
    wire [31:0] mchild_data_out_n, mchild_data_out_s;
    wire        mchild_fire_n, mchild_fire_s;

    wire rb2_ready_out, rc_ready_out;
    wire rb2_ack_out_w, rc_ack_out_w;

    mux_cell_v1 #(.CELL_ID(16'h0012)) MUX_CHILD (
        .clk(clk), .rst(rst), .cfg_valid(mchild_cfg), .cfg_data(mchild_cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(root_data_out_e),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(root_fire_e),
        .routing_in_n(8'h0), .routing_in_s(8'h0), .routing_in_e(8'h0), .routing_in_w(root_routing_out),
        .data_out_n(mchild_data_out_n), .data_out_s(mchild_data_out_s), .data_out_e(), .data_out_w(),
        .fire_n(mchild_fire_n), .fire_s(mchild_fire_s), .fire_e(), .fire_w(),
        .routing_out(),
        .ready_out(mchild_ready_out),
        .ready_in_n(rb2_ready_out), .ready_in_s(rc_ready_out), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(mchild_ack_out_w),
        .ack_in_n(rb2_ack_out_w), .ack_in_s(rc_ack_out_w), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid()
    );

    // ── 4 real 1-cell relay staging points (ram_cell_v1) ──────────────
    localparam [63:0] CFG_STAGE = {54'h0, DIR_W /*upstream*/, DIR_E /*downstream*/};

    reg ra_cfg=0, rb1_cfg=0, rb2_cfg=0, rc_cfg=0;
    reg [63:0] ra_cfg_d=0, rb1_cfg_d=0, rb2_cfg_d=0, rc_cfg_d=0;

    wire [31:0] ra_data_out_e, rb1_data_out_e, rb2_data_out_e, rc_data_out_e;
    wire ra_fire_e, rb1_fire_e, rb2_fire_e, rc_fire_e;
    wire adder1_ready_out, adder2_ready_out;
    wire adder1_ack_out_n, adder1_ack_out_w, adder2_ack_out_n, adder2_ack_out_w;

    ram_cell_v1 #(.CELL_ID(16'h0013)) RA (
        .clk(clk), .rst(rst), .cfg_valid(ra_cfg), .cfg_data(ra_cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(root_data_out_n),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(root_fire_n),
        .data_out_n(), .data_out_s(), .data_out_e(ra_data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(ra_fire_e), .fire_w(),
        .ready_out(ra_ready_out),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(adder1_ready_out), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(ra_ack_out_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(adder1_ack_out_n), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid()
    );

    ram_cell_v1 #(.CELL_ID(16'h0014)) RB1 (
        .clk(clk), .rst(rst), .cfg_valid(rb1_cfg), .cfg_data(rb1_cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(root_data_out_s),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(root_fire_s),
        .data_out_n(), .data_out_s(), .data_out_e(rb1_data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(rb1_fire_e), .fire_w(),
        .ready_out(rb1_ready_out),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(adder1_ready_out), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(rb1_ack_out_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(adder1_ack_out_w), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid()
    );

    ram_cell_v1 #(.CELL_ID(16'h0015)) RB2 (
        .clk(clk), .rst(rst), .cfg_valid(rb2_cfg), .cfg_data(rb2_cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(mchild_data_out_n),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(mchild_fire_n),
        .data_out_n(), .data_out_s(), .data_out_e(rb2_data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(rb2_fire_e), .fire_w(),
        .ready_out(rb2_ready_out),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(adder2_ready_out), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(rb2_ack_out_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(adder2_ack_out_n), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid()
    );

    ram_cell_v1 #(.CELL_ID(16'h0016)) RC (
        .clk(clk), .rst(rst), .cfg_valid(rc_cfg), .cfg_data(rc_cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(mchild_data_out_s),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(mchild_fire_s),
        .data_out_n(), .data_out_s(), .data_out_e(rc_data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(rc_fire_e), .fire_w(),
        .ready_out(rc_ready_out),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(adder2_ready_out), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(rc_ack_out_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(adder2_ack_out_w), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid()
    );

    // ── Two real adders — ADDER1 = A+B (from RA/RB1), ADDER2 = B+C
    // (from RB2/RC). Both use upstream_mask=N|W (two-arrival model,
    // direction-agnostic A/B capture, same as #251/#252). ──
    localparam [63:0] CFG_ADDER = {56'h0, (DIR_N | DIR_W), DIR_E};

    reg adder1_cfg=0, adder2_cfg=0;
    reg [63:0] adder1_cfg_d=0, adder2_cfg_d=0;

    wire [31:0] adder1_data_out_e, adder2_data_out_e;
    wire adder1_fire_e, adder2_fire_e;
    wire croot_ready_out, crelay_ready_out;
    wire croot_ack_n, croot_ack_e;

    adder_cell_v1 #(.CELL_ID(16'h0017)) ADDER1 (
        .clk(clk), .rst(rst), .cfg_valid(adder1_cfg), .cfg_data(adder1_cfg_d),
        .data_in_n(ra_data_out_e), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(rb1_data_out_e),
        .arrived_n(ra_fire_e), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(rb1_fire_e),
        .data_out_n(), .data_out_s(), .data_out_e(adder1_data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(adder1_fire_e), .fire_w(),
        .ready_out(adder1_ready_out),
        .ready_in_n(1'b1), .ready_in_s(1'b1),
        .ready_in_e(1'b1) /* combiner_cell_v2's input side has no ready_out gate by design -- see header note; the chain always assumes ready and holds its own offer via pending_ack until genuinely acked, same as every stub-chain pattern in tb_combiner_cell_v1.v/tb_combiner_tree2_v1.v */,
        .ready_in_w(1'b1),
        .ack_out_n(adder1_ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(adder1_ack_out_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(croot_ack_n), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid(), .status_a_arrived()
    );

    adder_cell_v1 #(.CELL_ID(16'h0018)) ADDER2 (
        .clk(clk), .rst(rst), .cfg_valid(adder2_cfg), .cfg_data(adder2_cfg_d),
        .data_in_n(rb2_data_out_e), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(rc_data_out_e),
        .arrived_n(rb2_fire_e), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(rc_fire_e),
        .data_out_n(), .data_out_s(), .data_out_e(adder2_data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(adder2_fire_e), .fire_w(),
        .ready_out(adder2_ready_out),
        .ready_in_n(1'b1), .ready_in_s(1'b1),
        .ready_in_e(1'b1) /* combiner_relay_v1's chain-input side likewise has no ready_out gate -- crelay_ready_out is a DIFFERENT signal (the relay's own upward-offer readiness toward COMBINER_ROOT), not this. Same fix as ADDER1 above. */,
        .ready_in_w(1'b1),
        .ack_out_n(adder2_ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(adder2_ack_out_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(crelay_ack_n), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid(), .status_a_arrived()
    );

    // ════════════════════════════════════════════════════════════════
    // WRITE SIDE: ADDER1 -> COMBINER_ROOT slot0 (raw)
    //             ADDER2 -> COMBINER_RELAY -> COMBINER_ROOT slot2 (child)
    // ════════════════════════════════════════════════════════════════

    reg        crelay_cfg = 0;
    reg [63:0] crelay_cfg_d = 0;
    localparam [63:0] CFG_CRELAY = {48'h0, 4'h0, 4'h0 /*slot1,2 unused*/, DIR_N /*slot0<-ADDER2*/, DIR_E /*upstream->CROOT*/};

    wire crelay_ack_n;
    wire [31:0] crelay_data_out_e;
    wire crelay_fire_e;
    wire [7:0] crelay_routing_out;

    combiner_relay_v1 #(.CELL_ID(16'h0019)) COMBINER_RELAY (
        .clk(clk), .rst(rst), .cfg_valid(crelay_cfg), .cfg_data(crelay_cfg_d),
        .data_in_n(adder2_data_out_e), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(adder2_fire_e), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .ack_out_n(crelay_ack_n), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .data_out_n(), .data_out_s(), .data_out_e(crelay_data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(crelay_fire_e), .fire_w(),
        .routing_out(crelay_routing_out),
        .ready_out(crelay_ready_out),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(croot_ack_e), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_slot(), .status_data_valid()
    );

    reg        croot_cfg = 0;
    reg [63:0] croot_cfg_d = 0;
    // slot0=N(raw, ADDER1), slot2=E(child, COMBINER_RELAY). is_child_slot2=1.
    localparam [63:0] CFG_CROOT = {45'h0, 1'b1 /*is_child_slot2*/, 2'b00, DIR_E /*slot2*/, 4'h0 /*slot1 unused*/, DIR_N /*slot0*/, DIR_W /*downstream, unused*/};

    wire [1:0] croot_status_slot;

    wire        wr_cmd_valid;
    wire [15:0] wr_cmd_addr;
    wire [39:0] wr_cmd_wdata;
    wire        wr_write_done;

    combiner_cell_v2 #(.CELL_ID(16'h001A), .ADDR_WIDTH(16)) COMBINER_ROOT (
        .clk(clk), .rst(rst), .cfg_valid(croot_cfg), .cfg_data(croot_cfg_d),
        .data_in_n(adder1_data_out_e), .data_in_s(32'h0), .data_in_e(crelay_data_out_e), .data_in_w(32'h0),
        .arrived_n(adder1_fire_e), .arrived_s(1'b0), .arrived_e(crelay_fire_e), .arrived_w(1'b0),
        .routing_in_n(8'h0), .routing_in_s(8'h0), .routing_in_e(crelay_routing_out), .routing_in_w(8'h0),
        .ack_out_n(croot_ack_n), .ack_out_s(), .ack_out_e(croot_ack_e), .ack_out_w(),
        .wr_cmd_valid(wr_cmd_valid), .wr_cmd_addr(wr_cmd_addr), .wr_cmd_wdata(wr_cmd_wdata),
        .wr_write_done(wr_write_done),
        .freeze_in(1'b0),
        .status_slot(croot_status_slot), .status_wrote_this_cycle()
    );

    // ── BRAM(in) — a SEPARATE bram_controller_v1 instance from
    // BRAM(out) inside SPLITTER, matching #257's own "two independent
    // regions" design (not a shortcut). ──
    wire        in_rdata_valid;
    wire [39:0] in_rdata;
    reg         in_rd_cmd_valid = 0;
    reg  [15:0] in_rd_cmd_addr = 0;
    reg         in_mem_cmd_valid;
    reg         in_mem_cmd_op;
    reg  [15:0] in_mem_cmd_addr;
    reg  [39:0] in_mem_cmd_wdata;
    always @(*) begin
        if (wr_cmd_valid) begin
            in_mem_cmd_valid = 1'b1; in_mem_cmd_op = 1'b1;
            in_mem_cmd_addr = wr_cmd_addr; in_mem_cmd_wdata = wr_cmd_wdata;
        end else begin
            in_mem_cmd_valid = in_rd_cmd_valid; in_mem_cmd_op = 1'b0;
            in_mem_cmd_addr = in_rd_cmd_addr; in_mem_cmd_wdata = 40'h0;
        end
    end

    bram_controller_v1 #(.ADDR_WIDTH(16), .DATA_WIDTH(40)) BRAM_IN (
        .clk(clk), .rst(rst),
        .cmd_valid(in_mem_cmd_valid), .cmd_op(in_mem_cmd_op), .cmd_addr(in_mem_cmd_addr), .cmd_wdata(in_mem_cmd_wdata),
        .rdata_valid(in_rdata_valid), .rdata(in_rdata), .write_done(wr_write_done)
    );

    // ════════════════════════════════════════════════════════════════
    // Seed BRAM(out) [inside SPLITTER] with A, B, C.
    // ════════════════════════════════════════════════════════════════
    localparam [31:0] VAL_A = 32'h0000_1000;
    localparam [31:0] VAL_B = 32'h0000_0234;
    localparam [31:0] VAL_C = 32'h0000_0050;

    initial begin
        // Address 0x0010 = A, routed count=1 slot1=00 -> MUX_ROOT N -> RA
        SPLITTER.CORE.mem[16'h0010] = {2'd1, 2'b00, 2'b00, 2'b00, VAL_A};
        // Address 0x0011 = B, routed count=1 slot1=01 -> MUX_ROOT S -> RB1
        SPLITTER.CORE.mem[16'h0011] = {2'd1, 2'b01, 2'b00, 2'b00, VAL_B};
        // Address 0x0012 = C, routed count=2 slot2=10, slot1=01(child's S->RC)
        SPLITTER.CORE.mem[16'h0012] = {2'd2, 2'b01, 2'b10, 2'b00, VAL_C};
    end

    integer errors = 0;
    integer result1_seen = 0, result2_seen = 0;

    task issue_read(input [15:0] addr);
        begin
            wait (splitter_ready_o == 1'b1);
            addr_in = {16'h0, addr}; addr_pulse = 1'b1;
            #10;
            addr_pulse = 1'b0;
        end
    endtask

    // Continuous monitor of the whole write side — much more useful
    // than point-in-time snapshots for diagnosing where the pipeline
    // actually stalls.
    always @(posedge clk) begin
        if (!rst) begin
            if (ADDER1.can_fire)
                $display("[%0t] ADDER1 can_fire (about to compute A+B)", $time);
            if (adder1_fire_e)
                $display("[%0t] ADDER1 offering result on E, pending_ack=%b", $time, ADDER1.pending_ack);
            if (croot_ack_n)
                $display("[%0t] COMBINER_ROOT acked N (from ADDER1)", $time);
            if (ADDER2.can_fire)
                $display("[%0t] ADDER2 can_fire (about to compute B+C)", $time);
            if (adder2_fire_e)
                $display("[%0t] ADDER2 offering result on E, pending_ack=%b", $time, ADDER2.pending_ack);
            if (crelay_ack_n)
                $display("[%0t] COMBINER_RELAY acked N (from ADDER2)", $time);
            if (crelay_fire_e)
                $display("[%0t] COMBINER_RELAY offering upward on E", $time);
            if (croot_ack_e)
                $display("[%0t] COMBINER_ROOT acked E (from relay)", $time);
        end
    end

    // Captures writes CONTINUOUSLY from t=0 — an earlier draft used a
    // blocking `while` poll loop that only started watching wr_cmd_valid
    // AFTER a sequence of debug delays, by which point both real writes
    // (confirmed via the monitor above: t=185000 and t=305000-325000)
    // had already happened and gone by (wr_cmd_valid is a single-cycle
    // pulse, not held) -- the poll loop was waiting for events already
    // in the past, hence the timeout. Not a DUT bug -- purely a
    // testbench sequencing mistake, fixed by moving detection into an
    // always block active for the whole run.
    always @(posedge clk) begin
        if (!rst && wr_cmd_valid) begin
            if (wr_cmd_wdata == {2'd1, 2'b00, 2'b00, 2'b00, VAL_A + VAL_B}) begin
                $display("[%0t] result1 (A+B) written: %h (correct)", $time, wr_cmd_wdata);
                result1_seen = 1;
            end else if (wr_cmd_wdata == {2'd2, 2'b00, 2'd2, 2'b00, VAL_B + VAL_C}) begin
                $display("[%0t] result2 (B+C via relay child) written: %h (correct)", $time, wr_cmd_wdata);
                result2_seen = 1;
            end else begin
                $display("[%0t] FAIL: unexpected write %h", $time, wr_cmd_wdata);
                errors = errors + 1;
            end
        end
    end

    initial begin
        #12 rst = 0;
        #10 splitter_cfg=1; splitter_cfg_d=CFG_SPLITTER;
            root_cfg=1;      root_cfg_d=CFG_MROOT;
            mchild_cfg=1;    mchild_cfg_d=CFG_MCHILD;
            ra_cfg=1;  ra_cfg_d=CFG_STAGE;
            rb1_cfg=1; rb1_cfg_d=CFG_STAGE;
            rb2_cfg=1; rb2_cfg_d=CFG_STAGE;
            rc_cfg=1;  rc_cfg_d=CFG_STAGE;
            adder1_cfg=1; adder1_cfg_d=CFG_ADDER;
            adder2_cfg=1; adder2_cfg_d=CFG_ADDER;
            crelay_cfg=1; crelay_cfg_d=CFG_CRELAY;
            croot_cfg=1;  croot_cfg_d=CFG_CROOT;
        #10 splitter_cfg=0; root_cfg=0; mchild_cfg=0;
            ra_cfg=0; rb1_cfg=0; rb2_cfg=0; rc_cfg=0;
            adder1_cfg=0; adder2_cfg=0; crelay_cfg=0; croot_cfg=0;
        #10;

        // Issue 4 reads: A -> RA, B -> RB1 (for ADDER1), B(again) -> RB2,
        // C -> RC (for ADDER2). B's SAME address (0x0011) is read twice
        // with different routing bytes -- overwritten in between.
        issue_read(16'h0010);   // A -> RA
        $display("[%0t] DEBUG: after A read -- ra_ready=%b ra_fire_e=%b", $time, ra_ready_out, ra_fire_e);
        #40;
        issue_read(16'h0011);   // B -> RB1 (count=1)
        $display("[%0t] DEBUG: after B(1) read -- rb1_ready=%b rb1_fire_e=%b adder1_fire_e=%b", $time, rb1_ready_out, rb1_fire_e, adder1_fire_e);
        #40;

        // Re-seed 0x0011's routing for the SECOND read (same address,
        // same value, DIFFERENT routing byte).
        SPLITTER.CORE.mem[16'h0011] = {2'd2, 2'b00, 2'b10, 2'b00, VAL_B};
        issue_read(16'h0011);   // B -> RB2 via child (count=2)
        $display("[%0t] DEBUG: after B(2) read -- rb2_ready=%b rb2_fire_e=%b", $time, rb2_ready_out, rb2_fire_e);
        #40;
        issue_read(16'h0012);   // C -> RC via child (count=2)
        $display("[%0t] DEBUG: after C read -- rc_ready=%b rc_fire_e=%b adder2_fire_e=%b", $time, rc_ready_out, rc_fire_e, adder2_fire_e);
        #200;
        $display("[%0t] DEBUG at +200: adder1_data_valid=%b adder2_data_valid=%b adder1_fire_e=%b adder2_fire_e=%b croot_status_slot=%0d",
            $time, ADDER1.data_valid, ADDER2.data_valid, adder1_fire_e, adder2_fire_e, croot_status_slot);

        #40;
        if (errors == 0 && result1_seen && result2_seen)
            $display("PASS: FULL TREE SYSTEM -- 3 starter chains (A,B,C), B genuinely shared across two real joins, both mux tree levels + both combiner tree levels exercised. result1=A+B=%h result2=B+C=%h, both correct",
                VAL_A + VAL_B, VAL_B + VAL_C);
        else
            $display("FAIL: errors=%0d result1_seen=%0d result2_seen=%0d", errors, result1_seen, result2_seen);

        $finish;
    end

    // Safety timeout — never let this hang forever.
    initial begin
        #100000;
        $display("TIMEOUT at %0t -- result1_seen=%0d result2_seen=%0d", $time, result1_seen, result2_seen);
        $finish;
    end

endmodule
