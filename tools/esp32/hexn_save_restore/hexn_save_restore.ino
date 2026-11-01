// hexn_save_restore.ino -- Hex-N open unit, SAVE and RESTORE of the tables and the judge weights over the ESP32 SPI link.
// Bitstream: fpga/build/hexn_open_unit_v8/unit_top.fs (stage 5b). Serial Monitor 115200, line ending Newline. Wiring as hexn_open3_test.
// NOT YET RUN ON A BOARD (written 1 Nov 2026 against the simulated test benches tests/hexn_open7 and tests/hexn_open8; the SPI calls are copied from hexn_open3_test).
// Commands:
//   id | status
//   tabsave <space> [count]   copy table space 1..5 (1 rt, 2 mt, 3 decode, 4 glyph, 5 presets) from the card into scratch RAM, read it, store in flash as /tab<space>.bin.
//                             count may be left out for spaces 3,4,5 (256, 64, 64 words); give it for spaces 1 and 2 (the length of the table you loaded).
//   tabload <space>           read /tab<space>.bin from flash, write it into scratch RAM, copy it into the card's table (cfg17 / cfg19, the existing load path).
//   jsave <A|B>               dump the judge (260-word guarded record: header with array size, 256 entries, bias, checksum) and store it as /judge<A|B>.bin.
//   jload <A|B> [A|B]         restore /judge<first>.bin into the judge named by the optional second letter (default the same). The unit checks the whole record
//                             first; a refused record is reported and the judge is not touched. Status 0 ok, 1 bad magic, 2 wrong array size, 3 bad checksum, 4 order wrong or truncated.
//   tabcheck <space> [count]  read the table space from the card now and compare it word for word with /tab<space>.bin (use after tabload).
//   tabclear <space> [count]  write zeros into the card's table space (load path), so tabcheck should then DIFFER from the flash copy; tabload puts it back and tabcheck matches again.
//   jcompare <A|B> <A|B>      dump both judges now and compare geometry, entries and bias (not the judge number or checksum) word for word.
//   jsnap                     score 16 fixed test rows through BOTH judges and store the 32 result words in flash (/score.bin).
//   jscorecheck               score the same rows again and compare with /score.bin: after a restore the answers must be identical.
//   tabfill <space> [count]   load a known pattern (word i = 37*i + 11, cut to the table's width) into the card's table space, so the table tests have something real to carry.
//   jfill <A|B>               put a known test table (192 weights and a bias, different for A and B) into the judge, so jtest has something to save.
//   jcheck <A|B>              dump the judge now and compare it word for word with the file /judge<A|B>.bin in flash (use after jload, or after a power cycle).
//   jbreak <A|B> <c|m|g|o>   make a DAMAGED copy of the stored record as /judgeZ.bin (the real file is not touched): c = one weight bit flipped (checksum now wrong), m = wrong magic, g = wrong array size, o = two body words swapped (checksum made right in both, so only that fault is present).
//                             then `jclear` and `jload Z A`: the unit should refuse (status 3, 1 or 2) and `jcheck` / a dump should show judge A still empty.
//   jclear                    clear both judges (tables and bias)
//   jtest                     self test: dump A, clear, restore from the dump, dump again, compare word for word (needs a judge with weights loaded first).
//   pintest                   wiggle CS, MOSI and SCLK by hand (no SPI): on the Tang idle LEDs 1 (CS), 4 (MOSI) and 2 (clock) must light and STAY lit (they latch until the bitstream is reloaded). Works even when the unit is not answering.
//   ls                        list the stored files.
#include <Arduino.h>
#include <SPI.h>
#include <LittleFS.h>
#define PIN_CS 5
#define PIN_SCLK 18
#define PIN_MOSI 23
#define PIN_MISO 19
#define PIN_READY 34
static const uint32_t UNIT_ID_V2 = 0x57320002UL;
static const int REC_N = 260;                                             // judge record length in words
static const uint32_t DUMP_A = 0xF0000000UL, DUMP_B = 0xF0000002UL, REST_A = 0xF0000008UL, REST_B = 0xF000000AUL, CLEAR_BOTH = (14UL << 28) | 0xCUL;
static SPISettings cfg(1000000, MSBFIRST, SPI_MODE0);
static void cs_low()  { digitalWrite(PIN_CS, LOW);  delayMicroseconds(3); }
static void cs_high() { delayMicroseconds(3); digitalWrite(PIN_CS, HIGH); delayMicroseconds(5); }
static void wr_reg(uint8_t a, uint32_t d) { uint8_t t[6] = { 0x01, a, (uint8_t)(d >> 24), (uint8_t)(d >> 16), (uint8_t)(d >> 8), (uint8_t)d }; SPI.beginTransaction(cfg); cs_low(); SPI.transfer(t, 6); cs_high(); SPI.endTransaction(); }
static uint32_t rd_reg(uint8_t a) { uint8_t t[7] = { 0x02, a, 0, 0, 0, 0, 0 }; SPI.beginTransaction(cfg); cs_low(); SPI.transfer(t, 7); cs_high(); SPI.endTransaction(); return ((uint32_t)t[3] << 24) | ((uint32_t)t[4] << 16) | ((uint32_t)t[5] << 8) | t[6]; }
static uint8_t txb[4 + 4 * 128 + 8];
static void wr_words(uint16_t addr, const uint32_t* w, int n) {          // any n: sent in pieces of up to 128 words
  for (int off = 0; off < n; off += 128) { int c = min(128, n - off); uint16_t a = addr + off;
    txb[0] = 0x03; txb[1] = a >> 8; txb[2] = a & 255;
    for (int i = 0; i < c; i++) { uint32_t v = w[off + i]; txb[3+4*i] = v >> 24; txb[4+4*i] = v >> 16; txb[5+4*i] = v >> 8; txb[6+4*i] = v; }
    SPI.beginTransaction(cfg); cs_low(); SPI.transfer(txb, 3 + 4 * c); cs_high(); SPI.endTransaction(); } }
