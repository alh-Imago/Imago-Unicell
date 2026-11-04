"""tests/vm/test_hexn_frame_v3_led_v1.py - hexn_frame_v3 (4 Nov 2026) is hexn_frame_v2 with ONE change: at idle led[5:3] show PATTERN_ID[2:0] (active low) so a person can see which pattern a board has loaded after a hop; led[2:0] stay the status lights (off at idle). The UART behaviour is covered by test_hexn_hexcard_v1.py with FRAME=v3 and by the vector tool. This checks the LED value in iverilog for two patterns."""
import glob, os, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_wrgrid_hex_v3 as H, hexn_pattern_gen_hex_v1 as G, hexn_assemble_hex_v2 as A
pytestmark = pytest.mark.skipif(not shutil.which("iverilog"), reason="needs iverilog")
TB = """`timescale 1ns/1ps
module led_tb; reg clk=0; always #5 clk=~clk; wire tx; wire [5:0] led;
hexn_card_top #(.CLKDIV(4)) d(.clk(clk), .uart_rx(1'b1), .uart_tx(tx), .led(led));
initial begin #20000; $display("LED=%b", led); $finish; end endmodule
"""


def _led(n, off):
    H.OFFSET = off; wc = H.Grid12(n, n).work_cells(); ref = G.make_ref("ledt%d" % n, n, n, off, {w: "AL" for w in wc}); H.OFFSET = 0
    d = tempfile.mkdtemp(prefix="led_")
    try:
        A.assemble(ref, d, frame="v3"); open(os.path.join(d, "tb.v"), "w").write(TB)
        subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "t"), os.path.join(d, "tb.v")] + glob.glob(os.path.join(d, "src", "*.v")), check=True, capture_output=True)
        out = subprocess.run(["vvp", os.path.join(d, "t")], check=True, capture_output=True, text=True).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return int(ref["pattern_id"]), [l for l in out.splitlines() if l.startswith("LED=")][0][4:]


@pytest.mark.parametrize("n", [6, 7])
def test_idle_leds_show_the_pattern_id_low_bits(n):
    pid, bits = _led(n, 2)
    assert bits[3:] == "111"                       # status lights off at idle (active low)
    assert int(bits[:3], 2) == (~pid) & 7          # led[5:3] = ~PATTERN_ID[2:0]
