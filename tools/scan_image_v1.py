#!/usr/bin/env python3
"""tools/scan_image_v1.py -- ledger #1156: ONE self-describing state file for a saved mid-flight state.
The card's raw image is 256 bytes of bits whose meaning is only in SCAN_MAP.json (a second file you must not lose). This tool turns it into a single JSON file that carries
the design name, the formula, the register-layout fingerprint, the cut, and for EVERY cell and register its name, width and value (plus a plain-words 'live' reading), so the one file says what it is and where each value belongs.
  python3 tools/scan_image_v1.py pack   RAW.json SCAN_MAP.json OUT.state.json [--formula "..."]   raw card/sim image file (--capture-only --out / scan_swap from-sim) -> state file
  python3 tools/scan_image_v1.py unpack IN.state.json SCAN_MAP.json OUT.json                      state file -> raw image file the card host accepts (--restore-only --in)
  python3 tools/scan_image_v1.py show   IN.state.json                                             print it in words
unpack REFUSES (and says exactly what differs) if the target design's cells/registers/widths are not the ones in the file; it rebuilds the bits by NAME from the target's own map, never by position.
Values are lossless (stale registers keep their value); 'live' is a reading of the RTL (a data register counts as live when its own pending/have flag is set) and is advisory: it never changes the bits."""
import argparse, datetime, hashlib, json, sys

FORMAT = "unicell-state-v1"
STREAM_BYTES = 240

# data register -> the flag register that says it holds a word (None = not decided here). Only the cell types present in the LaTeX design are read; others stay null.
LIVE_FLAG = {
    "ram": {"data_reg": "have"},
    "adder": {"out_buffer": "pending", "carry_buffer": "pending_c"},
    "mul": {"out_buffer": "pending", "hi_buffer": "pending_hi"},
    "div": {"out_buffer": "pending", "rem_buffer": "pending_r", "d_reg": "busy", "r_reg": "busy", "q_reg": "busy", "remaining": "busy"},
}


def layout_id(scan_map):
    canon = json.dumps([[c["cell"], c["type"], [[r["name"], r["bits"]] for r in c["regs"]]] for c in scan_map["chain"]], separators=(",", ":"))   # the same fingerprint as board_scan_v2.layout_id
    return hashlib.sha256(canon.encode()).hexdigest()[:16]


