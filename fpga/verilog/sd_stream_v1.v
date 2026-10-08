// sd_stream_v1.v -- ledger #1036: moves whole runs of SD blocks between the card and the playout / capture RAMs (playout_v1.v, capture_v1.v).
//   cmd_load : read nblocks blocks starting at start_block into the playout RAM, word w of block i at address i*128 + w. (Then the host pulses playout's start with count = items*LANES.)
//   cmd_save : write nblocks blocks starting at start_block from the capture RAM, address i*128 + w (the low 32 bits of each stored word).
// `busy` is high during a command, `done` pulses at the end, `error` latches a card error (see sd_spi_v1 err_code). `ready` = the card is initialised.
// Raw blocks, no filesystem: the host (any PC) writes the input words to the card as plain 512-byte blocks, little-endian 32-bit words, item-major / lane-minor.
`default_nettype none
module sd_stream_v1 #(
    parameter AW = 10,                             // playout / capture address width
    parameter INIT_DIV = 34,
    parameter FAST_DIV = 1
) (
    input  wire            clk,
    input  wire            rst,
    // the card
    output wire            sd_clk,
    output wire            sd_mosi,
    input  wire            sd_miso,
    output wire            sd_cs_n,
    // commands
    input  wire            cmd_load,
    input  wire            cmd_save,
    input  wire [31:0]     start_block,
    input  wire [15:0]     nblocks,
    output reg             busy,
    output reg             done,
    output wire            ready,
    output wire            error,
    output wire [4:0]      err_code,
    // playout RAM write port
    output wire            pl_wr_en,
    output wire [AW-1:0]   pl_wr_addr,
    output wire [31:0]     pl_wr_data,
    // capture RAM read port (data one cycle after address)
    output wire [AW-1:0]   cap_rd_addr,
    input  wire [31:0]     cap_rd_data
);
    wire        sd_busy, sd_block_done, w_valid;
    wire [31:0] w_data;
    wire [6:0]  w_index, src_addr;
    reg         rd_req, wr_req;
    reg  [31:0] blk;
    reg  [15:0] i, n;
    reg         saving;
    reg  [1:0]  st;
    localparam IDLE = 0, ISSUE = 1, WAITB = 2;

    sd_spi_v1 #(.INIT_DIV(INIT_DIV), .FAST_DIV(FAST_DIV)) S (
        .clk(clk), .rst(rst), .sd_clk(sd_clk), .sd_mosi(sd_mosi), .sd_miso(sd_miso), .sd_cs_n(sd_cs_n),
        .ready(ready), .error(error), .err_code(err_code), .busy(sd_busy),
        .rd_req(rd_req), .wr_req(wr_req), .block(blk), .block_done(sd_block_done),
        .w_valid(w_valid), .w_data(w_data), .w_index(w_index), .src_addr(src_addr), .src_data(cap_rd_data));

    assign pl_wr_en   = w_valid && !saving;
    assign pl_wr_addr = {i[AW-8:0], w_index};          // block i, word w_index (128 words per block)
    assign pl_wr_data = w_data;
    assign cap_rd_addr = {i[AW-8:0], src_addr};

    always @(posedge clk) begin
        rd_req <= 1'b0; wr_req <= 1'b0; done <= 1'b0;
        if (rst) begin st <= IDLE; busy <= 1'b0; i <= 0; n <= 0; blk <= 0; saving <= 1'b0; end
        else case (st)
            IDLE: if ((cmd_load || cmd_save) && ready && !error) begin
                      busy <= 1'b1; saving <= cmd_save; blk <= start_block; n <= nblocks; i <= 0;
                      st <= (nblocks == 0) ? IDLE : ISSUE;
                      if (nblocks == 0) done <= 1'b1;
                  end
            ISSUE: if (!sd_busy) begin if (saving) wr_req <= 1'b1; else rd_req <= 1'b1; st <= WAITB; end
            WAITB: if (error) begin busy <= 1'b0; st <= IDLE; end
                   else if (sd_block_done) begin
                       if (i + 1 == n) begin busy <= 1'b0; done <= 1'b1; st <= IDLE; end
                       else begin i <= i + 1'b1; blk <= blk + 1'b1; st <= ISSUE; end
                   end
        endcase
    end
endmodule
`default_nettype wire
