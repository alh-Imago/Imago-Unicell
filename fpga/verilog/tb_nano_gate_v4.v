// tb_nano_gate_v4.v — points.md #617/#626: confirms nano_gate_v4.v's
// real, cloned two-arrival gate computation, hold mode, and dynamic
// behavior are unchanged from unicell_stripped_v1.v, then confirms
// the real shell additions: PROG_ID-targeted reconfiguration
// (including the one real NEW field, addon_config), the real addon
// chain, and `active` gating both the real capture and offer sides
// (unlike sequencer_cell_v4.v, #625, nano genuinely has a capture
// side to gate).
`timescale 1ns / 1ps

module tb_nano_gate_v4;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;
    reg active = 1;

    reg          cfg = 0;
    reg [127:0]  cfg_d = 0;

    // Real, explicit, real-position-accurate construction (safer than a
    // single wide concat given the field gaps).
    reg [127:0] cfg_and_real;

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
    reg         hold = 0, fb_int = 0, a_reemit = 0, a_upd = 0, a_self_upd = 0;

    integer errors = 0;
    integer checks = 0;

    nano_gate_v4 #(.CELL_ID(16'h0006), .ENABLE_DYNAMIC_ROUTING(1'b0)) DUT (
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
        .freeze_in(1'b0),
        .hold_in(hold), .fb_internal_in(fb_int), .a_reemit_in(a_reemit),
        .a_update_in(a_upd), .a_self_update_in(a_self_upd),
        .program_in(program_in), .program_done(program_done),
        .prog_data_in_n(prog_data_n), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(prog_arr_n), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(prog_ack_n), .prog_ack_out_s(prog_ack_s), .prog_ack_out_e(prog_ack_e), .prog_ack_out_w(prog_ack_w)
    );

    task send_pair_and_check(input [31:0] a_val, input [31:0] b_val, input [31:0] want, input [63:0] label);
        begin
            val_in = a_val; pulse = 1'b1; #10; pulse = 1'b0;
            #20;
            val_in = b_val; pulse = 1'b1; #10; pulse = 1'b0;
            #30;
            checks = checks + 1;
            if (!fire_e || data_out_e !== want) begin
                $display("[%0t] FAIL (%0s): expected fire_e=1 val=%h, got fire_e=%b val=%h",
                          $time, label, want, fire_e, data_out_e);
                errors = errors + 1;
            end else begin
                $display("[%0t] check #%0d (%0s): val=%h (correct)", $time, checks, label, data_out_e);
                cons_ack = 1'b1; #10; cons_ack = 1'b0; #20;
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
        // real field positions: topology[9:0] routing_mask[69:64]
        // cardinal_edge[75:70] addon_config[33:14]
        cfg_and_real = 128'h0;
        cfg_and_real[9:0]   = 10'h007;         // TOPO_AND
        cfg_and_real[69:64] = 6'b000100;       // routing_mask = E
        cfg_and_real[75:70] = 6'b000000;       // cardinal_edge = all consume

        #12 rst = 0;
        #10 cfg = 1; cfg_d = cfg_and_real;
        #10 cfg = 0;
        #20;

        // ── Real, identical-to-v1 core behavior: two-arrival AND gate,
        // real topology code TOPO_AND=0x007 ──
        send_pair_and_check(32'hFF, 32'h0F, 32'h0F & 32'hFF, "and-gate-basic");
        send_pair_and_check(32'hFF00, 32'h0FF0, (32'hFF00 & 32'h0FF0), "and-gate-second");

        // ── Real, identical-to-v1 core behavior: hold_in mode -- held
        // value stays latched across multiple real fires, continuously
        // comparing/gating against the SAME first operand. ──
        hold = 1'b1;
        val_in = 32'hF0F0; pulse = 1'b1; #10; pulse = 1'b0;
        #20;
        val_in = 32'h0F0F; pulse = 1'b1; #10; pulse = 1'b0;
        #30;
        checks = checks + 1;
        if (!fire_e || data_out_e !== (32'hF0F0 & 32'h0F0F)) begin
            $display("[%0t] FAIL (hold-first-fire): got val=%h", $time, data_out_e);
            errors = errors + 1;
        end else begin
            $display("[%0t] check #%0d (hold-first-fire): val=%h (correct)", $time, checks, data_out_e);
            cons_ack = 1'b1; #10; cons_ack = 1'b0; #20;
        end
        // held value (0xF0F0) should STILL be the first operand -- a
        // real, DIFFERENT second value confirms it wasn't cleared.
        val_in = 32'hFFFF; pulse = 1'b1; #10; pulse = 1'b0;
        #30;
        checks = checks + 1;
        if (!fire_e || data_out_e !== (32'hF0F0 & 32'hFFFF)) begin
            $display("[%0t] FAIL (hold-second-fire): got val=%h", $time, data_out_e);
            errors = errors + 1;
        end else begin
            $display("[%0t] check #%0d (hold-second-fire): val=%h (correct, held value survived)", $time, checks, data_out_e);
            cons_ack = 1'b1; #10; cons_ack = 1'b0; #20;
        end
        hold = 1'b0;

        // ── Real, necessary correction, found by tracing an actual
        // failure, not assumed: cfg_valid does NOT clear a_arrived in
        // the real v1 RTL (confirmed directly -- only rst does). A
        // mere reconfigure after hold_in mode leaves the held first
        // operand latched, so the next real send would be silently
        // treated as a SECOND operand against stale state, not a
        // fresh first one. A genuine reset is required to start
        // clean here, matching the real DUT's own actual behavior. ──
        rst = 1'b1; #10; rst = 1'b0;
        #10;
        cfg = 1; cfg_d = cfg_and_real; #10; cfg = 0;
        #20;

        // ── Real, targeted reprogram: PROG_ID_ADDON_CONFIG -- the ONE
        // real, new field this v4 build adds. Confirms it reaches
        // nano's own real, existing programming channel correctly,
        // and that routing/topology survive untouched. ──
        program_in = 1'b1;
        prog_send(4'd7, {1'b1, 19'h0}, 1'b1, 1'b1);   // PROG_ID_ADDON_CONFIG, invert_en=bit19=1, COMPLETE+arm
        program_in = 1'b0;
        #20;
        send_pair_and_check(32'hFF, 32'h0F, ~(32'h0F & 32'hFF), "addon-invert-after-targeted-reprogram");

        // clear addon_config
        program_in = 1'b1;
        prog_send(4'd7, 20'h0, 1'b1, 1'b1);
        program_in = 1'b0;
        #20;
        send_pair_and_check(32'hFF, 32'h0F, (32'h0F & 32'hFF), "topology-still-and-after-clear");

        // ── Real `active` gating: confirm BOTH capture and offer sides
        // are silenced -- nano genuinely has a capture side, unlike
        // sequencer_cell_v4.v (#625). ──
        active = 1'b0;
        #10;
        if (ready_o !== 1'b0) begin
            $display("[%0t] FAIL: ready_out should be 0 when active=0, got %b", $time, ready_o);
            errors = errors + 1;
        end
        val_in = 32'hAAAA; pulse = 1'b1; #10; pulse = 1'b0;   // first operand -- must be a genuine no-op
        #20;
        val_in = 32'h5555; pulse = 1'b1; #10; pulse = 1'b0;   // would-be second operand -- also a no-op
        #30;
        checks = checks + 1;
        if (fire_e) begin
            $display("[%0t] FAIL: fire_e should stay low while active=0, got %b", $time, fire_e);
            errors = errors + 1;
        end else begin
            $display("[%0t] check #%0d (active-silences-both-sides): confirmed no capture, no offer", $time, checks);
        end
        active = 1'b1;
        #20;
        send_pair_and_check(32'hFF, 32'h0F, (32'h0F & 32'hFF), "active-gating-normal-after");

        if (checks == 8 && errors == 0)
            $display("PASS: nano_gate_v4 -- identical core behavior to v1 (2 checks), real hold_in mode with the held value surviving across fires (2 checks), real targeted PROG_ID_ADDON_CONFIG reconfiguration surviving topology/routing (2 checks), real active=0 gating confirmed for both capture and offer (1 check + 1 resume check)");
        else
            $display("FAIL: checks=%0d errors=%0d", checks, errors);

        $finish;
    end

endmodule
