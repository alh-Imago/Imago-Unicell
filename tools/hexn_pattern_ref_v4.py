"""hexn_pattern_ref_v4 = ref_v3 on designer_v4 (3 Nov 2026); nothing else changed.
hexn_pattern_ref_v3 = ref_v2 on designer_v3 (3 Nov 2026); nothing else changed.
hexn_pattern_ref_v1.py - the PATTERN REFERENCE FILE (2 Nov 2026; Alan 17:59 and 18:02: the pattern designs are reference files, set in the bitstream; the programmer checks the card
and, if needed, pulls the bitstream, or builds it from the reference, or tells the user).

Builds on tools/hexn_pattern_designer_v1.py (untouched: its recipes, make_base and the stand-in pattern_file are reused) and adds what the load flow needs:
  * a PATTERN ID word = [31:16] type (4 hex digits K S NN) | [15:0] version - the scheme of the 2 Nov 17:20 ledger row;
  * the KIND rule (K).  The scheme named the kinds but not how a recipe gets one; THIS RULE IS MY PROPOSAL: lead2 RAM -> 4 (two RAM layers); every4 RAM -> 5 (RAM bands);
    else any control core (BR, MG, SQ, PR) -> 3 (mixed); else join cores (JN) present -> 2 (logic); else 1 (math).  F (user-created) is for designer output the user names themselves.
  * the SIZE code S = the grid side as a hex digit (7, 9, B);
  * a registry (plain dict, saved as json): name -> {type, version, hash}.  The sequence NN is the next free number for that kind and size.  A reference whose content hash
    is unchanged keeps its version; any change to the content takes version + 1 (a new version is a new bitstream, never a silent edit);
  * the reference file 'hexn-pattern-v2': name, pattern_id, kind, rows, cols, faces (4), lead_k, recipe, work cells, RAM cells, the judges the bitstream holds, routing and work counts,
    the estimate of slots (labelled: estimates from hexn_bases, NOT place and route), and a content hash over everything but the id word and the hash itself.
Nothing here builds a bitstream.  The assembler would read this file."""
import hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_pattern_designer_v4 as D1

FORMAT = "hexn-pattern-v2"
KIND_BITS = {"math": 1, "logic": 2, "mixed": 3, "ram2": 4, "banded": 5, "user": 0xF}
SIZE_CODE = {7: 0x7, 9: 0x9, 11: 0xB, 13: 0xD, 15: 0xF}


def _canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"))


def kind_of(recipe):
    if recipe["ram"] == "lead2": return "ram2"
    if recipe["ram"] == "every4": return "banded"
    c = recipe["counts"]
    if any(c.get(k) for k in ("BR", "MG", "SQ", "PR")): return "mixed"
    if c.get("JN"): return "logic"
    return "math"


def type_word(kind, n, seq):
    assert 0 <= seq <= 0xFF and n in SIZE_CODE
    return (KIND_BITS[kind] << 12) | (SIZE_CODE[n] << 8) | seq


def pack_id(ptype, version):
    assert 0 <= ptype <= 0xFFFF and 1 <= version <= 0xFFFF
    return (ptype << 16) | version


def unpack_id(word):
    return (word >> 16) & 0xFFFF, word & 0xFFFF


def _body(recipe, judges):
    b = D1.make_base(recipe); f = D1.pattern_file(recipe)
    return dict(format=FORMAT, name=f["name"], kind=kind_of(recipe), rows=f["rows"], cols=f["cols"], faces=4, lead_k=f["lead_k"], recipe=json.loads(_canon(recipe)),
                work_cells=f["work_cells"], ram_cells=f["ram_cells"], judges=sorted(judges),
                counts=dict(work=len(f["work_cells"]), ram=len(f["ram_cells"]), routing=b.n * b.n - len(f["work_cells"]) - len(f["ram_cells"])),
                slots_estimate=f["slots_estimate"], slots_note="estimates from hexn_bases (routing cell 30, 60 with a self-timed type), NOT place and route; the measured four-face routing cell is 12 / 24 LUT (2 Nov 17:53 ledger row)")


def content_hash(body):
    return hashlib.sha256(_canon(body).encode()).hexdigest()


def reference(recipe, registry, judges=("judge_a", "judge_b")):
    """-> (reference dict, registry).  registry: {name: {type, version, hash}} - returned updated (a new dict)."""
    reg = json.loads(json.dumps(registry)); body = _body(recipe, judges); h = content_hash(body); name = body["name"]
    if name in reg:
        e = reg[name]
        if e["hash"] != h: e = dict(type=e["type"], version=e["version"] + 1, hash=h)
    else:
        used = [r["type"] & 0xFF for r in reg.values() if (r["type"] >> 8) == (type_word(body["kind"], recipe["n"], 0) >> 8)]
        e = dict(type=type_word(body["kind"], recipe["n"], max(used) + 1 if used else 0), version=1, hash=h)
    reg[name] = e
    ref = dict(body, pattern_id=pack_id(e["type"], e["version"]), pattern_id_hex="%08X" % pack_id(e["type"], e["version"]), content_hash=h)
    return ref, reg


def check_reference(ref):
    """-> list of problems (empty = fine): format, content hash, and that the id's kind and size digits agree with the content"""
    p = []
    if ref.get("format") != FORMAT: return ["not a %s file" % FORMAT]
    body = {k: v for k, v in ref.items() if k not in ("pattern_id", "pattern_id_hex", "content_hash")}
    if content_hash(body) != ref.get("content_hash"): p.append("content hash does not match: file damaged or edited")
    t, v = unpack_id(ref.get("pattern_id", 0))
    if v < 1: p.append("version 0 is not a pattern")
    if (t >> 12) != KIND_BITS.get(ref.get("kind")): p.append("id kind digit %X does not match kind %r" % (t >> 12, ref.get("kind")))
    if ((t >> 8) & 0xF) != SIZE_CODE.get(ref.get("rows")): p.append("id size digit does not match a %s by %s grid" % (ref.get("rows"), ref.get("cols")))
    if ref.get("faces") != 4: p.append("only four faces are supported")
    return p
