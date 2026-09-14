// tb_vix_carrier_addon_chain_v1.v — points.md #722/#723: the real
// successor to the testbench removed in #721. Proves the shell-level
// addon chain genuinely works end to end NOW THAT the double-
// transformation risk is gone -- every core wired into VIX is a
// _v4c variant (#720), none of which carry their own internal addon
// chain anymore, so whatever transformation is seen at the carrier's
// own external output is unambiguously the SHELL's own chain, not a
// leftover core-level one layered underneath it.
//
// Real, honest scope, matching the removed testbench's own: NANO
// configured as TOPO_PASS_A (passes its own captured input straight
// through), isolating the addon chain's own real effect. Four real
// cases: disabled (genuine no-op), shift right, shift left, and
// nibble_mask+invert together -- the same real coverage the removed
// testbench had, now proven against the corrected, single-chain,
// _v4c-based design.
`timescale 1ns / 1ps

module tb_vix_carrier_addon_chain_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [4:0] SEL_NANO = 5'd0;
    localparam [9:0] TOPO_PASS_A = 10'h000;

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
    wire fz_n, fz_s, fz_e, fz_w, po_n, po_s, po_e, po_w;
    wire [31:0] pdo_n, pdo_s, pdo_e, pdo_w;
    wire pao_n, pao_s, pao_e, pao_w;
    reg pai_n = 0, pai_s = 0, pai_e = 0, pai_w = 0;

    unicell_vix_carrier_v1 #(.CELL_ID(16'hC200)) VIX (
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

    task send_arrival(input [31:0] v);
        begin
            val_n = v; pulse_n = 1'b1;
            @(posedge clk); #1;
            pulse_n = 1'b0;
            repeat (2) @(posedge clk); #1;
        end
    endtask

    // points.md #722: real addon_config/shift_fine fields live at
    // vix_latch[156:135] -- see unicell_vix_carrier_v1.v's own real
    // header for the exact bit allocation (identical to #719's own
    // original allocation; only the application changed).
    task configure_nano_with_addon(
        input [5:0] routing_mask, input [9:0] topology,
        input addon_shift_en, input addon_direction, input [4:0] addon_shift_amt,
        input addon_mask_en, input [7:0] addon_nibble_mask, input addon_invert_en
    );
        reg [19:0] addon_cfg;
        begin
            addon_cfg = 20'h0;
            addon_cfg[14] = addon_shift_en;
            addon_cfg[15] = addon_direction;
            addon_cfg[13:9] = addon_shift_amt;
            addon_cfg[8] = addon_mask_en;
            addon_cfg[7:0] = addon_nibble_mask;
            addon_cfg[19] = addon_invert_en;
            cfg = 1'b1;
            cfg_d = 160'h0;
            cfg_d[4:0] = SEL_NANO;
            cfg_d[132:5] = {58'h0, routing_mask, 54'h0, topology};
            cfg_d[154:135] = addon_cfg;
            cfg_d[156:155] = 2'b00;
            @(posedge clk); #1; cfg = 1'b0;
            repeat (2) @(posedge clk);
        end
    endtask

    initial begin
        $dumpfile("/tmp/tb_vix_carrier_addon_chain_v1.vcd");
        $dumpvars(0, tb_vix_carrier_addon_chain_v1);

        #12 rst = 0;
        @(posedge clk); #1;

        // ── Case 1: addon chain DISABLED -- must be a genuine no-op. ──
        configure_nano_with_addon(6'b000100, TOPO_PASS_A, 1'b0, 1'b0, 5'd0, 1'b0, 8'h0, 1'b0);
        send_arrival(32'hDEADBEEF);
        send_arrival(32'h11111111);
        check(fire_e === 1'b1 && dout_e === 32'hDEADBEEF,
              "VIX addon chain disabled: real pass-through, no leftover core-level transform either");
        cons_ack = 1'b1; @(posedge clk); #1; cons_ack = 1'b0;
        repeat (2) @(posedge clk);

        // ── Case 2: real, nibble-aligned right-shift by 8. ──
        configure_nano_with_addon(6'b000100, TOPO_PASS_A, 1'b1, 1'b1, 5'd8, 1'b0, 8'h0, 1'b0);
        send_arrival(32'hABCD1234);
        send_arrival(32'h11111111);
        check(fire_e === 1'b1 && dout_e === (32'hABCD1234 >> 8),
              "VIX addon chain: real shift_lane right-shift by 8, single chain, no double-transform");
        cons_ack = 1'b1; @(posedge clk); #1; cons_ack = 1'b0;
        repeat (2) @(posedge clk);

        // ── Case 3: real left-shift by 4. ──
        configure_nano_with_addon(6'b000100, TOPO_PASS_A, 1'b1, 1'b0, 5'd4, 1'b0, 8'h0, 1'b0);
        send_arrival(32'h0F0F0F0F);
        send_arrival(32'h11111111);
        check(fire_e === 1'b1 && dout_e === (32'h0F0F0F0F << 4),
              "VIX addon chain: real shift_lane left-shift by 4, single chain, no double-transform");
        cons_ack = 1'b1; @(posedge clk); #1; cons_ack = 1'b0;
        repeat (2) @(posedge clk);

        // ── Case 4: nibble_mask (clear the lowest nibble) + invert
        // together. ──
        configure_nano_with_addon(6'b000100, TOPO_PASS_A, 1'b0, 1'b0, 5'd0, 1'b1, 8'b00000001, 1'b1);
        send_arrival(32'h12345678);
        send_arrival(32'h11111111);
        check(fire_e === 1'b1 && dout_e === ~(32'h12345670),
              "VIX addon chain: real nibble_mask + invert together, single chain, no double-transform");

        if (errors == 0)
            $display("PASS: VIX carrier's own real, single, corrected addon chain (#722) genuinely works end to end with the _v4c cores in place (#720) -- disabled is a real no-op, both shift directions and mask+invert all transform data correctly through the carrier's own external ports, with no double-transformation from any leftover core-level chain");
        else
            $display("FAIL: %0d of %0d checks failed", errors, checks);
        $finish;
    end

endmodule
