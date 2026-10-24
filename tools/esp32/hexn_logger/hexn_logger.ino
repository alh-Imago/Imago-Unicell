// hexn_logger.ino -- raw sensor logger for the Hex-N noise study. NOT RUN ON HARDWARE YET (written 24 Oct 2026).
// No WiFi, no averaging, no Tang needed. Streams every sample over USB serial at a fixed rate so the real noise can be examined on the PC.
// Same pins as the UniCell sketch (docs/WIRING_REFERENCE_v1.md in imago-unicell): pot 35, light 36, thermistor 39 (all ADC1), PIR 16, tilt 17.
// Line format (text, one per sample):  S,<seq>,<us>,<a35>,<a36>,<a39>,<d16>,<d17>
//   seq = sample counter (a gap means the ESP missed a slot), us = micros() at the sample, a* = raw 12-bit ADC counts, d* = 0/1.
// Serial commands (end with newline):  rate N  (samples/s, 10..5000, default 1000)   go   stop   info
#include <Arduino.h>
static const int PIN_A[3] = {35, 36, 39};
static const int PIN_D[2] = {16, 17};
static uint32_t period_us = 1000, seq = 0, next_us = 0;
static bool running = false;
static String line;

static void info() {
  Serial.printf("I,hexn_logger_v1,rate=%u,period_us=%u,pins=35/36/39 adc1,16/17 dig\n", (unsigned)(1000000UL / period_us), (unsigned)period_us);
}
static void cmd(const String& c) {
  if (c.startsWith("rate ")) { int r = c.substring(5).toInt(); if (r < 10) r = 10; if (r > 5000) r = 5000; period_us = 1000000UL / r; info(); }
  else if (c == "go")   { seq = 0; next_us = micros() + period_us; running = true; info(); }
  else if (c == "stop") { running = false; Serial.println("I,stopped"); }
  else info();
}
void setup() {
  Serial.begin(921600);
  analogReadResolution(12);
  pinMode(PIN_D[0], INPUT); pinMode(PIN_D[1], INPUT_PULLUP);
  delay(200); info();
}
void loop() {
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n' || ch == '\r') { if (line.length()) { cmd(line); line = ""; } }
    else if (line.length() < 40) line += ch;
  }
  if (!running) return;
  if ((int32_t)(micros() - next_us) < 0) return;
  uint32_t t = micros();
  next_us += period_us;                                   // fixed grid: a late sample does not shift the later ones
  uint16_t a[3];
  for (int i = 0; i < 3; i++) { (void)analogRead(PIN_A[i]); a[i] = analogRead(PIN_A[i]); }   // first read discarded (ADC channel crosstalk), as in sensors.h
  Serial.printf("S,%u,%u,%u,%u,%u,%d,%d\n", (unsigned)seq++, (unsigned)t, a[0], a[1], a[2], digitalRead(PIN_D[0]), digitalRead(PIN_D[1]));
}
