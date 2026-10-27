// hexn_logger_v2.ino -- clone of hexn_logger.ino (v1 ran on hardware 27 Oct 2026 and is left untouched) plus an IR receiver on GPIO 14. v2 NOT COMPILED OR RUN YET (written 27 Oct 2026).
// New: every edge of GPIO 14 is time-stamped in an interrupt and printed as   E,<us>,<level>   (level = the pin level AFTER the edge; an IR module idles high and goes low during a burst). 'E' lines are asynchronous and do not change the 'S' sample lines. An edge ring buffer of 256 holds them between prints; overflows are counted and reported by 'stop' and 'info'.
// No WiFi, no averaging, no Tang needed. Streams every sample over USB serial at a fixed rate so the real noise can be examined on the PC.
// Same pins as the UniCell sketch (docs/WIRING_REFERENCE_v1.md in imago-unicell): pot 35, light 36, thermistor 39 (all ADC1), PIR 16, tilt 17.
// Line format (text, one per sample):  S,<seq>,<us>,<a35>,<a36>,<a39>,<d16>,<d17>
//   seq = sample counter (a gap means the ESP missed a slot), us = micros() at the sample, a* = raw 12-bit ADC counts, d* = 0/1.
// Serial commands (end with newline):  rate N  (samples/s, 10..5000, default 1000)   go   stop   info
#include <Arduino.h>
static const int PIN_A[3] = {35, 36, 39};
static const int PIN_D[2] = {16, 17};
static const int PIN_IR = 14;
static const int EQ = 256;
static volatile uint32_t eq_us[EQ]; static volatile uint8_t eq_lv[EQ];
static volatile uint32_t eq_head = 0, eq_dropped = 0; static uint32_t eq_tail = 0;
void IRAM_ATTR on_edge() {
  uint32_t h = eq_head;
  if (h - eq_tail >= EQ) { eq_dropped++; return; }
  eq_us[h % EQ] = micros(); eq_lv[h % EQ] = digitalRead(PIN_IR); eq_head = h + 1;
}
static uint32_t period_us = 1000, seq = 0, next_us = 0;
static bool running = false;
static String line;

static void info() {
  Serial.printf("I,hexn_logger_v2,rate=%u,period_us=%u,edge_dropped=%u,pins=35/36/39 adc1,16/17 dig,14 ir edges\n", (unsigned)(1000000UL / period_us), (unsigned)period_us, (unsigned)eq_dropped);
}
static void cmd(const String& c) {
  if (c.startsWith("rate ")) { int r = c.substring(5).toInt(); if (r < 10) r = 10; if (r > 5000) r = 5000; period_us = 1000000UL / r; info(); }
  else if (c == "go")   { seq = 0; next_us = micros() + period_us; eq_tail = eq_head; eq_dropped = 0; running = true; info(); }
  else if (c == "stop") { running = false; Serial.printf("I,stopped,edge_dropped=%u\n", (unsigned)eq_dropped); }
  else info();
}
void setup() {
  Serial.begin(921600);
  analogReadResolution(12);
  pinMode(PIN_D[0], INPUT); pinMode(PIN_D[1], INPUT_PULLUP);
  pinMode(PIN_IR, INPUT_PULLUP); attachInterrupt(digitalPinToInterrupt(PIN_IR), on_edge, CHANGE);
  delay(200); info();
}
void loop() {
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n' || ch == '\r') { if (line.length()) { cmd(line); line = ""; } }
    else if (line.length() < 40) line += ch;
  }
  while (eq_tail != eq_head) {                              // print the edges the interrupt stored
    uint32_t i = eq_tail % EQ; Serial.printf("E,%u,%d\n", (unsigned)eq_us[i], (int)eq_lv[i]); eq_tail++;
  }
  if (!running) return;
  if ((int32_t)(micros() - next_us) < 0) return;
  uint32_t t = micros();
  next_us += period_us;                                   // fixed grid: a late sample does not shift the later ones
  uint16_t a[3];
  for (int i = 0; i < 3; i++) { (void)analogRead(PIN_A[i]); a[i] = analogRead(PIN_A[i]); }   // first read discarded (ADC channel crosstalk), as in sensors.h
  Serial.printf("S,%u,%u,%u,%u,%u,%d,%d\n", (unsigned)seq++, (unsigned)t, a[0], a[1], a[2], digitalRead(PIN_D[0]), digitalRead(PIN_D[1]));
}
