// bram_probe_top.v - find out why the single-port block-RAM register file fails on the Tang Nano 20K.
//
// One real 1-bit core (uc_core_v2s) runs a register-file stress program forever.  It is fed from a LUT-RAM
// register file (the configuration that passes on the board).  Beside it, several block-RAM register files
// receive exactly the same addresses, write enables and data, each coded differently (V0 = as in sc_sys_v5,
// V1 = write-through, V2 = no-change).  Every time the core consumes a read (the clock where cph = 1), each
// block-RAM copy's output is compared with the LUT-RAM output.  A mismatch is counted and the first one is
// recorded with its address, so the board tells us WHICH accesses go wrong and WHICH coding is fine.
// The data memory is checked the same way (block RAM as in sc_sys_v5 vs LUT-RAM).
//
// Report: one line over the UART (115200 8N1) about 4 times a second:  Q + 188 hex digits + CR LF.
// Decode it with  python3 read_probe.py [port].   LEDs (active low): 0 heartbeat, 1 core running,
// 2 any V0 mismatch, 3 any V1 mismatch, 4 any V2 mismatch, 5 any mismatch of the falling-edge data memory.
module bp_rport #(parameter V = 0, parameter BLK = 1, parameter NEG = 0) (
    input  wire       clk,
    input  wire       sel,        // 1 = write address phase (cph), 0 = read address phase
    input  wire       we,         // write enable (already gated with cph)
    input  wire [9:0] rd_addr,
    input  wire [9:0] wr_addr,
    input  wire       wd,
    output reg        q
);
    wire [9:0] a0 = sel ? wr_addr : rd_addr;
    // NEG=1: address, write enable and data are re-registered on the FALLING edge, so the block RAM sees inputs that
    // have been stable for half a cycle before the rising edge that samples them (hold-time test)
    reg [9:0] a_n = 10'd0; reg we_n = 1'b0, wd_n = 1'b0;
    always @(negedge clk) begin a_n <= a0; we_n <= we; wd_n <= wd; end
    wire [9:0] a  = NEG ? a_n  : a0;
    wire       wen = NEG ? we_n : we;
    wire       wdi = NEG ? wd_n : wd;
    integer zi;
    generate if (BLK) begin : g_blk
        (* ram_style = "block" *) reg m [0:1023];
`ifndef SYNTHESIS
        initial for (zi = 0; zi < 1024; zi = zi + 1) m[zi] = 1'b0;
`endif
        if (V == 0) begin : v0                        // read-before-write, exactly as sc_sys_v5
            always @(posedge clk) begin if (wen) m[a] <= wdi; q <= m[a]; end
        end else if (V == 1) begin : v1               // write-through
            always @(posedge clk) begin if (wen) begin m[a] <= wdi; q <= wdi; end else q <= m[a]; end
        end else begin : v2                           // no-change on write
            always @(posedge clk) begin if (wen) m[a] <= wdi; else q <= m[a]; end
        end
    end else begin : g_dist
        (* ram_style = "distributed" *) reg m [0:1023];
`ifndef SYNTHESIS
        initial for (zi = 0; zi < 1024; zi = zi + 1) m[zi] = 1'b0;
`endif
        always @(posedge clk) begin if (wen) m[a] <= wdi; q <= m[a]; end
    end endgenerate
endmodule

