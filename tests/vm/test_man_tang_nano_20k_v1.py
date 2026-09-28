"""
test_man_tang_nano_20k_v1.py -- points.md #887: the MAN file for the Sipeed Tang Nano 20K.

What these tests protect, in order of how much a mistake would cost on real hardware:
  * every PIN in the MAN exists in the chip database's QFN88 table with the recorded location and bank
    (proves the pin is real; it does NOT prove the board is wired that way -- the MAN says so itself);
  * every RESOURCE COUNT is what the chip database says (46 block RAMs, 12 DSP tiles, 648 logic tiles giving
    20,736 LUT4 and 15,552 FF), and the embedded-SDRAM port list is the database's own;
  * the committed MAN and .cst are exactly what the generator produces (no hand edits, no drift);
  * the loaders behave: the fit tool sizes the carrier in LUT4 without touching the Intel path, the VM mirror
    accepts a Gowin MAN, and the Quartus generator refuses one CLEARLY;
  * the MAN does not quietly claim more than was verified.
The chip-database tests skip if `apycula`/`msgpack` are not installed.
"""
import importlib.util
import json
import os
import re
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "nano"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import card_fit_v1 as cf  # noqa: E402
import vm_mirror_v1 as vmm  # noqa: E402
import project_assemble_v1 as pa  # noqa: E402

MAN_PATH = os.path.join(ROOT, "docs", "man", "tang-nano-20k.man.json")
CST_PATH = os.path.join(ROOT, "docs", "man", "tang-nano-20k.cst")
ARRIA_PATH = os.path.join(ROOT, "docs", "man", "mustang-f100-a10.man.json")
GEN_PATH = os.path.join(ROOT, "tools", "man_gen", "gen_tang_nano_20k_man.py")

MAN = json.load(open(MAN_PATH))


def _chipdb():
    pytest.importorskip("apycula")
    pytest.importorskip("msgpack")
    spec = importlib.util.spec_from_file_location("gen_tang_man", GEN_PATH)
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    return gen, gen.load_chipdb()


def _pin_records(node, path=""):
    """Every dict in the MAN that names a package pin and its recorded location."""
    if isinstance(node, dict):
        if "pin" in node and "package_location" in node:
            yield path, node
        for k, v in node.items():
            yield from _pin_records(v, f"{path}.{k}" if path else k)


def test_the_man_has_the_expected_identity_and_blocks():
    assert MAN["vendor"] == "gowin" and MAN["man_version"] == "1.1"
    assert MAN["device"]["part"] == "GW2AR-LV18QN88C8/I7" and MAN["device"]["package"] == "QFN88"
    assert MAN["device"]["logic"]["unit"] == "LUT4" and MAN["device"]["alm_total"] is None
    for block in ("clock", "buttons", "leds", "uart", "spi_flash", "sd_card", "sdram", "jtag", "host_link"):
        assert block in MAN["board"], block
    assert MAN["board"]["clock"]["CLK_27M"]["pin"] == 4 and MAN["board"]["clock"]["CLK_27M"]["freq_hz"] == 27000000


def test_every_pin_exists_in_the_chip_database_with_the_recorded_location_and_bank():
    gen, db = _chipdb()
    qn = db["pinout"][gen.DEVICE_KEY][gen.PACKAGE_KEY]
    records = list(_pin_records(MAN["board"]))
    assert len(records) >= 30, "the pin walk must actually find the pins"
    for path, rec in records:
        loc, funcs = qn[str(rec["pin"])]
        assert rec["package_location"] == loc, f"{path}: pin {rec['pin']} is {loc} in the chip database"
        assert rec["bank"] == db["pin_bank"][loc], f"{path}: bank"
        assert rec["io_standard"] == "LVCMOS33"
        if funcs:
            assert rec["chip_function"] == "/".join(funcs), f"{path}: chip function"


def test_no_package_pin_is_assigned_to_two_different_signals():
    roles = {}
    for path, rec in _pin_records(MAN["board"]):
        roles.setdefault(rec["pin"], set()).add(path)
    clashes = {p: sorted(r) for p, r in roles.items() if len(r) > 1}
    assert not clashes, f"a pin is listed under more than one role: {clashes}"


def test_resource_counts_match_the_chip_database():
    gen, db = _chipdb()
    logic = MAN["device"]["logic"]
    tiles = gen.tiles_of(db, "M")
    assert logic["tiles"] == len(tiles) == 648
    assert logic["lut4_total"] == len(tiles) * 32 == 20736
    assert logic["ff_total"] == len(tiles) * 24 == 15552
    bram_sites = sum(len(c["y_segments"]) for c in MAN["device"]["bram"]["columns"])
    assert bram_sites == MAN["device"]["bram"]["blocks"] == len(gen.tiles_of(db, "B")) == 46
    dsp_sites = sum(len(c["y_segments"]) for c in MAN["device"]["dsp"]["columns"])
    assert dsp_sites == MAN["device"]["dsp"]["total_blocks"] == len(gen.tiles_of(db, "D")) == 12
    assert MAN["device"]["dsp"]["multipliers_18x18"] == 48 == 12 * MAN["device"]["dsp"]["multipliers_per_block_derived"]
    assert MAN["device"]["io"]["banks"] == 8 == len({db["pin_bank"][v[0]] for v in
                                                    db["pinout"][gen.DEVICE_KEY][gen.PACKAGE_KEY].values()})


