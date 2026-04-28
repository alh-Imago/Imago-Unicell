"""
fpga_bridge.py — Python Host Bridge for UniCell FPGA
Claudette v1.1

Connects the Python workbench to a physical UniCell FPGA implementation
via UART. The FPGA handles the cell array and bus timing. This bridge
handles everything above the bus — configuration, Shore, COMPANION,
and the workbench interface.

On small FPGAs (iCE40UP5K with 64 cells) the cell array runs at full
speed on the FPGA while all OS functions run on the host CPU. This is
the correct partitioning — the FPGA does what only silicon can do
(deterministic bus timing), the CPU does what software does best
(policy, routing, user interface).

Usage:
    python3 fpga_bridge.py --port COM3          # Windows
    python3 fpga_bridge.py --port /dev/ttyUSB0  # Linux
    python3 fpga_bridge.py --port /dev/tty.usbserial-* --baud 115200

    Then open the workbench normally — it will detect the FPGA bridge
    and route bus transactions through the physical array.

    python3 workbench.py --fpga --port /dev/ttyUSB0

Requirements:
    pip install pyserial
"""

import serial
import struct
import time
import threading
import queue
import sys
import argparse
from typing import Optional, Callable

# ── Protocol constants ────────────────────────────────────────────────────────
CMD_INJECT    = 0x01  # Inject bus transaction (cmd + bus1(4) + addr(4) + data(4))
CMD_CONFIGURE = 0x02  # Configure cell (LOAD_PATTERN sequence)
CMD_RESET     = 0x03  # Reset array
CMD_STATUS    = 0x04  # Query status
CMD_FREEZE    = 0x06  # Freeze array — all cells decouple
CMD_RELEASE   = 0x07  # Release freeze

RSP_FIRED     = 0x10  # Cell fired (addr + data + handshake byte)
RSP_STATUS    = 0x11  # Status response
RSP_CELL      = 0x12  # Cell state response
RSP_FREEZE_OK = 0x13  # Freeze acknowledged
RSP_RELEASE_OK= 0x14  # Release acknowledged
RSP_ERROR     = 0xFF  # Error

LOAD_PATTERN  = 0xA5A5A5A5

# ── Bus 1 handshake constants (matching command_interface.py) ─────────────────
HANDSHAKE_NONE    = 0x0
HANDSHAKE_ACK     = 0x1
HANDSHAKE_NAK     = 0x2
HANDSHAKE_BUSY    = 0x3
HANDSHAKE_REQUEST = 0x4
HANDSHAKE_GRANT   = 0x5
HANDSHAKE_DENY    = 0x6
HANDSHAKE_RETRY   = 0x7

# ── Scope constants ───────────────────────────────────────────────────────────
SCOPE_LOCAL    = 0b00   # 32-bit local address
SCOPE_SHORE    = 0b01   # 48-bit cross-card
SCOPE_EXTENDED = 0b10   # 64-bit system-wide

def build_bus1(cmd: int = 0, auth: int = 0, raw_addr: bool = True,
               scope: int = SCOPE_LOCAL,
               handshake: int = HANDSHAKE_NONE) -> int:
    """Build a Bus 1 word for the inject command.
    Matches command_interface.py build_bus1 exactly.
    """
    b1  = (cmd & 0xF)
    b1 |= ((auth & 0x7FF) << 4)
    if raw_addr:
        b1 |= (1 << 15)
    b1 |= ((scope     & 0x3) << 16)
    b1 |= ((handshake & 0xF) << 18)
    return b1