// compares two block-RAM read results against the reference at every core step and keeps a 144-bit record
module bp_chk (
    input  wire        clk,
    input  wire        run,       // checking enabled (out of reset)
    input  wire        cph,
    input  wire [31:0] step,
    input  wire        wr,        // a write happens at this step
    input  wire [9:0]  wa,
    input  wire [9:0]  ra, rb,
    input  wire        ea, aa,    // expected (LUT-RAM) / actual (block RAM) read A
    input  wire        eb, ab,
    output wire [143:0] rec,
    output wire        any
);
    reg [15:0] cntA = 0, cntB = 0;
    reg [31:0] fstep = 0;
    reg [9:0]  fra = 0, frb = 0;
    reg [3:0]  fbits = 0;
    reg [9:0]  orA = 0, andA = 10'h3FF, orB = 0, andB = 10'h3FF;
    reg [3:0]  fflags = 0;
    reg [9:0]  lw1 = 10'h3FF, lw2 = 10'h3FF;     // the two most recent write addresses
    reg        seen = 0;
    wire misA = (ea != aa), misB = (eb != ab);
    always @(posedge clk) if (run && cph) begin
        if (wr) begin lw1 <= wa; lw2 <= lw1; end
        if (misA) begin
            if (cntA != 16'hFFFF) cntA <= cntA + 1'b1;
            orA <= orA | ra; andA <= andA & ra;
        end
        if (misB) begin
            if (cntB != 16'hFFFF) cntB <= cntB + 1'b1;
            orB <= orB | rb; andB <= andB & rb;
        end
        if ((misA | misB) && !seen) begin
            seen <= 1'b1; fstep <= step; fra <= ra; frb <= rb; fbits <= {ea, aa, eb, ab};
            fflags <= {misA && ra == lw1, misA && ra == lw2, misB && rb == lw1, misB && rb == lw2};
        end
    end
    assign any = seen;
    assign rec = {cntA, cntB, fstep, 2'b00, fra, 2'b00, frb, fbits,
                  2'b00, orA, 2'b00, andA, 2'b00, orB, 2'b00, andB, fflags};
endmodule

module bram_probe_top #(parameter BAUD_DIV = 234, parameter GAPBIT = 23) (
    input  wire       clk,
    input  wire       uart_rx,
    output wire       uart_tx,
    output wire [5:0] led_n
);
    // ---- power-on reset, step phase
    reg [7:0] por = 8'd0;
    wire por_done = (por == 8'hFF);
    always @(posedge clk) if (!por_done) por <= por + 1'b1;
    wire rst = !por_done;
    reg cph = 1'b0;
    always @(posedge clk) cph <= rst ? 1'b0 : ~cph;     // same as sc_sys_v5

    // ---- instruction ROM (synchronous read, like the private instruction memory of sc_sys_v5)
    wire [29:0] ia;
    reg  [31:0] id_q;
    function [31:0] rom_f(input [7:0] a);
        case (a)
`include "bram_probe_rom.vh"
            default: rom_f = 32'h0000006f;               // j .
        endcase
    endfunction
    always @(posedge clk) id_q <= rom_f(ia[7:0]);

    // ---- the core, fed from the LUT-RAM (reference) memories
    wire [9:0] ra, rb, rwa;
    wire       rwe, rwd, dwe, dwd;
    wire [34:0] da;                                     // d_addr is KW+30 bits wide; only the low bits matter
    wire       rad_ref, rbd_ref, drd_ref;
    wire       halted, trap;
    uc_core_v2s #(.W(1)) core (
        .clk(clk), .rst(rst), .start(1'b1), .entry(32'd0), .ce(cph),
        .halted(halted), .trap(trap),
        .imem_addr(ia), .imem_data(id_q),
        .ra_addr(ra), .ra_data(rad_ref), .rb_addr(rb), .rb_data(rbd_ref),
        .rw_en(rwe), .rw_addr(rwa), .rw_data(rwd),
        .d_addr(da), .d_we(dwe), .d_wdata(dwd), .d_rdata(drd_ref));

    wire we = rwe & cph;
    // reference register file (LUT-RAM), both read ports
    wire ref_a, ref_b;
    bp_rport #(.V(0), .BLK(0)) rfa_ref (.clk(clk), .sel(cph), .we(we), .rd_addr(ra), .wr_addr(rwa), .wd(rwd), .q(ref_a));
    bp_rport #(.V(0), .BLK(0)) rfb_ref (.clk(clk), .sel(cph), .we(we), .rd_addr(rb), .wr_addr(rwa), .wd(rwd), .q(ref_b));
    assign rad_ref = ref_a;
    assign rbd_ref = ref_b;

    // reference data memory (LUT-RAM, 512 bits = 16 words, same size as DMW = 16) and its block-RAM twin
    wire [8:0] dadr = da[8:0];
    (* ram_style = "distributed" *) reg dm_ref [0:511];
    (* ram_style = "block" *)       reg dm_blk [0:511];
    reg dq_ref, dq_blk;
    integer zd;
`ifndef SYNTHESIS
    initial for (zd = 0; zd < 512; zd = zd + 1) begin dm_ref[zd] = 1'b0; dm_blk[zd] = 1'b0; end
`endif
    always @(posedge clk) begin
        if (dwe & cph) begin dm_ref[dadr] <= dwd; dm_blk[dadr] <= dwd; end
        dq_ref <= dm_ref[dadr];
        dq_blk <= dm_blk[dadr];
    end
    assign drd_ref = dq_ref;
    // data memory, block RAM, inputs re-registered on the falling edge
    reg [8:0] dadr_n = 9'd0; reg dwe_n = 1'b0, dwd_n = 1'b0;
    always @(negedge clk) begin dadr_n <= dadr; dwe_n <= dwe & cph; dwd_n <= dwd; end
    (* ram_style = "block" *) reg dm_neg [0:511];
    reg dq_neg;
    integer zn;
`ifndef SYNTHESIS
    initial for (zn = 0; zn < 512; zn = zn + 1) dm_neg[zn] = 1'b0;
`endif
    always @(posedge clk) begin
        if (dwe_n) dm_neg[dadr_n] <= dwd_n;
        dq_neg <= dm_neg[dadr_n];
    end

    // ---- block-RAM candidates (shadows: same inputs, outputs only compared): V0 as sc_sys_v5, V1 = V0 + falling-edge input registers, V2 = no-change mode + falling-edge input registers
    wire v0a, v0b, v1a, v1b, v2a, v2b;
    bp_rport #(.V(0), .BLK(1)) r0a (.clk(clk), .sel(cph), .we(we), .rd_addr(ra), .wr_addr(rwa), .wd(rwd), .q(v0a));
    bp_rport #(.V(0), .BLK(1)) r0b (.clk(clk), .sel(cph), .we(we), .rd_addr(rb), .wr_addr(rwa), .wd(rwd), .q(v0b));
    bp_rport #(.V(0), .BLK(1), .NEG(1)) r1a (.clk(clk), .sel(cph), .we(we), .rd_addr(ra), .wr_addr(rwa), .wd(rwd), .q(v1a));
    bp_rport #(.V(0), .BLK(1), .NEG(1)) r1b (.clk(clk), .sel(cph), .we(we), .rd_addr(rb), .wr_addr(rwa), .wd(rwd), .q(v1b));
    bp_rport #(.V(2), .BLK(1), .NEG(1)) r2a (.clk(clk), .sel(cph), .we(we), .rd_addr(ra), .wr_addr(rwa), .wd(rwd), .q(v2a));
    bp_rport #(.V(2), .BLK(1), .NEG(1)) r2b (.clk(clk), .sel(cph), .we(we), .rd_addr(rb), .wr_addr(rwa), .wd(rwd), .q(v2b));

    // ---- step counter and checkers
    reg [31:0] step = 0;
    always @(posedge clk) if (!rst && cph) step <= step + 1'b1;
    wire [143:0] rec0, rec1, rec2, recd, recn;
    wire any0, any1, any2, anyd, anyn;
    bp_chk c0 (.clk(clk), .run(!rst), .cph(cph), .step(step), .wr(rwe), .wa(rwa), .ra(ra), .rb(rb),
               .ea(ref_a), .aa(v0a), .eb(ref_b), .ab(v0b), .rec(rec0), .any(any0));
`ifdef INJECT_V1
    wire v1a_x = v1a ^ (step == 32'd400);
`else
    wire v1a_x = v1a;
`endif
    bp_chk c1 (.clk(clk), .run(!rst), .cph(cph), .step(step), .wr(rwe), .wa(rwa), .ra(ra), .rb(rb),
               .ea(ref_a), .aa(v1a_x), .eb(ref_b), .ab(v1b), .rec(rec1), .any(any1));
    bp_chk c2 (.clk(clk), .run(!rst), .cph(cph), .step(step), .wr(rwe), .wa(rwa), .ra(ra), .rb(rb),
               .ea(ref_a), .aa(v2a), .eb(ref_b), .ab(v2b), .rec(rec2), .any(any2));
    // data memory: A port = block vs LUT-RAM; the address recorded is the data address (low 9 bits)
    bp_chk cd (.clk(clk), .run(!rst), .cph(cph), .step(step), .wr(dwe), .wa({1'b0, dadr}), .ra({1'b0, dadr}), .rb(10'd0),
               .ea(dq_ref), .aa(dq_blk), .eb(1'b0), .ab(1'b0), .rec(recd), .any(anyd));

    bp_chk cn (.clk(clk), .run(!rst), .cph(cph), .step(step), .wr(dwe), .wa({1'b0, dadr}), .ra({1'b0, dadr}), .rb(10'd0),
               .ea(dq_ref), .aa(dq_neg), .eb(1'b0), .ab(1'b0), .rec(recn), .any(anyn));

    // ---- UART report: 'Q', 188 hex digits (step counter, V0, V1, V2, D, N records), CR, LF, then a pause
    localparam NIB = 188;
    wire [751:0] live = {step, rec0, rec1, rec2, recd, recn};
    reg  [751:0] snap;
    reg  [8:0]   idx = 9'd0;                      // 0 = 'P', 1..NIB = digits, NIB+1 = CR, NIB+2 = LF, NIB+3 = pause
    reg  [23:0]  gap = 24'd0;
    reg  [7:0]   data = 8'h51;
    reg          send = 1'b0;
    wire         busy;
    uart_tx #(.DIV(BAUD_DIV)) utx (.clk(clk), .data(data), .send(send), .tx(uart_tx), .busy(busy));
    wire [3:0] nib = snap[(NIB - idx) * 4 +: 4];
    wire [7:0] hexch = (nib < 4'd10) ? (8'd48 + nib) : (8'd55 + nib);
    always @(posedge clk) begin
        send <= 1'b0;
        if (rst) begin idx <= NIB + 3; gap <= 24'd0; end
        else if (idx == NIB + 3) begin                         // pause ~0.25 s, then take a snapshot
            gap <= gap + 1'b1;
            if (gap[GAPBIT]) begin gap <= 24'd0; snap <= live; idx <= 9'd0; end
        end else if (!busy && !send) begin
            send <= 1'b1; idx <= idx + 1'b1;
            if (idx == 0)           data <= 8'h51;
            else if (idx <= NIB)    data <= hexch;
            else if (idx == NIB + 1) data <= 8'h0D;
            else                    data <= 8'h0A;
        end
    end

    reg [24:0] hb = 0;
    always @(posedge clk) hb <= hb + 1'b1;
    assign led_n = ~{anyn, any2, any1, any0, !halted & !rst, hb[24]};
endmodule
