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
    parameter [31:0] DESIGN_ID = 32'h0,
    parameter NSENS = 2,              // sensor pins that can feed the design directly (lane j <- pin j for j < NSENS)
    parameter DIRECT_RAW = 0,         // 1: the lane word is the bare 16-bit amount (a CORDIC angle), 0: the packed SensorTrix word {amount, location = lane+1}
    parameter DIRECT_DEFAULT = 0,     // 1: power up in direct mode
    parameter SENS_INVERT = 0         // 1: the sensor pins are active LOW (buttons that pull the pin to ground when pressed)
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
    // sensor pins wired straight to the FPGA (direct mode)
    input  wire [NSENS-1:0]      sens_pins,
    output wire                  direct_on,     // for the LEDs: direct mode is on ...
    output wire                  live_nz,       // ... the newest result's amount is not zero
    output wire                  live_two,      // ... and it is at least two sensors' worth (>= 16384)
    output wire [15:0]           live_amt,      // the newest result's amount (for a display)
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

    spi_bridge_v1 #(.AW(AW), .DESIGN_ID(DESIGN_ID), .DIRECT_DEFAULT(DIRECT_DEFAULT)) BR (
        .direct_en(direct_en), .live_result(live_result), .live_count(live_count), .sens_state({{(4-NSENS){1'b0}}, sp2}),
        .clk(clk), .rst(rst), .sclk(spi_sclk), .cs_n(spi_cs_n), .mosi(spi_mosi), .miso(spi_miso),
        .ctl_sd_load(ctl_sd_load), .ctl_sd_save(ctl_sd_save), .ctl_play_start(ctl_play_start), .ctl_cap_clear(ctl_cap_clear), .ctl_sd_reinit(ctl_sd_reinit),
        .start_block(start_block), .nblocks(nblocks), .play_count(play_count), .max_out(max_out), .rpi(rpi),
        .sd_ready(sd_ready), .sd_error(sd_error), .sd_busy(sd_busy), .play_busy(play_busy), .err_code(err_code), .err_cmd(err_cmd), .err_rx(err_rx),
        .sd_done_pulse(sd_done), .play_done_pulse(play_done), .cap_count(cap_count),
        .pl_wr_en(br_pl_en), .pl_wr_addr(br_pl_addr), .pl_wr_data(br_pl_data), .cap_rd_addr(br_cap_addr), .cap_rd_data(cap_rd_data));

    wire direct_en; reg [31:0] live_result, live_count;
    wire [LANES*32-1:0] pl_lane_data; wire [LANES-1:0] pl_lane_valid;
    wire [OUTS-1:0] cap_out_valid, cap_out_ack;

    wire pl_en = sd_pl_en | br_pl_en;                 // the two writers never run together (software sequence); the SD stream wins if they ever do
    playout_v1 #(.LANES(LANES), .AW(AW)) P (
        .clk(clk), .rst(rst), .wr_en(pl_en), .wr_addr(sd_pl_en ? sd_pl_addr : br_pl_addr), .wr_data(sd_pl_en ? sd_pl_data : br_pl_data),
        .start(ctl_play_start), .count(play_count), .max_out(max_out), .rpi(rpi), .results(cap_count), .busy(play_busy), .done(play_done),
        .lane_data(pl_lane_data), .lane_valid(pl_lane_valid), .lane_ack(lane_ack & {LANES{~direct_en}}));

    capture_v1 #(.OUTS(OUTS), .AW(AW)) C (
        .clk(clk), .rst(rst), .clear(ctl_cap_clear), .out_data(out_data), .out_valid(cap_out_valid), .out_ack(cap_out_ack),
        .count(cap_count), .rd_addr(sd_busy ? sd_cap_addr : br_cap_addr), .rd_data(cap_rd_word));

    // ---- DIRECT mode: the sensor pins feed the design with no ESP32 and no RAM in the path. About every millisecond a word per lane is offered (valid held until the design takes it);
    // the design's result is accepted at once and latched (registers 12, 13). A digital sensor reads as 8192 when active, 0 when not: four active sensors sum to 32768 and cannot overflow 16 bits.
    reg [NSENS-1:0] sp1, sp2;
    always @(posedge clk) begin sp1 <= sens_pins ^ {NSENS{SENS_INVERT[0]}}; sp2 <= sp1; end
    wire [LANES+NSENS-1:0] sp_pad = {{LANES{1'b0}}, sp2};
    reg [14:0] tick; reg [LANES*32-1:0] d_data; reg [LANES-1:0] d_valid;
    wire tick_hit = (tick == 15'd26999);
    integer dj;
    always @(posedge clk) begin
        if (rst || !direct_en) begin tick <= 0; d_valid <= 0; d_data <= 0; end
        else begin
            tick <= tick_hit ? 15'd0 : tick + 1'b1;
            d_valid <= d_valid & ~lane_ack;
            if (tick_hit && d_valid == 0) begin
                for (dj = 0; dj < LANES; dj = dj + 1)
                    d_data[dj*32 +: 32] <= DIRECT_RAW ? {16'b0, (sp_pad[dj] ? 16'd8192 : 16'd0)} : {(sp_pad[dj] ? 16'd8192 : 16'd0), 16'(dj + 1)};
                d_valid <= {LANES{1'b1}};
            end
        end
    end
    assign lane_data  = direct_en ? d_data  : pl_lane_data;
    assign lane_valid = direct_en ? d_valid : pl_lane_valid;
    assign cap_out_valid = direct_en ? {OUTS{1'b0}} : out_valid;
    assign out_ack       = direct_en ? {OUTS{1'b1}} : cap_out_ack;
    always @(posedge clk) begin
        if (rst || !direct_en) begin live_result <= 0; live_count <= 0; end
        else if (out_valid[0]) begin live_result <= out_data[31:0]; live_count <= live_count + 1'b1; end
    end
    assign direct_on = direct_en;
    assign live_amt  = live_result[31:16];
    assign live_nz   = |live_result[31:16];
    assign live_two  = live_result[31:16] >= 16'd16384;

    assign ready_line = sd_ready & ~sd_error;
endmodule
`default_nettype wire
