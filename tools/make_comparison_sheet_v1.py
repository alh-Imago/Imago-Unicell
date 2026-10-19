#!/usr/bin/env python3
"""Build the UniCell (Tang Nano 20K) against ESP32 comparison workbook (ledger #1233).

Reads the saved card result files in fpga/board_tests_*/card_run_18oct*/ and writes
fpga/board_results_comparison/unicell_vs_esp32_comparison_v1.xlsx.
Every number on the data sheets comes from a result file (source column says which);
the percentages, microsecond conversions and the Summary sheet are formulas.
The two clocks (Tang 27 MHz, ESP32 240 MHz) sit in the Settings sheet and can be changed.

Run from the repository root:  python3 tools/make_comparison_sheet_v1.py
Then recalculate: python scripts/recalc.py <xlsx>  (xlsx skill).
"""
import glob
import os
import re

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "fpga", "board_results_comparison")
OUT = os.path.join(OUT_DIR, "unicell_vs_esp32_comparison_v1.xlsx")

FN = "Arial"
BLUE = Font(name=FN, size=10, color="0000FF")
GREEN = Font(name=FN, size=10, color="008000")
BLK = Font(name=FN, size=10)
BOLD = Font(name=FN, size=10, bold=True)
TITLE = Font(name=FN, size=14, bold=True)
HFILL = PatternFill("solid", fgColor="D9E1F2")
YFILL = PatternFill("solid", fgColor="FFFF00")
thin = Side(style="thin", color="BFBFBF")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
HAL = Alignment(wrap_text=True, vertical="center", horizontal="center")
WRAP = Alignment(wrap_text=True, vertical="top")


def rd(pattern):
    files = sorted(glob.glob(os.path.join(ROOT, pattern)))
    if not files:
        raise SystemExit("missing result file: " + pattern)
    return files[0], open(files[0]).read()


def rel(p):
    return os.path.relpath(p, ROOT)


def head(ws, row, names, widths=None):
    for j, h in enumerate(names, 1):
        c = ws.cell(row=row, column=j, value=h)
        c.font = BOLD
        c.fill = HFILL
        c.alignment = HAL
        c.border = BOX
    ws.row_dimensions[row].height = 45
    if widths:
        for j, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(j)].width = w


def put(ws, r, c, v, font=BLK, fmt=None):
    cell = ws.cell(row=r, column=c, value=v)
    cell.font = font
    cell.border = BOX
    if fmt:
        cell.number_format = fmt
    return cell


def title(ws, text, note=None):
    ws["A1"] = text
    ws["A1"].font = TITLE
    if note:
        ws["A2"] = note
        ws["A2"].font = BLK
        ws["A2"].alignment = Alignment(wrap_text=False)


wb = Workbook()
S = "Settings"
TANG = "Settings!$B$3"
ESP = "Settings!$B$4"

# ------------------------------------------------------------------ Summary (filled last)
sm = wb.active
sm.title = "Summary"

# ------------------------------------------------------------------ Settings
st = wb.create_sheet(S)
title(st, "Settings: the two clocks")
st["A3"] = "Tang Nano 20K clock (MHz)"
st["B3"] = 27
st["A4"] = "ESP32 CPU clock (MHz)"
st["B4"] = 240
for a in ("A3", "A4"):
    st[a].font = BOLD
for a in ("B3", "B4"):
    st[a].font = BLUE
    st[a].fill = YFILL
st["C3"] = "Board oscillator: 1 clock = 37.04 ns. Every Tang time in this book is a clock count divided by this."
st["C4"] = "ESP32 CPU clock as set for these runs (240 MHz). Change it here and every cycle figure follows."
st["A6"] = "Tang ns per clock"
st["B6"] = f"=1000/{TANG}"
st["A7"] = "ESP32 ns per cycle"
st["B7"] = f"=1000/{ESP}"
st["A8"] = "Clock ratio ESP32 / Tang"
st["B8"] = f"={ESP}/{TANG}"
for a in ("A6", "A7", "A8"):
    st[a].font = BOLD
for a in ("B6", "B7", "B8"):
    st[a].font = BLK
    st[a].number_format = "0.00"
st["A10"] = ("Yellow cells are inputs (blue = typed from a source, black = formula, green = link to another sheet). "
             "Alan's idea that the flex designs run at half clock is NOT used: it is not written in the notes; "
             "the Tang times here use the 27 MHz clock the counters actually ran on.")
st["A10"].font = BLK
st["A10"].alignment = WRAP
st.merge_cells("A10:F12")
st.column_dimensions["A"].width = 30
st.column_dimensions["B"].width = 12
st.column_dimensions["C"].width = 90