static void rd_words(uint16_t addr, uint32_t* w, int n) {
  for (int off = 0; off < n; off += 128) { int c = min(128, n - off); uint16_t a = addr + off;
    txb[0] = 0x04; txb[1] = a >> 8; txb[2] = a & 255; for (int i = 3; i < 4 + 4 * c; i++) txb[i] = 0;
    SPI.beginTransaction(cfg); cs_low(); SPI.transfer(txb, 4 + 4 * c); cs_high(); SPI.endTransaction();
    for (int i = 0; i < c; i++) w[off + i] = ((uint32_t)txb[4+4*i] << 24) | ((uint32_t)txb[5+4*i] << 16) | ((uint32_t)txb[6+4*i] << 8) | txb[7+4*i]; } }
static uint32_t seq = 5000;
static bool wait_idle() {                                                 // status bit 4 = table copy busy, bit 6 = raw engine busy
  for (int i = 0; i < 4000; i++) { uint32_t s = rd_reg(10); if (!((s >> 4) & 1) && !((s >> 6) & 1)) return true; }
  Serial.println("unit still busy"); return false; }
static bool cmd_id() { uint32_t id = rd_reg(0); Serial.printf("ID 0x%08lX -> %s\n", (unsigned long)id, id == UNIT_ID_V2 ? "OPEN UNIT OK" : "NOT the open unit"); return id == UNIT_ID_V2; }
static uint32_t buf[REC_N + 8], buf2[REC_N + 8];
static int space_default(int sp) { return sp == 3 ? 256 : (sp == 4 || sp == 5) ? 64 : 0; }
static bool put_file(const char* name, const uint32_t* w, int n) { File f = LittleFS.open(name, "w"); if (!f) return false; size_t k = f.write((const uint8_t*)w, 4 * n); f.close(); return k == (size_t)(4 * n); }
static int get_file(const char* name, uint32_t* w, int maxn) { File f = LittleFS.open(name, "r"); if (!f) return -1; int n = f.read((uint8_t*)w, 4 * maxn) / 4; f.close(); return n; }
static bool tabread(int sp, int count, uint32_t* out) {                   // copy a table space into scratch RAM (cfg30/31) and read it
  uint16_t base = (count > 124) ? 0 : 900;                               // scratch RAM has 1024 words; a short table goes to 900, a long one to 0
  wr_reg(30, ((uint32_t)sp << 28) | ((uint32_t)base << 16) | (uint32_t)count);
  wr_reg(31, ++seq); delay(2);
  if (!wait_idle()) return false;
  rd_words(base, out, count); return true; }
static bool tab_args(int sp, int& count) {
  if (sp < 1 || sp > 5) { Serial.println("space must be 1..5"); return false; }
  if (count <= 0) count = space_default(sp);
  if (count <= 0) { Serial.println("give the word count for space 1 or 2"); return false; }
  if (count > 1000) { Serial.println("count too large for the scratch RAM"); return false; }
  return true; }
