// unit_link.h -- the SPI link from the ESP32 (master) to the small unit on the Tang Nano 20K (ledger #1036). Same protocol as tools/esp32/unicell_unit_bridge.
// Wiring: IO5 CS_N, IO18 SCLK, IO23 MOSI, IO19 MISO, IO34 READY, GND. See docs/unit_bringup_guide.md.
#pragma once
#include <Arduino.h>
#include <SPI.h>

#define PIN_CS    5
#define PIN_SCLK  18
#define PIN_MOSI  23
#define PIN_MISO  19
#define PIN_READY 34
#define SPI_HZ    1000000

enum { R_ID = 0, R_STATUS = 1, R_CONTROL = 2, R_START_BLOCK = 3, R_NBLOCKS = 4, R_PLAY_COUNT = 5,
       R_CAP_COUNT = 6, R_SCRATCH = 7, R_MAX_OUT = 8, R_RPI = 9 };
enum { C_LOAD = 1, C_SAVE = 2, C_PLAY = 4, C_CAP_CLEAR = 8, C_CLEAR_DONE = 16, C_SD_REINIT = 32 };
enum { S_SD_READY = 1, S_SD_ERROR = 2, S_SD_BUSY = 4, S_PLAY_BUSY = 8, S_SD_DONE = 16, S_PLAY_DONE = 32, S_CAP_NONEMPTY = 64 };
static const uint32_t UNIT_ID = 0x57320001UL;
static const int MAX_WORDS = 512;              // playout RAM holds 1024 words; keep half free

static SPISettings spi_cfg(SPI_HZ, MSBFIRST, SPI_MODE0);
static void cs_low()  { digitalWrite(PIN_CS, LOW);  delayMicroseconds(3); }
static void cs_high() { delayMicroseconds(3); digitalWrite(PIN_CS, HIGH); delayMicroseconds(5); }

static void link_begin() {
  pinMode(PIN_CS, OUTPUT); digitalWrite(PIN_CS, HIGH);
  pinMode(PIN_READY, INPUT);
  SPI.begin(PIN_SCLK, PIN_MISO, PIN_MOSI, -1);
}
static void wr_reg(uint8_t a, uint32_t d) {
  uint8_t t[6] = { 0x01, a, (uint8_t)(d >> 24), (uint8_t)(d >> 16), (uint8_t)(d >> 8), (uint8_t)d };
  SPI.beginTransaction(spi_cfg); cs_low(); SPI.transfer(t, 6); cs_high(); SPI.endTransaction();
}
static uint32_t rd_reg(uint8_t a) {
  uint8_t t[7] = { 0x02, a, 0, 0, 0, 0, 0 };
  SPI.beginTransaction(spi_cfg); cs_low(); SPI.transfer(t, 7); cs_high(); SPI.endTransaction();
  return ((uint32_t)t[3] << 24) | ((uint32_t)t[4] << 16) | ((uint32_t)t[5] << 8) | t[6];
}
static void wr_words(uint16_t addr, const int32_t* w, int n) {
  while (n > 0) {
    int k = n > 64 ? 64 : n;
    uint8_t t[3 + 64 * 4]; t[0] = 0x03; t[1] = addr >> 8; t[2] = addr & 255;
    for (int i = 0; i < k; i++) { uint32_t v = (uint32_t)w[i]; t[3 + 4*i] = v >> 24; t[4 + 4*i] = v >> 16; t[5 + 4*i] = v >> 8; t[6 + 4*i] = v; }
    SPI.beginTransaction(spi_cfg); cs_low(); SPI.transfer(t, 3 + 4 * k); cs_high(); SPI.endTransaction();
    w += k; n -= k; addr += k;
  }
}
static void rd_words(uint16_t addr, int32_t* w, int n) {
  while (n > 0) {
    int k = n > 64 ? 64 : n;
    uint8_t t[4 + 64 * 4] = { 0x04, (uint8_t)(addr >> 8), (uint8_t)(addr & 255), 0 };
    for (int i = 4; i < 4 + 4 * k; i++) t[i] = 0;
    SPI.beginTransaction(spi_cfg); cs_low(); SPI.transfer(t, 4 + 4 * k); cs_high(); SPI.endTransaction();
    for (int i = 0; i < k; i++) w[i] = (int32_t)(((uint32_t)t[4 + 4*i] << 24) | ((uint32_t)t[5 + 4*i] << 16) | ((uint32_t)t[6 + 4*i] << 8) | t[7 + 4*i]);
    w += k; n -= k; addr += k;
  }
}
static bool wait_status(uint32_t mask, uint32_t ms) {
  uint32_t t0 = millis();
  while (millis() - t0 < ms) { if ((rd_reg(R_STATUS) & mask) == mask) return true; delay(1); }
  return false;
}

// Feed `items` items of `lanes` words each (item-major, lane-minor) through the design one at a time (pacing MAX_OUT=1, RPI=1) and read `items` results.
// Returns an empty string on success, else an error message.
static const char* run_items(const int32_t* w, int items, int lanes, int32_t* out) {
  if (items < 1 || lanes < 1 || items * lanes > MAX_WORDS) return "too many words (limit 512)";
  if (rd_reg(R_ID) != UNIT_ID) return "the unit does not answer (check the FPGA is loaded and the SPI wiring)";
  wr_reg(R_CONTROL, C_CAP_CLEAR);
  wr_reg(R_MAX_OUT, 1); wr_reg(R_RPI, 1);
  wr_words(0, w, items * lanes);
  wr_reg(R_PLAY_COUNT, items * lanes);
  wr_reg(R_CONTROL, C_PLAY);
  uint32_t t0 = millis();
  while (rd_reg(R_CAP_COUNT) < (uint32_t)items) { if (millis() - t0 > 4000) return "timed out waiting for results"; }
  rd_words(0, out, items);
  return "";
}
// SD card: load (card -> playout RAM) or save (capture RAM -> card), `n` raw 512-byte blocks starting at `block`. Empty string = ok.
static const char* sd_op(bool save, uint32_t block, uint32_t n) {
  if (block < 16) return "refusing blocks below 16 (block 0 holds a FAT32 card's partition table)";
  if (n < 1 || n > 8) return "block count must be 1 to 8";
  if (!(rd_reg(R_STATUS) & S_SD_READY)) return "SD card not ready (reseat it, then use re-init)";
  wr_reg(R_CONTROL, C_CLEAR_DONE); wr_reg(R_START_BLOCK, block); wr_reg(R_NBLOCKS, n); wr_reg(R_CONTROL, save ? C_SAVE : C_LOAD);
  bool done = wait_status(S_SD_DONE, 6000); uint32_t s = rd_reg(R_STATUS);
  if (!done || (s & S_SD_ERROR)) return "SD operation failed";
  return "";
}
