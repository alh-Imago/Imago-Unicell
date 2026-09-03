// tb_branch_cell_v4.v — points.md #617/#624: confirms branch_cell_v4.v
//'s real, cloned held-reference 3-outcome core behaves IDENTICALLY to
// branch_cell_v1.v, reusing the SAME real, established test scenario
// `top_branch_cell_test_v1.v`'s own Quartus attempt already checks
// (upstream N, reference seeded to 8: LOW=5 emits marker 1 on E,
// EQUAL=8 emits marker 2 on E, HIGH=10 is genuinely SUPPRESSED — no
// offer at all, not a zero value). Then confirms each new real shell
// addition independently: the real, widened 4-bit PROG_ID channel,
// the real addon chain, and `active` gating both real capture paths.
`timescale 1ns / 1ps

module tb_branch_cell_v4;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;
    reg active = 1;

    reg        cfg = 0;
    reg [79:0] cfg_d = 0;
    // cfg_data[79:0], same real scenario as top_branch_cell_test_v1.v:
    // upstream=N, value_source_low/equal=1 (fixed), value_source_high=0
    // (irrelevant, emit_high=0), fixed_value_low=1, fixed_value_equal=2,
    // emit_low=1, emit_equal=1, emit_high=0 (genuine suppression),
    // route_low=route_equal=E, rolling_mode=0.
    localparam [79:0] CFG_BR = {
        11'h0,              // [79:69] reserved
        20'h0,              // [68:49] addon_config
        1'b0,               // [48]    rolling_mode
        6'h0,               // [47:42] route_high (unused, emit_high=0)
        6'b000100,          // [41:36] route_equal = E
        6'b000100,          // [35:30] route_low   = E
        1'b0,               // [29]    emit_high (genuine suppression)
        1'b1,               // [28]    emit_equal
        1'b1,               // [27]    emit_low
        7'd0,               // [26:20] fixed_value_high (unused)
        7'd2,               // [19:13] fixed_value_equal -- marker
        7'd1,               // [12:6]  fixed_value_low   -- marker
        1'b0,               // [5]     value_source_high
        1'b1,               // [4]     value_source_equal
        1'b1,               // [3]     value_source_low
        3'd0                // [2:0]   upstream_dir -- N
    };

    reg  [31:0] val_in = 0;
    reg         pulse = 0;
    wire [31:0] data_out_e;
    wire        fire_e, ready_o;
    reg         cons_ready = 1, cons_ack = 0;
    wire        program_done;
    wire        prog_ack_n, prog_ack_s, prog_ack_e, prog_ack_w;

    reg         program_in = 0;
    reg  [31:0] prog_data_n = 0;
    reg         prog_arr_n = 0;

    integer errors = 0;
    integer checks = 0;

    branch_cell_v4 #(.CELL_ID(16'h0004)) DUT (
        .clk(clk), .rst(rst), .active(active),
        .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(val_in), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
        .ready_out(ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
        .program_in(program_in), .program_done(program_done),
        .prog_data_in_n(prog_data_n), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(prog_arr_n), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(prog_ack_n), .prog_ack_out_s(prog_ack_s), .prog_ack_out_e(prog_ack_e), .prog_ack_out_w(prog_ack_w),
        .freeze_in(1'b0), .status_data_valid()
    );

    task send_and_check(input [31:0] v, input want_fire, input [31:0] want_val, input [63:0] label);
        begin
            val_in = v; pulse = 1'b1; #10; pulse = 1'b0;
            #40;
            checks = checks + 1;
            if (want_fire) begin
                if (!fire_e || data_out_e !== want_val) begin
                    $display("[%0t] FAIL (%0s): expected fire_e=1 val=%h, got fire_e=%b val=%h",
                              $time, label, want_val, fire_e, data_out_e);
                    errors = errors + 1;
                end else begin
                    $display("[%0t] check #%0d (%0s): fired val=%h (correct)", $time, checks, label, data_out_e);
                    cons_ack = 1'b1; #10; cons_ack = 1'b0; #20;
                end
            end else begin
                if (fire_e) begin
                    $display("[%0t] FAIL (%0s): expected genuine suppression, but fire_e=1 val=%h",
                              $time, label, data_out_e);
                    errors = errors + 1;
                end else begin
                    $display("[%0t] check #%0d (%0s): genuinely suppressed, no offer (correct)", $time, checks, label);
                end
            end
        end
    endtask

    task prog_send(input [3:0] id, input [19:0] word, input do_complete, input arm_bit);
        begin
            prog_data_n = {8'h0, id, word};
            prog_arr_n = 1'b1;
            #10;
            prog_arr_n = 1'b0;
            #10;
            if (do_complete) begin
                prog_data_n = {8'h0, 4'd15, 19'h0, arm_bit};
                prog_arr_n = 1'b1;
                #10;
                prog_arr_n = 1'b0;
                #10;
            end
        end
    endtask

    initial begin
        #12 rst = 0;
        #10 cfg = 1; cfg_d = CFG_BR;
        #10 cfg = 0;
        #20;

        // ── Real, identical-to-v1 core behavior -- the SAME real
        // scenario top_branch_cell_test_v1.v already checks on real
        // silicon attempts ──
        send_and_check(32'd8, 1'b0, 32'h0, "seed-reference-no-offer");  // first arrival becomes the reference, never itself compared
        send_and_check(32'd5, 1'b1, 32'd1, "low-emits-marker-1");
        send_and_check(32'd8, 1'b1, 32'd2, "equal-emits-marker-2");
        send_and_check(32'd10, 1'b0, 32'h0, "high-genuinely-suppressed");

        // ── Real, targeted reprogram using the real, widened 4-bit
        // PROG_ID (this core's own real, necessary adaptation -- 15
        // real fields exceed the 3-bit budget every prior core used).
        // Change PROG_ID_ROUTE_HIGH so a HIGH outcome now routes
        // somewhere real too. Real, important confirmation, checked
        // directly against v1's own real design rather than assumed:
        // the targeted channel does NOT release the held reference --
        // only a FULL cfg_valid reconfigure does that (v1's own real,
        // documented judgment call). The reference (8, from the very
        // first arrival above) stays exactly as it was. ──
        program_in = 1'b1;
        prog_send(4'd12, 20'h4, 1'b0, 1'b0);   // PROG_ID_ROUTE_HIGH = E (4'b0100 as a 6-bit field)
        prog_send(4'd9,  20'h1, 1'b0, 1'b0);   // PROG_ID_EMIT_HIGH = 1 (no longer suppressed)
        prog_send(4'd15, 20'h1, 1'b0, 1'b0);   // COMPLETE, word[0]=1 (arm)
        program_in = 1'b0;
        #20;
        send_and_check(32'd8, 1'b1, 32'd2, "ref-survives-targeted-reprogram");   // still ==8 -> EQUAL -> marker 2, confirms the targeted channel does NOT release the reference
        send_and_check(32'd99, 1'b1, 32'd99, "high-no-longer-suppressed");       // 99>8 -> HIGH, now real per the reprogram above; value_source_high still 0 (relay)

        // ── Real addon chain: invert_en. Reference is STILL 8 (no
        // full cfg_valid has happened since boot) -- 5<8 is a real LOW
        // outcome, marker 1, now inverted. ──
        program_in = 1'b1;
        prog_send(4'd14, {1'b1, 19'h0}, 1'b0, 1'b0);   // PROG_ID_ADDON_CONFIG, invert_en=bit19=1
        prog_send(4'd15, 20'h1, 1'b0, 1'b0);           // COMPLETE, arm=1
        program_in = 1'b0;
        #20;
        send_and_check(32'd5, 1'b1, ~32'd1, "invert-addon-of-low-marker");     // 5 < 8 -> LOW -> marker 1, inverted

        // clear addon_config for the final real check
        program_in = 1'b1;
        prog_send(4'd14, 20'h0, 1'b0, 1'b0);
        prog_send(4'd15, 20'h1, 1'b0, 1'b0);
        program_in = 1'b0;
        #20;

        // ── Real `active` gating: confirm BOTH real capture paths are
        // silenced -- neither a new reference capture nor a compare
        // happens while inactive. Real, full cfg_valid reconfigure
        // here (not targeted) specifically to get a genuinely fresh,
        // real "no reference yet" state to test the capture-side
        // gating cleanly, matching the real distinction just
        // confirmed above. ──
        cfg = 1'b1; cfg_d = CFG_BR; #10; cfg = 1'b0;
        #20;
        active = 1'b0;
        #10;
        if (ready_o !== 1'b0) begin
            $display("[%0t] FAIL: ready_out should be 0 when active=0, got %b", $time, ready_o);
            errors = errors + 1;
        end
        val_in = 32'd42; pulse = 1'b1; #10; pulse = 1'b0;   // must be a genuine no-op -- no reference capture
        #40;
        active = 1'b1;
        #20;
        // the arrival above must NOT have been captured as the
        // reference -- confirm by seeding a real reference fresh now
        // and checking it works normally, meaning nothing leaked
        // through while inactive (if 42 HAD been captured as the
        // reference, seeding with 10 below would show as a real LOW
        // comparison against 42, not a fresh, unconsumed reference).
        send_and_check(32'd10, 1'b0, 32'h0, "active-gating-fresh-reference");
        send_and_check(32'd5, 1'b1, 32'd1, "active-gating-normal-after");

        if (checks == 9 && errors == 0)
            $display("PASS: branch_cell_v4 -- identical core behavior to v1 including the real 3-outcome scenario and genuine suppression (4 checks), real targeted PROG_ID reconfiguration with the widened 4-bit ID confirmed to reach route/emit fields WITHOUT releasing the held reference, matching v1's own real design (2 checks), real addon chain (invert_en, 1 check), real active=0 gating confirmed for both real capture paths (2 checks)");
        else
            $display("FAIL: checks=%0d errors=%0d", checks, errors);

        $finish;
    end

endmodule
