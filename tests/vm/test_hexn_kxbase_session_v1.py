"""tests/vm/test_hexn_kxbase_session_v1.py - several host SESSIONS in a row against the base design behind the real JTAG bridge RTL (rtl/hexn_jtag_bridge_v1.v with the BSCANE2 model), iverilog. Found 5 Nov 2026: on the card, only the first `info` worked; JtagLink computed the sequence number of a new session's first write before it had synced with the card, so it repeated the card's last number and the frame was dropped. The base host starts each session with a read (reset_input_buffer) to avoid that. Simulation only."""
import json, os, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_jtag_host_v1 as J, hexn_kxbase_host_v1 as H
pytestmark = pytest.mark.skipif(not shutil.which("iverilog"), reason="needs iverilog")
WRAP = """module hexn_arr_core_w (input wire clk, input wire [7:0] rx_d, input wire rx_v, output wire [7:0] tx_d, output wire tx_s, input wire tx_b, output wire [5:0] led);
    hexn_arr_core c (.clk(clk), .rx_d(rx_d), .rx_v(rx_v), .tx_dout(tx_d), .tx_s(tx_s), .tx_b(tx_b), .led(led));
endmodule
"""


@pytest.fixture(scope="module")
def vvp():
    d = tempfile.mkdtemp(prefix="kxsess_"); os.system("python3 %s sim %s %s > /dev/null" % (os.path.join(ROOT, "tools", "hexn_kxbase_v1.py"), os.path.join(ROOT, "docs/hex-n/data/hexrefs/hex5.json"), d))
    open(os.path.join(d, "wrap.v"), "w").write(WRAP); o = os.path.join(d, "o.vvp"); src = sorted(os.path.join(d, "src", f) for f in os.listdir(os.path.join(d, "src")))
    subprocess.run(["iverilog", "-g2012", "-DREALCORE", "-DCORE_MOD=hexn_arr_core_w", "-DFSP=128", "-s", "tb_hexn_jtag_v1", "-o", o, os.path.join(ROOT, "rtl/tb_hexn_jtag_v2.v"), os.path.join(ROOT, "rtl/hexn_jtag_bridge_v1.v"),
                    os.path.join(ROOT, "rtl/sim/bscane2_model.v"), os.path.join(d, "wrap.v")] + src, check=True)
    yield o; shutil.rmtree(d, ignore_errors=True)


def test_three_sessions_in_a_row(vvp):
    ex = J.SimExec(vvp)
    try:
        for _ in range(3):
            link = J.JtagLink(ex.scan, maxpoll=400)
            assert H.info(link) == dict(id="42415345", arrays=1, library_slots=4)
            H.select(link, 0)
    finally:
        ex.close()
