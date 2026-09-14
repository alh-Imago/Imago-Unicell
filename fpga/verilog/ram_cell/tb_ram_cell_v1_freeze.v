// tb_ram_cell_v1_freeze.v — same R0(FIXED)->R1->R2->consumer chain as
// tb_ram_cell_v1_chain.v, but freezes R1 (the middle cell) mid-run.
// Confirms Alan's point directly: freezing a RAM cell uses the SAME ack
// mechanism the ordinary backpressure cascade already uses (#92), so
// pausing one cell pauses BOTH the chain feeding it (R0 stalls, gets no
// new acks, stays stuck holding its offer) AND the chain it serves (no
// NEW value crosses the frozen cell -- R2 may drain exactly one residual
// value it had already captured before the freeze took hold, which is
// expected and distinct from new data flowing through). Then release and
// confirm the whole chain resumes and drains/refills correctly.
// points.md #236.
`timescale 1ns / 1ps

module tb_ram_cell_v1_freeze;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    reg cfg0=0, cfg1=0, cfg2=0;
    reg [63:0] cfg0_d=0, cfg1_d=0, cfg2_d=0;
    reg r1_freeze = 0;

    localparam [31:0] SRC_VAL = 32'h000000AA;
    localparam [63:0] CFG_R0 = {22'h0, SRC_VAL, 1'b1, 1'b1, 4'b0000, 4'b0100};
    localparam [63:0] CFG_R1 = {22'h0, 32'h0,   1'b0, 1'b0, 4'b1000, 4'b0100};
    localparam [63:0] CFG_R2 = {22'h0, 32'h0,   1'b0, 1'b0, 4'b1000, 4'b0100};

    wire [31:0] r0_dout_e;
    wire        r0_fire_e, r0_ready_o, r0_ack_out_e;
    wire        r1_ready_o, r1_ack_out_w;
    wire [31:0] r1_dout_e;
    wire        r1_fire_e, r1_ack_out_e;
    wire        r2_ready_o, r2_ack_out_w;
    wire [31:0] r2_dout_e;
    wire        r2_fire_e;
    reg         cons_ack = 0;
    reg         cons_ready = 1;
    wire        status0, status1, status2;
    wire        r2_ack_out_e_unused;

    ram_cell_v1 #(.CELL_ID(16'h0000)) R0 (
        .clk(clk), .rst(rst), .cfg_valid(cfg0), .cfg_data(cfg0_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(r0_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(r0_fire_e), .fire_w(),
        .ready_out(r0_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(r1_ready_o), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(r0_ack_out_e), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(r1_ack_out_w), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid(status0)
    );

    ram_cell_v1 #(.CELL_ID(16'h0001)) R1 (
        .clk(clk), .rst(rst), .cfg_valid(cfg1), .cfg_data(cfg1_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(r0_dout_e),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(r0_fire_e),
        .data_out_n(), .data_out_s(), .data_out_e(r1_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(r1_fire_e), .fire_w(),
        .ready_out(r1_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(r2_ready_o), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(r1_ack_out_e), .ack_out_w(r1_ack_out_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(r2_ack_out_w), .ack_in_w(r0_ack_out_e),
        .freeze_in(r1_freeze), .status_data_valid(status1)
    );

    ram_cell_v1 #(.CELL_ID(16'h0002)) R2 (
        .clk(clk), .rst(rst), .cfg_valid(cfg2), .cfg_data(cfg2_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(r1_dout_e),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(r1_fire_e),
        .data_out_n(), .data_out_s(), .data_out_e(r2_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(r2_fire_e), .fire_w(),
        .ready_out(r2_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(r2_ack_out_e_unused), .ack_out_w(r2_ack_out_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(r1_ack_out_e),
        .freeze_in(1'b0), .status_data_valid(status2)
    );

    integer received_count = 0;
    integer errors = 0;
    reg     frozen_window = 0;   // testbench-side marker: true while R1 is frozen
    integer receives_during_freeze = 0;

    reg [1:0] consume_state = 0;
    always @(posedge clk) begin
        cons_ack <= 1'b0;
        if (!rst) begin
            case (consume_state)
                0: if (r2_fire_e) begin
                       if (r2_dout_e !== SRC_VAL) begin
                           $display("[%0t] FAIL: consumer expected %h got %h", $time, SRC_VAL, r2_dout_e);
                           errors = errors + 1;
                       end
                       consume_state <= 1;
                   end
                1: begin
                       cons_ack <= 1'b1;
                       received_count = received_count + 1;
                       if (frozen_window) receives_during_freeze = receives_during_freeze + 1;
                       $display("[%0t] consumer receive #%0d value=%h frozen_window=%b (R0=%b R1=%b R2=%b)",
                                $time, received_count, r2_dout_e, frozen_window, status0, status1, status2);
                       consume_state <= 2;
                   end
                2: consume_state <= 0;
                default: consume_state <= 0;
            endcase
        end
    end

    // The real invariant: R1 must never CAPTURE a new value from R0 while
    // frozen (that's what "upstream stays stalled" actually means). A
    // single residual receive at the consumer right after freeze asserts
    // is EXPECTED and correct -- it's R2 draining a value it already
    // captured from R1 before the freeze took hold (R1 shows data_valid=0
    // at that moment, proving the handoff had already completed prior to
    // freeze), not new data crossing through the frozen cell. Watching
    // status1 for any 0->1 transition during the freeze window is the
    // precise check for "did R1 refill while frozen."
    reg last_status1 = 0;
    integer r1_refilled_during_freeze = 0;
    always @(posedge clk) begin
        if (frozen_window && !last_status1 && status1) r1_refilled_during_freeze = r1_refilled_during_freeze + 1;
        last_status1 <= status1;
    end

    initial begin
        #12 rst = 0;
        #10 cfg0=1; cfg0_d=CFG_R0; cfg1=1; cfg1_d=CFG_R1; cfg2=1; cfg2_d=CFG_R2;
        #10 cfg0=0; cfg1=0; cfg2=0;

        // Let a few consumes happen normally first.
        #150;
        $display("[%0t] --- freezing R1 ---", $time);
        r1_freeze = 1;
        frozen_window = 1;

        // Hold frozen for a while — long enough that, if the cascade were
        // NOT working, several more consumes would have happened.
        #300;

        if (r1_refilled_during_freeze != 0) begin
            $display("FAIL: R1 captured a NEW value from R0 %0d times while frozen — upstream backpressure did not hold", r1_refilled_during_freeze);
            errors = errors + 1;
        end
        if (status0 !== 1'b1) begin
            $display("FAIL: R0.data_valid should still be 1 (stuck, un-drained) while R1 frozen, got %b", status0);
            errors = errors + 1;
        end
        $display("[%0t] during freeze: receives_during_freeze=%0d (1 expected: residual drain already in R2 before freeze) r1_refilled_during_freeze=%0d (must be 0)",
                  $time, receives_during_freeze, r1_refilled_during_freeze);

        $display("[%0t] --- releasing R1 ---", $time);
        r1_freeze = 0;
        frozen_window = 0;

        // Confirm the chain resumes.
        #300;

        if (receives_during_freeze > 1) begin
            $display("FAIL: consumer received %0d values WHILE R1 was frozen (at most 1 residual expected)", receives_during_freeze);
            errors = errors + 1;
        end
        if (received_count < 6) begin
            $display("FAIL: only %0d total receives — chain did not resume properly after unfreeze", received_count);
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS: freeze cascaded correctly both directions (upstream stalled, downstream starved), and the chain resumed cleanly after release. total receives=%0d", received_count);
        else
            $display("FAIL: errors=%0d total_receives=%0d", errors, received_count);

        $finish;
    end

endmodule
