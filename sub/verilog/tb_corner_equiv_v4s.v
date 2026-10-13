// tb_corner_equiv_v4s.v -- ledger #1165: the NATIVE sub cross / corner tile against the four ram_cell_v4s relays it replaces, compared EVERY CLOCK on every data and valid output under random
// offers (valid_in with fresh random data). Three tiles (cross, corner turn 0, corner turn 1). BREAK = 1 wires the reference wrong on purpose and the run must then report mismatches.
`timescale 1ns / 1ps
module tb_corner_equiv_v4s;
    parameter BREAK = 0;
    parameter CYCLES = 30000;
    reg clk = 0, rst = 1, cfg_valid = 0;
    always #5 clk = ~clk;
    integer mism = 0, cyc = 0;
    reg [31:0] lfsr = 32'hBEEF_1234;
    function [31:0] nxt(input [31:0] x); begin nxt = {x[30:0], x[31] ^ x[21] ^ x[1] ^ x[0]}; end endfunction
    reg [31:0] d_n, d_s, d_e, d_w;
    reg v_n, v_s, v_e, v_w;
    function [1:0] pcross(input [1:0] f); begin case (f) 0: pcross = 1; 1: pcross = 0; 2: pcross = 3; default: pcross = 2; endcase end endfunction
    function [1:0] pt0(input [1:0] f);    begin case (f) 0: pt0 = 2; 1: pt0 = 3; 2: pt0 = 0; default: pt0 = 1; endcase end endfunction
    function [1:0] pt1(input [1:0] f);    begin case (f) 0: pt1 = 3; 1: pt1 = 2; 2: pt1 = 1; default: pt1 = 0; endcase end endfunction
    wire [31:0] din [0:3];
    assign din[0] = d_n; assign din[1] = d_s; assign din[2] = d_e; assign din[3] = d_w;
    wire [3:0] vin = {v_w, v_e, v_s, v_n};

    genvar V;
    generate for (V = 0; V < 3; V = V + 1) begin : T
        wire [31:0] do_n, do_s, do_e, do_w; wire vo_n, vo_s, vo_e, vo_w;
        corner_cell_v4s #(.CROSS(V == 0), .TURN(V == 2)) dut (.clk(clk), .rst(rst), .cfg_valid(cfg_valid),
            .din_n(d_n), .din_s(d_s), .din_e(d_e), .din_w(d_w), .valid_in_n(v_n), .valid_in_s(v_s), .valid_in_e(v_e), .valid_in_w(v_w),
            .data_out_n(do_n), .data_out_s(do_s), .data_out_e(do_e), .data_out_w(do_w), .valid_out_n(vo_n), .valid_out_s(vo_s), .valid_out_e(vo_e), .valid_out_w(vo_w));
        wire [31:0] rd [0:3]; wire [3:0] rv;
        genvar L;
        for (L = 0; L < 4; L = L + 1) begin : R
            ram_cell_v4s relay (.clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(32'h0), .cfg_fixed_mode(1'b0), .data_in(din[L]), .valid_in(vin[L]), .data_out(rd[L]), .valid_out(rv[L]));
        end
        wire [1:0] qn0 = (V == 0) ? pcross(0) : (V == 1) ? pt0(0) : pt1(0);
        wire [1:0] qn = (BREAK != 0) ? ((qn0 + 1) & 3) : qn0;
        wire [1:0] qs = (V == 0) ? pcross(1) : (V == 1) ? pt0(1) : pt1(1);
        wire [1:0] qe = (V == 0) ? pcross(2) : (V == 1) ? pt0(2) : pt1(2);
        wire [1:0] qw = (V == 0) ? pcross(3) : (V == 1) ? pt0(3) : pt1(3);
        always @(negedge clk) if (!rst) begin
            if (do_n !== rd[qn] || do_s !== rd[qs] || do_e !== rd[qe] || do_w !== rd[qw]) mism = mism + 1;
            if ({vo_n, vo_s, vo_e, vo_w} !== {rv[qn], rv[qs], rv[qe], rv[qw]}) mism = mism + 1;
        end
    end endgenerate

    always @(posedge clk) begin
        cyc <= cyc + 1;
        lfsr = nxt(nxt(nxt(lfsr)));
        v_n <= lfsr[0] & lfsr[3]; v_s <= lfsr[1] | lfsr[4]; v_e <= lfsr[2]; v_w <= lfsr[5] ^ lfsr[9];
        d_n <= lfsr ^ 32'h1111; d_s <= {lfsr[15:0], lfsr[31:16]} ^ 32'h2222; d_e <= ~lfsr; d_w <= {lfsr[7:0], lfsr[31:8]};
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
