// tb_div_cell_v4.v -- ledger #1073. Bench for div_cell_v4 and div_cell_v4c (the cardinal division core).
//   iverilog -g2012 -DCELL=div_cell_v4  -DSTEPS=4 -DHAS_ADDON -o t div_cell_v4.v <addon files> tb_div_cell_v4.v && vvp t
//   iverilog -g2012 -DCELL=div_cell_v4c -DSTEPS=4            -o t div_cell_v4c.v tb_div_cell_v4.v && vvp t
// Reference: Verilog's own / and % (divide by zero: quotient all ones, remainder = dividend).
// Checks: quotient; second word on a separate face; second word on the same face (order); rem_primary (both orders, and the remainder alone);
// division by zero; the exact busy latency ceil(32/STEPS) (+1 to see the data valid); ready_out low while a dividend is held and the loop runs;
// no new operand taken meanwhile when two words are due; live reprogramming of rem_primary through the programming channel;
// freeze in the middle of the loop; reconfigure in the middle discards the operation; active = 0 silences the cell; addon (v4 only).
`timescale 1ns / 1ps
`ifndef CELL
`define CELL div_cell_v4
`endif
`ifndef STEPS
`define STEPS 1
`endif
module tb_div_cell_v4;
    localparam LAT = (32 + `STEPS - 1) / `STEPS;
    reg clk = 0; always #5 clk = ~clk;
    reg rst = 1, cfg = 0; reg [63:0] cfg_d = 0;
    reg [31:0] din_w = 0; reg arr_w = 0;
    reg active = 1, freeze = 0;
    reg program_in = 0; reg [31:0] prog_d = 0; reg prog_arr = 0;
    wire [31:0] do_e, do_s; wire f_e, f_s, ack_w, rdy, st_dv, st_aa;
    reg ak_e = 0, ak_s = 0;
    `CELL #(.STEPS(`STEPS)) DUT (.clk(clk), .rst(rst), .active(active), .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(din_w),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(arr_w),
        .data_out_n(), .data_out_s(do_s), .data_out_e(do_e), .data_out_w(),
        .fire_n(), .fire_s(f_s), .fire_e(f_e), .fire_w(), .ready_out(rdy),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(ack_w),
        .ack_in_n(1'b0), .ack_in_s(ak_s), .ack_in_e(ak_e), .ack_in_w(1'b0),
        .program_in(program_in), .program_done(),
        .prog_data_in_n(prog_d), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(prog_arr), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .freeze_in(freeze), .status_data_valid(st_dv), .status_a_arrived(st_aa));

    integer errors = 0, checks = 0, ne = 0, ns = 0, cyc = 0, t0 = 0, t1 = 0, lat_seen = 0, lat_n = 0;
    reg [31:0] ev [0:63]; reg [31:0] sv [0:63];
    // handshake consumer on east and south: take a word on fire when no ack is in flight, ack it for one cycle
    always @(posedge clk) begin
        cyc <= cyc + 1;
        ak_e <= 1'b0; ak_s <= 1'b0;
        if (f_e && !ak_e) begin ev[ne] = do_e; ne = ne + 1; ak_e <= 1'b1; end
        if (f_s && !ak_s) begin sv[ns] = do_s; ns = ns + 1; ak_s <= 1'b1; end
    end
    // latency monitor: the divisor is taken on the edge where ack_w is high with the dividend held; the result is "valid" (status) LAT+1 edges later
    reg watching = 0;
    always @(posedge clk) begin
        if (ack_w && st_aa && !watching) begin t0 = cyc; watching = 1; end
        else if (watching && st_dv) begin t1 = cyc; watching = 0; lat_seen = t1 - t0; lat_n = lat_n + 1; end
    end
    reg ack_seen = 0;
    always @(posedge clk) if (ack_w) ack_seen <= 1'b1;
    task send(input [31:0] v);
        begin din_w = v; arr_w = 1; @(posedge clk); while (!ack_w) @(posedge clk); arr_w = 0; @(posedge clk); end
    endtask
    // cfg: east = first word, south = second word when sdown = 6'b000010
    task conf(input remp, input second, input [5:0] sdown, input inv);
        begin
            @(posedge clk); cfg = 1;
            cfg_d = 64'h0; cfg_d[5:0] = 6'b000100; cfg_d[11:6] = 6'b001000; cfg_d[12] = remp; cfg_d[33] = second; cfg_d[39:34] = sdown;
            cfg_d[32] = inv;      // addon_config[19] = invert_en (v4 only; reserved in v4c)
            @(posedge clk); cfg = 0; ne = 0; ns = 0; repeat (3) @(posedge clk);
        end
    endtask
    task chk(input c, input [255:0] m); begin checks = checks + 1; if (!c) begin $display("FAIL: %0s (STEPS=%0d ne=%0d ns=%0d)", m, `STEPS, ne, ns); errors = errors + 1; end end endtask
    function [31:0] qf(input [31:0] a, input [31:0] b); qf = (b == 0) ? 32'hFFFFFFFF : a / b; endfunction
    function [31:0] rf(input [31:0] a, input [31:0] b); rf = (b == 0) ? a : a % b; endfunction
    task settle; begin repeat (LAT + 40) @(posedge clk); end endtask
    task prog(input [2:0] id, input [19:0] w);
        begin
            program_in = 1; @(posedge clk);
            prog_d = {9'b0, id, w}; prog_arr = 1; repeat (2) @(posedge clk); prog_arr = 0; @(posedge clk);
            program_in = 0; @(posedge clk);
        end
    endtask

    integer t, k;
    reg [31:0] ra, rb, base_ne, base_ns;
    initial begin
        #22 rst = 0;
        // 1. quotient only, east
        conf(0, 0, 6'b000000, 0);
        send(32'd100); send(32'd7); settle;
        chk(ne == 1 && ns == 0 && ev[0] == 14, "100 / 7 = 14, one word");
        chk(lat_n == 1 && lat_seen == LAT + 1, "exact busy latency ceil(32/STEPS), data valid one edge later");
        send(32'd7); send(32'd100); settle;           // roles by arrival order: the first is the dividend
        chk(ev[1] == 0, "7 / 100 = 0 (dividend arrives first)");
        send(32'hFFFFFFFF); send(32'd1); settle;     chk(ev[2] == 32'hFFFFFFFF, "FFFFFFFF / 1");
        send(32'hFFFFFFFF); send(32'hFFFFFFFF); settle; chk(ev[3] == 1, "FFFFFFFF / FFFFFFFF = 1");
        send(32'd5); send(32'd0); settle;            chk(ev[4] == 32'hFFFFFFFF, "5 / 0 = all ones");
        send(32'd0); send(32'd0); settle;            chk(ev[5] == 32'hFFFFFFFF, "0 / 0 = all ones");
        send(32'h80000000); send(32'd3); settle;     chk(ev[6] == 32'h2AAAAAAA, "top bit set / 3");
        send(32'd0); send(32'd9); settle;            chk(ev[7] == 0, "0 / 9");
        chk(ne == 8 && ns == 0, "eight words, nothing south");
        // random operands against the native operators
        for (t = 0; t < 40; t = t + 1) begin
            ra = $urandom; rb = $urandom;
            if (t % 3 == 1) rb = rb >> ($urandom % 32);
            if (t % 3 == 2) ra = ra >> ($urandom % 32);
            base_ne = ne; send(ra); send(rb); settle;
            chk(ne == base_ne + 1 && ev[base_ne] === qf(ra, rb), "random quotient");
        end
        // 2. remainder routed apart: quotient east, remainder south
        conf(0, 1, 6'b000010, 0);
        send(32'd100); send(32'd7); settle; send(32'd5); send(32'd0); settle;
        chk(ne == 2 && ns == 2, "apart: two quotients east, two remainders south");
        chk(ev[0] == 14 && sv[0] == 2, "100 / 7 = 14 rem 2");
        chk(ev[1] == 32'hFFFFFFFF && sv[1] == 5, "5 / 0 = all ones rem 5");
        for (t = 0; t < 20; t = t + 1) begin
            ra = $urandom; rb = $urandom >> ($urandom % 32); base_ne = ne; base_ns = ns;
            send(ra); send(rb); settle;
            chk(ne == base_ne + 1 && ns == base_ns + 1 && ev[base_ne] === qf(ra, rb) && sv[base_ns] === rf(ra, rb), "random: quotient east, remainder south");
        end
        // 3. both words on the same face: quotient then remainder, in order
        conf(0, 1, 6'b000000, 0);
        send(32'd100); send(32'd7); settle; send(32'd50); send(32'd8); settle;
        chk(ne == 4 && ns == 0, "together: four words east");
        chk(ev[0] == 14 && ev[1] == 2 && ev[2] == 6 && ev[3] == 2, "q, r, q, r in order");
        // 4. rem_primary: remainder first, quotient second (and the remainder alone)
        conf(1, 1, 6'b000000, 0);
        send(32'd100); send(32'd7); settle;
        chk(ne == 2 && ev[0] == 2 && ev[1] == 14, "rem_primary together: remainder then quotient");
        conf(1, 1, 6'b000010, 0);
        send(32'd100); send(32'd7); settle;
        chk(ne == 1 && ns == 1 && ev[0] == 2 && sv[0] == 14, "rem_primary apart: remainder east, quotient south");
        conf(1, 0, 6'b000000, 0);
        send(32'd100); send(32'd7); settle; send(32'd9); send(32'd0); settle;
        chk(ne == 2 && ns == 0 && ev[0] == 2 && ev[1] == 9, "x mod y alone: one word, 9 mod 0 = 9");
        for (t = 0; t < 20; t = t + 1) begin
            ra = $urandom; rb = $urandom >> ($urandom % 32); base_ne = ne; send(ra); send(rb); settle;
            chk(ne == base_ne + 1 && ev[base_ne] === rf(ra, rb), "random remainder alone");
        end
        // 5. busy: with the dividend held and the divisor accepted, ready_out is low until the loop ends (when it takes more than one clock)
        conf(0, 1, 6'b000010, 0);
        send(32'd1000); din_w = 32'd7; arr_w = 1; @(posedge clk); while (!ack_w) @(posedge clk); arr_w = 0;
        @(posedge clk);
        if (LAT > 1) begin
            chk(!rdy || !st_aa, "busy: not offering a second divisor slot");
            // a new dividend is NOT taken while a two-word result is pending (second_output=1)
            ack_seen = 0; din_w = 32'd77; arr_w = 1; repeat (3) @(posedge clk); chk(!ack_seen, "no new operand taken while busy with two words due"); arr_w = 0;
        end
        settle;
        chk(ne == 1 && ns == 1 && ev[0] == 142 && sv[0] == 6, "1000 / 7 = 142 rem 6 after the busy period");
        // 6. live reprogramming of rem_primary through the programming channel (PROG_ID 2), commit and arm
        conf(0, 0, 6'b000000, 0);
        prog(3'd2, 20'd1); prog(3'd7, 20'd1);
        send(32'd100); send(32'd7); settle;
        chk(ne == 1 && ev[0] == 2, "reprogrammed rem_primary: remainder first");
        prog(3'd2, 20'd0); prog(3'd7, 20'd1);
        send(32'd100); send(32'd7); settle;
        chk(ne == 2 && ev[1] == 14, "reprogrammed back: quotient first");
        prog(3'd4, 20'd1); prog(3'd5, 20'd2); prog(3'd7, 20'd1);       // second_output on, second face south
        send(32'd100); send(32'd7); settle;
        chk(ne == 3 && ns == 1 && ev[2] == 14 && sv[0] == 2, "reprogrammed second_output and second_downstream_mask");
        // 7. freeze in the middle of the loop: nothing moves, the result is right afterwards
        conf(0, 0, 6'b000000, 0);
        send(32'd100); din_w = 32'd7; arr_w = 1; @(posedge clk); while (!ack_w) @(posedge clk); arr_w = 0;
        @(posedge clk); freeze = 1; repeat (LAT + 6) @(posedge clk);
        chk(ne == 0 && !f_e, "frozen: no word offered");
        if (LAT >= 4) chk(!st_dv, "frozen: the loop itself does not advance");
        freeze = 0; settle;
        chk(ne == 1 && ev[0] == 14, "after the freeze: 100 / 7 = 14");
        // 8. reconfigure in the middle of an operation discards it
        send(32'd50); din_w = 32'd3; arr_w = 1; @(posedge clk); while (!ack_w) @(posedge clk); arr_w = 0;
        conf(0, 0, 6'b000000, 0); settle;
        chk(ne == 0, "operation in flight discarded by the reconfigure");
        send(32'd9); send(32'd2); settle;
        chk(ne == 1 && ev[0] == 4, "works normally after the reconfigure");
        // 8b. single-word mode pipelines: the next dividend is taken while the loop runs, but its divisor is NOT until the loop is done
        conf(0, 0, 6'b000000, 0);
        send(32'd1000); send(32'd7);
        send(32'd90);                                            // dividend 2 captured during the busy period
        if (LAT >= 3) chk(st_aa && !rdy, "busy with a dividend held: not ready for a divisor");
        send(32'd4);                                             // divisor 2 waits for the loop to finish
        settle;
        chk(ne == 2 && ev[0] == 142 && ev[1] == 22, "back-to-back pairs: 1000/7 then 90/4, each with its own divisor");
        // 8c. active drops in the middle of the loop: the loop holds, then finishes when active returns
        send(32'd100); din_w = 32'd7; arr_w = 1; @(posedge clk); while (!ack_w) @(posedge clk); arr_w = 0;
        @(posedge clk); active = 0; repeat (LAT + 6) @(posedge clk);
        if (LAT >= 4) chk(!st_dv && ne == 2, "inactive mid-loop: the loop holds");
        active = 1; settle;
        chk(ne == 3 && ev[2] == 14, "after active returns: 100 / 7 = 14");
        // 9. active = 0: fully silent
        active = 0;
        din_w = 32'd10; arr_w = 1; repeat (4) @(posedge clk); chk(!ack_w && !rdy, "inactive: no ack, not ready"); arr_w = 0;
        active = 1; @(posedge clk);
`ifdef HAS_ADDON
        // 10. the addon chain (v4 only): invert_en inverts what is offered
        conf(0, 0, 6'b000000, 1);
        send(32'd100); send(32'd7); settle;
        chk(ne == 1 && ev[0] == ~32'd14, "addon invert on the offered word");
`endif
        if (errors == 0) $display("PASS: %0s STEPS=%0d (%0d checks, busy latency %0d)", "div cell v4/v4c", `STEPS, checks, LAT);
        else $display("FAILED: %0d of %0d checks (STEPS=%0d)", errors, checks, `STEPS);
        $finish;
    end
    initial begin #80000000; $display("FAIL: timeout"); $finish; end
endmodule
