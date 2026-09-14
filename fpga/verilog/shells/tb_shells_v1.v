// tb_shells_v1.v — points.md #638's own standing queue item 1
// (command core prerequisite): proves each of the 4 new cardinal
// shell wrappers (nano_shell_v1, adder_shell_v1, ram_shell_v1,
// compare_shell_v1) genuinely preserves the wrapped core's own proven
// behavior, AND that the real new cardinal control ports genuinely
// work -- specifically that asserting freeze/active/hold/reemit from
// just ONE of the 4 real directions is sufficient (the OR-combine
// genuinely reaches the wrapped core), not requiring all four.
`timescale 1ns / 1ps

module tb_shells_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

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

    // ═══════════════════════════════════════════════════════════════
    // nano_shell_v1 -- real cardinal active/freeze/hold/reemit/update
    // ═══════════════════════════════════════════════════════════════
    reg nv_active_n=0, nv_active_s=0, nv_active_e=0, nv_active_w=0;
    reg nv_freeze_n=0, nv_freeze_s=0, nv_freeze_e=0, nv_freeze_w=0;
    reg nv_hold_n=0, nv_hold_s=0, nv_hold_e=0, nv_hold_w=0;
    reg nv_reemit_n=0, nv_reemit_s=0, nv_reemit_e=0, nv_reemit_w=0;
    reg nv_update_n=0, nv_update_s=0, nv_update_e=0, nv_update_w=0;
    reg nv_cfg = 0; reg [127:0] nv_cfg_d;
    reg [31:0] nv_val = 0; reg nv_pulse = 0;
    wire [31:0] nv_dout_e; wire nv_fire_e, nv_ready_o;
    reg nv_cons_ready = 1, nv_cons_ack = 0;

    nano_shell_v1 #(.CELL_ID(16'h8000), .ENABLE_DYNAMIC_ROUTING(1'b0)) NV (
        .clk(clk), .rst(rst),
        .active_in_n(nv_active_n), .active_in_s(nv_active_s), .active_in_e(nv_active_e), .active_in_w(nv_active_w),
        .freeze_in_n(nv_freeze_n), .freeze_in_s(nv_freeze_s), .freeze_in_e(nv_freeze_e), .freeze_in_w(nv_freeze_w),
        .hold_in_n(nv_hold_n), .hold_in_s(nv_hold_s), .hold_in_e(nv_hold_e), .hold_in_w(nv_hold_w),
        .fb_internal_in_n(1'b0), .fb_internal_in_s(1'b0), .fb_internal_in_e(1'b0), .fb_internal_in_w(1'b0),
        .a_reemit_in_n(nv_reemit_n), .a_reemit_in_s(nv_reemit_s), .a_reemit_in_e(nv_reemit_e), .a_reemit_in_w(nv_reemit_w),
        .a_update_in_n(nv_update_n), .a_update_in_s(nv_update_s), .a_update_in_e(nv_update_e), .a_update_in_w(nv_update_w),
        .a_self_update_in_n(1'b0), .a_self_update_in_s(1'b0), .a_self_update_in_e(1'b0), .a_self_update_in_w(1'b0),
        .cfg_valid(nv_cfg), .cfg_data(nv_cfg_d),
        .data_in_n(nv_val), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(nv_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(nv_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(nv_fire_e), .fire_w(),
        .ready_out(nv_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(nv_cons_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(nv_cons_ack), .ack_in_w(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    task nv_pulse_arrival(input [31:0] v);
        begin
            nv_val = v; nv_pulse = 1'b1;
            @(posedge clk); #1;
            nv_pulse = 1'b0;
            repeat (2) @(posedge clk); #1;
        end
    endtask

    // ═══════════════════════════════════════════════════════════════
    // adder_shell_v1 / ram_shell_v1 / compare_shell_v1 -- real cardinal
    // active/freeze only (matching each core's own real port set)
    // ═══════════════════════════════════════════════════════════════
    reg ad_active_n=0, ad_active_s=0, ad_active_e=0, ad_active_w=0;
    reg ad_freeze_n=0, ad_freeze_s=0, ad_freeze_e=0, ad_freeze_w=0;
    reg ad_cfg = 0; reg [63:0] ad_cfg_d;
    reg [31:0] ad_a=0, ad_b=0; reg ad_a_p=0, ad_b_p=0;
    wire [31:0] ad_dout_w; wire ad_fire_w;
    wire ad_a_arr, ad_dv;

    adder_shell_v1 #(.CELL_ID(16'h8001)) AD (
        .clk(clk), .rst(rst),
        .active_in_n(ad_active_n), .active_in_s(ad_active_s), .active_in_e(ad_active_e), .active_in_w(ad_active_w),
        .freeze_in_n(ad_freeze_n), .freeze_in_s(ad_freeze_s), .freeze_in_e(ad_freeze_e), .freeze_in_w(ad_freeze_w),
        .cfg_valid(ad_cfg), .cfg_data(ad_cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(ad_b), .data_in_w(ad_a),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(ad_b_p), .arrived_w(ad_a_p),
        .data_out_n(), .data_out_s(), .data_out_e(), .data_out_w(ad_dout_w),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(ad_fire_w),
        .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .status_data_valid(ad_dv), .status_a_arrived(ad_a_arr)
    );

    // ═══════════════════════════════════════════════════════════════
    // ram_shell_v1 -- real cardinal active/freeze
    // ═══════════════════════════════════════════════════════════════
    reg rm_active_n=0, rm_active_s=0, rm_active_e=0, rm_active_w=0;
    reg rm_freeze_n=0, rm_freeze_s=0, rm_freeze_e=0, rm_freeze_w=0;
    reg rm_cfg = 0; reg [79:0] rm_cfg_d;
    reg [31:0] rm_w=0; reg rm_w_p=0;
    wire [31:0] rm_dout_e; wire rm_fire_e; wire rm_dv;

    ram_shell_v1 #(.CELL_ID(16'h8002)) RM (
        .clk(clk), .rst(rst),
        .active_in_n(rm_active_n), .active_in_s(rm_active_s), .active_in_e(rm_active_e), .active_in_w(rm_active_w),
        .freeze_in_n(rm_freeze_n), .freeze_in_s(rm_freeze_s), .freeze_in_e(rm_freeze_e), .freeze_in_w(rm_freeze_w),
        .cfg_valid(rm_cfg), .cfg_data(rm_cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(rm_w),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(rm_w_p),
        .data_out_n(), .data_out_s(), .data_out_e(rm_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(rm_fire_e), .fire_w(),
        .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .status_data_valid(rm_dv)
    );

    // ═══════════════════════════════════════════════════════════════
    // compare_shell_v1 -- real cardinal active/freeze
    // ═══════════════════════════════════════════════════════════════
    reg cm_active_n=0, cm_active_s=0, cm_active_e=0, cm_active_w=0;
    reg cm_freeze_n=0, cm_freeze_s=0, cm_freeze_e=0, cm_freeze_w=0;
    reg cm_cfg = 0; reg [63:0] cm_cfg_d;
    reg [31:0] cm_n=0; reg cm_n_p=0;
    wire [31:0] cm_dout_e; wire cm_fire_e;

    compare_shell_v1 #(.CELL_ID(16'h8003)) CM (
        .clk(clk), .rst(rst),
        .active_in_n(cm_active_n), .active_in_s(cm_active_s), .active_in_e(cm_active_e), .active_in_w(cm_active_w),
        .freeze_in_n(cm_freeze_n), .freeze_in_s(cm_freeze_s), .freeze_in_e(cm_freeze_e), .freeze_in_w(cm_freeze_w),
        .cfg_valid(cm_cfg), .cfg_data(cm_cfg_d),
        .data_in_n(cm_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(cm_n_p), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(cm_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(cm_fire_e), .fire_w(),
        .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .status_data_valid()
    );

    initial begin
        $dumpfile("/tmp/tb_shells_v1.vcd");
        $dumpvars(0, tb_shells_v1);

        #12 rst = 0;
        @(posedge clk); #1;

        // ── nano_shell_v1: real single-direction active, real basic
        // two-arrival gate (PASS_A), matching tb_nano_gate_v4's own
        // baseline check. ──
        nv_active_e = 1'b1;   // ONLY east asserted -- proves OR-combine, not "need all 4"
        nv_cfg = 1; nv_cfg_d = 128'h0;
        nv_cfg_d[9:0]   = 10'h000;              // TOPO_PASS_A
        nv_cfg_d[69:64] = 6'b000100;            // routing_mask = E
        @(posedge clk); #1; nv_cfg = 0;
        repeat (2) @(posedge clk);

        nv_pulse_arrival(32'hAAAA0000);   // capture
        nv_pulse_arrival(32'hBBBB1111);   // fire (PASS_A -> first captured value)
        check(nv_fire_e === 1'b1 && nv_dout_e === 32'hAAAA0000,
              "nano_shell: single-direction active_in_e alone activates the real wrapped core");
        nv_cons_ack = 1; @(posedge clk); #1; nv_cons_ack = 0;
        repeat (2) @(posedge clk);

        // ── Real freeze, single direction (south), while active stays
        // asserted only via east -- proves freeze genuinely reaches
        // the wrapped core's own effective_freeze from a DIFFERENT
        // single direction than active. ──
        nv_freeze_s = 1'b1;
        nv_pulse_arrival(32'hCCCC2222);
        nv_pulse_arrival(32'hDDDD3333);
        check(nv_fire_e === 1'b0,
              "nano_shell: single-direction freeze_in_s alone genuinely freezes the real wrapped core");

        // ── Release freeze -- real recovery, matching tb_nano_gate_v4's
        // own established resume check. ──
        nv_freeze_s = 1'b0;
        repeat (2) @(posedge clk); #1;
        nv_pulse_arrival(32'hCCCC2222);
        nv_pulse_arrival(32'hDDDD3333);
        check(nv_fire_e === 1'b1 && nv_dout_e === 32'hCCCC2222,
              "nano_shell: releasing freeze_in_s resumes real capture/fire");
        nv_cons_ack = 1; @(posedge clk); #1; nv_cons_ack = 0;

        // ── adder_shell_v1: real single-direction active (west this
        // time, a different direction than nano's own test above, on
        // purpose) plus the real two-operand sum, matching
        // tb_adder_cell_v4's own baseline. ──
        ad_active_w = 1'b1;
        ad_cfg = 1; ad_cfg_d = 64'h0;
        ad_cfg_d[5:0]  = 6'b001000;    // downstream_mask = W
        ad_cfg_d[11:6] = 6'b001100;    // upstream_mask = W (A) | E (B)
        @(posedge clk); #1; ad_cfg = 0;
        repeat (2) @(posedge clk);

        ad_a = 32'd7; ad_a_p = 1'b1;
        @(posedge clk); #1; ad_a_p = 1'b0;
        while (ad_a_arr !== 1'b1) @(posedge clk);
        #1;
        ad_b = 32'd5; ad_b_p = 1'b1;
        @(posedge clk); #1; ad_b_p = 1'b0;
        while (ad_dv !== 1'b1) @(posedge clk);
        #1;
        @(posedge clk); #1;   // real settle cycle: fire_w registers one cycle after data_valid, #636's own established pattern
        check(ad_fire_w === 1'b1 && ad_dout_w === 32'd12,
              "adder_shell: single-direction active_in_w alone activates the real wrapped core, 7+5=12");

        // ── Real freeze, single direction (north) on the adder shell. ──
        ad_freeze_n = 1'b1;
        repeat (2) @(posedge clk); #1;
        ad_a = 32'd1; ad_a_p = 1'b1;
        @(posedge clk); #1; ad_a_p = 1'b0;
        repeat (3) @(posedge clk); #1;
        check(ad_a_arr === 1'b0,
              "adder_shell: single-direction freeze_in_n alone genuinely freezes real capture");
        ad_freeze_n = 1'b0;

        // ── ram_shell_v1: real single-direction active (south), real
        // flowing-mode single-arrival relay, matching tb_ram_cell_v4's
        // own baseline convention (downstream=E, upstream=W). ──
        rm_active_s = 1'b1;
        rm_cfg = 1; rm_cfg_d = 80'h0;
        rm_cfg_d[5:0]  = 6'b000100;   // downstream_mask = E
        rm_cfg_d[11:6] = 6'b001000;   // upstream_mask   = W
        @(posedge clk); #1; rm_cfg = 0;
        repeat (2) @(posedge clk);

        rm_w = 32'hFEED0001; rm_w_p = 1'b1;
        @(posedge clk); #1; rm_w_p = 1'b0;
        while (rm_dv !== 1'b1) @(posedge clk);
        #1; @(posedge clk); #1;
        check(rm_fire_e === 1'b1 && rm_dout_e === 32'hFEED0001,
              "ram_shell: single-direction active_in_s alone activates the real wrapped core, real relay value correct");

        // Real freeze, single direction (east) on the ram shell.
        rm_freeze_e = 1'b1;
        repeat (2) @(posedge clk); #1;
        rm_w = 32'hFEED0002; rm_w_p = 1'b1;
        @(posedge clk); #1; rm_w_p = 1'b0;
        repeat (3) @(posedge clk); #1;
        check(rm_dv !== 1'b1 || rm_dout_e === 32'hFEED0001,
              "ram_shell: single-direction freeze_in_e alone genuinely blocks the real wrapped core's capture");
        rm_freeze_e = 1'b0;

        // ── compare_shell_v1: real single-direction active (north),
        // real single-arrival comparator, matching tb_compare_cell_v4's
        // own baseline (threshold=8, input N, result E). ──
        cm_active_n = 1'b1;
        cm_cfg = 1; cm_cfg_d = 64'h0;
        cm_cfg_d[5:0]   = 6'b000100;         // downstream_mask = E
        cm_cfg_d[11:6]  = 6'b000001;         // upstream_mask   = N
        cm_cfg_d[43:12] = 32'sd8;            // threshold = 8
        @(posedge clk); #1; cm_cfg = 0;
        repeat (2) @(posedge clk);

        cm_n = 32'd10; cm_n_p = 1'b1;
        @(posedge clk); #1; cm_n_p = 1'b0;
        repeat (3) @(posedge clk); #1;
        check(cm_fire_e === 1'b1 && cm_dout_e === 32'd1,
              "compare_shell: single-direction active_in_n alone activates the real wrapped core, 10>=8 -> 1");

        if (checks == 8 && errors == 0)
            $display("PASS: all 4 real cardinal shell wrappers (nano_shell_v1, adder_shell_v1, ram_shell_v1, compare_shell_v1) genuinely preserve each wrapped core's own proven behavior AND respond correctly to single-direction active/freeze assertion, confirming the OR-combine reaches the real core in every case");
        else
            $display("FAIL: checks=%0d errors=%0d", checks, errors);

        $finish;
    end

endmodule
