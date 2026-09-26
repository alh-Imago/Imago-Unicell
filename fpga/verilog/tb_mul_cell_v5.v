// tb_mul_cell_v5.v — points.md #853: proves mul_cell_v5's real,
// sequential two-phase delivery (low then high, same shared
// downstream_mask reused twice) and the real blocking requirement
// Alan stated directly: no new operand may be captured until BOTH
// phases of the current wide-mode delivery are done.
`timescale 1ns / 1ps

module tb_mul_cell_v5;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;
    reg active = 1;

    reg cfg = 0;
    reg [63:0] cfg_d = 0;

    localparam [5:0] DIR_N6 = 6'b000001, DIR_S6 = 6'b000010, DIR_E6 = 6'b000100;
    // cfg_data[63:0]: [5:0]down(E) [11:6]up(N|S) [12]wide_mode [63:13]reserved
    localparam [63:0] CFG_LOW_ONLY = {51'h0, 1'b0, (DIR_N6 | DIR_S6), DIR_E6};
    localparam [63:0] CFG_WIDE     = {51'h0, 1'b1, (DIR_N6 | DIR_S6), DIR_E6};

    reg  [31:0] opA = 0, opB = 0;
    reg         pulse_a = 0, pulse_b = 0;

    wire [31:0] product_out_e;
    wire        fire_e;
    wire        ready_o;
    wire        status_dv, status_aa;

    reg cons_ready = 1;
    reg cons_ack   = 0;

    mul_cell_v5 #(.CELL_ID(16'h000C)) DUT (
        .clk(clk), .rst(rst), .active(active),
        .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(opA), .data_in_s(opB), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(pulse_a), .arrived_s(pulse_b), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(product_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
        .ready_out(ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .freeze_in(1'b0),
        .status_data_valid(status_dv), .status_a_arrived(status_aa)
    );

    integer errors = 0;
    integer checks = 0;
    reg [63:0] expected_full;

    task check(input cond, input [255:0] label);
        begin
            checks = checks + 1;
            if (!cond) begin
                $display("[t=%0t] FAIL: %0s", $time, label);
                errors = errors + 1;
            end else begin
                $display("[t=%0t] check #%0d OK: %0s", $time, checks, label);
            end
        end
    endtask

    task send_pair(input [31:0] a_val, input [31:0] b_val);
        begin
            expected_full = {32'h0, a_val} * {32'h0, b_val};
            opA = a_val; pulse_a = 1'b1;
            #10;
            pulse_a = 1'b0;
            wait (status_aa == 1'b1);
            #10;
            opB = b_val; pulse_b = 1'b1;
            #10;
            pulse_b = 1'b0;
        end
    endtask

    task ack_once;
        begin
            cons_ack = 1'b1;
            #2;   // real, necessary settle: without this, setting cons_ack immediately
                  // before @(posedge clk) can land in the same simulation timestep as
                  // the edge itself, making evaluation order against the DUT's own
                  // always block ambiguous -- found by tracing a real, otherwise
                  // inexplicable mismatch between RTL-internal and testbench-observed state.
            @(posedge clk); #1;
            cons_ack = 1'b0;
            repeat (2) @(posedge clk);
        end
    endtask

    initial begin
        #2000;
        $display("WATCHDOG: simulation did not finish in time -- likely a real hang, not just a slow test");
        $finish;
    end

    initial begin
        #12 rst = 0;

        // ══════════════════════════════════════════════════════════
        // Part 1: wide_mode=0 -- must be byte-for-byte v4 behaviour (v5 is the standalone twin of v5c).
        // ══════════════════════════════════════════════════════════
        #10 cfg = 1; cfg_d = CFG_LOW_ONLY;
        #10 cfg = 0;

        send_pair(32'd5, 32'd7);
        #40;
        check(fire_e === 1'b1, "wide_mode=0: fires exactly like v4");
        check(product_out_e === expected_full[31:0], "wide_mode=0: low-only result matches v4's own truncation");
        ack_once;
        #20;
        check(fire_e === 1'b0, "wide_mode=0: single delivery, done after one ack -- no second phase");

        // ══════════════════════════════════════════════════════════
        // Part 2: wide_mode=1 -- real sequential two-phase delivery.
        // ══════════════════════════════════════════════════════════
        #10 cfg = 1; cfg_d = CFG_WIDE;
        #10 cfg = 0;

        send_pair(24'hC00000, 24'hC00000);   // real FP32-significand-shaped operands (1.5*1.5)
        #40;
        check(fire_e === 1'b1, "wide phase 1: fires");
        check(product_out_e === expected_full[31:0], "wide phase 1: LOW half correct");
        check(ready_o === 1'b0, "wide phase 1: ready_out is LOW -- no new operand may be offered yet");

        ack_once;   // ack phase 1 (low) -- this should trigger phase 2 (high) automatically
        #10;
        check(fire_e === 1'b1, "wide phase 2: fires automatically after phase 1 was acked, with NO new capture in between");
        check(product_out_e === expected_full[63:32], "wide phase 2: HIGH half correct -- the whole point of this entry");
        check(ready_o === 1'b0, "wide phase 2: ready_out STILL low -- second phase not yet acked");

        ack_once;   // ack phase 2 (high) -- NOW the round is genuinely complete
        #10;
        check(fire_e === 1'b0, "wide: fully complete after both phases acked");
        check(ready_o === 1'b1, "wide: ready_out finally returns HIGH only once BOTH phases are done");

        // ══════════════════════════════════════════════════════════
        // Part 3: the real, decisive blocking check Alan stated
        // directly -- attempt to offer a new operand DURING the
        // two-phase window and confirm it is genuinely refused.
        // ══════════════════════════════════════════════════════════
        send_pair(24'hFFFFFF, 24'hFFFFFF);
        #40;
        check(fire_e === 1'b1, "second round: phase 1 fires");
        check(ready_o === 1'b0, "second round: ready_out low during phase 1 -- attempting a new offer now must be refused");
        // Attempt to force a new operand in anyway (as if an upstream
        // cell ignored ready_out) -- confirm the cell genuinely does
        // NOT capture it, since capture_now itself is blocked.
        opA = 32'd999; pulse_a = 1'b1;
        #10;
        pulse_a = 1'b0;
        #10;
        check(product_out_e === expected_full[31:0], "attempted early offer during phase 1 was correctly ignored -- low value unchanged");
        ack_once;
        #10;
        check(product_out_e === expected_full[63:32], "phase 2 (high) still correct despite the attempted early-offer interference");
        ack_once;
        #20;
        check(ready_o === 1'b1, "finally ready again after the real round genuinely completed");

        #20;
        $display("=== tb_mul_cell_v5: %0d checks, %0d errors ===", checks, errors);
        if (errors == 0) $display("ALL CHECKS PASSED");
        else $display("FAILURES DETECTED");
        $finish;
    end

endmodule
