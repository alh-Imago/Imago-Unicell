"""
fpga_bridge.py — Python UART host interface for UniCell latch array
Claudette v2.1 / unicell-latch variant

Talks to the iCEBreaker (or any supported FPGA board) running the
unicell_array_latch + uart_bridge Verilog design.

Mirrors controller.py in API style so bring-up scripts can switch
between VM and hardware with a one-line change:

    # VM:
    from controller import Controller
    ctrl = Controller(num_cells=8)

    # Hardware:
    from fpga_bridge import FPGABridge
    ctrl = FPGABridge(port="/dev/ttyUSB0", num_cells=8)

Both expose:
    configure(cell_id, gate_state, input_addr, output_addr)
    inject(addr, data)
    set_flags(mask)               -- latch variant only
    reset()
    freeze() / release()
    read_output(timeout=1.0)      -- returns (addr, data) or None
    status()                      -- returns (armed_count, cycle_count)

Protocol (115200 8N1):
    Host → FPGA:
        0x01 [bus1:4] [addr:4] [data:4]   inject bus transaction (13 bytes)
        0x02 [addr:4] [data:4]             configure cell (9 bytes)
        0x03                               reset array
        0x04                               query status
        0x06                               freeze array
        0x07                               release freeze
        0x08 [flags:8]                     SET_FLAGS: 64-bit start_flag mask

    FPGA → Host:
        0x10 [addr:4] [data:4] [hs:1]     cell fired (10 bytes)
        0x11 [armed:2] [cycles:4]         status response (7 bytes)
        0x13                              freeze acknowledged
        0x14                              release acknowledged
        0x15 [flags:8]                    SET_FLAGS acknowledged (9 bytes)
        0xFF                              error / unknown command

All multi-byte values are big-endian.

Bring-up sequence (iCEBreaker, 8 cells):
    bridge = FPGABridge("/dev/ttyUSB0", num_cells=8)
    bridge.reset()
    bridge.set_flags(0xFF)                  # arm all 8 cells directly
    bridge.configure(0, GS_NOT, 0x1000, 0x1001)
    bridge.inject(0x1000, 1)
    result = bridge.read_output()
    assert result == (0x1001, 0)            # NOT(1) = 0
"""

from __future__ import annotations
import struct
import time
import threading
from typing import Optional, Tuple

# Serial is an optional dependency — only needed for real hardware.
# Import lazily so VM-only environments don't need pyserial.
try:
    import serial
    _SERIAL_AVAILABLE = True
except ImportError:
    _SERIAL_AVAILABLE = False


# ── Protocol constants ─────────────────────────────────────────────────────────
CMD_INJECT      = 0x01
CMD_CONFIGURE   = 0x02
CMD_RESET       = 0x03
CMD_STATUS      = 0x04
CMD_FREEZE      = 0x06
CMD_RELEASE     = 0x07
CMD_SET_FLAGS   = 0x08     # latch variant only

RESP_CELL_FIRED = 0x10
RESP_STATUS     = 0x11
RESP_FREEZE_ACK = 0x13
RESP_RELEASE_ACK = 0x14
RESP_FLAGS_ACK  = 0x15
RESP_ERROR      = 0xFF

# Bus 1 default (no handshake, local scope, no auth)
BUS1_DEFAULT    = 0x00000000


class FPGABridgeError(Exception):
    pass


