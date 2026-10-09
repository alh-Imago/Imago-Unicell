// sd_unit_v1.v -- ledger #1036: the SMALL UNIT's wrapper around ANY generated flex design: an SD card (raw blocks) -> playout RAM -> the design -> capture RAM -> SD card, all driven over SPI by an
// ESP32 (spi_bridge_v1). The design's entry ports are the `lane_*` bus (LANES of them, in the order the design's entry list is given) and its exits are the `out_*` bus (OUTS).
//   ESP32 --SPI--> spi_bridge_v1 --registers--> sd_stream_v1 (SD blocks <-> RAMs) , playout_v1 (RAM -> lanes) , capture_v1 (outs -> RAM)
// See docs/playout_capture_v1.md for the register map and the typical sequence. The SD pins are the Tang Nano 20K slot used in SPI mode; the SPI pins are the proposed ESP32 link.
`default_nettype none
module sd_unit_v1 #(
    parameter LANES    = 4,
    parameter OUTS     = 1,
    parameter AW       = 10,
    parameter INIT_DIV = 34,
    parameter FAST_DIV = 1,
    parameter [31:0] DESIGN_ID = 32'h0
) (
    input  wire                  clk,
    input  wire                  rst,
    // SD card (SPI mode)
    output wire                  sd_clk,
    output wire                  sd_mosi,
    input  wire                  sd_miso,
    output wire                  sd_cs_n,
    // ESP32 (SPI slave, mode 0; SCLK must be slower than clk/16)
    input  wire                  spi_sclk,
    input  wire                  spi_cs_n,
    input  wire                  spi_mosi,
    output wire                  spi_miso,
    // the design
    output wire [LANES*32-1:0]   lane_data,
    output wire [LANES-1:0]      lane_valid,
    input  wire [LANES-1:0]      lane_ack,
    input  wire [OUTS*32-1:0]    out_data,
    input  wire [OUTS-1:0]       out_valid,
    output wire [OUTS-1:0]       out_ack,
    // for a status LED / READY line
    output wire                  ready_line
);
    wire ctl_sd_load, ctl_sd_save, ctl_play_start, ctl_cap_clear, ctl_sd_reinit; wire [5:0] err_cmd; wire [7:0] err_rx;
    wire [31:0] start_block; wire [15:0] nblocks; wire [AW:0] play_count, max_out, rpi;
    wire sd_busy, sd_done, sd_ready, sd_error; wire [4:0] err_code;
    wire sd_pl_en, br_pl_en; wire [AW-1:0] sd_pl_addr, br_pl_addr; wire [31:0] sd_pl_data, br_pl_data;
    localparam TAGW = (OUTS > 1) ? $clog2(OUTS) : 1;
    wire [AW-1:0] sd_cap_addr, br_cap_addr; wire [31+TAGW:0] cap_rd_word;
    wire play_busy, play_done; wire [AW:0] cap_count;
    wire [31:0] cap_rd_data = cap_rd_word[31:0];

    sd_stream_v1 #(.AW(AW), .INIT_DIV(INIT_DIV), .FAST_DIV(FAST_DIV)) SS (
        .clk(clk), .rst(rst | ctl_sd_reinit), .sd_clk(sd_clk), .sd_mosi(sd_mosi), .sd_miso(sd_miso), .sd_cs_n(sd_cs_n),
        .cmd_load(ctl_sd_load), .cmd_save(ctl_sd_save), .start_block(start_block), .nblocks(nblocks),
        .busy(sd_busy), .done(sd_done), .ready(sd_ready), .error(sd_error), .err_code(err_code), .err_cmd(err_cmd), .err_rx(err_rx),
        .pl_wr_en(sd_pl_en), .pl_wr_addr(sd_pl_addr), .pl_wr_data(sd_pl_data), .cap_rd_addr(sd_cap_addr), .cap_rd_data(cap_rd_data));

    spi_bridge_v1 #(.AW(AW), .DESIGN_ID(DESIGN_ID)) BR (
        .clk(clk), .rst(rst), .sclk(spi_sclk), .cs_n(spi_cs_n), .mosi(spi_mosi), .miso(spi_miso),
        .ctl_sd_load(ctl_sd_load), .ctl_sd_save(ctl_sd_save), .ctl_play_start(ctl_play_start), .ctl_cap_clear(ctl_cap_clear), .ctl_sd_reinit(ctl_sd_reinit),
        .start_block(start_block), .nblocks(nblocks), .play_count(play_count), .max_out(max_out), .rpi(rpi),
        .sd_ready(sd_ready), .sd_error(sd_error), .sd_busy(sd_busy), .play_busy(play_busy), .err_code(err_code), .err_cmd(err_cmd), .err_rx(err_rx),
        .sd_done_pulse(sd_done), .play_done_pulse(play_done), .cap_count(cap_count),
        .pl_wr_en(br_pl_en), .pl_wr_addr(br_pl_addr), .pl_wr_data(br_pl_data), .cap_rd_addr(br_cap_addr), .cap_rd_data(cap_rd_data));

    wire pl_en = sd_pl_en | br_pl_en;                 // the two writers never run together (software sequence); the SD stream wins if they ever do
    playout_v1 #(.LANES(LANES), .AW(AW)) P (
        .clk(clk), .rst(rst), .wr_en(pl_en), .wr_addr(sd_pl_en ? sd_pl_addr : br_pl_addr), .wr_data(sd_pl_en ? sd_pl_data : br_pl_data),
        .start(ctl_play_start), .count(play_count), .max_out(max_out), .rpi(rpi), .results(cap_count), .busy(play_busy), .done(play_done),
        .lane_data(lane_data), .lane_valid(lane_valid), .lane_ack(lane_ack));

    capture_v1 #(.OUTS(OUTS), .AW(AW)) C (
        .clk(clk), .rst(rst), .clear(ctl_cap_clear), .out_data(out_data), .out_valid(out_valid), .out_ack(out_ack),
        .count(cap_count), .rd_addr(sd_busy ? sd_cap_addr : br_cap_addr), .rd_data(cap_rd_word));

    assign ready_line = sd_ready & ~sd_error;
endmodule
`default_nettype wire
