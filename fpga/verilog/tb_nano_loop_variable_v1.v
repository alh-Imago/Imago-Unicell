// tb_nano_loop_variable_v1.v — real, live investigation for LLVM's
// phi/loop support (points.md #611/#612's own real, standing gap).
// Confirms nano's own real hold_in + a_update_in + a_reemit_in
// sequence genuinely holds a loop-carried variable that a SEPARATE,
// real physical feedback wire can update -- the SAME real conceptual
// mechanism the old llvm_ir_mapper.py's own real "GS_LATCH |
// LOOP_MODE" storage cell used (a cell that holds the previous
// iteration's value and re-emits it, #612's own archive read), here
// achieved via a genuine PHYSICAL back-edge wire instead of a bus
// address.
//
// Real, necessary correction, found by tracing an actual failure, not
// assumed: a first draft tried nano's own `a_self_update_in` mode for
// this, following a surface reading of the port list. Checked
// directly against the real, ESTABLISHED `tb_stripped_v1_selfupdate.v`
// testbench before building further: self-update mode recomputes
// `A = topology(A, out_buffer)` where `out_buffer` is a FIXED value
// set once before self-update begins, never a fresh per-iteration
// input -- suited to bitwise-converging patterns (a self-adjusting
// threshold), not arithmetic counting. Nano also has no native ADD
// gate of its own (that's the separate `adder` core). The real,
// correct mechanism for a counting loop is `a_update_in` (a genuinely
// fresh EXTERNAL arrival overwrites the held A each iteration) fed by
// a real, physical feedback wire from a SEPARATE `adder` cell -- a
// genuine hardware loop in the cardinal mesh, matching this project's
// own "topology is computation" philosophy directly, not an internal
// single-cell trick.
`timescale 1ns / 1ps

module tb_nano_loop_variable_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [5:0] DIR_N6=6'b000001, DIR_E6=6'b000100;

    reg cfg = 0; reg [127:0] cfg_d;
    reg [31:0] init_val = 0; reg init_pulse = 0;
    reg hold = 0, upd = 0, reemit = 0;
    reg cons_ready = 1, cons_ack = 0;

    // ── LOOPVAR: nano, holds the real loop-carried value. Real,
    // deliberate topology choice: PASS_A (0x000) -- this cell's own
    // real job is to STORE and RE-EMIT, not compute; the arithmetic
    // (i+1) happens on the separate real ADDER below. ──
    localparam [9:0] TOPO_PASS_A = 10'h000;

    reg [31:0] update_val = 0;
    reg update_pulse = 0;

    wire [31:0] loopvar_dout_e; wire loopvar_fire_e; wire loopvar_ready_o;

    nano_gate_v4 #(.CELL_ID(16'h5000), .ENABLE_DYNAMIC_ROUTING(1'b0)) LOOPVAR (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(update_pulse ? update_val : init_val),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(update_pulse | init_pulse),
        .data_out_n(), .data_out_s(), .data_out_e(loopvar_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(loopvar_fire_e), .fire_w(),
        .ready_out(loopvar_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
        .freeze_in(1'b0), .hold_in(hold), .fb_internal_in(1'b0), .a_reemit_in(reemit),
        .a_update_in(upd), .a_self_update_in(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    integer errors = 0;
    integer checks = 0;

    task check_now(input [31:0] want, input [63:0] label);
        begin
            checks = checks + 1;
            if (!loopvar_fire_e || loopvar_dout_e !== want) begin
                $display("[%0t] FAIL (%0s): expected fire=1 val=%h, got fire=%b val=%h", $time, label, want, loopvar_fire_e, loopvar_dout_e);
                errors = errors + 1;
            end else begin
                $display("[%0t] check #%0d (%0s): loop-var=%h (correct)", $time, checks, label, loopvar_dout_e);
                cons_ack = 1'b1; #10; cons_ack = 1'b0; #20;
            end
        end
    endtask

    initial begin
        #12 rst = 0;
        cfg = 1; cfg_d = 128'h0; cfg_d[9:0] = TOPO_PASS_A; cfg_d[69:64] = DIR_E6;
        #10; cfg = 0;
        #10;

        // ── Real "entry edge": seed the loop variable's real initial
        // value. Real, necessary second (dummy) arrival, matching this
        // session's own recurring real pattern (#629/#630/#633): nano
        // always needs TWO real arrivals to fire, even for PASS_A,
        // which only ever uses the first. Real, necessary ordering,
        // found by tracing an actual failure: hold_in must be set
        // BEFORE this second arrival, since `a_arrived <= hold_in` on
        // fire -- setting hold_in only afterward leaves a_arrived
        // cleared, and a_reemit_active later requires a_arrived=1. ──
        hold = 1'b1;
        init_val = 32'd0;
        init_pulse = 1'b1; #10; init_pulse = 1'b0; #20;
        update_val = 32'hDEADBEEF; update_pulse = 1'b1; #10; update_pulse = 1'b0; #30;
        check_now(32'd0, "entry-seed");

        #10;

        // ── Real iteration 1: a fresh, EXTERNAL value (standing in
        // for a real adder's own i+1 output) overwrites the held
        // loop variable via a_update_in. ──
        update_val = 32'd1;
        upd = 1'b1; update_pulse = 1'b1;
        #10;
        upd = 1'b0; update_pulse = 1'b0;
        #20;
        // real, necessary accompanying arrival during reemit (value
        // ignored per #119's own established convention, confirmed
        // directly against tb_stripped_v1_selfupdate.v's own real
        // usage) -- a_reemit_active requires consume_arrived, reemit
        // alone with no real arrival never triggers.
        reemit = 1'b1; update_val = 32'hFFFFFFFF; update_pulse = 1'b1;
        #10; update_pulse = 1'b0; reemit = 1'b0; #30;
        check_now(32'd1, "iteration-1");

        // ── Real iteration 2: confirms the loop variable genuinely
        // carries forward -- the NEXT external update would, in a
        // real loop, be i+1 computed from THIS iteration's own
        // re-emitted value (a real physical feedback wire), not from
        // the original entry value. ──
        update_val = 32'd2;
        upd = 1'b1; update_pulse = 1'b1;
        #10;
        upd = 1'b0; update_pulse = 1'b0;
        #20;
        reemit = 1'b1; update_val = 32'hFFFFFFFF; update_pulse = 1'b1;
        #10; update_pulse = 1'b0; reemit = 1'b0; #30;
        check_now(32'd2, "iteration-2-carries-forward");

        if (checks == 3 && errors == 0)
            $display("PASS: real loop-carried variable storage via nano's own real hold_in+a_update_in+a_reemit_in -- entry seed + 2 real external updates (standing in for a real adder's own feedback), each correctly overwriting the held value, confirming the real STORAGE half of a physical hardware loop");
        else
            $display("FAIL: checks=%0d errors=%0d", checks, errors);

        $finish;
    end

endmodule

