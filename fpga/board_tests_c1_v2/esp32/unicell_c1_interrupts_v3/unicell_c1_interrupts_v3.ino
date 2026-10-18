// unicell_c1_interrupts_v3.ino -- (ledger #1224; clone of v2 from #1217, v2 untouched). v3 adds a check on every edge interrupt: the handler compares the level it sees with the level it saw the LAST time it ran. Edges alternate, so two runs of the handler in a row with the SAME level mean an edge between them never got a handler run of its own (dupT= counts these; hiT= / loT= count handler runs that saw high / low). dupT > 0 means edges really were lost on the ESP32 side; dupT = 0 with an unanswered edge on the Tang would mean the handler did run. Everything else is as v2. v2 header follows: v2 adds CUMULATIVE interrupt counters (evT=, stormT=) that never lose an edge while the line is being printed, and a z command to zero them. Original header: (ledger #1211) an interrupt handler answering edges, with and without other work going on.
// The Tang Nano 20K is the stopwatch (tools/board_esp32_c1_v1.py, fpga/board_tests_c1): it sends random-timed edges and times how long the answer takes.
// Wiring (ESP32 pin <-> Tang pin), plus GND-GND which is already there:
//   IO16  <-  Tang pin 86   the edges to be answered
//   IO17  ->  Tang pin 72   the answer: the interrupt handler copies the level of IO16 onto IO17
//   IO21  <-  Tang pin 53   the "storm": edges every 26 to 102 us, mean 64 us, about 15,670 a second (v1 said 26-76 us: wrong, ledger #1216) (only while the c1_storm bitstream runs); each one costs STORM_WORK_US of busy work in its handler
// (IO16/17/21 are the pins the wiring reference lists for the PIR / tilt / ultrasonic sensors: unplug those first.)
// Serial Monitor, 115200 baud, line ending "Newline". Commands:  l1 = compute loop ON (default)   l0 = compute loop OFF   w<N> = storm work in microseconds (default 6)   i = print the setup   z = zero the totals (do this just before loading a Tang bitstream)
// Once a second it prints one line:
//   C1 loop=1 jobs=N job_us min/avg/max= a/b/c  ev=<edge interrupts this second>  storm=<storm interrupts this second>  evT=<total since z>  stormT=<total since z>  storm_work_us=6
// A full Tang run adds 16 slow test edges + 4,096 timed edges to evT (4,112 in all) plus a few stray edges while the Tang loads; with the storm build stormT is about 15,650 per second of run.
// The compute job is a fixed amount of integer work (JOB_ITERS xorshift steps); its time per run is how much the ESP32 is slowed by the interrupts. The Tang's own result line gives the answer time.
// The handlers are the plain Arduino attachInterrupt() kind (what a normal sketch would use), kept in IRAM so flash cache misses do not matter. WiFi and Bluetooth are NOT started.
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
  uint32_t lvl = (REG_READ(GPIO_IN_REG) >> PIN_EVENT) & 1u;
  if (lvl) REG_WRITE(GPIO_OUT_W1TS_REG, 1u << PIN_ANSWER);
  else     REG_WRITE(GPIO_OUT_W1TC_REG, 1u << PIN_ANSWER);
  if (lvl == prev_lvl) dup_cnt++;
  prev_lvl = lvl;
  if (lvl) hi_cnt++; else lo_cnt++;
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
  Serial.printf("C1 setup: cpu=%u MHz  core=%d  sdk=%s  event=IO%d answer=IO%d storm=IO%d  job=%lu xorshift steps  storm_work_us=%lu  loop=%d\n",
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
  attachInterrupt(digitalPinToInterrupt(PIN_EVENT), isr_event, CHANGE);
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
    else if (s == "z") { noInterrupts(); ev_cnt = 0; storm_cnt = 0; dup_cnt = 0; hi_cnt = 0; lo_cnt = 0; interrupts(); ev_prev = 0; st_prev = 0; Serial.println("C1 totals zeroed"); }
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
    noInterrupts(); uint32_t evT = ev_cnt, stT = storm_cnt, dupT = dup_cnt, hiT = hi_cnt, loT = lo_cnt; interrupts();    // one consistent read of both totals; the window figures are differences of totals, so nothing is lost between lines
    Serial.printf("C1 loop=%d jobs=%lu job_us min/avg/max= %lu/%lu/%lu  ev=%lu storm=%lu evT=%lu stormT=%lu dupT=%lu hiT=%lu loT=%lu storm_work_us=%lu\n", loop_on ? 1 : 0, (unsigned long)jobs,
                  (unsigned long)(jobs ? jmin : 0), (unsigned long)(jobs ? jsum / jobs : 0), (unsigned long)jmax,
                  (unsigned long)(evT - ev_prev), (unsigned long)(stT - st_prev), (unsigned long)evT, (unsigned long)stT, (unsigned long)dupT, (unsigned long)hiT, (unsigned long)loT, (unsigned long)storm_work_us);
    ev_prev = evT; st_prev = stT;
    win_start = 0; jobs = 0; jmin = 0xFFFFFFFFUL; jmax = 0; jsum = 0;
  }
}
