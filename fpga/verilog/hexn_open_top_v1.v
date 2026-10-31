// hexn_open_top_v1.v -- Hex-N OPEN UNIT, STAGE 1 (new file 1 Nov 2026; docs/hex-n/OPEN_UNIT_v1.md). ONE build, personality chosen by DATA over SPI:
//   config register 16 (SPI address 16), bits [1:0] = MODE: 0 = idle (display blank, nothing running), 1 = reaction game (buttons A1..A3), 2 = Morse key (A1 key, A2 clear).
// The unused personality is held in reset, so it does nothing (no buzzer, no display). Changing the mode restarts the chosen one (its table is loaded again).
// The SPI side is spi_bridge_v2 (16-bit byte counter, so long transactions work; ID 0x57320002; config registers 16..31; status at 10: [1:0] mode, [2] reaction core ready, [3] Morse core ready).
// A 1,024-word scratch RAM sits behind WR_WORDS / RD_WORDS (write at address a, read back from the same address) so long transfers can be checked on the board.
// Pins: SPI 73 CS, 74 SCLK, 75 MOSI, 76 MISO, 77 READY (high when a personality is running); shield A1 72, A2 71, A3 86; display 25/26/27; buzzer 28; Tang S1 = restart. LEDs: mode 0: 0 heartbeat, 1 CS seen, 2 SCLK seen, 4 MOSI 1 seen.
`default_nettype none
module hexn_open_top_v1 #(
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

    // ---- SPI bridge v2 and the scratch RAM
    wire pl_en; wire [9:0] pl_a, cap_a; wire [31:0] pl_d; reg [31:0] cap_d; wire [16*32-1:0] cfg; wire [31:0] status;
    reg [31:0] mem [0:1023]; always @(posedge clk) begin if (pl_en) mem[pl_a] <= pl_d; cap_d <= mem[cap_a]; end
    spi_bridge_v2 #(.AW(10)) BR (
        .clk(clk), .rst(rst), .sclk(SPI_SCLK), .cs_n(SPI_CS_N), .mosi(SPI_MOSI), .miso(SPI_MISO),
        .ctl_sd_load(), .ctl_sd_save(), .ctl_play_start(), .ctl_cap_clear(), .ctl_sd_reinit(), .start_block(), .nblocks(), .play_count(), .max_out(), .rpi(),
        .sd_ready(1'b0), .sd_error(1'b0), .sd_busy(1'b0), .play_busy(1'b0), .err_code(5'd0), .err_cmd(6'd0), .err_rx(8'd0), .sd_done_pulse(1'b0), .play_done_pulse(1'b0), .cap_count(11'd0),
        .pl_wr_en(pl_en), .pl_wr_addr(pl_a), .pl_wr_data(pl_d), .cap_rd_addr(cap_a), .cap_rd_data(cap_d), .cfg_flat(cfg), .status_in(status));
    wire [1:0] mode = cfg[1:0];

    // ---- the two personalities (each held in reset unless chosen)
    wire [31:0] r_segs, m_segs; wire r_en, m_en, r_buzz, m_buzz; wire [5:0] r_led, m_led;
    hexn_react_core_v1 #(.TICK(TICK), .DEBMS(DEBMS)) RC (.clk(clk), .rst(rst | (mode != 2'd1)), .BTN1_N(BTN1_N), .BTN2_N(BTN2_N), .BTN3_N(BTN3_N), .segs(r_segs), .disp_en(r_en), .buzz(r_buzz), .led_n(r_led));
    hexn_morse_core_v1 #(.TICK(TICK), .DEBMS(DEBMS)) MC (.clk(clk), .rst(rst | (mode != 2'd2)), .BTN1_N(BTN1_N), .BTN2_N(BTN2_N), .segs(m_segs), .disp_en(m_en), .buzz(m_buzz), .led_n(m_led));
    assign status = {28'd0, ~m_led[5] & (mode == 2'd2), ~r_led[5] & (mode == 2'd1), mode};

    wire [31:0] segs = (mode == 2'd1) ? r_segs : (mode == 2'd2) ? m_segs : 32'hFFFFFFFF;
    wire en = (mode == 2'd1) ? r_en : (mode == 2'd2) ? m_en : 1'b0;
    wire buzz = (mode == 2'd1) ? r_buzz : (mode == 2'd2) ? m_buzz : 1'b0;
    hw262_shield_v2 SH (.clk(clk), .rst(rst), .enable(en), .segs(segs), .buzz(buzz), .latch(DISP_LATCH), .sclk(DISP_CLK), .sdata(DISP_DATA), .buzzer(BUZZER));

    reg [24:0] hb = 0; reg seen_cs = 0, seen_clk = 0, seen_mosi = 0;
    always @(posedge clk) begin hb <= hb + 1'b1; if (!SPI_CS_N) seen_cs <= 1'b1; if (SPI_SCLK) seen_clk <= 1'b1; if (!SPI_CS_N && SPI_MOSI) seen_mosi <= 1'b1; end
    wire [5:0] idle_led = ~{1'b0, seen_mosi, 1'b0, seen_clk, seen_cs, hb[24]};
    assign LED_N = (mode == 2'd1) ? r_led : (mode == 2'd2) ? m_led : idle_led;
    assign READY = (mode == 2'd1) || (mode == 2'd2);
endmodule
`default_nettype wire
