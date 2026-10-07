#!/usr/bin/env python3
"""
flexsub_compile_v1.py -- compile LLVM IR for the SUB / FLEX targets (Alan's ruling #929, option C, narrowed:
"this really only affects the sub and flex systems, the nano is a separate mechanism anyway").

The stock compiler (nano/llvm_cli_v1.py, untouched) orders the operands of a non-commutative op (x - y) with
the VM-only "sequenced channel" priority mode (scheduling_mode 2). No RTL implements that mode (the mainline
priority cell has a 1-bit strict/weighted mode), and the saved ICM v3 does not even record the turn order, so
such a file cannot run from itself (#926). This tool uses the stock compiler as a library and rewrites each
mode-2 priority into STRICT mode 0 with explicit RANKS that encode the SAME order the compiler chose
(first = operand A = rank 0, second = operand B = rank 1). Everything the file needs is then already in the
format; no format change.

Why ranks are enough HERE and not on the mainline: on the mainline a priority captures the FIRST ARRIVAL and
rank only breaks ties (#770), which is why #771 pads paths. The sub/flex assembler (flexsub_icm_generate_v1)
eliminates the priority cell and equalises arrival EXACTLY itself (every cell is a known 1 cycle), so there
rank is free to define operand identity -- #771's equalisation, performed where the exact timing is known.
The calling convention this relies on (all arguments of a call presented on the same cycle) is inherent to
the fixed-latency targets. A file written by this tool is NOT meant for the mainline VM/hardware path.

Usage: python3 tools/flexsub_compile_v1.py prog.ll [-o out.icm]
"""
import argparse
import copy
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "nano"))
sys.path.insert(0, REPO_ROOT)

DIR_LETTER = {0: "n", 1: "s", 2: "e", 3: "w"}      # icm_v3._DIR_BITS: n=0, s=1, e=2, w=3


def retarget_records(records, seq_orders):
    """Return (new_records, changed_cell_ids). A sequenced priority whose file already records its turn order (#1018: sequence_len / sequence_0..) is KEPT as it is -- nothing to change.
    Otherwise each priority named by `seq_orders` (label -> (dirA, dirB), direction indices; an older file that does not record the order) becomes scheduling_mode 0 with rank 0 on dirA's face and rank 1 on dirB's. Records are copied, never
    mutated in place. Raises ValueError if a named priority is missing or not in sequenced mode."""
    recs = copy.deepcopy(records)
    byid = {r.cell_id: r for r in recs}
    changed = []
    for label, (da, db) in seq_orders.items():
        cid = next((c for c in (f"main.pri_{label}", f"pri_{label}") if c in byid), None)
        if cid is None:
            raise ValueError(f"seq_orders names priority {label!r} but no cell main.pri_{label} exists")
        cfg = byid[cid].core_config
        if cfg.get("scheduling_mode") != 2:
            raise ValueError(f"{cid}: expected scheduling_mode 2, found {cfg.get('scheduling_mode')!r}")
        if da == db or da not in DIR_LETTER or db not in DIR_LETTER:
            raise ValueError(f"{cid}: bad sequence order {(da, db)}")
        if int(cfg.get("sequence_len", 0)) == 2 and (int(cfg.get("sequence_0", -1)), int(cfg.get("sequence_1", -1))) == (da, db):
            continue        # ledger #1018: the file RECORDS the turn order itself, so the faithful sequenced channel is kept (the generator turns it into operand wiring / the RTL core)
        cfg["scheduling_mode"] = 0
        for d in DIR_LETTER.values():
            cfg[f"priority_rank_{d}"] = 0
        cfg[f"priority_rank_{DIR_LETTER[db]}"] = 1          # B loses; A (rank 0) is first
        changed.append(cid)
    return recs, changed


def compile_for_flexsub(source_text, name="prog"):
    """(IcmV3File, report, diagnostics). report = {'retargeted': [...], 'priorities': n}. result is None on a compile error."""
    from icm_v3 import IcmV3File
    from llvm_dag_frontend_v1 import compile_llvm_via_dag
    result, diagnostics = compile_llvm_via_dag(source_text)
    if result is None:
        return None, None, diagnostics
    recs, changed = retarget_records(result.records, result.seq_orders)
    at = {(r.row, r.col): r for r in recs}
    # The saved ICM does not say which cell is the program's OUTPUT -- `result_cell` lives only in the compiler's memory (the same class of omission as
    # the sequenced-priority order, #926). A result that ALSO feeds unused logic (an unrolled loop leaves dead iterations hanging off it) looks, from the
    # file alone, exactly like a design whose last cell is the result. So record it with the format's own field: io_name is "a genuine external
    # data entry/exit point" (icm_v3, #667). The name is `result`; the generator treats it as authoritative and prunes whatever cannot reach it.
    rc = at.get(tuple(result.result_cell)) if getattr(result, "result_cell", None) is not None else None
    if rc is not None and not rc.io_name:
        rc.io_name = "result"
    step = {"n": (-1, 0), "s": (1, 0), "e": (0, 1), "w": (0, -1)}

    def entry_cell(pos):
        """The compiler's injection position can be a relay next to the consumer; follow the (single-source) upstream
        chain back to the cell with no upstream face -- the real entry the generated design exposes as a port."""
        seen = set()
        while True:
            r = at[pos]
            ups = [str(u).lower() for u in (r.core_config.get("upstream_mask") or [])]
            if not ups or pos in seen:
                return r.cell_id
            seen.add(pos)
            pos = (pos[0] + step[ups[0]][0], pos[1] + step[ups[0]][1])

    report = {"retargeted": changed, "priorities": sum(1 for r in recs if r.core == "priority"),
              # function argument -> the entry cell(s) that must be driven with its value (host-side contract)
              "arg_cells": {a: [entry_cell(p) for p in ps] for a, ps in result.arg_injections.items()}}
    return IcmV3File(name=name, records=recs), report, diagnostics


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("-o", "--output")
    ap.add_argument("--min-bit-width", type=int, default=None, metavar="N",
                    help="Declare, in the saved ICM's header, the MINIMUM bit width this design needs (ledger #958). Absent = 32. A requirement: building wider always satisfies it.")
    a = ap.parse_args(argv)
    try:
        text = open(a.source).read()
    except OSError as e:
        print(f"error: could not read {a.source!r}: {e}", file=sys.stderr)
        return 2
    name = os.path.splitext(os.path.basename(a.source))[0]
    f, report, diags = compile_for_flexsub(text, name)
    for d in diags:
        print(d.format(text.splitlines()), file=sys.stderr)
    if f is None:
        print("compile failed", file=sys.stderr)
        return 1
    out = a.output or os.path.splitext(a.source)[0] + ".icm"
    if a.min_bit_width is not None:
        import icm_width_v1 as _w
        try:
            f.min_bit_width = _w.validate_min_bit_width(a.min_bit_width)   # declared in the saved file's header; covered by its integrity hash
        except _w.IcmWidthError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
    f.save(out)
    print(f"compiled '{name}' for sub/flex -> {out} ({len(f.records)} cells; {len(report['retargeted'])} of "
          f"{report['priorities']} priority cells moved from sequenced mode 2 to strict mode 0 + ranks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
