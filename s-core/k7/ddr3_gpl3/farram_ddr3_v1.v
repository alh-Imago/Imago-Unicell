// farram_ddr3_v1.v - far RAM in DDR3 (one channel of the Kintex-7 card) behind the same request / acknowledge interface as sdram_ctl.v and farram_bram_v1.v.
//
// LICENCE NOTE: this file is kept in ddr3_gpl3/ and is part of the GPL-3.0 DDR3 build (it is written to drive the UberDDR3 controller's Wishbone port;
// see README.md in this folder).  The pool does not include it; only the *_ddr3 builds do.
//
// Pool side (clk, 50 MHz): req_v & req_rdy hands over {req_we, req_a[20:0], req_wd}; ack_v pulses when done (ack_d = the word read, 0 for a write).
// The SDRAM tuning inputs (cfg_*, reinit) are accepted and ignored.  init_done rises when the DDR3 has calibrated.  One request at a time.
//
// Controller side (cclk, the controller clock, 83.33 MHz, asynchronous to clk as far as this file is concerned): UberDDR3's Wishbone port moves one burst
// of 8 beats of the whole data bus at a time: with 9 byte lanes that is 9 x 8 x 8 = 576 bits (64 bytes of data plus the 9th, unused, ECC lane).  The
// port has a byte strobe, but this card has no data-mask pins, so a write always replaces the whole line.  A 32-bit word is therefore written by read-modify-write
// (see the cclk side below) with a one-line cache.  Word a lives in line a[20:4], slot a[3:0] (slot s = bits 32s..32s+31).  Which physical DQ lines
// those bytes use does not matter, because a word is always read back from the place it was written.  A line is 16 words, so 2**21 words (8 MB) address
// 2**17 lines; the rest of the 2 GiB channel is not reached yet.
//
// Crossing between the clocks: a request is held in registers on the clk side and announced by a toggle; the cclk side sees the toggle through two
// flip-flops, runs the Wishbone transfer, holds the read word in a register and toggles the answer; the clk side sees that through two flip-flops.
// The data registers never change while a request is in flight, so only the one-bit toggles cross between the clocks.
module farram_ddr3_v1 #(parameter LANES = 9, parameter WBA = 25) (
    // pool side
    input  wire        clk,
    input  wire        rst,
    input  wire [1:0]  cfg_cl,
    input  wire [1:0]  cfg_dly,
    input  wire        cfg_inv,
    input  wire        reinit,
    input  wire        req_v, req_we,
    input  wire [20:0] req_a,
    input  wire [31:0] req_wd,
    output wire        req_rdy,
    output reg         ack_v,
    output reg  [31:0] ack_d,
    output wire        init_done,
    output wire        busy,
    // controller side (to ddr3_top's Wishbone port)
    input  wire        cclk,
    input  wire        crst_n,        // low = reset (controller clock domain)
    input  wire        calib_complete,
    output reg         wb_cyc,
    output reg         wb_stb,
    output reg         wb_we,
    output reg  [WBA-1:0]        wb_addr,
    output reg  [LANES*64-1:0]   wb_data,
    output reg  [LANES*8-1:0]    wb_sel,
    input  wire        wb_stall,
    input  wire        wb_ack,
    input  wire [LANES*64-1:0]   wb_rdata
);
    localparam DW = LANES * 64;                 // 576 for 9 lanes
    localparam SLOTS = DW / 32;                 // 18 slots of 32 bits; slots 0..15 hold words, 16..17 are never used

    // ---------------- clk side
    reg        pend = 1'b0, req_t = 1'b0;
    reg        q_we = 1'b0;
    reg [20:0] q_a = 21'd0;
    reg [31:0] q_wd = 32'd0;
    (* ASYNC_REG = "TRUE" *) reg a1 = 1'b0, a2 = 1'b0, i1 = 1'b0, i2 = 1'b0;
    wire [31:0] c_rdata;                        // cclk-side hold register
    wire        ack_t;                          // cclk-side answer toggle
    assign init_done = i2;
    assign req_rdy   = i2 && !pend && !rst;
    assign busy      = pend;
    wire take = req_v && req_rdy;
    reg  ack_t_seen = 1'b0;
    always @(posedge clk) begin
        ack_v <= 1'b0;
        a1 <= ack_t;  a2 <= a1;
        i1 <= calib_complete; i2 <= i1;
        if (rst) begin
            pend <= 1'b0;
            ack_t_seen <= a2;                   // forget any answer that was on its way
        end else begin
            if (take) begin
                q_we <= req_we; q_a <= req_a; q_wd <= req_wd;
                req_t <= ~req_t;
                pend <= 1'b1;
            end
            if (pend && (a2 != ack_t_seen)) begin
                ack_t_seen <= a2;
                pend  <= 1'b0;
                ack_v <= 1'b1;
                ack_d <= q_we ? 32'd0 : c_rdata;
            end
        end
    end

    // ---------------- cclk side
    // The card's DDR3 has no data-mask pins (none in the pin list), so the controller always writes the whole 64-byte line and the byte strobe cannot
    // protect the neighbouring words (found on the card 2026-11-16: every word of a line read back the last word written to it).  A write is therefore
    // read-modify-write: the line is read once into a one-line cache (a miss), the word is replaced in the cache, and the whole line is written back.
    // Reads of the cached line need no controller transfer.  The cache is exact because every access to the far RAM goes through this one master.
    (* ASYNC_REG = "TRUE" *) reg r1 = 1'b0, r2 = 1'b0;
    reg        req_t_seen = 1'b0;
    reg        ack_t_r = 1'b0;
    reg [31:0] c_hold = 32'd0;
    reg [1:0]  st = 2'd0;                       // 0 idle / decide, 1 present a controller transfer, 2 wait for its answer
    reg        fin = 1'b0;                      // the transfer in flight is the write-back that ends the request
    reg [DW-1:0] cache = {DW{1'b0}};
    reg [16:0] c_line = 17'd0;
    reg        c_val = 1'b0;
    assign ack_t   = ack_t_r;
    assign c_rdata = c_hold;
    wire [3:0]  slot  = q_a[3:0];
    wire [16:0] line  = q_a[20:4];
    wire        hit   = c_val && (c_line == line);
    reg  [DW-1:0] merged;
    always @* begin
        merged = cache;
        merged[32 * slot +: 32] = q_wd;
    end
    always @(posedge cclk) begin
        r1 <= req_t; r2 <= r1;
        if (!crst_n) begin
            st <= 2'd0; wb_cyc <= 1'b0; wb_stb <= 1'b0; wb_we <= 1'b0; c_val <= 1'b0; fin <= 1'b0;
            req_t_seen <= r2;                   // a request raised during reset is dropped (the pool is held in reset as well)
        end else begin
            wb_cyc <= calib_complete;
            case (st)
            2'd0: if (calib_complete && (r2 != req_t_seen)) begin
                    if (hit && !q_we) begin                        // read of the cached line: answer at once
                        c_hold <= cache[32 * slot +: 32];
                        ack_t_r <= ~ack_t_r; req_t_seen <= r2;
                    end else if (hit && q_we) begin                // write: change the word in the cache, write the whole line back
                        cache   <= merged;
                        wb_we   <= 1'b1; wb_addr <= {{(WBA-17){1'b0}}, line}; wb_data <= merged; wb_sel <= {(LANES*8){1'b1}};
                        wb_stb  <= 1'b1; fin <= 1'b1; st <= 2'd1;
                    end else begin                                 // miss: read the line first (then this same request is decided again as a hit)
                        wb_we   <= 1'b0; wb_addr <= {{(WBA-17){1'b0}}, line}; wb_sel <= {(LANES*8){1'b1}};
                        wb_stb  <= 1'b1; fin <= 1'b0; st <= 2'd1;
                    end
                  end
            2'd1: if (!wb_stall) begin          // the transfer was accepted on this clock edge
                    wb_stb <= 1'b0;
                    st     <= 2'd2;
                  end
            2'd2: if (wb_ack) begin
                    st <= 2'd0;
                    if (fin) begin               // write-back done: the request is finished
                        c_hold <= 32'd0; ack_t_r <= ~ack_t_r; req_t_seen <= r2; fin <= 1'b0;
                    end else begin               // line read done: keep it, decide the request again
                        cache <= wb_rdata; c_line <= line; c_val <= 1'b1;
                    end
                  end
            default: st <= 2'd0;
            endcase
        end
    end
endmodule