static void cmd_tabsave(int sp, int count) {
  if (!tab_args(sp, count) || !tabread(sp, count, buf)) return;
  char nm[24]; snprintf(nm, sizeof nm, "/tab%d.bin", sp);
  Serial.printf("space %d: %d words read; stored %s -> %s\n", sp, count, nm, put_file(nm, buf, count) ? "ok" : "FAILED"); }
static void cmd_tabcheck(int sp, int count) {
  if (!tab_args(sp, count)) return;
  char nm[24]; snprintf(nm, sizeof nm, "/tab%d.bin", sp); int n = get_file(nm, buf, 1000);
  if (n != count) { Serial.printf("%s: %d words, asked for %d\n", nm, n, count); return; }
  if (!tabread(sp, count, buf2)) return; int bad = 0, nz = 0; for (int i = 0; i < count; i++) { if (buf[i] != buf2[i]) bad++; if (buf2[i]) nz++; }
  Serial.printf("space %d now: %d non-zero words; %d of %d differ from %s (want 0)\n", sp, nz, bad, count, nm); Serial.println(bad == 0 ? (nz == 0 ? "MATCHES THE FLASH COPY, BUT BOTH ARE ALL ZERO: this proves nothing" : "MATCHES THE FLASH COPY") : "DIFFERS FROM THE FLASH COPY"); }
static void cmd_tabload(int sp) {
  if (sp < 1 || sp > 5) { Serial.println("space must be 1..5"); return; }
  char nm[24]; snprintf(nm, sizeof nm, "/tab%d.bin", sp); int n = get_file(nm, buf, 1000);
  if (n <= 0) { Serial.printf("no file %s\n", nm); return; }
  wr_words(0, buf, n);
  wr_reg(17, ((uint32_t)sp << 28) | (0UL << 16) | (uint32_t)n); wr_reg(19, ++seq); delay(2);   // the existing load path: space, scratch base 0, count
  if (wait_idle()) Serial.printf("space %d: %d words loaded from flash into the card's table\n", sp, n); }
static bool run_stream(const uint32_t* w, int n, int out_base) {          // words -> scratch 0.., unit runs them as a stream (mode 3), results at out_base
  wr_reg(16, 3); delay(20); wr_words(0, w, n);
  wr_reg(24, ((uint32_t)out_base << 16) | (uint32_t)n); wr_reg(25, ++seq); delay(2); return wait_idle(); }
static bool jdump(char j, uint32_t* out) { uint32_t w[1] = { j == 'B' ? DUMP_B : DUMP_A }; if (!run_stream(w, 1, 300)) return false; rd_words(300, out, REC_N); return true; }
static int jrestore(char into, const uint32_t* rec) {                      // returns the status word (0 ok) or -1 on a link problem
  static uint32_t w[REC_N + 2]; w[0] = (into == 'B') ? REST_B : REST_A; for (int i = 0; i < REC_N; i++) w[1 + i] = rec[i];
  if (!run_stream(w, REC_N + 1, 300)) return -1; uint32_t st; rd_words(300, &st, 1); return (int)st; }
static void cmd_jsave(char j) {
  if (!jdump(j, buf)) return; char nm[24]; snprintf(nm, sizeof nm, "/judge%c.bin", j);
  Serial.printf("judge %c: record of %d words (header %08lX %08lX, checksum %08lX); stored %s -> %s\n", j, REC_N, (unsigned long)buf[0], (unsigned long)buf[1], (unsigned long)buf[REC_N - 1], nm, put_file(nm, buf, REC_N) ? "ok" : "FAILED"); }
static void cmd_jload(char from, char into) {
  char nm[24]; snprintf(nm, sizeof nm, "/judge%c.bin", from); int n = get_file(nm, buf, REC_N + 4);
  if (n != REC_N) { Serial.printf("%s: %d words, want %d\n", nm, n, REC_N); return; }
  int st = jrestore(into, buf); const char* why[] = { "ok", "bad magic", "wrong array size", "bad checksum", "order wrong or truncated" };
  Serial.printf("restore %c -> judge %c: status %d (%s)\n", from, into, st, (st >= 0 && st <= 4) ? why[st] : "link problem"); }
