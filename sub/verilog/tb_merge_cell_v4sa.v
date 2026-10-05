// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design -- see LICENSE-HARDWARE and NOTICE
//
// tb_merge_cell_v4sa.v -- self-checking bench for merge_cell_v4sa.v (the flex MERGE core, ledger #955). Per-case PASS/FAIL, ends with ALL PASS.
// Run:  iverilog -g2012 -o /tmp/tb_m.vvp tb_merge_cell_v4sa.v merge_cell_v4sa.v && vvp /tmp/tb_m.vvp
// Covers the four modes (0 A only, 1 B only, 2 arbitrate, 3 join-OR) and what makes a merge dangerous under a handshake: an item that must be KEPT (not fused with
// the other source's) while the output is pending, round-robin fairness with both sources always valid, join-OR waiting for BOTH, a one-path mode that never accepts the
// other input, backpressure, freeze, and reconfiguration while pending.
`timescale 1ns/1ps
module tb_merge_cell_v4sa;
    reg clk = 0, rst = 1, freeze_in = 0, cfg_valid = 0, va = 0, vb = 0, ack_in = 0;
    reg [31:0] cfg_data = 0, in_a = 0, in_b = 0;
    wire aa, ab, vo;
    wire xa = va & aa, xb = vb & ab;        // a TRANSFER is valid & ready: in join-OR an ack LEVEL can be high with nothing to take
    wire [31:0] d;
    always #5 clk = ~clk;

    merge_cell_v4sa dut (.clk(clk), .rst(rst), .freeze_in(freeze_in), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
                         .in_a(in_a), .valid_in_a(va), .ack_out_a(aa), .in_b(in_b), .valid_in_b(vb), .ack_out_b(ab),
                         .data_out(d), .valid_out(vo), .ack_in(ack_in));

    integer errors = 0, k, seen;
    reg ok;
    task check_cond(input cond, input [1023:0] label);
        begin
            if (!cond) begin $display("FAIL: %0s", label); errors = errors + 1; end
            else $display("PASS: %0s", label);
        end
    endtask
    task step;  begin @(posedge clk); #1; end endtask
    task do_cfg(input [1:0] m); begin cfg_data = {30'b0, m}; cfg_valid = 1; step; cfg_valid = 0; end endtask
    task drain; begin ack_in = 1; step; ack_in = 0; end endtask      // release a pending output

    initial begin
        rst = 1; step; step; rst = 0; step;

        // ---- unarmed ----
        va = 1; vb = 1; in_a = 32'h1; in_b = 32'h2; #1;
        check_cond(aa === 1'b0 && ab === 1'b0, "unarmed: neither input is ready");
        step; check_cond(vo === 1'b0, "unarmed: nothing is captured");
        va = 0; vb = 0;

        // ---- mode 0: A only ----
        do_cfg(0);
        in_a = 32'h11111111; in_b = 32'h22222222; va = 1; vb = 1; #1;
        check_cond(aa === 1'b1 && ab === 1'b0, "mode 0 (A only): A is ready, B is never accepted");
        step; va = 0; vb = 0;
        check_cond(vo === 1'b1 && d === 32'h11111111, "mode 0: A passes through (B ignored)");
        va = 1; in_a = 32'h33333333; #1;
        check_cond(aa === 1'b0, "mode 0: not ready while the output is pending");
        step; check_cond(vo === 1'b1 && d === 32'h11111111, "mode 0: the pending output is held stable; the new item was not captured");
        va = 0; drain;
        check_cond(vo === 1'b0, "mode 0: ack_in releases it");
        vb = 1; in_b = 32'h44444444; #1;
        check_cond(ab === 1'b0, "mode 0: B alone is never accepted");
        step; check_cond(vo === 1'b0, "mode 0: and nothing is captured from it"); vb = 0;

        // ---- mode 1: B only ----
        do_cfg(1);
        in_a = 32'h11111111; in_b = 32'h22222222; va = 1; vb = 1; #1;
        check_cond(ab === 1'b1 && aa === 1'b0, "mode 1 (B only): B is ready, A is never accepted");
        step; va = 0; vb = 0;
        check_cond(vo === 1'b1 && d === 32'h22222222, "mode 1: B passes through (A ignored)");
        drain;
        va = 1; #1; check_cond(aa === 1'b0, "mode 1: A alone is never accepted"); step; check_cond(vo === 1'b0, "mode 1: nothing captured from A"); va = 0;

        // ---- mode 2: arbitrate ----
        do_cfg(2);
        va = 1; in_a = 32'hA0A0A0A0; #1;
        check_cond(aa === 1'b1 && ab === 1'b0, "mode 2 (arbitrate): only A valid -> A granted");
        step; va = 0;
        check_cond(vo === 1'b1 && d === 32'hA0A0A0A0, "mode 2: A's item passes");
        drain;
        vb = 1; in_b = 32'hB0B0B0B0; #1;
        check_cond(ab === 1'b1 && aa === 1'b0, "mode 2: only B valid -> B granted");
        step; vb = 0;
        check_cond(vo === 1'b1 && d === 32'hB0B0B0B0, "mode 2: B's item passes");
        drain;

        do_cfg(2);                                                     // rr = 0: A has priority
        va = 1; vb = 1; in_a = 32'hA1A1A1A1; in_b = 32'hB1B1B1B1; #1;
        check_cond(aa === 1'b1 && ab === 1'b0, "mode 2: both valid -> ONE granted (A first); B is NOT acknowledged");
        step; va = 0;                                                  // A's source transferred and dropped; B's item is retained
        check_cond(vo === 1'b1 && d === 32'hA1A1A1A1, "mode 2: A's item is the output");
        #1; check_cond(ab === 1'b0, "mode 2: B is held off while the output is pending -- its item is KEPT, not fused with A's");
        drain;
        #1; check_cond(ab === 1'b1, "mode 2: once the output is released B is ready");
        step; vb = 0;
        check_cond(vo === 1'b1 && d === 32'hB1B1B1B1, "mode 2: B's item comes out SECOND, intact (two items, not one fused value)");
        drain;

        do_cfg(2);                                                     // fairness: both ALWAYS valid, consumer always ready
        va = 1; vb = 1; in_a = 32'hAAAA0001; in_b = 32'hBBBB0002; ack_in = 1;
        seen = 0; ok = 1;
        for (k = 0; k < 12; k = k + 1) begin
            step;
            if (vo === 1'b1) begin
                if (d !== ((seen % 2 == 0) ? 32'hAAAA0001 : 32'hBBBB0002)) ok = 0;
                seen = seen + 1;
            end
        end
        check_cond(ok && seen === 6, "mode 2 fairness: with both sources always valid the grants alternate A,B,A,B,A,B (no starvation)");
        va = 0; vb = 0; ack_in = 0;

        // ---- mode 2 under backpressure ----
        do_cfg(2);
        va = 1; in_a = 32'hA2A2A2A2; step; va = 0; vb = 1; in_b = 32'hB2B2B2B2;
        ok = 1;
        for (k = 0; k < 3; k = k + 1) begin #1; if (ab !== 1'b0 || d !== 32'hA2A2A2A2 || vo !== 1'b1) ok = 0; step; end
        check_cond(ok, "backpressure: ack_in held low for 3 cycles -> the output stays valid and stable and B is not accepted");
        drain; #1; step; vb = 0;
        check_cond(vo === 1'b1 && d === 32'hB2B2B2B2, "backpressure: after the release B is accepted next");
        drain;

        // ---- mode 3: join-OR ----
        do_cfg(3);
        va = 1; in_a = 32'h0000F0F0; vb = 0; #1;
        check_cond(xa === 1'b0 && xb === 1'b0, "mode 3 (join-OR): A alone is NOT taken (no transfer) -- it waits for B");
        step; check_cond(vo === 1'b0, "mode 3: nothing captured while only one side is present");
        vb = 1; in_b = 32'h00FF00FF; #1;
        check_cond(aa === 1'b1 && ab === 1'b1, "mode 3: both present -> BOTH acknowledged together");
        step; va = 0; vb = 0;
        check_cond(vo === 1'b1 && d === 32'h00FFF0FF, "mode 3: the output is A | B");
        drain;
        vb = 1; #1; check_cond(xa === 1'b0 && xb === 1'b0, "mode 3: B alone is not taken either (no transfer)"); step; check_cond(vo === 1'b0, "mode 3: nothing captured"); vb = 0;
        va = 1; vb = 1; in_a = 32'hAAAAAAAA; in_b = 32'h55555555; step; va = 0; vb = 0;
        check_cond(d === 32'hFFFFFFFF && vo === 1'b1, "mode 3: full width, 0xAAAAAAAA | 0x55555555 = 0xFFFFFFFF");
        drain;
        va = 1; vb = 1; in_a = 32'h80000000; in_b = 32'h80000001; step; va = 0; vb = 0;
        check_cond(d === 32'h80000001, "mode 3: it is an OR, not an AND or a sum");
        drain;

        // ---- freeze, reconfigure while pending ----
        do_cfg(2);
        freeze_in = 1; va = 1; in_a = 32'hC0C0C0C0; #1;
        check_cond(aa === 1'b0 && ab === 1'b0, "freeze: no input is ready");
        step; check_cond(vo === 1'b0, "freeze: nothing is captured"); freeze_in = 0; va = 0;
        va = 1; step; va = 0;
        check_cond(vo === 1'b1, "after the freeze lifts an item is captured");
        do_cfg(0);
        check_cond(vo === 1'b0, "reconfiguring while an output is pending clears it (a fresh start)");

        if (errors == 0) $display("ALL PASS");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
