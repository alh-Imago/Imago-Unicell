// design.h -- which design is loaded on the FPGA, and which sensor feeds each input lane. Chosen at RUN TIME (the web page's Setup card, or `design relay` in the Serial Monitor)
// and kept in the ESP32's flash, so changing it never means editing the sketch (and never clashes with an update from the repo).
// In a header, not the .ino, because the Arduino IDE builds C++ prototypes from the .ino and mishandles user types declared there.
#pragma once
#include <Arduino.h>
#include "sensors.h"

#define MAX_LANES 4

struct DesignInfo {
  const char* key;        // short name used by the page and the Serial Monitor
  const char* name;
  int         lanes;      // input words per item
  const char* laneNames;
  const char* example;
  bool        rawAngle;   // true: the live feed sends the bare 16-bit amount (CORDIC angle); false: the packed SensorTrix word
};
static const DesignInfo DESIGNS[] = {
  { "cordic", "CORDIC z convergence",                 1, "angle z0",                  "50000\n-50000\n0\n12345\n-12345\n90000",           true  },   // fpga/build/unit_cordic_v1
  { "relay",  "Relay chain (word passes through)",    1, "one input word per item",   "7\n123456\n-5",                                    false },   // fpga/build/unit_relay_v1
  { "tree",   "Parallel reduction tree (sum of 4)",   4, "four input words per item", "1 2 3 4\n10 20 30 40\n100 200 300 400",             false },   // fpga/build/unit_tree_v1
};
static const int DESIGN_COUNT = sizeof(DESIGNS) / sizeof(DESIGNS[0]);

static int g_design = 0;                                    // index into DESIGNS
static int g_laneSensor[MAX_LANES] = { 0, 1, 2, 3 };        // index into SENSORS[] for each input lane

static const DesignInfo& dsg() { return DESIGNS[g_design]; }
static int design_index(const char* key) { for (int i = 0; i < DESIGN_COUNT; i++) if (!strcmp(DESIGNS[i].key, key)) return i; return -1; }

// "0,1,2,3" -> g_laneSensor (anything out of range is ignored, so a stale value from an older sketch cannot break the live feed)
static void design_parse_lanes(const char* s) {
  for (int i = 0; i < MAX_LANES && *s; i++) {
    char* e; long v = strtol(s, &e, 10);
    if (e == s) break;
    if (v >= 0 && v < SENSOR_COUNT) g_laneSensor[i] = (int)v;
    s = (*e == ',') ? e + 1 : e;
  }
}
