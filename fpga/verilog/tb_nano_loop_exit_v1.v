// tb_nano_loop_exit_v1.v — points.md #636's own standing queue item 1:
// the real loop-exit mechanism via nano's dynamic pattern-routing
// (ENABLE_DYNAMIC_ROUTING, kept real and sim-verified since #626, not
// yet exercised for this specific purpose).
//
// Real construction: a single nano_gate_v4 cell (LOOP_CTRL) captures
// the loop variable i as its first real arrival (west) and the loop
// bound N as its second real arrival (north, standing in for a
// not-yet-built constant source, matching #636's own precedent for
// the adder's B operand). Topology PASS_A means computed_output=
// input_val=i regardless of outcome -- what changes is WHICH real
// cardinal direction the cell routes i to:
//   cmp_gt (second_val=N > input_val=i, i.e. i still < N) -> pattern_high -> EAST  (continue)
//   cmp_lt (N < i, degenerate/past-bound)                 -> pattern_low  -> SOUTH (exit, safety)
//   otherwise (N == i, the real loop-boundary case)        -> pattern_equal -> SOUTH (exit)
//
// Real, honest scope: this proves the DECISION mechanism in isolation,
// the same discipline #629/#630/#633/#634 each used before any wider
// integration. NOT attempted here: wiring LOOP_CTRL into the real
// LOOPVAR+ADDER physical loop from #636. Real, concrete reason found
// while designing this file, not glossed over: nano's cardinal mesh is
// bipartite (only even-length real cycles are physically realizable --
// a genuine 3-cell ring cannot close under pure N/S/E/W hops), AND
// dynamic_route_en applies to a cell's WHOLE effective_routing,
// including any cardinal_edge-marked relay direction -- so a single
// cell can't simultaneously be a reliable straight relay for the real
// return-sum path AND a dynamic comparator-router for the real
// continue/exit decision. Full physical integration needs either a
// 4th real relay cell (closing a proper even-length ring) or a
// redesigned control scheme where the exit test doesn't require
// routing return traffic back through this same cell -- a real,
// separate, later design question, not resolved here.
`timescale 1ns / 1ps

module tb_nano_loop_exit_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [9:0] TOPO_PASS_A = 10'h000;
    // Real bit convention, confirmed against the RTL directly:
    // bit0=N, bit1=S, bit2=E, bit3=W (want_n/s/e/w = effective_routing[0/1/2/3]).
    localparam [3:0] DIR_E4 = 4'b0100;
    localparam [3:0] DIR_S4 = 4'b0010;

    reg cfg = 0; reg [127:0] cfg_d;

    reg [31:0] i_val = 0; reg i_pulse = 0;    // west: loop variable i (first real arrival)
    reg [31:0] n_val = 0; reg n_pulse = 0;    // north: loop bound N (second real arrival)
    reg cont_ready = 1, cont_ack = 0;         // east (continue) consumer stand-in
    reg exit_ready = 1, exit_ack = 0;         // south (exit) consumer stand-in

    wire [31:0] ctrl_dout_e, ctrl_dout_s;
    wire ctrl_fire_e, ctrl_fire_s;
    wire ctrl_ready_o;

    nano_gate_v4 #(.CELL_ID(16'h6000), .ENABLE_DYNAMIC_ROUTING(1'b1)) LOOP_CTRL (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(n_val), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(i_val),
        .arrived_n(n_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(i_pulse),
        .data_out_n(), .data_out_s(ctrl_dout_s), .data_out_e(ctrl_dout_e), .data_out_w(),
        .fire_n(), .fire_s(ctrl_fire_s), .fire_e(ctrl_fire_e), .fire_w(),
        .ready_out(ctrl_ready_o),
        .ready_in_n(1'b1), .ready_in_s(exit_ready), .ready_in_e(cont_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(exit_ack), .ack_in_e(cont_ack), .ack_in_w(1'b0),
        .freeze_in(1'b0), .hold_in(1'b0), .fb_internal_in(1'b0), .a_reemit_in(1'b0),
        .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    integer errors = 0;
    integer checks = 0;

    // want_east=1 means "expect the CONTINUE route (east)"; want_east=0
    // means "expect the EXIT route (south)".
    task check_route(input [31:0] i_in, input [31:0] n_in, input want_east, input [255:0] label);
        begin
            checks = checks + 1;
            i_val = i_in; i_pulse = 1'b1;
            @(posedge clk); #1;
            i_pulse = 1'b0;
            repeat (2) @(posedge clk);
            n_val = n_in; n_pulse = 1'b1;
            @(posedge clk); #1;
            n_pulse = 1'b0;
            repeat (2) @(posedge clk); #1;

            if (want_east) begin
                if (!ctrl_fire_e || ctrl_dout_e !== i_in || ctrl_fire_s) begin
                    $display("[t=%0t] FAIL (%0s): expected CONTINUE(east) fire=1 val=%0d, got fire_e=%b val_e=%0d fire_s=%b",
                              $time, label, i_in, ctrl_fire_e, ctrl_dout_e, ctrl_fire_s);
                    errors = errors + 1;
                end else begin
                    $display("[t=%0t] check #%0d (%0s): i=%0d N=%0d -> CONTINUE (east, val=%0d) correct",
                              $time, checks, label, i_in, n_in, ctrl_dout_e);
                    cont_ack = 1'b1; @(posedge clk); #1; cont_ack = 1'b0;
                end
            end else begin
                if (!ctrl_fire_s || ctrl_dout_s !== i_in || ctrl_fire_e) begin
                    $display("[t=%0t] FAIL (%0s): expected EXIT(south) fire=1 val=%0d, got fire_s=%b val_s=%0d fire_e=%b",
                              $time, label, i_in, ctrl_fire_s, ctrl_dout_s, ctrl_fire_e);
                    errors = errors + 1;
                end else begin
                    $display("[t=%0t] check #%0d (%0s): i=%0d N=%0d -> EXIT (south, val=%0d) correct",
                              $time, checks, label, i_in, n_in, ctrl_dout_s);
                    exit_ack = 1'b1; @(posedge clk); #1; exit_ack = 1'b0;
                end
            end
            repeat (3) @(posedge clk);
        end
    endtask

    initial begin
        $dumpfile("/tmp/tb_nano_loop_exit_v1.vcd");
        $dumpvars(0, tb_nano_loop_exit_v1);

        #12 rst = 0;
        @(posedge clk); #1;

        cfg = 1; cfg_d = 128'h0;
        cfg_d[9:0]   = TOPO_PASS_A;
        cfg_d[69:64] = {2'b00, DIR_E4 | DIR_S4};   // routing_mask: east|south
        cfg_d[79:76] = DIR_S4;                     // pattern_low    (N<i, degenerate)  -> south
        cfg_d[85:82] = DIR_S4;                     // pattern_equal  (N==i, real exit)  -> south
        cfg_d[91:88] = DIR_E4;                     // pattern_high   (N>i, continue)    -> east
        cfg_d[94]    = 1'b1;                       // dynamic_route_en
        @(posedge clk); #1;
        cfg = 0;
        repeat (2) @(posedge clk);

        // ── Real loop bound N=3, "for i in 0..N": continue while i<N,
        // exit exactly when i==N, plus a degenerate i>N safety case. ──
        check_route(32'd0, 32'd3, 1'b1, "i=0,N=3 (i<N)");
        check_route(32'd1, 32'd3, 1'b1, "i=1,N=3 (i<N)");
        check_route(32'd2, 32'd3, 1'b1, "i=2,N=3 (i<N)");
        check_route(32'd3, 32'd3, 1'b0, "i=3,N=3 (i==N, real exit boundary)");
        check_route(32'd5, 32'd3, 1'b0, "i=5,N=3 (i>N, degenerate/safety)");

        if (checks == 5 && errors == 0)
            $display("PASS: real loop-exit mechanism -- nano_gate_v4's own dynamic pattern-routing (ENABLE_DYNAMIC_ROUTING) correctly routes the loop variable to CONTINUE (east) while i<N and to EXIT (south) at i==N and i>N, confirmed over 5 real cases");
        else
            $display("FAIL: checks=%0d errors=%0d", checks, errors);

        $finish;
    end

endmodule
