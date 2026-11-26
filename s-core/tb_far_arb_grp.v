// tb_far_arb_grp.v - standalone test of far_arb_grp_v1 against the flat far_arb (ledger #1494).  NB requesters do random reads and writes in their own address
// regions through the arbiter to a RAM model (random 1 to 3 clock latency, random busy gaps); every read is checked against a shadow copy, an acknowledge to a
// block with nothing pending is an error, every block must finish OPS operations.  USE_GRP = 1 tests far_arb_grp_v1, 0 the flat far_arb.
`timescale 1ns/1ps
module tb_far_arb_grp;
    parameter NB = 10, G = 4, USE_GRP = 1, OPS = 150;
    reg clk = 0; always #5 clk = ~clk;
    reg rst = 1;
    reg  [NB-1:0] req_v = 0, req_we = 0; reg [NB*21-1:0] req_a = 0; reg [NB*32-1:0] req_wd = 0;
    wire [NB-1:0] req_rdy, ack_v; wire [31:0] ack_d;
    wire f_req_v, f_req_we, f_req_rdy, f_ack_v; wire [20:0] f_req_a; wire [31:0] f_req_wd, f_ack_d;
    generate if (USE_GRP) begin : g1
        far_arb_grp_v1 #(.NB(NB), .G(G)) dut (.clk(clk), .rst(rst), .req_v(req_v), .req_we(req_we), .req_a(req_a), .req_wd(req_wd), .req_rdy(req_rdy), .ack_v(ack_v), .ack_d(ack_d),
            .f_req_v(f_req_v), .f_req_we(f_req_we), .f_req_a(f_req_a), .f_req_wd(f_req_wd), .f_req_rdy(f_req_rdy), .f_ack_v(f_ack_v), .f_ack_d(f_ack_d));
    end else begin : g0
        far_arb #(.NB(NB)) dut (.clk(clk), .rst(rst), .req_v(req_v), .req_we(req_we), .req_a(req_a), .req_wd(req_wd), .req_rdy(req_rdy), .ack_v(ack_v), .ack_d(ack_d),
            .f_req_v(f_req_v), .f_req_we(f_req_we), .f_req_a(f_req_a), .f_req_wd(f_req_wd), .f_req_rdy(f_req_rdy), .f_ack_v(f_ack_v), .f_ack_d(f_ack_d));
    end endgenerate
    // RAM model
    reg [31:0] mem [0:1023]; integer i;
    reg ram_busy = 0; reg [2:0] cnt = 0; reg [9:0] a_l = 0; reg we_l = 0; reg [31:0] wd_l = 0;
    reg ack_r = 0; reg [31:0] ackd_r = 0; reg [31:0] rl = 32'h9E3779B9; reg gap = 0;
    assign f_req_rdy = !ram_busy && !gap; assign f_ack_v = ack_r; assign f_ack_d = ackd_r;
    always @(posedge clk) begin
        rl <= rl * 1664525 + 1013904223; gap <= rl[20] & rl[21]; ack_r <= 1'b0;
        if (f_req_v && f_req_rdy) begin ram_busy <= 1'b1; cnt <= 1 + (rl[9:8] % 3); a_l <= f_req_a[9:0]; we_l <= f_req_we; wd_l <= f_req_wd; end
        else if (ram_busy) begin
            if (cnt <= 1) begin ram_busy <= 1'b0; ack_r <= 1'b1; if (we_l) begin mem[a_l] <= wd_l; ackd_r <= 32'd0; end else ackd_r <= mem[a_l]; end
            else cnt <= cnt - 1'b1;
        end
    end
    // requesters
    wire [NB-1:0] done_f; wire [NB*16-1:0] errs_f; wire [NB*16-1:0] ops_f;
    reg [31:0] shad [0:NB*32-1];
    genvar k;
    generate for (k = 0; k < NB; k = k + 1) begin : rq
        reg [1:0] st = 0; reg [3:0] dly = 0; reg [31:0] lf = 32'h1234567 + k * 7919; reg cw = 0; reg [4:0] co = 0; reg [31:0] cwd = 0;
        reg [15:0] er = 0, op = 0;
        assign done_f[k] = (op >= OPS); assign errs_f[k*16 +: 16] = er; assign ops_f[k*16 +: 16] = op;
        always @(posedge clk) begin
            lf <= lf * 1664525 + 1013904223;
            if (rst) begin st <= 0; req_v[k] <= 1'b0; dly <= 0; end
            else begin
                if (ack_v[k] && st != 2) er <= er + 1'b1;
                case (st)
                    0: if (op >= OPS) ; else if (dly == 0) begin
                        cw <= lf[7]; co <= lf[16:12]; cwd <= lf ^ 32'hA5A5_0000 ^ k;
                        req_we[k] <= lf[7]; req_a[k*21 +: 21] <= k * 32 + lf[16:12]; req_wd[k*32 +: 32] <= lf ^ 32'hA5A5_0000 ^ k; req_v[k] <= 1'b1; st <= 1;
                    end else dly <= dly - 1'b1;
                    1: if (req_v[k] && req_rdy[k]) begin req_v[k] <= 1'b0; st <= 2; end
                    2: if (ack_v[k]) begin
                        if (!cw && ack_d !== shad[k*32 + co]) er <= er + 1'b1;
                        if (cw) shad[k*32 + co] <= cwd;
                        op <= op + 1'b1; dly <= lf[19:17]; st <= 0;
                    end
                endcase
            end
        end
    end endgenerate
    integer cyc = 0; integer tot, e, kk;
    initial begin
        for (i = 0; i < 1024; i = i + 1) mem[i] = 0;
        for (i = 0; i < NB*32; i = i + 1) shad[i] = 0;
        repeat (4) @(posedge clk); rst = 0;
        while (!(&done_f) && cyc < 400000) begin @(posedge clk); cyc = cyc + 1; end
        e = 0; tot = 0;
        for (kk = 0; kk < NB; kk = kk + 1) begin e = e + errs_f[kk*16 +: 16]; tot = tot + ops_f[kk*16 +: 16]; end
        $display("USE_GRP=%0d NB=%0d G=%0d: cycles %0d, ops %0d, errors %0d -> %s", USE_GRP, NB, G, cyc, tot, e, (e == 0 && (&done_f)) ? "PASS" : "FAIL");
        $finish;
    end
endmodule
