"""hexn_unit_file_v1.py - the Hex-N loadable unit: ONE json file, a HEADER and TWO distinct parts that stay together
(Alan, 2 Nov 16:22: 'the file holds 2 distinct parts separated by a header, they stay together, it's only a json file, as is the normal icm file').

  header   : format, name (the name ties the unit to a pattern and base, as ICM files tie to a design), base, pattern, and for each part its sha256
  program  : the UCC side - a program as made by hexn_bases_v2.program_of (routing selects, core parameters, pads)
  weights  : the judge side - named judges, each an opaque json payload (e.g. docs/hex-n/data/judge_v4_h64_weights.json)

Each part is checked on its own (like the weights records: a refused part is skipped whole with a status word).
Status words (same numbers as the weights loader where the meaning is the same): 0 ok, 1 bad magic/format, 3 bad checksum, 5 names a different base or pattern, 6 part missing.
Load order for the board (proposal, 2 Nov 16:18 row): wipe all cells, program, weights, then data.
This file only reads, writes and checks; it loads nothing onto a board."""
import hashlib, json

MAGIC = "hexn-unit-v1"
OK, BAD_MAGIC, BAD_SUM, WRONG_TARGET, MISSING = 0, 1, 3, 5, 6
PARTS = ("program", "weights")
LOAD_ORDER = ("wipe", "program", "weights", "data")


def _canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"))


def part_hash(x):
    return hashlib.sha256(_canon(x).encode()).hexdigest()


def make_unit(name, base, pattern, program, weights, description=""):
    """weights: {judge name: json payload}"""
    body = dict(program=json.loads(_canon(program)), weights=json.loads(_canon(weights)))
    return dict(header=dict(format=MAGIC, name=name, base=base, pattern=pattern, description=description,
                            load_order=list(LOAD_ORDER), part_hash={p: part_hash(body[p]) for p in PARTS}), **body)


def save(unit, path):
    with open(path, "w") as f:
        json.dump(unit, f, sort_keys=True, indent=1)


def load(path):
    with open(path) as f:
        return json.load(f)


def check(unit, base=None, pattern=None):
    """-> {'header': status, 'program': status, 'weights': status}; a bad part does not hide the other"""
    h = unit.get("header") if isinstance(unit, dict) else None
    if not isinstance(h, dict) or h.get("format") != MAGIC:
        return dict(header=BAD_MAGIC, program=BAD_MAGIC, weights=BAD_MAGIC)
    out = dict(header=OK)
    for p in PARTS:
        if p not in unit or p not in h.get("part_hash", {}):
            out[p] = MISSING
        elif part_hash(unit[p]) != h["part_hash"][p]:
            out[p] = BAD_SUM
        elif p == "program" and ((base is not None and h.get("base") != base) or (pattern is not None and h.get("pattern") != pattern)):
            out[p] = WRONG_TARGET
        else:
            out[p] = OK
    return out


def unicell_view(unit, base=None, pattern=None):
    """ADAPTER for the UniCell side (Alan, 2 Nov 16:25): read the SAME file but ignore the judge weights.
    Returns (program or None, report).  The weights part is never read, only counted as skipped, so a UniCell loader
    needs no judge code; an empty weights part (the holding place with nothing in it) is normal.
    Only the header and the program part are checked.  It does NOT yet turn the program into ICM cell records, and it does not
    say which cells UniCell can run: faces beyond four and the Hex-N-only parts are the 'to a point' still to be listed."""
    st = check(unit, base, pattern)
    h = unit.get("header", {}) if isinstance(unit, dict) else {}
    report = dict(header=st["header"], program=st["program"], weights_skipped=len(unit.get("weights", {})) if isinstance(unit, dict) and isinstance(unit.get("weights"), dict) else 0,
                  name=h.get("name"), base=h.get("base"), pattern=h.get("pattern"))
    ok = st["header"] == OK and st["program"] == OK
    return (unit["program"] if ok else None), report
