// tb_select_full_chain_v1.v — real, complete chain closing #629's own
// honest gap: comparator -> boolean-expand -> 4-cell select, all real,
// chained cells, no raw testbench-injected `cond` this time. Confirms
// `icmp`-shaped output (a real comparator's own raw 0/1 result) can
// genuinely drive `select` end to end.
//
// Real chain:
//   Comparator: upstream_val >= threshold -> raw cond (0 or 1)
//   Expander (adder, subtract_mode=1): 0 - cond -> real all-ones/
//     all-zeros mask (0 stays 0; 1 wraps to 0xFFFFFFFF via real
//     two's-complement subtraction) -- real, dynamic value, NOT a
//     compile-time constant this time, unlike #611's own negate-at-
//     injection trick for LLVM literals.
//   Expander broadcasts to BOTH Cell1 and Cell2 simultaneously (real,
//     already-proven multi-bit downstream_mask multicast).
//   4-cell select (Cell1-4, unchanged from #629): (cond AND a) OR
//     (NOT(cond) AND b).
`timescale 1ns / 1ps

module tb_select_full_chain_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    // ── cfg helpers ──
    function [63:0] mk_cmp_cfg(input signed [31:0] thr, input [5:0] down, input [5:0] up);
        begin
            mk_cmp_cfg = {20'h0, thr, up, down};
        end
    endfunction
    function [63:0] mk_adder_cfg(input subtract_mode, input [5:0] up);
        begin
            mk_adder_cfg = {31'h0, 20'h0, subtract_mode, up, 6'b000000};   // downstream set live below via cfg override
        end
    endfunction
    function [127:0] mk_nano_cfg(input [9:0] topo, input [5:0] route);
        begin
            mk_nano_cfg = 128'h0;
            mk_nano_cfg[9:0]   = topo;
            mk_nano_cfg[69:64] = route;
        end
    endfunction

    localparam [9:0] TOPO_NOT_A = 10'h001;
    localparam [9:0] TOPO_AND   = 10'h007;
    localparam [9:0] TOPO_OR    = 10'h024;
    localparam [5:0] DIR_N6=6'b000001, DIR_S6=6'b000010, DIR_E6=6'b000100, DIR_W6=6'b001000;

    // ── Comparator: threshold=10, upstream on N, offer on E ──
    reg cfg_cmp = 0; reg [63:0] cfg_d_cmp;
    reg [31:0] cmp_in = 0; reg cmp_pulse = 0;
    wire [31:0] cmp_dout_e; wire cmp_fire_e, cmp_ready_o;
    wire exp_ready_for_cmp;
    wire exp_ack_for_cmp;

    compare_cell_v4 #(.CELL_ID(16'h2001)) CMP (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfg_cmp), .cfg_data(cfg_d_cmp),
        .data_in_n(cmp_in), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(cmp_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(cmp_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(cmp_fire_e), .fire_w(),
        .ready_out(cmp_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(exp_ready_for_cmp), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(exp_ack_for_cmp), .ack_in_w(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .freeze_in(1'b0), .status_data_valid()
    );

    // ── Expander: adder, subtract_mode=1, computes 0 - cond.
    // A(zero, injected, arrives first via N) - B(cond from comparator,
    // arrives second via W) -- real dynamic subtraction, not a
    // compile-time negate-at-injection trick this time. Broadcasts to
    // BOTH Cell1(W) and Cell2(N) via real multicast (downstream_mask
    // with 2 bits set). ──
    reg cfg_exp = 0; reg [63:0] cfg_d_exp;
    reg [31:0] zero_val = 32'h0; reg zero_pulse = 0;
    wire [31:0] exp_dout_e, exp_dout_s; wire exp_fire_e, exp_fire_s, exp_ready_o;
    reg c1_ready_for_exp = 1, c2_ready_for_exp = 1;
    wire c1_ack_for_exp;
    wire c2_ack_for_exp;

    adder_cell_v4 #(.CELL_ID(16'h2002)) EXP (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfg_exp), .cfg_data(cfg_d_exp),
        .data_in_n(zero_val), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(cmp_dout_e),
        .arrived_n(zero_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(cmp_fire_e),
        .data_out_n(), .data_out_s(exp_dout_s), .data_out_e(exp_dout_e), .data_out_w(),
        .fire_n(), .fire_s(exp_fire_s), .fire_e(exp_fire_e), .fire_w(),
        .ready_out(exp_ready_o),
        .ready_in_n(1'b1), .ready_in_s(c2_ready_for_exp), .ready_in_e(c1_ready_for_exp), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(exp_ack_for_cmp),
        .ack_in_n(1'b0), .ack_in_s(c2_ack_for_exp), .ack_in_e(c1_ack_for_exp), .ack_in_w(1'b0),
        .freeze_in(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .status_data_valid(), .status_a_arrived()
    );
    assign exp_ready_for_cmp = exp_ready_o;

    // ── The 4-cell select composition, real-unchanged shape from
    // #629 -- only the cond SOURCE changes (real cells now, not raw
    // testbench injection). ──
    function [127:0] mk_cfg4(input [9:0] topo, input [5:0] route);
        begin
            mk_cfg4 = 128'h0; mk_cfg4[9:0] = topo; mk_cfg4[69:64] = route;
        end
    endfunction

    reg cfg1=0, cfg2=0, cfg3=0, cfg4=0;
    reg [127:0] cfg_d1, cfg_d2, cfg_d3, cfg_d4;
    reg [31:0] dummy2_val = 0; reg dummy2_pulse = 0;   // Cell1's own real 2nd (ignored) operand
    reg [31:0] a_val = 0, b_val = 0;
    reg a_pulse = 0, b_pulse = 0;

    wire [31:0] c1_dout_e; wire c1_fire_e, c1_ready_o;
    wire [31:0] c2_dout_e; wire c2_fire_e, c2_ready_o;
    wire [31:0] c3_dout_e; wire c3_fire_e, c3_ready_o;
    wire c4_ack_out_n, c4_ack_out_s;
    wire [31:0] result_out; wire result_fire;
    reg cons_ready = 1, cons_ack = 0;
    wire c3_ack_out_w;

    nano_gate_v4 #(.CELL_ID(16'h1001), .ENABLE_DYNAMIC_ROUTING(1'b0)) CELL1 (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfg1), .cfg_data(cfg_d1),
        .data_in_n(dummy2_val), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(exp_dout_e),
        .arrived_n(dummy2_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(exp_fire_e),
        .data_out_n(), .data_out_s(), .data_out_e(c1_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(c1_fire_e), .fire_w(),
        .ready_out(c1_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(c3_ready_o_fwd), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(c1_ack_for_exp),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(c3_ack_out_w), .ack_in_w(1'b0),
        .freeze_in(1'b0), .hold_in(1'b0), .fb_internal_in(1'b0), .a_reemit_in(1'b0),
        .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );
    wire c3_ready_o_fwd = c3_ready_o;

    nano_gate_v4 #(.CELL_ID(16'h1002), .ENABLE_DYNAMIC_ROUTING(1'b0)) CELL2 (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfg2), .cfg_data(cfg_d2),
        .data_in_n(exp_dout_s), .data_in_s(a_val), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(exp_fire_s), .arrived_s(a_pulse), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(c2_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(c2_fire_e), .fire_w(),
        .ready_out(c2_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(c2_ack_for_exp), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(c4_ack_out_n), .ack_in_w(1'b0),
        .freeze_in(1'b0), .hold_in(1'b0), .fb_internal_in(1'b0), .a_reemit_in(1'b0),
        .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    nano_gate_v4 #(.CELL_ID(16'h1003), .ENABLE_DYNAMIC_ROUTING(1'b0)) CELL3 (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfg3), .cfg_data(cfg_d3),
        .data_in_n(32'h0), .data_in_s(b_val), .data_in_e(32'h0), .data_in_w(c1_dout_e),
        .arrived_n(1'b0), .arrived_s(b_pulse), .arrived_e(1'b0), .arrived_w(c1_fire_e),
        .data_out_n(), .data_out_s(), .data_out_e(c3_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(c3_fire_e), .fire_w(),
        .ready_out(c3_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(c3_ack_out_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(c4_ack_out_s), .ack_in_w(1'b0),
        .freeze_in(1'b0), .hold_in(1'b0), .fb_internal_in(1'b0), .a_reemit_in(1'b0),
        .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    nano_gate_v4 #(.CELL_ID(16'h1004), .ENABLE_DYNAMIC_ROUTING(1'b0)) CELL4 (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfg4), .cfg_data(cfg_d4),
        .data_in_n(c2_dout_e), .data_in_s(c3_dout_e), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(c2_fire_e), .arrived_s(c3_fire_e), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(result_out), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(result_fire), .fire_w(),
        .ready_out(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(c4_ack_out_n), .ack_out_s(c4_ack_out_s), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
        .freeze_in(1'b0), .hold_in(1'b0), .fb_internal_in(1'b0), .a_reemit_in(1'b0),
        .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    integer errors = 0;
    integer checks = 0;

    task run_case(input signed [31:0] upstream, input signed [31:0] thr,
                  input [31:0] a, input [31:0] b, input [31:0] want, input [63:0] label);
        begin
            rst = 1'b1; #10; rst = 1'b0; #10;
            cfg_cmp = 1; cfg_d_cmp = mk_cmp_cfg(thr, DIR_E6, DIR_N6); #10; cfg_cmp = 0;
            cfg_exp = 1; cfg_d_exp = {31'h0, 20'h0, 1'b1, (DIR_N6 | DIR_W6), (DIR_E6 | DIR_S6)}; #10; cfg_exp = 0;
            cfg1 = 1; cfg_d1 = mk_cfg4(TOPO_NOT_A, DIR_E6); #10; cfg1 = 0;
            cfg2 = 1; cfg_d2 = mk_cfg4(TOPO_AND,   DIR_E6); #10; cfg2 = 0;
            cfg3 = 1; cfg_d3 = mk_cfg4(TOPO_AND,   DIR_E6); #10; cfg3 = 0;
            cfg4 = 1; cfg_d4 = mk_cfg4(TOPO_OR,    DIR_E6); #10; cfg4 = 0;
            #10;

            // Real, necessary ordering fix, found by tracing an actual
            // failure, not assumed correct up front: the comparator's
            // own real output stays PERSISTENTLY asserted once it
            // fires (a one-shot core holds its offer until acked) --
            // pulsing it before the zero-feeder means it would become
            // the expander's real FIRST operand (A), not the intended
            // SECOND (B), silently computing cond-0 instead of 0-cond.
            // Real fix: the zero-feeder must arrive and be captured as
            // A FIRST, with the comparator's own real offer starting
            // only afterward.
            zero_val = 32'h0; zero_pulse = 1'b1; #10; zero_pulse = 1'b0; #40;

            // real comparator: upstream_val >= threshold -- its own
            // real, persistent offer becomes the expander's real
            // SECOND operand (B), landing after zero is already
            // captured as A.
            cmp_in = upstream; cmp_pulse = 1'b1; #10; cmp_pulse = 1'b0; #40;

            // Cell1's own real, dummy 2nd operand (value ignored by
            // NOT_A) -- timed after the expander's own real multicast
            // has had a chance to land as Cell1's first real operand.
            #40;
            dummy2_val = 32'hDEADBEEF; dummy2_pulse = 1'b1; #10; dummy2_pulse = 1'b0; #30;

            a_val = a; a_pulse = 1'b1; #10; a_pulse = 1'b0; #30;
            b_val = b; b_pulse = 1'b1; #10; b_pulse = 1'b0; #60;

            checks = checks + 1;
            if (!result_fire || result_out !== want) begin
                $display("[%0t] FAIL (%0s): upstream=%0d thr=%0d a=%h b=%h -- expected fire=1 val=%h, got fire=%b val=%h",
                          $time, label, upstream, thr, a, b, want, result_fire, result_out);
                errors = errors + 1;
            end else begin
                $display("[%0t] check #%0d (%0s): upstream=%0d thr=%0d -> cond genuinely computed, result=%h (correct)",
                          $time, checks, label, upstream, thr, result_out);
                cons_ack = 1'b1; #10; cons_ack = 1'b0; #20;
            end
        end
    endtask

    initial begin
        // upstream=10 >= threshold=5 -> real cond=true -> selects a
        run_case(32'sd10, 32'sd5, 32'hAAAAAAAA, 32'hBBBBBBBB, 32'hAAAAAAAA, "10>=5-true-selects-a");
        // upstream=2 >= threshold=5 -> real cond=false -> selects b
        run_case(32'sd2, 32'sd5, 32'hAAAAAAAA, 32'hBBBBBBBB, 32'hBBBBBBBB, "2>=5-false-selects-b");

        if (checks == 2 && errors == 0)
            $display("PASS: full real chain -- comparator (real icmp-shaped 0/1 output) -> boolean-expand (real dynamic 0-cond via adder subtract_mode) -> 4-cell select, all real, chained cells, confirmed correct for both real outcomes");
        else
            $display("FAIL: checks=%0d errors=%0d", checks, errors);

        $finish;
    end

endmodule
