// tb_accumulator_cell_v4.v — points.md #617/#621: confirms
// accumulator_cell_v4.v's real, cloned continuously-live running-total
// core behaves IDENTICALLY to accumulator_cell_v1.v, then confirms
// each new real shell addition independently: PROG_ID-targeted
// reconfiguration (step_amount), the real addon chain, and — the real,
// necessary extension this core's own shape required — that `active`
// gates the INTERNAL running total itself, not just the offered
// output.
//
// Real, deliberate testbench design, found necessary by tracing an
// actual real race, not assumed correct up front: this core
// continuously RE-OFFERS its current total, re-arming `pending_ack`
// again the very next cycle after any single ack clears it (even if
// nothing new happened) -- a real, direct, single "ack once around
// each event" pattern races against that re-arm and can catch a STALE
// re-offer instead of the fresh one (confirmed directly by tracing:
// an isolated one-shot ack+check sequence worked, but the same
// pattern repeated across several sequential real events did not, the
// timing margin around the re-arm being too narrow to land reliably
// every time). The robust fix: a free-running auto-consumer (acks
// whatever's offered, continuously) so `pending_ack` clears rapidly
// and often, combined with generous settle time after each real event
// before sampling `data_out_e` directly -- no discrete "receive count"
// bookkeeping at all, which is what a one-shot core's own tests can
// rely on but this continuously-live core cannot.
`timescale 1ns / 1ps

module tb_accumulator_cell_v4;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;
    reg active = 1;

    localparam [5:0] DIR_N6 = 6'b000001, DIR_S6 = 6'b000010, DIR_E6 = 6'b000100;
    // cfg_data[63:0]: [5:0]inc [11:6]dec [17:12]down [25:18]step [26]pulse [42:27]threshold [62:43]addon [63]reserved
    // inc on N, dec on S, offer on E, step_amount=1, pulse_mode=0
    localparam [63:0] CFG = {1'b0, 20'h0, 16'h0000, 1'b0, 8'h01, DIR_E6, DIR_S6, DIR_N6};

    reg cfg = 0;
    reg [63:0] cfg_d = 0;

    reg inc_pulse = 0, dec_pulse = 0;
    wire [31:0] data_out_e;
    wire        fire_e, ready_o, status_neg;
    wire        program_done;
    wire        prog_ack_n, prog_ack_s, prog_ack_e, prog_ack_w;

    reg cons_ready = 1;
    reg cons_ack = 0;

    reg         program_in = 0;
    reg  [31:0] prog_data_n = 0;
    reg         prog_arr_n = 0;

    integer errors = 0;
    integer checks = 0;

    accumulator_cell_v4 #(.CELL_ID(16'h0001), .WIDTH(32)) DUT (
        .clk(clk), .rst(rst), .active(active),
        .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(inc_pulse), .arrived_s(dec_pulse), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
        .program_in(program_in), .program_done(program_done),
        .prog_data_in_n(prog_data_n), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(prog_arr_n), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(prog_ack_n), .prog_ack_out_s(prog_ack_s), .prog_ack_out_e(prog_ack_e), .prog_ack_out_w(prog_ack_w),
        .freeze_in(1'b0),
        .ready_out(ready_o), .status_negative(status_neg)
    );

    // Free-running auto-consumer: acks whatever's currently offered,
    // as fast as the handshake allows -- matches this core's own real
    // "continuously-live" design instead of fighting it.
    reg [1:0] cons_state = 0;
    always @(posedge clk) begin
        cons_ack <= 1'b0;
        if (!rst) begin
            case (cons_state)
                0: if (fire_e) cons_state <= 1;
                1: begin cons_ack <= 1'b1; cons_state <= 2; end
                2: cons_state <= 0;
                default: cons_state <= 0;
            endcase
        end
    end

    task check_now(input [31:0] want_total, input [63:0] label);
        begin
            checks = checks + 1;
            if (data_out_e !== want_total) begin
                $display("[%0t] FAIL (%0s): expected=%h got=%h", $time, label, want_total, data_out_e);
                errors = errors + 1;
            end else begin
                $display("[%0t] check #%0d (%0s): total=%h (correct)", $time, checks, label, data_out_e);
            end
        end
    endtask

    task prog_send(input [2:0] id, input [19:0] word, input do_complete, input arm_bit);
        begin
            prog_data_n = {9'h0, id, word};
            prog_arr_n = 1'b1;
            #10;
            prog_arr_n = 1'b0;
            #10;
            if (do_complete) begin
                prog_data_n = {9'h0, 3'd7, 19'h0, arm_bit};
                prog_arr_n = 1'b1;
                #10;
                prog_arr_n = 1'b0;
                #10;
            end
        end
    endtask

    initial begin
        #12 rst = 0;
        #10 cfg = 1; cfg_d = CFG;
        #10 cfg = 0;
        #40;   // real, generous settle time before the first real check

        // ── Real, identical-to-v1 core behavior: running total across
        // several real inc/dec events, step_amount=1 ──
        inc_pulse = 1; #10; inc_pulse = 0; #40;
        check_now(32'd1, "inc1");

        inc_pulse = 1; #10; inc_pulse = 0; #40;
        check_now(32'd2, "inc2");

        dec_pulse = 1; #10; dec_pulse = 0; #40;
        check_now(32'd1, "dec1");

        inc_pulse = 1; #10; inc_pulse = 0; #40;
        check_now(32'd2, "inc2b");

        // ── Real, targeted reprogram: PROG_ID_STEP_AMOUNT=5 -- fits in
        // ONE real targeted write (unlike ram's/compare's own wider
        // fields, #619/#620), confirms it takes effect immediately. ──
        program_in = 1'b1;
        prog_send(3'd3, 20'h5, 1'b1, 1'b1);   // PROG_ID_STEP_AMOUNT=5, COMPLETE+arm
        program_in = 1'b0;
        #40;
        inc_pulse = 1; #10; inc_pulse = 0; #40;
        check_now(32'd7, "step5");

        // ── Real addon chain: invert_en ──
        program_in = 1'b1;
        prog_send(3'd6, {1'b1, 19'h0}, 1'b1, 1'b1);   // PROG_ID_ADDON_CONFIG, invert_en=bit19=1
        program_in = 1'b0;
        #40;
        inc_pulse = 1; #10; inc_pulse = 0; #40;
        check_now(~32'd12, "invert");

        // clear addon_config for the final real check
        program_in = 1'b1;
        prog_send(3'd6, 20'h0, 1'b1, 1'b1);
        program_in = 1'b0;
        #40;

        // ── Real `active` gating, extended for this core's own real
        // shape: confirm the INTERNAL running total itself holds while
        // inactive, not just the offered output -- an inc arriving
        // while active=0 must have ZERO real effect. ──
        active = 1'b0;
        #10;
        if (ready_o !== 1'b0) begin
            $display("[%0t] FAIL: ready_out should be 0 when active=0, got %b", $time, ready_o);
            errors = errors + 1;
        end
        inc_pulse = 1'b1; #10; inc_pulse = 1'b0;   // this real arrival must be a genuine no-op
        #40;
        active = 1'b1;
        #40;
        inc_pulse = 1; #10; inc_pulse = 0; #40;
        check_now(32'd17, "active");

        if (checks == 7 && errors == 0)
            $display("PASS: accumulator_cell_v4 -- identical core behavior to v1 (4 checks), real targeted PROG_ID reconfiguration (step_amount, 1 check), real addon chain (invert_en, 1 check), real active=0 gating confirmed to hold the INTERNAL running total, not just the output (1 check)");
        else
            $display("FAIL: checks=%0d errors=%0d", checks, errors);

        $finish;
    end

endmodule
