"""
host_registry_v1.py — the real, standalone host-side resource registry
(points.md #400), closing a genuine gap Alan named directly: "the host
has to keep a list of resources and what has been used... when the
loader initiates it has to query the host system for that information
... every time something is loaded or unloaded the host system has to
keep a record of resources that are in use at any one time."

Checked directly before building this (not assumed): the CURRENT
implementation has no such thing. `nano/workbench_v1.py`'s own
`WorkbenchController` manipulates `self.session.grid.cells` (a raw
dict on the `SuperGrid` object) DIRECTLY -- `bind_shape()` reads it,
`load_region()` writes into it after a successful placement,
`clear_region()` pops entries out of it. This works, but it is NOT a
real, separate, queryable registry -- it's ad-hoc bookkeeping tightly
coupled to one specific workbench session, not something the loader
(or any other future host-side consumer, e.g. a real host driver
talking to actual hardware) could consult independently.

This module is deliberately GENERIC -- it has zero knowledge of grids,
sessions, or workbenches, matching `loader_v1.py`'s own real precedent
(`#375`) for how a shared, reusable piece of infrastructure should be
built: operating purely on `(row, col)` positions and opaque resource
IDs, so anything that needs to track "what's currently placed" can use
it, not just the workbench.

Real, deliberate scope: this tracks POSITION occupancy (the same real
concern `loader_v1.py`'s own `bind_shape()` already needs), not
arbitrary resource types (ALM budget, DSP columns, etc.) -- those
remain real, separate, unbuilt tracking concerns for whenever they're
actually needed, not assumed solved here.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple


class ResourceConflictError(Exception):
    """A real, specific exception -- raised when a load would occupy a
    position already claimed by another registered resource, or when
    a resource_id is reused/unloaded incorrectly. Never silently
    overwrites or ignores a conflict."""


class HostResourceRegistry:
    """The real, queryable authority on what's currently placed. A
    genuinely SEPARATE object from any grid/session -- something that
    represents "the host" can hold exactly one of these and have it be
    the real, single source of truth for occupancy, queried by the
    loader before placing anything and updated on every real load/
    unload, matching Alan's own framing precisely."""

    def __init__(self) -> None:
        self._occupied: Dict[Tuple[int, int], str] = {}
        self._resources: Dict[str, Dict[str, object]] = {}

    def query_occupied(self) -> Dict[Tuple[int, int], object]:
        """What the loader actually needs: a real occupancy map in the
        EXACT shape `loader_v1.py`'s own `bind_shape()`/
        `find_auto_placement()`/`find_dsp_aware_placement()` already
        expect (`Dict[(row, col), Any]`) -- this registry is a drop-in
        source for that parameter, not a new interface the loader
        needs to learn. A real copy is returned, not a live reference
        -- callers can't accidentally mutate the registry's own real
        state by mutating what they got back."""
        return dict(self._occupied)

    def register_load(self, resource_id: str, positions: Iterable[Tuple[int, int]],
                       metadata: Optional[dict] = None) -> None:
        """A real load event -- the resource now genuinely occupies
        these positions, and the registry's own record of "what's in
        use" updates to reflect it. Real, deliberate validation: a
        reused `resource_id` or a genuine position conflict with an
        ALREADY-registered resource is a real error, not silently
        overwritten or merged."""
        positions = list(positions)
        if resource_id in self._resources:
            raise ResourceConflictError(
                f"resource {resource_id!r} is already registered -- "
                f"unload it first before loading it again"
            )
        conflicts = [p for p in positions if p in self._occupied]
        if conflicts:
            raise ResourceConflictError(
                f"cannot load {resource_id!r} -- position(s) {sorted(conflicts)} "
                f"already occupied by {sorted({self._occupied[p] for p in conflicts})}"
            )
        for p in positions:
            self._occupied[p] = resource_id
        self._resources[resource_id] = {"positions": positions, "metadata": dict(metadata or {})}

    def register_unload(self, resource_id: str) -> None:
        """A real unload event -- frees every position this resource
        held. A real, clear error if the resource_id was never
        registered, or was already unloaded -- never a silent no-op."""
        if resource_id not in self._resources:
            raise ResourceConflictError(
                f"cannot unload {resource_id!r} -- it is not currently registered"
            )
        for p in self._resources[resource_id]["positions"]:
            del self._occupied[p]
        del self._resources[resource_id]

    def list_resources(self) -> List[str]:
        """Every resource_id currently registered -- a real, live
        inventory, not a snapshot from load time."""
        return list(self._resources.keys())

    def resource_info(self, resource_id: str) -> Dict[str, object]:
        """The real, current positions and metadata for one registered
        resource. A real KeyError if it isn't registered -- never
        returns a default/empty result for something that doesn't
        exist."""
        if resource_id not in self._resources:
            raise KeyError(resource_id)
        info = dict(self._resources[resource_id])
        info["positions"] = list(info["positions"])   # a real copy, not the live list
        return info

    def total_occupied_cells(self) -> int:
        return len(self._occupied)
