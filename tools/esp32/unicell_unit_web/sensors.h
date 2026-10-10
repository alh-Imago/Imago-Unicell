// sensors.h -- sensors the ESP32 can feed LIVE into the running design (ledger #1036 addendum 17).
// A reading becomes one SensorTrix word: bits 31..16 = amount (16 bits), bits 15..0 = location (the sensor's number). Same format as the old full-cell stack
// (tests/vm/legacy_full_cell/test_sensortrix.py); simulated end to end in tests/vm/test_unit_live_feed_v1.py.
//
// HOW TO ADD A SENSOR FROM YOUR PACK: add one line to SENSORS[]. For a plain analog sensor give its ADC1 pin. For anything digital (I2C / one-wire / SPI) give pin -1, set
// `custom` to a function that returns the reading as 0..65535 (scale it yourself), and include that sensor's Arduino library at the top of this file.
// ADC pins: use ADC1 only (GPIO 32..39). ADC2 does not work while WiFi is on, and this sketch always has WiFi on. GPIO 32/33 and 34 are already used here
// (the ESP32's own SD card and the READY line), 25/26 too, so the free ADC1 pins are 35, 36 and 39 (input-only pins, fine for sensors).
#pragma once
#include <Arduino.h>
#include <math.h>
#include "scan.h"

typedef uint16_t (*SensorFn)();

struct Sensor {
  const char* name;
  uint16_t    loc;      // location number carried in the low 16 bits of the word
  int8_t      pin;      // ADC1 pin, or -1 when `custom` supplies the reading
  SensorFn    custom;   // used when pin == -1
};

// ---- ready-made readers for the SunFounder ESP32 Ultimate Starter Kit parts (pins are YOUR choice: wire them, then put the pin in the table below; the web page's Setup card chooses which sensor feeds which input) -----------------
// Free GPIOs on this build (not used by the unit link 5/18/19/23/34 or the file card 32/33/25/26, and not strapping/flash pins): digital 4, 13, 14, 16, 17, 21, 22, 27
// (4, 13, 14, 27 are also the ones kept free for the later JTAG loader); analog (ADC1, input-only) 35, 36, 39.
// Every reading is scaled to 0..65535 so it fits the 16-bit amount field; the scaling is written in each function and is yours to change.

// Digital sensors (button, tilt switch, PIR motion, obstacle avoidance, line tracking): 0 or 65535. Many of these modules read LOW when active; flip with `~` if yours does.
static uint16_t rd_digital(int pin) { return digitalRead(pin) ? 65535 : 0; }
#define DIGITAL_SENSOR(fname, PIN) static uint16_t fname() { return rd_digital(PIN); }

// Thermistor on an analog pin: ASSUMED a 10 k NTC (B = 3950) in a divider with a 10 k resistor, thermistor on the GND side. If your kit wires it the other way round, swap
// the two resistances in the formula. Result = (degC + 40) * 100, so -40 C -> 0 and 25 C -> 6500 (clamped to 16 bits). The ESP32 ADC is not linear; treat it as indicative.
static uint16_t rd_thermistor(int pin) {
  (void)analogRead(pin); delayMicroseconds(100);                       // discard the first read (crosstalk from the previously read channel)
  uint32_t sum = 0; for (int i = 0; i < 8; i++) sum += analogRead(pin);
  float v = sum / 8.0f; if (v < 1) v = 1; if (v > 4094) v = 4094;
  float r = 10000.0f * v / (4095.0f - v);                              // thermistor resistance
  float t = 1.0f / (1.0f / 298.15f + logf(r / 10000.0f) / 3950.0f) - 273.15f;
  float a = (t + 40.0f) * 100.0f; if (a < 0) a = 0; if (a > 65535) a = 65535;
  return (uint16_t)a;
}

// Ultrasonic (HC-SR04 style, trigger + echo): distance in millimetres (0 = no echo). The echo pin of a 5 V module sends 5 V: use a divider (e.g. 1 k + 2 k) before the ESP32 pin.
static uint16_t rd_ultrasonic(int trig, int echo) {
  digitalWrite(trig, LOW); delayMicroseconds(3); digitalWrite(trig, HIGH); delayMicroseconds(10); digitalWrite(trig, LOW);
  unsigned long us = pulseIn(echo, HIGH, 30000UL);                      // 30 ms timeout = about 5 m
  if (us == 0) return 0;
  uint32_t mm = (uint32_t)(us * 0.1715f); return mm > 65535 ? 65535 : (uint16_t)mm;
}

// DHT11 temperature / humidity: needs the Arduino "DHT sensor library" (Adafruit). Switched off until you define USE_DHT11 (with its pin) in this file. NOT tried.
// #define USE_DHT11 21
#ifdef USE_DHT11
  #include <DHT.h>
  static DHT g_dht(USE_DHT11, DHT11);
  static uint16_t rd_dht_temp()  { float t = g_dht.readTemperature(); return isnan(t) ? 0 : (uint16_t)((t + 40.0f) * 100.0f); }   // (degC + 40) * 100
  static uint16_t rd_dht_humid() { float h = g_dht.readHumidity();    return isnan(h) ? 0 : (uint16_t)(h * 100.0f); }               // percent * 100
