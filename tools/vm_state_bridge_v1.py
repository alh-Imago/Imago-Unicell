#!/usr/bin/env python3
"""tools/vm_state_bridge_v1.py -- ledger #1159: move a saved mid-flight state between the CARD (the single state file of tools/scan_image_v1.py) and the VM (FlexGrid) for a design compiled from a LaTeX line.
  card/sim state file  ->  VM   : every live register is written into the VM cell of the same name; a division still part-way through is finished with the divider's own step rule (replica of div_cell_v4sa.v) because the VM computes its answer up front.
  VM  ->  state file           : only for a VM state the card's registers can express exactly; otherwise it REFUSES and says which cell and why (it never invents a hardware register).
Looping (the card's wrapper feeds each result back into the inputs) is done here by `LoopDriver`, so a restored VM can be run on and compared with the card/model.
  python3 tools/vm_state_bridge_v1.py to-vm STATE.json [--more 4]       restore the state file into the VM, run on, print the words it produces and compare with the model
  python3 tools/vm_state_bridge_v1.py from-vm OUT.json [--ticks N]      run the VM from the first value for N ticks, write what it holds as a state file (or refuse)
The design is the one in fpga/board_tests_scan_latex/design.json."""
import argparse, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ("tools", "nano"):
    sys.path.insert(0, os.path.join(ROOT, d))
KIT = os.path.join(ROOT, "fpga", "board_tests_scan_latex")
MASK = 0xFFFFFFFF


def hw_name(cell_id):
    return "c_" + cell_id.replace(".", "_")


def load_design(kit=KIT):
    d = json.load(open(os.path.join(kit, "design.json")))
    sm = json.load(open(os.path.join(kit, "SCAN_MAP.json")))
    return d, sm


def build_vm(formula):
    from latex_frontend_v1 import compile_latex
    import flex_grid_v1 as fg
    r = compile_latex(formula)
    grid = fg.FlexGrid(r.result.records, width=32)
    for name, order in r.result.seq_orders.items():          # the caller-side step compile_dag() requires (as llvm_dag_frontend_v1.run_in_vm does)
        for rec in r.result.records:
            if rec.cell_id == f"main.pri_{name}":
                grid.cells[(rec.row, rec.col)].pri_seq_order = order
    pos = {hw_name(rec.cell_id): (rec.row, rec.col) for rec in r.result.records}
    return r, grid, pos


def div_finish(d_reg, q_reg, r_reg, remaining, width=32):
    """The divider's own restoring step (div_cell_v4sa.v, one quotient bit per step) run `remaining` more times; returns (remainder, quotient)."""
    m = (1 << width) - 1
    R, Q = r_reg & m, q_reg & m
    for _ in range(remaining):
        R = ((R << 1) | (Q >> (width - 1))) & m
        Q = (Q << 1) & m
        if R >= d_reg:
            R -= d_reg
            Q |= 1
    return R, Q


def _regs(state):
    return {c["cell"]: {r["name"]: r["value"] for r in c["registers"]} for c in state["cells"]}


def _types(state):
    return {c["cell"]: c["type"] for c in state["cells"]}


def fix_constants(grid, pos, constants):
    """The flex hardware makes a constant a FIXED ram that offers its word continuously; the compiled record is a flowing ram preloaded with a word offered once (so the VM, built for one evaluation, runs dry after a few rounds).
    For a looped run mirror the hardware: mark those cells fixed. Returns notes."""
    notes = []
    for n in constants or []:
        if n in pos:
            c = grid.cells[pos[n]]
            c.ram_fixed_mode, c.ram_data_valid = True, True
            notes.append("%s: made a fixed (continuous) constant, as the card builds it" % n)
    return notes


