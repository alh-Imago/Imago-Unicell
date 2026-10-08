// tb_vix_carrier_new_cores_v1.v -- ledger #1036: the carrier's new cores driven through core_select, end to end: corner (12), cross (13), merge (14), and the adder's optional second output (carry).
// Config convention (as tb_vix_carrier_mul_v1): cfg_d[4:0] = core_select, cfg_d[132:5] = core_config. Run with -DCARRIER=unicell_vix_carrier_v1 or unicell_vix_carrier_v1d.
`timescale 1ns / 1ps
`ifndef CARRIER
`define CARRIER unicell_vix_carrier_v1
`endif
module tb_vix_carrier_new_cores_v1;
    reg clk = 0; always #5 clk = ~clk;
    reg rst = 1;
    localparam [4:0] SEL_ADDER = 5'd1, SEL_CORNER = 5'd12, SEL_CROSS = 5'd13, SEL_MERGE = 5'd14;
    integer errors = 0;
    task check(input cond, input [511:0] label); begin if (!cond) begin $display("FAIL: %0s", label); errors = errors + 1; end else $display("ok: %0s", label); end endtask

    reg cfg = 0; reg [159:0] cfg_d = 0;
    reg [31:0] val_n = 0, val_w = 0; reg pulse_n = 0, pulse_w = 0;
    wire [31:0] dout_e, dout_s, dout_n, dout_w; wire fire_e, fire_s, fire_n, fire_w; wire ack_n, ack_w;
    reg ak_e = 0, ak_s = 0, ak_n = 0, ak_w = 0;
    wire fz_n, fz_s, fz_e, fz_w, po_n, po_s, po_e, po_w; wire [31:0] pdo_n, pdo_s, pdo_e, pdo_w; wire pao_n, pao_s, pao_e, pao_w;

    `CARRIER #(.CELL_ID(16'hC400)) VIX (
        .clk(clk), .rst(rst),
        .active_in_n(1'b1), .active_in_s(1'b0), .active_in_e(1'b0), .active_in_w(1'b0),
        .freeze_in_n(1'b0), .freeze_in_s(1'b0), .freeze_in_e(1'b0), .freeze_in_w(1'b0),
        .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(val_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(val_w),
        .arrived_n(pulse_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(pulse_w),
        .data_out_n(dout_n), .data_out_s(dout_s), .data_out_e(dout_e), .data_out_w(dout_w),
        .fire_n(fire_n), .fire_s(fire_s), .fire_e(fire_e), .fire_w(fire_w),
        .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(ack_n), .ack_out_s(), .ack_out_e(), .ack_out_w(ack_w),
        .ack_in_n(ak_n), .ack_in_s(ak_s), .ack_in_e(ak_e), .ack_in_w(ak_w),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .freeze_out_n(fz_n), .freeze_out_s(fz_s), .freeze_out_e(fz_e), .freeze_out_w(fz_w),
        .program_out_n(po_n), .program_out_s(po_s), .program_out_e(po_e), .program_out_w(po_w),
        .prog_data_out_n(pdo_n), .prog_data_out_s(pdo_s), .prog_data_out_e(pdo_e), .prog_data_out_w(pdo_w),
        .prog_arrived_out_n(pao_n), .prog_arrived_out_s(pao_s), .prog_arrived_out_e(pao_e), .prog_arrived_out_w(pao_w),
        .prog_ack_in_n(1'b0), .prog_ack_in_s(1'b0), .prog_ack_in_e(1'b0), .prog_ack_in_w(1'b0),
        .status_core_select());

    // consumers on every face: take a word on fire (when no ack in flight), ack it for a cycle
    integer ne = 0, ns = 0, nn = 0, nw = 0; reg [31:0] ev [0:7]; reg [31:0] sv [0:7]; reg [31:0] nv [0:7]; reg [31:0] wv [0:7];
    always @(posedge clk) begin
        ak_e <= 0; ak_s <= 0; ak_n <= 0; ak_w <= 0;
        if (fire_e && !ak_e) begin ev[ne] = dout_e; ne = ne + 1; ak_e <= 1; end
        if (fire_s && !ak_s) begin sv[ns] = dout_s; ns = ns + 1; ak_s <= 1; end
        if (fire_n && !ak_n) begin nv[nn] = dout_n; nn = nn + 1; ak_n <= 1; end
        if (fire_w && !ak_w) begin wv[nw] = dout_w; nw = nw + 1; ak_w <= 1; end
        if (pulse_n && ack_n) pulse_n <= 0;
        if (pulse_w && ack_w) pulse_w <= 0;
    end
    task send_n(input [31:0] v); begin val_n = v; pulse_n = 1; repeat (6) @(posedge clk); end endtask
    task send_w(input [31:0] v); begin val_w = v; pulse_w = 1; repeat (6) @(posedge clk); end endtask
    task conf(input [4:0] sel, input [127:0] c);
        begin pulse_n = 0; pulse_w = 0; @(posedge clk); cfg = 1; cfg_d = 160'h0; cfg_d[4:0] = sel; cfg_d[132:5] = c; @(posedge clk); #1 cfg = 0; ne = 0; ns = 0; nn = 0; nw = 0; repeat (3) @(posedge clk); end
    endtask
    initial begin
        #12 rst = 0; @(posedge clk);
        // corner turn 0: N -> E.  (the carrier gives a corner no routing masks: turn = config bit 0)
        conf(SEL_CORNER, 128'h0);
        send_n(32'hA1); repeat (10) @(posedge clk);
        check(ne == 1 && ev[0] == 32'hA1 && ns == 0 && nw == 0, "corner (12), turn 0: N -> E");
        conf(SEL_CORNER, 128'h1);
        send_n(32'hA2); repeat (10) @(posedge clk);
        check(nw == 1 && wv[0] == 32'hA2 && ne == 0, "corner (12), turn 1: N -> W");
        conf(SEL_CROSS, 128'h0);
        send_n(32'hB1); repeat (10) @(posedge clk);
        check(ns == 1 && sv[0] == 32'hB1 && ne == 0 && nw == 0, "cross (13): N -> S straight through");
        // merge: A = N, B = W, result E. config: [5:0] down E, [11:6] up N+W, [13:12] mode
        conf(SEL_MERGE, {114'h0, 2'd3, 6'b001001, 6'b000100});
        send_n(32'h0F); repeat (10) @(posedge clk);
        check(ne == 0, "merge (14) join-or: one half alone does not go out");
        send_w(32'hF0); repeat (10) @(posedge clk);
        check(ne == 1 && ev[0] == 32'hFF, "merge (14) join-or: A|B = FF");
        conf(SEL_MERGE, {114'h0, 2'd1, 6'b001001, 6'b000100});     // B only
        send_n(32'h11); send_w(32'h22); repeat (10) @(posedge clk);
        check(ne == 1 && ev[0] == 32'h22, "merge (14) B only: passes W, never takes N");
        // adder with its second output (carry) routed south: A and B both from N
        conf(SEL_ADDER, (128'h4) | (128'h1 << 6) | (128'h1 << 33) | (128'h2 << 34));       // down E, up N, second_output, second_downstream S
        send_n(32'hFFFFFFFF); send_n(32'h1); repeat (30) @(posedge clk);
        check(ne == 1 && ev[0] == 32'h0 && ns == 1 && sv[0] == 32'h1, "adder (1) second output: sum 0 east, carry 1 south");
        if (errors == 0) $display("PASS: carrier new cores (corner 12, cross 13, merge 14, adder second output) end to end");
        else $display("FAIL: %0d", errors);
        $finish;
    end
    initial begin #400000; $display("FAIL: timeout"); $finish; end
endmodule
