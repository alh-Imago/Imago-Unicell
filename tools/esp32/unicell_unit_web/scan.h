// scan.h -- the maths behind the Serial command  scan  (ledger #1036 addendum 51). Plain C++ with no Arduino calls, so it is tested on a PC (tests/vm/test_light_scan_v1.py).
// Idea: read ONE analog pin fast and evenly for 100 ms (500 reads, 200 us apart) and ask whether the wobble in the reading is a single steady frequency (room-light flicker:
// mains lighting flickers at TWICE the mains frequency, 100 Hz on 50 Hz mains, 120 Hz on 60 Hz) or just broadband noise, or whether the pin is simply sitting on the ADC's floor or ceiling.
// Why it can be told apart: 100 ms holds a whole number of cycles of 50, 100, 120, 150, 200 and 300 Hz, so each can be measured on its own (Goertzel filter) with no leakage.
#pragma once
#include <math.h>
#include <stdint.h>

#define SCAN_N  500          // reads per scan
#define SCAN_US 200          // microseconds between reads (5 kHz sampling; 100 ms in all)
static volatile bool g_scanBusy = false;   // set while a scan runs; the background sampler skips its sweep so the two never share the ADC

static const int SCAN_LINES = 6;
static const float SCAN_HZ[SCAN_LINES] = {50.0f, 100.0f, 120.0f, 150.0f, 200.0f, 300.0f};

struct ScanResult {
  uint16_t mn, mx;           // lowest and highest raw reading (0..4095)
  float mean;                // average raw reading
  float acrms;               // size of the wobble: RMS of (reading - mean), in raw counts
  float amp[SCAN_LINES];     // peak size (raw counts) of the wobble at each line frequency
  float frac[SCAN_LINES];    // share of the total wobble power that sits on that line (0..1)
  float flicker;             // share of the wobble power on 100 Hz + 200 Hz + 300 Hz (mains flicker on 50 Hz mains, with its harmonics)
  int   best;                // index of the strongest line
  const char* verdict;
};

// fs = the real sampling rate (reads / elapsed seconds), measured by the caller.
static float scan_goertzel_amp(const uint16_t* x, int n, float fs, float f, float mean) {
  const float w = 2.0f * (float)M_PI * f / fs, c = 2.0f * cosf(w);
  float s1 = 0, s2 = 0;
  for (int i = 0; i < n; i++) { float s = (x[i] - mean) + c * s1 - s2; s2 = s1; s1 = s; }
  float re = s1 - s2 * cosf(w), im = s2 * sinf(w);
  return 2.0f * sqrtf(re * re + im * im) / n;
}

static void scan_analyze(const uint16_t* x, int n, float fs, ScanResult& r) {
  r.mn = 65535; r.mx = 0; double sum = 0;
  for (int i = 0; i < n; i++) { if (x[i] < r.mn) r.mn = x[i]; if (x[i] > r.mx) r.mx = x[i]; sum += x[i]; }
  r.mean = (float)(sum / n);
  double v = 0; for (int i = 0; i < n; i++) { double d = x[i] - r.mean; v += d * d; }
  r.acrms = (float)sqrt(v / n);
  const float power = r.acrms * r.acrms;
  r.best = 0;
  for (int k = 0; k < SCAN_LINES; k++) {
    r.amp[k] = scan_goertzel_amp(x, n, fs, SCAN_HZ[k], r.mean);
    r.frac[k] = power > 0 ? (r.amp[k] * r.amp[k] * 0.5f) / power : 0;
    if (r.amp[k] > r.amp[r.best]) r.best = k;
  }
  r.flicker = r.frac[1] + r.frac[4] + r.frac[5];
  if (r.mean < 40)             r.verdict = "FLOOR: the pin sits at the bottom of the ADC range (under about 30 mV). Check the wiring and which way round the module reads; the wobble here is not trustworthy";
  else if (r.mean > 4050)      r.verdict = "CEILING: the pin sits at the top of the ADC range. Check the supply to the module (3.3 V, not 5 V) and the wiring";
  else if (r.acrms < 2.0f)     r.verdict = "STEADY: under 2 counts of wobble. Nothing to fix";
  else if (r.flicker >= 0.5f)  r.verdict = "FLICKER: most of the wobble is a steady 100 Hz line (and its harmonics): mains lighting. Average over 10 ms or longer, or accept it";
  else if (r.frac[2] >= 0.5f)  r.verdict = "FLICKER at 120 Hz: lighting on 60 Hz mains";
  else if (r.frac[r.best] >= 0.5f) r.verdict = "A STEADY LINE at the frequency shown, but not mains flicker: look for a switching supply, a PWM light or a motor";
  else                         r.verdict = "NOISE: the wobble is spread over many frequencies, not one line. Suspect the wiring, the supply, or WiFi interference on the ADC";
}