class FPGABridge:
    """
    Bridge between the Python workbench and a physical UniCell FPGA.

    Provides the same interface as ImagoController so it can be used
    as a drop-in replacement — the workbench doesn't know whether it's
    talking to a VM or silicon.
    """

    def __init__(self, port: str, baud: int = 115200, timeout: float = 2.0):
        self.port    = port
        self.baud    = baud
        self.timeout = timeout

        self._ser: Optional[serial.Serial] = None
        self._rx_queue: queue.Queue = queue.Queue()
        self._rx_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        # Callbacks — called when a cell fires
        self._fire_callbacks: list[Callable] = []

        # Statistics
        self.stats = {
            'injected': 0,
            'configured': 0,
            'fired': 0,
            'errors': 0,
        }

    # ── Connection ────────────────────────────────────────────────────────────

    def connect(self) -> bool:
        """Open serial connection and verify FPGA responds."""
        try:
            self._ser = serial.Serial(
                port=self.port,
                baudrate=self.baud,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=self.timeout,
            )
            self._running = True
            self._rx_thread = threading.Thread(
                target=self._rx_loop, daemon=True)
            self._rx_thread.start()

            time.sleep(0.1)  # Allow FPGA to settle after DTR reset

            # Verify connection with status query
            status = self.get_status()
            if status is None:
                print(f"[FPGA] No response from {self.port}")
                return False

            print(f"[FPGA] Connected to {self.port} at {self.baud} baud")
            print(f"[FPGA] Armed cells: {status['armed']}")
            print(f"[FPGA] Cycle count: {status['cycles']}")
            return True

        except serial.SerialException as e:
            print(f"[FPGA] Connection failed: {e}")
            return False

    def disconnect(self):
        """Close serial connection."""
        self._running = False
        if self._ser and self._ser.is_open:
            self._ser.close()
        print(f"[FPGA] Disconnected")

    # ── RX thread ─────────────────────────────────────────────────────────────

    def _rx_loop(self):
        """Background thread reads responses from FPGA."""
        buf = bytearray()
        while self._running:
            try:
                if self._ser.in_waiting:
                    buf += self._ser.read(self._ser.in_waiting)
                    buf = self._process_buffer(buf)
                else:
                    time.sleep(0.001)
            except Exception as e:
                if self._running:
                    print(f"[FPGA] RX error: {e}")

    def _process_buffer(self, buf: bytearray) -> bytearray:
        """Parse incoming bytes and dispatch responses."""
        while len(buf) > 0:
            cmd = buf[0]

            if cmd == RSP_FIRED and len(buf) >= 10:
                addr      = struct.unpack('>I', buf[1:5])[0]
                data      = struct.unpack('>I', buf[5:9])[0]
                handshake = buf[9] & 0xF   # lower nibble is handshake field
                self._rx_queue.put(('fired', addr, data, handshake))
                self.stats['fired'] += 1
                for cb in self._fire_callbacks:
                    try:
                        cb(addr, data, handshake)
                    except Exception:
                        pass
                buf = buf[10:]

            elif cmd == RSP_STATUS and len(buf) >= 7:
                armed  = struct.unpack('>H', buf[1:3])[0]
                cycles = struct.unpack('>I', buf[3:7])[0]
                self._rx_queue.put(('status', armed, cycles))
                buf = buf[7:]

            elif cmd == RSP_ERROR:
                self.stats['errors'] += 1
                self._rx_queue.put(('error',))
                buf = buf[1:]

            else:
                # Not enough data yet
                break

        return buf

    # ── Commands ──────────────────────────────────────────────────────────────

    def _send(self, data: bytes):
        """Send bytes to FPGA."""
        with self._lock:
            if self._ser and self._ser.is_open:
                self._ser.write(data)

    def inject(self, addr: int, data: int,
               handshake: int = HANDSHAKE_NONE,
               scope: int = SCOPE_LOCAL) -> bool:
        """
        Inject a bus transaction into the FPGA cell array.

        Equivalent to ImagoController.inject_bus_value() in the VM.
        handshake: HANDSHAKE_* constant — bridge-level ACK/REQ signal.
        scope:     SCOPE_LOCAL/SHORE/EXTENDED — address width hint.
        """
        bus1 = build_bus1(raw_addr=True, scope=scope, handshake=handshake)
        # Protocol: CMD_INJECT + bus1(4) + addr(4) + data(4) = 13 bytes
        pkt = struct.pack('>BIII', CMD_INJECT,
                          bus1 & 0xFFFFFFFF,
                          addr & 0xFFFFFFFF,
                          data & 0xFFFFFFFF)
        self._send(pkt)
        self.stats['injected'] += 1
        return True

    def configure_cell(self, cell_addr: int,
                       gate_state: int,
                       input_addr: int,
                       output_addr: int) -> bool:
        """
        Configure a cell via the FUNCTION_LOAD_PATTERN mechanism.

        Sends the load pattern to the cell's CONFIG_ADDRESS (= cell index),
        then gate_state, input_address, and output_address in sequence.
        Note: cell_addr here is the CONFIG_ADDRESS — the fixed synthesis-time
        address, not the runtime input_address.
        """
        self.inject(cell_addr, LOAD_PATTERN)
        time.sleep(0.001)
        self.inject(cell_addr, gate_state)
        time.sleep(0.001)
        self.inject(cell_addr, input_addr)
        time.sleep(0.001)
        self.inject(cell_addr, output_addr)
        self.stats['configured'] += 1
        return True

    def freeze(self, timeout: float = 1.0) -> bool:
        """
        Freeze the cell array — all cells decouple from bus simultaneously.
        Used for pond migration, system snapshots, and fault isolation.
        Returns True if FPGA acknowledged the freeze.
        """
        self._send(bytes([CMD_FREEZE]))
        # Wait for RSP_FREEZE_OK (0x13)
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._ser and self._ser.in_waiting:
                b = self._ser.read(1)
                if b and b[0] == RSP_FREEZE_OK:
                    return True
            time.sleep(0.001)
        return False

    def release(self, timeout: float = 1.0) -> bool:
        """
        Release the cell array freeze — cells resume normal operation.
        Returns True if FPGA acknowledged the release.
        """
        self._send(bytes([CMD_RELEASE]))
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._ser and self._ser.in_waiting:
                b = self._ser.read(1)
                if b and b[0] == RSP_RELEASE_OK:
                    return True
            time.sleep(0.001)
        return False

    def reset(self):
        """Reset the FPGA cell array."""
        self._send(bytes([CMD_RESET]))
        time.sleep(0.1)
        print("[FPGA] Array reset")

    def get_status(self, timeout: float = 2.0) -> Optional[dict]:
        """Query array status — armed cell count and cycle count."""
        # Clear any pending responses
        while not self._rx_queue.empty():
            try:
                self._rx_queue.get_nowait()
            except queue.Empty:
                break

        self._send(bytes([CMD_STATUS]))

        try:
            rsp = self._rx_queue.get(timeout=timeout)
            if rsp[0] == 'status':
                return {'armed': rsp[1], 'cycles': rsp[2]}
        except queue.Empty:
            pass
        return None

    def wait_for_fire(self, timeout: float = 5.0) -> Optional[tuple]:
        """
        Wait for any cell to fire and return (addr, data).

        Used for synchronous test execution — send input, wait for output.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                rsp = self._rx_queue.get(timeout=0.1)
                if rsp[0] == 'fired':
                    return (rsp[1], rsp[2])
            except queue.Empty:
                pass
        return None

    def on_fire(self, callback: Callable):
        """Register a callback called when any cell fires: callback(addr, data)."""
        self._fire_callbacks.append(callback)

    # ── High level operations ─────────────────────────────────────────────────

    def load_map(self, cell_map: list, base_address: int = 0x00001000) -> bool:
        """
        Load a compiled CellMapRecord list onto the FPGA.

        cell_map: list of CellMapRecord from the Python compiler
        base_address: starting address in the FPGA address space

        This is the bridge between the Python compiler output and
        the physical FPGA cell array.
        """
        print(f"[FPGA] Loading {len(cell_map)} cells from base {hex(base_address)}")

        for i, record in enumerate(cell_map):
            cell_addr = base_address + i

            # Extract fields from CellMapRecord
            # (compatible with compiler.py output format)
            if hasattr(record, 'gate_state'):
                gs     = record.gate_state
                iaddr  = record.input_address
                oaddr  = record.output_address
            elif isinstance(record, (list, tuple)) and len(record) >= 3:
                gs, iaddr, oaddr = record[0], record[1], record[2]
            else:
                print(f"[FPGA] Unknown record format at index {i}")
                continue

            self.configure_cell(cell_addr, gs, iaddr, oaddr)

            # v2: register input_b_address for two-input cells
            # Sent as a 5th word after the standard 4-word config sequence
            b_addr = getattr(record, 'input_b_address', None)
            if b_addr is not None:
                self.inject(cell_addr, b_addr)  # 5th config word: B input address

            if i % 10 == 0:
                print(f"[FPGA] Loaded {i+1}/{len(cell_map)} cells...",
                      end='\r')

        print(f"[FPGA] Load complete — {len(cell_map)} cells configured")
        return True

    def run_test(self, inputs: dict, output_addrs: list,
                 timeout: float = 5.0) -> dict:
        """
        Run a loaded program by injecting inputs and collecting outputs.

        inputs: {address: value}
        output_addrs: [address, ...] to collect results from
        Returns: {address: value}
        """
        results = {}
        pending = set(output_addrs)

        def capture(addr, data):
            if addr in pending:
                results[addr] = data
                pending.discard(addr)

        self.on_fire(capture)

        # Inject inputs
        for addr, value in inputs.items():
            self.inject(addr, value)

        # Wait for all outputs
        deadline = time.time() + timeout
        while pending and time.time() < deadline:
            time.sleep(0.01)

        # Remove capture callback
        self._fire_callbacks = [
            cb for cb in self._fire_callbacks if cb != capture]

        return results

    # ── Demo programs ─────────────────────────────────────────────────────────

    def demo_not_gate(self):
        """
        Load and test a single NOT gate.
        The simplest possible UniCell program.
        """
        print("\n[FPGA] Demo: NOT gate")
        print("  Configure one cell as GS_NOT")
        print("  Input address:  0x1000")
        print("  Output address: 0x2000")

        GS_NOT = 0x00000001
        self.configure_cell(
            cell_addr=0x0001,
            gate_state=GS_NOT,
            input_addr=0x1000,
            output_addr=0x2000
        )

        time.sleep(0.1)

        print("  Injecting input=0...")
        self.inject(0x1000, 0)
        result = self.wait_for_fire(timeout=2.0)
        if result:
            print(f"  Output at {hex(result[0])}: {result[1]} (expected 1)")
        else:
            print("  No output received")

        print("  Injecting input=1...")
        self.inject(0x1000, 1)
        result = self.wait_for_fire(timeout=2.0)
        if result:
            print(f"  Output at {hex(result[0])}: {result[1]} (expected 0)")
        else:
            print("  No output received")

    def demo_wired_or_nand(self):
        """
        Load and test NAND via wired-OR.
        Two NOT cells sharing an output address produce NAND by De Morgan.
        This demonstrates the key architectural property.
        """
        print("\n[FPGA] Demo: NAND via wired-OR (two NOT cells)")
        print("  Cell A: NOT(input_A) → address 0x3000")
        print("  Cell B: NOT(input_B) → address 0x3000")
        print("  Address 0x3000 receives OR of both outputs = NAND(A,B)")

        GS_NOT = 0x00000001
        self.configure_cell(0x0002, GS_NOT, 0x1100, 0x3000)
        self.configure_cell(0x0003, GS_NOT, 0x1200, 0x3000)

        time.sleep(0.1)

        test_cases = [(0,0,1), (0,1,1), (1,0,1), (1,1,0)]
        for a, b, expected in test_cases:
            self.inject(0x1100, a)
            self.inject(0x1200, b)
            time.sleep(0.05)
            result = self.wait_for_fire(timeout=1.0)
            got = result[1] if result else '?'
            status = '✓' if got == expected else '✗'
            print(f"  NAND({a},{b}) = {got} (expected {expected}) {status}")


# ── CLI entry point ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Imago UniCell FPGA Bridge"
    )
    parser.add_argument("--port", required=True,
                        help="Serial port (e.g. COM3 or /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200,
                        help="Baud rate (default: 115200)")
    parser.add_argument("--demo", action="store_true",
                        help="Run demo programs after connecting")
    parser.add_argument("--reset", action="store_true",
                        help="Reset the array on connect")
    args = parser.parse_args()

    bridge = FPGABridge(port=args.port, baud=args.baud)

    if not bridge.connect():
        sys.exit(1)

    if args.reset:
        bridge.reset()

    if args.demo:
        bridge.demo_not_gate()
        time.sleep(0.5)
        bridge.demo_wired_or_nand()

    status = bridge.get_status()
    if status:
        print(f"\n[FPGA] Status:")
        print(f"  Armed cells: {status['armed']}")
        print(f"  Cycles:      {status['cycles']}")
        print(f"  Injected:    {bridge.stats['injected']}")
        print(f"  Configured:  {bridge.stats['configured']}")
        print(f"  Fired:       {bridge.stats['fired']}")
        print(f"  Errors:      {bridge.stats['errors']}")

    bridge.disconnect()


if __name__ == "__main__":
    main()
