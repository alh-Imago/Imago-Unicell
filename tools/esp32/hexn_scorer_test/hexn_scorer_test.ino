// hexn_scorer_test.ino -- Hex-N: drives the Tang batch scorer (fpga/build/hexn_scorer_unit_v1/unit_top.fs) over SPI and times it against the ESP32 judging the same words itself. Serial Monitor 115200, Newline.
// Wiring as in docs/hex-n/LINK_TEST_v1.md (IO5 CS -> 73, IO18 SCLK -> 74, IO23 MOSI -> 75, IO19 MISO <- 76, IO34 READY <- 77, GND). Commands: id | table | bench | all
// Word format (hexn_scorer_v1.v): top nibble 0..11 = SCORE (sensor i's bin in bits 4i+3:4i, 8 sensors); 12 = LOAD table entry; 13 = BIAS. Result {pred, 3'b0, s1[11:0] at 27:16, s0[11:0] at 11:0}.
#include <Arduino.h>
#include <SPI.h>
#define PIN_CS 5
#define PIN_SCLK 18
#define PIN_MOSI 23
#define PIN_MISO 19
#define PIN_READY 34
enum { R_ID = 0, R_STATUS = 1, R_CONTROL = 2, R_PLAY_COUNT = 5, R_CAP_COUNT = 6 };
enum { C_PLAY = 4, C_CAP_CLEAR = 8, C_CLEAR_DONE = 16 };
enum { S_PLAY_DONE = 32 };
static const uint32_t UNIT_ID = 0x57320001UL;
static const int NS = 8, NBIN = 12;
static int SPI_HZ_USED = 1000000;
static SPISettings cfg(1000000, MSBFIRST, SPI_MODE0);
static void cs_low()  { digitalWrite(PIN_CS, LOW);  delayMicroseconds(3); }
static void cs_high() { delayMicroseconds(3); digitalWrite(PIN_CS, HIGH); delayMicroseconds(5); }
static void wr_reg(uint8_t a, uint32_t d) { uint8_t t[6] = { 0x01, a, (uint8_t)(d >> 24), (uint8_t)(d >> 16), (uint8_t)(d >> 8), (uint8_t)d }; SPI.beginTransaction(cfg); cs_low(); SPI.transfer(t, 6); cs_high(); SPI.endTransaction(); }
static uint32_t rd_reg(uint8_t a) { uint8_t t[7] = { 0x02, a, 0, 0, 0, 0, 0 }; SPI.beginTransaction(cfg); cs_low(); SPI.transfer(t, 7); cs_high(); SPI.endTransaction(); return ((uint32_t)t[3] << 24) | ((uint32_t)t[4] << 16) | ((uint32_t)t[5] << 8) | t[6]; }
static void wr_words(uint16_t addr, const uint32_t* w, int n) {
  while (n > 0) { int k = n > 64 ? 64 : n; uint8_t t[3 + 64 * 4]; t[0] = 0x03; t[1] = addr >> 8; t[2] = addr & 255;
    for (int i = 0; i < k; i++) { uint32_t v = w[i]; t[3+4*i] = v >> 24; t[4+4*i] = v >> 16; t[5+4*i] = v >> 8; t[6+4*i] = v; }
    SPI.beginTransaction(cfg); cs_low(); SPI.transfer(t, 3 + 4 * k); cs_high(); SPI.endTransaction(); w += k; n -= k; addr += k; } }
static void rd_words(uint16_t addr, uint32_t* w, int n) {
  while (n > 0) { int k = n > 64 ? 64 : n; uint8_t t[4 + 64 * 4] = { 0x04, (uint8_t)(addr >> 8), (uint8_t)(addr & 255), 0 };
    SPI.beginTransaction(cfg); cs_low(); SPI.transfer(t, 4 + 4 * k); cs_high(); SPI.endTransaction();
    for (int i = 0; i < k; i++) w[i] = ((uint32_t)t[4+4*i] << 24) | ((uint32_t)t[5+4*i] << 16) | ((uint32_t)t[6+4*i] << 8) | t[7+4*i];
    w += k; n -= k; addr += k; } }

// ---- the test table (fixed pseudo-random, whole numbers -127..0) and bias, and the local judge ----
static int8_t W[2][NS][16];
static int BIAS = 17;
static uint32_t lcg = 12345;
static uint32_t rnd() { lcg = lcg * 1664525UL + 1013904223UL; return lcg >> 8; }
static void make_table() { lcg = 12345; for (int c = 0; c < 2; c++) for (int s = 0; s < NS; s++) for (int b = 0; b < 16; b++) W[c][s][b] = -(int)(rnd() % 100); }
static uint32_t local_judge(uint32_t w) {
  int s0 = 0, s1 = 0; for (int s = 0; s < NS; s++) { int b = (w >> (4 * s)) & 15; s0 += W[0][s][b]; s1 += W[1][s][b]; }
  return ((uint32_t)((s1 + BIAS) > s0) << 31) | ((uint32_t)(s1 & 0xFFF) << 16) | (uint32_t)(s0 & 0xFFF);
}
static uint32_t make_sample() { uint32_t w = 0; for (int s = 0; s < NS; s++) w |= (uint32_t)(rnd() % NBIN) << (4 * s); return w; }

