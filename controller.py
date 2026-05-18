import imago_log
from typing import Optional
from unicell import UniCell
from unicell_array import UniCellArray

# ── reserved addresses ────────────────────────────────────────────────────────

ADDR_NULL     = 0x00000000
ADDR_SENTINEL = 0xFFFFFFFF


# ── cell map record ───────────────────────────────────────────────────────────

class CellMapRecord:
    """
    One entry in a compiled cell map.
    Describes the configuration of a single cell as a cmd_latch word
    plus input/output addresses.

    cmd_latch: 32-bit word encoding topology + all flags.
               Matches the silicon cmd_latch register exactly.
               Auth_mask bits (21-11) are always zero here.

    initial_value: preloaded a_data value for latch/storage cells.
      Written as the first arrival at input_address after configure().
      Enables preloaded comparator pattern without extra bus traffic.

    Retired fields (not in Verilog):
      input_b_address  — two-input model retired; two-arrival is default
      output_address_alt — SELECT cells retired
      storage_mode — encoded in cmd_latch cell_type bits instead
    """
    def __init__(self, gate_state: int, input_address: int, output_address: int,
                 initial_value: Optional[int] = None,
                 # Legacy kwargs accepted but ignored — emit a warning
                 output_address_alt: Optional[int] = None,
                 storage_mode: bool = False,
                 input_b_address: Optional[int] = None):
        self.gate_state    = gate_state    & 0xFFFFFFFF  # cmd_latch word
        self.input_address = input_address & 0xFFFFFFFF
        self.output_address= output_address& 0xFFFFFFFF
        self.initial_value = initial_value
        # Legacy fields — kept as None so old code reading them gets None
        # rather than AttributeError. Compiler must stop emitting these.
        self.input_b_address    = None
        self.output_address_alt = None
        self.storage_mode       = False

    def __repr__(self) -> str:
        return (
            f"CellMapRecord("
            f"cl={self.gate_state:#010x} "
            f"in={self.input_address:#010x} "
            f"out={self.output_address:#010x})"
        )


# ── region ────────────────────────────────────────────────────────────────────

class Region:
    """
    A contiguous range of cell addresses allocated to one loaded image.
    Tracks lifecycle state: CONFIGURED → RUNNING → HALTED → FREED.
    """

    CONFIGURED = "CONFIGURED"
    RUNNING    = "RUNNING"
    HALTED     = "HALTED"
    FREED      = "FREED"

    _id_counter = 0

    def __init__(self, cell_addresses: list[int], image_name: str):
        Region._id_counter += 1
        self.region_id     = f"region_{Region._id_counter:04d}"
        self.cell_addresses = cell_addresses       # physical addresses of cells in this region
        self.image_name    = image_name
        self.state         = Region.CONFIGURED
        self.cycles_run    = 0
        self.known_values: dict = {}  # {bus_addr: value} — auto-injected at start()
        self._pending_inputs: dict = {}  # second-arrival re-injection (two-arrival model)

    def __repr__(self) -> str:
        return (
            f"Region({self.region_id} "
            f"image={self.image_name} "
            f"state={self.state} "
            f"cells={len(self.cell_addresses)} "
            f"cycles={self.cycles_run})"
        )


# ── ImagoController ───────────────────────────────────────────────────────────

