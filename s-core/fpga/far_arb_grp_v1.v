// far_arb_grp_v1.v - far_arb with SUB-ARBITERS: the blocks are put in groups of G (ledger #1494; Alan's idea, 26 Nov: a shared bus with a select instead of one
// wire set per block all the way to the top).  Drop-in for far_arb (same ports).  Cloned from far_arb.v (left as proven).
// Each group has a far_sub_v1: it picks the lowest-numbered requesting block of its group and keeps that ONE request in a register slot, so the 55 request wires of a
// block (valid, write, 21 address, 32 data) only have to reach their group's register, and the groups' slots (not every block) go to the top far_arb (NG = ceil(NB/G)
// requesters).  Costs about one clock more per far-RAM request; one transaction per group at a time (it waits for its acknowledge before taking the next one).
// Priority is still fixed (lower block number first, lower group first), as in far_arb.  The acknowledge data (ack_d) stays one shared 32-bit bus to all blocks.
module far_sub_v1 #(parameter G = 4) (
    input  wire              clk, rst,
    input  wire [G-1:0]      req_v, req_we,
    input  wire [G*21-1:0]   req_a,
    input  wire [G*32-1:0]   req_wd,
    output wire [G-1:0]      req_rdy, ack_v,
    // up to the top arbiter (one requester)
    output wire              up_v, up_we,
    output wire [20:0]       up_a,
    output wire [31:0]       up_wd,
    input  wire              up_rdy, up_ack_v
);
    localparam IW = (G <= 1) ? 1 : $clog2(G);
    reg              s_v = 1'b0, s_we = 1'b0, pend = 1'b0;
    reg  [20:0]      s_a = 21'd0;
    reg  [31:0]      s_wd = 32'd0;
    reg  [IW-1:0]    own = {IW{1'b0}};
    reg  [IW-1:0]    pick; integer k;
    always @* begin
        pick = {IW{1'b0}};
        for (k = G - 1; k >= 0; k = k - 1) if (req_v[k]) pick = k[IW-1:0];
    end
    wire busy = s_v | pend;
    genvar g;
    generate for (g = 0; g < G; g = g + 1) begin : per
        assign req_rdy[g] = !busy && req_v[g] && (pick == g);
        assign ack_v[g]   = pend && up_ack_v && (own == g);
    end endgenerate
    assign up_v = s_v; assign up_we = s_we; assign up_a = s_a; assign up_wd = s_wd;
    always @(posedge clk) begin
        if (rst) begin s_v <= 1'b0; pend <= 1'b0; end
        else begin
            if (!busy && (|req_v)) begin
                s_v <= 1'b1; own <= pick; s_we <= req_we[pick]; s_a <= req_a[pick*21 +: 21]; s_wd <= req_wd[pick*32 +: 32];
            end
            if (s_v && up_rdy) begin s_v <= 1'b0; pend <= 1'b1; end
            else if (pend && up_ack_v) pend <= 1'b0;
        end
    end
endmodule

module far_arb_grp_v1 #(parameter NB = 2, parameter G = 4) (
    input  wire              clk, rst,
    input  wire [NB-1:0]     req_v, req_we,
    input  wire [NB*21-1:0]  req_a,
    input  wire [NB*32-1:0]  req_wd,
    output wire [NB-1:0]     req_rdy, ack_v,
    output wire [31:0]       ack_d,
    output wire              f_req_v, f_req_we,
    output wire [20:0]       f_req_a,
    output wire [31:0]       f_req_wd,
    input  wire              f_req_rdy, f_ack_v,
    input  wire [31:0]       f_ack_d
);
    localparam NG = (NB + G - 1) / G;
    localparam NP = NG * G;
    // pad to whole groups (the unused slots never request)
    wire [NP-1:0]    p_v  = {{(NP-NB){1'b0}}, req_v};
    wire [NP-1:0]    p_we = {{(NP-NB){1'b0}}, req_we};
    wire [NP*21-1:0] p_a  = {{((NP-NB)*21){1'b0}}, req_a};
    wire [NP*32-1:0] p_wd = {{((NP-NB)*32){1'b0}}, req_wd};
    wire [NP-1:0]    p_rdy, p_ack;
    assign req_rdy = p_rdy[NB-1:0];
    assign ack_v   = p_ack[NB-1:0];
    wire [NG-1:0]    u_v, u_we, u_rdy, u_ack;
    wire [NG*21-1:0] u_a;
    wire [NG*32-1:0] u_wd;
    genvar gi;
    generate for (gi = 0; gi < NG; gi = gi + 1) begin : grp
        far_sub_v1 #(.G(G)) sub (.clk(clk), .rst(rst),
            .req_v(p_v[gi*G +: G]), .req_we(p_we[gi*G +: G]), .req_a(p_a[gi*G*21 +: G*21]), .req_wd(p_wd[gi*G*32 +: G*32]),
            .req_rdy(p_rdy[gi*G +: G]), .ack_v(p_ack[gi*G +: G]),
            .up_v(u_v[gi]), .up_we(u_we[gi]), .up_a(u_a[gi*21 +: 21]), .up_wd(u_wd[gi*32 +: 32]), .up_rdy(u_rdy[gi]), .up_ack_v(u_ack[gi]));
    end endgenerate
    far_arb #(.NB(NG)) top (.clk(clk), .rst(rst), .req_v(u_v), .req_we(u_we), .req_a(u_a), .req_wd(u_wd), .req_rdy(u_rdy), .ack_v(u_ack), .ack_d(ack_d),
        .f_req_v(f_req_v), .f_req_we(f_req_we), .f_req_a(f_req_a), .f_req_wd(f_req_wd), .f_req_rdy(f_req_rdy), .f_ack_v(f_ack_v), .f_ack_d(f_ack_d));
endmodule
