// hexn_open_top_v3.v -- Hex-N OPEN UNIT, STAGE 4a (new file 1 Nov 2026; clone of hexn_open_top_v2.v, untouched). As stage 2 PLUS MODE 3 = RAW WORD STREAM (hexn_raw_engine_v1: cfg24 = {out_base, count}, cfg25 = go, status bit 6 busy, bits 15:8 results written). As stage 2: as stage 1 (one build, MODE in config register 16: 0 idle, 1 reaction game, 2 Morse key) plus LOADABLE DATA:
//   * spi_bridge_v2 as before (ID 0x57320002, config registers 16..31, status 10, 1,024-word scratch RAM behind WR_WORDS / RD_WORDS)
//   * four loadable tables (hexn_tabs_v1): reaction scorer table, Morse scorer table, Morse decode table, glyph table, with factory defaults copied in at power-up.
//       load: write the words into the scratch RAM, then  cfg17 = {space[31:28], scratch base[27:16], count[15:0]}  and change cfg19 (any new value) to copy; wait for status bit 4 (busy) to clear. Then (re)select the mode: a core reads its table when it starts.
//       restore the factory defaults: change cfg23 (any new value), wait for busy to clear.
//   * per-channel BINNING config words: cfg20 reaction time, cfg21 Morse press length, cfg22 Morse gap length.  bit 0 = linear (else log2 as before), bits [7:4] = shift (a bin is 2^shift ms wide), bits [27:16] = low end in ms.  0 = log2 bins.
//   * status register 10: [1:0] mode, [2] reaction core ready, [3] Morse core ready, [4] table copy / default fill busy, [5] defaults loaded.
// Pins as stage 1: SPI 73 CS, 74 SCLK, 75 MOSI, 76 MISO, 77 READY; shield A1 72, A2 71, A3 86, display 25/26/27, buzzer 28; Tang S1 = restart (factory defaults again).
`default_nettype none
module hexn_open_top_v3 #(
    parameter TICK = 27000, parameter DEBMS = 10, parameter RSTW = 16
) (
    input  wire BOARD_CLK, input wire KEY_S1,
    input  wire SPI_SCLK, input wire SPI_CS_N, input wire SPI_MOSI, output wire SPI_MISO, output wire READY,
    input  wire BTN1_N, input wire BTN2_N, input wire BTN3_N,
    output wire DISP_LATCH, output wire DISP_CLK, output wire DISP_DATA, output wire BUZZER,
    output wire [5:0] LED_N
);
    wire clk = BOARD_CLK;
    reg [RSTW-1:0] rcnt = 0; wire rst = ~&rcnt;
    reg [1:0] key_q = 2'b00; always @(posedge clk) key_q <= {key_q[0], KEY_S1};
    always @(posedge clk) if (key_q[1]) rcnt <= 0; else if (rst) rcnt <= rcnt + 1'b1;

    wire pl_en; wire [9:0] pl_a, cap_a, sr_a; wire [31:0] pl_d; reg [31:0] cap_d, sr_d; wire [16*32-1:0] cfg; wire [31:0] status;
    wire raw_busy, raw_we; wire [9:0] raw_ra, raw_wa; wire [31:0] raw_wd; wire [7:0] raw_nres;
    wire w_en = raw_busy ? raw_we : pl_en; wire [9:0] w_a = raw_busy ? raw_wa : pl_a; wire [31:0] w_d = raw_busy ? raw_wd : pl_d;   // ONE write port (block RAM): the raw engine owns it while busy
    wire [9:0] r_a = raw_busy ? raw_ra : sr_a;
    reg [31:0] mem [0:1023]; always @(posedge clk) begin if (w_en) mem[w_a] <= w_d; cap_d <= mem[cap_a]; sr_d <= mem[r_a]; end
    spi_bridge_v2 #(.AW(10)) BR (
        .clk(clk), .rst(rst), .sclk(SPI_SCLK), .cs_n(SPI_CS_N), .mosi(SPI_MOSI), .miso(SPI_MISO),
        .ctl_sd_load(), .ctl_sd_save(), .ctl_play_start(), .ctl_cap_clear(), .ctl_sd_reinit(), .start_block(), .nblocks(), .play_count(), .max_out(), .rpi(),
        .sd_ready(1'b0), .sd_error(1'b0), .sd_busy(1'b0), .play_busy(1'b0), .err_code(5'd0), .err_cmd(6'd0), .err_rx(8'd0), .sd_done_pulse(1'b0), .play_done_pulse(1'b0), .cap_count(11'd0),
        .pl_wr_en(pl_en), .pl_wr_addr(pl_a), .pl_wr_data(pl_d), .cap_rd_addr(cap_a), .cap_rd_data(cap_d), .cfg_flat(cfg), .status_in(status));
    wire [1:0] mode = cfg[1:0];

    // ---- tables
    wire [7:0] rt_a, mt_a, dec_a; wire [31:0] rt_d, mt_d; wire [8:0] rt_len, mt_len; wire [5:0] dec_ch; wire [23:0] chars; wire pend; wire [31:0] gsegs; wire busy, init_done;
    hexn_tabs_v1 TB (.clk(clk), .rst(rst), .ctl(cfg[17*32-512 +: 32]), .go(cfg[19*32-512 +: 32]), .restore(cfg[23*32-512 +: 32]), .sr_addr(sr_a), .sr_data(sr_d),
        .rt_addr(rt_a), .rt_data(rt_d), .rt_len(rt_len), .mt_addr(mt_a), .mt_data(mt_d), .mt_len(mt_len), .dec_addr(dec_a), .dec_ch(dec_ch), .chars(chars), .pend(pend), .gsegs(gsegs), .busy(busy), .init_done(init_done));

    // ---- mode 3: raw word stream
    hexn_raw_engine_v1 RW (.clk(clk), .rst(rst | (mode != 2'd3)), .ctl(cfg[24*32-512 +: 32]), .go(cfg[25*32-512 +: 32]), .ra(raw_ra), .rd(sr_d), .we(raw_we), .wa(raw_wa), .wd(raw_wd), .busy(raw_busy), .nres(raw_nres));

    // ---- the two personalities
    wire [31:0] r_segs, m_segs; wire r_en, m_en, r_buzz, m_buzz; wire [5:0] r_led, m_led;
    hexn_react_core_v2 #(.TICK(TICK), .DEBMS(DEBMS)) RC (.clk(clk), .rst(rst | ~init_done | busy | (mode != 2'd1)), .BTN1_N(BTN1_N), .BTN2_N(BTN2_N), .BTN3_N(BTN3_N), .segs(r_segs), .disp_en(r_en), .buzz(r_buzz), .led_n(r_led),
        .tab_addr(rt_a), .tab_data(rt_d), .tab_len(rt_len), .bin_cfg(cfg[20*32-512 +: 32]));
    hexn_morse_core_v2 #(.TICK(TICK), .DEBMS(DEBMS)) MC (.clk(clk), .rst(rst | ~init_done | busy | (mode != 2'd2)), .BTN1_N(BTN1_N), .BTN2_N(BTN2_N), .segs(m_segs), .disp_en(m_en), .buzz(m_buzz), .led_n(m_led),
        .tab_addr(mt_a), .tab_data(mt_d), .tab_len(mt_len), .bin_p(cfg[21*32-512 +: 32]), .bin_g(cfg[22*32-512 +: 32]), .dec_addr(dec_a), .dec_ch(dec_ch), .chars(chars), .pend(pend), .gsegs(gsegs));
    assign status = {16'd0, raw_nres, 1'b0, raw_busy, init_done, busy, ~m_led[5] & (mode == 2'd2), ~r_led[5] & (mode == 2'd1), mode};

    wire [31:0] segs = (mode == 2'd1) ? r_segs : (mode == 2'd2) ? m_segs : 32'hFFFFFFFF;
    wire en = (mode == 2'd1) ? r_en : (mode == 2'd2) ? m_en : 1'b0;
    wire buzz = (mode == 2'd1) ? r_buzz : (mode == 2'd2) ? m_buzz : 1'b0;
    hw262_shield_v2 SH (.clk(clk), .rst(rst), .enable(en), .segs(segs), .buzz(buzz), .latch(DISP_LATCH), .sclk(DISP_CLK), .sdata(DISP_DATA), .buzzer(BUZZER));

    reg [24:0] hb = 0; reg seen_cs = 0, seen_clk = 0, seen_mosi = 0;
    always @(posedge clk) begin hb <= hb + 1'b1; if (!SPI_CS_N) seen_cs <= 1'b1; if (SPI_SCLK) seen_clk <= 1'b1; if (!SPI_CS_N && SPI_MOSI) seen_mosi <= 1'b1; end
    wire [5:0] idle_led = ~{init_done, seen_mosi, busy, seen_clk, seen_cs, hb[24]};
    assign LED_N = (mode == 2'd1) ? r_led : (mode == 2'd2) ? m_led : idle_led;
    assign READY = (mode != 2'd0);
endmodule
`default_nettype wire
