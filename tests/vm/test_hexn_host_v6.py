"""tests/vm/test_hexn_host_v1.py - the PC-side byte layouts of tools/hexn_host_v1.py equal the ones the simulated card is driven with (tools/hexn_card_sim_v1.py), and the reply parsers read what the frame sends. No serial port needed (3 Nov 2026)."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_host_v6 as H, hexn_card_sim_v1 as S


def _bytes(cmds, clkdiv=8):
    lv, _ = S.encode(cmds, clkdiv); out = []; i = 4 * clkdiv
    while i < len(lv) - 10 * clkdiv:
        if lv[i] == 0:
            out.append(sum(lv[i + clkdiv + clkdiv // 2 + k * clkdiv] << k for k in range(8))); i += 10 * clkdiv
        else: i += 1
    return bytes(out)


def test_command_bytes_equal_the_simulated_drivers():
    img = bytes(range(20))
    assert _bytes([("I",)]) == H.cmd_id() and _bytes([("W",)]) == H.cmd_wipe() and _bytes([("B", img)]) == H.cmd_cfg(img)
    assert _bytes([("D", 3, 0xDEADBEEF)]) == H.cmd_data(3, 0xDEADBEEF) and _bytes([("G", 0b101)]) == H.cmd_go(5) and _bytes([("L",)]) == H.cmd_log()


def test_parsers():
    assert H.parse_id(bytes([1, 0, 2, 0x37, 7])) == dict(pattern_id=0x37020001, rows=7)
    assert H.parse_log(bytes([2, 1, 0x78, 0x56, 0x34, 0x12, 45, 0, 3, 1, 0, 0, 0, 79, 0])) == [(1, 0x12345678, 45), (3, 1, 79)]
    assert H.parse_log(bytes([0])) == []
    with pytest.raises(ValueError): H.parse_id(b"abc")
    with pytest.raises(ValueError): H.parse_log(bytes([1, 0]))


def test_text_is_not_mistaken_for_a_card():
    with pytest.raises(ValueError): H.parse_id(b"t da" + b"t")      # what a text console port sent back on the first board try


def test_suite_logic_against_the_simulated_card(tmp_path, capsys, monkeypatch):
    import json, hexn_assemble_v2 as A
    ref = json.load(open(os.path.join(ROOT, "docs/hex-n/data/patterns/J2U2+BRMG_7_37010001.json")))
    A.assemble(ref, str(tmp_path))
    sim = S.CardSim(str(tmp_path), 8)

    class Fake:
        def __init__(self, *a, **k): self.cmds = []
        def ident(self): return dict(pattern_id=ref["pattern_id"], rows=7)
        def wipe(self): self.cmds = [("W",)]
        def load(self, image): self.cmds.append(("B", bytes(image)))
        def put(self, row, word): self.cmds.append(("D", row, word))
        def go(self, mask): self.cmds.append(("G", mask)); self.cmds.append(("wait", 800))
        def log(self): return sim.run(self.cmds + [("L",)])[-1]
    monkeypatch.setattr(H, "Card", Fake); monkeypatch.setattr(H.time, "sleep", lambda s: None)
    rc = H.main(["suite", "--port", "x", "--ref", os.path.join(ROOT, "docs/hex-n/data/patterns/J2U2+BRMG_7_37010001.json"), "--units", os.path.join(ROOT, "docs/hex-n/data/units/brmg_join_min.unit.json")])
    out = capsys.readouterr().out
    assert rc == 0 and out.count("MATCHES") == 4 and "4 runs, 0 differ" in out, out
