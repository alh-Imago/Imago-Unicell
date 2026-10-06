"""
target_capabilities_v1.py -- ledger #981: what each TARGET can do with the target-agnostic ICM's optional features, so the compiler can refuse at COMPILE time (when it is told the
target) instead of at load time. The ICM itself never names a target: it states the NEED (`second_output`, `second_downstream_mask`); this table says which targets can meet it.

Targets: "std" (the standard VM / fixed-address cells), "flex" (the valid/ack handshake family) and "sub" (the fixed-latency flex-sub family).
  second_output           which cores can deliver a second result word (the adder/subtractor's carry, the multiplier's high word)
  second_downstream_mask  which cores can send that second word to its OWN faces
std: the multiplier's high word exists (sequential, on the same faces as the low word); nothing else. flex: both, on adder and mul. sub: neither.
No target given = no check (the ICM is produced unchanged).
"""
from typing import Dict, Iterable, List, Optional, Set

CAPABILITIES: Dict[str, Dict[str, Set[str]]] = {
    "std": {"second_output": {"mul"}, "second_downstream_mask": set()},
    "flex": {"second_output": {"adder", "mul"}, "second_downstream_mask": {"adder", "mul"}},
    "sub": {"second_output": set(), "second_downstream_mask": set()},
}


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
    return out
