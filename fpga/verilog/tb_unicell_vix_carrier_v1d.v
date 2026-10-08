// tb_unicell_vix_carrier_v1d.v — points.md #841: the real, first
// testbench proving the carrier's own new SEL_ADDON_CONFIG-addressed
// live addon reprogramming actually works -- not re-proving the 9
// cores' own internal logic (already separately proven), and not
// re-proving ordinary core_select routing (already proven by
// tb_unicell_vix_carrier_v1.v) -- proving specifically what's new
// here: (1) addressing the addon block does NOT disturb core_select
// or the active core's own config; (2) a live shift_amt+shift_fine
// reprogram genuinely changes the addon chain's real effect on data
// already flowing through, with no cfg_valid ever reasserted.
`timescale 1ns / 1ps

module tb_unicell_vix_carrier_v1d;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [4:0] SEL_NANO = 5'd0, SEL_ADDON_CONFIG = 5'd11;
    localparam [9:0] TOPO_PASS_A = 10'h000;
    localparam [3:0] DIR_E4 = 4'b0100;   // routing_mask: east

    integer errors = 0;
    integer checks = 0;

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

    reg cfg = 0; reg [159:0] cfg_d;
    reg [31:0] val_n = 0; reg pulse_n = 0;
    wire [31:0] dout_e; wire fire_e;
    reg cons_ready = 1'b1; reg cons_ack = 0;
    reg program_in = 0; reg [31:0] prog_data_n = 0; reg prog_arr_n = 0;
    wire prog_ack_n;
    wire prog_done;

    unicell_vix_carrier_v1d #(.CELL_ID(16'hD000)) VIX (
        .clk(clk), .rst(rst),
        .active_in_n(1'b1), .active_in_s(1'b0), .active_in_e(1'b0), .active_in_w(1'b0),
        .freeze_in_n(1'b0), .freeze_in_s(1'b0), .freeze_in_e(1'b0), .freeze_in_w(1'b0),
        .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(val_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(pulse_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
        .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
        .program_in(program_in), .program_done(prog_done),
        .prog_data_in_n(prog_data_n), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(prog_arr_n), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(prog_ack_n), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .freeze_out_n(), .freeze_out_s(), .freeze_out_e(), .freeze_out_w(),
        .program_out_n(), .program_out_s(), .program_out_e(), .program_out_w(),
        .prog_data_out_n(), .prog_data_out_s(), .prog_data_out_e(), .prog_data_out_w(),
        .prog_arrived_out_n(), .prog_arrived_out_s(), .prog_arrived_out_e(), .prog_arrived_out_w(),
        .prog_ack_in_n(1'b0), .prog_ack_in_s(1'b0), .prog_ack_in_e(1'b0), .prog_ack_in_w(1'b0),
        .status_core_select()
    );

    task send_arrival(input [31:0] v);
        begin
            val_n = v; pulse_n = 1'b1;
            @(posedge clk); #1;
            pulse_n = 1'b0;
            repeat (2) @(posedge clk); #1;
        end
    endtask

    // Real, standing architectural requirement (this project's own
    // "dummy second arrival" pattern, confirmed directly against
    // tb_unicell_vix_carrier_v1.v's own working nano test): nano
    // ALWAYS needs two real arrivals to fire, even for a single-
    // operand passthrough topology. The first captures the real
    // value; the second (any value) is the trigger. The output is the
    // FIRST value, not the second.
    task ack_east;
        begin
            cons_ack = 1'b1; @(posedge clk); #1; cons_ack = 1'b0;
            repeat (2) @(posedge clk);
        end
    endtask

    task send_value_pair(input [31:0] v);
        begin
            send_arrival(v);
            send_arrival(32'hDEAD_BEEF);   // dummy trigger, value irrelevant
        end
    endtask

    // Boots as nano, TOPO_PASS_A, routed to east -- the SAME minimal,
    // already-proven shape tb_unicell_vix_carrier_v1.v's own nano test
    // uses, deliberately not re-testing anything about nano itself.
    reg [127:0] nano_cfg_build;
    task boot_nano_passthrough;
        begin
            // Real nano_gate_v4c.v field map, confirmed directly against
            // its own header before use (NOT the old lineage's [13:10]
            // routing_mask -- this generation's is [69:64], 6 bits):
            // [9:0]=topology, [69:64]=routing_mask, [75:70]=cardinal_edge.
            nano_cfg_build = 128'h0;
            nano_cfg_build[9:0]   = TOPO_PASS_A;
            nano_cfg_build[13]    = 1'b1;        // real, required "ready" arming bit -- confirmed against nano_gate_v4c.v's own header
            nano_cfg_build[69:64] = 6'b000100;   // east, matching DIR_E4's own one-hot bit position
            nano_cfg_build[75:70] = 6'h0;        // cardinal_edge=0: consume from all directions
            cfg = 1'b1;
            cfg_d = 160'h0;
            cfg_d[4:0] = SEL_NANO;
            cfg_d[132:5] = nano_cfg_build;
            @(posedge clk); #1; cfg = 1'b0;
            repeat (2) @(posedge clk);
        end
    endtask

    // Relays one raw 32-bit word into the carrier's receive-side
    // programming channel via the north port -- the SAME real timing
    // shape tb_adder_cell_v4.v's own prog_send already uses at the
    // per-core level, applied here at the carrier's own receive port.
    task relay_word(input [31:0] word);
        begin
            prog_data_n = word;
            prog_arr_n = 1'b1;
            #10;
            prog_arr_n = 1'b0;
            #10;
        end
    endtask

    initial begin
        $dumpfile("/tmp/tb_unicell_vix_carrier_v1d.vcd");
        $dumpvars(0, tb_unicell_vix_carrier_v1d);

        #12 rst = 0;
        boot_nano_passthrough;

        // ── Capture ONE stable value into nano -- a single real
        // two-arrival round, addon left disabled. The addon chain
        // itself (nibble_mask/shift_fine/shift_lane/invert) is pure
        // combinational logic downstream of mux_dout -- no register of
        // its own -- so once this value is held, addon reprogramming
        // can be tested in complete isolation from nano's own fire/ack
        // state machine (a real, separate, pre-existing mechanism this
        // entry has no need to re-exercise repeatedly). Matches this
        // project's own "isolate the variable" discipline directly. ──
        send_value_pair(32'h00001000);
        check(dout_e === 32'h00001000, "baseline passthrough, addon disabled, raw value unchanged");
        check(VIX.core_select === 5'd0, "core_select is nano before any addon addressing");

        // ── Address the carrier's own addon block -- a FRESH
        // programming session whose first word is SEL_ADDON_CONFIG,
        // NOT a real core. Must NOT touch core_select/core_config. ──
        program_in = 1'b1;
        @(posedge clk); #1;   // real, necessary settle: let awaiting_select re-arm before relaying the select word
        relay_word({27'h0, SEL_ADDON_CONFIG});   // first word of a session = pseudo-select

        // Real, targeted reprogram: shift_amt=4 (real, supported coarse
        // tap), direction=1 (SHIFT_OUT/right), shift_en=1 -- via
        // PROG_ID_ADDON_LOCAL_ADDON_CONFIG=0. addon_config[19:0] layout:
        // [7:0]=nibble_mask [8]=mask_en [13:9]=shift_amt [14]=shift_en
        // [15]=direction [18:16]=lane_cut [19]=invert_en (ICM_V3_FORMAT.md).
        relay_word({9'h0, 3'd0, 4'd0, 1'b1, 1'b1, 5'd4, 1'b0, 8'h0});
        // Real, targeted reprogram: shift_fine=2 -- via
        // PROG_ID_ADDON_LOCAL_SHIFT_FINE=1.
        relay_word({9'h0, 3'd1, 18'h0, 2'd2});
        // Terminate the addon-addressing session.
        relay_word({9'h0, 3'd7, 20'h0});
        program_in = 1'b0;
        #20;

        // ── The real, decisive checks. NOTHING sent to nano since the
        // single capture above -- mux_dout is unchanged, still
        // 0x00001000. Any change in dout_e can ONLY come from the
        // addon reprogram just performed, live, with no cfg_valid ever
        // reasserted and no new arrival ever sent. ──
        check(VIX.core_select === 5'd0, "core_select STILL nano -- addon addressing never touched it");
        check(dout_e === (32'h00001000 >> 6), "SAME held value, NEW live shift genuinely applied -- shift_amt=4+shift_fine=2=6, 0x1000>>6=0x40");

        // ── Reprogram AGAIN, to a genuinely DIFFERENT shift amount --
        // proves this is real, repeatable live reconfiguration, not a
        // one-shot fluke or a coincidental match. ──
        program_in = 1'b1;
        @(posedge clk); #1;   // real, necessary settle: let awaiting_select re-arm before relaying the select word
        relay_word({27'h0, SEL_ADDON_CONFIG});
        relay_word({9'h0, 3'd0, 4'd0, 1'b1, 1'b1, 5'd1, 1'b0, 8'h0});   // shift_amt=1 this time
        relay_word({9'h0, 3'd1, 18'h0, 2'd0});                          // shift_fine=0 this time
        relay_word({9'h0, 3'd7, 20'h0});
        program_in = 1'b0;
        #20;

        check(VIX.core_select === 5'd0, "core_select STILL nano after a SECOND addon reprogram");
        check(dout_e === (32'h00001000 >> 1), "a DIFFERENT live shift (amount=1, fine=0) genuinely takes effect -- not stuck at the first reprogram's value");

        #20;
        $display("=== tb_unicell_vix_carrier_v1d: %0d checks, %0d errors ===", checks, errors);
        if (errors == 0) $display("ALL CHECKS PASSED");
        else $display("FAILURES DETECTED");
        $finish;
    end

endmodule
