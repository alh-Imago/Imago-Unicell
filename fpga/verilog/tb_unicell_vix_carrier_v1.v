// tb_unicell_vix_carrier_v1.v — the first real testbench for the VIX
// Carrier. Not re-proving each of the 9 cores' own internal logic
// (already separately proven in each one's own dedicated testbench)
// -- proving what's genuinely NEW and carrier-specific: real
// core_select routing, real cross-core ISOLATION (switching away from
// a core genuinely stops it from reacting, checked via a real
// hierarchical probe into its own internal state, not just "the
// output changed"), and command mode's own new external ports
// (freeze_out/program_out/prog_data_out/prog_arrived_out/prog_ack_in)
// genuinely programming a real, separate, EXTERNAL target cell end to
// end through the carrier.
`timescale 1ns / 1ps

module tb_unicell_vix_carrier_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [4:0] SEL_NANO=5'd0, SEL_ADDER=5'd1, SEL_RAM=5'd2, SEL_COMPARE=5'd3,
                      SEL_BRANCH=5'd4, SEL_ACCUM=5'd5, SEL_LATCH=5'd6, SEL_SEQ=5'd7,
                      SEL_COMMAND=5'd8;
    localparam [9:0] TOPO_PASS_A = 10'h000;
    localparam [3:0] DIR_E4 = 4'b0100;
    localparam [2:0] DIR_W3 = 3'd3;

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

    function [31:0] make_word(input [3:0] pid, input [19:0] word);
        make_word = {8'h0, pid, word};
    endfunction

    reg cfg = 0; reg [159:0] cfg_d;
    reg [31:0] val_n = 0; reg pulse_n = 0;
    wire [31:0] dout_e; wire fire_e;
    reg cons_ready = 1'b1; reg cons_ack = 0;
    reg program_in = 0; reg [31:0] prog_data_n = 0; reg prog_arr_n = 0;
    wire prog_ack_n;

    wire fz_n, fz_s, fz_e, fz_w, po_n, po_s, po_e, po_w;
    wire [31:0] pdo_n, pdo_s, pdo_e, pdo_w;
    wire pao_n, pao_s, pao_e, pao_w;
    reg pai_n = 0, pai_s = 0, pai_e = 0, pai_w = 0;

    unicell_vix_carrier_v1 #(.CELL_ID(16'hC000)) VIX (
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
        .program_in(program_in), .program_done(),
        .prog_data_in_n(prog_data_n), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(prog_arr_n), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(prog_ack_n), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .freeze_out_n(fz_n), .freeze_out_s(fz_s), .freeze_out_e(fz_e), .freeze_out_w(fz_w),
        .program_out_n(po_n), .program_out_s(po_s), .program_out_e(po_e), .program_out_w(po_w),
        .prog_data_out_n(pdo_n), .prog_data_out_s(pdo_s), .prog_data_out_e(pdo_e), .prog_data_out_w(pdo_w),
        .prog_arrived_out_n(pao_n), .prog_arrived_out_s(pao_s), .prog_arrived_out_e(pao_e), .prog_arrived_out_w(pao_w),
        .prog_ack_in_n(pai_n), .prog_ack_in_s(pai_s), .prog_ack_in_e(pai_e), .prog_ack_in_w(pai_w),
        .status_core_select()
    );

    // ── A real, separate EXTERNAL target for command mode's own new
    // ports to reach -- command's drive_dir=W means VIX's own west
    // port; TARGET sits west of VIX, so VIX.west <-> TARGET.east. ──
    wire [31:0] tgt_dout_e; wire tgt_fire_e; wire tgt_prog_ack_out_e;
    reg tgt_cons_ready = 1'b1; reg tgt_cons_ack = 0; reg tgt_west_pulse = 0;

    nano_gate_v4 #(.CELL_ID(16'hC001), .ENABLE_DYNAMIC_ROUTING(1'b0)) TARGET (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(1'b0), .cfg_data(128'h0),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'hD00D0000),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(tgt_west_pulse),
        .data_out_n(), .data_out_s(), .data_out_e(tgt_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(tgt_fire_e), .fire_w(),
        .ready_out(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(tgt_cons_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(tgt_cons_ack), .ack_in_w(1'b0),
        .freeze_in(fz_w),
        .hold_in(1'b0), .fb_internal_in(1'b0), .a_reemit_in(1'b0),
        .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(po_w), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(pdo_w), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(pao_w), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(tgt_prog_ack_out_e), .prog_ack_out_w()
    );
    always @(*) pai_w = tgt_prog_ack_out_e;

    task send_arrival(input [31:0] v);
        begin
            val_n = v; pulse_n = 1'b1;
            @(posedge clk); #1;
            pulse_n = 1'b0;
            repeat (2) @(posedge clk); #1;
        end
    endtask

    task select_core(input [4:0] sel);
        begin
            cfg = 1'b1;
            cfg_d = 160'h0;
            cfg_d[4:0] = sel;
            @(posedge clk); #1; cfg = 1'b0;
            repeat (2) @(posedge clk);
        end
    endtask

    task configure_core(input [4:0] sel, input [127:0] core_cfg);
        begin
            cfg = 1'b1;
            cfg_d = 160'h0;
            cfg_d[4:0] = sel;
            cfg_d[132:5] = core_cfg;
            @(posedge clk); #1; cfg = 1'b0;
            repeat (2) @(posedge clk);
        end
    endtask

    initial begin
        $dumpfile("/tmp/tb_unicell_vix_carrier_v1.vcd");
        $dumpvars(0, tb_unicell_vix_carrier_v1);

        #12 rst = 0;
        @(posedge clk); #1;

        // ── NANO: PASS_A, routing E. Real, verified-width construction
        // (128 bits: 58 reserved + routing_mask[6] + 54 gap + topology[10]). ──
        configure_core(SEL_NANO, {58'h0, 6'b000100, 54'h0, TOPO_PASS_A});
        send_arrival(32'hAAAA0000);
        send_arrival(32'hBBBB1111);
        check(fire_e === 1'b1 && dout_e === 32'hAAAA0000,
              "VIX/nano: real core_select=NANO activates and fires correctly");
        cons_ack = 1'b1; @(posedge clk); #1; cons_ack = 1'b0;
        repeat (2) @(posedge clk);

        // ── Real, genuine cross-core ISOLATION check: switch to
        // RAM while nano's own internal a_arrived is still 1 (it just
        // captured 0xAAAA0000 above and hasn't fired again). Confirm
        // via a real hierarchical probe that nano's own internal state
        // genuinely freezes in place -- not just "the external output
        // changed" but "the non-selected core stopped reacting
        // entirely," the real property this carrier exists to provide. ──
        select_core(SEL_RAM);
        // RAM (80 bits: 14 reserved + addon[20] + init_data[32] +
        // load_data_valid[1] + fixed_mode[1] + upstream_mask[6] +
        // downstream_mask[6]). upstream=N, downstream=E, flowing mode.
        configure_core(SEL_RAM, {14'h0, 20'h0, 32'h0, 1'b0, 1'b0, 6'b000001, 6'b000100});
        send_arrival(32'hCCCC2222);   // would have been nano's 2nd real arrival if nano were still selected
        repeat (2) @(posedge clk); #1;
        check(VIX.CORE_NANO.CORE.a_arrived === 1'b0 && VIX.CORE_NANO.CORE.data_reg === 32'hAAAA0000,
              "VIX isolation: nano's own real internal state is genuinely frozen while RAM is selected, not just its output");
        check(fire_e === 1'b1 && dout_e === 32'hCCCC2222,
              "VIX/ram: real core_select=RAM activates and relays correctly while nano stays isolated");
        cons_ack = 1'b1; @(posedge clk); #1; cons_ack = 1'b0;
        repeat (2) @(posedge clk);

        // ── SEQUENCER: doesn't need arrivals, offers value_0 directly.
        // Real, verified-width construction (64 bits: 4 reserved +
        // addon[20] + downstream_mask[6] + seq_len[2] + value_3..1[8
        // each] + value_0[8]). ──
        configure_core(SEL_SEQ, {4'h0, 20'h0, 6'b000100, 2'b00, 8'h0, 8'h0, 8'h0, 8'hFE});
        repeat (3) @(posedge clk); #1;
        check(fire_e === 1'b1 && dout_e === 32'h000000FE,
              "VIX/sequencer: real core_select=SEQ activates and offers value_0 correctly");
        cons_ack = 1'b1; @(posedge clk); #1; cons_ack = 1'b0;
        repeat (2) @(posedge clk);

        // ── COMMAND, programmer mode: drive_dir=W, toggle_pattern=0xF
        // (nano's real COMPLETE), programming the real EXTERNAL
        // TARGET from scratch through the carrier's own new ports.
        // Real, verified-width construction (64 bits: 55 reserved +
        // toggle_pattern[4] + drive_dir[3] + polarity[1] + mode[1]). ──
        configure_core(SEL_COMMAND, {55'h0, 4'hF, DIR_W3, 1'b0, 1'b1});
        repeat (2) @(posedge clk);

        val_n = make_word(4'h0, {10'h0, TOPO_PASS_A}); pulse_n = 1'b1;
        @(posedge clk); #1; pulse_n = 1'b0;
        while (!pao_w) @(posedge clk);
        while (!tgt_prog_ack_out_e) @(posedge clk);
        #1; @(posedge clk); #1;

        val_n = make_word(4'h1, {16'h0, DIR_E4}); pulse_n = 1'b1;
        @(posedge clk); #1; pulse_n = 1'b0;
        while (!pao_w) @(posedge clk);
        while (!tgt_prog_ack_out_e) @(posedge clk);
        #1; @(posedge clk); #1;

        val_n = make_word(4'hF, {19'h0, 1'b1}); pulse_n = 1'b1;
        @(posedge clk); #1; pulse_n = 1'b0;
        while (!pao_w) @(posedge clk);
        while (!tgt_prog_ack_out_e) @(posedge clk);
        #1; @(posedge clk); #1;
        repeat (2) @(posedge clk); #1;

        check(fz_w === 1'b0, "VIX/command: real target freeze released after real COMPLETE, through the carrier's own new ports");

        tgt_west_pulse = 1'b1; @(posedge clk); #1; tgt_west_pulse = 1'b0;
        repeat (2) @(posedge clk); #1;
        tgt_west_pulse = 1'b1; @(posedge clk); #1; tgt_west_pulse = 1'b0;
        repeat (3) @(posedge clk); #1;
        check(tgt_fire_e === 1'b1 && tgt_dout_e === 32'hD00D0000,
              "VIX/command: real functional check -- external TARGET, programmed via the carrier's own command instance, genuinely works");
        tgt_cons_ack = 1'b1; @(posedge clk); #1; tgt_cons_ack = 1'b0;

        if (checks == 6 && errors == 0)
            $display("PASS: unicell_vix_carrier_v1 -- real core_select routing across nano/RAM/sequencer, genuine cross-core isolation confirmed via a real internal-state probe (not just output), and command mode's own new external ports genuinely programming a real, separate external target end to end through the carrier");
        else
            $display("FAIL: checks=%0d errors=%0d", checks, errors);

        $finish;
    end

endmodule