static bool wait_play_done(uint32_t ms) { uint32_t t0 = millis(); while (millis() - t0 < ms) { if (rd_reg(R_STATUS) & S_PLAY_DONE) return true; } return false; }
static bool cmd_id() { uint32_t id = rd_reg(R_ID); Serial.printf("ID 0x%08lX -> %s\n", (unsigned long)id, id == UNIT_ID ? "LINK OK" : "NO LINK (wiring, or the scorer bitstream is not loaded)"); return id == UNIT_ID; }
static bool cmd_table() {
  make_table(); static uint32_t buf[2 * NS * NBIN + 1]; int n = 0;
  for (int c = 0; c < 2; c++) for (int s = 0; s < NS; s++) for (int b = 0; b < NBIN; b++) buf[n++] = (12UL << 28) | ((uint32_t)c << 24) | ((uint32_t)((s << 4) | b) << 16) | (uint8_t)W[c][s][b];
  buf[n++] = (13UL << 28) | (uint16_t)BIAS;
  uint32_t t0 = micros();
  wr_reg(R_CONTROL, C_CAP_CLEAR); wr_reg(R_CONTROL, C_CLEAR_DONE); wr_words(0, buf, n); wr_reg(R_PLAY_COUNT, n); wr_reg(R_CONTROL, C_PLAY);
  bool ok = wait_play_done(500); uint32_t us = micros() - t0;
  Serial.printf("table: %d words (%d weights + bias) loaded in %lu us, play %s\n", n, n - 1, (unsigned long)us, ok ? "done" : "TIMED OUT");
  return ok;
}
static void cmd_bench() {
  const int N = 64, REPS = 20; static uint32_t smp[64], res[64];
  uint32_t tw = 0, tp = 0, tr = 0, tl = 0; int bad = 0, timeouts = 0; long polls = 0;
  for (int rep = 0; rep < REPS; rep++) {
    for (int i = 0; i < N; i++) smp[i] = make_sample();
    uint32_t t0 = micros();
    wr_reg(R_CONTROL, C_CAP_CLEAR); wr_words(0, smp, N); wr_reg(R_PLAY_COUNT, N); wr_reg(R_CONTROL, C_PLAY);
    uint32_t t1 = micros();
    uint32_t t = millis(); while (rd_reg(R_CAP_COUNT) < (uint32_t)N) { polls++; if (millis() - t > 200) { timeouts++; break; } }
    uint32_t t2 = micros();
    rd_words(0, res, N);
    uint32_t t3 = micros();
    uint32_t sink = 0; for (int i = 0; i < N; i++) sink += local_judge(smp[i]);   // the ESP32 judging the same 64 words itself
    uint32_t t4 = micros();
    (void)sink;
    for (int i = 0; i < N; i++) if (res[i] != local_judge(smp[i])) bad++;
    tw += t1 - t0; tp += t2 - t1; tr += t3 - t2; tl += t4 - t3;
  }
  Serial.printf("SPI %d Hz, batches of %d words x %d: wrong %d of %d | timeouts %d\n", SPI_HZ_USED, N, REPS, bad, N * REPS, timeouts);
  Serial.printf("per batch: write+start %.0f us | wait for results %.0f us (%.1f register polls) | read %.0f us | Tang route total %.0f us = %.1f us per word\n",
    tw / (float)REPS, tp / (float)REPS, polls / (float)REPS, tr / (float)REPS, (tw + tp + tr) / (float)REPS, (tw + tp + tr) / (float)(REPS * N));
  Serial.printf("ESP32 judging the same 64 words itself: %.0f us per batch = %.2f us per word\n", tl / (float)REPS, tl / (float)(REPS * N));
}
void setup() {
  Serial.begin(115200); pinMode(PIN_CS, OUTPUT); digitalWrite(PIN_CS, HIGH); pinMode(PIN_READY, INPUT); SPI.begin(PIN_SCLK, PIN_MISO, PIN_MOSI, -1); delay(300);
  Serial.println("\nHex-N scorer test. Type: id | table | bench | all   (hz 500000|1000000|1500000 sets the SPI clock)");
}
void loop() {
  static String line;
  while (Serial.available()) { char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (line == "id") cmd_id(); else if (line == "table") cmd_table(); else if (line == "bench") cmd_bench();
      else if (line == "all") { if (cmd_id() && cmd_table()) cmd_bench(); }
      else if (line.startsWith("hz ")) { SPI_HZ_USED = line.substring(3).toInt(); cfg = SPISettings(SPI_HZ_USED, MSBFIRST, SPI_MODE0); Serial.printf("SPI clock %d Hz\n", SPI_HZ_USED); }
      line = ""; } else line += c; }
}
