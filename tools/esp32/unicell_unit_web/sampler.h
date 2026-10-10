// sampler.h -- reads the chosen sensors on the ESP32's SECOND core (core 0), so the web server on core 1 never waits for a sensor.
// A slow reading (the ultrasonic sensor can take 30 ms, the ADC averages 8 reads) used to hold up the page; now the page just takes the latest value.
// Lives in a header for the same reason as page.h (the Arduino IDE mangles functions it finds in the .ino).
#pragma once
#include <Arduino.h>
#include "design.h"

static volatile uint16_t g_latest[MAX_LANES];     // newest reading for each input lane
static volatile uint32_t g_sampleSeq = 0;         // counts finished sweeps, so the page can tell fresh data from stale

static void sampler_task(void*) {
  for (;;) {
    if (g_scanBusy) { vTaskDelay(pdMS_TO_TICKS(5)); continue; }      // a  scan  is using the ADC
    const int L = dsg().lanes;
    for (int i = 0; i < L; i++) {
      int k = g_laneSensor[i]; if (k < 0 || k >= SENSOR_COUNT) k = 0;
      g_latest[i] = sensor_amount(SENSORS[k]);
    }
    g_sampleSeq = g_sampleSeq + 1;
    vTaskDelay(pdMS_TO_TICKS(20));                // about 20 ms between sweeps, leaves WiFi (also on core 0) its time
  }
}
static void sampler_begin() { xTaskCreatePinnedToCore(sampler_task, "sampler", 6144, nullptr, 1, nullptr, 0); }