def sequence_joins(grid, pos, joins):
    """The card's join cell takes operand A and operand B together; the VM's priority cell in front of it picks one word at a time by rank, so with the constant and the product both waiting it could serve the
    constant twice. Put each such priority cell into sequence mode (A's face first, then B's), which is what a join amounts to. Returns notes. VM configuration only; no card register is involved."""
    notes = []
    for j, ab in joins.items():
        if j not in pos:
            continue
        jr, jc = pos[j]
        p = grid.cells.get((jr, jc - 1))
        if p is None or p.core != "priority":
            continue                                  # a join with no priority cell in front of it (the VM's own delivery applies)
        def face(name):
            r, c = pos[name]
            return {(-1, 0): 0, (1, 0): 1, (0, 1): 2, (0, -1): 3}[(r - (jr), c - (jc - 1))]
        try:
            order = (face(ab["A"]), face(ab["B"]))
        except KeyError:
            continue
        if not p.pri_seq_order:
            p.pri_scheduling_mode, p.pri_seq_order, p.pri_seq_index = 2, order, 0
            notes.append("%s: priority cell at %s put in sequence mode %s (operand A, then B)" % (j, (jr, jc - 1), order))
    return notes


def settle_joins(state, grid, pos, joins):
    """The card's join cells (adder / mul / div) fire when BOTH operand cells are presenting and the cell's own output is free; the VM takes operands one at a time. A saved state with both operands waiting
    is one clock short of that firing, so fire it here: consume both operand words, put the result in the cell exactly as the VM's own delivery does."""
    notes, regs = [], _regs(state)
    for j, ab in joins.items():
        if j not in pos or ab["A"] not in regs or ab["B"] not in regs:
            continue
        cell, ca, cb = grid.cells[pos[j]], grid.cells[pos[ab["A"]]], grid.cells[pos[ab["B"]]]
        busy_out = {"adder": "adder_data_valid", "mul": "mul_data_valid", "div": "div_data_valid"}[cell.core]
        if getattr(cell, busy_out) or not (ca.ram_data_valid and cb.ram_data_valid):
            continue
        va, vb = ca.ram_data_reg, cb.ram_data_reg
        h = cell._handler()
        h.deliver(cell, {}, va)           # first operand into the cell's A register (the VM's own one-at-a-time delivery) ...
        h.deliver(cell, {}, vb)           # ... then the second, which fires it
        ca.ram_data_valid = cb.ram_data_valid = False
        notes.append("%s: both operands were waiting (%d, %d) -> fired" % (j, va, vb))
    return notes


def state_to_vm(state, grid, pos, joins=None):
    """Write the state file's live registers into the VM cells. Returns notes (what was finished/skipped)."""
    notes, regs, types = [], _regs(state), _types(state)
    for name, rg in regs.items():
        cell = grid.cells[pos[name]]
        t = types[name]
        if t == "ram":
            if rg["pending"] or rg["have"]:
                cell.ram_data_reg, cell.ram_data_valid = rg["data_reg"] & MASK, True
        elif t == "adder":
            if rg["pending_c"]:
                raise ValueError("%s: a carry word in flight is not mapped to the VM yet" % name)
            if rg["pending"]:
                cell.adder_out_buffer, cell.adder_data_valid = rg["out_buffer"], True
        elif t == "mul":
            if rg["pending_hi"]:
                raise ValueError("%s: a high word in flight is not mapped to the VM yet" % name)
            if rg["pending"]:
                cell.mul_out_buffer, cell.mul_data_valid = rg["out_buffer"], True
        elif t == "div":
            prim = bool(cell.div_remainder_primary)
            if rg["busy"]:
                R, Q = div_finish(rg["d_reg"], rg["q_reg"], rg["r_reg"], rg["remaining"])
                first, second = (R, Q) if prim else (Q, R)
                cell.div_out_buffer, cell.div_captured_second = first, second
                cell.div_data_valid, cell.div_busy, cell.div_delivering_second = True, rg["remaining"], False
                notes.append("%s: division with %d step(s) left finished by the divider's own rule -> %d" % (name, rg["remaining"], first))
            elif rg["pending"] or rg["pending_r"]:
                if rg["pending_r"]:
                    raise ValueError("%s: a remainder word in flight is not mapped to the VM yet" % name)
                cell.div_out_buffer, cell.div_data_valid, cell.div_busy = rg["out_buffer"], True, 0
        else:
            raise ValueError("%s: cell type %s has no VM mapping yet" % (name, t))
    return notes + settle_joins(state, grid, pos, joins or {})


