// unicell_c2_threads_v2.ino -- ESP32 test C2 (ledger #1212; v1 of #1211 called disableCore0WDT(), which on this board gave a "esp_task_wdt_reset: task not found" loop; v2 does not touch the watchdog): the same job as 1, 2, 4 and 8 threads on the SAME device, compared with itself. No wiring, no Tang.
// Question: when more threads of the same work are added on a conventional processor, what happens to (a) the time of one watched job and (b) the total time?
// For each case it runs RUNS repeats of: THREADS FreeRTOS tasks (all the same priority), each doing REPS runs of the same fixed integer job; task 0 is "the watched job" and times every one of its runs.
// Two layouts: "core1" = every task pinned to ONE core (core 1, where the Arduino loop runs), "both" = tasks alternate between core 0 and core 1.
// Serial Monitor, 115200 baud, line ending "Newline". It runs the whole table at start-up and again whenever you send  r  .   Send  i  to print the setup.
// Output, one line per run:  C2 layout=core1 threads=4 run=1 wall_ms=.. total_jobs=.. jobs_per_s=.. watched_job_us min/avg/max=a/b/c
// What the numbers mean: with one thread the watched job takes about one job time. If threads share a core the scheduler gives each task a time slice (the tick is 1 ms), so the watched job's time and the wall time are expected to grow; this sketch measures how much, it does not assume it.
// WiFi and Bluetooth are NOT started. The task watchdog is left alone: each case keeps a core busy for well under a second, far below the watchdog time-out (5 s by default).
#include <Arduino.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"

#define JOB_ITERS 50000UL     // one job = this many xorshift + integer-divide steps (about 1-2 ms at 240 MHz)
#define REPS      60          // jobs per task per run
#define RUNS      3           // repeats of every case, to show run-to-run variation
#define MAXTHR    8

static EventGroupHandle_t eg;
static const EventBits_t START_BIT = (1 << 23);
static volatile uint32_t sink[MAXTHR];
static uint32_t w_min, w_max, w_sum, w_n;           // the watched task's job times

static uint32_t job(uint32_t seed) {
  uint32_t x = seed | 1u, acc = 0;
  for (uint32_t i = 0; i < JOB_ITERS; i++) {
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    acc += x / ((x & 0xFFu) + 3u);
  }
  return acc;
}

static void worker(void *arg) {
  uint32_t idx = (uint32_t)(uintptr_t)arg;
  xEventGroupWaitBits(eg, START_BIT, pdFALSE, pdTRUE, portMAX_DELAY);       // all workers released together
  uint32_t acc = 0;
  for (uint32_t r = 0; r < REPS; r++) {
    uint32_t a = micros();
    acc += job(0x9E3779B9u * (idx + 1) + r);
    uint32_t d = micros() - a;
    if (idx == 0) { w_n++; w_sum += d; if (d < w_min) w_min = d; if (d > w_max) w_max = d; }
  }
  sink[idx] = acc;
  xEventGroupSetBits(eg, (EventBits_t)(1u << idx));
  vTaskDelete(NULL);
}

static void run_case(const char *layout, int threads, int run) {
  w_min = 0xFFFFFFFFUL; w_max = 0; w_sum = 0; w_n = 0;
  xEventGroupClearBits(eg, 0x00FFFFFF);
  for (int t = 0; t < threads; t++) {
    int core = (layout[0] == 'b') ? (t & 1) : 1;                 // "both": 0,1,0,1,...   "core1": all on 1
    xTaskCreatePinnedToCore(worker, "w", 4096, (void *)(uintptr_t)t, 1, NULL, core);
  }
  delay(20);                                                      // let every worker reach its start gate
  uint32_t t0 = micros();
  xEventGroupSetBits(eg, START_BIT);
  EventBits_t all = (1u << threads) - 1u;
  xEventGroupWaitBits(eg, all, pdFALSE, pdTRUE, portMAX_DELAY);
  uint32_t wall_us = micros() - t0;
  xEventGroupClearBits(eg, START_BIT);
  uint32_t total = (uint32_t)threads * REPS;
  Serial.printf("C2 layout=%s threads=%d run=%d wall_ms=%lu total_jobs=%lu jobs_per_s=%lu watched_job_us min/avg/max=%lu/%lu/%lu\n",
                layout, threads, run, (unsigned long)(wall_us / 1000), (unsigned long)total, (unsigned long)((uint64_t)total * 1000000ULL / wall_us),
                (unsigned long)w_min, (unsigned long)(w_n ? w_sum / w_n : 0), (unsigned long)w_max);
  delay(50);
}

static void print_setup() {
  Serial.printf("C2 setup: cpu=%u MHz  sdk=%s  tick_hz=%u  job=%lu steps  reps=%d  runs=%d  loop core=%d\n",
                getCpuFrequencyMhz(), ESP.getSdkVersion(), (unsigned)configTICK_RATE_HZ, (unsigned long)JOB_ITERS, REPS, RUNS, xPortGetCoreID());
}

static void run_table() {
  const int T[4] = {1, 2, 4, 8};
  const char *L[2] = {"core1", "both"};
  for (int l = 0; l < 2; l++)
    for (int ti = 0; ti < 4; ti++) {
      if (l == 1 && T[ti] == 1) continue;                         // one thread on "both" is the same as on core1
      for (int r = 1; r <= RUNS; r++) run_case(L[l], T[ti], r);
    }
  Serial.println("C2 table done");
}

void setup() {
  Serial.begin(115200);
  delay(500);
  eg = xEventGroupCreate();
  print_setup();
  run_table();
}

void loop() {
  if (Serial.available()) {
    String s = Serial.readStringUntil('\n'); s.trim();
    if (s == "r") run_table();
    else if (s == "i") print_setup();
  }
  delay(20);
}
