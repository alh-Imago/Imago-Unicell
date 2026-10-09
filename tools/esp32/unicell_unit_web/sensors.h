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

typedef uint16_t (*SensorFn)();

struct Sensor {
  const char* name;
  uint16_t    loc;      // location number carried in the low 16 bits of the word
  int8_t      pin;      // ADC1 pin, or -1 when `custom` supplies the reading
  SensorFn    custom;   // used when pin == -1
};

// Defaults: three analog inputs so something works with a pot / LDR / analog sensor on 35, 36, 39. Replace or extend freely.
static Sensor SENSORS[] = {
  { "analog 35", 1, 35, nullptr },
  { "analog 36", 2, 36, nullptr },
  { "analog 39", 3, 39, nullptr },
};
static const int SENSOR_COUNT = sizeof(SENSORS) / sizeof(SENSORS[0]);

static uint16_t sensor_amount(const Sensor& s) {
  if (s.pin < 0) return s.custom ? s.custom() : 0;
  uint32_t sum = 0;
  for (int i = 0; i < 8; i++) sum += analogRead(s.pin);        // 12-bit reads, averaged over 8 to calm the noise
  return (uint16_t)((sum / 8) << 4);                           // 0..4095 -> 0..65520 (12-bit scaled up to the 16-bit amount field)
}
static uint32_t sensor_word(const Sensor& s, uint16_t amount) { return ((uint32_t)amount << 16) | s.loc; }
