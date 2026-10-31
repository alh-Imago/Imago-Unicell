// hexn_link_speed.ino -- Hex-N: times the ESP32 <-> Tang Nano 20K SPI link and the ESP32's own Connect Four search.
// Load the CORDIC unit bitstream on the Tang first (fpga/build/unit_cordic_v1/unit_top.fs). Serial Monitor 115200 baud.
// Wiring (ESP32 pin -> Tang Nano package pin): IO5 CS_N -> 73, IO18 SCLK -> 74, IO23 MOSI -> 75, IO19 MISO <- 76, IO34 READY <- 77, GND-GND.
// Type: id | link | search | all
#include <Arduino.h>
#include <SPI.h>
#include "c4search.h"
#define PIN_CS 5
#define PIN_SCLK 18
#define PIN_MOSI 23
#define PIN_MISO 19
#define PIN_READY 34
enum { R_ID = 0, R_SCRATCH = 7 };
static const uint32_t UNIT_ID = 0x57320001UL;
static SPISettings cfg(1000000, MSBFIRST, SPI_MODE0);
static void setHz(uint32_t hz) { cfg = SPISettings(hz, MSBFIRST, SPI_MODE0); }
static void cs_low()  { digitalWrite(PIN_CS, LOW);  delayMicroseconds(3); }
static void cs_high() { delayMicroseconds(3); digitalWrite(PIN_CS, HIGH); delayMicroseconds(5); }
static void wr_reg(uint8_t a, uint32_t d) {
  uint8_t t[6] = { 0x01, a, (uint8_t)(d >> 24), (uint8_t)(d >> 16), (uint8_t)(d >> 8), (uint8_t)d };
  SPI.beginTransaction(cfg); cs_low(); SPI.transfer(t, 6); cs_high(); SPI.endTransaction();
}
static uint32_t rd_reg(uint8_t a) {
  uint8_t t[7] = { 0x02, a, 0, 0, 0, 0, 0 };
  SPI.beginTransaction(cfg); cs_low(); SPI.transfer(t, 7); cs_high(); SPI.endTransaction();
  return ((uint32_t)t[3] << 24) | ((uint32_t)t[4] << 16) | ((uint32_t)t[5] << 8) | t[6];
}
static void wr_block(uint16_t addr, uint32_t seed, int k) {         // k <= 64 words into the playout RAM
  uint8_t t[3 + 64 * 4]; t[0] = 0x03; t[1] = addr >> 8; t[2] = addr & 255;
  for (int i = 0; i < k; i++) { uint32_t v = seed + i; t[3+4*i] = v >> 24; t[4+4*i] = v >> 16; t[5+4*i] = v >> 8; t[6+4*i] = v; }
  SPI.beginTransaction(cfg); cs_low(); SPI.transfer(t, 3 + 4 * k); cs_high(); SPI.endTransaction();
}
static void rd_block(uint16_t addr, int k) {                          // k <= 64 words from the capture RAM
  uint8_t t[4 + 64 * 4] = { 0x04, (uint8_t)(addr >> 8), (uint8_t)(addr & 255), 0 };
  SPI.beginTransaction(cfg); cs_low(); SPI.transfer(t, 4 + 4 * k); cs_high(); SPI.endTransaction();
}

static bool cmd_id() {
  uint32_t id = rd_reg(R_ID);
  Serial.printf("ID read 0x%08lX (expect 0x%08lX) -> %s | READY pin=%d\n", (unsigned long)id, (unsigned long)UNIT_ID, id == UNIT_ID ? "LINK OK" : "NO LINK", digitalRead(PIN_READY));
  return id == UNIT_ID;
}
static void cmd_link() {
  if (!cmd_id()) { Serial.println("Stop: fix the wiring / load the bitstream first (see LINK_TEST_v1.md)."); return; }
  const uint32_t hzs[3] = { 500000, 1000000, 1500000 };                 // bridge limit is SCLK < 27 MHz/16 = 1.69 MHz
  for (int h = 0; h < 3; h++) {
    setHz(hzs[h]);
    int bad = 0; const int N = 200;
    for (int i = 0; i < N; i++) { uint32_t v = 0xA5000000UL + i * 2654435761UL; wr_reg(R_SCRATCH, v); if (rd_reg(R_SCRATCH) != v) bad++; }
    uint32_t t0 = micros(); for (int i = 0; i < N; i++) (void)rd_reg(R_ID); uint32_t us = micros() - t0;
    t0 = micros(); for (int i = 0; i < 100; i++) wr_block(0, i, 64); uint32_t uw = micros() - t0;
    t0 = micros(); for (int i = 0; i < 100; i++) rd_block(0, 64); uint32_t ur = micros() - t0;
    t0 = micros(); for (int i = 0; i < 6400; i++) wr_block(0, i, 1); uint32_t u1 = micros() - t0;
    Serial.printf("SCLK %lu Hz: scratch loopback %d/%d wrong | reg read %.1f us | 64-word write %.0f us = %.0f words/s | 64-word read %.0f us = %.0f words/s | 1-word write %.1f us = %.0f words/s\n",
      (unsigned long)hzs[h], bad, N, us / (float)N, uw / 100.0, 6400000000.0 / uw, ur / 100.0, 6400000000.0 / ur, u1 / 6400.0, 6400000000.0 / u1);
  }
  setHz(1000000);
  Serial.println("A position is 1-3 words; compare 'one per transaction' (1-word row) with 'batch of 64' (64-word row).");
}
static void cmd_search() {
  int cols[] = { 3, 3, 2, 4 };
  for (int d = 3; d <= 6; d++) {
    C4 g; for (int c : cols) g.play(c);
    uint32_t t0 = micros(); int m = g.best(d); uint32_t us = micros() - t0;
    Serial.printf("depth %d: move %d, %lu nodes, %.1f ms, %.0f nodes/s\n", d, m, (unsigned long)g.nodes, us / 1000.0, us ? g.nodes * 1e6 / us : 0.0);
  }
}
void setup() {
  Serial.begin(115200);
  pinMode(PIN_CS, OUTPUT); digitalWrite(PIN_CS, HIGH);
  pinMode(PIN_READY, INPUT);
  SPI.begin(PIN_SCLK, PIN_MISO, PIN_MOSI, -1);
  delay(300);
  Serial.println("\nHex-N link speed test. Type: id | link | search | all");
}
void loop() {
  static String line;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (line == "id") cmd_id(); else if (line == "link") cmd_link(); else if (line == "search") cmd_search();
      else if (line == "all") { cmd_link(); cmd_search(); }
      line = "";
    } else line += c;
  }
}
