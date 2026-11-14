// bram_char_top.v - characterise the Tang Nano 20K block RAM with no core in the way.
//
// Seven single-port memory shapes (1, 4, 9, 16, 18, 18x512 and 32 bit wide) run side by side, each against a LUT-RAM reference.
// (The simple-dual-port shape SDPX9 cannot be placed by this nextpnr beside the others, so it is not tested.)  Per shape:
//   S0  init scan   read every address before anything is written: how many words are not zero? (expect 0)
//   S1  write all   address 0..N-1, one write per clock, data = hash(address)
//   S2  read all    one read per clock; counts how often the output equals hash(address) read 1 clock ago
//                   (m1, correct for a synchronous read: expect N), the address of this clock (m0, would mean
//                   an asynchronous read), or 2 clocks ago (m2).  errSeq counts reads that differ from m1's rule.
//   S3  random      forever: 2-clock windows exactly like the core (clock 0 read address, clock 1 write address
//                   and write enable; the read is compared with the LUT-RAM copy at clock 1).  errRand counts
//                   differences; the first one is kept (read address, expected word, actual word).
// All shapes time-share ONE address between read and write, like the register file in sc_sys_v5.
// Report: 'C' + 316 hex digits + CR LF about 4 times a second:  tick(32 bit) then 7 records of 176 bits.
// Decode with  python3 read_char.py [port].   LEDs (active low): 0 heartbeat, 1..5 unit 0..4 has an error,
// (units 5 and 6 are only in the report).
module bc_unit #(parameter W = 1, parameter AB = 10, parameter SDP = 0) (
    input  wire         clk,
    input  wire         run,
    output wire [175:0] rec,
    output wire         bad
);
    localparam N = 1 << AB;
    function [31:0] hsh(input [15:0] a);
        reg [31:0] x;
        begin
            x = {a, ~a};
            x = x ^ (x << 13); x = x ^ (x >> 17); x = x ^ (x << 5);
            hsh = x ^ 32'hA5A5C3C3;
        end
    endfunction
    function [31:0] xs(input [31:0] v);
        reg [31:0] x;
        begin x = v; x = x ^ (x << 13); x = x ^ (x >> 17); x = x ^ (x << 5); xs = x; end
    endfunction

    localparam P_INIT = 2'd0, P_WR = 2'd1, P_RD = 2'd2, P_RAND = 2'd3;
    reg [1:0]  ph = P_INIT;
    reg [15:0] idx = 16'd0;
    reg        w = 1'b0;
    reg [31:0] r1 = 32'h1BADB002, r2 = 32'hC0FFEE11;
    wire [AB-1:0] rd_r = r1[AB-1:0];
    wire [AB-1:0] wr_r = r1[15 +: AB];
    wire          we_r = r1[30];
    wire [31:0]   wd_r = r2;

    wire          seq    = (ph != P_RAND);
    wire [AB-1:0] seq_a  = idx[AB-1:0];
    wire          seq_we = (ph == P_WR) && (idx < N);
    wire [31:0]   seq_h  = hsh(idx);
    wire [AB-1:0] ra_in  = seq ? seq_a : rd_r;
    wire [AB-1:0] wa_in  = seq ? seq_a : wr_r;
    wire          we_in  = seq ? seq_we : (we_r & w);
    wire [W-1:0]  wd_in  = seq ? seq_h[W-1:0] : wd_r[W-1:0];
    wire          sel_w  = seq ? seq_we : w;

    // ---- memory under test
    wire [W-1:0] qb;
    generate if (SDP) begin : g_sdp
        (* ram_style = "block" *) reg [W-1:0] m [0:N-1];
        reg [W-1:0] q;
        always @(posedge clk) begin if (we_in) m[wa_in] <= wd_in; q <= m[ra_in]; end
        assign qb = q;
    end else begin : g_sp
        (* ram_style = "block" *) reg [W-1:0] m [0:N-1];
        reg [W-1:0] q;
        wire [AB-1:0] a = sel_w ? wa_in : ra_in;
        always @(posedge clk) begin if (we_in) m[a] <= wd_in; q <= m[a]; end
        assign qb = q;
    end endgenerate
    // ---- LUT-RAM reference (separate read/write addresses; only the random phase uses it)
    (* ram_style = "distributed" *) reg [W-1:0] rm [0:N-1];
    reg [W-1:0] rq;
    always @(posedge clk) begin if (we_in) rm[wa_in] <= wd_in; rq <= rm[ra_in]; end
