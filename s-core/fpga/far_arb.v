// far_arb.v - lets NB blocks share ONE far RAM (farram_bram_v1 or the DDR3 wrapper: same request / acknowledge interface).  One transaction at a time:
// the lowest-numbered block with a request wins when the RAM is free (fixed priority: a block's copy engine issues one request per ~15 clocks and a
// request takes 1 to 3 clocks, so a block cannot hold another one off for long); the acknowledge goes only to the block that owns the transaction.
// With NB = 1 this is wires only: a block sees exactly the RAM's own req_rdy / ack_v (ledger #1347).  Each requester has at most one request in
// flight and waits for its acknowledge before the next one (far_copy, batch_seq_v2 and the bridge all do).
module far_arb #(parameter NB = 2) (
    input  wire              clk, rst,
    input  wire [NB-1:0]     req_v, req_we,
    input  wire [NB*21-1:0]  req_a,
    input  wire [NB*32-1:0]  req_wd,
    output wire [NB-1:0]     req_rdy, ack_v,
    output wire [31:0]       ack_d,
    // to the far RAM
    output wire              f_req_v, f_req_we,
    output wire [20:0]       f_req_a,
    output wire [31:0]       f_req_wd,
    input  wire              f_req_rdy, f_ack_v,
    input  wire [31:0]       f_ack_d
);
    localparam IW = (NB <= 1) ? 1 : $clog2(NB);
    reg              busy_o = 1'b0;
    reg  [IW-1:0]    owner  = {IW{1'b0}};
    // lowest-numbered requester
    reg  [IW-1:0]    pick;  integer k;
    always @* begin
        pick = {IW{1'b0}};
        for (k = NB - 1; k >= 0; k = k - 1) if (req_v[k]) pick = k[IW-1:0];
    end
    wire [IW-1:0] cur = busy_o ? owner : pick;
    assign f_req_v  = !busy_o && req_v[cur];
    assign f_req_we = req_we[cur];
    assign f_req_a  = req_a[cur*21 +: 21];
    assign f_req_wd = req_wd[cur*32 +: 32];
    genvar g;
    generate for (g = 0; g < NB; g = g + 1) begin : per
        assign req_rdy[g] = !busy_o && (cur == g) && f_req_rdy;
        assign ack_v[g]   = busy_o && (owner == g) && f_ack_v;
    end endgenerate
    assign ack_d = f_ack_d;
    always @(posedge clk) begin
        if (rst) busy_o <= 1'b0;
        else begin
            if (f_req_v && f_req_rdy) begin busy_o <= 1'b1; owner <= cur; end
            else if (busy_o && f_ack_v) busy_o <= 1'b0;
        end
    end
endmodule
