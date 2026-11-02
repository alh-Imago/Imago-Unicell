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


def pack_id(ptype, version):
    """pattern ID word as read from register 11 of spi_bridge_v3: [31:16] type, [15:0] version (4 hex digits each); 0 = no pattern"""
    assert 0 <= ptype <= 0xFFFF and 0 <= version <= 0xFFFF
    return (ptype << 16) | version


def unpack_id(word):
    return (word >> 16) & 0xFFFF, word & 0xFFFF


def make_unit(name, base, pattern, program, weights, description="", pattern_id=None):
    """weights: {judge name: json payload}; pattern_id: the 32-bit word the card reports for the pattern this unit was designed for"""
    body = dict(program=json.loads(_canon(program)), weights=json.loads(_canon(weights)))
    return dict(header=dict(format=MAGIC, name=name, base=base, pattern=pattern, pattern_id=pattern_id, description=description,
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


def load_plan(unit, loaded, library, card_pattern_id=None):
    """THE LOADER'S DECISION (Alan, 2 Nov 16:27): a unit stays with the base+pattern it was designed for, or it would fail.
    loaded  : (base, pattern) the host last loaded, or None (only a fallback)
    card_pattern_id : the word READ FROM THE CARD (register 11 of spi_bridge_v3); when given it decides what is loaded, not the host's record
    library : {(base, pattern): {'file': bitstream file, 'judges': [judge names that bitstream holds], 'pattern_id': 32-bit word (optional)}}
    -> (steps, problems).  steps are plain words for the host to carry out; problems non-empty means NOTHING is loaded.
    Order: [load the bitstream only if it is not the one already on the card], wipe, program, weights, ready for data."""
    st = check(unit)
    h = unit.get("header", {}) if isinstance(unit, dict) else {}
    problems = []
    if st["header"] != OK:
        return [], ["header refused (status %d)" % st["header"]]
    for p in PARTS:
        if st[p] != OK:
            problems.append("%s part refused (status %d)" % (p, st[p]))
    key = (h.get("base"), h.get("pattern"))
    if not key[0] or not key[1]:
        problems.append("unit does not name its base and pattern")
    elif key not in library:
        problems.append("no bitstream for base %r pattern %r in the library" % key)
    else:
        missing = sorted(set(unit.get("weights", {})) - set(library[key].get("judges", [])))
        if missing:
            problems.append("weights for judges the bitstream does not hold: %s" % ", ".join(missing))
    want = library.get(key, {}).get("pattern_id")
    if not problems and h.get("pattern_id") is not None and want is not None and h["pattern_id"] != want:
        problems.append("unit expects pattern id %08X but the library bitstream has %08X" % (h["pattern_id"], want))
    if problems:
        return [], problems
    steps = []
    if card_pattern_id is not None and want is not None:
        on_card = card_pattern_id == want
    else:
        on_card = tuple(loaded or ()) == key
    if not on_card:
        steps.append("load bitstream %s" % library[key]["file"])
    return steps + ["wipe all cells", "load program", "load weights", "ready for data"], []


def unit_from_icm(icm, weights, pattern, pattern_id=None, description=""):
    """a unit whose program part IS an icm-hexn file: the unit takes the ICM file's own name and base (bitstream), so one name ties file, program and unit together"""
    return make_unit(icm["name"], icm["bitstream"], pattern, icm, weights, description, pattern_id)


def plan_load(unit, card, card_pattern_id, library, can_build=False):
    """THE FULL LOAD DECISION (Alan, 2 Nov 17:59).  An ICM/unit is read by the programmer, which
      A) checks which pattern the target card holds (the pattern id word read from the card),
      B) if it is the right one, goes straight on; if not, PULLS the bitstream from the library, or, if there is none, BUILDS it from the pattern's reference file
         with the assembler (only when can_build), or else TELLS THE USER the bitstream has to be put in place first and loads NOTHING,
      C) then wipes, loads the program from the file, then the weights, then is ready for data.
    card: card id (a bitstream is per card).  library: {card: {(base, pattern): {'pattern_id': word, 'reference': pattern reference file name or None,
      'file': bitstream file for THIS card or None, 'judges': [names]}}}.  -> dict(steps=[...], problems=[...], needs=[...]); problems non-empty means nothing is done."""
    st = check(unit); h = unit.get("header", {}) if isinstance(unit, dict) else {}
    problems, needs = [], []
    if st["header"] != OK:
        return dict(steps=[], problems=["header refused (status %d)" % st["header"]], needs=[])
    for p in PARTS:
        if st[p] != OK: problems.append("%s part refused (status %d)" % (p, st[p]))
    key = (h.get("base"), h.get("pattern")); entry = library.get(card, {}).get(key)
    if not key[0] or not key[1]: problems.append("unit does not name its base and pattern")
    elif entry is None: problems.append("pattern %r on base %r is not known for card %r (no reference file, no bitstream)" % (key[1], key[0], card))
    else:
        missing = sorted(set(unit.get("weights", {})) - set(entry.get("judges", [])))
        if missing: problems.append("weights for judges the bitstream does not hold: %s" % ", ".join(missing))
        if h.get("pattern_id") is not None and entry.get("pattern_id") is not None and h["pattern_id"] != entry["pattern_id"]:
            problems.append("unit expects pattern id %08X but the library has %08X" % (h["pattern_id"], entry["pattern_id"]))
    steps = []
    if not problems:
        if card_pattern_id is not None and entry.get("pattern_id") is not None and card_pattern_id == entry["pattern_id"]:
            steps.append("bitstream already on the card")
        elif entry.get("file"):
            steps.append("pull bitstream %s from the library and load it on card %s" % (entry["file"], card))
        elif entry.get("reference") and can_build:
            steps += ["build the bitstream for card %s from reference %s with the assembler" % (card, entry["reference"]), "load the new bitstream"]
        else:
            what = "reference file %s" % entry["reference"] if entry.get("reference") else "reference file"
            needs.append("bitstream for pattern %r on card %r" % (key[1], card))
            problems.append("the bitstream is not on the card, not in the library, and cannot be built here (%s %s): it needs to be in place before this unit can load"
                            % ("have" if entry.get("reference") else "no", what))
    if problems: return dict(steps=[], problems=problems, needs=needs)
    return dict(steps=steps + ["wipe all cells", "load program", "load weights", "ready for data"], problems=[], needs=[])
