#!/usr/bin/env python3
"""tools/flex_tang_bridge_v1.py -- ledger #1098: the VM <-> Tang Nano 20K side of the save / load / retarget proof for the looped CORDIC.

  vm-save   N OUT.json          run the flex VM (the closed ring, as nano/looped_cordic_v1.py) until the N-th result has reached the exit relay, and write a flex_save_v1 save there
                                (design model + state diff by cell name + words in flight + tick + step=N).
  make-state SAVE.json OUT.json translate a flex_save_v1 save into the small file the board host loads (`tang_state.json`): the loop word and the step it belongs to. REFUSES (exit 1, with the
                                reason) unless the VM state is one the card can hold: exactly one non-constant cell holds a word and it is the exit relay `lp.fb19`; every word still in flight comes from a
                                constant source or is the exit relay offering its own word; every adder's waiting first operand is a constant. (Why those are the conditions: ledger #1095 and #1096.)
  compare   SAVE.json TANG_RESULT.json    take the board's result file (written by saveload_host.py), restore the VM from the same save, run it the same number of steps and compare the word at the
                                end; also against the independent Python model. Writes <TANG_RESULT>.compare.json and exits 0 only on a match.
Step numbering: step k = the k-th result delivered to the exit relay; its value is looped_cordic_v1.model(k)[k-1].
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "nano"))
import looped_cordic_v1 as L  # noqa: E402
import flex_save_v1 as S  # noqa: E402
from flex_grid_v1 import FlexGrid  # noqa: E402

EXIT = "lp.fb19"


def grid_from_design(doc):
    p = os.path.join(tempfile.mkdtemp(), "d.icm-hier.json")
    json.dump(doc, open(p, "w"))
    recs, _ = L.flatten(L.load_hierarchical(p))
    return FlexGrid(recs)


def vm_save(n, out):
    g, _ = L.new_grid(FlexGrid)
    got = L.run_steps(g, n)
    assert len(got) == n, "the VM did not reach step %d" % n
    pay = S.save(g, FlexGrid(L.build_records()), L.build_doc(), out, step=n, note="looped CORDIC, closed ring, flex VM, cut at the arrival of result %d at the exit relay" % n)
    return got[-1][1], pay


def _holding(grid):
    out = []
    for c in grid.cells.values():
        if c.core == "ram" and not c.ram_fixed_mode and c.ram_data_valid:
            out.append((c.cell_id, c.ram_data_reg & 0xFFFFFFFF))
        elif c.core == "adder" and c.adder_data_valid:
            out.append((c.cell_id, c.adder_out_buffer & 0xFFFFFFFF))
        elif c.core == "branch" and c.br_data_valid:
            out.append((c.cell_id, c.br_out_buffer & 0xFFFFFFFF))
    return out


def make_state(save_path, out):
    pay = S.read(save_path)
    g = grid_from_design(pay["design"])
    step = S.load_state(g, pay)
    hold = _holding(g)
    if [h[0] for h in hold] != [EXIT]:
        raise SystemExit("make-state refused: the card can only take a state with ONE word, in the exit relay %s; this save has non-constant cells holding words: %s" % (EXIT, hold))
    byname = {c.cell_id: c for c in g.cells.values()}
    pos = {c.cell_id: p for p, c in g.cells.items()}
    for src, dst, face, val in pay["flight"]:
        c = byname.get(src)
        if src == EXIT and (val & 0xFFFFFFFF) == hold[0][1]:          # the exit relay offering its own word to its consumer: the same item, not a second one
            continue
        if c is None or not (c.core == "ram" and c.ram_fixed_mode):
            raise SystemExit("make-state refused: a word in flight from %r is not from a constant source" % src)
    consts = {c.ram_data_reg & 0xFFFFFFFF for c in g.cells.values() if c.core == "ram" and c.ram_fixed_mode}
    for c in g.cells.values():
        if c.core == "adder" and c.adder_a_arrived and (c.adder_a_reg & 0xFFFFFFFF) not in consts:
            raise SystemExit("make-state refused: adder %s holds a waiting first operand that is not a constant" % c.cell_id)
    word = hold[0][1]
    st = {"format": "tang-state-v1", "step": step, "word": word, "word_signed": word - (1 << 32) if word >> 31 else word, "cell": EXIT, "tick": pay["tick"],
          "design_hash": pay["design_hash"], "model_check": L.model(step)[step - 1] & 0xFFFFFFFF}
    st["matches_independent_model"] = st["model_check"] == word
    json.dump(st, open(out, "w"), indent=1)
    return st


def compare(save_path, result_path):
    pay = S.read(save_path)
    res = json.load(open(result_path))
    g = grid_from_design(pay["design"])
    step0 = S.load_state(g, pay)
    if res.get("from_step") != step0:
        raise SystemExit("the board result is from step %r but the save is at step %d" % (res.get("from_step"), step0))
    ran = res["ran"]
    got = L.run_steps(g, ran)
    vm_word = got[-1][1] & 0xFFFFFFFF
    model_word = L.model(step0 + ran)[-1] & 0xFFFFFFFF
    tang = res["word"] & 0xFFFFFFFF
    r = {"from_step": step0, "ran": ran, "final_step": step0 + ran, "tang_word": tang, "vm_word": vm_word, "model_word": model_word,
         "tang_equals_vm": tang == vm_word, "vm_equals_model": vm_word == model_word, "tang_equals_model": tang == model_word}
    r["match"] = r["tang_equals_vm"] and r["vm_equals_model"]
    json.dump(r, open(result_path.replace(".json", "") + ".compare.json", "w"), indent=1)
    return r


def main(argv):
    if len(argv) >= 3 and argv[0] == "vm-save":
        w, _ = vm_save(int(argv[1]), argv[2])
        print("saved %s at step %s, exit word %d" % (argv[2], argv[1], w - (1 << 32) if w >> 31 else w))
    elif len(argv) == 3 and argv[0] == "make-state":
        print(json.dumps(make_state(argv[1], argv[2])))
    elif len(argv) == 3 and argv[0] == "compare":
        r = compare(argv[1], argv[2])
        print(json.dumps(r, indent=1))
        return 0 if r["match"] else 1
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
