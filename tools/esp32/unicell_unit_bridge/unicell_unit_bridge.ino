// unicell_unit_bridge.ino -- ESP32 (SPI master) <-> Tang Nano 20K small unit (ledger #1036).
// Talks to the FPGA unit over SPI (mode 0, 1 MHz), from the Arduino Serial Monitor (115200 baud, line ending "Newline").
// Wiring (ESP32 pin -> Tang Nano package pin): IO5 CS_N -> 73, IO18 SCLK -> 74, IO23 MOSI -> 75, IO19 MISO <- 76, IO34 READY <- 77, GND-GND.
// Built for the CORDIC example unit (1 input lane, 1 result lane, one item at a time -> pacing registers MAX_OUT=1, RPI=1).
#include <Arduino.h>
#include <SPI.h>

#define PIN_CS    5
#define PIN_SCLK  18
#define PIN_MOSI  23
#define PIN_MISO  19
#define PIN_READY 34          // input-only pin: high = SD card up and no error
#define SPI_HZ    1000000     // keep <= 1 MHz on a breadboard (the FPGA needs SCLK < 27 MHz / 16)

enum { R_ID = 0, R_STATUS = 1, R_CONTROL = 2, R_START_BLOCK = 3, R_NBLOCKS = 4, R_PLAY_COUNT = 5,
       R_CAP_COUNT = 6, R_SCRATCH = 7, R_MAX_OUT = 8, R_RPI = 9 };
enum { C_LOAD = 1, C_SAVE = 2, C_PLAY = 4, C_CAP_CLEAR = 8, C_CLEAR_DONE = 16 };
enum { S_SD_READY = 1, S_SD_ERROR = 2, S_SD_BUSY = 4, S_PLAY_BUSY = 8, S_SD_DONE = 16, S_PLAY_DONE = 32, S_CAP_NONEMPTY = 64 };
static const uint32_t UNIT_ID = 0x57320001UL;

// reference results from the repo's simulator for the six test angles (z0 = 50000 -> -404 is the anchor)
static const int32_t ANGLES[6] = { 50000, -50000, 0, 12345, -12345, 90000 };
static const int32_t EXPECT[6] = { -404, 404, -2726, 821, -821, -2726 };

static SPISettings spi_cfg(SPI_HZ, MSBFIRST, SPI_MODE0);

static void cs_low()  { digitalWrite(PIN_CS, LOW);  delayMicroseconds(3); }
static void cs_high() { delayMicroseconds(3); digitalWrite(PIN_CS, HIGH); delayMicroseconds(5); }

static void wr_reg(uint8_t a, uint32_t d) {
  uint8_t t[6] = { 0x01, a, (uint8_t)(d >> 24), (uint8_t)(d >> 16), (uint8_t)(d >> 8), (uint8_t)d };
  SPI.beginTransaction(spi_cfg); cs_low(); SPI.transfer(t, 6); cs_high(); SPI.endTransaction();
}
static uint32_t rd_reg(uint8_t a) {
  uint8_t t[7] = { 0x02, a, 0, 0, 0, 0, 0 };
  SPI.beginTransaction(spi_cfg); cs_low(); SPI.transfer(t, 7); cs_high(); SPI.endTransaction();
  return ((uint32_t)t[3] << 24) | ((uint32_t)t[4] << 16) | ((uint32_t)t[5] << 8) | t[6];
}
// words go into the PLAYOUT RAM starting at word address `addr` (auto-increment)
static void wr_words(uint16_t addr, const int32_t* w, int n) {
  while (n > 0) {
    int k = n > 64 ? 64 : n;
    uint8_t t[3 + 64 * 4]; t[0] = 0x03; t[1] = addr >> 8; t[2] = addr & 255;
    for (int i = 0; i < k; i++) { uint32_t v = (uint32_t)w[i]; t[3 + 4*i] = v >> 24; t[4 + 4*i] = v >> 16; t[5 + 4*i] = v >> 8; t[6 + 4*i] = v; }
    SPI.beginTransaction(spi_cfg); cs_low(); SPI.transfer(t, 3 + 4 * k); cs_high(); SPI.endTransaction();
    w += k; n -= k; addr += k;
  }
}
// words come out of the CAPTURE RAM starting at word address `addr`
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
static void print_status() {
  uint32_t s = rd_reg(R_STATUS);
  Serial.printf("STATUS 0x%04X: sd_ready=%u sd_error=%u sd_busy=%u play_busy=%u sd_done=%u play_done=%u cap_nonempty=%u err_code=%u | READY pin=%d | CAP_COUNT=%u\n",
    (unsigned)s, (unsigned)(s & 1), (unsigned)((s >> 1) & 1), (unsigned)((s >> 2) & 1), (unsigned)((s >> 3) & 1), (unsigned)((s >> 4) & 1),
    (unsigned)((s >> 5) & 1), (unsigned)((s >> 6) & 1), (unsigned)((s >> 8) & 31), digitalRead(PIN_READY), (unsigned)rd_reg(R_CAP_COUNT));
}

