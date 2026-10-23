"""tests/vm/test_icm3d_v2.py -- ledger #1313/#1314: ICM-3D v2, the six-face file format for the flex family (experimental/three_d/icm3d_v2.py). VM ONLY, an exploration.
Checks: JSON and binary round trips of every composer example; face bit order; the consistency rule (in_mask must match the neighbours' out_masks); refusal of dangling faces, gates without two inputs,
damaged / truncated / foreign binaries and reserved bits; the command line; and that the toy's topology codes are the ones the format uses."""
import copy
import json
import os
import struct
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ("../../experimental/three_d", "../../nano", "../../tools"):
    sys.path.insert(0, os.path.join(HERE, sub))
import composer3d_v1 as c3  # noqa: E402
import experimental_3d_nor_v2 as m3  # noqa: E402
import icm3d_v2 as icm  # noqa: E402


def key(d):
    return sorted((p, n["kind"], n["gate"], n["shift"], n["left"], sorted(n["down"])) for p, n in d.nodes.items())


@pytest.mark.parametrize("which", ["gate", "crossing", "adder"])
def test_roundtrip_json_and_binary(which):
    d = c3.EXAMPLES[which][1]()
    doc = icm.from_design(d, which)
    assert key(icm.to_design(json.loads(json.dumps(doc)))) == key(d)
    data = icm.pack(doc)
    back = icm.unpack(data)
    assert key(icm.to_design(back)) == key(d)
    assert icm.pack(back) == data                                    # packing is canonical
    assert len(data) == icm.HEADER.size + 8 * len(d.nodes) + 4


def test_a_binary_design_still_runs_to_the_same_answer():
    d = c3.EXAMPLES["adder"][1]()
    d2 = icm.to_design(icm.unpack(icm.pack(icm.from_design(d))))
    d2.meta = d.meta
    d2.nodes = {p: dict(n, name=d.nodes[p]["name"]) for p, n in d2.nodes.items()}      # the binary has no names; put them back to use the check's names
    assert c3.selfcheck(d2)["ok"]


def test_face_bit_order_and_masks():
    d = c3.EXAMPLES["gate"][1]()                                       # A(1,0,0) E-> G(1,1,0); B(1,1,1) D-> G; G E-> E(1,2,0)
    doc = icm.from_design(d)
    rec = {tuple(r["pos"]): r for r in doc["cells"]}
    assert rec[(1, 0, 0)]["out_mask"] == 1 << 2                      # E is bit 2
    assert rec[(1, 1, 1)]["out_mask"] == 1 << 5                      # D is bit 5
    assert rec[(1, 1, 0)]["in_mask"] == (1 << 3) | (1 << 4)           # G hears A through its W face and B through its U face
    assert rec[(1, 1, 0)]["core"] == "nano" and rec[(1, 1, 0)]["topology"] == 0x0BC
    assert rec[(1, 2, 0)]["core"] == "ram" and rec[(1, 2, 0)]["shift"] == 4 and "topology" not in rec[(1, 2, 0)]


def test_topology_codes_are_the_toys():
    assert icm.TOPOLOGY == {g: t for t, g in m3.TOPOLOGY.items()}


def test_dangling_face_and_bad_gate_inputs_are_refused():
    d = c3.EXAMPLES["gate"][1]()
    d.nodes[(1, 2, 0)]["down"].add(2)                                  # E sends east into nothing
    with pytest.raises(icm.IcmError, match="no cell there"):
        icm.from_design(d)
    d = c3.EXAMPLES["gate"][1]()
    d.nodes[(1, 1, 1)]["down"] = set()                                 # B no longer feeds the gate: one input
    with pytest.raises(icm.IcmError, match="needs exactly two"):
        icm.from_design(d)


def test_consistency_rules_catch_hand_edits():
    doc = icm.from_design(c3.EXAMPLES["gate"][1]())
    for edit, word in [
        (lambda r: r[0].update(in_mask=r[0]["in_mask"] ^ 1), "does not match"),
        (lambda r: r[0].update(out_mask=0), "does not match"),
        (lambda r: r[0].update(pos=r[1]["pos"]), "two cells"),
        (lambda r: r[0].update(pos=[9, 9, 9]), "outside"),
        (lambda r: r[0].update(core="alu"), "unknown core"),
        (lambda r: r[0].update(out_mask=64), "six bits"),
        (lambda r: r[0].update(shift=40), "shift"),
    ]:
        bad = copy.deepcopy(doc)
        edit(bad["cells"])
        with pytest.raises(icm.IcmError, match=word):
            icm.validate(bad)
    gate = next(r for r in doc["cells"] if r["core"] == "nano")
    for field, val, word in [("topology", 0x123, "topology"), ("shift", 3, "no shift")]:
        bad = copy.deepcopy(doc)
        next(r for r in bad["cells"] if r["core"] == "nano")[field] = val
        with pytest.raises(icm.IcmError, match=word):
            icm.validate(bad)
    assert gate
    for bad in ({}, dict(doc, version=3), dict(doc, family="sub"), dict(doc, format="icm-v3")):
        with pytest.raises(icm.IcmError):
            icm.validate(bad)


