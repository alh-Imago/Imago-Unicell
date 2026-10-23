"""experimental/three_d/icm3d_v1.py -- ICM-3D v1: a file format for six-face (3D) designs, flex/sub family. VM ONLY, an exploration (ledger #1313).

REAL, HONEST SCOPE. A standalone format, separate from ICM v3 (which is untouched: its 42-bit `core_config` cannot hold six faces for five cores, see CELL_AUDIT_6_FACE.md). Nothing reads it but this file and the 3D Composer:
there is no 3D RTL, no assembler pass and no card. It describes a design in the toy model `experimental_3d_nor_v2.py`, in the shape a flex-family generator would need: one record per cell with its grid square, its core,
its add-on, and its faces as 6-bit masks. Which core a toy cell stands for:
  * a toy GATE cell  -> core `nano`, `topology` = the toy's own nano topology code (AND 0x007, OR 0x024, XOR 0x0BC, NOR 0x004, NAND 0x027, XNOR 0x03C -- copied from the toy model, not re-checked against the RTL here);
  * a toy RELAY cell -> core `relay`, a TOY PSEUDO-CORE (a pass-through with the shift add-on). No real RTL core is claimed for it; mapping it onto a real core is open (see ICM_3D_FORMAT.md).

FACES. Bit order is the toy's: bit 0 N, 1 S, 2 E, 3 W, 4 U, 5 D (U and D after W, so every four-face design keeps its four low bits). A record has `out_mask` (faces it sends to) and `in_mask` (faces it receives from).
`in_mask` is derived from the neighbours' `out_mask`s and is stored anyway: a reader that finds the two disagree must refuse the file (that catches a wrongly edited or truncated file).

TWO FORMS, same content
  JSON    human-readable; carries names and free text (`name`, `description`, `meta`).
  BINARY  magic `I3D1`, then a fixed 64-bit record per cell, then a CRC-32 of everything before it; no names. Layout below.

    python3 experimental/three_d/icm3d_v1.py convert design.3d.json out.icm3d.json      (composer design -> ICM-3D JSON)
    python3 experimental/three_d/icm3d_v1.py convert design.3d.json out.icm3d           (-> binary; any other extension)
    python3 experimental/three_d/icm3d_v1.py convert out.icm3d back.3d.json            (either ICM-3D form -> composer design)
    python3 experimental/three_d/icm3d_v1.py show out.icm3d
"""
import argparse
import json
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in (os.path.join(REPO, "tools"), os.path.join(REPO, "nano"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import experimental_3d_nor_v2 as m3  # noqa: E402
import composer3d_v1 as c3  # noqa: E402

FORMAT = "icm-3d"
VERSION = 1
MAGIC = b"I3D1"
FAMILY = {"flex": 1}
FAMILY_NAME = {v: k for k, v in FAMILY.items()}
CORES = {"relay": 0, "nano": 1}
CORE_NAME = {v: k for k, v in CORES.items()}
GATE_ORDER = ["AND", "OR", "XOR", "NOR", "NAND", "XNOR"]
TOPOLOGY = {"AND": 0x007, "OR": 0x024, "XOR": 0x0BC, "NOR": 0x004, "NAND": 0x027, "XNOR": 0x03C}
GATE_OF_TOPOLOGY = {v: k for k, v in TOPOLOGY.items()}
assert {m3.TOPOLOGY[v]: v for v in m3.TOPOLOGY} == TOPOLOGY      # the table above is the toy's own
FACES = "NSEWUD"
LIMITS = {"rows": 63, "cols": 63, "layers": 31, "cells": 65535}
HEADER = struct.Struct("<4sBBBBBH")        # magic, version, family, rows, cols, layers, count
RECORD = struct.Struct("<Q")
# 64-bit record, bit positions (LSB first): row[0:6] col[6:12] layer[12:17] core[17:19] gate_index[19:22] shift[22:27] shift_left[27] out_mask[28:34] in_mask[34:40] reserved[40:64] (must be zero)
FIELDS = [("row", 0, 6), ("col", 6, 6), ("layer", 12, 5), ("core", 17, 2), ("gate_index", 19, 3), ("shift", 22, 5), ("shift_left", 27, 1), ("out_mask", 28, 6), ("in_mask", 34, 6), ("reserved", 40, 24)]


class IcmError(ValueError):
    """The file or design is not a valid ICM-3D v1."""


def _mask(faces):
    return sum(1 << f for f in faces)


def from_design(d, name="design"):
    """Composer Design -> ICM-3D document. Refuses anything the format cannot hold."""
    inc, out, dangling = d.graph()
    if dangling:
        p, f = dangling[0]
        raise IcmError("%s sends %s but there is no cell there; ICM-3D has no dangling faces" % (d.name_of(p), FACES[f]))
    if d.rows > LIMITS["rows"] or d.cols > LIMITS["cols"] or d.layers > LIMITS["layers"] or len(d.nodes) > LIMITS["cells"]:
        raise IcmError("the design is larger than the format's limits %s" % LIMITS)
    cells = []
    for p, n in sorted(d.nodes.items()):
        in_faces = {m3.OPP[next(k for k in range(6) if c3._add(s, k) == p)] for s in inc[p]}
        rec = {"name": n["name"], "pos": list(p), "core": "nano" if n["kind"] == "gate" else "relay",
               "shift": n["shift"], "shift_left": bool(n["left"]) if n["shift"] else True,
               "out_mask": _mask(n["down"]), "in_mask": _mask(in_faces)}
        if n["kind"] == "gate":
            rec["topology"] = TOPOLOGY[n["gate"]]
        cells.append(rec)
    doc = {"format": FORMAT, "version": VERSION, "family": "flex", "name": name,
           "note": "VM-only exploration format (toy six-face grid); nothing but icm3d_v1.py and composer3d_v1.py reads it",
           "face_bits": list(FACES), "size": {"rows": d.rows, "cols": d.cols, "layers": d.layers},
           "cores": {"nano": {"real": True, "note": "gate cells; topology codes copied from experimental_3d_nor_v2.py"},
                     "relay": {"real": False, "note": "toy pseudo-core: pass-through with the shift add-on; no RTL core claimed"}},
           "description": d.description, "meta": d.meta, "cells": cells}
    validate(doc)
    return doc


def validate(doc):
    """Raise IcmError (first problem, in plain words) unless the document is a self-consistent ICM-3D v1."""
    if not isinstance(doc, dict) or doc.get("format") != FORMAT:
        raise IcmError("not an %s file" % FORMAT)
    if doc.get("version") != VERSION:
        raise IcmError("unknown version %r (this reader knows %d)" % (doc.get("version"), VERSION))
    if doc.get("family") not in FAMILY:
        raise IcmError("unknown family %r" % doc.get("family"))
    try:
        size = doc["size"]
        rows, cols, layers = int(size["rows"]), int(size["cols"]), int(size["layers"])
        recs = doc["cells"]
    except (KeyError, TypeError, ValueError):
        raise IcmError("missing size or cells")
    if not (1 <= rows <= LIMITS["rows"] and 1 <= cols <= LIMITS["cols"] and 1 <= layers <= LIMITS["layers"]) or len(recs) > LIMITS["cells"]:
        raise IcmError("size outside the format's limits %s" % LIMITS)
    at = {}
    for i, r in enumerate(recs):
        try:
            pos = tuple(int(x) for x in r["pos"])
            core, shift, left = r["core"], int(r["shift"]), bool(r["shift_left"])
            out, inn = int(r["out_mask"]), int(r["in_mask"])
        except (KeyError, TypeError, ValueError):
            raise IcmError("cell record %d is missing a field" % i)
        if len(pos) != 3 or not (0 <= pos[0] < rows and 0 <= pos[1] < cols and 0 <= pos[2] < layers):
            raise IcmError("cell %d: square %s is outside the board" % (i, pos))
        if pos in at:
            raise IcmError("two cells on square %s" % (pos,))
        if core not in CORES:
            raise IcmError("cell %d: unknown core %r" % (i, core))
        if core == "nano":
            if r.get("topology") not in GATE_OF_TOPOLOGY:
                raise IcmError("cell %d: nano topology %r is not one of %s" % (i, r.get("topology"), ", ".join("0x%03X" % t for t in sorted(GATE_OF_TOPOLOGY))))
            if shift:
                raise IcmError("cell %d: a gate has no shift add-on in this model" % i)
        elif "topology" in r:
            raise IcmError("cell %d: a relay has no topology" % i)
        if not 0 <= shift <= 31:
            raise IcmError("cell %d: shift must be 0 to 31" % i)
        if not (0 <= out < 64 and 0 <= inn < 64):
            raise IcmError("cell %d: a face mask is wider than six bits" % i)
        at[pos] = (out, inn, core)
    for pos, (out, inn, core) in at.items():
        want_in = 0
        for f in range(6):
            src = tuple(pos[i] + m3.DELTA[f][i] for i in range(3))     # the cell beyond face f of this one: it sends into us when its opposite face is on
            if src in at and at[src][0] >> m3.OPP[f] & 1:
                want_in |= 1 << f
        if want_in != inn:
            raise IcmError("cell at %s: in_mask %s does not match its neighbours' out_masks (%s)" % (pos, format(inn, "06b"), format(want_in, "06b")))
        for f in range(6):
            if out >> f & 1 and tuple(pos[i] + m3.DELTA[f][i] for i in range(3)) not in at:
                raise IcmError("cell at %s sends %s into an empty square" % (pos, FACES[f]))
        if core == "nano" and bin(inn).count("1") != 2:
            raise IcmError("gate at %s has %d inputs; it needs exactly two" % (pos, bin(inn).count("1")))
    return True


def to_design(doc):
    """ICM-3D document -> composer Design (names from the file, or c1, c2 ... when the binary form had none)."""
    validate(doc)
    s = doc["size"]
    d = c3.Design(int(s["rows"]), int(s["cols"]), int(s["layers"]))
    d.description = str(doc.get("description") or "")[:500]
    d.meta = doc.get("meta") if isinstance(doc.get("meta"), dict) else {}
    used = set()
    for i, r in enumerate(doc["cells"]):
        nm = r.get("name") or "c%d" % (i + 1)
        if nm in used or not c3.NAME_RE.match(nm):
            raise IcmError("cell %d: bad or repeated name %r" % (i, nm))
        used.add(nm)
        gate = GATE_OF_TOPOLOGY[r["topology"]] if r["core"] == "nano" else None
        d.nodes[tuple(r["pos"])] = {"name": nm, "kind": "gate" if gate else "relay", "gate": gate, "shift": int(r["shift"]), "left": bool(r["shift_left"]),
                                    "down": {f for f in range(6) if int(r["out_mask"]) >> f & 1}}
    return d


# ---------------------------------------------------------------------------------------------------------------------- binary
def _pack_record(r):
    gate_index = GATE_ORDER.index(GATE_OF_TOPOLOGY[r["topology"]]) if r["core"] == "nano" else 0
    vals = {"row": r["pos"][0], "col": r["pos"][1], "layer": r["pos"][2], "core": CORES[r["core"]], "gate_index": gate_index, "shift": int(r["shift"]),
            "shift_left": 1 if r["shift_left"] else 0, "out_mask": int(r["out_mask"]), "in_mask": int(r["in_mask"]), "reserved": 0}
    w = 0
    for name, lo, width in FIELDS:
        w |= (vals[name] & ((1 << width) - 1)) << lo
    return w


def _unpack_record(w):
    v = {name: (w >> lo) & ((1 << width) - 1) for name, lo, width in FIELDS}
    if v["reserved"]:
        raise IcmError("a record has reserved bits set (a newer format?)")
    if v["core"] not in CORE_NAME:
        raise IcmError("unknown core number %d" % v["core"])
    core = CORE_NAME[v["core"]]
    r = {"pos": [v["row"], v["col"], v["layer"]], "core": core, "shift": v["shift"], "shift_left": bool(v["shift_left"]), "out_mask": v["out_mask"], "in_mask": v["in_mask"]}
    if core == "nano":
        if v["gate_index"] >= len(GATE_ORDER):
            raise IcmError("unknown gate index %d" % v["gate_index"])
        r["topology"] = TOPOLOGY[GATE_ORDER[v["gate_index"]]]
    return r


def pack(doc):
    validate(doc)
    s = doc["size"]
    recs = doc["cells"]
    body = HEADER.pack(MAGIC, VERSION, FAMILY[doc["family"]], int(s["rows"]), int(s["cols"]), int(s["layers"]), len(recs))
    body += b"".join(RECORD.pack(_pack_record(r)) for r in recs)
    return body + struct.pack("<I", zlib.crc32(body) & 0xFFFFFFFF)


def unpack(data):
    if len(data) < HEADER.size + 4:
        raise IcmError("file too short")
    magic, version, family, rows, cols, layers, count = HEADER.unpack_from(data, 0)
    if magic != MAGIC:
        raise IcmError("not an ICM-3D binary (bad magic)")
    if version != VERSION:
        raise IcmError("unknown version %d" % version)
    if family not in FAMILY_NAME:
        raise IcmError("unknown family %d" % family)
    if len(data) != HEADER.size + count * RECORD.size + 4:
        raise IcmError("file length does not match its record count")
    (crc,) = struct.unpack_from("<I", data, len(data) - 4)
    if zlib.crc32(data[:-4]) & 0xFFFFFFFF != crc:
        raise IcmError("checksum mismatch: the file is damaged")
    recs = [_unpack_record(RECORD.unpack_from(data, HEADER.size + i * RECORD.size)[0]) for i in range(count)]
    doc = {"format": FORMAT, "version": VERSION, "family": FAMILY_NAME[family], "size": {"rows": rows, "cols": cols, "layers": layers}, "cells": recs}
    validate(doc)
    return doc


def load(path):
    """Read either form (decided by the first bytes, not the file name)."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] == MAGIC:
        return unpack(data)
    try:
        doc = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise IcmError("neither an ICM-3D binary nor JSON")
    validate(doc)
    return doc


def describe(doc):
    cells = doc["cells"]
    gates = sum(1 for r in cells if r["core"] == "nano")
    vert = sum(bin(int(r["out_mask"]) >> 4).count("1") for r in cells)
    s = doc["size"]
    return "ICM-3D v%d, family %s: %d x %d x %d board, %d cells (%d nano gates, %d relays), %d vertical faces" % (doc["version"], doc["family"], s["rows"], s["cols"], s["layers"], len(cells), gates, len(cells) - gates, vert)


def main(argv=None):
    ap = argparse.ArgumentParser(description="ICM-3D v1 (VM-only exploration)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    cv = sub.add_parser("convert")
    cv.add_argument("src")
    cv.add_argument("dst")
    sh = sub.add_parser("show")
    sh.add_argument("src")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "show":
            print(describe(load(a.src)))
            return 0
        with open(a.src, "rb") as f:
            head = f.read(4)
        if head == MAGIC or '"format": "icm-3d"' in open(a.src, errors="ignore").read(400).replace('":"', '": "'):
            doc = load(a.src)
            with open(a.dst, "w") as f:
                json.dump(to_design(doc).export(), f, indent=1)
            print("wrote composer design", a.dst, "--", describe(doc))
        else:
            with open(a.src) as f:
                d = c3.Design.from_export(json.load(f))
            doc = from_design(d, os.path.basename(a.src))
            if a.dst.endswith(".json"):
                with open(a.dst, "w") as f:
                    json.dump(doc, f, indent=1)
            else:
                with open(a.dst, "wb") as f:
                    f.write(pack(doc))
            print("wrote", a.dst, "--", describe(doc))
        return 0
    except (IcmError, c3.DesignError, OSError, ValueError) as e:
        print("failed:", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
