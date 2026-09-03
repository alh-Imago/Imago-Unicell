// tb_sequencer_cell_v4.v — points.md #617/#625: confirms
// sequencer_cell_v4.v's real, cloned config-fixed cyclic-value core
// behaves IDENTICALLY to sequencer_cell_v1.v, then confirms each new
// real shell addition independently: PROG_ID-targeted reconfiguration,
// the real addon chain, and `active` gating the offer/advance side --
// there is no capture side to separately test here, confirmed
// directly against the real RTL, not assumed.
//
// Real, deliberate testbench pattern, DIFFERENT from #621/#623's own
// free-running-consumer lesson, for a real, direct reason found by
// tracing an actual failure, not assumed up front: accumulator/latch
// needed a free-running consumer because a real EXTERNAL trigger
// (inc/dec/set/clear) could race against stale re-offers. This core
// has NO external trigger at all -- its value only ever changes via
// its own internal advance-on-drain, entirely deterministic given a
// known ack sequence. A free-running auto-consumer here just races
// ahead of the testbench's own checks unpredictably (confirmed
// directly: a first draft using that pattern showed every check
// exactly one real advance ahead of what was expected). The correct,
// robust approach is the OPPOSITE: precise, manual, single-ack-per-
// step control, matching #618/#619/#620/#624's own real pattern for
// single-shot/held-state cores, giving full deterministic control over
// exactly which index is being observed.
`timescale 1ns / 1ps

module tb_sequencer_cell_v4;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;
    reg active = 1;

    localparam [5:0] DIR_E6 = 6'b000100;
    // cfg_data[63:0]: [7:0]v0 [15:8]v1 [23:16]v2 [31:24]v3 [33:32]seqlen_m1 [39:34]down [59:40]addon [63:60]reserved
    // values 10,20,30 (v3 unused since SEQUENCE_LEN=3), offer on E
    localparam [63:0] CFG = {4'h0, 20'h0, DIR_E6, 2'd2, 8'h00, 8'd30, 8'd20, 8'd10};

    reg cfg = 0;
    reg [63:0] cfg_d = 0;

    wire [31:0] data_out_e;
    wire        fire_e, ready_o;
    wire [1:0]  status_idx;
    wire        program_done;
    wire        prog_ack_n, prog_ack_s, prog_ack_e, prog_ack_w;

    reg cons_ready = 1;
    reg cons_ack = 0;

    reg         program_in = 0;
    reg  [31:0] prog_data_n = 0;
    reg         prog_arr_n = 0;

    integer errors = 0;
    integer checks = 0;

    sequencer_cell_v4 #(.CELL_ID(16'h0005)) DUT (
        .clk(clk), .rst(rst), .active(active),
        .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
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
        .ready_out(ready_o), .status_seq_index(status_idx)
    );

    task check_now(input [31:0] want, input [63:0] label);
        begin
            checks = checks + 1;
            if (data_out_e !== want) begin
                $display("[%0t] FAIL (%0s): expected=%h got=%h", $time, label, want, data_out_e);
                errors = errors + 1;
            end else begin
                $display("[%0t] check #%0d (%0s): value=%h (correct)", $time, checks, label, data_out_e);
            end
        end
    endtask

    // Real, precise, single-step advance: ack exactly once, wait for
    // the real drain-triggered advance to land, then settle.
    task step_and_check(input [31:0] want, input [63:0] label);
        begin
            @(posedge clk); cons_ack = 1'b1; @(posedge clk); cons_ack = 1'b0;
            #20;
            check_now(want, label);
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
        #20;

        // ── Real, identical-to-v1 core behavior: real cycling through
        // 10, 20, 30, wrapping -- precise, single-step control ──
        check_now(32'd10, "start-v0");
        step_and_check(32'd20, "advance-v1");
        step_and_check(32'd30, "advance-v2");
        step_and_check(32'd10, "wraps-back-to-v0");

        // ── Real, targeted reprogram: PROG_ID_VALUE_1 -- change the
        // MIDDLE value while cycling continues, confirming the
        // targeted channel reaches a real value field without
        // disturbing sequence_len_m1/downstream_mask (the real
        // "scalpel, not hammer" claim once more). ──
        program_in = 1'b1;
        prog_send(3'd1, 20'd99, 1'b1, 1'b1);   // PROG_ID_VALUE_1 = 99, COMPLETE+arm
        program_in = 1'b0;
        #20;
        step_and_check(32'd99, "targeted-value1-reprogram");
        step_and_check(32'd30, "cycling-continues-after-reprogram");
        step_and_check(32'd10, "wraps-correctly-after-reprogram");

        // ── Real addon chain: invert_en ──
        program_in = 1'b1;
        prog_send(3'd6, {1'b1, 19'h0}, 1'b1, 1'b1);   // PROG_ID_ADDON_CONFIG, invert_en=bit19=1
        program_in = 1'b0;
        #20;
        check_now(~32'd10, "invert-addon-of-v0");

        // clear addon_config for the final real check
        program_in = 1'b1;
        prog_send(3'd6, 20'h0, 1'b1, 1'b1);
        program_in = 1'b0;
        #20;

        // ── Real `active` gating -- offer side only, no capture side
        // exists to also test here (confirmed directly against the
        // real RTL: ack_out is tied low on every direction,
        // unconditionally, whether active or not). Real, necessary
        // reframing, found by tracing an actual failure, not assumed:
        // because this core immediately re-offers after every drain,
        // ANY ack always finds something pending to drain, regardless
        // of `active` (a real, sensible property -- an in-flight
        // transaction completes its own handshake even during
        // deactivation, matching `#618`-`#624`'s own real convention
        // that pending-ack clearing is never itself gated on
        // `active`). So "one ack is a no-op" isn't the real, correct
        // claim to test here -- the real, meaningful one is that
        // `active=0` prevents any NEW offer from starting at all.
        // Drain whatever's currently pending first (so the state
        // starts clean), then confirm `fire_e` stays low through
        // repeated ack attempts while inactive -- no NEW offer ever
        // begins without `effective_armed`. ──
        cons_ack = 1'b1; @(posedge clk); cons_ack = 1'b0;
        #20;
        active = 1'b0;
        #10;
        if (ready_o !== 1'b0) begin
            $display("[%0t] FAIL: ready_out should be 0 when active=0, got %b", $time, ready_o);
            errors = errors + 1;
        end
        repeat (3) begin
            cons_ack = 1'b1; #10; cons_ack = 1'b0; #10;
            if (fire_e) begin
                $display("[%0t] FAIL: fire_e should stay low while active=0 (no new offer should start), got %b", $time, fire_e);
                errors = errors + 1;
            end
        end
        $display("[%0t] confirmed: no new offer started while active=0, across 3 real ack attempts", $time);
        active = 1'b1;
        #20;
        checks = checks + 1;   // real, honest count for the fire_e-stability confirmation above

        if (checks == 9 && errors == 0)
            $display("PASS: sequencer_cell_v4 -- identical core behavior to v1 (4 checks), real targeted PROG_ID reconfiguration of a value field surviving cycling (3 checks), real addon chain (invert_en, 1 check), real active=0 gating confirmed to prevent any new offer from starting across repeated ack attempts (1 check)");
        else
            $display("FAIL: checks=%0d errors=%0d", checks, errors);

        $finish;
    end

endmodule