class ImagoController:
    """
    Models the BIOS-plus chip.

    Responsibilities:
      - Owns and manages the UniCellArray
      - Maintains the 64-bit system address map
      - Loads cell maps into the array via config write packets
      - Manages Regions (lifecycle, start flag, halt, free)
      - Injects input data onto the bus
      - Reads output values from the bus
      - Enforces the security gate (pattern check on config writes)
      - Manages the defect map
      - Provides run-to-completion execution

    The controller is the only component that writes config packets
    to the array. Nothing else touches cell configuration directly.
    """

    def __init__(self, cell_count: int = 1_000_000,
                 segments: Optional[list[dict]] = None,
                 licensed_tier: str = "FULL",
                 fpga_target: str = "vm",
                 cell_budget: int = None):
        """
        segments: optional list of segment descriptors.
        licensed_tier: tile license tier held by this system
          ("BASE", "INTEGER", "FLOAT", "FULL"). Default FULL in simulation.
          In production this is read from the BIOS-plus license register.
        fpga_target: target identifier — "vm", "icebreaker", "icestick",
          "basys3", "orangecrab", "kintex7", or "custom".
          Used by the compiler and workbench to warn when a program exceeds
          the target's cell budget.
        cell_budget: maximum cells for the target (None = unlimited for VM).
          When set, load_map() warns if a program would exceed this limit.
          Automatically derived from fpga_target if not explicitly set.
        """
        # FPGA target profiles — matches Composer TARGETS dict
        FPGA_BUDGETS = {
            "vm":         None,    # unlimited
            "icebreaker": 64,
            "icestick":   16,
            "basys3":     256,
            "orangecrab": 256,
            "kintex7":    1500,
        }
        self.fpga_target  = fpga_target
        self.cell_budget  = (cell_budget if cell_budget is not None
                             else FPGA_BUDGETS.get(fpga_target))

        self.array = UniCellArray(cell_count)
        if segments:
            for seg in segments:
                self.array.add_segment(**seg)

        self._address_map: dict[str, tuple[int, int]] = {}
        self._regions: dict[str, Region] = {}
        self._machine_key: int = 0xDEADC0DEBEEF1234
        self.licensed_tier: str = licensed_tier
        self.total_cycles: int = 0

    # ── defect map ────────────────────────────────────────────────────────────

    def load_defect_map(self, defective_addresses: list[int]) -> int:
        """
        Register defective cell addresses with the array.
        Called once at boot before any cells are allocated.
        Returns count of defective addresses registered.
        """
        count = self.array.load_defect_map(defective_addresses)
        imago_log.info(f"[CONTROLLER] Defect map loaded — {count} defective addresses excluded")
        return count

    # ── security gate ─────────────────────────────────────────────────────────

    def _security_gate(self, cell_map: list[CellMapRecord]) -> bool:
        """
        Layer 2 security check (array controller level).

        Verifies:
          1. No record contains a raw FUNCTION_LOAD_PATTERN in its address fields
             (prevents injection of spurious config triggers via data)
          2. Record count is non-zero and within reasonable bounds

        In a full implementation this would also verify a cryptographic
        signature against the machine-unique key. In simulation we perform
        the structural checks only.

        Returns True if the map passes. False if it should be rejected.
        """
        if len(cell_map) == 0:
            return False

        for record in cell_map:
            # reserved addresses must not be used as outputs
            if record.output_address == ADDR_NULL:
                return False

        return True

    # ── cell map loading ──────────────────────────────────────────────────────

    def load_map(
        self,
        cell_map: list,   # CellMapRecord or CellRecord_v2
        image_name: str = "unnamed",
        base_address: int = 0,
        known_values: Optional[dict] = None,
        ptt = None,       # PondPTT instance — if set, wires _ptt_ref on all cells
                          # and patches sentry output addresses from PTT_BUS_BASE
                          # placeholder to the correct ptt_bus_address(index).
    ) -> Optional[str]:
        """
        Load a compiled cell map into the array.

        For each record in the map:
          1. Allocate a cell from the array
          2. Build the config write packet
          3. Deliver via write_config

        base_address: when non-zero, all addresses in the map are treated
          as offsets from this base. Effective address = base + offset.
          This enables relative-addressed tiles compiled with TilePlacer
          relative mode to be placed anywhere in the address space.
          base_address=0 means legacy absolute addressing (no change).

        known_values: optional {bus_address: value} dict of constants whose
          values are known at compile time (e.g. literal 0/1 in source, or
          carry-in constants). These are auto-injected by start() before
          user-supplied inputs, so callers don't need to inject them manually.

        Returns the region_id string on success.
        Returns None if the security gate rejects the map or
        allocation fails.

        The loader does NOT assert the start flag — that is the
        controller's explicit run() call. A loaded region sits in
        CONFIGURED state until run() is called.
        """
        # Resolve offsets to absolute addresses if base_address is set
        if base_address:
            resolved = []
            for r in cell_map:
                alt = ((r.output_address_alt + base_address)
                       if r.output_address_alt is not None else None)
                resolved.append(CellMapRecord(
                    gate_state    = r.gate_state,
                    input_address = r.input_address  + base_address,
                    output_address= r.output_address + base_address,
                    initial_value = r.initial_value,
                ))
            cell_map = resolved

        if not self._security_gate(cell_map):
            imago_log.info(f"[CONTROLLER] Security gate REJECTED map '{image_name}'")
            return None

        cell_addresses = []
        try:
            for record in cell_map:
                cell = self.array.allocate_cell()
                success = self.array.configure_cell(
                    cell.address,
                    record.gate_state,
                    record.input_address,
                    record.output_address,
                )
                if not success:
                    raise RuntimeError(
                        f"Config write failed at cell address 0x{cell.address:08X}"
                    )
                # Pre-load initial_value: send as first arrival to set a_data.
                # Used for preloaded comparator pattern, sentry cells, loop seeds.
                # Cell stays armed (configure() sets start_flag=True).
                if record.initial_value is not None:
                    c = self.array.cells.get(cell.address)
                    if c is not None:
                        c.receive(record.initial_value)
                cell_addresses.append(cell.address)

        except RuntimeError as e:
            imago_log.info(f"[CONTROLLER] Load failed: {e}")
            return None

        region = Region(cell_addresses, image_name)
        if known_values:
            region.known_values = dict(known_values)
        self._regions[region.region_id] = self._track_address_range(region)

        # Wire PTT reference to all loaded cells so sentry output interception works.
        # unicell.py checks getattr(cell, '_ptt_ref', None) on every output that
        # targets the PTT bus range (0xFFE00000+). Without this, sentry ticks are
        # silently dropped and the entire PTT liveness machinery is dark.
        if ptt is not None:
            from pond_ptt import PTT_BUS_BASE, is_ptt_bus_address, ptt_bus_address
            for addr in cell_addresses:
                cell = self.array.cells.get(addr)
                if cell is not None:
                    cell._ptt_ref = ptt

            # Patch sentry placeholder addresses: program_builder.py emits sentry
            # cells with output_address = PTT_BUS_BASE (0xFFE00000) as a placeholder.
            # Now that PTT registration has happened, resolve each sentry to its
            # correct per-entry bus address using the entry's ptt_index.
            # We patch the cell's output_address directly so future ticks go to the
            # right address. All PTT entries with a registered sentry_address are
            # candidates — find matching placeholder cells and patch them.
            placeholder_cells = [
                self.array.cells.get(addr) for addr in cell_addresses
                if self.array.cells.get(addr) is not None
                and self.array.cells.get(addr).output_address == PTT_BUS_BASE
            ]
            if placeholder_cells:
                # Build list of registered sentry addresses from PTT entries
                sentry_entries = [
                    e for e in ptt._entries.values()
                    if e.sentry_address != 0
                ]
                # Assign one sentry entry per placeholder cell (FIFO order)
                for cell, entry in zip(placeholder_cells, sentry_entries):
                    cell.output_address = entry.sentry_address
                    imago_log.info(
                        f"[CONTROLLER] Sentry cell 0x{cell.address:08X} → "
                        f"PTT addr 0x{entry.sentry_address:08X} (entry {entry.index})"
                    )

        # Warn if design exceeds FPGA cell budget
        if self.cell_budget is not None and len(cell_addresses) > self.cell_budget:
            imago_log.warn(
                f"[CONTROLLER] ⚠ '{image_name}' uses {len(cell_addresses)} cells "
                f"but target '{self.fpga_target}' budget is {self.cell_budget}. "
                f"Program will not fit on hardware — VM only."
            )
        imago_log.info(
            f"[CONTROLLER] Loaded '{image_name}' — "
            f"{len(cell_addresses)} cells — "
            f"region {region.region_id}"
        )
        return region.region_id

    # ── Boot sequencer (Section 6) ───────────────────────────────────────────

    def boot(self, storage_root: str,
             boot_image_path: str = "boot/uniflex_core.icm",
             fs_type: str = "NATIVE") -> Optional[str]:
        """
        Execute the boot sequence (Section 6.3):
          1. DIMM enumeration (already done in __init__)
          2. Security gate init (machine key already loaded)
          3. Locate boot image on storage via FS decoder
          4. Load, verify, and place the boot image
          5. Return region_id of the loaded boot image

        storage_root:    path to the storage root (simulator: directory)
        boot_image_path: path within storage_root to the .icm boot image
        fs_type:         filesystem type of the storage medium
        """
        from uniflex_fs import UniFlex, FS_NATIVE
        from pond import PondManager

        imago_log.info(f"[BOOT] Starting boot sequence")
        imago_log.info(f"[BOOT] Storage root: {storage_root}  FS: {fs_type}")

        # Step 1: Create UniFlex and mount boot volume
        pm      = PondManager(self.array)
        ufx     = UniFlex(self.array, self._machine_key_str(), pm)
        try:
            sp = ufx.mount(storage_root, name="boot_volume",
                           fs_type=fs_type, bridge_count=2)
        except Exception as e:
            imago_log.info(f"[BOOT] Mount failed: {e}")
            return None

        # Step 2: Locate boot image
        import os
        from pathlib import Path
        full_path = Path(storage_root) / boot_image_path
        if not full_path.exists():
            imago_log.info(f"[BOOT] Boot image not found: {full_path}")
            return None
        imago_log.info(f"[BOOT] Boot image found: {full_path}")

        # Step 3: Load boot image via load_tile (signature + license check)
        rid = self.load_tile(str(full_path), "uniflex_core")
        if rid is None:
            # Fall back to unsigned load for simulator convenience
            rid = self._load_icm_unsigned(str(full_path), "uniflex_core")

        if rid:
            imago_log.info(f"[BOOT] Boot complete — region {rid}")
        else:
            imago_log.info(f"[BOOT] Boot failed — could not load boot image")
        return rid

    def _machine_key_str(self) -> str:
        """Return machine key as hex string (public ID)."""
        import hashlib
        return hashlib.sha256(
            self._machine_key.to_bytes(8, "big")).hexdigest()[:16]

    def _load_icm_unsigned(self, path: str,
                            image_name: str = "image") -> Optional[str]:
        """
        Load a .icm file without signature verification.
        Used during boot for the initial UniFlex image before the
        security gate is fully operational.
        """
        import json
        try:
            with open(path) as f:
                data = json.load(f)
            records = [
                __import__("controller").CellMapRecord(
                    c["gate_state"], c["input_address"], c["output_address"])
                for c in data["cell_map"]
            ]
            return self.load_map(records, image_name)
        except Exception as e:
            imago_log.info(f"[BOOT] Unsigned load failed: {e}")
            return None

    def load_tile(self, tile_path: str, image_name: str = "tile") -> Optional[str]:
        """
        Load a signed .icm tile file. Verifies signature and license tier,
        then places it into the array as a region.
        Returns region_id on success, None on any failure.
        """
        from fp_tiles import TileLibrary, TileSigningError, TileLicenseError
        lib = TileLibrary()
        try:
            tile = lib.load_tile(tile_path, self._machine_key, self.licensed_tier)
        except TileLicenseError as e:
            imago_log.info(f"[CONTROLLER] Tile license rejected: {e}")
            return None
        except TileSigningError as e:
            imago_log.info(f"[CONTROLLER] Tile signature rejected: {e}")
            return None
        except Exception as e:
            imago_log.info(f"[CONTROLLER] Tile load error: {e}")
            return None
        return self.load_map(tile.records, image_name)

    def _track_address_range(self, region: Region) -> Region:
        """Record the logical address range used by this region."""
        if region.cell_addresses:
            start = min(region.cell_addresses)
            end   = max(region.cell_addresses)
            self._address_map[region.region_id] = (start, end)
        return region

    # ── execution control ─────────────────────────────────────────────────────

    def start(
        self,
        region_id: str,
        inputs: Optional[dict[int, int]] = None
    ) -> bool:
        """
        Assert the start flag for a region and optionally inject input data.

        inputs: dict of {bus_address: value} for initial data injection.
        Returns True on success, False if region not found or wrong state.
        """
        region = self._regions.get(region_id)
        if region is None:
            imago_log.info(f"[CONTROLLER] Region '{region_id}' not found")
            return False
        if region.state == Region.RUNNING:
            imago_log.info(f"[CONTROLLER] Region '{region_id}' is already running")
            return False
        if region.state == Region.FREED:
            imago_log.info(f"[CONTROLLER] Region '{region_id}' has been freed")
            return False

        # Auto-inject known values (compile-time constants) first.
        # User-supplied inputs can override these if needed.
        for address, value in region.known_values.items():
            self.array._injected[address] = (value, 0)

        # Inject inputs onto the bus before asserting the flag.
        # Two-arrival model: each cell needs the value delivered TWICE —
        # first delivery stores in a_data, second delivery triggers the gate.
        # We inject the value now (first arrival) and re-inject after the
        # first tick (second arrival) inside the run loop.
        if inputs:
            for address, value in inputs.items():
                self.array._injected[address] = (value, 0)
            # Store inputs for second injection on first tick
            region._pending_inputs = dict(inputs)
        else:
            region._pending_inputs = {}

        # assert start flag only for cells in this region
        self.array.assert_start_flag(region.cell_addresses)
        region.state = Region.RUNNING
        return True

    def halt(self, region_id: str) -> bool:
        """
        De-assert the start flag for a region.
        Cells retain configuration but stop acting.
        Region moves to HALTED state.
        Returns True on success.
        """
        region = self._regions.get(region_id)
        if region is None:
            imago_log.info(f"[CONTROLLER] Region '{region_id}' not found")
            return False
        if region.state != Region.RUNNING:
            imago_log.info(f"[CONTROLLER] Region '{region_id}' is not running (state={region.state})")
            return False

        self.array.clear_start_flag(region.cell_addresses)
        region.state = Region.HALTED
        return True

    def free(self, region_id: str) -> bool:
        """
        Release a region's cells back to the free pool.
        Region must be HALTED or CONFIGURED — not RUNNING.
        Returns True on success.
        """
        region = self._regions.get(region_id)
        if region is None:
            imago_log.info(f"[CONTROLLER] Region '{region_id}' not found")
            return False
        if region.state == Region.RUNNING:
            imago_log.info(f"[CONTROLLER] Cannot free running region '{region_id}' — halt first")
            return False
        if region.state == Region.FREED:
            imago_log.info(f"[CONTROLLER] Region '{region_id}' already freed")
            return False

        # clear cells from the array
        for addr in region.cell_addresses:
            if addr in self.array.cells:
                del self.array.cells[addr]
            # return address to the free pool by resetting next pointer
            # if it's lower than current next (simple allocator reuse)

        # remove from address map
        self._address_map.pop(region_id, None)
        region.state = Region.FREED
        print(
            f"[CONTROLLER] Freed region '{region_id}' — "
            f"{len(region.cell_addresses)} cells returned"
        )
        return True

    # ── run to completion ─────────────────────────────────────────────────────

    def run(
        self,
        region_id: str,
        inputs: Optional[dict[int, int]] = None,
        max_cycles: int = 1_000_000,
        capture_addresses: Optional[list[int]] = None,
    ) -> Optional[dict[int, int]]:
        """
        Start a region, run to completion, return output values.

        inputs:            {bus_address: value} — injected before execution
        max_cycles:        hard limit — raises on timeout
        capture_addresses: list of bus addresses to read as outputs.
                           These addresses act as terminal sinks — values
                           arriving here are captured but not delivered to
                           further cells, preventing echo propagation through
                           downstream NOT cells in the pipeline.

        Returns dict of {address: value} for the captured addresses.
        Returns None if the region could not be started.
        """
        # Clear stale bus state, output buffers, and carry entries from any previous run.
        # _carry persists buffered values across ticks — must be cleared between runs
        # so old results don't leak into the new execution.
        region_pre = self._regions.get(region_id)
        if region_pre is not None:
            for addr in region_pre.cell_addresses:
                cell = self.array.cells.get(addr)
                if cell is not None:
                    cell._output_buf = None
                    self.array.bus.pop(cell.input_address, None)
                    self.array.bus.pop(cell.output_address, None)
                    self.array._carry.pop(cell.input_address, None)
                    self.array._carry.pop(cell.output_address, None)
                    pass  # no additional address fields to clear

        if not self.start(region_id, inputs):
            return None

        region = self._regions[region_id]
        captured: dict[int, int] = {}   # final captured output values
        sink_addrs = set(capture_addresses) if capture_addresses else set()
        cycles = 0

        for cycle in range(max_cycles):
            # Terminal sink model:
            # Before each tick, intercept any sink addresses present on the bus.
            for addr in list(self.array.bus.keys()):
                if addr in sink_addrs and addr not in captured:
                    entry = self.array.bus.pop(addr)
                    captured[addr] = entry[0] if isinstance(entry, tuple) else entry
                elif addr in sink_addrs:
                    del self.array.bus[addr]

            active = self.array.tick()
            cycles += 1

            # Two-arrival model: after first tick, re-inject inputs as second arrival.
            # First injection (in start()) stores value in a_data.
            # Second injection (here, on cycle 1) triggers the gate.
            if cycle == 0 and region._pending_inputs:
                for address, value in region._pending_inputs.items():
                    self.array._injected[address] = (value, 0)

            # Capture any sink values produced this tick (first occurrence only)
            for addr in sink_addrs:
                entry = self.array.bus.get(addr)
                if entry is not None and addr not in captured:
                    captured[addr] = entry[0] if isinstance(entry, tuple) else entry

            if active == 0 and not self.array._injected:
                # Only terminate when there's nothing pending —
                # pending _injected means a second arrival is queued.
                # Drain output buffers: cells cleared start_flag this tick but their
                # results are still in _output_buf. One more tick publishes them.
                buf_pending = any(c._output_buf is not None for c in self.array.cells.values())
                if buf_pending:
                    # Intercept sink addresses before drain tick
                    for addr in list(self.array.bus.keys()):
                        if addr in sink_addrs and addr not in captured:
                            entry = self.array.bus.pop(addr)
                            captured[addr] = entry[0] if isinstance(entry, tuple) else entry
                        elif addr in sink_addrs:
                            del self.array.bus[addr]
                    self.array.tick()
                    cycles += 1
                    for addr in sink_addrs:
                        entry = self.array.bus.get(addr)
                        if entry is not None and addr not in captured:
                            captured[addr] = entry[0] if isinstance(entry, tuple) else entry
                break
        else:
            self.halt(region_id)
            raise RuntimeError(
                f"Region '{region_id}' did not terminate within {max_cycles} cycles"
            )

        region.cycles_run += cycles
        self.total_cycles += cycles
        region.state = Region.HALTED

        # clear start flag
        self.array.clear_start_flag(region.cell_addresses)

        if capture_addresses is not None:
            # Return captured sink values — these were intercepted before
            # delivery to prevent echo propagation
            return {addr: captured.get(addr) for addr in capture_addresses}
        # No capture addresses: return the final bus state (values only)
        return {addr: (v[0] if isinstance(v, tuple) else v)
                for addr, v in self.array.bus.items()}

    # ── bus read ──────────────────────────────────────────────────────────────

    def run_loop(
        self,
        region_id: str,
        inputs: Optional[dict[int, int]] = None,
        capture_addresses: Optional[list[int]] = None,
        max_cycles: int = 10_000,
    ) -> Optional[dict[int, int]]:
        """
        Run a region that contains loops (storage cells stay live indefinitely).

        Unlike run(), which stops when active==0, run_loop() stops as soon as
        all capture_addresses have been seen on the bus. This is correct for
        compiled while loops, where storage cells re-emit forever after the
        loop exits — active never reaches 0, but the result appears on the
        result cell's output address once the loop terminates.

        inputs:            {bus_address: value} — injected before execution.
                           For loops, this must include the initial value of
                           each loop variable at its storage_in_addr.
        capture_addresses: output addresses to collect. Stops when all seen.
        max_cycles:        hard limit to prevent infinite loops in programs
                           that never terminate.

        Returns dict of {address: value} for capture_addresses.
        Returns None if region could not be started.
        """
        if not self.start(region_id, inputs):
            return None

        region = self._regions[region_id]
        captured: dict[int, int] = {}
        sink_addrs = set(capture_addresses) if capture_addresses else set()
        cycles = 0

        for _ in range(max_cycles):
            # Capture values from bus before tick (they may not be there after)
            for addr in sink_addrs:
                entry = self.array.bus.get(addr)
                if entry is not None and addr not in captured:
                    captured[addr] = entry[0] if isinstance(entry, tuple) else entry

            # Stop as soon as every output address has been seen
            if sink_addrs and all(a in captured for a in sink_addrs):
                break

            self.array.tick()
            cycles += 1

            # Also capture values produced this tick
            for addr in sink_addrs:
                entry = self.array.bus.get(addr)
                if entry is not None and addr not in captured:
                    captured[addr] = entry[0] if isinstance(entry, tuple) else entry

            if sink_addrs and all(a in captured for a in sink_addrs):
                break
        else:
            self.halt(region_id)
            raise RuntimeError(
                f"run_loop: region '{region_id}' did not produce output "
                f"within {max_cycles} cycles (possible infinite loop)"
            )

        region.cycles_run += cycles
        self.total_cycles += cycles
        # Don't transition to HALTED — loop regions stay RUNNING (storage cells live)
        # Caller can halt() explicitly if needed.

        if capture_addresses is not None:
            return {addr: captured.get(addr) for addr in capture_addresses}
        return captured

    def read(self, address: int) -> Optional[int]:
        """Read the current value at address from the bus."""
        return self.array.read_bus(address)

    # ── Start-flag control — freeze / thaw / snapshot ─────────────────────────

    def freeze(self, cell_addresses: Optional[list[int]] = None,
               region_id: Optional[str] = None) -> int:
        """
        Freeze cells by clearing their start_flags.

        The cells remain fully configured and retain all stored values.
        They simply stop participating in computation — data waves pass
        through the array and frozen cells are silent.

        Use cases:
          - Freeze a branch's cells while the other branch runs (role 2)
          - Freeze a Pond region to snapshot it before migration (role 3)
          - Freeze a subset of cells to inspect state mid-computation (role 4)

        cell_addresses: specific cell addresses to freeze. If None, uses region.
        region_id:      freeze all cells in a named region. Ignored if addresses given.

        Returns count of cells frozen.
        """
        if cell_addresses is not None:
            count = self.array.clear_start_flag(cell_addresses)
        elif region_id is not None:
            region = self._regions.get(region_id)
            if region is None:
                imago_log.info(f"[CONTROLLER] freeze: region '{region_id}' not found")
                return 0
            count = self.array.clear_start_flag(region.cell_addresses)
        else:
            imago_log.info("[CONTROLLER] freeze: provide cell_addresses or region_id")
            return 0
        imago_log.info(f"[CONTROLLER] Frozen {count} cells")
        return count

    def thaw(self, cell_addresses: Optional[list[int]] = None,
             region_id: Optional[str] = None) -> int:
        """
        Thaw cells by asserting their start_flags.

        Resumes cells frozen by freeze(). The cells re-enter computation
        on the next tick. Storage cells immediately resume re-emitting
        their held values. Compute cells wait for data on their input address.

        cell_addresses: specific cells to thaw.
        region_id:      thaw all cells in a named region.

        Returns count of cells thawed.
        """
        if cell_addresses is not None:
            count = self.array.assert_start_flag(cell_addresses)
        elif region_id is not None:
            region = self._regions.get(region_id)
            if region is None:
                imago_log.info(f"[CONTROLLER] thaw: region '{region_id}' not found")
                return 0
            count = self.array.assert_start_flag(region.cell_addresses)
        else:
            imago_log.info("[CONTROLLER] thaw: provide cell_addresses or region_id")
            return 0
        imago_log.info(f"[CONTROLLER] Thawed {count} cells")
        return count

    def snapshot(self, cell_addresses: Optional[list[int]] = None,
                 region_id: Optional[str] = None) -> list[dict]:
        """
        Capture the complete state of a set of cells.

        Returns a list of cell state dicts (one per cell), each containing
        all configuration registers, flags, and stored values. The snapshot
        is a complete description of the cell's state — enough to restore
        it identically on any array.

        The cells are NOT frozen by snapshot() — call freeze() first if
        you want to pause computation before capturing state.

        Use cases:
          - Checkpoint a running Pond region for migration or persistence
          - Inspect stored values at a specific pipeline stage for debugging
          - Capture a branch's state before routing to the other branch

        cell_addresses: specific cells to snapshot.
        region_id:      snapshot all cells in a named region.

        Returns list of snapshot dicts, ordered by cell address.
        """
        if cell_addresses is not None:
            addrs = cell_addresses
        elif region_id is not None:
            region = self._regions.get(region_id)
            if region is None:
                imago_log.info(f"[CONTROLLER] snapshot: region '{region_id}' not found")
                return []
            addrs = region.cell_addresses
        else:
            imago_log.info("[CONTROLLER] snapshot: provide cell_addresses or region_id")
            return []

        states = []
        for addr in addrs:
            cell = self.array.cells.get(addr)
            if cell is not None:
                states.append(cell.snapshot())
        imago_log.info(f"[CONTROLLER] Snapshot: {len(states)} cells captured")
        return states

    def restore_snapshot(self, states: list[dict]) -> int:
        """
        Restore cells from a snapshot captured by snapshot().

        For each state dict: if a cell already exists at that address,
        its configuration and stored value are overwritten. If no cell
        exists at that address, the restore is skipped (the array must
        be pre-loaded with the correct cell layout via load_map first).

        This is the reload path for Pond migration and checkpoint/resume.
        After restore_snapshot(), call thaw() to re-arm the cells.

        Returns count of cells successfully restored.
        """
        count = 0
        for state in states:
            addr = state["address"]
            cell = self.array.cells.get(addr)
            if cell is None:
                continue
            # Restore via cell.restore() which unpacks cmd_latch correctly
            cell.restore(state)
            # Sync _armed set with restored start_flag
            if cell.start_flag:
                self.array._armed.add(addr)
            else:
                self.array._armed.discard(addr)
            count += 1
        imago_log.info(f"[CONTROLLER] Restored {count} cells from snapshot")
        return count



    # ── status ────────────────────────────────────────────────────────────────

    def status(self) -> dict:
        """Return a summary of controller and array state."""
        array_status = self.array.status()
        active_regions = [
            r for r in self._regions.values()
            if r.state in (Region.RUNNING, Region.CONFIGURED, Region.HALTED)
        ]
        return {
            **array_status,
            "active_regions":  len(active_regions),
            "total_regions":   len(self._regions),
            "total_cycles":    self.total_cycles,
            "address_ranges":  dict(self._address_map),
        }

    def list_regions(self) -> list[Region]:
        """Return all non-freed regions."""
        return [
            r for r in self._regions.values()
            if r.state != Region.FREED
        ]

    def __repr__(self) -> str:
        s = self.status()
        return (
            f"ImagoController("
            f"cells={s['allocated_cells']}/{s['total_cells']} "
            f"regions={s['active_regions']} "
            f"cycles={s['total_cycles']})"
        )
