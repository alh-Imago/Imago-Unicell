// tb_vix_carrier_mul_v1.v — points.md #726: the real, first proof
// that mul (SEL_MUL, the 10th core, #724) genuinely works through VIX
// carrier's own real core_select routing, not just standalone. Real,
// deliberately narrow scope, matching this whole project's own
// established discipline: prove the NEW thing (SEL_MUL routes real
// data through the real multiplier, computes and offers the correct
// low-32-bit product) without re-proving what the four existing VIX
// testbenches (re-run and confirmed passing unchanged alongside this
// one) already cover.
`timescale 1ns / 1ps

module tb_vix_carrier_mul_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [4:0] SEL_MUL = 5'd9;

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

    unicell_vix_carrier_v1 #(.CELL_ID(16'hC300)) VIX (
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

    task configure_mul(input [5:0] routing_mask, input [5:0] upstream_mask);
        begin
            cfg = 1'b1;
            cfg_d = 160'h0;
            cfg_d[4:0] = SEL_MUL;
            cfg_d[132:5] = {58'h0, upstream_mask, routing_mask};
            @(posedge clk); #1; cfg = 1'b0;
            repeat (2) @(posedge clk);
        end
    endtask

    initial begin
        $dumpfile("/tmp/tb_vix_carrier_mul_v1.vcd");
        $dumpvars(0, tb_vix_carrier_mul_v1);

        #12 rst = 0;
        @(posedge clk); #1;

        // ── Case 1: real multiply, no overflow. ──
        configure_mul(6'b000100, 6'b000001);   // route E, listen N
        send_arrival(32'd6);
        send_arrival(32'd7);
        check(fire_e === 1'b1 && dout_e === 32'd42,
              "VIX/mul: real core_select=MUL routes and computes 6*7=42 correctly");
        cons_ack = 1'b1; @(posedge clk); #1; cons_ack = 1'b0;
        repeat (2) @(posedge clk);

        // ── Case 2: real low-32-bit overflow truncation, the same
        // real edge case mul_cell_v4/v4c's own standalone testbenches
        // already confirmed -- proven again here specifically through
        // the carrier's own real routing, not assumed to carry over. ──
        send_arrival(32'h10000);
        send_arrival(32'h10000);
        check(fire_e === 1'b1 && dout_e === 32'h00000000,
              "VIX/mul: real low-32-bit overflow truncation (0x10000 x 0x10000 wraps to 0) through the carrier");

        if (errors == 0)
            $display("PASS: VIX carrier's own real SEL_MUL routing (#726) genuinely works end to end -- the 10th core computes and offers the correct product, including the real overflow-truncation edge case, through the carrier's own external ports");
        else
            $display("FAIL: %0d of %0d checks failed", errors, checks);
        $finish;
    end

endmodule
