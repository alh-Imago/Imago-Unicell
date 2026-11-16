// sdt_selftest.v - memory test that runs inside the FPGA (the UART is far too slow to test 8 MB).
// Writes `count` words, then reads them back and compares.  Data = a function of the address (and a seed), so a wrong address, a stuck bit
// or a stale word all show up.  mode[0] = 1: visit the words in bit-reversed order (needs count = 2^lg), which hops between banks and rows
// on every access; 0: in order.  mode[1] = 1: data = {~addr[15:0], addr[15:0]} (easy to read in a dump); 0: a xorshift hash of addr ^ seed.
// Reports the number of wrong words, the first one (address, expected, got) and the clocks spent writing and reading.
module sdt_selftest (
    input  wire        clk, rst,
    input  wire        start,
    input  wire [1:0]  mode,
    input  wire [4:0]  lg,
    input  wire [20:0] base,
    input  wire [21:0] count,
    input  wire [31:0] seed,
    output reg         run, done,
    output reg  [31:0] err_cnt, first_a, first_exp, first_got, wcyc, rcyc,
    output reg         req_v, req_we,
    output reg  [20:0] req_a,
    output reg  [31:0] req_wd,
    input  wire        req_rdy, ack_v,
    input  wire [31:0] ack_d
);
    localparam [2:0] S_IDLE = 0, S_PW = 1, S_IW = 2, S_AW = 3, S_PR = 4, S_IR = 5, S_AR = 6;
    reg [2:0]  st;
    reg [21:0] i;
    wire [21:0] rev = {i[0],i[1],i[2],i[3],i[4],i[5],i[6],i[7],i[8],i[9],i[10],i[11],i[12],i[13],i[14],i[15],i[16],i[17],i[18],i[19],i[20],i[21]};
    wire [21:0] off = mode[0] ? (rev >> (5'd22 - lg)) : i;
    wire [20:0] cur_a = base + off[20:0];
    function [31:0] xs(input [31:0] x0);
        reg [31:0] x;
        begin x = x0; x = x ^ (x << 13); x = x ^ (x >> 17); x = x ^ (x << 5); xs = x; end
    endfunction
    wire [31:0] cur_d = mode[1] ? {~cur_a[15:0], cur_a[15:0]} : xs(xs({11'd0, cur_a} ^ seed) ^ seed ^ 32'h5A5A5A5A);
    wire last = (i + 1'b1 == count);
    always @(posedge clk) begin
        if (rst) begin st <= S_IDLE; run <= 1'b0; done <= 1'b0; req_v <= 1'b0; req_we <= 1'b0; end
        else begin
            if (st >= S_PW && st <= S_AW) wcyc <= wcyc + 1'b1;
            if (st >= S_PR)               rcyc <= rcyc + 1'b1;
            case (st)
                S_IDLE: if (start) begin i <= 22'd0; err_cnt <= 32'd0; first_a <= 32'd0; first_exp <= 32'd0; first_got <= 32'd0; wcyc <= 32'd0; rcyc <= 32'd0; run <= 1'b1; done <= 1'b0; st <= S_PW; end
                S_PW: begin req_a <= cur_a; req_wd <= cur_d; req_we <= 1'b1; req_v <= 1'b1; st <= S_IW; end
                S_IW: if (req_v && req_rdy) begin req_v <= 1'b0; st <= S_AW; end
                S_AW: if (ack_v) begin if (last) begin i <= 22'd0; st <= S_PR; end else begin i <= i + 1'b1; st <= S_PW; end end
                S_PR: begin req_a <= cur_a; req_we <= 1'b0; req_v <= 1'b1; st <= S_IR; end
                S_IR: if (req_v && req_rdy) begin req_v <= 1'b0; st <= S_AR; end
                S_AR: if (ack_v) begin
                    if (ack_d == cur_d) begin end                 // (written so that an X / Z read counts as wrong in simulation)
                    else begin
                        if (err_cnt == 32'd0) begin first_a <= {11'd0, req_a}; first_exp <= cur_d; first_got <= ack_d; end
                        err_cnt <= err_cnt + 1'b1;
                    end
                    if (last) begin run <= 1'b0; done <= 1'b1; st <= S_IDLE; end else begin i <= i + 1'b1; st <= S_PR; end
                end
                default: st <= S_IDLE;
            endcase
        end
    end
    initial begin st = S_IDLE; run = 0; done = 0; req_v = 0; req_we = 0; req_a = 0; req_wd = 0; err_cnt = 0; first_a = 0; first_exp = 0; first_got = 0; wcyc = 0; rcyc = 0; i = 0; end
endmodule
