// tb_nano_select_compose_v1.v — real, live investigation: does
// select(cond, a, b) = (cond AND a) OR (NOT(cond) AND b) genuinely
// work when built from 4 real, chained nano_gate_v4.v instances,
// using only its own already-proven, already-tested real gate
// primitives (TOPO_NOT_A/TOPO_AND/TOPO_OR)? Real, honest test, not
// assumed correct from the Boolean identity alone -- this session's
// own repeated real lesson (#611, #619, #624) is that composing
// multiple real cells correctly needs real, deliberate timing
// engineering, not just a correct-on-paper circuit.
//
// Real topology: 4 chained cells --
//   Cell1 (NOT_A): cond -> NOT(cond)
//   Cell2 (AND):   cond, a -> (cond AND a)
//   Cell3 (AND):   Cell1's real output, b -> (NOT(cond) AND b)
//   Cell4 (OR):    Cell2's real output, Cell3's real output -> result
`timescale 1ns / 1ps

module tb_nano_select_compose_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    // ── Real cfg construction, same real field positions as
    // nano_gate_v4.v's own field map: [9:0]topology [69:64]routing_mask
    // [75:70]cardinal_edge(0=all consume). ──
    function [127:0] mk_cfg(input [9:0] topo, input [5:0] route);
        begin
            mk_cfg = 128'h0;
            mk_cfg[9:0]   = topo;
            mk_cfg[69:64] = route;
        end
    endfunction

    localparam [9:0] TOPO_NOT_A = 10'h001;
    localparam [9:0] TOPO_AND   = 10'h007;
    localparam [9:0] TOPO_OR    = 10'h024;
    localparam [5:0] DIR_E6 = 6'b000100;

    reg cfg1=0, cfg2=0, cfg3=0, cfg4=0;
    reg [127:0] cfg_d1, cfg_d2, cfg_d3, cfg_d4;

    // ── Real external stimulus ──
    reg [31:0] cond_val = 0, a_val = 0, b_val = 0;
    reg cond_pulse1_n = 0, cond_pulse2_n = 0;   // Cell1's own two real arrivals (NOT_A ignores the 2nd)
    reg cond_pulse_c2n = 0, a_pulse_c2s = 0;    // Cell2's own two real arrivals
    reg b_pulse_c3s = 0;                        // Cell3's own second real arrival (1st comes from Cell1)

    // ── Real inter-cell wiring: Cell1.E -> Cell3.W ──
    wire [31:0] c1_dout_e; wire c1_fire_e, c1_ready_o;
    wire c3_ack_out_w, c3_ready_in_w_from_readyout1;

    // ── Real inter-cell wiring: Cell2.E -> Cell4.N, Cell3.E -> Cell4.S ──
    wire [31:0] c2_dout_e; wire c2_fire_e, c2_ready_o;
    wire [31:0] c3_dout_e; wire c3_fire_e, c3_ready_o;
    wire c4_ack_out_n, c4_ack_out_s, c4_ready_o;

    wire [31:0] result_out; wire result_fire;
    reg cons_ready = 1, cons_ack = 0;

    // ── Cell 1: NOT_A ──
    nano_gate_v4 #(.CELL_ID(16'h1001), .ENABLE_DYNAMIC_ROUTING(1'b0)) CELL1 (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfg1), .cfg_data(cfg_d1),
        .data_in_n(cond_val), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(cond_pulse1_n | cond_pulse2_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(c1_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(c1_fire_e), .fire_w(),
        .ready_out(c1_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(c3_ready_in_w_from_readyout1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(c3_ack_out_w), .ack_in_w(1'b0),
        .freeze_in(1'b0), .hold_in(1'b0), .fb_internal_in(1'b0), .a_reemit_in(1'b0),
        .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    // ── Cell 2: AND(cond, a) ──
    nano_gate_v4 #(.CELL_ID(16'h1002), .ENABLE_DYNAMIC_ROUTING(1'b0)) CELL2 (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfg2), .cfg_data(cfg_d2),
        .data_in_n(cond_val), .data_in_s(a_val), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(cond_pulse_c2n), .arrived_s(a_pulse_c2s), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(c2_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(c2_fire_e), .fire_w(),
        .ready_out(c2_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(c4_ack_out_n), .ack_in_w(1'b0),
        .freeze_in(1'b0), .hold_in(1'b0), .fb_internal_in(1'b0), .a_reemit_in(1'b0),
        .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    // ── Cell 3: AND(NOT(cond) [from Cell1], b) ──
    nano_gate_v4 #(.CELL_ID(16'h1003), .ENABLE_DYNAMIC_ROUTING(1'b0)) CELL3 (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfg3), .cfg_data(cfg_d3),
        .data_in_n(32'h0), .data_in_s(b_val), .data_in_e(32'h0), .data_in_w(c1_dout_e),
        .arrived_n(1'b0), .arrived_s(b_pulse_c3s), .arrived_e(1'b0), .arrived_w(c1_fire_e),
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
    assign c3_ready_in_w_from_readyout1 = c3_ready_o;

    // ── Cell 4: OR(Cell2's real output, Cell3's real output) ──
    nano_gate_v4 #(.CELL_ID(16'h1004), .ENABLE_DYNAMIC_ROUTING(1'b0)) CELL4 (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfg4), .cfg_data(cfg_d4),
        .data_in_n(c2_dout_e), .data_in_s(c3_dout_e), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(c2_fire_e), .arrived_s(c3_fire_e), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(result_out), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(result_fire), .fire_w(),
        .ready_out(c4_ready_o),
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

    task run_select(input [31:0] cond, input [31:0] a, input [31:0] b, input [31:0] want, input [63:0] label);
        begin
            // real reset between real, independent trials -- avoids any
            // stale a_arrived leftover state (matches #626's own real
            // lesson: cfg_valid alone does not clear a_arrived).
            rst = 1'b1; #10; rst = 1'b0; #10;
            cfg1 = 1; cfg_d1 = mk_cfg(TOPO_NOT_A, DIR_E6); #10; cfg1 = 0;
            cfg2 = 1; cfg_d2 = mk_cfg(TOPO_AND,   DIR_E6); #10; cfg2 = 0;
            cfg3 = 1; cfg_d3 = mk_cfg(TOPO_AND,   DIR_E6); #10; cfg3 = 0;
            cfg4 = 1; cfg_d4 = mk_cfg(TOPO_OR,    DIR_E6); #10; cfg4 = 0;
            #10;

            cond_val = cond; a_val = a; b_val = b;

            // Cell1: NOT(cond) -- two real arrivals of cond (2nd ignored by NOT_A)
            cond_pulse1_n = 1'b1; #10; cond_pulse1_n = 1'b0; #20;
            cond_pulse2_n = 1'b1; #10; cond_pulse2_n = 1'b0; #20;

            // Cell2: AND(cond, a) -- two real, STAGGERED arrivals (never
            // simultaneous -- #611's own real, confirmed OR-combine hazard)
            cond_pulse_c2n = 1'b1; #10; cond_pulse_c2n = 1'b0; #20;
            a_pulse_c2s = 1'b1; #10; a_pulse_c2s = 1'b0; #20;

            // Cell3's own first real arrival (Cell1's output) lands
            // automatically via the real wire once Cell1 fires above --
            // wait for it, THEN drive b as the real, staggered second.
            #40;
            b_pulse_c3s = 1'b1; #10; b_pulse_c3s = 1'b0; #40;

            // Real settle time for Cell2/Cell3 to reach Cell4 -- checked
            // directly via simulation whether their own natural pipeline
            // delay keeps them from colliding, not assumed.
            #60;

            checks = checks + 1;
            if (!result_fire || result_out !== want) begin
                $display("[%0t] FAIL (%0s): cond=%h a=%h b=%h -- expected fire=1 val=%h, got fire=%b val=%h",
                          $time, label, cond, a, b, want, result_fire, result_out);
                errors = errors + 1;
            end else begin
                $display("[%0t] check #%0d (%0s): cond=%h a=%h b=%h -> result=%h (correct)",
                          $time, checks, label, cond, a, b, result_out);
                cons_ack = 1'b1; #10; cons_ack = 1'b0; #20;
            end
        end
    endtask

    initial begin
        run_select(32'hFFFFFFFF, 32'hAAAAAAAA, 32'hBBBBBBBB, 32'hAAAAAAAA, "cond=true-selects-a");
        run_select(32'h00000000, 32'hAAAAAAAA, 32'hBBBBBBBB, 32'hBBBBBBBB, "cond=false-selects-b");

        if (checks == 2 && errors == 0)
            $display("PASS: real select(cond,a,b) composed from 4 chained nano_gate_v4 cells -- (cond AND a) OR (NOT(cond) AND b), using only already-proven real gate primitives, confirmed correct for both real outcomes");
        else
            $display("FAIL: checks=%0d errors=%0d", checks, errors);

        $finish;
    end

endmodule