# ------------------------------------------------------------------ T2 / T3 (UniCell response time)
ws = wb.create_sheet("T2-T3 UniCell latency")
title(ws, "T2 / T3: UniCell response to an edge (counted on the Tang, 27 MHz clock)",
      "Direct sensor mode samples the input once per 1 ms (27,000 clocks). Column 'own part' is the design after the sample.")
names = ["Test", "Build", "Load running", "Events", "Time-outs",
         "Edge->result min (clk)", "Edge->result max (clk)", "Edge->result avg (clk)",
         "Edge->result min (us)", "Edge->result max (us)", "Edge->result avg (us)",
         "Own part min (clk)", "Own part max (clk)", "Own part (us)", "Own part in ESP32 cycles (same time)",
         "Both-input events", "Source file"]
head(ws, 4, names, [8, 11, 9, 8, 9, 12, 12, 12, 11, 11, 11, 10, 10, 10, 16, 10, 62])
r = 5
src2, t2 = rd("fpga/board_tests_latency_v2/card_run_18oct/board_results.txt")
src3, t3 = rd("fpga/board_tests_latency3/card_run_18oct/board_results.txt")


def block(text, name):
    m = re.search(r"=== " + name + r":.*?(?=\n=== |\nidle against|\Z)", text, re.S)
    return m.group(0)


def mm(b, tag):
    m = re.search(r"\n\s+" + tag + r"\s+min\s+(\d+) clk .*?max\s+(\d+) clk .*?avg\s+([\d.]+) clk", b)
    return int(m.group(1)), int(m.group(2)), float(m.group(3))


for test, text, src, name, loadflag, a_tag, b_tag in [
    ("T2 rising", t2, src2, "lat_busy", "yes", "rA", "rB"),
    ("T2 rising", t2, src2, "lat_idle", "no", "rA", "rB"),
    ("T2 falling", t2, src2, "lat_busy", "yes", "fA", "fB"),
    ("T2 falling", t2, src2, "lat_idle", "no", "fA", "fB"),
    ("T3 one input", t3, src3, "lt3_busy", "yes", "sA", "sB"),
    ("T3 one input", t3, src3, "lt3_idle", "no", "sA", "sB"),
    ("T3 both inputs", t3, src3, "lt3_busy", "yes", "dA", "dB"),
    ("T3 both inputs", t3, src3, "lt3_idle", "no", "dA", "dB"),
]:
    b = block(text, name)
    ev = int(re.search(r"events (\d+)", b).group(1))
    to = int(re.search(r"time-outs (\d+)", b).group(1))
    amin, amax, aavg = mm(b, a_tag)
    bmin, bmax, bavg = mm(b, b_tag)
    both = re.search(r"both-input events (\d+)", b)
    put(ws, r, 1, test)
    put(ws, r, 2, name)
    put(ws, r, 3, loadflag)
    put(ws, r, 4, ev, BLUE)
    put(ws, r, 5, to, BLUE)
    put(ws, r, 6, amin, BLUE, "#,##0")
    put(ws, r, 7, amax, BLUE, "#,##0")
    put(ws, r, 8, aavg, BLUE, "#,##0.0")
    put(ws, r, 9, f"=F{r}/{TANG}", BLK, "#,##0.000")
    put(ws, r, 10, f"=G{r}/{TANG}", BLK, "#,##0.000")
    put(ws, r, 11, f"=H{r}/{TANG}", BLK, "#,##0.000")
    put(ws, r, 12, bmin, BLUE)
    put(ws, r, 13, bmax, BLUE)
    put(ws, r, 14, f"=L{r}/{TANG}", BLK, "0.000")
    put(ws, r, 15, f"=N{r}*{ESP}", BLK, "0.0")
    put(ws, r, 16, int(both.group(1)) if both and test == "T3 both inputs" else None, BLUE)
    put(ws, r, 17, rel(src))
    r += 1
T23_FIRST, T23_LAST = 5, r - 1
ws[f"A{r+1}"] = ("Reading: 'Own part' is identical (8 clocks, min = max) in idle and busy builds, so the load did not change it. "
                 "Edge->result includes waiting for the next 1 ms sample, so it spans about 0 to 1,000 us; for 'both inputs' it also includes the gap between the two edges.")
ws[f"A{r+1}"].font = BLK
ws.freeze_panes = "C5"

# ------------------------------------------------------------------ C1 v1 (Tang counted, from ledger)
v1 = wb.create_sheet("C1 v1 ESP32 answer")
title(v1, "C1 version 1: how fast the ESP32 answers an edge from the Tang (answer time counted by the Tang, 27 MHz)",
      "Typed from the result lines recorded in ledger #1214-#1216 (files in fpga/board_tests_c1/card_run_18oct). Clock counts are the originals.")
