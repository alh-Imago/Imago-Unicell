// hexn_open4_test.ino -- Hex-N open unit, stage 3 PIN MATRIX (fpga/build/hexn_open_unit_v4/unit_top.fs). Serial Monitor 115200, line ending Newline.
// Wiring as docs/hex-n/LINK_TEST_v1.md (IO5 CS -> 73, IO18 SCLK -> 74, IO23 MOSI -> 75, IO19 MISO <- 76, IO34 READY <- 77, GND) plus the HW-262 shield as docs/hex-n/DEMO_REACT_v1.md (A1 72, A2 71, A3 86, display 25/26/27, buzzer 28).
// Commands: id | mode 0..3 | pins | btn 1|2|3 TANGPIN | out latch|clk|data|buzz TANGPIN | default | all.   The Tang pins in the pool: 72 71 86 25 26 27 28 29 30 31 85 80 42 41 56 54 (the first seven are the shield's normal wiring).
// 'pins' prints the live level of each pool pin: press a button or touch a wire and see which pin changes. 'btn 1 31' moves button 1 to Tang pin 31; 'out buzz 54' moves the buzzer to Tang pin 54. 'default' puts the shield wiring back.
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




static const int POOLPIN[16] = { 72, 71, 86, 25, 26, 27, 28, 29, 30, 31, 85, 80, 42, 41, 56, 54 };
static int pool_index(int tang) { for (int i = 0; i < 16; i++) if (POOLPIN[i] == tang) return i; return -1; }
static bool cmd_id() {
  uint32_t id = rd_reg(0);
  Serial.printf("ID 0x%08lX -> %s\n", (unsigned long)id, id == UNIT_ID_V2 ? "OPEN UNIT (v2 bridge) OK" : "NOT the open unit (wiring, or another bitstream)");
  return id == UNIT_ID_V2; }
static void set_mode(uint32_t m) { wr_reg(16, m); delay(50); Serial.printf("mode set to %lu\n", (unsigned long)m); }
static void cmd_pins() {
  uint32_t s = rd_reg(10); uint32_t lv = s >> 16; uint32_t in = rd_reg(26), out = rd_reg(27);
  Serial.printf("registers: inputs (26) 0x%03lX, outputs (27) 0x%04lX  (0 = the normal shield wiring)\n", (unsigned long)in, (unsigned long)out);
  Serial.print("pin levels:"); for (int i = 0; i < 16; i++) Serial.printf(" %d=%d", POOLPIN[i], (int)((lv >> i) & 1)); Serial.println(); }
static void cmd_btn(int which, int tang) {
  int idx = pool_index(tang); if (which < 1 || which > 3 || idx < 0) { Serial.println("btn 1|2|3 TANGPIN (a pool pin)"); return; }
  uint32_t r = rd_reg(26); int def = which - 1, sh = 4 * (which - 1); r = (r & ~(0xFUL << sh)) | ((uint32_t)(idx ^ def) << sh); wr_reg(26, r);
  Serial.printf("button %d now read from Tang pin %d\n", which, tang); }
static void cmd_out(const String& name, int tang) {
  int idx = pool_index(tang), k = name == "latch" ? 0 : name == "clk" ? 1 : name == "data" ? 2 : name == "buzz" ? 3 : -1;
  if (k < 0 || idx < 0) { Serial.println("out latch|clk|data|buzz TANGPIN (a pool pin)"); return; }
  uint32_t r = rd_reg(27); int def = k + 3, sh = 4 * k; r = (r & ~(0xFUL << sh)) | ((uint32_t)(idx ^ def) << sh); wr_reg(27, r);
  Serial.printf("%s now driven on Tang pin %d (only wire that pin to the shield input!)\n", name.c_str(), tang); }
void setup() {
  Serial.begin(115200); pinMode(PIN_CS, OUTPUT); digitalWrite(PIN_CS, HIGH); pinMode(PIN_READY, INPUT); SPI.begin(PIN_SCLK, PIN_MISO, PIN_MOSI, -1); delay(300);
  Serial.println("\nHex-N open unit, stage 3. Type: id | mode 0..3 | pins | btn N PIN | out NAME PIN | default | all"); }
void loop() {
  static String line;
  while (Serial.available()) { char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (line == "id") cmd_id(); else if (line == "pins") cmd_pins(); else if (line == "default") { wr_reg(26, 0); wr_reg(27, 0); Serial.println("normal shield wiring restored"); }
      else if (line == "all") { if (cmd_id()) { cmd_pins(); } }
      else if (line.startsWith("mode ")) set_mode((uint32_t)line.substring(5).toInt());
      else if (line.startsWith("btn ")) { int a = 0, b = 0; sscanf(line.c_str(), "btn %d %d", &a, &b); cmd_btn(a, b); }
      else if (line.startsWith("out ")) { char nm[16] = {0}; int b = 0; sscanf(line.c_str(), "out %15s %d", nm, &b); cmd_out(String(nm), b); }
      line = ""; } else line += c; }
}