static void cmd_jtest() {
  if (!jdump('A', buf)) return; int nz = 0; for (int i = 2; i < REC_N - 1; i++) if (buf[i] & 0xFF) nz++;
  Serial.printf("dump 1 taken (%d entries non-zero)\n", nz);
  uint32_t c[1] = { CLEAR_BOTH }; run_stream(c, 1, 300);
  if (!jdump('A', buf2)) return; int nz2 = 0; for (int i = 2; i < REC_N - 1; i++) if (buf2[i] & 0xFF) nz2++;
  Serial.printf("after clear: %d entries non-zero (want 0)\n", nz2);
  int st = jrestore('A', buf); Serial.printf("restore status %d (want 0)\n", st);
  if (!jdump('A', buf2)) return; int bad = 0; for (int i = 0; i < REC_N; i++) if (buf[i] != buf2[i]) bad++;
  Serial.printf("dump 2 vs dump 1: %d words differ (want 0)\n", bad);
  Serial.println((bad == 0 && st == 0 && nz2 == 0 && nz > 0) ? "JUDGE SAVE/RESTORE OK" : "JUDGE SAVE/RESTORE FAILED (if dump 1 shows 0 non-zero, load a table into judge A first)"); }
static void cmd_jfill(char j) {                                           // class 0/1 x 8 sensors x bins 0..11 = 192 LOAD words, then the bias; CONTROL word first picks the judge (0 = A, 2 = B)
  static uint32_t w[200]; int n = 0; int k = (j == 'B') ? 11 : 0;
  w[n++] = (14UL << 28) | ((j == 'B') ? 2UL : 0UL);
  for (int c = 0; c < 2; c++) for (int sn = 0; sn < 8; sn++) for (int b = 0; b < 12; b++) { int wt = ((sn * 7 + b * 3 + c * 5 + k) % 101) - 50; w[n++] = (12UL << 28) | ((uint32_t)c << 24) | ((uint32_t)((sn << 4) | b) << 16) | (uint32_t)(wt & 0xFF); }
  w[n++] = (13UL << 28) | (uint32_t)((j == 'B') ? 0xFFEF : 25); w[n++] = (14UL << 28) | 1UL;
  if (run_stream(w, n, 300)) Serial.printf("judge %c filled with the test table (%d words)\n", j, n); }
static void cmd_jcheck(char j) {
  char nm[24]; snprintf(nm, sizeof nm, "/judge%c.bin", j); int n = get_file(nm, buf, REC_N + 4);
  if (n != REC_N) { Serial.printf("%s: %d words, want %d\n", nm, n, REC_N); return; }
  if (!jdump(j, buf2)) return; int bad = 0, nz = 0; for (int i = 0; i < REC_N; i++) if (buf[i] != buf2[i]) bad++;
  for (int i = 2; i < REC_N - 1; i++) if (buf2[i] & 0xFF) nz++;
  Serial.printf("judge %c now has %d non-zero entries; %d of %d words differ from %s (want 0)\n", j, nz, bad, REC_N, nm); Serial.println(bad == 0 ? (nz == 0 ? "MATCHES THE FLASH COPY, BUT BOTH ARE ALL ZERO: this proves nothing" : "MATCHES THE FLASH COPY") : "DIFFERS FROM THE FLASH COPY"); }
static void cmd_jbreak(char j, char how) {
  char nm[24]; snprintf(nm, sizeof nm, "/judge%c.bin", j); int n = get_file(nm, buf, REC_N + 4);
  if (n != REC_N) { Serial.printf("%s: %d words, want %d\n", nm, n, REC_N); return; }
  if (how == 'c') buf[100] ^= 1UL;                                        // body word: one weight bit, checksum left as it was
  else if (how == 'm') { buf[0] ^= (1UL << 20); }                         // magic field (bits 31..12) changed
  else if (how == 'g') { buf[1] ^= (1UL << 24); }
  else if (how == 'o') { uint32_t t = buf[2]; buf[2] = buf[3]; buf[3] = t; }  // two body words swapped: class / address out of order, expect status 4                         // sensors field 8 -> 9
  else { Serial.println("use c, m, g or o"); return; }
  if (how != 'c') { uint32_t sum = 0; for (int i = 0; i < REC_N - 1; i++) sum += buf[i]; buf[REC_N - 1] = sum; }   // keep the checksum right so only one fault is present
  Serial.printf("damaged copy (%c) stored as /judgeZ.bin -> %s. Now: jclear, then jload Z A\n", how, put_file("/judgeZ.bin", buf, REC_N) ? "ok" : "FAILED"); }