#endif

// Example wiring used below (change to what you wire): potentiometer -> 35, light sensor -> 36, thermistor -> 39, PIR -> 16, tilt switch -> 17, ultrasonic trig 22 / echo 21.
DIGITAL_SENSOR(rd_pir, 16)
DIGITAL_SENSOR(rd_tilt, 17)
static uint16_t rd_thermistor39() { return rd_thermistor(39); }
static uint16_t rd_ultra()        { return rd_ultrasonic(22, 21); }

// The table. EVERY line here can be chosen on the web page's Setup card (one sensor per design input lane); only the chosen ones are read, so listing a sensor you have not wired is harmless.
// Add a line for each new sensor; the order is the order on the page, and the first entries are the default for input 1, 2, 3, 4.
static Sensor SENSORS[] = {
  { "potentiometer",  1, 35, nullptr },            // analog, 0..4095 scaled up to 0..65520
  { "light sensor",   2, 36, nullptr },            // analog (photoresistor in a divider): brighter or darker depending on how the module is wired
  { "thermistor",     3, -1, rd_thermistor39 },    // analog pin 39, see rd_thermistor for the assumed circuit
  { "PIR motion",     4, -1, rd_pir },             // digital pin 16
  { "tilt switch",    5, -1, rd_tilt },            // digital pin 17
  { "ultrasonic mm",  6, -1, rd_ultra },           // trigger 22, echo 21 (echo needs a voltage divider)
};
static const int SENSOR_COUNT = sizeof(SENSORS) / sizeof(SENSORS[0]);

// Call once from setup(): sets the pin directions the readers above need. Edit to match your wiring.
static void sensors_begin() {
  pinMode(16, INPUT); pinMode(17, INPUT_PULLUP);            // PIR, tilt switch
  pinMode(22, OUTPUT); pinMode(21, INPUT);                  // ultrasonic trigger, echo
  analogReadResolution(12);
#ifdef USE_DHT11
  g_dht.begin();
#endif
}

static uint16_t sensor_amount(const Sensor& s) {
  if (s.pin < 0) return s.custom ? s.custom() : 0;
  (void)analogRead(s.pin); delayMicroseconds(100);              // throw one read away: the ESP32 ADC's sample capacitor still holds the PREVIOUS channel's voltage, which leaks into a high-impedance sensor (a pot or thermistor divider) as crosstalk
  uint32_t sum = 0;
  for (int i = 0; i < 8; i++) sum += analogRead(s.pin);        // 12-bit reads, averaged over 8 to calm the noise
  return (uint16_t)((sum / 8) << 4);                           // 0..4095 -> 0..65520 (12-bit scaled up to the 16-bit amount field)
}
// Serial command  scan [pin] [raw]  (addendum 51): 500 fast reads of one analog pin, then say whether the wobble is room-light flicker, noise, or a pin stuck on the ADC floor/ceiling.
// Default pin = the "light sensor" line of the table. With  raw  it also prints every reading, so the numbers can be kept and re-analysed on a PC.
static void adc_scan_run(int pin, bool raw) {
  static uint16_t buf[SCAN_N];
  g_scanBusy = true; vTaskDelay(pdMS_TO_TICKS(40));             // let the sampler task finish the sweep it is in
  (void)analogRead(pin); delayMicroseconds(100);
  uint32_t t0 = micros();
  for (int i = 0; i < SCAN_N; i++) {
    buf[i] = analogRead(pin);
    uint32_t due = t0 + (uint32_t)(i + 1) * SCAN_US;
    while ((int32_t)(micros() - due) < 0) { }
  }
  float secs = (micros() - t0) / 1e6f;
  g_scanBusy = false;
  ScanResult r; scan_analyze(buf, SCAN_N, SCAN_N / secs, r);
  Serial.printf("scan pin %d: %d reads in %.1f ms (%.0f reads/s)\n", pin, SCAN_N, secs * 1000.0f, SCAN_N / secs);
  Serial.printf("  reading: min %u  max %u  mean %.1f  wobble (rms) %.1f counts of 4095\n", r.mn, r.mx, r.mean, r.acrms);
  for (int k = 0; k < SCAN_LINES; k++) Serial.printf("  %3.0f Hz: peak %.1f counts, %.0f%% of the wobble\n", SCAN_HZ[k], r.amp[k], r.frac[k] * 100.0f);
  Serial.printf("  100+200+300 Hz together: %.0f%% of the wobble\n", r.flicker * 100.0f);
  Serial.printf("  VERDICT: %s\n", r.verdict);
  if (raw) { Serial.println("  raw readings:"); for (int i = 0; i < SCAN_N; i++) { Serial.print(buf[i]); Serial.print(i % 25 == 24 ? '\n' : ' '); } }
}
static uint32_t sensor_word(const Sensor& s, uint16_t amount) { return ((uint32_t)amount << 16) | s.loc; }