class LoopDriver:
    """What the card's loop wrapper does around the grid: take each result, feed it back into the inputs (all sites that read the argument)."""
    def __init__(self, grid, sites, result_pos, closing_word=0, has=0, steps=0):
        self.g, self.sites, self.res = grid, sites, result_pos
        self.pending_feed = closing_word if has else None
        self.steps, self.last = steps, closing_word
        self.out = []

    def _feed(self, v):
        cs = [self.g.cells[p] for p in self.sites]
        if any(c.ram_data_valid for c in cs):
            return False
        for c in cs:
            c.ram_data_reg, c.ram_data_valid = v & MASK, True
        return True

    def step(self, limit=4000):
        for _ in range(limit):
            if self.pending_feed is not None and self._feed(self.pending_feed):
                self.pending_feed = None
            c = self.g.cells[self.res]
            if c.div_data_valid and c.div_busy == 0 and self.pending_feed is None:
                v = c.div_out_buffer
                c.div_data_valid, c.div_delivering_second = False, False
                self.steps += 1; self.last = v; self.out.append(v); self.pending_feed = v
                return v
            self.g.tick()
        raise RuntimeError("no result within %d ticks" % limit)


def vm_to_state(grid, pos, drv, scan_map, design, made_by="VM (FlexGrid)"):
    """Build a state file from the VM as it stands (right after a driver step). REFUSES, naming the cell and why, if the VM holds something the card's registers cannot express exactly."""
    import scan_image_v1 as si
    zero = dict(ses=0, image=(bytes(256)).hex(), cut=None, design=design["name"], layout=si.layout_id(scan_map), made_by=made_by)
    st = si.pack(zero, scan_map, design["formula"])
    byname = {c["cell"]: {r["name"]: r for r in c["registers"]} for c in st["cells"]}
    mapped = set(pos[n] for n in byname) | set(pos[n] for n in design.get("constants", []) if n in pos)
    problems = []
    for p, c in sorted(grid.cells.items()):
        if p in mapped:
            continue
        if c.core == "priority":
            if c.pri_data_valid:
                problems.append("priority cell at %s holds a word (%d): the card has no such cell, its eliminated by the assembler" % (p, c.pri_data_reg))
        else:
            problems.append("cell %s (%s) has no counterpart on the card" % (p, c.core))
    for name, regs in byname.items():
        c = grid.cells[pos[name]]
        t = {k: v for k, v in [(cc["cell"], cc["type"]) for cc in st["cells"]]}[name]
        if t == "ram":
            if c.ram_data_valid:
                regs["pending"]["value"], regs["data_reg"]["value"] = 1, c.ram_data_reg & MASK
        elif t == "adder":
            if c.adder_a_arrived:
                problems.append("%s: one operand has arrived and the other has not; the card's adder takes both together and has no register for that" % name)
            if c.adder_data_valid:
                if c.adder_carry_mode:
                    problems.append("%s: carry mode word in flight is not mapped yet" % name)
                regs["pending"]["value"], regs["out_buffer"]["value"] = 1, c.adder_out_buffer
        elif t == "mul":
            if c.mul_a_arrived:
                problems.append("%s: one operand has arrived and the other has not; the card's multiplier has no register for that" % name)
            if c.mul_data_valid:
                if c.mul_wide_mode:
                    problems.append("%s: wide mode word in flight is not mapped yet" % name)
                regs["pending"]["value"], regs["out_buffer"]["value"] = 1, c.mul_out_buffer
        elif t == "div":
            if c.div_a_arrived:
                problems.append("%s: one operand has arrived and the other has not; the card's divider has no register for that" % name)
            if c.div_data_valid:
                if c.div_busy:
                    problems.append("%s: division still counting (%d left) in the VM, which computes its answer up front; the card would need the half-way registers, which the VM does not have" % (name, c.div_busy))
                elif c.div_delivering_second or getattr(c, "div_second_output", False):
                    problems.append("%s: second (remainder) word is not mapped yet" % name)
                else:
                    regs["pending"]["value"], regs["out_buffer"]["value"] = 1, c.div_out_buffer
    if problems:
        raise ValueError("this VM state cannot be handed to the card:\n  " + "\n  ".join(problems))
    word = drv.last
    st["closing"].update(word=word & MASK, has=1 if drv.pending_feed is not None else 0, steps=drv.steps)
    st["cut"] = None
    return st