def _bit(buf, i):
    return (buf[i // 8] >> (7 - i % 8)) & 1


def _get(buf, off, n):
    v = 0
    for i in range(n):
        v = (v << 1) | _bit(buf, off + i)
    return v


def _put(buf, off, n, v):
    for i in range(n):
        if (v >> (n - 1 - i)) & 1:
            buf[(off + i) // 8] |= 0x80 >> ((off + i) % 8)


def pack(raw, scan_map, formula=None):
    img = bytes.fromhex(raw["image"])
    if len(img) != 256:
        sys.exit("REFUSED: raw image is %d bytes, expected 256" % len(img))
    nb = scan_map["total_bits"]
    stream = img[:STREAM_BYTES]
    if any(_bit(stream, i) for i in range(nb, STREAM_BYTES * 8)):
        sys.exit("REFUSED: padding bits after the %d scan bits are not zero" % nb)
    lid = layout_id(scan_map)
    if raw.get("layout") not in (None, lid):
        sys.exit("REFUSED: raw file layout %s does not match this SCAN_MAP (%s)" % (raw.get("layout"), lid))
    cells = []
    for c in scan_map["chain"]:
        regs, vals = [], {}
        for r in c["regs"]:
            vals[r["name"]] = _get(stream, r["stream_offset"], r["bits"])
        flags = LIVE_FLAG.get(c["type"], {})
        for r in c["regs"]:
            live = None
            if c["type"] in LIVE_FLAG:
                f = flags.get(r["name"])
                live = (vals[f] != 0) if f in vals else (True if r["bits"] == 1 else None)
            regs.append(dict(name=r["name"], bits=r["bits"], value=vals[r["name"]], live=live))
        cells.append(dict(cell=c["cell"], type=c["type"], registers=regs))
    tr = img[STREAM_BYTES:]
    return dict(
        format=FORMAT, design=raw.get("design"), formula=formula or raw.get("formula"), layout=lid,
        session=raw.get("ses"), cut=raw.get("cut"), made_by=raw.get("made_by", "real card"), made=raw.get("when"),
        total_bits=nb, stream_rule=scan_map.get("stream_order"),
        closing=dict(word=int.from_bytes(tr[0:4], "big"), has=tr[4], steps=int.from_bytes(tr[5:7], "big"), rest_hex=tr[7:].hex(),
                     meaning="the word waiting in the closing register after the grid; whether it is valid; steps taken when the run was stopped"),
        cells=cells, constants_left_out=scan_map.get("constants_left_out"),
        note="values are exact; 'live' is a reading of the RTL (data counts as live when its own pending/have flag is set) and does not change the bits",
        packed=datetime.datetime.now().isoformat(timespec="seconds"))


def unpack(st, scan_map):
    if st.get("format") != FORMAT:
        sys.exit("REFUSED: not a %s file" % FORMAT)
    lid = layout_id(scan_map)
    problems = []
    if st.get("layout") not in (None, lid):
        problems.append("the file's layout fingerprint is %s, the target design's is %s" % (st.get("layout"), lid))
    have = {c["cell"]: c for c in st["cells"]}
    want = {c["cell"]: c for c in scan_map["chain"]}
    for n in want:
        if n not in have:
            problems.append("the target design has cell %s, the file does not" % n)
    for n in have:
        if n not in want:
            problems.append("the file has cell %s, the target design does not" % n)
    stream = bytearray(STREAM_BYTES)
    for n, wc in want.items():
        fc = have.get(n)
        if not fc:
            continue
        if fc["type"] != wc["type"]:
            problems.append("cell %s: file says %s, target is %s" % (n, fc["type"], wc["type"]))
            continue
        fr = {r["name"]: r for r in fc["registers"]}
        for r in wc["regs"]:
            x = fr.get(r["name"])
            if x is None:
                problems.append("cell %s: target register %s missing in the file" % (n, r["name"]))
            elif x["bits"] != r["bits"]:
                problems.append("cell %s register %s: file %d bits, target %d bits" % (n, r["name"], x["bits"], r["bits"]))
            else:
                if x["value"] >> r["bits"]:
                    problems.append("cell %s register %s: value does not fit %d bits" % (n, r["name"], r["bits"]))
                else:
                    _put(stream, r["stream_offset"], r["bits"], x["value"])
        for x in fc["registers"]:
            if x["name"] not in {r["name"] for r in wc["regs"]}:
                problems.append("cell %s: file register %s not in the target" % (n, x["name"]))
    if problems:
        sys.exit("REFUSED: this state file does not fit the target design:\n  " + "\n  ".join(problems))
    cl = st["closing"]
    tr = cl["word"].to_bytes(4, "big") + bytes([cl["has"]]) + cl["steps"].to_bytes(2, "big") + bytes.fromhex(cl["rest_hex"])
    img = bytes(stream) + tr
    assert len(img) == 256
    return dict(ses=st.get("session"), image=img.hex(), cut=st.get("cut"), design=st["design"], layout=lid, when=datetime.datetime.now().isoformat(), made_by="unpacked from state file (%s)" % st.get("made_by"))


def load_any(path, scan_map):
    """Read either file kind; always return the raw image dict (a state file is unpacked by name against scan_map, and refused if it does not fit)."""
    d = json.load(open(path))
    return unpack(d, scan_map) if d.get("format") == FORMAT else d


def save_state(raw, scan_map, formula, path):
    json.dump(pack(raw, scan_map, formula), open(path, "w"), indent=1)


def show(st):
    print("%s  design %s  layout %s  made by %s" % (st["format"], st["design"], st["layout"], st["made_by"]))
    print("formula: %s" % st.get("formula")); print("cut %s, stopped after %d steps; closing register: word %d, valid %d" % (st.get("cut"), st["closing"]["steps"], st["closing"]["word"], st["closing"]["has"] & 1))
    for c in st["cells"]:
        live = ["%s=%d" % (r["name"], r["value"]) for r in c["registers"] if r["live"] and r["value"]]
        print("  %-34s %-6s live: %s" % (c["cell"], c["type"], ", ".join(live) or "-"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("mode", choices=["pack", "unpack", "show"]); ap.add_argument("files", nargs="+"); ap.add_argument("--formula")
    a = ap.parse_args()
    if a.mode == "pack":
        raw, sm = json.load(open(a.files[0])), json.load(open(a.files[1]))
        json.dump(pack(raw, sm, a.formula), open(a.files[2], "w"), indent=1); print("written", a.files[2])
    elif a.mode == "unpack":
        st, sm = json.load(open(a.files[0])), json.load(open(a.files[1]))
        json.dump(unpack(st, sm), open(a.files[2], "w"), indent=1); print("written", a.files[2])
    else:
        show(json.load(open(a.files[0])))


if __name__ == "__main__":
    main()
