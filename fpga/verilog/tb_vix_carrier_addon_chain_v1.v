// tb_vix_carrier_addon_chain_v1.v — points.md #719: the FIRST real
// testbench proving VIX's own newly-ported addon chain actually works,
// not just that it doesn't break anything (that's already covered by
// the three existing VIX testbenches, all re-run and confirmed passing
// unchanged after this port). Deliberately narrow, matching this
// project's own established discipline: prove the NEW thing, don't
// re-prove what's already proven elsewhere.
//
// Real, honest scope for this first proof: NANO configured as
// TOPO_PASS_A (passes its own captured input straight through), so
// any transformation seen at the carrier's own external output is
// unambiguously the ADDON CHAIN's own doing, not the core's own gate
// logic. Two real cases: shift_en asserted (a real, nibble-aligned
// right-shift, matching `lshr`'s own real hardware direction
// convention) and shift_en left OFF (confirming the addon chain is
// a genuine no-op when disabled, not a stuck construction that always
// transforms the data regardless of config -- the same real "prove
// disabled-by-default too" discipline the mask/invert addons already
// established elsewhere in this project).
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

    unicell_vix_carrier_v1 #(.CELL_ID(16'hC100)) VIX (
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

    // points.md #719: real addon_config/shift_fine fields now live at
    // vix_latch[156:135] -- see unicell_vix_carrier_v1.v's own real
    // header for the exact bit allocation. direction/shift_en/
    // shift_amt/lane_cut match #312's own real addon_config[19:0]
    // layout exactly (shift_lane's own real fields at [15],[14],
    // [13:9],[18:16]).
    task configure_nano_with_addon(
        input [5:0] routing_mask, input [9:0] topology,
        input addon_shift_en, input addon_direction, input [4:0] addon_shift_amt
    );
        reg [19:0] addon_cfg;
        begin
            addon_cfg = 20'h0;
            addon_cfg[14] = addon_shift_en;
            addon_cfg[15] = addon_direction;
            addon_cfg[13:9] = addon_shift_amt;
            cfg = 1'b1;
            cfg_d = 160'h0;
            cfg_d[4:0] = SEL_NANO;
            cfg_d[132:5] = {58'h0, routing_mask, 54'h0, topology};
            cfg_d[154:135] = addon_cfg;   // addon_config
            cfg_d[156:155] = 2'b00;       // shift_fine -- unused, nibble-aligned test
            @(posedge clk); #1; cfg = 1'b0;
            repeat (2) @(posedge clk);
        end
    endtask

    // points.md #719: real, direct test of the other two addons this
    // same port wired in -- nibble_mask (addon_config[8]=mask_en,
    // [7:0]=nibble_mask) and invert (addon_config[19]=invert_en),
    // neither exercised by the shift-focused task above.
    task configure_nano_mask_invert(
        input [5:0] routing_mask, input [9:0] topology,
        input mask_en, input [7:0] nibble_mask, input invert_en
    );
        reg [19:0] addon_cfg;
        begin
            addon_cfg = 20'h0;
            addon_cfg[8] = mask_en;
            addon_cfg[7:0] = nibble_mask;
            addon_cfg[19] = invert_en;
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

        // ── Case 1: addon chain DISABLED -- must be a genuine no-op,
        // not a construction that always transforms the data. ──
        configure_nano_with_addon(6'b000100, TOPO_PASS_A, 1'b0, 1'b0, 5'd0);
        send_arrival(32'hDEADBEEF);
        send_arrival(32'h11111111);
        check(fire_e === 1'b1 && dout_e === 32'hDEADBEEF,
              "VIX addon chain disabled: real pass-through, unmodified");
        cons_ack = 1'b1; @(posedge clk); #1; cons_ack = 1'b0;
        repeat (2) @(posedge clk);

        // ── Case 2: real, nibble-aligned right-shift by 8 (lshr's own
        // real hardware direction, matching the compiler's own
        // FieldIR("addon.direction", 1) convention for lshr). ──
        configure_nano_with_addon(6'b000100, TOPO_PASS_A, 1'b1, 1'b1, 5'd8);
        send_arrival(32'hABCD1234);
        send_arrival(32'h11111111);
        check(fire_e === 1'b1 && dout_e === (32'hABCD1234 >> 8),
              "VIX addon chain: real shift_lane right-shift by 8 through the carrier");
        cons_ack = 1'b1; @(posedge clk); #1; cons_ack = 1'b0;
        repeat (2) @(posedge clk);

        // ── Case 3: real left-shift by 4, confirming direction=0
        // works too, not just the one case above. ──
        configure_nano_with_addon(6'b000100, TOPO_PASS_A, 1'b1, 1'b0, 5'd4);
        send_arrival(32'h0F0F0F0F);
        send_arrival(32'h11111111);
        check(fire_e === 1'b1 && dout_e === (32'h0F0F0F0F << 4),
              "VIX addon chain: real shift_lane left-shift by 4 through the carrier");

        // ── Case 4: nibble_mask (clear the lowest nibble, mask bit 0)
        // and invert together -- the other two addons this same port
        // wired in, neither exercised by the shift tests above. ──
        configure_nano_mask_invert(6'b000100, TOPO_PASS_A, 1'b1, 8'b00000001, 1'b1);
        send_arrival(32'h12345678);
        send_arrival(32'h11111111);
        check(fire_e === 1'b1 && dout_e === ~(32'h12345670),
              "VIX addon chain: real nibble_mask + invert through the carrier");

        if (errors == 0)
            $display("PASS: VIX carrier's own newly-ported real addon chain (#719) genuinely works end to end -- disabled is a real no-op, both shift directions transform data correctly through the carrier's own external ports");
        else
            $display("FAIL: %0d of %0d checks failed", errors, checks);
        $finish;
    end

endmodule