class FPGABridge:
    """
    Host-side UART bridge to a UniCell latch array on FPGA hardware.

    Parameters
    ----------
    port        : serial port path (e.g. "/dev/ttyUSB0", "COM3")
    num_cells   : number of cells in the array (for validation)
    baud_rate   : UART baud rate (must match Verilog CLK_FREQ/BAUD_RATE)
    timeout     : default read timeout in seconds
    """

    def __init__(self,
                 port: str,
                 num_cells: int = 64,
                 baud_rate: int = 115_200,
                 timeout: float = 2.0):
        if not _SERIAL_AVAILABLE:
            raise FPGABridgeError(
                "pyserial is required for hardware mode.\n"
                "Install it with: pip install pyserial"
            )
        self.port      = port
        self.num_cells = num_cells
        self.timeout   = timeout
        self._lock     = threading.Lock()
        self._ser      = serial.Serial(port, baud_rate, timeout=timeout)
        time.sleep(0.1)   # let the FPGA reset after DTR toggle
        self._ser.reset_input_buffer()

    def close(self):
        """Release the serial port."""
        if self._ser and self._ser.is_open:
            self._ser.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # ── Low-level send/receive ─────────────────────────────────────────────────

    def _send(self, data: bytes):
        with self._lock:
            self._ser.write(data)

    def _read_exact(self, n: int, timeout: Optional[float] = None) -> bytes:
        """Read exactly n bytes, raise on timeout."""
        deadline = time.monotonic() + (timeout or self.timeout)
        buf = b""
        while len(buf) < n:
            if time.monotonic() > deadline:
                raise FPGABridgeError(
                    f"Timeout reading {n} bytes (got {len(buf)}): {buf.hex()}"
                )
            chunk = self._ser.read(n - len(buf))
            buf += chunk
        return buf

    def _read_response(self, timeout: Optional[float] = None) -> Tuple[int, bytes]:
        """
        Read one response packet from the FPGA.
        Returns (response_code, payload_bytes).
        """
        deadline = time.monotonic() + (timeout or self.timeout)
        # Read response header byte
        while True:
            if time.monotonic() > deadline:
                raise FPGABridgeError("Timeout waiting for response header")
            hdr = self._ser.read(1)
            if hdr:
                break
        code = hdr[0]

        # Read payload based on response code
        if code == RESP_CELL_FIRED:
            payload = self._read_exact(9, timeout)  # addr(4)+data(4)+hs(1)
        elif code == RESP_STATUS:
            payload = self._read_exact(6, timeout)  # armed(2)+cycles(4)
        elif code in (RESP_FREEZE_ACK, RESP_RELEASE_ACK, RESP_ERROR):
            payload = b""
        elif code == RESP_FLAGS_ACK:
            payload = self._read_exact(8, timeout)  # flags(8) echo
        else:
            payload = b""

        return code, payload

    # ── Public API — mirrors controller.py ────────────────────────────────────

    def reset(self):
        """
        Assert array reset. All cells return to unconfigured state.
        start_flags are cleared. Use set_flags() or configure() to re-arm.
        """
        self._send(bytes([CMD_RESET]))
        time.sleep(0.01)   # reset pulse propagation

    def configure(self,
                  cell_id:     int,
                  gate_state:  int,
                  input_addr:  int,
                  output_addr: int):
        """
        Configure one cell via the LOAD_PATTERN config sequence.

        Sends three bus transactions:
            LOAD_PATTERN  → CONFIG_ADDRESS
            gate_state    → CONFIG_ADDRESS
            input_addr    → CONFIG_ADDRESS
            output_addr   → CONFIG_ADDRESS

        The cell arms automatically after step 4.
        After configure(), the cell's start_flag is set by hardware.
        """
        config_addr = cell_id   # CONFIG_ADDRESS == CELL_ID in current RTL
        load_pattern = 0xA5A5A5A5

        # Use CMD_CONFIGURE (0x02) for direct config — same as inject but
        # routed through the config address cleanly.
        for data in [load_pattern, gate_state, input_addr, output_addr]:
            pkt = bytes([CMD_CONFIGURE]) + \
                  struct.pack(">I", config_addr) + \
                  struct.pack(">I", data)
            self._send(pkt)
            time.sleep(0.001)   # inter-packet gap

    def inject(self, addr: int, data: int, bus1: int = BUS1_DEFAULT):
        """
        Inject a bus transaction (addr, data) into the array.

        bus1 : Bus 1 word (scope, handshake, auth). Default = 0 (local, none).
        """
        pkt = (bytes([CMD_INJECT]) +
               struct.pack(">I", bus1) +
               struct.pack(">I", addr) +
               struct.pack(">I", data))
        self._send(pkt)

    def set_flags(self, mask: int):
        """
        SET_FLAGS (0x08) — write a 64-bit bitmask directly to the array's
        start_flag lines. Bit N sets/clears the start_flag for cell N.

        This bypasses the config sequence entirely and arms cells in one shot.
        Intended for:
          - iCEBreaker bring-up: arm cells after a manual configure()
          - Batch arm/disarm without touching gate_state or addresses
          - Testing: arm a specific subset of cells

        The FPGA echoes the flags back in a RESP_FLAGS_ACK (0x15) packet.
        Returns the echoed mask for verification.

        Example — arm cells 0 and 1 only:
            bridge.set_flags(0b11)  →  cell 0 armed, cell 1 armed, rest disarmed
        """
        if mask < 0 or mask > 0xFFFF_FFFF_FFFF_FFFF:
            raise ValueError(f"set_flags mask must be 64-bit, got: {mask:#x}")

        pkt = bytes([CMD_SET_FLAGS]) + struct.pack(">Q", mask)
        self._send(pkt)

        # Wait for acknowledgement
        code, payload = self._read_response()
        if code != RESP_FLAGS_ACK:
            raise FPGABridgeError(
                f"SET_FLAGS: unexpected response 0x{code:02X} (expected 0x15)"
            )
        echoed = struct.unpack(">Q", payload)[0]
        if echoed != mask:
            raise FPGABridgeError(
                f"SET_FLAGS: echo mismatch — sent {mask:#018x}, got {echoed:#018x}"
            )
        return echoed

    def freeze(self):
        """Freeze all cells — fully decouple from bus. State preserved."""
        self._send(bytes([CMD_FREEZE]))
        code, _ = self._read_response()
        if code != RESP_FREEZE_ACK:
            raise FPGABridgeError(f"freeze: unexpected response 0x{code:02X}")

    def release(self):
        """Release freeze — cells resume normal operation."""
        self._send(bytes([CMD_RELEASE]))
        code, _ = self._read_response()
        if code != RESP_RELEASE_ACK:
            raise FPGABridgeError(f"release: unexpected response 0x{code:02X}")

    def status(self) -> Tuple[int, int]:
        """
        Query array status.
        Returns (armed_count, cycle_count).
        """
        self._send(bytes([CMD_STATUS]))
        code, payload = self._read_response()
        if code != RESP_STATUS:
            raise FPGABridgeError(f"status: unexpected response 0x{code:02X}")
        armed  = struct.unpack(">H", payload[0:2])[0]
        cycles = struct.unpack(">I", payload[2:6])[0]
        return armed, cycles

    def read_output(self,
                    timeout: Optional[float] = None
                    ) -> Optional[Tuple[int, int]]:
        """
        Wait for a cell-fired response from the array.
        Returns (out_addr, out_data) or None on timeout.

        The FPGA sends 0x10 [addr:4] [data:4] [hs:1] when any cell fires.
        The handshake byte is logged but not returned — use read_output_full()
        if you need it.
        """
        try:
            code, payload = self._read_response(timeout=timeout or self.timeout)
        except FPGABridgeError:
            return None

        if code != RESP_CELL_FIRED:
            return None

        addr = struct.unpack(">I", payload[0:4])[0]
        data = struct.unpack(">I", payload[4:8])[0]
        return addr, data

    def read_output_full(self,
                         timeout: Optional[float] = None
                         ) -> Optional[Tuple[int, int, int]]:
        """
        Like read_output() but also returns the handshake byte.
        Returns (out_addr, out_data, handshake) or None on timeout.
        """
        try:
            code, payload = self._read_response(timeout=timeout or self.timeout)
        except FPGABridgeError:
            return None

        if code != RESP_CELL_FIRED:
            return None

        addr = struct.unpack(">I", payload[0:4])[0]
        data = struct.unpack(">I", payload[4:8])[0]
        hs   = payload[8]
        return addr, data, hs

    def drain(self, timeout: float = 0.1) -> list:
        """
        Drain all pending cell-fired responses until the FPGA goes quiet.
        Returns list of (addr, data) tuples.
        Useful after inject() to collect multi-cell pipeline results.
        """
        results = []
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            r = self.read_output(timeout=0.02)
            if r is None:
                break
            results.append(r)
        return results


