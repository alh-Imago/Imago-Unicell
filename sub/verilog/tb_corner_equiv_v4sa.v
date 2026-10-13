// tb_corner_equiv_v4sa.v -- ledger #1165: the NATIVE cross / corner tile against the four ram_cell_v4sa relays it replaces, compared EVERY CLOCK on every output and every backward ack,
// under random offers and random acks. Three tiles (cross, corner turn 0, corner turn 1), each in two widths' worth of stimulus. BREAK = 1 wires the reference WRONG on purpose (the lane for N
// feeds the wrong exit face): the run must then report mismatches (a test that cannot fail proves nothing). Prints "MISMATCHES n" and "RESULT PASS|FAIL".
`timescale 1ns / 1ps
module tb_corner_equiv_v4sa;
    parameter BREAK = 0;
    parameter WIDTH = 32;
    parameter CYCLES = 30000;
    reg clk = 0, rst = 1, cfg_valid = 0;
    always #5 clk = ~clk;
    integer mism = 0, cyc = 0;
    reg [31:0] lfsr = 32'hACE1_2345;
    function [31:0] nxt(input [31:0] x); begin nxt = {x[30:0], x[31] ^ x[21] ^ x[1] ^ x[0]}; end endfunction

    // stimulus, shared by all three pairs
    reg [WIDTH-1:0] d_n, d_s, d_e, d_w;
    reg v_n, v_s, v_e, v_w, a_n, a_s, a_e, a_w;

    // partner tables (face index 0 N, 1 S, 2 E, 3 W) for the three variants
    function [1:0] pcross(input [1:0] f); begin case (f) 0: pcross = 1; 1: pcross = 0; 2: pcross = 3; default: pcross = 2; endcase end endfunction
    function [1:0] pt0(input [1:0] f);    begin case (f) 0: pt0 = 2; 1: pt0 = 3; 2: pt0 = 0; default: pt0 = 1; endcase end endfunction
    function [1:0] pt1(input [1:0] f);    begin case (f) 0: pt1 = 3; 1: pt1 = 2; 2: pt1 = 1; default: pt1 = 0; endcase end endfunction

    genvar V;
    generate for (V = 0; V < 3; V = V + 1) begin : T
        // device under test
        wire [WIDTH-1:0] do_n, do_s, do_e, do_w; wire vo_n, vo_s, vo_e, vo_w; wire ao_n, ao_s, ao_e, ao_w;
        corner_cell_v4sa #(.WIDTH(WIDTH), .CROSS(V == 0), .TURN(V == 2)) dut (.clk(clk), .rst(rst), .freeze_in(1'b0), .cfg_valid(cfg_valid),
            .din_n(d_n), .din_s(d_s), .din_e(d_e), .din_w(d_w), .valid_in_n(v_n), .valid_in_s(v_s), .valid_in_e(v_e), .valid_in_w(v_w),
            .ack_out_n(ao_n), .ack_out_s(ao_s), .ack_out_e(ao_e), .ack_out_w(ao_w),
            .data_out_n(do_n), .data_out_s(do_s), .data_out_e(do_e), .data_out_w(do_w), .valid_out_n(vo_n), .valid_out_s(vo_s), .valid_out_e(vo_e), .valid_out_w(vo_w),
            .ack_in_n(a_n), .ack_in_s(a_s), .ack_in_e(a_e), .ack_in_w(a_w));
        // reference: one ram relay per entering face; its ack_in is the ack of the face it leaves by
        wire [3:0] av = {a_w, a_e, a_s, a_n};
        wire [WIDTH-1:0] rd [0:3]; wire [3:0] rv, rr;
        wire [WIDTH-1:0] din [0:3];
        assign din[0] = d_n; assign din[1] = d_s; assign din[2] = d_e; assign din[3] = d_w;
        wire [3:0] vin = {v_w, v_e, v_s, v_n};
        genvar L;
        for (L = 0; L < 4; L = L + 1) begin : R
            wire [1:0] p0 = (V == 0) ? pcross(L) : (V == 1) ? pt0(L) : pt1(L);
            wire [1:0] p = (BREAK != 0 && L == 0) ? ((p0 + 1) & 3) : p0;
            ram_cell_v4sa #(.WIDTH(WIDTH)) relay (.clk(clk), .rst(rst), .freeze_in(1'b0), .cfg_valid(cfg_valid), .cfg_data({(WIDTH > 32 ? WIDTH : 32){1'b0}}), .cfg_fixed_mode(1'b0),
                .data_in(din[L]), .valid_in(vin[L]), .ack_out(rr[L]), .data_out(rd[L]), .valid_out(rv[L]), .ack_in(av[p]));
        end
        // compare: output face o is fed by lane partner(o); lanes are an involution so partner(o) = the lane whose partner is o
        wire [1:0] qn = (V == 0) ? pcross(0) : (V == 1) ? pt0(0) : pt1(0);
        wire [1:0] qs = (V == 0) ? pcross(1) : (V == 1) ? pt0(1) : pt1(1);
        wire [1:0] qe = (V == 0) ? pcross(2) : (V == 1) ? pt0(2) : pt1(2);
        wire [1:0] qw = (V == 0) ? pcross(3) : (V == 1) ? pt0(3) : pt1(3);
        wire [WIDTH-1:0] exp_dn = rd[qn], exp_ds = rd[qs], exp_de = rd[qe], exp_dw = rd[qw];
        wire exp_vn = rv[qn], exp_vs = rv[qs], exp_ve = rv[qe], exp_vw = rv[qw];
        always @(negedge clk) if (!rst) begin
            if (do_n !== exp_dn || do_s !== exp_ds || do_e !== exp_de || do_w !== exp_dw) mism = mism + 1;
            if ({vo_n, vo_s, vo_e, vo_w} !== {exp_vn, exp_vs, exp_ve, exp_vw}) mism = mism + 1;
            if ({ao_n, ao_s, ao_e, ao_w} !== {rr[0], rr[1], rr[2], rr[3]}) mism = mism + 1;
        end
    end endgenerate

    always @(posedge clk) begin
        cyc <= cyc + 1;
        lfsr = nxt(nxt(nxt(lfsr)));
        // random offers and acks: roughly 1/2 valid, 1/2 ack; data from the LFSR
        v_n <= lfsr[0] & lfsr[3]; v_s <= lfsr[1] | lfsr[4]; v_e <= lfsr[2]; v_w <= lfsr[5] ^ lfsr[9];
        a_n <= lfsr[6] | lfsr[10]; a_s <= lfsr[7] & lfsr[11]; a_e <= lfsr[8]; a_w <= lfsr[12] ^ lfsr[13];
        d_n <= {lfsr, lfsr} ^ 64'h1111; d_s <= {lfsr[15:0], lfsr[31:16], lfsr} ^ 64'h2222; d_e <= ~{lfsr, lfsr}; d_w <= {lfsr, ~lfsr};
        if (cyc == 5) rst <= 0;
        if (cyc == 8) cfg_valid <= 1;
        if (cyc == 9) cfg_valid <= 0;
        if (cyc == CYCLES) begin
            $display("MISMATCHES %0d", mism);
            if (BREAK) $display("RESULT %s", mism > 0 ? "PASS (the deliberately wrong reference was caught)" : "FAIL (the break was NOT caught)");
            else       $display("RESULT %s", mism == 0 ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
