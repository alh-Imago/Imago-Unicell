"""
target_capabilities_v1.py -- ledger #981: what each TARGET can do with the target-agnostic ICM's optional features, so the compiler can refuse at COMPILE time (when it is told the
target) instead of at load time. The ICM itself never names a target: it states the NEED (`second_output`, `second_downstream_mask`); this table says which targets can meet it.

Targets: "std" (the standard VM / fixed-address cells), "flex" (the valid/ack handshake family) and "sub" (the fixed-latency flex-sub family).
  second_output           which cores can deliver a second result word (the adder/subtractor's carry, the multiplier's high word)
  second_downstream_mask  which cores can send that second word to its OWN faces
std: the multiplier's high word exists (sequential, on the same faces as the low word); nothing else. flex: both, on adder and mul. sub: neither.
shift amount (add-on): ONE number in the ICM (`shift_amt`, direction beside it). flex/nano: ANY amount 0..31 (a wired shift; coarse + fine are just how it is programmed). std: coarse taps (+ fine 0-3).
sub: coarse taps only, no fine. A number the target cannot make would be a silent no-op in the VM/RTL, so the compiler refuses it when the target is named (ledger #986).
No target given = no check (the ICM is produced unchanged).
"""
from typing import Dict, Iterable, List, Optional, Set

CAPABILITIES: Dict[str, Dict[str, Set[str]]] = {
    "std": {"second_output": {"mul"}, "second_downstream_mask": set()},
    "flex": {"second_output": {"adder", "mul"}, "second_downstream_mask": {"adder", "mul"}},
    "sub": {"second_output": set(), "second_downstream_mask": set()},
}
COARSE_TAPS = (1, 2, 4, 8, 12, 16, 20, 24, 28)
FINE_OK = {"std": True, "flex": True, "sub": False}      # may shift_fine be used
FREE_SHIFT = {"std": False, "flex": True, "sub": False}   # any shift_amt 0..31


def check_records(records: Iterable, target: Optional[str]) -> List[str]:
    """Problems (empty = fine) of running `records` (IcmV3Record-like: cell_id, core, core_config) on `target`. A None target checks nothing; an unknown target is an error."""
    if target is None:
        return []
    if target not in CAPABILITIES:
        return [f"unknown target {target!r}: known targets are {sorted(CAPABILITIES)}"]
    caps, out = CAPABILITIES[target], []
    for r in records:
        cfg = r.core_config or {}
        for feature in ("second_output", "second_downstream_mask"):
            if cfg.get(feature) and r.core not in caps[feature]:
                have = sorted(caps[feature])
                out.append(f"{r.cell_id}: {feature} on a {r.core} -- target {target!r} cannot do that ("
                           + (f"it supports {feature} on {have}" if have else f"it has no {feature} at all") + ")")
        ad = getattr(r, "addon_config", None) or {}
        if ad.get("shift_en"):
            amt, fine = ad.get("shift_amt", 0), ad.get("shift_fine", 0) & 3
            if amt and not FREE_SHIFT[target] and amt not in COARSE_TAPS:
                out.append(f"{r.cell_id}: shift_amt {amt} -- target {target!r} has only the coarse shifts {list(COARSE_TAPS)} (that amount would silently do nothing)")
            if fine and not FINE_OK[target]:
                out.append(f"{r.cell_id}: shift_fine {fine} -- target {target!r} has no fine shift")
    return out
