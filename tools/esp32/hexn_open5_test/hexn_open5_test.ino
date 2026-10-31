// hexn_open5_test.ino -- Hex-N open unit, stage 4b PRESETS and TWO JUDGES (fpga/build/hexn_open_unit_v5/unit_top.fs). Serial Monitor 115200, line ending Newline.
// Wiring as docs/hex-n/LINK_TEST_v1.md (IO5 CS -> 73, IO18 SCLK -> 74, IO23 MOSI -> 75, IO19 MISO <- 76, IO34 READY <- 77, GND) plus the HW-262 shield as docs/hex-n/DEMO_REACT_v1.md (A1 72, A2 71, A3 86, display 25/26/27, buzzer 28).
// Commands: id | status | preset 0..8 | setp P MODE BR BP BG IN OUT JC (edit preset P, 1..8, in the Tang's preset table) | factory | twojudge [BIAS_B] | all.   Needs replay_data.h next to this sketch (python3 tools/hexn_raw_replay_v1.py).
// preset 0 = no preset (direct registers); 1 reaction game, 2 Morse key, 3 raw stream (one judge), 4 raw stream (two judges), 5..8 idle until you edit them. 'twojudge' streams the River Exe table into judges A AND B (B gets a different bias), then 1000 real rows: two answers per row.
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
static void cmd_status() { uint32_t s = rd_reg(10); Serial.printf("status 0x%08lX: mode %lu, copy busy %lu, raw busy %lu, preset active %lu, raw results %lu | cfg29 (preset select) = %lu\n", (unsigned long)s, (unsigned long)(s & 3), (unsigned long)((s >> 4) & 1), (unsigned long)((s >> 6) & 1), (unsigned long)((s >> 7) & 1), (unsigned long)((s >> 8) & 255), (unsigned long)rd_reg(29)); }
static uint32_t seq = 3000;
static bool wait_copy() { for (int i = 0; i < 200; i++) { if (!((rd_reg(10) >> 4) & 1)) return true; delay(2); } return false; }
static bool wait_raw() { for (int i = 0; i < 4000; i++) { if (!((rd_reg(10) >> 6) & 1)) return true; } Serial.println("raw engine still busy"); return false; }
static void set_preset(int n) { wr_reg(29, 0); delay(5); wr_reg(29, n); delay(20);
  Serial.printf("preset %d %s | ", n, n == 0 ? "(none: the direct registers act)" : n == 1 ? "reaction game" : n == 2 ? "Morse key" : n == 3 ? "raw stream, one judge" : n == 4 ? "raw stream, two judges" : "(as edited)"); cmd_status(); }
// the ESP32 keeps a shadow copy of the 64-word preset table, edits it, and sends all 64 words (copy space 5)
static uint32_t shadow[64];
static void shadow_factory() { memset(shadow, 0, sizeof(shadow)); shadow[0] = 1; shadow[8] = 2; shadow[16] = 3; shadow[24] = 3; shadow[24 + 6] = 1; }
static void send_presets() { wr_words(0, shadow, 64); wr_reg(17, (5UL << 28) | 64UL); wr_reg(19, ++seq); wait_copy(); Serial.println("preset table sent (64 words)"); }
static void cmd_setp(const String& a) {
  unsigned p, m, br, bp, bg, in, out, jc; if (sscanf(a.c_str(), "%u %u %x %x %x %x %x %u", &p, &m, &br, &bp, &bg, &in, &out, &jc) != 8 || p < 1 || p > 8) { Serial.println("setp P(1..8) MODE BR BP BG IN OUT JC   (BR/BP/BG/IN/OUT in hex; 0 = defaults)"); return; }
  uint32_t* w = shadow + (p - 1) * 8; w[0] = m; w[1] = br; w[2] = bp; w[3] = bg; w[4] = in; w[5] = out; w[6] = jc; w[7] = 0; send_presets(); Serial.printf("preset %u set; use: preset %u\n", p, p); }