// feed n angles through the design one at a time (pacing), straight from the ESP32 (no SD card involved)
static bool run_angles(const int32_t* z, int n, int32_t* out) {
  wr_reg(R_CONTROL, C_CAP_CLEAR);
  wr_reg(R_MAX_OUT, 1); wr_reg(R_RPI, 1);
  wr_words(0, z, n);
  wr_reg(R_PLAY_COUNT, n);
  wr_reg(R_CONTROL, C_PLAY);
  uint32_t t0 = millis();
  while (rd_reg(R_CAP_COUNT) < (uint32_t)n) { if (millis() - t0 > 3000) { Serial.println("TIMEOUT waiting for results"); return false; } }
  rd_words(0, out, n);
  return true;
}

static void cmd_id()      { uint32_t v = rd_reg(R_ID); Serial.printf("ID = 0x%08X  %s\n", (unsigned)v, v == UNIT_ID ? "OK (unit answers)" : "WRONG - check wiring / bitstream"); }
static void cmd_scratch() {
  const uint32_t pat[3] = { 0xA5A55A5AUL, 0x12345678UL, 0xFFFFFFFFUL }; bool ok = true;
  for (int i = 0; i < 3; i++) { wr_reg(R_SCRATCH, pat[i]); uint32_t r = rd_reg(R_SCRATCH); if (r != pat[i]) { ok = false; Serial.printf("  wrote 0x%08X read 0x%08X\n", (unsigned)pat[i], (unsigned)r); } }
  Serial.println(ok ? "SCRATCH read-back OK (SPI link is good)" : "SCRATCH MISMATCH - SPI link problem (wiring, GND, speed)");
}
static void cmd_cordic() {
  int32_t out[6]; if (!run_angles(ANGLES, 6, out)) return; bool ok = true;
  for (int i = 0; i < 6; i++) { bool m = out[i] == EXPECT[i]; ok &= m; Serial.printf("  z0=%7ld -> %6ld  (expect %6ld) %s\n", (long)ANGLES[i], (long)out[i], (long)EXPECT[i], m ? "ok" : "WRONG"); }
  Serial.println(ok ? "CORDIC OK: all six match the simulator" : "CORDIC MISMATCH");
}
static void cmd_z(char* args) {
  int32_t z[32], out[32]; int n = 0;
  for (char* p = strtok(args, " "); p && n < 32; p = strtok(NULL, " ")) z[n++] = (int32_t)strtol(p, NULL, 0);
  if (!n) { Serial.println("usage: z <angle> [angle ...]"); return; }
  if (run_angles(z, n, out)) for (int i = 0; i < n; i++) Serial.printf("  z0=%ld -> %ld\n", (long)z[i], (long)out[i]);
}
static bool sd_op(uint32_t ctl, uint32_t block, uint32_t nblocks) {
  wr_reg(R_CONTROL, C_CLEAR_DONE); wr_reg(R_START_BLOCK, block); wr_reg(R_NBLOCKS, nblocks); wr_reg(R_CONTROL, ctl);
  bool done = wait_status(S_SD_DONE, 5000); uint32_t s = rd_reg(R_STATUS);
  if (!done || (s & S_SD_ERROR)) { Serial.printf("SD operation failed (STATUS 0x%04X, err_code %u)\n", (unsigned)s, (unsigned)((s >> 8) & 31)); return false; }
  return true;
}
// card round trip: angles -> results R1 -> saved to the card -> loaded back as inputs -> results R2; R2 must equal the direct run of R1
static void cmd_sdtest(uint32_t block) {
  if (!(rd_reg(R_STATUS) & S_SD_READY)) { Serial.println("SD card not ready (insert the card, then power-cycle the FPGA)"); return; }
  int32_t r1[6], direct[6], viacard[6];
  if (!run_angles(ANGLES, 6, r1)) return;
  Serial.printf("saving 6 results to card block %lu ...\n", (unsigned long)block);
  if (!sd_op(C_SAVE, block, 1)) return;
  if (!run_angles(r1, 6, direct)) return;                       // reference: R1 fed in over SPI
  Serial.printf("loading block %lu back as the next inputs ...\n", (unsigned long)block);
  if (!sd_op(C_LOAD, block, 1)) return;                         // card -> playout RAM
  wr_reg(R_CONTROL, C_CAP_CLEAR); wr_reg(R_MAX_OUT, 1); wr_reg(R_RPI, 1); wr_reg(R_PLAY_COUNT, 6); wr_reg(R_CONTROL, C_PLAY);
  uint32_t t0 = millis(); while (rd_reg(R_CAP_COUNT) < 6) { if (millis() - t0 > 3000) { Serial.println("TIMEOUT"); return; } }
  rd_words(0, viacard, 6); bool ok = true;
  for (int i = 0; i < 6; i++) { bool m = viacard[i] == direct[i]; ok &= m; Serial.printf("  %6ld -> via SPI %6ld | via card %6ld %s\n", (long)r1[i], (long)direct[i], (long)viacard[i], m ? "ok" : "WRONG"); }
  Serial.println(ok ? "SD ROUND TRIP OK" : "SD ROUND TRIP MISMATCH");
}
// wire test: drive CS and SCLK by hand, slowly, so the FPGA's LEDs show whether each wire arrives (LED1 = CS seen, LED2 = SCLK seen)
static void cmd_wires() {
  SPI.end();
  pinMode(PIN_SCLK, OUTPUT); digitalWrite(PIN_SCLK, LOW); pinMode(PIN_MOSI, OUTPUT); digitalWrite(PIN_MOSI, LOW);
  Serial.println("CS (IO5) goes LOW for 4 s now: Tang LED1 should light and stay lit.");
  digitalWrite(PIN_CS, LOW); delay(4000); digitalWrite(PIN_CS, HIGH);
  Serial.println("SCLK (IO18) goes HIGH for 4 s now: Tang LED2 should light and stay lit.");
  digitalWrite(PIN_SCLK, HIGH); delay(4000); digitalWrite(PIN_SCLK, LOW);
  Serial.printf("MISO (IO19) reads %d, READY (IO34) reads %d (idle expected: MISO 0 or 1 steady, READY 0 until the SD card is up).\n", digitalRead(PIN_MISO), digitalRead(PIN_READY));
  SPI.begin(PIN_SCLK, PIN_MISO, PIN_MOSI, -1);
  Serial.println("done. LED1/LED2 stay lit until the FPGA is reloaded or its reset button is pressed.");
}
// MISO test: is the MISO wire connected to something that DRIVES it? A floating pin follows the ESP32's own pull resistors; a pin driven by the FPGA reads the same either way.
static void cmd_miso() {
  SPI.end();
  pinMode(PIN_MISO, INPUT_PULLDOWN); delay(20); int a = digitalRead(PIN_MISO);
  pinMode(PIN_MISO, INPUT_PULLUP);   delay(20); int b = digitalRead(PIN_MISO);
  Serial.printf("MISO (IO19) with pull-DOWN reads %d, with pull-UP reads %d\n", a, b);
  if (a != b) Serial.println("=> FLOATING: nothing is driving the MISO wire. Check it goes from ESP32 IO19 to Tang pin 76 (top header, third pin from the USB end) and that the FPGA is loaded.");
  else Serial.printf("=> DRIVEN steadily at %d: the FPGA (or something) is holding the line, so the MISO wire is connected.\n", a);
  SPI.begin(PIN_SCLK, PIN_MISO, PIN_MOSI, -1);
}
static void cmd_help() {
  Serial.println("commands:  id | status | scratch | cordic | z <a> [a ...] | sdtest [block=64] | load <block> <n> | save <block> <n> |");
  Serial.println("           reg <n> [value] | words <addr> <n>  (dump capture RAM) | wires | miso | help");
  Serial.println("first time: id, then scratch, then cordic (no SD needed), then status, then sdtest.  Blocks are RAW: never use block 0.");
}

