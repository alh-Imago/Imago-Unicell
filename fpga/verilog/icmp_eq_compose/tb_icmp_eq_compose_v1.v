// tb_icmp_eq_compose_v1.v — real, live investigation for LLVM's
// icmp eq/ne (points.md #614's own real lead: nano's TOPO_AND exists,
// but a cleaner real formula was found here instead, needing no AND
// at all): given comp1=(diff>=0) and comp2=(diff>=1), XOR(comp1,comp2)
// == (diff==0) exactly -- verified case by case: diff<0 -> 0 XOR 0=0;
// diff==0 -> 1 XOR 0=1; diff>0 -> 1 XOR 1=0.
//
// Real topology:
//   DIFF (adder, subtract_mode via negate): A - B -> diff
//   diff multicasts to COMP1 (threshold=0, E) and COMP2 (threshold=1, S)
//   COMP1/COMP2 both feed a real nano_gate XOR cell -> eq result
`timescale 1ns / 1ps

module tb_icmp_eq_compose_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    // ── DIFF: adder, computes A + (-B) = A - B ──
    reg cfg_diff = 0; reg [63:0] cfg_d_diff;
    reg [31:0] a_val = 0, negb_val = 0;
    reg a_pulse = 0, negb_pulse = 0;
    wire [31:0] diff_dout_e, diff_dout_s; wire diff_fire_e, diff_fire_s;
    wire c1_ready, c2_ready;
    wire c1_ack, c2_ack;

    localparam [5:0] DIR_N6=6'b000001, DIR_S6=6'b000010, DIR_E6=6'b000100, DIR_W6=6'b001000;

    adder_cell_v4 #(.CELL_ID(16'h4000)) DIFF (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfg_diff), .cfg_data(cfg_d_diff),
        .data_in_n(negb_val), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(a_val),
        .arrived_n(negb_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(a_pulse),
        .data_out_n(), .data_out_s(diff_dout_s), .data_out_e(diff_dout_e), .data_out_w(),
        .fire_n(), .fire_s(diff_fire_s), .fire_e(diff_fire_e), .fire_w(),
        .ready_out(),
        .ready_in_n(1'b1), .ready_in_s(c2_ready), .ready_in_e(c1_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(c2_ack), .ack_in_e(c1_ack), .ack_in_w(1'b0),
        .freeze_in(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .status_data_valid(), .status_a_arrived()
    );

    // ── COMP1: threshold=0, receives diff via W ──
    reg cfg_c1 = 0; reg [63:0] cfg_d_c1;
    wire [31:0] c1_dout_e; wire c1_fire_e;
    wire xg_ready_n;
    wire xg_ack_n;

    compare_cell_v4 #(.CELL_ID(16'h4001)) COMP1 (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfg_c1), .cfg_data(cfg_d_c1),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(diff_dout_e),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(diff_fire_e),
        .data_out_n(), .data_out_s(), .data_out_e(c1_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(c1_fire_e), .fire_w(),
        .ready_out(c1_ready),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(xg_ready_n), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(c1_ack),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(xg_ack_n), .ack_in_w(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .freeze_in(1'b0), .status_data_valid()
    );

    // ── COMP2: threshold=1, receives diff via N (from DIFF's own S) ──
    reg cfg_c2 = 0; reg [63:0] cfg_d_c2;
    wire [31:0] c2_dout_e; wire c2_fire_e;
    wire xg_ready_w;
    wire xg_ack_w;

    compare_cell_v4 #(.CELL_ID(16'h4002)) COMP2 (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfg_c2), .cfg_data(cfg_d_c2),
        .data_in_n(diff_dout_s), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(diff_fire_s), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(c2_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(c2_fire_e), .fire_w(),
        .ready_out(c2_ready),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(xg_ready_w), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(c2_ack),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(xg_ack_w), .ack_in_w(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .freeze_in(1'b0), .status_data_valid()
    );

    // ── XOR-gate: real nano_gate, comp1 on N, comp2 on W ──
    reg cfg_xg = 0; reg [127:0] cfg_d_xg;
    wire [31:0] result_out; wire result_fire;
    reg cons_ready=1, cons_ack=0;

    localparam [9:0] TOPO_XOR = 10'h0BC;

    nano_gate_v4 #(.CELL_ID(16'h4003), .ENABLE_DYNAMIC_ROUTING(1'b0)) XORGATE (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfg_xg), .cfg_data(cfg_d_xg),
        .data_in_n(c1_dout_e), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(c2_dout_e),
        .arrived_n(c1_fire_e), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(c2_fire_e),
        .data_out_n(), .data_out_s(), .data_out_e(result_out), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(result_fire), .fire_w(),
        .ready_out(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(xg_ack_n), .ack_out_s(), .ack_out_e(), .ack_out_w(xg_ack_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
        .freeze_in(1'b0), .hold_in(1'b0), .fb_internal_in(1'b0), .a_reemit_in(1'b0),
        .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );
    assign xg_ready_n = 1'b1;
    assign xg_ready_w = 1'b1;

    integer errors = 0;
    integer checks = 0;

    task run_case(input signed [31:0] a, input signed [31:0] b, input want, input [63:0] label);
        reg [31:0] want32;
        begin
            want32 = {31'h0, want};
            rst = 1'b1; #10; rst = 1'b0; #10;

            // real cfg for DIFF: downstream=E+S (multicast), upstream N+W
            cfg_diff = 1;
            cfg_d_diff = {31'h0, 20'h0, 1'b0, (DIR_N6 | DIR_W6), (DIR_E6 | DIR_S6)};
            #10; cfg_diff = 0;
            cfg_c1 = 1; cfg_d_c1 = {20'h0, 32'sd0, DIR_W6, DIR_E6}; #10; cfg_c1 = 0;
            cfg_c2 = 1; cfg_d_c2 = {20'h0, 32'sd1, DIR_N6, DIR_E6}; #10; cfg_c2 = 0;
            cfg_xg = 1; cfg_d_xg = 128'h0; cfg_d_xg[9:0]=TOPO_XOR; cfg_d_xg[69:64]=DIR_E6;
            #10; cfg_xg = 0;
            #10;

            // real diff = a + (-b) -- reusing #611's own negate-at-
            // injection trick (b here is a real, compile-time-known
            // test value, matching the LLVM frontend's own real
            // second-operand restriction).
            a_val = a;
            negb_val = (-b) & 32'hFFFFFFFF;
            negb_pulse = 1'b1; #10; negb_pulse = 1'b0; #40;
            a_pulse = 1'b1; #10; a_pulse = 1'b0; #80;

            checks = checks + 1;
            if (!result_fire || result_out !== want32) begin
                $display("[%0t] FAIL (%0s): a=%0d b=%0d -- expected fire=1 val=%h, got fire=%b val=%h",
                          $time, label, a, b, want32, result_fire, result_out);
                errors = errors + 1;
            end else begin
                $display("[%0t] check #%0d (%0s): a=%0d b=%0d -> eq=%h (correct)", $time, checks, label, a, b, result_out);
                cons_ack = 1'b1; #10; cons_ack = 1'b0; #20;
            end
        end
    endtask

    initial begin
        run_case(32'sd5, 32'sd5, 1'b1, "equal");
        run_case(32'sd5, 32'sd3, 1'b0, "greater");
        run_case(32'sd3, 32'sd5, 1'b0, "less");
        run_case(-32'sd7, -32'sd7, 1'b1, "equal-negative");

        if (checks == 4 && errors == 0)
            $display("PASS: real icmp eq construction -- XOR(diff>=0, diff>=1) == (diff==0), confirmed correct for equal/greater/less/negative-equal cases");
        else
            $display("FAIL: checks=%0d errors=%0d", checks, errors);

        $finish;
    end

endmodule
