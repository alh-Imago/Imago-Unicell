"""Tests for tools/kintex_carrier_scale_v1.py and kintex_carrier_scale_report_v1.py (ledger #1319).

The generator makes a grid of full VIXeN carriers for the Kintex size/speed build. These tests check that the folder is complete, the top elaborates and RUNS in
iverilog with the LEDs actually changing (so the logic is live), the grid wiring has the right neighbours, and the log reader takes the last timing report.
The utilisation line used in the log-reader test is an ASSUMED format (nextpnr-xilinx output was not available here); the reader is written to be lenient about it.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kintex_carrier_scale_v1 as g
import kintex_carrier_scale_report_v1 as rep


class T(unittest.TestCase):
    def test_grid_shape(self):
        self.assertEqual(g.grid_shape(1), (1, 1))
        self.assertEqual(g.grid_shape(4), (2, 2))
        self.assertEqual(g.grid_shape(9), (3, 3))
        self.assertEqual(g.grid_shape(5), (2, 3))
        r, c = g.grid_shape(30)
        self.assertGreaterEqual(r * c, 30)

    def test_folder_files_and_wiring(self):
        tmp = tempfile.mkdtemp()
        try:
            out, proj = g.make_folder(4, tmp, 100)
            for need in ("Makefile", "kit.json", "README.md", proj + ".v", proj + ".xdc", "unicell_vixen_v1.v"):
                self.assertTrue(os.path.exists(os.path.join(out, need)), need)
            mk = open(os.path.join(out, "Makefile")).read()
            self.assertIn("include ../openXC7.mk", mk)
            self.assertIn("unicell_vixen_v1.v", mk)
            xdc = open(os.path.join(out, proj + ".xdc")).read()
            self.assertIn("create_clock -period 10.000", xdc)
            self.assertIn("AA28", xdc)
            v = open(os.path.join(out, proj + ".v")).read()
            # cell 0 (0,0): its east input is cell 1's west output; its south input is cell 2's north output
            self.assertIn(".data_in_e(d1_w)", v)
            self.assertIn(".data_in_s(d2_n)", v)
            # cell 3 (1,1): north input from cell 1's south output, west input from cell 2's east output
            self.assertIn(".data_in_n(d1_s)", v)
            self.assertIn(".data_in_w(d2_e)", v)
            self.assertEqual(v.count("unicell_vixen_v1 #("), 4)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @unittest.skipUnless(shutil.which("iverilog"), "iverilog missing")
    def test_elaborates_and_leds_toggle(self):
        tmp = tempfile.mkdtemp()
        try:
            out, proj = g.make_folder(2, tmp, 100)
            tb = os.path.join(tmp, "tb.v")
            open(tb, "w").write("`timescale 1ns/1ps\nmodule tb; reg clk=0; always #5 clk=~clk; wire a,b,c; top t(.CLK(clk),.LED0(a),.LED1(b),.LED2(c));\n"
                                " integer tg=0; reg la=0; always @(posedge clk) begin if (a!==la) tg=tg+1; la<=a; end\n"
                                " initial begin #300000; $display(\"TOGGLES %0d\", tg); $finish; end endmodule\n")
            exe = os.path.join(tmp, "s.vvp")
            files = [os.path.join(out, f) for f in sorted(os.listdir(out)) if f.endswith(".v")]
            c = subprocess.run(["iverilog", "-g2012", "-o", exe, tb] + files, capture_output=True, text=True)
            self.assertEqual(c.returncode, 0, c.stderr[:500])
            r = subprocess.run(["vvp", exe], capture_output=True, text=True, timeout=600)
            m = re.search(r"TOGGLES (\d+)", r.stdout)
            self.assertTrue(m, r.stdout[-300:])
            self.assertGreater(int(m.group(1)), 100, "LED0 hardly changes: the logic may not be live")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_report_takes_last_timing_block(self):
        log = "\n".join([
            "Info: Device utilisation:",
            "Info:             SLICE_LUTX:  31428/597200     5%",
            "Info:             SLICE_FFX:   22240/1194400    1%",
            "Info: Max frequency for clock 'sys_clk': 61.10 MHz (FAIL at 100.00 MHz)",
            "Info: Max frequency for clock 'sys_clk': 72.50 MHz (FAIL at 100.00 MHz)",
            "fpga-as --part xc7k480tffg1156-1 x.fasm > x.bit",
        ])
        r = rep.parse_log(log)
        self.assertEqual(r["lut"], 31428)
        self.assertEqual(r["lut_total"], 597200)
        self.assertEqual(r["ff"], 22240)
        self.assertTrue(r["bit"])
        self.assertEqual(len(r["fmax"]), 1)
        self.assertAlmostEqual(r["fmax"][0][1], 72.50)
        self.assertEqual(r["fmax"][0][2], "FAIL")

    def test_report_no_bitstream_and_empty(self):
        r = rep.parse_log("Info: Placing..\nERROR: failed to place")
        self.assertFalse(r["bit"])
        self.assertIn("ERROR", r["last"])
        self.assertEqual(r["fmax"], [])


if __name__ == "__main__":
    unittest.main()