def vm_run(formula_dir=KIT, z0=None):
    d, sm = load_design(formula_dir)
    r, grid, pos = build_vm(d["formula"])
    notes = fix_constants(grid, pos, d.get("constants")) + sequence_joins(grid, pos, d.get("joins") or {})
    drv = LoopDriver(grid, r.result.arg_injections["v_z"], r.result.result_cell, d["z0"] if z0 is None else z0, 1, 0)
    return d, sm, r, grid, pos, drv, notes


def run_on(state, more, kit=KIT):
    d, sm = load_design(kit)
    if state.get("layout") != None and state["design"] != d["name"]:
        sys.exit("REFUSED: state file is design %r, this design is %r" % (state["design"], d["name"]))
    r, grid, pos = build_vm(d["formula"])
    notes = fix_constants(grid, pos, d.get("constants")) + sequence_joins(grid, pos, d.get("joins") or {}) + state_to_vm(state, grid, pos, d.get("joins"))
    cl = state["closing"]
    drv = LoopDriver(grid, r.result.arg_injections["v_z"], r.result.result_cell, cl["word"], cl["has"] & 1, cl["steps"])
    return d, notes, drv, [drv.step() for _ in range(more)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("mode", choices=["to-vm", "from-vm"]); ap.add_argument("file")
    ap.add_argument("--more", type=int, default=4, help="to-vm: how many more results to take from the VM")
    ap.add_argument("--steps", type=int, default=3, help="from-vm: results taken before the cut"); ap.add_argument("--ticks", type=int, default=10, help="from-vm: VM ticks after the last result was fed back")
    a = ap.parse_args()
    import scan_image_v1 as si
    d, sm = load_design()
    if a.mode == "to-vm":
        st = si.load_state_or_raw(a.file, sm, d)
        d, notes, drv, outs = run_on(st, a.more)
        f = eval("lambda z: " + d["step"]); z = st["closing"]["word"]; want = []
        for _ in range(a.more):
            z = f(z); want.append(z)
        for n in notes:
            print("note:", n)
        print("VM produced %s, model %s -> %s" % (outs, want, "PASS" if outs == want else "FAIL"))
        sys.exit(0 if outs == want else 1)
    d, sm, r, grid, pos, drv, notes = vm_run()
    for _ in range(a.steps):
        drv.step()
    if drv.pending_feed is not None:
        drv._feed(drv.pending_feed); drv.pending_feed = None
    for _ in range(a.ticks):
        grid.tick()
    try:
        st = vm_to_state(grid, pos, drv, sm, d)
    except ValueError as e:
        sys.exit("REFUSED: %s" % e)
    json.dump(st, open(a.file, "w"), indent=1)
    print("VM state after %d results + %d ticks written to %s (closing word %d, %d steps); restore it on the card with --restore-only --in" % (a.steps, a.ticks, a.file, st["closing"]["word"], st["closing"]["steps"]))


if __name__ == "__main__":
    main()
