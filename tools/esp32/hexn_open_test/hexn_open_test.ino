// hexn_open_test.ino -- Hex-N open unit, stage 1 (fpga/build/hexn_open_unit_v1/unit_top.fs). Serial Monitor 115200, line ending Newline.
// Wiring as docs/hex-n/LINK_TEST_v1.md (IO5 CS -> 73, IO18 SCLK -> 74, IO23 MOSI -> 75, IO19 MISO <- 76, IO34 READY <- 77, GND) plus the HW-262 shield as docs/hex-n/DEMO_REACT_v1.md (A1 72, A2 71, A3 86, display 25/26/27, buzzer 28).
// Commands: id | mode 0|1|2 (0 idle, 1 reaction game, 2 Morse key) | cfg N [value] (read or write config register 16..31) | status | ram (long-transfer test: 64 and 200 words) | all
// The v2 bridge counts bytes in 16 bits, so long transactions work (v1 loses the 64th word of a 64-word transfer).
#include <Arduino.h>
#include <SPI.h>
#define PIN_CS 5
#define PIN_SCLK 18
#define PIN_MOSI 23
#define PIN_MISO 19
#define PIN_READY 34
static const uint32_t UNIT_ID_V2 = 0x57320002UL;
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
  Serial.printf("ID 0x%08lX -> %s\n", (unsigned long)id, id == UNIT_ID_V2 ? "OPEN UNIT (v2 bridge) OK" : id == 0x57320001UL ? "an OLD unit (v1 bridge) is loaded, not the open unit" : "NO LINK (wiring, or no bitstream)");
  return id == UNIT_ID_V2; }
static void cmd_status() { uint32_t s = rd_reg(10), m = rd_reg(16); Serial.printf("mode register %lu | status 0x%08lX: mode %lu, reaction core ready %lu, Morse core ready %lu | READY pin %d\n", (unsigned long)m, (unsigned long)s, (unsigned long)(s & 3), (unsigned long)((s >> 2) & 1), (unsigned long)((s >> 3) & 1), digitalRead(PIN_READY)); }
static void set_mode(uint32_t m) { wr_reg(16, m); delay(50); Serial.printf("mode set to %lu (%s)\n", (unsigned long)m, m == 0 ? "idle" : m == 1 ? "reaction game: wait for the target, press the matching button" : m == 2 ? "Morse key: A1 is the key, A2 clears" : "not defined"); cmd_status(); }
static void cmd_ram() {
  static uint32_t a[256], b[256]; const int sizes[3] = { 64, 100, 200 };
  for (int k = 0; k < 3; k++) {
    int n = sizes[k]; for (int i = 0; i < n; i++) a[i] = 0xC3000000UL + (uint32_t)i * 40503UL + n;
    uint32_t t0 = micros(); wr_words(0, a, n); uint32_t t1 = micros(); rd_words(0, b, n); uint32_t t2 = micros();
    int bad = 0; for (int i = 0; i < n; i++) if (b[i] != a[i]) bad++;
    Serial.printf("%d words in ONE transaction: %d wrong | write %lu us, read %lu us (%.0f words/s each way)\n", n, bad, (unsigned long)(t1 - t0), (unsigned long)(t2 - t1), n * 1e6 / (double)(t1 - t0));
  } }
void setup() {
  Serial.begin(115200); pinMode(PIN_CS, OUTPUT); digitalWrite(PIN_CS, HIGH); pinMode(PIN_READY, INPUT); SPI.begin(PIN_SCLK, PIN_MISO, PIN_MOSI, -1); delay(300);
  Serial.println("\nHex-N open unit test. Type: id | mode 0|1|2 | cfg N [value] | status | ram | all"); }
void loop() {
  static String line;
  while (Serial.available()) { char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (line == "id") cmd_id(); else if (line == "status") cmd_status(); else if (line == "ram") cmd_ram();
      else if (line == "all") { if (cmd_id()) { cmd_ram(); set_mode(0); } }
      else if (line.startsWith("mode ")) set_mode((uint32_t)line.substring(5).toInt());
      else if (line.startsWith("cfg ")) { int sp = line.indexOf(' ', 4); int n = line.substring(4, sp < 0 ? line.length() : sp).toInt();
        if (n < 16 || n > 31) Serial.println("config registers are 16..31");
        else { if (sp >= 0) wr_reg(n, (uint32_t)strtoul(line.substring(sp + 1).c_str(), NULL, 0)); Serial.printf("cfg %d = 0x%08lX\n", n, (unsigned long)rd_reg(n)); } }
      line = ""; } else line += c; }
}
