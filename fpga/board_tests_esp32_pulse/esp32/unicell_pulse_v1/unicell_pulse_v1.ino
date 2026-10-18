// unicell_pulse_v1.ino -- ESP32 side of test P1 (ledger #1227): how short a pulse does the ESP32's interrupt handler notice? Built from the C1 v3 sketch (ledger #1224); the storm, compute loop and commands are unchanged.
// The Tang (tools/board_esp32_pulse_v1.py, fpga/board_tests_esp32_pulse) sends pulses of 12 widths (100 us down to 37 ns) on pin 86 -> IO16. The handler is a RISING-edge interrupt that TOGGLES the answer pin IO17 (-> Tang pin 72) each time it runs; the Tang counts a pulse as caught if the answer pin changed.
// Wiring is the same as C1: Tang 86 -> IO16, IO17 -> Tang 72, Tang 53 -> IO21 (storm, only in the pe_storm build), GND-GND.
// Serial Monitor, 115200 baud, "Newline". Commands:  l1 / l0 = compute loop on / off   w<N> = storm work in us (default 6)   i = setup   z = zero the totals (do this before every run)
// Each second:  P1 loop=.. jobs=.. job_us min/avg/max=..  runs=<handler runs this second>  storm=..  rT=<handler runs since z>  stormT=..  storm_work_us=..
// A full Tang run is 8 slow pre-check pulses + 12 x 512 = 6,152 pulses, so rT should end at about 6,152 (plus or minus a stray) if every pulse is noticed once.
#include <Arduino.h>
#include "soc/gpio_reg.h"
#include "soc/soc.h"

#define PIN_EVENT  16
#define PIN_ANSWER 17
#define PIN_STORM  21
#define JOB_ITERS  200000UL

static volatile uint32_t ev_cnt = 0, storm_cnt = 0, sink = 0, dup_cnt = 0, hi_cnt = 0, lo_cnt = 0;
static volatile uint32_t prev_lvl = 0;
static volatile uint32_t storm_work_cycles = 0;     // set from STORM_WORK_US * CPU MHz
static uint32_t storm_work_us = 6;
static bool loop_on = true;

static inline uint32_t IRAM_ATTR ccount() { uint32_t c; __asm__ __volatile__("rsr %0, ccount" : "=a"(c)); return c; }

void IRAM_ATTR isr_event() {
  if (REG_READ(GPIO_OUT_REG) & (1u << PIN_ANSWER)) REG_WRITE(GPIO_OUT_W1TC_REG, 1u << PIN_ANSWER);
  else                                             REG_WRITE(GPIO_OUT_W1TS_REG, 1u << PIN_ANSWER);
  ev_cnt++;
}

void IRAM_ATTR isr_storm() {
  uint32_t t0 = ccount();
  while ((uint32_t)(ccount() - t0) < storm_work_cycles) { }
  storm_cnt++;
}

static void set_storm_work(uint32_t us) {
  storm_work_us = us;
  storm_work_cycles = us * getCpuFrequencyMhz();
}

static uint32_t job() {                              // fixed integer work, no memory traffic, cannot be optimised away (result is stored in sink)
  uint32_t x = 2463534242UL;
  for (uint32_t i = 0; i < JOB_ITERS; i++) { x ^= x << 13; x ^= x >> 17; x ^= x << 5; }
  return x;
}

static void print_setup() {
  Serial.printf("P1 setup: cpu=%u MHz  core=%d  sdk=%s  event=IO%d answer=IO%d storm=IO%d  job=%lu xorshift steps  storm_work_us=%lu  loop=%d\n",
                getCpuFrequencyMhz(), xPortGetCoreID(), ESP.getSdkVersion(), PIN_EVENT, PIN_ANSWER, PIN_STORM, (unsigned long)JOB_ITERS, (unsigned long)storm_work_us, loop_on ? 1 : 0);
}

void setup() {
  Serial.begin(115200);
  delay(500);
  pinMode(PIN_ANSWER, OUTPUT);
  digitalWrite(PIN_ANSWER, LOW);
  pinMode(PIN_EVENT, INPUT_PULLDOWN);
  pinMode(PIN_STORM, INPUT_PULLDOWN);
  set_storm_work(storm_work_us);
  attachInterrupt(digitalPinToInterrupt(PIN_EVENT), isr_event, RISING);
  attachInterrupt(digitalPinToInterrupt(PIN_STORM), isr_storm, CHANGE);
  print_setup();
}

void loop() {
  static uint32_t win_start = 0, jobs = 0, jmin = 0xFFFFFFFFUL, jmax = 0, jsum = 0, ev_prev = 0, st_prev = 0;
  while (Serial.available()) {
    String s = Serial.readStringUntil('\n'); s.trim();
    if (s == "l1") loop_on = true;
    else if (s == "l0") loop_on = false;
    else if (s.startsWith("w")) set_storm_work(s.substring(1).toInt());
    else if (s == "i") { print_setup(); }
    else if (s == "z") { noInterrupts(); ev_cnt = 0; storm_cnt = 0; dup_cnt = 0; hi_cnt = 0; lo_cnt = 0; interrupts(); ev_prev = 0; st_prev = 0; Serial.println("P1 totals zeroed"); }
    win_start = 0; jobs = 0; jmin = 0xFFFFFFFFUL; jmax = 0; jsum = 0;
  }
  if (win_start == 0) win_start = micros();
  if (loop_on) {
    uint32_t a = micros();
    sink = job();
    uint32_t d = micros() - a;
    jobs++; jsum += d; if (d < jmin) jmin = d; if (d > jmax) jmax = d;
  } else {
    delay(1);
  }
  if ((uint32_t)(micros() - win_start) >= 1000000UL) {
    noInterrupts(); uint32_t evT = ev_cnt, stT = storm_cnt; interrupts();    // one consistent read of both totals; the window figures are differences of totals, so nothing is lost between lines
    Serial.printf("P1 loop=%d jobs=%lu job_us min/avg/max= %lu/%lu/%lu  runs=%lu storm=%lu rT=%lu stormT=%lu storm_work_us=%lu\n", loop_on ? 1 : 0, (unsigned long)jobs,
                  (unsigned long)(jobs ? jmin : 0), (unsigned long)(jobs ? jsum / jobs : 0), (unsigned long)jmax,
                  (unsigned long)(evT - ev_prev), (unsigned long)(stT - st_prev), (unsigned long)evT, (unsigned long)stT, (unsigned long)storm_work_us);
    ev_prev = evT; st_prev = stT;
    win_start = 0; jobs = 0; jmin = 0xFFFFFFFFUL; jmax = 0; jsum = 0;
  }
}