names = ["Run", "ESP32 compute loop", "Tang build", "Events", "Time-outs",
         "Rise min (clk)", "Rise max (clk)", "Rise avg (clk)", "Fall min (clk)", "Fall max (clk)", "Fall avg (clk)",
         "Rise avg (us)", "Fall avg (us)", "Max (us)", "Avg in ESP32 cycles (rise)",
         "< 2 us", "2-5 us", "5-10 us", "10-20 us", "20-50 us", ">= 50 us", "Share >= 2 us", "Share >= 5 us", "Source file"]
head(v1, 4, names, [6, 10, 24, 8, 9, 9, 9, 9, 9, 9, 9, 10, 10, 9, 12, 8, 8, 8, 8, 8, 8, 10, 10, 54])
rows = [
    ("A", "ON", "c1_quiet (no storm)", 4096, 0, 32, 110, 51.2, 36, 111, 52.2, 4031, 65, 0, 0, 0, 0),
    ("B", "ON", "c1_storm (storm)", 4096, 1, 20, 252, 58.6, 1, 210, 58.9, 3611, 315, 169, 0, 0, 0),
    ("C", "OFF", "c1_quiet (no storm)", 4096, 0, 51, 172, 56.4, 30, 170, 56.9, 12, 4076, 8, 0, 0, 0),
    ("D", "OFF", "c1_storm (storm)", 4096, 2, 1, 216, 62.7, 1, 209, 63.4, 194, 3708, 192, 0, 0, 0),
]
srcs = ["card_run_18oct/loopON_run2/board_results_loopON.txt"] * 2 + ["card_run_18oct/loopOFF/board_results_loopOFF.txt"] * 2
for i, row in enumerate(rows):
    rr = 5 + i
    for j, v in enumerate(row[:11], 1):
        put(v1, rr, j, v, BLUE if j >= 4 else BLK)
    put(v1, rr, 12, f"=H{rr}/{TANG}", BLK, "0.00")
    put(v1, rr, 13, f"=K{rr}/{TANG}", BLK, "0.00")
    put(v1, rr, 14, f"=MAX(G{rr},J{rr})/{TANG}", BLK, "0.00")
    put(v1, rr, 15, f"=L{rr}*{ESP}", BLK, "0")
    for j, v in enumerate(row[11:17], 16):
        put(v1, rr, j, v, BLUE)
    put(v1, rr, 22, f"=SUM(Q{rr}:U{rr})/SUM(P{rr}:U{rr})", BLK, "0.0%")
    put(v1, rr, 23, f"=SUM(R{rr}:U{rr})/SUM(P{rr}:U{rr})", BLK, "0.0%")
    put(v1, rr, 24, "fpga/board_tests_c1/" + srcs[i])
v1["A10"] = ("A 1-clock minimum in runs B and D is a stopwatch artifact after an unanswered edge (ledger #1215, #1216); those events sit in '< 2 us'. "
             "Run A/B storm build: ledger #1214 found no storm reaching the ESP32 in its first storm run (wire), so only #1215/#1216 storm numbers are used.")
v1["A10"].font = BLK
v1.freeze_panes = "D5"

# ------------------------------------------------------------------ C1 v2/v3 runs
cr = wb.create_sheet("C1 v2-v3 runs")
title(cr, "C1 versions 2 and 3: every run, quiet and storm (answer time counted by the Tang, 27 MHz; storm = ESP32 pin IO21 edges every 26-102 us)",
      "All values parsed from the saved result files by tools/make_comparison_sheet_v1.py. Unanswered = Tang waited and the ESP32 never changed the answer pin.")
names = ["Ledger", "Run label", "Sketch", "ESP32 compute loop", "Storm work per interrupt (us)", "Tang build",
         "Result", "Timed events", "Unanswered rising", "Unanswered falling", "Unanswered total",
         "Rise avg (us)", "Fall avg (us)", "Max (us)", "Avg in ESP32 cycles (rise)",
         "< 2 us", "2-5 us", "5-10 us", "10-20 us", "20-50 us", ">= 50 us", "Share >= 5 us", "Share >= 10 us",
         "ESP32 edge-handler runs", "ESP32 storm interrupts", "Source file"]
