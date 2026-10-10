"""Host test of tools/esp32/unicell_unit_web/scan.h (the light-sensor 'scan' maths). Not run on a real ESP32."""
import math, os, random, shutil, subprocess, sys, tempfile

HDR = os.path.join(os.path.dirname(__file__), "..", "..", "tools", "esp32", "unicell_unit_web")
DRV = r'''
#include <cstdio>
#include <cstdlib>
#include "scan.h"
int main(int argc, char** argv) {
  uint16_t x[SCAN_N]; int v, i = 0;
  while (i < SCAN_N && scanf("%d", &v) == 1) x[i++] = (uint16_t)v;
  ScanResult r; scan_analyze(x, SCAN_N, 1e6f / SCAN_US, r);
  printf("%s|%.2f|%.2f|%.3f\n", r.verdict, r.mean, r.acrms, r.flicker);
  return 0;
}
'''

def _build(tmp):
    src = os.path.join(tmp, "drv.cpp")
    open(src, "w").write(DRV)
    exe = os.path.join(tmp, "drv")
    subprocess.run(["g++", "-std=c++17", "-O1", "-I", HDR, src, "-o", exe], check=True)
    return exe

def _run(exe, xs):
    xs = [max(0, min(4095, int(round(v)))) for v in xs]
    out = subprocess.run([exe], input=" ".join(map(str, xs)), capture_output=True, text=True, check=True).stdout
    return out.strip().split("|")

def _sig(f):
    return [f(i * 200e-6) for i in range(500)]

def test_scan_verdicts():
    if shutil.which("g++") is None:
        print("SKIP: no g++"); raise SystemExit(1)
    rnd = random.Random(5)
    with tempfile.TemporaryDirectory() as tmp:
        exe = _build(tmp)
        v = lambda xs: _run(exe, xs)[0].split(":")[0]
        assert v(_sig(lambda t: 2000 + 300 * math.sin(2 * math.pi * 100 * t + 1))) == "FLICKER"
        assert v(_sig(lambda t: 2000 + 300 * math.sin(2 * math.pi * 120 * t))) == "FLICKER at 120 Hz"
        assert v(_sig(lambda t: 2000 + rnd.gauss(0, 10))) == "NOISE"
        assert v(_sig(lambda t: 2000)) == "STEADY"
        assert v(_sig(lambda t: 10 + rnd.gauss(0, 1))) == "FLOOR"
        assert v(_sig(lambda t: 4095)) == "CEILING"
        assert v(_sig(lambda t: 2000 + 200 * math.sin(2 * math.pi * 150 * t))).startswith("A STEADY LINE")
        # mixed: 100 Hz with a little noise still flicker
        assert v(_sig(lambda t: 2000 + 200 * math.sin(2 * math.pi * 100 * t) + rnd.gauss(0, 20))) == "FLICKER"

if __name__ == "__main__":
    test_scan_verdicts(); print("ok")


def test_averaging_slider_wired_in():
    """Static check (nothing runs on a board): the page has the slider, the sketch has the /api/avg route and saves it, readers use the shared mean."""
    d = HDR
    page = open(os.path.join(d, "page.h")).read(); ino = open(os.path.join(d, "unicell_unit_web.ino")).read(); sen = open(os.path.join(d, "sensors.h")).read()
    assert 'id="avg"' in page and "/api/avg" in page
    assert '"/api/avg"' in ino and 'putUInt("avgms"' in ino and 'getUInt("avgms"' in ino
    assert sen.count("adc_mean(") >= 3 and "g_avgMs" in sen