static String line;
static void handle(char* s) {
  char* cmd = strtok(s, " "); if (!cmd) return; char* rest = strtok(NULL, "");
  if (!strcmp(cmd, "id")) cmd_id();
  else if (!strcmp(cmd, "status")) print_status();
  else if (!strcmp(cmd, "scratch")) cmd_scratch();
  else if (!strcmp(cmd, "cordic")) cmd_cordic();
  else if (!strcmp(cmd, "wires")) cmd_wires();
  else if (!strcmp(cmd, "miso")) cmd_miso();
  else if (!strcmp(cmd, "z")) { if (rest) cmd_z(rest); else Serial.println("usage: z <angle> [angle ...]"); }
  else if (!strcmp(cmd, "sdtest")) cmd_sdtest(rest ? strtoul(rest, NULL, 0) : 64);
  else if (!strcmp(cmd, "load") || !strcmp(cmd, "save")) {
    unsigned long b = 0, n = 1; if (rest) sscanf(rest, "%lu %lu", &b, &n);
    if (b < 16) { Serial.println("refusing blocks below 16 (block 0 holds a FAT32 card's partition table)"); return; }
    if (sd_op(cmd[0] == 'l' ? C_LOAD : C_SAVE, b, n)) Serial.printf("%s block %lu x%lu done\n", cmd, b, n);
  }
  else if (!strcmp(cmd, "reg")) {
    unsigned a = 0; unsigned long v = 0; int c = rest ? sscanf(rest, "%u %li", &a, (long*)&v) : 0;
    if (c == 2) { wr_reg(a, v); Serial.printf("reg %u <- 0x%08lX\n", a, v); } else if (c == 1) Serial.printf("reg %u = 0x%08X\n", a, (unsigned)rd_reg(a)); else Serial.println("usage: reg <n> [value]");
  }
  else if (!strcmp(cmd, "words")) {
    unsigned a = 0, n = 8; if (rest) sscanf(rest, "%u %u", &a, &n); if (n > 64) n = 64;
    int32_t w[64]; rd_words(a, w, n); for (unsigned i = 0; i < n; i++) Serial.printf("  [%u] = %ld (0x%08lX)\n", a + i, (long)w[i], (unsigned long)(uint32_t)w[i]);
  }
  else cmd_help();
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_CS, OUTPUT); digitalWrite(PIN_CS, HIGH);
  pinMode(PIN_READY, INPUT);
  SPI.begin(PIN_SCLK, PIN_MISO, PIN_MOSI, -1);   // CS is driven by hand above
  delay(300);
  Serial.println("\nUniCell unit bridge ready. Type 'help'.");
  cmd_id();
}
void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') { if (line.length()) { char buf[128]; line.toCharArray(buf, sizeof buf); line = ""; handle(buf); } }
    else if (line.length() < 120) line += c;
  }
}