head(cr, 4, names, [7, 10, 7, 9, 11, 12, 7, 9, 10, 10, 10, 9, 9, 8, 12, 8, 8, 8, 8, 8, 8, 9, 9, 11, 12, 66])
runs = [
    (1219, "loopON", "card_run_18oct_loopON", "v2", "OFF", 6),
    (1220, "loop1", "card_run_18oct_loop1", "v2", "ON", 6),
    (1221, "loop1_b", "card_run_18oct_loop1_b", "v2", "ON", 6),
    (1222, "w20a", "card_run_18oct_w20a", "v2", "not logged", 20),
    (1223, "w20b", "card_run_18oct_w20b", "v2", "ON", 20),
    (1226, "v3a", "card_run_18oct_v3a", "v3", "ON", 6),
    (1227, "v3b", "card_run_18oct_v3b", "v3", "ON", 6),
    (1228, "v3c", "card_run_18oct_v3c", "v3", "ON", 6),
    (1229, "v3d", "card_run_18oct_v3d", "v3", "ON", 20),
    (1230, "v3d_b", "card_run_18oct_v3d_b", "v3", "ON", 20),
    (1231, "v3e", "card_run_18oct_v3e", "v3", "OFF", 20),
]
r = 5
for led, lab, folder, sk, loop, work in runs:
    path = glob.glob(os.path.join(ROOT, "fpga/board_tests_c1_v2", folder, "*board_results*.txt"))
    if not path:
        raise SystemExit("missing " + folder)
    path = path[0]
    t = open(path).read()
    for b in re.split(r"\n(?==== c1_)", t):
        m = re.match(r"=== (c1_\w+): (\w)\s+timed events (\d+) of 4096\s+unanswered: rising (\d+), falling (\d+)", b)
        if not m:
            continue
        rise = re.search(r"rising edge -> answer.*?max\s+(\d+) clk .*?avg\s+([\d.]+) clk", b)
        fall = re.search(r"falling edge -> answer.*?max\s+(\d+) clk .*?avg\s+([\d.]+) clk", b)
        h = [int(x) for x in re.search(
            r"< 2 us: (\d+).*?2-5 us: (\d+).*?5-10 us: (\d+).*?10-20 us: (\d+).*?20-50 us: (\d+).*?>= 50 us: (\d+)", b, re.S).groups()]
        e = re.search(r"ESP32 counted (\d+) edge interrupts", b)
        s = re.search(r"ESP32 counted (\d+) storm interrupts", b)
        put(cr, r, 1, led)
        put(cr, r, 2, lab)
        put(cr, r, 3, sk)
        put(cr, r, 4, loop)
        put(cr, r, 5, work, BLUE)
        put(cr, r, 6, m.group(1))
        put(cr, r, 7, m.group(2), BLUE)
        put(cr, r, 8, int(m.group(3)), BLUE, "#,##0")
        put(cr, r, 9, int(m.group(4)), BLUE)
        put(cr, r, 10, int(m.group(5)), BLUE)
        put(cr, r, 11, f"=I{r}+J{r}", BLK)
        put(cr, r, 12, float(rise.group(2)) / 27.0, BLUE, "0.00")  # avg clk -> us via the clock in Settings below
        cr.cell(row=r, column=12).value = f"={float(rise.group(2))}/{TANG}"
        cr.cell(row=r, column=13).value = f"={float(fall.group(2))}/{TANG}"
        put(cr, r, 13, cr.cell(row=r, column=13).value, BLK, "0.00")
        cr.cell(row=r, column=12).font = BLK
        put(cr, r, 14, f"=MAX({int(rise.group(1))},{int(fall.group(1))})/{TANG}", BLK, "0.00")
        put(cr, r, 15, f"=L{r}*{ESP}", BLK, "0")
        for j, v in enumerate(h, 16):
            put(cr, r, j, v, BLUE)
        put(cr, r, 22, f"=SUM(R{r}:U{r})/SUM(P{r}:U{r})", BLK, "0.0%")
        put(cr, r, 23, f"=SUM(S{r}:U{r})/SUM(P{r}:U{r})", BLK, "0.0%")
        put(cr, r, 24, int(e.group(1)) if e else None, BLUE, "#,##0")
        put(cr, r, 25, int(s.group(1)) if s else None, BLUE, "#,##0")
        put(cr, r, 26, rel(path))
        r += 1
C1_FIRST, C1_LAST = 5, r - 1
cr[f"A{r+1}"] = ("Notes: #1222 had no ESP32 log (port flag missing) so loop state and handler counts are not logged. In #1221 and #1229 the quiet ESP32 count is "
                 "a capture shortfall, not lost edges (ledger #1221, #1229). The compute loop was OFF in #1219 (folder name says loopON by mistake) and #1231. "
                 "Storm = 'c1_storm' builds. Units: Rise/Fall avg and Max in us are clock counts divided by the Tang clock in Settings.")
cr[f"A{r+1}"].font = BLK
cr.freeze_panes = "G5"

# ------------------------------------------------------------------ C2 ESP32 threads
c2 = wb.create_sheet("C2 ESP32 threads")
title(c2, "C2: ESP32 threads against the watched job (ledger #1213) and the Tang counterpart",
      "Each device compared with itself (single thread against several). Numbers typed from ledger #1213; Tang counterpart from #1180/#1181 (T1/T4).")
