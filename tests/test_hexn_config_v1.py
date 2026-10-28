"""Tests for tools/hexn_config_v1.py: derived settings for the Tang and for a Kintex-like card, the 4096 floor, overrides, the shortcut switch, and the fit refusal."""
import json, os, sys, tempfile
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_config_v1 as C
KINTEX_LIKE = {"capabilities": {"bram": True, "sd_card": False, "pcie_hardware": True}, "device": {"part": "XC7K480T-FFG1156", "bram": {"total": None}}}   # same shape as docs/man/kintex7-ypcb00338.man.json (not present on every branch)
def run(man, *extra):
    if man == "kintex":
        p = os.path.join(tempfile.mkdtemp(), "kintex_like.man.json"); json.dump(KINTEX_LIKE, open(p, "w"))
    else: p = os.path.join(ROOT, "docs/man", man)
    out = tempfile.mkdtemp(); rc = C.main(["--man", p, "--out", out] + list(extra))
    return rc, json.load(open(os.path.join(out, "hexn_config.json"))), open(os.path.join(out, "hexn_config.vh")).read()
def test_tang_defaults():
    rc, j, vh = run("tang-nano-20k.man.json"); s = {k: d["value"] for k, d in j["settings"].items()}
    assert rc == 0 and s["card_tier"] == "sd" and s["ram_tier"] == "sdram" and s["ram_entries"] == 1048576
    assert s["bitmap_bits"] == 65536 and s["batch_sectors"] == 4 and rc == 0
    assert "localparam HEXN_BITMAP_BITS" in vh and "HEXN_SHORTCUT = 0" in vh
def test_floor_and_override_and_shortcut():
    rc, j, vh = run("tang-nano-20k.man.json", "--patterns-on-card", "100", "--shortcut"); s = {k: d for k, d in j["settings"].items()}
    assert s["bitmap_bits"]["value"] == 4096 and s["shortcut"]["value"] is True
    rc, j, _ = run("tang-nano-20k.man.json", "--bitmap-bits", "16000"); assert j["settings"]["bitmap_bits"] == {"value": 16384, "from": "override"}
def test_kintex_needs_bram_size_and_has_no_card_tier():
    try: run("kintex"); assert False
    except SystemExit as e: assert "bram-kbits" in str(e)
    rc, j, _ = run("kintex", "--bram-kbits", "30000", "--ddr-mb", "2048", "--bram-used-blocks", "0", "--patterns-on-card", "1000000")
    s = {k: d["value"] for k, d in j["settings"].items()}
    assert s["card_tier"] == "ram" and s["ram_tier"] == "ddr" and s["bitmap_bits"] > 16384 and s["batch_sectors"] > 2
def test_refuses_when_it_does_not_fit():
    rc, j, _ = run("tang-nano-20k.man.json", "--fast-entries", "200000"); assert rc == 1 and not j["fit"]["fits"]
def test_fast_table_growth_counts_only_beyond_store_v5():
    rc, j, _ = run("tang-nano-20k.man.json"); assert j["fit"]["block_ram_blocks_each"]["fast_table"] == 0
    rc, j, _ = run("tang-nano-20k.man.json", "--fast-entries", "4096"); assert j["fit"]["block_ram_blocks_each"]["fast_table"] == 7