# ── Convenience: VM-compatible wrapper ────────────────────────────────────────

class SimBridge:
    """
    Drop-in replacement for FPGABridge that runs against the Python VM
    (unicell_array.py) instead of real hardware. Useful for bring-up
    script development without an iCEBreaker attached.

    Usage:
        # Develop and test against VM:
        bridge = SimBridge(num_cells=8)
        bridge.reset()
        bridge.set_flags(0xFF)           # arm all 8 cells
        bridge.configure(0, GS_NOT, 0x1000, 0x1001)
        bridge.inject(0x1000, 1)
        print(bridge.read_output())      # → (0x1001, 0)

        # Swap to hardware with no other changes:
        bridge = FPGABridge("/dev/ttyUSB0", num_cells=8)

    Cell identity:
        configure(cell_id=N, ...) allocates the Nth cell on first call.
        cell_id maps to a stable bus address via self._cell_addrs[cell_id].
        After reset() the mapping is cleared and cells are reallocated fresh.

    set_flags(mask):
        Bit N of mask controls the start_flag of cell N (by cell_id order).
        Mirrors hardware SET_FLAGS (0x08) exactly.

    inject(addr, data):
        Writes (data, 0) to the bus at addr, then calls tick_drain().
        All cell-fired outputs are queued for read_output().
    """

    def __init__(self, num_cells: int = 8):
        import os, sys
        sys.path.insert(0, os.path.dirname(__file__))
        self.num_cells  = num_cells
        self._cell_addrs: dict = {}   # cell_id → bus address
        self._pending: list   = []    # queued (out_addr, out_data) results
        self._init_array()

    def _init_array(self):
        from unicell_array import UniCellArray
        self._array      = UniCellArray(self.num_cells)
        self._cell_addrs = {}
        self._pending    = []

    def _get_or_alloc(self, cell_id: int) -> int:
        """Return the bus address for cell_id, allocating if needed."""
        if cell_id not in self._cell_addrs:
            cell = self._array.allocate_cell()
            self._cell_addrs[cell_id] = cell.address
        return self._cell_addrs[cell_id]

    def reset(self):
        """Reset array — clears all cell state and the cell_id → address map."""
        self._init_array()

    def configure(self, cell_id: int, gate_state: int,
                  input_addr: int, output_addr: int):
        """
        Configure one cell and arm it.

        Equivalent to the hardware LOAD_PATTERN config sequence.
        The cell is automatically armed (start_flag set) after configure.
        cell_id is the logical index (0, 1, 2, ...).
        """
        from unicell import FUNCTION_LOAD_PATTERN
        bus_addr = self._get_or_alloc(cell_id)
        self._array.write_config(
            bus_addr,
            [FUNCTION_LOAD_PATTERN, gate_state, input_addr, output_addr]
        )
        self._array.assert_start_flag([bus_addr])

    def inject(self, addr: int, data: int, bus1: int = BUS1_DEFAULT):
        """
        Write data to bus address addr, then run tick_drain().
        All cell outputs produced are queued for read_output().
        bus1 is accepted for API compatibility but ignored in simulation.
        """
        self._array.bus[addr] = (data, 0)   # (data, ecc=0)
        self._array.tick_drain()
        # Harvest all bus entries that are not the injected address
        for bus_addr, entry in list(self._array.bus.items()):
            if bus_addr != addr and entry is not None:
                out_data, _ecc = entry
                self._pending.append((bus_addr, out_data))
                # Don't consume the bus entry — downstream cells may need it

    def set_flags(self, mask: int) -> int:
        """
        Arm/disarm cells by bitmask. Bit N controls cell_id N.

        Allocates cells 0..num_cells-1 on first call if not yet allocated.
        Mirrors hardware SET_FLAGS (0x08) exactly.
        Returns the applied mask for verification.
        """
        if mask < 0 or mask > 0xFFFF_FFFF_FFFF_FFFF:
            raise ValueError(f"set_flags mask must be 64-bit, got: {mask:#x}")

        # Ensure all cells are allocated up to num_cells
        for cid in range(self.num_cells):
            self._get_or_alloc(cid)

        arm_addrs   = []
        disarm_addrs = []
        for cid, bus_addr in self._cell_addrs.items():
            if mask & (1 << cid):
                arm_addrs.append(bus_addr)
            else:
                disarm_addrs.append(bus_addr)

        if arm_addrs:
            self._array.assert_start_flag(arm_addrs)
        if disarm_addrs:
            self._array.clear_start_flag(disarm_addrs)

        return mask & ((1 << self.num_cells) - 1)

    def freeze(self):
        """Freeze the array (no-op in latch VM — pond freeze handled by controller)."""
        pass   # UniCellArray has no freeze flag; freeze is pond-level

    def release(self):
        """Release freeze."""
        pass

    def status(self) -> tuple:
        """
        Returns (armed_count, cycle_count) matching FPGABridge.status().
        """
        s = self._array.status()
        armed  = sum(
            1 for c in self._array.cells.values() if c.start_flag
        )
        cycles = s.get('bus_active_addresses', 0)   # best proxy in VM
        return armed, cycles

    def read_output(self, timeout=None) -> Optional[Tuple[int, int]]:
        """Return (out_addr, out_data) from queue, or None if empty."""
        if self._pending:
            return self._pending.pop(0)
        return None

    def read_output_full(self, timeout=None) -> Optional[Tuple[int, int, int]]:
        """Return (out_addr, out_data, handshake=0) from queue, or None."""
        if self._pending:
            addr, data = self._pending.pop(0)
            return addr, data, 0
        return None

    def drain(self, timeout: float = 0.1) -> list:
        """Return all queued outputs and clear the queue."""
        results = list(self._pending)
        self._pending = []
        return results

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass
