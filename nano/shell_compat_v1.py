"""shell_compat_v1.py — points.md #606: real, RTL-derived shell/core
compatibility data, built directly for Composer per Alan's own real
concern: "a version1 may not work with a version3." Checked by direct
inspection before writing a line of this: v1/v2 shells genuinely lack
`branch_cell`/`sequencer_cell` instantiations in their own real RTL --
not a hypothetical, a hardware fact confirmed against the actual .v
files.

REAL, DELIBERATE CHOICE: this data is DERIVED by scanning the real
`.v` files each time it's asked for, reusing
`project_assemble_v1.discover_instantiated_modules()` directly (the
SAME real, already-proven heuristic scan `#590`'s own compatibility
check already uses) -- not a hand-copied table that could silently
drift out of sync as new shell versions are added. If a `v9` file
shows up in `fpga/verilog/` tomorrow, this module sees it with no
changes needed.

REAL, HONEST SCOPE: this answers "is core type X even INSTANTIATED in
shell Y's own RTL" -- a real, hard yes/no. It does NOT model timing,
ALM cost, or any other real difference between shell versions (those
are `#578`-`#592`'s own separate, already-covered concerns). Different
module VERSIONS implementing the SAME core type across shells (e.g.
`ram_cell_v1` vs `ram_cell_v2`) are reported for information, not
flagged as an incompatibility -- this project's own shared-storage
refactor arc verified those functionally identical via differential
testbenches; only real ABSENCE is a real hazard.
"""

import os
import re
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import project_assemble_v1 as pa  # noqa: E402

_VERILOG_DIR_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fpga", "verilog")

#: real core TYPE name -> the real module-naming pattern that
#: identifies it, whatever version implements it. Matches
#: project_assemble_v1.CORE_REGISTRY's own real type names exactly
#: (ram_cell -> "ram", etc.) except spelled as the short form the DSL/
#: core_select world already uses ("ram", not "ram_cell") -- kept
#: explicit here rather than derived, since the mapping from module
#: name to core_select name isn't itself a simple string transform
#: (unicell_stripped -> "nano").
CORE_TYPE_PATTERNS: Dict[str, "re.Pattern"] = {
    "ram": re.compile(r"^ram_cell_v\d+$"),
    "adder": re.compile(r"^adder_cell_v\d+$"),
    "accumulator": re.compile(r"^accumulator_cell_v\d+$"),
    "comparator": re.compile(r"^compare_cell_v\d+$"),
    "latch": re.compile(r"^latch_cell_v\d+$"),
    "sequencer": re.compile(r"^sequencer_cell_v\d+$"),
    "branch": re.compile(r"^branch_cell_v\d+$"),
    "nano": re.compile(r"^unicell_stripped_v\d+$"),
}

_SHELL_FILE_RE = re.compile(r"^unicell_super_v(\d+)\.v$")


def discover_shell_versions(verilog_dir: Optional[str] = None) -> Dict[str, str]:
    """Real, direct filesystem scan for every real `unicell_super_v<N>.
    v` file present -- deliberately excludes experimental/wrapped
    variants (`unicell_super_v3_wrapped_experimental.v`), which aren't
    real, buildable shell targets. Returns {"v1": "/path/to/
    unicell_super_v1.v", ...}, sorted by version number."""
    verilog_dir = verilog_dir or _VERILOG_DIR_DEFAULT
    versions = {}
    for fname in os.listdir(verilog_dir):
        m = _SHELL_FILE_RE.match(fname)
        if m:
            versions[f"v{m.group(1)}"] = os.path.join(verilog_dir, fname)
    return dict(sorted(versions.items(), key=lambda kv: int(kv[0][1:])))


def supported_cores(shell_path: str) -> Dict[str, List[str]]:
    """Real, RTL-derived: which core TYPES are actually instantiated
    in this one real shell file, and which real module version(s)
    implement each (normally exactly one; more than one is reported
    honestly rather than silently collapsed, since that would itself
    be a real, worth-seeing anomaly)."""
    instantiated = pa.discover_instantiated_modules(shell_path)
    result: Dict[str, List[str]] = {}
    for core_type, pattern in CORE_TYPE_PATTERNS.items():
        matches = sorted(m for m in instantiated if pattern.match(m))
        if matches:
            result[core_type] = matches
    return result


def compatibility_matrix(verilog_dir: Optional[str] = None) -> Dict[str, Dict[str, List[str]]]:
    """The real, full matrix across every real shell version found on
    disk -- {"v1": {"ram": ["ram_cell_v1"], ...}, "v2": {...}, ...}."""
    versions = discover_shell_versions(verilog_dir)
    return {v: supported_cores(path) for v, path in versions.items()}


def check_core_compatible(shell_path: str, core_type: str) -> Tuple[bool, Optional[str]]:
    """Real yes/no + a real, human-readable reason for one specific
    core type against one specific shell file. Returns
    (True, None) if compatible."""
    cores = supported_cores(shell_path)
    if core_type not in cores:
        return False, (
            f"core type '{core_type}' is not instantiated anywhere in "
            f"{os.path.basename(shell_path)} -- a real RTL fact (checked "
            f"directly against the file), not a heuristic guess about "
            f"behavior. Available on this shell: {', '.join(sorted(cores)) or '(none found)'}."
        )
    return True, None