static void cmd_tabclear(int sp, int count) {
  if (!tab_args(sp, count)) return;
  static uint32_t z[1000]; for (int i = 0; i < count; i++) z[i] = 0;
  wr_words(0, z, count); wr_reg(17, ((uint32_t)sp << 28) | (0UL << 16) | (uint32_t)count); wr_reg(19, ++seq); delay(2);
  if (wait_idle()) Serial.printf("space %d: %d zero words loaded into the card's table\n", sp, count); }
static void cmd_tabfill(int sp, int count) {
  if (!tab_args(sp, count)) return;
  static uint32_t f[1000]; uint32_t mask = (sp == 3) ? 0x3FUL : (sp == 4) ? 0xFFUL : 0xFFFFFFFFUL;
  for (int i = 0; i < count; i++) f[i] = ((uint32_t)(37 * i + 11)) & mask;
  wr_words(0, f, count); wr_reg(17, ((uint32_t)sp << 28) | (0UL << 16) | (uint32_t)count); wr_reg(19, ++seq); delay(2);
  if (wait_idle()) Serial.printf("space %d: pattern of %d words loaded into the card's table\n", sp, count); }
static void cmd_jcompare(char a, char b) {
  if (!jdump(a, buf) || !jdump(b, buf2)) return; int bad = 0, nz = 0; for (int i = 1; i < REC_N - 1; i++) { if (buf[i] != buf2[i]) bad++; if (buf[i] & 0xFF) nz++; }
  Serial.printf("judge %c vs judge %c: %d of %d words differ (geometry, entries, bias); %c has %d non-zero words\n", a, b, bad, REC_N - 2, a, nz); Serial.println(nz == 0 ? "BOTH EMPTY: this proves nothing" : bad == 0 ? "THE JUDGES MATCH" : "THE JUDGES DIFFER"); }
static const int NROWS = 16;
static bool score_run(uint32_t* res) {                                      // CONTROL word 1 = score both judges; results alternate A, B per row
  static uint32_t w[NROWS + 1]; w[0] = (14UL << 28) | 1UL;
  for (int r = 0; r < NROWS; r++) { uint32_t v = 0; for (int i = 0; i < 8; i++) v |= (uint32_t)((r * 5 + i * 3 + (r >> 2)) % 12) << (4 * i); w[1 + r] = v; }
  if (!run_stream(w, NROWS + 1, 300)) return false; rd_words(300, res, 2 * NROWS); return true; }
static void cmd_jsnap() {
  if (!score_run(buf)) return; int nz = 0; for (int i = 0; i < 2 * NROWS; i++) if (buf[i]) nz++;
  Serial.printf("scored %d rows through both judges: %d non-zero result words; first four %08lX %08lX %08lX %08lX; stored /score.bin -> %s\n", NROWS, nz, (unsigned long)buf[0], (unsigned long)buf[1], (unsigned long)buf[2], (unsigned long)buf[3], put_file("/score.bin", buf, 2 * NROWS) ? "ok" : "FAILED"); }
static void cmd_jscorecheck() {
  int n = get_file("/score.bin", buf, 2 * NROWS + 4); if (n != 2 * NROWS) { Serial.printf("/score.bin: %d words, want %d (run jsnap first)\n", n, 2 * NROWS); return; }
  if (!score_run(buf2)) return; int bad = 0, nz = 0; for (int i = 0; i < 2 * NROWS; i++) { if (buf[i] != buf2[i]) bad++; if (buf2[i]) nz++; }
  Serial.printf("scored again: %d non-zero result words; %d of %d differ from /score.bin (want 0)\n", nz, bad, 2 * NROWS); Serial.println(bad == 0 ? (nz == 0 ? "SAME, BUT ALL ZERO: this proves nothing (judges empty or the unit is not scoring)" : "SAME ANSWERS AS BEFORE") : "ANSWERS DIFFER FROM THE SNAPSHOT"); }
static void cmd_pintest() {
  SPI.end(); pinMode(PIN_SCLK, OUTPUT); pinMode(PIN_MOSI, OUTPUT); digitalWrite(PIN_SCLK, LOW); digitalWrite(PIN_MOSI, LOW);
  digitalWrite(PIN_CS, LOW); delay(100); digitalWrite(PIN_MOSI, HIGH); delay(100); digitalWrite(PIN_SCLK, HIGH); delay(100);
  digitalWrite(PIN_SCLK, LOW); digitalWrite(PIN_MOSI, LOW); digitalWrite(PIN_CS, HIGH); SPI.begin(PIN_SCLK, PIN_MISO, PIN_MOSI, -1);
  Serial.println("pintest done: CS (IO5) was pulled low, MOSI (IO23) high, SCLK (IO18) pulsed. Look at the Tang LEDs 1, 4 and 2 (they stay lit)."); }
