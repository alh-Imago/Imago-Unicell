// hexn_gateway.ino -- Hex-N open unit GATEWAY (1 Nov 2026). One general ESP32 sketch that lets the PC drive the whole open unit (any build v1..v5): it only MOVES words, all intelligence is on the PC (tools/hexn_open_host_v1.py).
// Serial 460800 baud, one text command per line (numbers in hex), one reply line: OK ... or ERR ... . Every command and every OK reply may end with ' #HHHH' = the 16-bit sum of the bytes before it; a command whose sum is wrong is refused with 'ERR checksum' (the PC resends).
// (Version 2, 1 Nov 2026: the first version used 921600 baud, a 256-byte receive buffer and one-character reads; long lines were cut or damaged on the first real run. Now an 8 KB receive buffer, bulk reads, a checksum, 460800 baud.)
//   ID                      -> OK <unit id>                   (read register 0)
//   R reg                   -> OK <value>                     (read a register)
//   W reg value             -> OK                             (write a register)
//   WW addr w1 w2 ... wn    -> OK n                           (write n words into the scratch RAM from addr; n up to 255)
//   RW addr n               -> OK w1 w2 ... wn                (read n words from the scratch RAM; n up to 255)
//   SPD hz                  -> OK                             (SPI clock, decimal; the Tang bridge works to about 1.5 MHz)
// Wiring as docs/hex-n/LINK_TEST_v1.md (IO5 CS -> 73, IO18 SCLK -> 74, IO23 MOSI -> 75, IO19 MISO <- 76, IO34 READY <- 77, GND). Needs the v2 bridge (open unit builds), not the 63-word-limited v1.
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

static char buf[4096]; static int blen = 0; static uint32_t wbuf[256];
static void reply(const char* text) { unsigned sum = 0; for (const char* p = text; *p; p++) sum += (uint8_t)*p; Serial.print(text); Serial.printf(" #%04X\n", sum & 0xFFFF); }   // OK replies carry their checksum
static void reply_err(const char* why) { Serial.print("ERR "); Serial.println(why); }
static char rbuf[256 * 9 + 16];
static void handle(char* line) {
  char* h = strrchr(line, '#');
  if (h && h > line && h[-1] == ' ') { unsigned want = strtoul(h + 1, NULL, 16), sum = 0; for (char* p = line; p < h - 1; p++) sum += (uint8_t)*p; if ((sum & 0xFFFF) != want) return reply_err("checksum"); h[-1] = 0; }
  char* tok = strtok(line, " \t"); if (!tok) return;
  if (!strcmp(tok, "ID")) { snprintf(rbuf, sizeof(rbuf), "OK %08lX", (unsigned long)rd_reg(0)); reply(rbuf); }
  else if (!strcmp(tok, "R")) { char* a = strtok(NULL, " \t"); if (!a) return reply_err("R needs a register"); snprintf(rbuf, sizeof(rbuf), "OK %08lX", (unsigned long)rd_reg((uint8_t)strtoul(a, NULL, 16))); reply(rbuf); }
  else if (!strcmp(tok, "W")) { char* a = strtok(NULL, " \t"); char* v = strtok(NULL, " \t"); if (!a || !v) return reply_err("W needs register and value"); wr_reg((uint8_t)strtoul(a, NULL, 16), (uint32_t)strtoul(v, NULL, 16)); reply("OK"); }
  else if (!strcmp(tok, "WW")) { char* a = strtok(NULL, " \t"); if (!a) return reply_err("WW needs an address"); uint16_t addr = (uint16_t)strtoul(a, NULL, 16); int n = 0; char* w;
    while ((w = strtok(NULL, " \t")) != NULL) { if (n >= 255) return reply_err("more than 255 words"); wbuf[n++] = (uint32_t)strtoul(w, NULL, 16); }
    if (n == 0) return reply_err("no words"); wr_words(addr, wbuf, n); snprintf(rbuf, sizeof(rbuf), "OK %d", n); reply(rbuf); }
  else if (!strcmp(tok, "RW")) { char* a = strtok(NULL, " \t"); char* c = strtok(NULL, " \t"); if (!a || !c) return reply_err("RW needs address and count");
    int n = (int)strtoul(c, NULL, 16); if (n < 1 || n > 255) return reply_err("count 1..255"); rd_words((uint16_t)strtoul(a, NULL, 16), wbuf, n);
    int k = snprintf(rbuf, sizeof(rbuf), "OK"); for (int i = 0; i < n; i++) k += snprintf(rbuf + k, sizeof(rbuf) - k, " %08lX", (unsigned long)wbuf[i]); reply(rbuf); }
  else if (!strcmp(tok, "SPD")) { char* hz = strtok(NULL, " \t"); if (!hz) return reply_err("SPD needs hz"); cfg = SPISettings((uint32_t)strtoul(hz, NULL, 10), MSBFIRST, SPI_MODE0); reply("OK"); }
  else reply_err("unknown command");
}
void setup() {
  Serial.setRxBufferSize(8192);                  // must come before begin(); the default 256 bytes overflowed on 100-word lines
  Serial.begin(460800); pinMode(PIN_CS, OUTPUT); digitalWrite(PIN_CS, HIGH); pinMode(PIN_READY, INPUT); SPI.begin(PIN_SCLK, PIN_MISO, PIN_MOSI, -1); delay(300);
  Serial.println("OK hexn gateway ready"); }
void loop() {
  int n = Serial.available();
  if (n <= 0) return;
  if (n > (int)sizeof(buf) - 1 - blen) n = (int)sizeof(buf) - 1 - blen;
  if (n <= 0) { blen = 0; reply_err("line too long"); return; }
  n = Serial.readBytes(buf + blen, n);            // one bulk read, not one character at a time
  int start = 0;
  for (int i = blen; i < blen + n; i++) if (buf[i] == '\n' || buf[i] == '\r') { buf[i] = 0; if (i > start) handle(buf + start); start = i + 1; }
  int rest = blen + n - start; if (rest > 0 && start > 0) memmove(buf, buf + start, rest); blen = rest > 0 ? rest : 0;
}
