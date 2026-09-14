// tb_full_distribution_system_v1.v — the FULL test build Alan asked
// for (2026-08-10): "an out, into chains, fed back to an in, maybe an
// adder... in the middle of a pair of chains, just do some work, then
// read the results back to check." Every core built this session wired
// into one real pipeline:
//
//   BRAM(out) -> mem_read_splitter_v1 -> mux_cell_v1 -> [two 2-cell
//   ram_cell_v1 relay chains] -> adder_cell_v1 (real work: A+B) ->
//   combiner_cell_v1 -> BRAM(in) -> read back and check.
//
// SCOPE NOTE: the OUT-side and IN-side memories are deliberately two
// separate bram_controller_v1 instances here (one embedded inside
// mem_read_splitter_v1.v, one driven directly by combiner_cell_v1.v) —
// matching points.md #257's own "two independent regions, one draining
// OUT, one collecting IN" design, not a limitation. A real
// cross-instance SHARED single memory (#256's own still-open item)
// remains a separate, later task.
`timescale 1ns / 1ps

module tb_full_distribution_system_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [3:0] DIR_N = 4'b0001, DIR_S = 4'b0010, DIR_E = 4'b0100, DIR_W = 4'b1000;

    // ══════════════════════════════════════════════════════════════════
    // OUT SIDE: splitter (address -> real BRAM read -> DATA/ROUTING) ->
    // mux (routes DATA to chain A or chain B based on ROUTING)
    // ══════════════════════════════════════════════════════════════════
    reg        splitter_cfg = 0;
    reg [63:0] splitter_cfg_d = 0;
    localparam [63:0] CFG_SPLITTER = {56'h0, DIR_N, DIR_E};   // addr in N, data out E

    reg  [31:0] addr_in = 0;
    reg         addr_pulse = 0;
    wire [31:0] splitter_data_out_e;
    wire [7:0]  splitter_routing_out;
    wire        splitter_fire_e, splitter_ready_o, mux_ack_out_w;

    mem_read_splitter_v1 #(.CELL_ID(16'h0010), .ADDR_WIDTH(16)) SPLITTER (
        .clk(clk), .rst(rst), .cfg_valid(splitter_cfg), .cfg_data(splitter_cfg_d),
        .data_in_n(addr_in), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(addr_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(splitter_data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(splitter_fire_e), .fire_w(),
        .ready_out(splitter_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(mux_ready_out), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(mux_ack_out_w), .ack_in_w(1'b0),
        .freeze_in(1'b0),
        .routing_out(splitter_routing_out),
        .status_data_valid(), .status_addr_captured()
    );

    reg        mux_cfg = 0;
    reg [63:0] mux_cfg_d = 0;
    // upstream=W (from splitter's E), slot0(00)->N (chain A), slot1(01)->S (chain B)
    localparam [63:0] CFG_MUX = {48'h0, 4'h0 /*slot2 unused*/, DIR_S /*slot1*/, DIR_N /*slot0*/, DIR_W /*upstream*/};

    wire mux_ready_out;
    wire [31:0] mux_data_out_n, mux_data_out_s;
    wire        mux_fire_n, mux_fire_s;

    wire cons_a_ready, cons_a_ack;   // driven by RA1's own ready/ack below —
    wire cons_b_ready, cons_b_ack;   // must be wire, not reg, for continuous assign

    mux_cell_v1 #(.CELL_ID(16'h0011)) MUX (
        .clk(clk), .rst(rst), .cfg_valid(mux_cfg), .cfg_data(mux_cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(splitter_data_out_e),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(splitter_fire_e),
        .routing_in_n(8'h0), .routing_in_s(8'h0), .routing_in_e(8'h0), .routing_in_w(splitter_routing_out),
        .data_out_n(mux_data_out_n), .data_out_s(mux_data_out_s), .data_out_e(), .data_out_w(),
        .fire_n(mux_fire_n), .fire_s(mux_fire_s), .fire_e(), .fire_w(),
        .routing_out(),
        .ready_out(mux_ready_out),
        .ready_in_n(cons_a_ready), .ready_in_s(cons_b_ready), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(mux_ack_out_w),
        .ack_in_n(cons_a_ack), .ack_in_s(cons_b_ack), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid()
    );

    // ══════════════════════════════════════════════════════════════════
    // TWO 2-CELL RELAY CHAINS — genuinely "into chains", not a direct
    // wire — chain A from mux's N output, chain B from mux's S output.
    // ══════════════════════════════════════════════════════════════════
    localparam [63:0] CFG_RELAY = {56'h0, DIR_W, DIR_E};   // upstream=W, downstream=E, every relay cell

    wire [31:0] ra1_data_e, ra2_data_e;
    wire        ra1_fire_e, ra2_fire_e;
    wire        ra1_ready, ra2_ready;
    wire        ra1_ack_w, ra2_ack_w;

    ram_cell_v1 #(.CELL_ID(16'h0012)) RA1 (
        .clk(clk), .rst(rst), .cfg_valid(chain_cfg), .cfg_data(CFG_RELAY),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(mux_data_out_n),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(mux_fire_n),
        .data_out_n(), .data_out_s(), .data_out_e(ra1_data_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(ra1_fire_e), .fire_w(),
        .ready_out(ra1_ready),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(ra2_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(ra1_ack_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ra2_ack_w), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid()
    );
    assign cons_a_ready = ra1_ready;
    assign cons_a_ack   = ra1_ack_w;

    ram_cell_v1 #(.CELL_ID(16'h0013)) RA2 (
        .clk(clk), .rst(rst), .cfg_valid(chain_cfg), .cfg_data(CFG_RELAY),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(ra1_data_e),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(ra1_fire_e),
        .data_out_n(), .data_out_s(), .data_out_e(ra2_data_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(ra2_fire_e), .fire_w(),
        .ready_out(ra2_ready),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(adder_ready_out), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(ra2_ack_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(adder_ack_out_w), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid()
    );

    wire [31:0] rb1_data_e, rb2_data_e;
    wire        rb1_fire_e, rb2_fire_e;
    wire        rb1_ready, rb2_ready;
    wire        rb1_ack_w, rb2_ack_w;

    ram_cell_v1 #(.CELL_ID(16'h0014)) RB1 (
        .clk(clk), .rst(rst), .cfg_valid(chain_cfg), .cfg_data(CFG_RELAY),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(mux_data_out_s),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(mux_fire_s),
        .data_out_n(), .data_out_s(), .data_out_e(rb1_data_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(rb1_fire_e), .fire_w(),
        .ready_out(rb1_ready),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(rb2_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(rb1_ack_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(rb2_ack_w), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid()
    );
    assign cons_b_ready = rb1_ready;
    assign cons_b_ack   = rb1_ack_w;

    ram_cell_v1 #(.CELL_ID(16'h0015)) RB2 (
        .clk(clk), .rst(rst), .cfg_valid(chain_cfg), .cfg_data(CFG_RELAY),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(rb1_data_e),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(rb1_fire_e),
        .data_out_n(), .data_out_s(), .data_out_e(rb2_data_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(rb2_fire_e), .fire_w(),
        .ready_out(rb2_ready),
        .ready_in_n(adder_ready_out_n), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(rb2_ack_w),
        .ack_in_n(adder_ack_out_n), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid()
    );

    reg chain_cfg = 0;

    // ══════════════════════════════════════════════════════════════════
    // THE REAL WORK: adder_cell_v1 combines chain A (arrives W) and
    // chain B (arrives N) -- "an adder in the middle of a pair of
    // chains", exactly as asked.
    // ══════════════════════════════════════════════════════════════════
    reg        adder_cfg = 0;
    reg [63:0] adder_cfg_d = 0;
    localparam [63:0] CFG_ADDER = {56'h0, (DIR_W | DIR_N), DIR_E};   // upstream W|N, downstream E

    wire [31:0] adder_data_out_e;
    wire        adder_fire_e;
    wire        adder_ready_out, adder_ready_out_n;
    wire        adder_ack_out_w, adder_ack_out_n;

    assign adder_ready_out_n = adder_ready_out;   // same cell, one ready_out signal, wired to both feeders

    adder_cell_v1 #(.CELL_ID(16'h0016)) ADDER (
        .clk(clk), .rst(rst), .cfg_valid(adder_cfg), .cfg_data(adder_cfg_d),
        .data_in_n(rb2_data_e), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(ra2_data_e),
        .arrived_n(rb2_fire_e), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(ra2_fire_e),
        .data_out_n(), .data_out_s(), .data_out_e(adder_data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(adder_fire_e), .fire_w(),
        .ready_out(adder_ready_out),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(combiner_slot0_will_ack), .ready_in_w(1'b1),
        .ack_out_n(adder_ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(adder_ack_out_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(combiner_ack_e), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid(), .status_a_arrived()
    );

    // Adder's ready_in_e/ack_in_e are driven by the combiner's own
    // ack_out_w — the combiner is the adder's downstream "chain".
    wire combiner_slot0_will_ack = 1'b1;   // combiner has no separate ready
                                            // signal (per #268's own design
                                            // — chains simply hold their
                                            // offer until acked), so this
                                            // is always "ready" from the
                                            // adder's perspective; real
                                            // pacing comes from the
                                            // combiner's own round-robin.
    wire combiner_ack_e;

    // ══════════════════════════════════════════════════════════════════
    // IN SIDE: combiner collects the adder's result (its only real
    // input channel, slot0) and writes it back to its OWN BRAM.
    // ══════════════════════════════════════════════════════════════════
    reg        combiner_cfg = 0;
    reg [63:0] combiner_cfg_d = 0;
    // slot0 = W (adder's E output arrives on combiner's W input)
    localparam [63:0] CFG_COMBINER = {48'h0, 4'h0 /*slot2*/, 4'h0 /*slot1*/, DIR_W /*slot0*/, DIR_E /*downstream, unused*/};

    wire        wr_cmd_valid;
    wire [15:0] wr_cmd_addr;
    wire [39:0] wr_cmd_wdata;
    wire        wr_write_done;

    combiner_cell_v1 #(.CELL_ID(16'h0017), .ADDR_WIDTH(16)) COMBINER (
        .clk(clk), .rst(rst), .cfg_valid(combiner_cfg), .cfg_data(combiner_cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(adder_data_out_e),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(adder_fire_e),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(combiner_ack_e),
        .wr_cmd_valid(wr_cmd_valid), .wr_cmd_addr(wr_cmd_addr), .wr_cmd_wdata(wr_cmd_wdata),
        .wr_write_done(wr_write_done),
        .freeze_in(1'b0), .status_slot(), .status_wrote_this_cycle()
    );

    // The combiner's own IN-side memory (a real, separate
    // bram_controller_v1 instance, per this test's own scope note).
    reg         rd_cmd_valid = 0;
    reg  [15:0] rd_cmd_addr = 0;
    reg         mem_in_cmd_valid, mem_in_cmd_op;
    reg [15:0]  mem_in_cmd_addr;
    reg [39:0]  mem_in_cmd_wdata;
    always @(*) begin
        if (wr_cmd_valid) begin
            mem_in_cmd_valid = 1'b1; mem_in_cmd_op = 1'b1;
            mem_in_cmd_addr = wr_cmd_addr; mem_in_cmd_wdata = wr_cmd_wdata;
        end else begin
            mem_in_cmd_valid = rd_cmd_valid; mem_in_cmd_op = 1'b0;
            mem_in_cmd_addr = rd_cmd_addr; mem_in_cmd_wdata = 40'h0;
        end
    end
    wire        mem_in_rdata_valid;
    wire [39:0] mem_in_rdata;

    bram_controller_v1 #(.ADDR_WIDTH(16), .DATA_WIDTH(40)) MEM_IN (
        .clk(clk), .rst(rst),
        .cmd_valid(mem_in_cmd_valid), .cmd_op(mem_in_cmd_op),
        .cmd_addr(mem_in_cmd_addr), .cmd_wdata(mem_in_cmd_wdata),
        .rdata_valid(mem_in_rdata_valid), .rdata(mem_in_rdata), .write_done(wr_write_done)
    );

    // ══════════════════════════════════════════════════════════════════
    // Seed the OUT-side memory: two operands, A at addr 0x0050 (routed
    // to chain A), B at addr 0x0060 (routed to chain B).
    // ══════════════════════════════════════════════════════════════════
    initial begin
        SPLITTER.CORE.mem[16'h0050] = {2'd1, 2'b00, 4'b0, 32'h0000_1000};   // -> chain A (mux slot0=N)
        SPLITTER.CORE.mem[16'h0060] = {2'd1, 2'b01, 4'b0, 32'h0000_0234};   // -> chain B (mux slot1=S)
    end

    integer errors = 0;

    task issue_read(input [15:0] addr);
        begin
            wait (splitter_ready_o == 1'b1);
            addr_in = {16'h0, addr}; addr_pulse = 1'b1;
            #10;
            addr_pulse = 1'b0;
        end
    endtask

    task check_result(input [15:0] addr, input [39:0] expected, input [255:0] label);
        begin
            @(posedge clk);
            rd_cmd_valid = 1'b1; rd_cmd_addr = addr;
            @(posedge clk);
            rd_cmd_valid = 1'b0;
            #1;
            if (!mem_in_rdata_valid) begin
                $display("FAIL: %0s -- rdata_valid never asserted", label);
                errors = errors + 1;
            end else if (mem_in_rdata !== expected) begin
                $display("FAIL: %0s -- expected=%h got=%h", label, expected, mem_in_rdata);
                errors = errors + 1;
            end else begin
                $display("%0s: %h (correct)", label, mem_in_rdata);
            end
        end
    endtask

    initial begin
        #12 rst = 0;
        #10;
        splitter_cfg = 1; splitter_cfg_d = CFG_SPLITTER;
        mux_cfg      = 1; mux_cfg_d      = CFG_MUX;
        chain_cfg    = 1;
        adder_cfg    = 1; adder_cfg_d    = CFG_ADDER;
        combiner_cfg = 1; combiner_cfg_d = CFG_COMBINER;
        #10;
        splitter_cfg = 0; mux_cfg = 0; chain_cfg = 0; adder_cfg = 0; combiner_cfg = 0;
        #10;

        // Issue both reads — the adder needs BOTH operands before it
        // fires, so both must arrive (order doesn't matter, the adder's
        // own two-arrival capture handles whichever comes first as A).
        issue_read(16'h0050);
        #20;
        issue_read(16'h0060);

        // Let the whole pipeline settle: splitter read -> mux route ->
        // 2-cell relay chains -> adder capture+capture+fire -> combiner
        // capture+write. Generous margin, not tuned to a minimum.
        #400;

        // 0x1000 + 0x234 = 0x1234 -- expected sum, real arithmetic
        // through the whole pipeline, not just a wired-through value.
        check_result(16'h0000, {2'd1, 2'b00, 4'b0, 32'h0000_1234}, "combined result (chain A + chain B via real adder)");

        if (errors == 0)
            $display("PASS: FULL SYSTEM -- BRAM(out) -> splitter -> mux -> two 2-cell relay chains -> adder_cell_v1 (real 0x1000+0x234=0x1234) -> combiner -> BRAM(in) -> read-back, all correct end to end");
        else
            $display("FAIL: %0d error(s)", errors);

        $finish;
    end

endmodule