static void cmd_twojudge(long biasB) {
  static uint32_t st[420], res[255]; int n = 0;
  for (int i = 0; i < 192; i++) st[n++] = REPLAY_TABLE[i];                       // judge A (loads go to A while jc = 1)
  st[n++] = 0xE0000003UL;                                                         // control: two judges, loads to B
  for (int i = 0; i < 192; i++) st[n++] = REPLAY_TABLE[i];                       // the same weights into judge B ...
  st[n++] = (13UL << 28) | (uint32_t)(biasB & 0xFFFF);                           // ... with a different bias
  st[n++] = 0xE0000001UL;                                                         // control: two judges, loads to A
  st[n++] = 13UL << 28;                                                           // judge A bias 0
  set_preset(4);
  wr_words(0, st, 128); wr_words(128, st + 128, 128); wr_words(256, st + 256, n - 256);
  wr_reg(24, (400UL << 16) | (uint32_t)n); wr_reg(25, ++seq); wait_raw(); Serial.printf("setup stream sent: %d words (two tables and two biases)\n", n);
  int wrongA = 0, tpA = 0, fnA = 0, fpA = 0, tnA = 0, tpB = 0, fnB = 0, fpB = 0, tnB = 0;
  for (int off = 0; off < REPLAY_N; off += 125) {
    int k = min(125, REPLAY_N - off); wr_words(0, REPLAY_ROWS + off, k); wr_reg(24, (300UL << 16) | (uint32_t)k); wr_reg(25, ++seq); wait_raw(); rd_words(300, res, 2 * k);
    for (int i = 0; i < k; i++) { uint32_t a = res[2 * i], b = res[2 * i + 1]; int lab = REPLAY_LABEL[off + i];
      if (a != REPLAY_EXPECT[off + i]) wrongA++;
      if (lab) { if (a >> 31) tpA++; else fnA++; if (b >> 31) tpB++; else fnB++; } else { if (a >> 31) fpA++; else tnA++; if (b >> 31) fpB++; else tnB++; } } }
  Serial.printf("judge A (bias 0): caught %d, missed %d, false alarms %d, correct quiet %d | A result words wrong vs the expected: %d\n", tpA, fnA, fpA, tnA, wrongA);
  Serial.printf("judge B (bias %ld): caught %d, missed %d, false alarms %d, correct quiet %d\n", biasB, tpB, fnB, fpB, tnB);
  Serial.println(wrongA == 0 ? "TWO JUDGES OK (A matches the reference; B differs only by its bias)" : "MISMATCH"); }
void setup() {
  Serial.begin(115200); pinMode(PIN_CS, OUTPUT); digitalWrite(PIN_CS, HIGH); pinMode(PIN_READY, INPUT); SPI.begin(PIN_SCLK, PIN_MISO, PIN_MOSI, -1); delay(300); shadow_factory();
  Serial.println("\nHex-N open unit, stage 4b. Type: id | status | preset 0..8 | setp ... | factory | twojudge [BIAS_B] | all"); }
void loop() {
  static String line;
  while (Serial.available()) { char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (line == "id") cmd_id(); else if (line == "status") cmd_status();
      else if (line == "factory") { wr_reg(23, ++seq); delay(5); wait_copy(); shadow_factory(); Serial.println("factory tables and presets restored"); }
      else if (line == "all") { if (cmd_id()) { cmd_status(); set_preset(1); delay(300); set_preset(2); set_preset(0); cmd_twojudge(-40); set_preset(0); } }
      else if (line.startsWith("preset ")) set_preset((int)line.substring(7).toInt());
      else if (line.startsWith("setp ")) cmd_setp(line.substring(5));
      else if (line.startsWith("twojudge")) cmd_twojudge(line.length() > 9 ? line.substring(9).toInt() : -40);
      line = ""; } else line += c; }
}