def test_the_embedded_sdram_ports_are_the_chip_databases_own_and_the_geometry_is_consistent():
    gen, db = _chipdb()
    sd = MAN["device"]["embedded_memory"]["sdram"]
    real = db["sip_cst"][gen.DEVICE_KEY][gen.PACKAGE_KEY]
    assert [p["name"] for p in sd["ports"]] == [r[0] for r in real] and sd["port_count"] == len(real) == 55
    names = [p["name"] for p in sd["ports"]]
    assert sum(n.startswith("IO_sdram_dq[") for n in names) == sd["data_width"] == 32
    assert sum(n.startswith("O_sdram_addr[") for n in names) == sd["row_address_bits"] == 11
    assert sum(n.startswith("O_sdram_ba[") for n in names) == 2 and sd["banks"] == 4
    assert sum(n.startswith("O_sdram_dqm[") for n in names) == 4
    assert sd["banks"] * 2 ** sd["row_address_bits"] * 2 ** sd["column_address_bits_derived"] * sd["data_width"] == sd["bits"]
    assert all(p["io_standard"] == "LVCMOS33" for p in sd["ports"])
    assert sd["board_pins"] is None, "the SDRAM is inside the package: it has no board pins"


def test_the_committed_man_and_constraints_are_exactly_what_the_generator_produces():
    gen, db = _chipdb()
    man = gen.build(db)
    assert json.dumps(man, indent=2) + "\n" == open(MAN_PATH).read(), "docs/man/tang-nano-20k.man.json is stale"
    assert gen.build_cst(man) == open(CST_PATH).read(), "docs/man/tang-nano-20k.cst is stale"


def test_the_constraints_file_agrees_with_the_man_and_uses_no_pin_twice():
    text = open(CST_PATH).read()
    locs = re.findall(r'IO_LOC\s+"([^"]+)"\s+(\d+);', text)
    assert len(locs) >= 25
    pins = [int(p) for _, p in locs]
    assert len(pins) == len(set(pins)), "a package pin is constrained to two ports"
    by_port = {n: int(p) for n, p in locs}
    b = MAN["board"]
    assert by_port["clk"] == b["clock"]["CLK_27M"]["pin"] == 4
    assert by_port["uart_tx"] == b["uart"]["tx"]["pin"] and by_port["uart_rx"] == b["uart"]["rx"]["pin"]
    assert [by_port[f"led_n[{i}]"] for i in range(6)] == [15, 16, 17, 18, 19, 20]
    assert by_port["sd_clk"] == b["sd_card"]["clk"]["pin"] and by_port["flash_cs_n"] == b["spi_flash"]["cs_n"]["pin"]
    assert "sdram" not in " ".join(by_port).lower(), "the embedded SDRAM must not be given board pins"


def test_the_fit_tool_sizes_the_carrier_in_lut4_and_it_does_not_fit_at_the_default_ceiling():
    for shell, expect in (("vix_carrier_v1d", 20736 // 17339), ("vix_carrier_v1", 20736 // 16574)):
        t = cf.target_from_man(MAN_PATH, rows=4, cols=4, shell=shell)
        assert t.cell_budget == expect == 1
        assert t.max_cells == 0, "one carrier position is 80-84% of the LUT4 budget: over the 80% ceiling"
    assert cf.target_from_man(MAN_PATH, rows=4, cols=4, shell="nano_lean").cell_budget == 11
    assert cf.target_from_man(MAN_PATH, rows=4, cols=4, shell="ram_lean").cell_budget == 52
    assert cf.target_from_man(MAN_PATH, rows=4, cols=4, shell="command").cell_budget == 61


def test_the_fit_tool_refuses_an_unmeasured_shell_on_a_lut4_device_and_leaves_the_intel_path_alone():
    with pytest.raises(ValueError, match="LUT4"):
        cf.target_from_man(MAN_PATH, rows=4, cols=4, shell="super_v3")     # an ALM-measured shell, wrong unit
    arria = cf.target_from_man(ARRIA_PATH, rows=4, cols=4, shell="super_v3")
    assert arria.cell_budget == int(251680 // cf.ALM_PER_POSITION["super_v3"]), "the Intel path is unchanged"


def test_the_measured_lut4_table_is_internally_consistent():
    t = cf.LUT4_PER_POSITION
    for cell in ("nano", "ram", "adder", "branch", "accumulator", "compare", "sequencer", "latch", "mul"):
        assert t[f"{cell}_lean"] < t[f"{cell}_full"], f"{cell}: removing the addon chain cannot add area"
    assert t["command"] == 338, "the command cell has no addon chain, so it has no lean form"
    assert t["vix_carrier_v1d"] > t["vix_carrier_v1"], "v1d adds the addon-addressing mechanism"
    assert all(v < MAN["device"]["logic"]["lut4_total"] for v in t.values()), "no single position exceeds the chip"


def test_the_vm_mirror_accepts_a_gowin_man_but_the_quartus_generator_refuses_it_clearly():
    b = vmm.load_mirror_bounds(MAN_PATH, 4)
    assert b.card_id == "sipeed-tang-nano-20k-01" and b.cells == 4
    with pytest.raises(ValueError, match="non-Intel"):
        pa.load_man(MAN_PATH)
    assert pa.load_man(ARRIA_PATH)["family"] == "Arria 10", "the Intel loader still works for the Arria MAN"
    assert vmm.load_mirror_bounds(ARRIA_PATH, 4).card_id.startswith("mustang")


def test_the_man_does_not_claim_more_than_was_verified():
    v = MAN["verification"]
    assert v["schematic"] == "NOT CHECKED"
    assert v["physical_board"].startswith("NOT TESTED")
    hl = MAN["board"]["host_link"]
    assert hl["status"].startswith("PROPOSED") and "NOT" in hl["status"]
    assert "NOT YET STATED" in hl["host"]["device"], "the ESP32-C variant has not been given"
    assert all(v is False for k, v in MAN["capabilities"].items() if k.endswith("_integrated")), \
        "nothing has been built on this board yet"
    assert MAN["board"]["not_yet_mapped"], "the unmapped interfaces must stay listed until they are mapped"