def test_damaged_binaries_are_refused():
    data = icm.pack(icm.from_design(c3.EXAMPLES["crossing"][1]()))
    with pytest.raises(icm.IcmError, match="checksum"):
        icm.unpack(data[:20] + bytes([data[20] ^ 1]) + data[21:])
    with pytest.raises(icm.IcmError, match="length"):
        icm.unpack(data[:-9])
    with pytest.raises(icm.IcmError, match="magic"):
        icm.unpack(b"XXXX" + data[4:])
    with pytest.raises(icm.IcmError, match="too short"):
        icm.unpack(b"I3D2")
    # reserved bits set (with a fresh, correct checksum: a newer-format file must still be refused)
    body = bytearray(data[:-4])
    w = icm.RECORD.unpack_from(body, icm.HEADER.size)[0] | (1 << 50)
    icm.RECORD.pack_into(body, icm.HEADER.size, w)
    import zlib
    with pytest.raises(icm.IcmError, match="reserved"):
        icm.unpack(bytes(body) + struct.pack("<I", zlib.crc32(bytes(body)) & 0xFFFFFFFF))
    body = bytearray(data[:-4])
    body[4] = 3                                                       # version 3
    with pytest.raises(icm.IcmError, match="version"):
        icm.unpack(bytes(body) + struct.pack("<I", zlib.crc32(bytes(body)) & 0xFFFFFFFF))


def test_command_line_round_trip(tmp_path):
    src = tmp_path / "d.3d.json"
    d = c3.EXAMPLES["adder"][1]()
    src.write_text(json.dumps(d.export()))
    assert icm.main(["convert", str(src), str(tmp_path / "d.icm3d")]) == 0
    assert icm.main(["convert", str(src), str(tmp_path / "d.icm3d.json")]) == 0
    nameless = lambda doc: [{k: v for k, v in r.items() if k != "name"} for r in doc["cells"]]
    assert nameless(icm.load(str(tmp_path / "d.icm3d"))) == nameless(icm.load(str(tmp_path / "d.icm3d.json")))
    assert icm.main(["convert", str(tmp_path / "d.icm3d"), str(tmp_path / "back.3d.json")]) == 0
    back = c3.Design.from_export(json.loads((tmp_path / "back.3d.json").read_text()))
    assert [(p, n["kind"], n["gate"], n["shift"], sorted(n["down"])) for p, n in sorted(back.nodes.items())] == \
           [(p, n["kind"], n["gate"], n["shift"], sorted(n["down"])) for p, n in sorted(d.nodes.items())]
    assert icm.main(["show", str(tmp_path / "d.icm3d")]) == 0
    (tmp_path / "junk").write_bytes(b"not a file")
    assert icm.main(["show", str(tmp_path / "junk")]) == 1


def test_composer_export_and_load_actions():
    import base64
    comp = c3.Composer3D(c3.EXAMPLES["gate"][1]())
    st = comp.handle("export_icm3d", {})
    assert st["icm3d"]["format"] == "icm-3d"
    assert len(icm.unpack(base64.b64decode(st["icm3d_bin"]))["cells"]) == len(st["icm3d"]["cells"]) == 4
    comp2 = c3.Composer3D()
    s2 = comp2.handle("load_icm3d_bin", {"b64": st["icm3d_bin"]})
    assert s2["summary"]["cells"] == 4 and s2["summary"]["gates"] == 1
    s3 = c3.Composer3D().handle("load_icm3d", {"doc": st["icm3d"]})
    assert s3["summary"]["cells"] == 4
    with pytest.raises(c3.DesignError):
        comp2.handle("load_icm3d_bin", {"b64": "!!!"})
    with pytest.raises(c3.DesignError):
        comp2.handle("load_icm3d", {"doc": {"format": "icm-3d"}})
    bad = c3.Composer3D(c3.EXAMPLES["gate"][1]())
    bad.design.nodes[(1, 2, 0)]["down"].add(2)
    with pytest.raises(c3.DesignError, match="no cell there"):
        bad.handle("export_icm3d", {})


def test_v2_and_v1_refuse_each_others_files():
    import icm3d_v1 as old
    d = c3.EXAMPLES["gate"][1]()
    new_bin, old_bin = icm.pack(icm.from_design(d)), old.pack(old.from_design(d))
    assert new_bin[:4] == b"I3D2" and old_bin[:4] == b"I3D1"
    with pytest.raises(icm.IcmError):
        icm.unpack(old_bin)
    with pytest.raises(old.IcmError):
        old.unpack(new_bin)
    with pytest.raises(icm.IcmError, match="unknown version"):
        icm.validate(old.from_design(d))


def test_pass_through_is_the_ram_core_in_flowing_mode():
    doc = icm.from_design(c3.EXAMPLES["gate"][1]())
    assert doc["cores"]["ram"]["real"] is True and "fixed_mode 0" in doc["cores"]["ram"]["mode"]
    assert "relay" not in doc["cores"] and all(r["core"] in ("ram", "nano") for r in doc["cells"])
    bad = json.loads(json.dumps(doc))
    next(r for r in bad["cells"] if r["core"] == "ram")["topology"] = 7
    with pytest.raises(icm.IcmError, match="no topology"):
        icm.validate(bad)
