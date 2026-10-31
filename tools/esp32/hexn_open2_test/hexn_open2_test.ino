// hexn_open2_test.ino -- Hex-N open unit, stage 2 (fpga/build/hexn_open_unit_v2/unit_top.fs). Serial Monitor 115200, line ending Newline.
// Wiring as docs/hex-n/LINK_TEST_v1.md (IO5 CS -> 73, IO18 SCLK -> 74, IO23 MOSI -> 75, IO19 MISO <- 76, IO34 READY <- 77, GND) plus the HW-262 shield as docs/hex-n/DEMO_REACT_v1.md (A1 72, A2 71, A3 86, display 25/26/27, buzzer 28).
// Commands: id | mode 0|1|2 | status | bins react|press|gap log | bins react|press|gap lin SHIFT LOW_MS | fast | strict | restore | cfg N [value] | all
// Stage 2: the tables and the binning are LOADED over SPI, not built in. 'fast' = a Morse table for a quick key (about 60 ms dots) with linear 32 ms bins; 'strict' = a reaction table that only calls a press under 128 ms good; 'restore' = factory tables and log2 bins.
#include <Arduino.h>
#include <SPI.h>
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
static void cmd_status() { uint32_t s = rd_reg(10); Serial.printf("status 0x%08lX: mode %lu, reaction ready %lu, Morse ready %lu, copy busy %lu, defaults loaded %lu\n", (unsigned long)s, (unsigned long)(s & 3), (unsigned long)((s >> 2) & 1), (unsigned long)((s >> 3) & 1), (unsigned long)((s >> 4) & 1), (unsigned long)((s >> 5) & 1)); }
static void set_mode(uint32_t m) { wr_reg(16, m); delay(50); Serial.printf("mode set to %lu (0 idle, 1 reaction game, 2 Morse key)\n", (unsigned long)m); }
static uint32_t seq = 1000;
static bool wait_idle() { for (int i = 0; i < 200; i++) { if (!((rd_reg(10) >> 4) & 1)) return true; delay(2); } Serial.println("copy still busy after 400 ms"); return false; }
static bool load_space(uint8_t space, const uint32_t* w, int n) {          // words -> scratch RAM (address 0) -> table space, then wait for the copy to finish
  wr_words(0, w, n); wr_reg(17, ((uint32_t)space << 28) | (uint32_t)n); wr_reg(19, ++seq);
  bool ok = wait_idle(); uint32_t back[255]; rd_words(0, back, n); int bad = 0; for (int i = 0; i < n; i++) if (back[i] != w[i]) bad++;
  Serial.printf("space %u: %d words loaded (scratch read-back %d wrong)\n", space, n, bad); return ok && bad == 0; }
static uint32_t w_load(int cls, int sensor, int b, int wt) { return (12UL << 28) | ((uint32_t)cls << 24) | ((uint32_t)((sensor << 4) | b) << 16) | (uint32_t)(wt & 255); }
static int make_morse(uint32_t* w, int t0, int t1, int t2) {               // three jobs: press (dash from bin t0), gap (letter gap from t1), gap (word gap from t2)
  int T[3] = { t0, t1, t2 }, n = 0;
  for (int c = 0; c < 2; c++) for (int s = 0; s < 8; s++) for (int k = 0; k < 13; k++) { int b = (k < 12) ? k : 15, wt = 0;
    if (s < 3 && b < 12) wt = c ? -10 * max(0, T[s] - b) : -10 * max(0, b - (T[s] - 1));
    w[n++] = w_load(c, s, b, wt); }
  w[n++] = 13UL << 28; return n; }
static int make_react(uint32_t* w, int good_max_bin) {                      // good hit = reaction bin <= good_max_bin
  int n = 0;
  for (int c = 0; c < 2; c++) for (int s = 0; s < 8; s++) for (int b = 0; b < 12; b++) { int wt = 0;
    if (s == 1) wt = c ? -10 * max(0, b - good_max_bin) : -10 * max(0, (good_max_bin + 1) - b);
    if (s == 0 && b == 0 && c == 1) wt = -100;
    w[n++] = w_load(c, s, b, wt); }
  w[n++] = 13UL << 28; return n; }
static int chan(const String& s) { return s == "react" ? 20 : s == "press" ? 21 : s == "gap" ? 22 : -1; }
static void cmd_bins(const String& a) {                                      // "react log" | "press lin 5 0"
  int sp = a.indexOf(' '); String ch = a.substring(0, sp < 0 ? a.length() : sp); int r = chan(ch);
  if (r < 0 || sp < 0) { Serial.println("bins react|press|gap log   or   bins react|press|gap lin SHIFT LOW_MS"); return; }
  String rest = a.substring(sp + 1); uint32_t v = 0;
  if (rest.startsWith("lin")) { int shift = 0; long low = 0; sscanf(rest.c_str(), "lin %d %ld", &shift, &low); v = 1UL | ((uint32_t)(shift & 15) << 4) | ((uint32_t)(low & 0xFFF) << 16); }
  wr_reg(r, v); Serial.printf("%s binning = 0x%08lX (%s)\n", ch.c_str(), (unsigned long)rd_reg(r), v ? "linear: (ms - low) >> shift, at most 11" : "log2 of ms"); }
static void cmd_fast() { static uint32_t w[255]; set_mode(0);
  wr_reg(21, 0x00000051); wr_reg(22, 0x00000051);                            // linear, 32 ms wide, from 0 ms
  int n = make_morse(w, 3, 4, 8); load_space(SP_MORSE, w, n);
  Serial.println("fast key loaded: dash from 96 ms, letter gap from 128 ms, word gap from 256 ms. Now: mode 2"); }
static void cmd_strict() { static uint32_t w[255]; set_mode(0); int n = make_react(w, 6); load_space(SP_REACT, w, n); Serial.println("strict reaction table loaded: good only under 128 ms. Now: mode 1"); }
static void cmd_restore() { set_mode(0); wr_reg(20, 0); wr_reg(21, 0); wr_reg(22, 0); wr_reg(23, ++seq); delay(5); wait_idle(); Serial.println("factory tables and log2 binning restored"); }
void setup() {
  Serial.begin(115200); pinMode(PIN_CS, OUTPUT); digitalWrite(PIN_CS, HIGH); pinMode(PIN_READY, INPUT); SPI.begin(PIN_SCLK, PIN_MISO, PIN_MOSI, -1); delay(300);
  Serial.println("\nHex-N open unit, stage 2. Type: id | mode 0|1|2 | status | bins ... | fast | strict | restore | cfg N [value] | all"); }
void loop() {
  static String line;
  while (Serial.available()) { char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (line == "id") cmd_id(); else if (line == "status") cmd_status(); else if (line == "fast") cmd_fast(); else if (line == "strict") cmd_strict(); else if (line == "restore") cmd_restore();
      else if (line == "all") { if (cmd_id()) { cmd_status(); cmd_restore(); cmd_status(); } }
      else if (line.startsWith("mode ")) set_mode((uint32_t)line.substring(5).toInt());
      else if (line.startsWith("bins ")) cmd_bins(line.substring(5));
      else if (line.startsWith("cfg ")) { int sp = line.indexOf(' ', 4); int n = line.substring(4, sp < 0 ? line.length() : sp).toInt();
        if (n < 16 || n > 31) Serial.println("config registers are 16..31");
        else { if (sp >= 0) wr_reg(n, (uint32_t)strtoul(line.substring(sp + 1).c_str(), NULL, 0)); Serial.printf("cfg %d = 0x%08lX\n", n, (unsigned long)rd_reg(n)); } }
      line = ""; } else line += c; }
}
