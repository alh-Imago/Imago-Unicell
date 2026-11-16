// sdram_ctl.v - controller for the Tang Nano 20K's in-package SDR SDRAM (64 Mbit, 2M words of 32 bits: 4 banks, 11 row bits, 8 column bits).
// One clock (the 27 MHz board clock), one request at a time, every access = ACTIVE, READ or WRITE with auto-precharge, wait.  About 10 clocks
// per word.  Word address a[20:0] = {bank(2), row(11), column(8)}, so consecutive words share a row.
// Things the datasheet is not at hand for are RUN-TIME settings so a card can be tuned without a rebuild:
//   cfg_cl   CAS latency written into the mode register (2 or 3)
//   cfg_inv  1 = the SDRAM clock pin gets the inverted clock (the chip samples half a clock later)
//   cfg_dly  0..3 = extra clocks before the read data is sampled
//   reinit   one-clock pulse: run the power-up sequence again with the current settings (init_done drops until it is finished)
// Request:  req_v & req_rdy in one clock hands over {req_we, req_a, req_wd}.  ack_v pulses when it is done (ack_d = the word read; for a write ack_d is 0).
// Timing is generous on purpose (a 37 ns clock): tRCD 2, tRP 3, tRFC 4, tMRD 3 clocks, write recovery 6, refresh every 200 clocks (7.4 us).
module sdram_ctl #(parameter INIT_CLKS = 5400) (        // 200 us at 27 MHz
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
    output reg         init_done,
    output wire        busy,
    output wire        O_sdram_clk,
    output wire        O_sdram_cke,
    output wire        O_sdram_cs_n, O_sdram_ras_n, O_sdram_cas_n, O_sdram_wen_n,
    output wire [3:0]  O_sdram_dqm,
    output wire [10:0] O_sdram_addr,
    output wire [1:0]  O_sdram_ba,
    inout  wire [31:0] IO_sdram_dq
);
    localparam [3:0] C_NOP = 4'b0111, C_ACT = 4'b0011, C_RD = 4'b0101, C_WR = 4'b0100, C_PRE = 4'b0010, C_REF = 4'b0001, C_MRS = 4'b0000;
    localparam [4:0] S_PWR = 0, S_PRE = 1, S_REF1 = 2, S_REF2 = 3, S_MRS = 4, S_IDLE = 5, S_RCD = 6, S_RW = 7, S_RDW = 8, S_WRW = 9, S_RP = 10, S_RFW = 11, S_WAIT = 12;
    reg [4:0]  st;
    reg [15:0] cnt;
    reg [3:0]  cmd;
    reg [10:0] addr;
    reg [1:0]  ba;
    reg        dq_oe;
    reg [31:0] dq_o;
    reg        dqm_hi;
    reg        cke;
    reg        we_q;
    reg [20:0] a_q;
    reg [31:0] wd_q;
    reg [7:0]  ref_cnt;
    reg [4:0]  next_st;
    wire ref_due = (ref_cnt >= 8'd200);

    assign O_sdram_clk   = cfg_inv ? ~clk : clk;
    assign O_sdram_cke   = cke;
    assign {O_sdram_cs_n, O_sdram_ras_n, O_sdram_cas_n, O_sdram_wen_n} = cmd;
    assign O_sdram_addr  = addr;
    assign O_sdram_ba    = ba;
    assign O_sdram_dqm   = {4{dqm_hi}};
    assign IO_sdram_dq   = dq_oe ? dq_o : 32'bz;
    assign req_rdy = (st == S_IDLE) && init_done && !ref_due && !reinit;
    assign busy    = (st != S_IDLE);

    always @(posedge clk) begin
        ack_v <= 1'b0;
        cmd   <= C_NOP;
        dq_oe <= 1'b0;
        if (ref_cnt != 8'hFF) ref_cnt <= ref_cnt + 1'b1;
        if (rst || reinit) begin
            st <= S_PWR; cnt <= INIT_CLKS; init_done <= 1'b0; cke <= 1'b1; dqm_hi <= 1'b1; ref_cnt <= 8'd0; addr <= 11'd0; ba <= 2'd0;
        end else case (st)
            S_PWR: if (cnt != 0) cnt <= cnt - 1'b1; else begin cmd <= C_PRE; addr <= 11'h400; st <= S_WAIT; cnt <= 3; next_st <= S_REF1; end
            S_REF1: begin cmd <= C_REF; st <= S_WAIT; cnt <= 4; next_st <= S_REF2; end
            S_REF2: begin cmd <= C_REF; st <= S_WAIT; cnt <= 4; next_st <= S_MRS; end
            S_MRS: begin cmd <= C_MRS; addr <= {4'd0, {1'b0, cfg_cl}, 4'd0}; ba <= 2'd0; st <= S_WAIT; cnt <= 3; next_st <= S_IDLE; end   // mode: burst length 1, sequential, CAS latency in A6..A4
            S_WAIT: if (cnt <= 1) begin st <= next_st; if (next_st == S_IDLE) begin init_done <= 1'b1; dqm_hi <= 1'b0; ref_cnt <= 8'd0; end end else cnt <= cnt - 1'b1;
            S_IDLE: begin
                if (ref_due && init_done) begin cmd <= C_REF; ref_cnt <= 8'd0; st <= S_WAIT; cnt <= 4; next_st <= S_IDLE; end
                else if (req_v && init_done) begin
                    we_q <= req_we; a_q <= req_a; wd_q <= req_wd;
                    cmd <= C_ACT; ba <= req_a[20:19]; addr <= req_a[18:8];
                    st <= S_RCD; cnt <= 1;
                end
            end
            S_RCD: if (cnt != 0) cnt <= cnt - 1'b1; else begin                           // ACTIVE was two clocks ago
                cmd  <= we_q ? C_WR : C_RD; ba <= a_q[20:19]; addr <= {1'b1, 2'b00, a_q[7:0]};    // A10 = 1: auto-precharge
                if (we_q) begin dq_oe <= 1'b1; dq_o <= wd_q; st <= S_WRW; cnt <= 6; end
                else begin st <= S_RDW; cnt <= {14'd0, cfg_cl} + {14'd0, cfg_dly}; end
            end
            S_WRW: if (cnt != 0) cnt <= cnt - 1'b1; else begin ack_v <= 1'b1; ack_d <= 32'd0; st <= S_IDLE; end
            S_RDW: if (cnt != 0) cnt <= cnt - 1'b1; else begin ack_d <= IO_sdram_dq; st <= S_RP; cnt <= 2; end
            S_RP:  if (cnt != 0) cnt <= cnt - 1'b1; else begin ack_v <= 1'b1; st <= S_IDLE; end
            default: st <= S_PWR;
        endcase
    end
    initial begin st = S_PWR; cnt = INIT_CLKS; init_done = 0; cke = 1; dqm_hi = 1; ref_cnt = 0; cmd = C_NOP; addr = 0; ba = 0; dq_oe = 0; dq_o = 0; ack_v = 0; ack_d = 0; next_st = S_IDLE; we_q = 0; a_q = 0; wd_q = 0; end
endmodule
