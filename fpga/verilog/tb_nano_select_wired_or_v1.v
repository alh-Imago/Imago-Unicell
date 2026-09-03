// tb_nano_select_wired_or_v1.v — real, live investigation of the OLD
// library's own third, cheaper MUX construction (fp_tiles.py's own
// `_barrel_shift_right_wired`, found in #631): two AND cells, each
// holding a PRELOADED operand (sel/nsel via nano's own real hold_in
// mode, #626), routed to the SAME real downstream cell -- letting the
// wired-OR combine physics (#611's own confirmed hazard, deliberately
// used here as a FEATURE) do the final selection, no dedicated OR
// cell needed.
//
// Real, honest adaptation from the old system's own real assumption:
// the old construction assumed sel/nsel were ALREADY known constants
// from outside; here cond is genuinely dynamic, so a real NOT_A cell
// still computes nsel once -- the real saving under test is ONE cell
// (the dedicated OR), not the old system's own much larger amortized
// number (which came from SHARING one NOT across 24 parallel bit
// lanes, not from eliminating it for a single use).
//
// Real topology:
//   Cell0 (NOT_A): cond -> nsel
//   CellA (AND, hold_in=1): holds cond, computes AND(cond, a) per live a
//   CellB (AND, hold_in=1): holds nsel, computes AND(nsel, b) per live b
//   Receiver (nano, PASS_A): CellA on N, CellB on S -- nano's own real
//     any_arrived OR-combine does the final selection.
`timescale 1ns / 1ps

module tb_nano_select_wired_or_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    function [127:0] mk_cfg(input [9:0] topo, input [5:0] route, input hold);
        begin
            mk_cfg = 128'h0;
            mk_cfg[9:0]   = topo;
            mk_cfg[69:64] = route;
            // hold_in is a real LIVE wire, not a config field -- driven
            // separately below, this function only sets topology/route.
        end
    endfunction

    localparam [9:0] TOPO_NOT_A = 10'h001;
    localparam [9:0] TOPO_AND   = 10'h007;
    localparam [9:0] TOPO_PASS_A= 10'h000;
    localparam [5:0] DIR_N6=6'b000001, DIR_S6=6'b000010, DIR_E6=6'b000100, DIR_W6=6'b001000;

    reg cfg0=0, cfgA=0, cfgB=0, cfgR=0;
    reg [127:0] cfg_d0, cfg_dA, cfg_dB, cfg_dR;

    reg [31:0] cond_val=0, a_val=0, b_val=0;
    reg cond_pulse0_n=0, cond_pulse0_n2=0;
    reg condA_pulse_n=0, aA_pulse_s=0;
    reg bB_pulse_s=0;
    reg holdA=0, holdB=0;

    wire [31:0] c0_dout_e; wire c0_fire_e;
    wire [31:0] cA_dout_e; wire cA_fire_e, cA_ready_o;
    wire [31:0] cB_dout_e; wire cB_fire_e, cB_ready_o;
    wire c0_ack_out_w_for_B;
    wire cA_ack_out_w_for_recv, cB_ack_out_w_for_recv;

    wire [31:0] result_out; wire result_fire;
    reg cons_ready=1, cons_ack=0;
    wire recv_ack_out_n, recv_ack_out_s;
    reg [31:0] recv_dummy_val = 0;
    reg recv_dummy_pulse = 0;

    // ── Cell0: NOT_A -- computes nsel from cond ──
    nano_gate_v4 #(.CELL_ID(16'h3000), .ENABLE_DYNAMIC_ROUTING(1'b0)) CELL0 (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfg0), .cfg_data(cfg_d0),
        .data_in_n(cond_val), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(cond_pulse0_n | cond_pulse0_n2), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(c0_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(c0_fire_e), .fire_w(),
        .ready_out(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(c0_ack_out_w_for_B), .ack_in_w(1'b0),
        .freeze_in(1'b0), .hold_in(1'b0), .fb_internal_in(1'b0), .a_reemit_in(1'b0),
        .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    // ── CellA: AND, hold_in -- holds cond, computes AND(cond,a) per live a ──
    nano_gate_v4 #(.CELL_ID(16'h3001), .ENABLE_DYNAMIC_ROUTING(1'b0)) CELLA (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfgA), .cfg_data(cfg_dA),
        .data_in_n(cond_val), .data_in_s(a_val), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(condA_pulse_n), .arrived_s(aA_pulse_s), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(cA_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(cA_fire_e), .fire_w(),
        .ready_out(cA_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(cA_ack_out_w_for_recv),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(recv_ack_out_n), .ack_in_w(1'b0),
        .freeze_in(1'b0), .hold_in(holdA), .fb_internal_in(1'b0), .a_reemit_in(1'b0),
        .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    // ── CellB: AND, hold_in -- holds nsel (from Cell0), computes
    // AND(nsel,b) per live b ──
    nano_gate_v4 #(.CELL_ID(16'h3002), .ENABLE_DYNAMIC_ROUTING(1'b0)) CELLB (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfgB), .cfg_data(cfg_dB),
        .data_in_n(c0_dout_e), .data_in_s(b_val), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(c0_fire_e), .arrived_s(bB_pulse_s), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(cB_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(cB_fire_e), .fire_w(),
        .ready_out(cB_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(c0_ack_out_w_for_B), .ack_out_s(), .ack_out_e(), .ack_out_w(cB_ack_out_w_for_recv),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(recv_ack_out_s), .ack_in_w(1'b0),
        .freeze_in(1'b0), .hold_in(holdB), .fb_internal_in(1'b0), .a_reemit_in(1'b0),
        .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    // ── Receiver: PASS_A -- CellA arrives on N, CellB arrives on S,
    // nano's own real any_arrived OR-combine does the final selection.
    // Real, deliberate test: are cA_fire_e/cB_fire_e ever asserted on
    // the SAME real cycle at all, given they're driven by two
    // independent, separately-timed testbench pulses? ──
    nano_gate_v4 #(.CELL_ID(16'h3003), .ENABLE_DYNAMIC_ROUTING(1'b0)) RECV (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfgR), .cfg_data(cfg_dR),
        .data_in_n(cA_dout_e), .data_in_s(cB_dout_e), .data_in_e(32'h0), .data_in_w(recv_dummy_val),
        .arrived_n(cA_fire_e), .arrived_s(cB_fire_e), .arrived_e(1'b0), .arrived_w(recv_dummy_pulse),
        .data_out_n(), .data_out_s(), .data_out_e(result_out), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(result_fire), .fire_w(),
        .ready_out(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(recv_ack_out_n), .ack_out_s(recv_ack_out_s), .ack_out_e(), .ack_out_w(),
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

    task run_case(input [31:0] cond, input [31:0] a, input [31:0] b, input [31:0] want, input [63:0] label);
        begin
            rst = 1'b1; #10; rst = 1'b0; #10;
            cfg0 = 1; cfg_d0 = mk_cfg(TOPO_NOT_A, DIR_E6, 1'b0); #10; cfg0 = 0;
            cfgA = 1; cfg_dA = mk_cfg(TOPO_AND,   DIR_E6, 1'b0); #10; cfgA = 0;
            cfgB = 1; cfg_dB = mk_cfg(TOPO_AND,   DIR_E6, 1'b0); #10; cfgB = 0;
            cfgR = 1; cfg_dR = mk_cfg(TOPO_PASS_A,DIR_E6, 1'b0); #10; cfgR = 0;
            holdA = 1'b0; holdB = 1'b0;
            #10;

            cond_val = cond; a_val = a; b_val = b;

            // Cell0: NOT_A(cond) -- two real arrivals of cond
            cond_pulse0_n = 1'b1; #10; cond_pulse0_n = 1'b0; #20;
            cond_pulse0_n2 = 1'b1; #10; cond_pulse0_n2 = 1'b0; #40;

            // CellA: hold cond as its own real first operand, THEN
            // enable hold_in so it stays latched across future fires.
            condA_pulse_n = 1'b1; #10; condA_pulse_n = 1'b0; #20;
            holdA = 1'b1;

            // CellB: hold nsel (from Cell0, already fired above) as its
            // own real first operand, then enable hold_in.
            #10;
            holdB = 1'b1;
            #30;

            // Now drive the real, live second operands -- a to CellA,
            // b to CellB, deliberately at the SAME real time, to see
            // whether their own real outputs land on RECV simultaneously.
            aA_pulse_s = 1'b1; bB_pulse_s = 1'b1;
            #10;
            aA_pulse_s = 1'b0; bB_pulse_s = 1'b0;
            #30;

            // Real, necessary dummy second arrival for RECV, same real
            // fix #629's own Cell1 (NOT_A) needed: PASS_A only uses the
            // real FIRST (OR-combined) arrival's value, but nano's own
            // hardware still requires a genuine second arrival to
            // trigger firing at all -- confirmed directly by tracing
            // (RECV correctly captured the OR-combined value as its
            // real first operand, then sat waiting forever for a
            // second one that never came).
            recv_dummy_val = 32'hDEADBEEF; recv_dummy_pulse = 1'b1; #10; recv_dummy_pulse = 1'b0; #40;

            checks = checks + 1;
            if (!result_fire || result_out !== want) begin
                $display("[%0t] FAIL (%0s): cond=%h a=%h b=%h -- expected fire=1 val=%h, got fire=%b val=%h",
                          $time, label, cond, a, b, want, result_fire, result_out);
                errors = errors + 1;
            end else begin
                $display("[%0t] check #%0d (%0s): cond=%h -> result=%h (correct, via real wired-OR combine, no dedicated OR cell)",
                          $time, checks, label, cond, result_out);
                cons_ack = 1'b1; #10; cons_ack = 1'b0; #20;
            end
        end
    endtask

    initial begin
        run_case(32'hFFFFFFFF, 32'hAAAAAAAA, 32'hBBBBBBBB, 32'hAAAAAAAA, "cond=true-wired-or");
        run_case(32'h00000000, 32'hAAAAAAAA, 32'hBBBBBBBB, 32'hBBBBBBBB, "cond=false-wired-or");

        if (checks == 2 && errors == 0)
            $display("PASS: real wired-OR select construction (2 AND cells, hold_in-preloaded, no dedicated OR cell) -- confirmed correct for both real outcomes on Unicell-S's own real two-arrival model");
        else
            $display("FAIL: checks=%0d errors=%0d", checks, errors);

        $finish;
    end

endmodule