head(c2, 4, ["Case", "Cores used", "Threads", "Watched job avg (us)", "Jobs per second (all cores)",
             "Slowdown vs 1 thread", "Watched job in ESP32 cycles", "Source"], [26, 12, 9, 14, 14, 12, 16, 40])
c2rows = [
    ("1 thread", "core 1", 1, 4388, 227),
    ("2 threads, one core", "core 1", 2, 8806, 226),
    ("4 threads, one core", "core 1", 4, 17606, 226),
    ("8 threads, one core", "core 1", 8, 35206, 226),
    ("2 threads, both cores", "both", 2, 4412, 453),
    ("4 threads, both cores", "both", 4, 8812, 453),
    ("8 threads, both cores", "both", 8, 17606, 453),
]
for i, row in enumerate(c2rows):
    rr = 5 + i
    put(c2, rr, 1, row[0])
    put(c2, rr, 2, row[1])
    put(c2, rr, 3, row[2], BLUE)
    put(c2, rr, 4, row[3], BLUE, "#,##0")
    put(c2, rr, 5, row[4], BLUE)
    put(c2, rr, 6, f"=D{rr}/$D$5", BLK, "0.00")
    put(c2, rr, 7, f"=D{rr}*{ESP}", BLK, "#,##0")
    put(c2, rr, 8, "ledger #1213")
c2["A14"] = "Tang counterpart (T1/T4, ledger #1180, #1181): the same small job took"
c2["A14"].font = BOLD
c2["A15"] = "Clocks, alone / beside 4 and 8 storm lanes / 4 copies at once"
c2["D15"] = 131
c2["D15"].font = BLUE
c2["A16"] = "Time (us)"
c2["D16"] = f"=D15/{TANG}"
c2["D16"].number_format = "0.00"
c2["A17"] = "Not the same job as the ESP32's (different size), so only the flatness is compared, not the absolute speed."
for a in ("A15", "A16", "A17"):
    c2[a].font = BLK
c2.freeze_panes = "B5"

# ------------------------------------------------------------------ T4 UniCell pulse
tp = wb.create_sheet("T4 UniCell pulse")
title(tp, "T4: how short a pulse the UniCell input catches (512 pulses per width, Tang drives itself via the jumper)",
      "Caught chance should be about width / 27,000 clocks (the 1 ms sampling window), up to 100%.")
head(tp, 4, ["Width (us)", "Width (clocks)", "Width in ESP32 cycles", "Idle build caught", "Busy build caught", "Pulses per width",
             "Idle caught %", "Busy caught %", "Expected % (width / 1 ms)", "Idle minus expected (points)", "Busy minus idle (pulses)"],
     [11, 11, 12, 11, 11, 11, 11, 11, 13, 13, 13])