static void cmd_ls() { File d = LittleFS.open("/"); File f = d.openNextFile(); while (f) { Serial.printf("%s  %u bytes\n", f.name(), (unsigned)f.size()); f = d.openNextFile(); } }
void setup() {
  Serial.begin(115200); pinMode(PIN_CS, OUTPUT); digitalWrite(PIN_CS, HIGH); pinMode(PIN_READY, INPUT); SPI.begin(PIN_SCLK, PIN_MISO, PIN_MOSI, -1);
  if (!LittleFS.begin(true)) Serial.println("flash file system failed to start"); delay(300);
  Serial.println("\nHex-N save/restore. Type: id | status | tabsave <1..5> [count] | tabload <1..5> | tabcheck <1..5> [count] | tabfill <1..5> [count] | tabclear <1..5> [count] | jsnap | jscorecheck | jcompare <A|B> <A|B> | jsave <A|B> | jload <A|B> [A|B] | jfill <A|B> | jcheck <A|B> | jbreak <A|B> <c|m|g|o> | jclear | jtest | pintest | ls"); }
void loop() {
  static String line;
  while (Serial.available()) { char c = Serial.read();
    if (c == '\n' || c == '\r') { line.trim();
      if (line.length() && line != "id" && line != "ls" && line != "pintest" && rd_reg(0) != UNIT_ID_V2) Serial.printf("the unit is not answering (ID read 0x%08lX, want 0x57320002): check the Tang has the v8 bitstream loaded and the wiring; command ignored\n", (unsigned long)rd_reg(0));
      else if (line == "id") cmd_id(); else if (line == "status") Serial.printf("status 0x%08lX\n", (unsigned long)rd_reg(10));
      else if (line.startsWith("tabsave ")) { int sp = line.substring(8).toInt(); int sx = line.indexOf(' ', 8); cmd_tabsave(sp, sx > 0 ? line.substring(sx + 1).toInt() : 0); }
      else if (line.startsWith("tabload ")) cmd_tabload(line.substring(8).toInt());
      else if (line.startsWith("tabcheck ")) { int sp = line.substring(9).toInt(); int sx = line.indexOf(' ', 9); cmd_tabcheck(sp, sx > 0 ? line.substring(sx + 1).toInt() : 0); }
      else if (line.startsWith("jsave ")) cmd_jsave(toupper(line.charAt(6)));
      else if (line.startsWith("jload ")) { char a = toupper(line.charAt(6)); char b = line.length() > 8 ? toupper(line.charAt(8)) : a; cmd_jload(a, b); }
      else if (line == "jclear") { uint32_t w[1] = { CLEAR_BOTH }; run_stream(w, 1, 300); Serial.println("both judges cleared"); }
      else if (line.startsWith("jfill ")) cmd_jfill(toupper(line.charAt(6)));
      else if (line.startsWith("jcheck ")) cmd_jcheck(toupper(line.charAt(7)));
      else if (line.startsWith("jbreak ")) cmd_jbreak(toupper(line.charAt(7)), tolower(line.charAt(9)));
      else if (line.startsWith("tabclear ")) { int sp = line.substring(9).toInt(); int sx = line.indexOf(' ', 9); cmd_tabclear(sp, sx > 0 ? line.substring(sx + 1).toInt() : 0); }
      else if (line.startsWith("tabfill ")) { int sp = line.substring(8).toInt(); int sx = line.indexOf(' ', 8); cmd_tabfill(sp, sx > 0 ? line.substring(sx + 1).toInt() : 0); }
      else if (line.startsWith("jcompare ")) cmd_jcompare(toupper(line.charAt(9)), toupper(line.charAt(11)));
      else if (line == "jsnap") cmd_jsnap(); else if (line == "jscorecheck") cmd_jscorecheck();
      else if (line == "pintest") cmd_pintest();
      else if (line == "pintest") cmd_pintest();
      else if (line == "jtest") cmd_jtest(); else if (line == "ls") cmd_ls();
      line = ""; } else line += c; }
}
