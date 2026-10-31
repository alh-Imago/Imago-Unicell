// hexn_open3_test.ino -- Hex-N open unit, stage 4a RAW WORD STREAM (fpga/build/hexn_open_unit_v3/unit_top.fs). Serial Monitor 115200, line ending Newline.
// Wiring as docs/hex-n/LINK_TEST_v1.md (IO5 CS -> 73, IO18 SCLK -> 74, IO23 MOSI -> 75, IO19 MISO <- 76, IO34 READY <- 77, GND) plus the HW-262 shield as docs/hex-n/DEMO_REACT_v1.md (A1 72, A2 71, A3 86, display 25/26/27, buzzer 28).
// Commands: id | status | mode 0..3 | replay | all.   'replay' = mode 3: load the River Exe table as WORDS in the stream, then stream 1000 real 2023 rows through the Tang scorer in batches of 250 and check every result word against the expected one.
// Stage 4a: in mode 3 the ESP32 sends scorer words (LOAD / BIAS / SCORE in any mix) and reads result words. Loading a table and streaming sensor data are the same act. Needs replay_data.h (tools/hexn_raw_replay_v1.py) next to this sketch.
#include <Arduino.h>
#include <SPI.h>
#include "replay_data.h"
#define PIN_CS 5
#define PIN_SCLK 18
#define PIN_MOSI 23
#define PIN_MISO 19
#define PIN_READY 34
static const uint32_t UNIT_ID_V2 = 0x57320002UL;
static const uint8_t SP_REACT = 1, SP_MORSE = 2, SP_DEC = 3, SP_GLYPH = 4;   // table spaces (cfg17 top nibble)
static SPISettings cfg(1000000, MSBFIRST, SPI_MODE0);
static void cs_low()  { digitalWrite(PIN_CS, LOW);  delayMicroseconds(3); }
static void cs_high() { delayMicroseconds(3); digitalWrite(PIN_CS, HIGH); delayMicroseconds(5); }
static void wr_reg(uint8_t a, uint32_t d) { uint8_t t[6] = { 0x01, a, (uint8_t)(d >> 24), (uint8_t)(d >> 16), (uint8_t)(d >> 8), (uint8_t)d }; SPI.beginTransaction(cfg); cs_low(); SPI.transfer(t, 6); cs_high(); SPI.endTransaction(); }
static uint32_t rd_reg(uint8_t a) { uint8_t t[7] = { 0x02, a, 0, 0, 0, 0, 0 }; SPI.beginTransaction(cfg); cs_low(); SPI.transfer(t, 7); cs_high(); SPI.endTransaction(); return ((uint32_t)t[3] << 24) | ((uint32_t)t[4] << 16) | ((uint32_t)t[5] << 8) | t[6]; }
static uint8_t txb[3 + 4 * 256 + 8];
static void wr_words(uint16_t addr, const uint32_t* w, int n) {          // one transaction, up to 255 words
  txb[0] = 0x03; txb[1] = addr >> 8; txb[2] = addr & 255;
  for (int i = 0; i < n; i++) { uint32_t v = w[i]; txb[3+4*i] = v >> 24; txb[4+4*i] = v >> 16; txb[5+4*i] = v >> 8; txb[6+4*i] = v; }
  SPI.beginTransaction(cfg); cs_low(); SPI.transfer(txb, 3 + 4 * n); cs_high(); SPI.endTransaction(); }
static void rd_words(uint16_t addr, uint32_t* w, int n) {
  txb[0] = 0x04; txb[1] = addr >> 8; txb[2] = addr & 255; txb[3] = 0; for (int i = 4; i < 4 + 4 * n; i++) txb[i] = 0;
  SPI.beginTransaction(cfg); cs_low(); SPI.transfer(txb, 4 + 4 * n); cs_high(); SPI.endTransaction();
  for (int i = 0; i < n; i++) w[i] = ((uint32_t)txb[4+4*i] << 24) | ((uint32_t)txb[5+4*i] << 16) | ((uint32_t)txb[6+4*i] << 8) | txb[7+4*i]; }