`ifndef SYNTHESIS
    integer zi;
    initial for (zi = 0; zi < N; zi = zi + 1) rm[zi] = 0;
    generate if (SDP) begin : i_sdp
        initial for (zi = 0; zi < N; zi = zi + 1) g_sdp.m[zi] = 0;
    end else begin : i_sp
        initial for (zi = 0; zi < N; zi = zi + 1) g_sp.m[zi] = 0;
    end endgenerate
`endif

    // ---- measurements
    reg [15:0] nz = 0, errSeq = 0, m0 = 0, m1 = 0, m2 = 0, errR = 0, faddr = 0;
    reg [31:0] fexp = 0, fact = 0;
    reg        seen = 0, v1 = 0, v2 = 0;
    reg [15:0] a1 = 0, a2 = 0;
    wire [31:0] qz = {{(32-W){1'b0}}, qb};
    wire [31:0] h1 = hsh(a1) & ((W == 32) ? 32'hFFFFFFFF : ((32'd1 << W) - 1));
    wire [31:0] h0 = hsh(idx) & ((W == 32) ? 32'hFFFFFFFF : ((32'd1 << W) - 1));
    wire [31:0] h2 = hsh(a2) & ((W == 32) ? 32'hFFFFFFFF : ((32'd1 << W) - 1));
    always @(posedge clk) if (run) begin
        v1 <= 1'b0; v2 <= v1; a2 <= a1;
        case (ph)
            P_INIT: begin
                v1 <= (idx < N); a1 <= idx;
                if (v1 && qb != 0 && nz != 16'hFFFF) nz <= nz + 1'b1;
                if (idx == N + 1) begin ph <= P_WR; idx <= 0; end else idx <= idx + 1'b1;
            end
            P_WR: begin
                if (idx == N) begin ph <= P_RD; idx <= 0; end else idx <= idx + 1'b1;
            end
            P_RD: begin
                v1 <= (idx < N); a1 <= idx;
                if (v1) begin
                    if (qz == h1) m1 <= m1 + 1'b1; else if (errSeq != 16'hFFFF) errSeq <= errSeq + 1'b1;
                end
                if (idx < N && idx != 0 && qz == h0) m0 <= m0 + 1'b1;
                if (v2 && qz == h2) m2 <= m2 + 1'b1;
                if (idx == N + 1) begin ph <= P_RAND; idx <= 0; w <= 1'b0; end else idx <= idx + 1'b1;
            end
            P_RAND: begin
                w <= ~w;
                if (w) begin
                    if (qb != rq) begin
                        if (errR != 16'hFFFF) errR <= errR + 1'b1;
                        if (!seen) begin seen <= 1'b1; faddr <= {{(16-AB){1'b0}}, rd_r}; fexp <= {{(32-W){1'b0}}, rq}; fact <= qz; end
                    end
                    r1 <= xs(r1); r2 <= xs(r2);
                end
            end
        endcase
    end
    assign rec = {nz, errSeq, m0, m1, m2, errR, faddr, fexp, fact};
    assign bad = (errR != 0) || (errSeq != 0) || (nz != 0);
endmodule

module bram_char_top #(parameter BAUD_DIV = 234, parameter GAPBIT = 23) (
    input  wire       clk,
    input  wire       uart_rx,
    output wire       uart_tx,
    output wire [5:0] led_n
);
    reg [7:0] por = 8'd0;
    wire por_done = (por == 8'hFF);
    always @(posedge clk) if (!por_done) por <= por + 1'b1;
    wire run = por_done;

    wire [175:0] r0, r1, r2, r3, r4, r5, r6;
    wire b0, b1, b2, b3, b4, b5, b6;
    bc_unit #(.W(1),  .AB(10), .SDP(0)) u0 (.clk(clk), .run(run), .rec(r0), .bad(b0));
    bc_unit #(.W(4),  .AB(8),  .SDP(0)) u1 (.clk(clk), .run(run), .rec(r1), .bad(b1));
    bc_unit #(.W(9),  .AB(8),  .SDP(0)) u2 (.clk(clk), .run(run), .rec(r2), .bad(b2));
    bc_unit #(.W(18), .AB(8),  .SDP(0)) u3 (.clk(clk), .run(run), .rec(r3), .bad(b3));
    bc_unit #(.W(32), .AB(5),  .SDP(0)) u4 (.clk(clk), .run(run), .rec(r4), .bad(b4));
    bc_unit #(.W(16), .AB(8),  .SDP(0)) u5 (.clk(clk), .run(run), .rec(r5), .bad(b5));
    bc_unit #(.W(18), .AB(9),  .SDP(0)) u6 (.clk(clk), .run(run), .rec(r6), .bad(b6));

    reg [31:0] tick = 0;
    always @(posedge clk) tick <= tick + 1'b1;

    // ---- report: 'C', 316 hex digits, CR, LF, pause
    localparam NIB = 316;
    wire [1263:0] live = {tick, r0, r1, r2, r3, r4, r5, r6};
    reg  [1263:0] snap;
    reg  [8:0]    idx = 9'd0;
    reg  [23:0]   gap = 24'd0;
    reg  [7:0]    data = 8'h43;
    reg           send = 1'b0;
    wire          busy;
    uart_tx #(.DIV(BAUD_DIV)) utx (.clk(clk), .data(data), .send(send), .tx(uart_tx), .busy(busy));
    wire [3:0] nib = snap[(NIB - idx) * 4 +: 4];
    wire [7:0] hexch = (nib < 4'd10) ? (8'd48 + nib) : (8'd55 + nib);
    always @(posedge clk) begin
        send <= 1'b0;
        if (!por_done) begin idx <= NIB + 3; gap <= 24'd0; end
        else if (idx == NIB + 3) begin
            gap <= gap + 1'b1;
            if (gap[GAPBIT]) begin gap <= 24'd0; snap <= live; idx <= 9'd0; end
        end else if (!busy && !send) begin
            send <= 1'b1; idx <= idx + 1'b1;
            if (idx == 0)            data <= 8'h43;
            else if (idx <= NIB)     data <= hexch;
            else if (idx == NIB + 1) data <= 8'h0D;
            else                     data <= 8'h0A;
        end
    end

    reg [24:0] hb = 0;
    always @(posedge clk) hb <= hb + 1'b1;
    assign led_n = ~{b4, b3, b2, b1, b0, hb[24]};
endmodule