srcp, tpx = rd("fpga/board_tests_pulse/card_run_18oct_a/*board_results_a.txt")
vals = {}
for name in ("pls_idle", "pls_busy"):
    b = block(tpx, name)
    vals[name] = [(float(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
                  for m in re.finditer(r"^\s*([\d.]+) us\s+(\d+)\s+(\d+)\s+(\d+)\s", b, re.M)]
for i, (w, clk, caught, of) in enumerate(vals["pls_idle"]):
    rr = 5 + i
    cb = vals["pls_busy"][i][2]
    put(tp, rr, 1, w, BLUE, "#,##0.00")
    put(tp, rr, 2, clk, BLUE, "#,##0")
    put(tp, rr, 3, f"=A{rr}*{ESP}", BLK, "#,##0")
    put(tp, rr, 4, caught, BLUE)
    put(tp, rr, 5, cb, BLUE)
    put(tp, rr, 6, of, BLUE)
    put(tp, rr, 7, f"=D{rr}/F{rr}", BLK, "0.0%")
    put(tp, rr, 8, f"=E{rr}/F{rr}", BLK, "0.0%")
    put(tp, rr, 9, f"=MIN(1,B{rr}/27000)", BLK, "0.0%")
    put(tp, rr, 10, f"=(G{rr}-I{rr})*100", BLK, "0.0")
    put(tp, rr, 11, f"=E{rr}-D{rr}", BLK)
T4_FIRST, T4_LAST = 5, 5 + len(vals["pls_idle"]) - 1
tp[f"A{T4_LAST+2}"] = (f"Source: {rel(srcp)}. 27,000 in column I is the 1 ms sampling window in clocks (T2). Idle and busy builds catch the same pulses at every width.")
tp[f"A{T4_LAST+2}"].font = BLK
tp.freeze_panes = "B5"

# ------------------------------------------------------------------ P1 ESP32 pulse
pp = wb.create_sheet("P1 ESP32 pulse")
title(pp, "P1: how short a pulse the ESP32 catches (512 pulses per width, Tang drives; ESP32 rising-edge handler toggles an answer pin)",
      "Caught = answer pin changed 185 us after the pulse. Storm = 15,670 other interrupts per second on IO21 with 6 us of work each, compute loop on.")
head(pp, 4, ["Width (ns)", "Width (Tang clocks)", "Width in ESP32 cycles", "Quiet caught", "Storm caught", "Pulses per width",
             "Quiet caught %", "Storm caught %", "Storm lost (pulses)"], [11, 12, 12, 11, 11, 11, 11, 11, 11])
srcq, pq = rd("fpga/board_tests_esp32_pulse/card_run_18oct_a/*board_results_a.txt")
pv = {}
for name in ("pe_quiet", "pe_storm"):
    b = block(pq, name)
    pv[name] = [(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
                for m in re.finditer(r"^\s*(\d+) ns\s+(\d+)\s+(\d+)\s+(\d+)\s", b, re.M)]
for i, (ns, clk, caught, of) in enumerate(pv["pe_quiet"]):
    rr = 5 + i
    put(pp, rr, 1, ns, BLUE, "#,##0")
    put(pp, rr, 2, clk, BLUE, "#,##0")
    put(pp, rr, 3, f"=A{rr}*{ESP}/1000", BLK, "#,##0.0")
    put(pp, rr, 4, caught, BLUE)
    put(pp, rr, 5, pv["pe_storm"][i][2], BLUE)
    put(pp, rr, 6, of, BLUE)
    put(pp, rr, 7, f"=D{rr}/F{rr}", BLK, "0.0%")
    put(pp, rr, 8, f"=E{rr}/F{rr}", BLK, "0.0%")
    put(pp, rr, 9, f"=F{rr}-E{rr}", BLK)
P1_FIRST, P1_LAST = 5, 5 + len(pv["pe_quiet"]) - 1
rr = P1_LAST + 1
put(pp, rr, 1, "Total", BOLD)
put(pp, rr, 4, f"=SUM(D{P1_FIRST}:D{P1_LAST})", BOLD)
put(pp, rr, 5, f"=SUM(E{P1_FIRST}:E{P1_LAST})", BOLD)
put(pp, rr, 6, f"=SUM(F{P1_FIRST}:F{P1_LAST})", BOLD)
put(pp, rr, 7, f"=D{rr}/F{rr}", BOLD, "0.00%")
put(pp, rr, 8, f"=E{rr}/F{rr}", BOLD, "0.00%")
put(pp, rr, 9, f"=F{rr}-E{rr}", BOLD)
P1_TOT = rr
pp[f"A{rr+2}"] = (f"Source: {rel(srcq)}. ESP32 handler runs counted: quiet 6,152 of 6,152 sent; storm 6,149 of 6,152 sent (-3), with 149,167 storm interrupts. "
                  "The smallest width, 37 ns, is one Tang clock; the ESP32 pin and wire may stretch it, so this is a limit of what the Tang can send, not of the ESP32.")
pp[f"A{rr+2}"].font = BLK
pp.freeze_panes = "B5"

# ------------------------------------------------------------------ Summary
sm["A1"] = "UniCell (Tang Nano 20K) against ESP32: measured results side by side"
sm["A1"].font = TITLE
sm["A2"] = ("Both devices measured on the same bench with the same wires and a Tang counter (27 MHz) as the clock for the ESP32's answer time. "
            "Each row says which side it applies to and the real time and clock count. Nothing here is a guess; see sheets for sources. Ledger #1233.")
sm["A2"].font = BLK
sm["A2"].alignment = WRAP
sm.merge_cells("A2:H3")
head(sm, 5, ["Question", "UniCell: value", "UniCell: unit", "ESP32: value", "ESP32: unit",
             "UniCell in ESP32 cycles / ESP32 in Tang clocks", "What it shows", "Where from"],
     [46, 14, 16, 14, 16, 22, 70, 30])
sm.row_dimensions[5].height = 45


def srow(r, q, uv, uu, ev, eu, conv, why, where, ufmt="0.00", efmt="0.00"):
    put(sm, r, 1, q).alignment = WRAP
    c = put(sm, r, 2, uv, GREEN if isinstance(uv, str) and uv.startswith("=") else BLK, ufmt)
    put(sm, r, 3, uu)
    c = put(sm, r, 4, ev, GREEN if isinstance(ev, str) and str(ev).startswith("=") else BLK, efmt)
    put(sm, r, 5, eu)
    put(sm, r, 6, conv, BLK, "#,##0.0")
    put(sm, r, 7, why).alignment = WRAP
    put(sm, r, 8, where).alignment = WRAP
    sm.row_dimensions[r].height = 48


T = "'T2-T3 UniCell latency'"
C = "'C1 v2-v3 runs'"
V = "'C1 v1 ESP32 answer'"
r = 6
# 1 response to an edge, own part
srow(r, "Answer time after an edge: the logic's own part",
     f"={T}!N{T23_FIRST}", "us (8 clocks, fixed)",
     f"=AVERAGEIFS({C}!L{C1_FIRST}:L{C1_LAST},{C}!F{C1_FIRST}:F{C1_LAST},\"c1_quiet\",{C}!D{C1_FIRST}:D{C1_LAST},\"ON\")",
     "us avg, quiet, loop on",
     f"=B{r}*{ESP}",
     "UniCell's own part is a constant 8 clocks, same idle and busy. The ESP32 figure is its interrupt answer (rising edge to answer pin) averaged over quiet loop-on runs; it has a spread (min-max in the runs sheet).",
     "T2 sheet; C1 v2-v3 runs")
sm.cell(row=r, column=6).value = f"=B{r}*{ESP}"
r += 1
srow(r, "Answer time after an edge: UniCell including the 1 ms sampling wait (average)",
     f"={T}!K{T23_FIRST}", "us avg (0 - 1,000 us range)",
     f"=AVERAGEIFS({C}!L{C1_FIRST}:L{C1_LAST},{C}!F{C1_FIRST}:F{C1_LAST},\"c1_quiet\",{C}!D{C1_FIRST}:D{C1_LAST},\"ON\")",
     "us avg, quiet, loop on",
     f"=D{r}*{TANG}",
     "In direct sensor mode the UniCell only looks once per millisecond, so its average edge-to-result is about half a millisecond; the ESP32's interrupt answers in about 2 us. At the edge the ESP32 wins on average time.",
     "T2 sheet; C1 v2-v3 runs", "#,##0.0")
r += 1
srow(r, "Answer time: worst case seen",
     f"={T}!J{T23_FIRST}", "us (max over 2,048 events)",
     f"=MAX({C}!N{C1_FIRST}:N{C1_LAST})", "us (max over all C1 v2-v3 runs)",
     f"=D{r}*{TANG}",
     "UniCell worst case is bounded by the sampling window (1 ms). ESP32 worst case grew to about 24 us when the interrupt storm carried 20 us of work per interrupt.",
     "T2 sheet; C1 v2-v3 runs", "#,##0.0", "#,##0.0")
r += 1
srow(r, "Does load change the answer? (quiet -> storm)",
     "none", "own part 8 clocks in idle and busy builds",
     f"=AVERAGEIFS({C}!L{C1_FIRST}:L{C1_LAST},{C}!F{C1_FIRST}:F{C1_LAST},\"c1_storm\",{C}!E{C1_FIRST}:E{C1_LAST},6)/AVERAGEIFS({C}!L{C1_FIRST}:L{C1_LAST},{C}!F{C1_FIRST}:F{C1_LAST},\"c1_quiet\",{C}!E{C1_FIRST}:E{C1_LAST},6)",
     "x avg answer time, storm / quiet (6 us work)",
     None,
     "UniCell: the load is inside the chip and its answer time did not move (same min and max). ESP32: the same interrupt takes longer with a storm (about 1.1x with 6 us of work, about 2.7x with 20 us), and the tail grows.",
     "T2 sheet; C1 v2-v3 runs", "@", "0.00")
r += 1
srow(r, "Edges the device did not answer in storm runs (total, all storm runs)",
     0, "not applicable: UniCell has no handler to miss (no counter for this was built)",
     f"=SUMIFS({C}!K{C1_FIRST}:K{C1_LAST},{C}!F{C1_FIRST}:F{C1_LAST},\"c1_storm\")",
     "unanswered edges",
     None,
     "Quiet runs: no unanswered edge in 11 runs. Storm runs: 0 to 3 per run of 4,096 events. Level-check sketch v3 matched each unanswered edge with a missing handler run. Cause of the missing run is not known.",
     "C1 v2-v3 runs", "0", "0")
sm.cell(row=r, column=2).value = "n/a"
r += 1
srow(r, "Share of answers slower than 10 us, storm with 20 us work",
     "n/a", "",
     f"=SUMIFS({C}!S{C1_FIRST}:S{C1_LAST},{C}!F{C1_FIRST}:F{C1_LAST},\"c1_storm\",{C}!E{C1_FIRST}:E{C1_LAST},20)/SUMIFS({C}!H{C1_FIRST}:H{C1_LAST},{C}!F{C1_FIRST}:F{C1_LAST},\"c1_storm\",{C}!E{C1_FIRST}:E{C1_LAST},20)+SUMIFS({C}!T{C1_FIRST}:T{C1_LAST},{C}!F{C1_FIRST}:F{C1_LAST},\"c1_storm\",{C}!E{C1_FIRST}:E{C1_LAST},20)/SUMIFS({C}!H{C1_FIRST}:H{C1_LAST},{C}!F{C1_FIRST}:F{C1_LAST},\"c1_storm\",{C}!E{C1_FIRST}:E{C1_LAST},20)",
     "of answers (10-50 us buckets)",
     None,
     "The ESP32's answer time spreads out under heavy interrupt load; the UniCell's own part cannot spread.",
     "C1 v2-v3 runs", "@", "0.0%")
r += 1
srow(r, "Shortest pulse caught every time (512 of 512)",
     f"=INDEX('T4 UniCell pulse'!A{T4_FIRST}:A{T4_LAST},2)", "us (= 27,000 clocks, the sampling window)",
     f"=INDEX('P1 ESP32 pulse'!A{P1_FIRST}:A{P1_LAST},COUNTIFS('P1 ESP32 pulse'!G{P1_FIRST}:G{P1_LAST},1))/1000",
     "us (shortest width with 100% caught, quiet)",
     f"=B{r}*{ESP}",
     "UniCell in direct sensor mode is certain only for pulses at least 1 ms long; shorter pulses are caught with probability width / 1 ms. The ESP32 caught every pulse down to the shortest the Tang can send (1 clock = 37 ns) when quiet. The 37 ns floor is the narrowest pulse the Tang can send, so the ESP32 limit is not found.",
     "T4 sheet; P1 sheet", "#,##0.0", "0.000")
r += 1
srow(r, "Pulses caught: 100 us wide (percent)",
     f"=INDEX('T4 UniCell pulse'!G{T4_FIRST}:G{T4_LAST},6)", "of 512 pulses",
     f"=INDEX('P1 ESP32 pulse'!G{P1_FIRST}:G{P1_LAST},1)", "of 512 pulses (quiet)",
     None,
     "At 100 us the UniCell sees about 8% of pulses and the ESP32 all of them.",
     "T4 sheet; P1 sheet", "0.0%", "0.0%")
r += 1
srow(r, "Pulses caught under storm, all widths together",
     "(same as idle: no load effect)", "",
     f"='P1 ESP32 pulse'!H{P1_TOT}", "of 6,144 pulses",
     None,
     "Under the storm the ESP32 missed 3 of 6,144 pulses (widths 100 us, 5 us, 148 ns); the UniCell build with a busy load caught exactly the same pulses as idle.",
     "T4 sheet; P1 sheet", "@", "0.00%")
r += 1
srow(r, "Throughput of 8 threads on one core vs one thread (slowdown of the watched job)",
     "flat (131 clocks, alone, beside storm lanes, 4 copies)", "",
     "='C2 ESP32 threads'!F8", "x slower on one core",
     None,
     "Each device compared with itself. ESP32: eight threads stretch the watched job eightfold; the second core doubles total throughput. UniCell: the same job takes 131 clocks regardless of neighbours (up to 8 storm lanes or 4 copies tested).",
     "C2 sheet; ledger #1180/#1181", "@", "0.00")
SUM_LAST = r
r += 2
sm.cell(row=r, column=1, value="Scope and honest limits").font = BOLD
lim = [
    "1. UniCell edge response was measured in direct sensor mode (1 ms sampling) only. A faster sampling stage was not examined.",
    "2. ESP32 numbers are for the plain Arduino interrupt (attachInterrupt, IRAM handler) at 240 MHz, not a hand-tuned assembly handler.",
    "3. Tang clock counts have 37 ns resolution; ESP32 answer times are therefore reported to about 0.04 us at best.",
    "4. Missed edges under storm: cause unknown. Each missed edge matched a missing handler run (v3 sketch evidence); the reason the handler did not run has not been established.",
    "5. One board of each, one bench, one afternoon; repeated runs show how the storm result varies (0 to 3 unanswered per run), so single runs should not be read as exact rates.",
    "6. This comparison is about the UniCell at its edges (input sampling) and the ESP32 inside (interrupts and threads). The UniCell internals under load were measured separately (T1/T4, 131 clocks every time).",
]
for i, t_ in enumerate(lim):
    c = sm.cell(row=r + 1 + i, column=1, value=t_)
    c.font = BLK
sm.freeze_panes = "B6"

os.makedirs(OUT_DIR, exist_ok=True)
wb.save(OUT)
print("saved", OUT)