static bool cmd_id() {
  uint32_t id = rd_reg(0);
  Serial.printf("ID 0x%08lX -> %s\n", (unsigned long)id, id == UNIT_ID_V2 ? "OPEN UNIT (v2 bridge) OK" : "NOT the open unit (wiring, or another bitstream)");
  return id == UNIT_ID_V2; }
static void cmd_status() { uint32_t s = rd_reg(10); Serial.printf("status 0x%08lX: mode %lu, copy busy %lu, raw busy %lu, raw results written %lu\n", (unsigned long)s, (unsigned long)(s & 3), (unsigned long)((s >> 4) & 1), (unsigned long)((s >> 6) & 1), (unsigned long)((s >> 8) & 255)); }
static void set_mode(uint32_t m) { wr_reg(16, m); delay(50); Serial.printf("mode set to %lu (0 idle, 1 reaction game, 2 Morse key, 3 raw word stream)\n", (unsigned long)m); }
static uint32_t seq = 2000;
static bool run_batch(int count, int out_base) {                              // words 0..count-1 of the scratch RAM -> scorer; SCORE results to out_base...
  wr_reg(24, ((uint32_t)out_base << 16) | (uint32_t)count); wr_reg(25, ++seq);
  for (int i = 0; i < 2000; i++) { if (!((rd_reg(10) >> 6) & 1)) return true; } Serial.println("raw engine still busy"); return false; }
static void cmd_replay() {
  static uint32_t res[255];
  set_mode(0); set_mode(3);
  uint32_t t0 = micros(); wr_words(0, REPLAY_TABLE, REPLAY_TABLE_N); run_batch(REPLAY_TABLE_N, 400); uint32_t t1 = micros();
  Serial.printf("table: %d LOAD/BIAS words sent as a stream in %lu us\n", REPLAY_TABLE_N, (unsigned long)(t1 - t0));
  int wrong = 0, tp = 0, fn = 0, fp = 0, tn = 0; uint32_t tt = 0;
  for (int off = 0; off < REPLAY_N; off += 250) {
    int n = min(250, REPLAY_N - off); uint32_t a = micros();
    wr_words(0, REPLAY_ROWS + off, n); run_batch(n, 300); rd_words(300, res, n); tt += micros() - a;
    for (int i = 0; i < n; i++) { if (res[i] != REPLAY_EXPECT[off + i]) wrong++;
      int pred = res[i] >> 31, lab = REPLAY_LABEL[off + i]; if (lab) { if (pred) tp++; else fn++; } else { if (pred) fp++; else tn++; } } }
  Serial.printf("%d real rows streamed: %d result words wrong (want 0) | %.1f us per row all-in (write + score + read)\n", REPLAY_N, wrong, tt / (float)REPLAY_N);
  Serial.printf("decisions against the true labels: high-flow caught %d, missed %d; false alarms %d, correct quiet %d\n", tp, fn, fp, tn);
  Serial.println(wrong == 0 ? "RAW STREAM OK" : "RAW STREAM MISMATCH"); }
void setup() {
  Serial.begin(115200); pinMode(PIN_CS, OUTPUT); digitalWrite(PIN_CS, HIGH); pinMode(PIN_READY, INPUT); SPI.begin(PIN_SCLK, PIN_MISO, PIN_MOSI, -1); delay(300);
  Serial.println("\nHex-N open unit, stage 4a. Type: id | status | mode 0..3 | replay | all"); }
void loop() {
  static String line;
  while (Serial.available()) { char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (line == "id") cmd_id(); else if (line == "status") cmd_status(); else if (line == "replay") cmd_replay();
      else if (line == "all") { if (cmd_id()) { cmd_status(); cmd_replay(); cmd_status(); } }
      else if (line.startsWith("mode ")) set_mode((uint32_t)line.substring(5).toInt());
      line = ""; } else line += c; }
}
