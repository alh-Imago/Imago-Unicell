"""hexn_medfilt_v1: a short running median in front of the coding, to remove single-sample glitches from the ESP32 readings (Python model only; no RTL; new file).
CAUSAL: each output is the median of the last w readings (the stream is real time, so no look-ahead); it therefore lags the input by (w-1)/2 samples.
Test data (docs/hex-n/data, 27 Oct 2026, 200 per second):
  glitchy  = thermistor_finger.csv a39 (61 samples more than 100 counts from the slow trend, 4 of them zero)
  clean    = thermistor_run2.csv a39 (no glitches)
  fast     = pot_sweep.csv a35 (moves up to ~1000 counts per second: shows what the lag costs)
  flicker  = light_on.csv a36 (100 Hz flicker folded to 99.6 Hz, sd ~42)
Glitch = a sample more than 100 counts from the centred median of 101 readings (0.5 s) of the SAME file, taken as the reference trend: a hand-made definition; in the dense bursts at 20 to 23 s the reference is itself disturbed.
Reported per window w: glitches left in 'glitchy'; on 'clean' the largest and RMS change the filter makes; on 'fast' the largest and RMS difference between the filtered and the raw reading (this is lag, not error); on 'flicker' the sd after filtering.
Usage: python3 tools/hexn_medfilt_v1.py"""
import os, csv, statistics as st
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "hex-n", "data")
def load(fn, col): return [int(r[col]) for r in csv.reader(l for l in open(os.path.join(D, fn)) if not l.startswith("#")) if len(r) == 8 and r[0].isdigit()]
def causal_median(v, w): return [sorted(v[max(0, i - w + 1):i + 1])[len(v[max(0, i - w + 1):i + 1]) // 2] for i in range(len(v))]
def centred_median(v, w=101): h = w // 2; return [sorted(v[max(0, i - h):i + h + 1])[len(v[max(0, i - h):i + h + 1]) // 2] for i in range(len(v))]
def main():
    glitchy = load("esp_run_20261027_200hz_thermistor_finger.csv", 5); clean = load("esp_run_20261027_200hz_thermistor_run2.csv", 5)
    fast = load("esp_run_20261027_200hz_pot_sweep.csv", 3); flick = load("esp_run_20261027_200hz_light_on.csv", 4)
    ref = centred_median(glitchy); n0 = sum(abs(a - b) > 100 for a, b in zip(glitchy, ref))
    print("glitchy raw: %d samples more than 100 from the 0.5 s median trend (of %d)\n" % (n0, len(glitchy)))
    print(" w | delay ms | glitches left | clean: max / rms change | fast pot: max / rms diff | flicker sd")
    for w in (1, 3, 5, 9, 15, 31, 61):
        g = causal_median(glitchy, w); left = sum(abs(a - b) > 100 for a, b in zip(g, ref))
        c = causal_median(clean, w); dc = [a - b for a, b in zip(c, clean)]
        f = causal_median(fast, w); df = [a - b for a, b in zip(f, fast)]
        fl = causal_median(flick, w)
        print("%2d |   %5.1f  |     %3d       |   %4d / %5.1f        |   %4d / %6.1f         |  %5.1f" % (w, (w - 1) / 2 * 5, left, max(map(abs, dc)), (sum(x * x for x in dc) / len(dc)) ** .5, max(map(abs, df)), (sum(x * x for x in df) / len(df)) ** .5, st.pstdev(fl)))
if __name__ == "__main__": main()
