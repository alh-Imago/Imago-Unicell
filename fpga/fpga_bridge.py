"""
fpga_bridge.py — Python Host Bridge for UniCell FPGA
Claudette v2.0 — updated for unicell_v3 protocol

Changes from v1.1:
  - LOAD_PATTERN magic retired — cmd_bus carries all config protocol
  - reconfigure_cell() replaces configure_cell() — 2-word sequence
  - CMD_SET_INPUT_ADDR / CMD_SET_OUTPUT_ADDR are separate commands
  - build_cmd_bus() constructs the full 32-bit Bus 1 word
  - Auth token required for system commands (RECONFIGURE/FREEZE/RELEASE)
  - SCOPE_EXTENDED retired — all addresses are 32-bit
  - input_b_address removed — SYNC_WAIT counts arrivals at own address
  - Sequence count (cmd_bus bits 22-28) and identifier (bits 29-31) supported

Command bus (cmd_bus) — now 8-bit opcode only:
  bits  0-7:   command code (256 opcodes, 243 free)

cmd_data — 16-bit payload:
  bits 15-5:   auth_token (11 bits, 2048 values) for auth commands
  bits  4-0:   spare / payload low bits

bus_addr — 16-bit logical address (65,536 cell address space)

CMD_RECONFIGURE sequence:
  First boot (auth_mask==0 on cell):
    Packet 0: CMD_RECONFIGURE, bus_data = auth_token[10:0]
    Packet 1: CMD_NOP,         bus_data = 32-bit config word
  Subsequent:
    Packet 0: CMD_RECONFIGURE, bus_data = 32-bit config word
  Then separately:
    CMD_SET_INPUT_ADDR  bus_data = input address
    CMD_SET_OUTPUT_ADDR bus_data = output address
"""

import serial
import struct
import time
import threading
import queue
import sys
import argparse
from typing import Optional, Callable

# ── Command codes ──────────────────────────────────────────────────────────────
CMD_NOP             = 0x0
CMD_DATA_WRITE      = 0x1
CMD_SET_INPUT_ADDR  = 0x2
CMD_SET_OUTPUT_ADDR = 0x3
CMD_RECONFIGURE     = 0x4
CMD_FREEZE          = 0x5
CMD_RELEASE         = 0x6
# CMD_COPY_TO_OUT = 0x7  -- retired (not in Verilog)
# CMD_COPY_TO_IN  = 0x8  -- retired (not in Verilog)
CMD_PING            = 0x9
CMD_LATCH_IN_ON     = 0xA
CMD_LATCH_IN_OFF    = 0xB
CMD_MEM_CALL        = 0xC
CMD_REARM           = 0xD
CMD_SET_LOGICAL     = 0xE  # set logical input addr, suppress physical ID

# ── UART protocol ──────────────────────────────────────────────────────────────
UART_INJECT     = 0x01
UART_RESET      = 0x03
UART_STATUS     = 0x04
UART_FREEZE     = 0x06
UART_RELEASE    = 0x07

RSP_FIRED       = 0x10
RSP_STATUS      = 0x11
RSP_FREEZE_OK   = 0x13
RSP_RELEASE_OK  = 0x14
RSP_ERROR       = 0xFF

# ── Handshake ──────────────────────────────────────────────────────────────────
HANDSHAKE_NONE    = 0x0
HANDSHAKE_ACK     = 0x1
HANDSHAKE_NAK     = 0x2
HANDSHAKE_BUSY    = 0x3
HANDSHAKE_REQUEST = 0x4
HANDSHAKE_GRANT   = 0x5
HANDSHAKE_DENY    = 0x6
HANDSHAKE_RETRY   = 0x7

SCOPE_LOCAL = 0b00

# ── Cell / data type ───────────────────────────────────────────────────────────
CTYPE_STANDARD = 0b00
CTYPE_LATCH    = 0b01
CTYPE_POSEDGE  = 0b10
CTYPE_NEGEDGE  = 0b11

DTYPE_NUMERIC  = 0b00
DTYPE_SIGNED   = 0b01
DTYPE_ALPHA    = 0b10
DTYPE_DATETIME = 0b11


def build_cmd_bus(code:      int  = CMD_NOP,
                  auth:      int  = 0,
                  raw_addr:  bool = True,
                  scope:     int  = SCOPE_LOCAL,
                  handshake: int  = HANDSHAKE_NONE,
                  seq_count: int  = 0,
                  ident:     int  = 0) -> int:
    """Return 8-bit opcode. Auth token now carried in cmd_data[15:5]."""
    return code & 0xFF


def build_cmd_data_with_auth(auth: int = 0, payload: int = 0) -> int:
    """
    Build 32-bit cmd_data: auth_token in [31:24], payload in [23:0].
    auth    = 8-bit token (256 values)
    payload = 24-bit config/address word
    """
    return ((auth & 0xFF) << 24) | (payload & 0xFFFFFF)


def build_config_word(topology:    int  = 0,
                      sync_wait:   bool = False,
                      edge_mode:   bool = False,
                      dtype:       int  = DTYPE_NUMERIC,
                      invert_out:  bool = False,
                      latch_in:    bool = False,
                      priority:    bool = False,
                      trace:       bool = False,
                      breakpoint:  bool = False,
                      one_shot:    bool = False,
                      loop_back:   bool = False) -> int:
    """
    Build 24-bit config word for CMD_RECONFIGURE cmd_data[23:0].
    Matches unicell.v CMD_RECONFIGURE bit mapping:
      [9:0]  topology
      [10]   edge_mode
      [11]   start_flag (always 1)
      [13:12] dtype
      [14]   invert_out
      [15]   latch_in (sync_wait)
      [16]   priority
      [17]   trace
      [18]   breakpoint
      [19]   one_shot
      [20]   loop_back
    auth_mask in cmd_data[31:24] via build_cmd_data_with_auth.
    """
    w  = (topology   & 0x3FF)
    w |= (1 if edge_mode   else 0) << 10
    w |= 1                         << 11  # start_flag always set
    w |= (dtype      & 0x3)        << 12
    w |= (1 if invert_out  else 0) << 14
    w |= (1 if (sync_wait or latch_in) else 0) << 15
    w |= (1 if priority    else 0) << 16
    w |= (1 if trace       else 0) << 17
    w |= (1 if breakpoint  else 0) << 18
    w |= (1 if one_shot    else 0) << 19
    w |= (1 if loop_back   else 0) << 20
    return w


class FPGABridge:
    """Host bridge to unicell_v3 FPGA array via UART."""

    def __init__(self, port: str, baud: int = 115200,
                 timeout: float = 2.0, auth_token: int = 0):
        self.port        = port
        self.baud        = baud
        self.timeout     = timeout
        self.auth_token  = auth_token
        self._ser        = None
        self._rx_queue   = queue.Queue()
        self._rx_thread  = None
        self._running    = False
        self._lock       = threading.Lock()
        self._fire_cbs   = []
        self.stats       = {'injected':0,'configured':0,'fired':0,'errors':0}

    # ── Connection ─────────────────────────────────────────────────────────────

    def connect(self) -> bool:
        try:
            self._ser = serial.Serial(
                port=self.port, baudrate=self.baud,
                bytesize=8, parity='N', stopbits=1, timeout=self.timeout)
            self._running = True
            self._rx_thread = threading.Thread(
                target=self._rx_loop, daemon=True)
            self._rx_thread.start()
            time.sleep(0.1)
            status = self.get_status()
            if status is None:
                print(f"[FPGA] No response from {self.port}")
                return False
            print(f"[FPGA] Connected {self.port} @ {self.baud}")
            print(f"[FPGA] Cycles: {status['cycles']}")
            return True
        except serial.SerialException as e:
            print(f"[FPGA] Connection failed: {e}")
            return False

    def disconnect(self):
        self._running = False
        if self._ser and self._ser.is_open:
            self._ser.close()
        print("[FPGA] Disconnected")

    # ── RX ─────────────────────────────────────────────────────────────────────

    def _rx_loop(self):
        buf = bytearray()
        while self._running:
            try:
                if self._ser.in_waiting:
                    buf += self._ser.read(self._ser.in_waiting)
                    buf = self._process(buf)
                else:
                    time.sleep(0.001)
            except Exception as e:
                if self._running: print(f"[FPGA] RX: {e}")

    def _process(self, buf):
        while buf:
            cmd = buf[0]
            if cmd == RSP_FIRED and len(buf) >= 8:
                # Frame: 0x10 + 2B addr + 4B data + 2B pad
                addr = struct.unpack('>H', buf[1:3])[0]
                data = struct.unpack('>I', buf[3:7])[0]
                self._rx_queue.put(('fired', addr, data, 0))
                self.stats['fired'] += 1
                for cb in self._fire_cbs:
                    try: cb(addr, data, 0)
                    except: pass
                buf = buf[8:]
            elif cmd == RSP_STATUS and len(buf) >= 7:
                armed  = struct.unpack('>H', buf[1:3])[0]
                cycles = struct.unpack('>I', buf[3:7])[0]
                self._rx_queue.put(('status', armed, cycles))
                buf = buf[7:]
            elif cmd == RSP_ERROR:
                self.stats['errors'] += 1
                self._rx_queue.put(('error',))
                buf = buf[1:]
            elif cmd in (RSP_FIRED, RSP_STATUS, RSP_FREEZE_OK, RSP_RELEASE_OK):
                break
            else:
                buf = buf[1:]
        return buf

    # ── Low level ──────────────────────────────────────────────────────────────

    def _send(self, data: bytes):
        with self._lock:
            if self._ser and self._ser.is_open:
                self._ser.write(data)

    def _inject_raw(self, cmd_bus: int, bus_addr: int, bus_data: int):
        """Send 8-byte command frame: 0x01 + opcode(1) + addr(2) + data(4)
        cmd_bus  = 8-bit opcode
        bus_addr = 16-bit physical/logical address
        bus_data = 32-bit payload: auth[31:24] + config/data[23:0]
        """
        pkt = struct.pack('>BBHI',
                          UART_INJECT,
                          cmd_bus  & 0xFF,
                          bus_addr & 0xFFFF,
                          bus_data & 0xFFFFFFFF)
        self._send(pkt)
        self.stats['injected'] += 1

    # ── Cell config ────────────────────────────────────────────────────────────

    def set_input_addr(self, cell_addr: int, input_addr: int, seq: int = 0):
        """Set cell input address. cell_addr = physical ID during boot."""
        self._inject_raw(
            build_cmd_bus(code=CMD_SET_INPUT_ADDR),
            cell_addr & 0xFFFF, input_addr & 0xFFFF)
        time.sleep(0.001)

    def set_output_addr(self, cell_addr: int, output_addr: int, seq: int = 0):
        """Set cell output address. cell_addr = physical ID during boot."""
        self._inject_raw(
            build_cmd_bus(code=CMD_SET_OUTPUT_ADDR),
            cell_addr & 0xFFFF, output_addr & 0xFFFF)
        time.sleep(0.001)

    def reconfigure_cell(self,
                         cell_addr:      int,
                         topology:       int  = 0,
                         sync_wait:      bool = False,
                         dtype:          int  = DTYPE_NUMERIC,
                         ctype:          int  = CTYPE_STANDARD,
                         priority:       bool = False,
                         trace:          bool = False,
                         breakpoint_flag:bool = False,
                         input_addr:     int  = 0,
                         output_addr:    int  = 0,
                         is_first_boot:  bool = False) -> bool:
        """
        Configure a cell. Auth required (uses self.auth_token).
        is_first_boot=True: sends auth_mask word first (cell starts with mask=0).
        """
        cfg = build_config_word(
            topology=topology, sync_wait=sync_wait,
            dtype=dtype, ctype=ctype,
            priority=priority, trace=trace, breakpoint=breakpoint_flag)

        # Single packet: auth[31:24] + config[23:0] in cmd_data
        # Cell targeted via physical ID on cmd_addr during boot
        cmd_data = build_cmd_data_with_auth(auth=self.auth_token, payload=cfg & 0xFFFFFF)
        self._inject_raw(build_cmd_bus(code=CMD_RECONFIGURE),
                         cell_addr & 0xFFFF, cmd_data)

        time.sleep(0.001)

        if input_addr:
            self.set_input_addr(cell_addr, input_addr)
        if output_addr:
            self.set_output_addr(cell_addr, output_addr)

        self.stats['configured'] += 1
        return True

    # ── Runtime commands ───────────────────────────────────────────────────────

    def inject(self, addr: int, data: int,
               handshake: int = HANDSHAKE_NONE,
               seq_count: int = 0, ident: int = 0) -> bool:
        """Write data to a cell input address (16-bit addr, 16-bit data)."""
        self._inject_raw(
            build_cmd_bus(code=CMD_DATA_WRITE),
            addr & 0xFFFF, data & 0xFFFF)
        return True

    def ping(self, cell_addr: int = 0):
        self._inject_raw(build_cmd_bus(code=CMD_PING), cell_addr & 0xFFFF, 0)

    def freeze_cell(self, cell_addr: int):
        auth_data = build_cmd_data_with_auth(auth=self.auth_token)
        self._inject_raw(build_cmd_bus(code=CMD_FREEZE),
                         cell_addr & 0xFFFF, auth_data)

    def release_cell(self, cell_addr: int):
        auth_data = build_cmd_data_with_auth(auth=self.auth_token)
        self._inject_raw(build_cmd_bus(code=CMD_RELEASE),
                         cell_addr & 0xFFFF, auth_data)

    def latch_in_on(self, cell_addr: int):
        auth_data = build_cmd_data_with_auth(auth=self.auth_token)
        self._inject_raw(build_cmd_bus(code=CMD_LATCH_IN_ON),
                         cell_addr & 0xFFFF, auth_data)

    def latch_in_off(self, cell_addr: int):
        auth_data = build_cmd_data_with_auth(auth=self.auth_token)
        self._inject_raw(build_cmd_bus(code=CMD_LATCH_IN_OFF),
                         cell_addr & 0xFFFF, auth_data)

    def mem_call(self, cell_addr: int):
        auth_data = build_cmd_data_with_auth(auth=self.auth_token)
        self._inject_raw(build_cmd_bus(code=CMD_MEM_CALL),
                         cell_addr & 0xFFFF, auth_data)

    def rearm(self, cell_addr: int):
        auth_data = build_cmd_data_with_auth(auth=self.auth_token)
        self._inject_raw(build_cmd_bus(code=CMD_REARM),
                         cell_addr & 0xFFFF, auth_data)

    def set_logical_addr(self, cell_addr: int, logical_addr: int):
        """Switch cell from physical to logical address mode."""
        auth_data = build_cmd_data_with_auth(auth=self.auth_token,
                                             payload=logical_addr & 0xFFFF)
        self._inject_raw(build_cmd_bus(code=CMD_SET_LOGICAL),
                         cell_addr & 0xFFFF, auth_data)

    def reset(self):
        self._send(bytes([UART_RESET]))
        time.sleep(0.1)
        print("[FPGA] Reset")

    def get_status(self, timeout: float = 2.0) -> Optional[dict]:
        while not self._rx_queue.empty():
            try: self._rx_queue.get_nowait()
            except queue.Empty: break
        self._send(bytes([UART_STATUS]))
        try:
            rsp = self._rx_queue.get(timeout=timeout)
            if rsp[0] == 'status':
                return {'armed': rsp[1], 'cycles': rsp[2]}
        except queue.Empty:
            pass
        return None

    def wait_for_fire(self, timeout: float = 5.0) -> Optional[tuple]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                rsp = self._rx_queue.get(timeout=0.1)
                if rsp[0] == 'fired': return (rsp[1], rsp[2])
            except queue.Empty: pass
        return None

    def on_fire(self, cb: Callable):
        self._fire_cbs.append(cb)

    # ── Load map ───────────────────────────────────────────────────────────────

    def load_map(self, cell_map: list,
                 base_address: int = 0x00001000,
                 first_boot:   bool = True) -> bool:
        print(f"[FPGA] Loading {len(cell_map)} cells from {hex(base_address)}")
        for i, rec in enumerate(cell_map):
            caddr = base_address + i
            if hasattr(rec, 'gate_state'):
                gs    = rec.gate_state
                topo  = gs & 0x3FF
                sw    = bool(gs & (1 << 10))
                dtype = (gs >> 23) & 0x3
                ctype = (gs >> 25) & 0x3
                prio  = bool(gs & (1 << 27))
                tr    = bool(gs & (1 << 28))
                bp    = bool(gs & (1 << 29))
                ia, oa = rec.input_address, rec.output_address
            elif isinstance(rec, (list, tuple)) and len(rec) >= 3:
                topo, ia, oa = rec[0] & 0x3FF, rec[1], rec[2]
                sw = dtype = ctype = prio = tr = bp = 0
            else:
                print(f"[FPGA] Unknown record at {i}"); continue

            self.reconfigure_cell(
                cell_addr=caddr, topology=topo, sync_wait=sw,
                dtype=dtype, ctype=ctype, priority=prio,
                trace=tr, breakpoint_flag=bp,
                input_addr=ia, output_addr=oa,
                is_first_boot=(first_boot and i == 0))

            if i % 10 == 0:
                print(f"[FPGA] {i+1}/{len(cell_map)}...", end='\r')

        print(f"[FPGA] Done — {len(cell_map)} cells")
        return True

    # ── Demos ──────────────────────────────────────────────────────────────────

    def demo_not_gate(self):
        print("\n[FPGA] Demo: NOT gate")
        self.reconfigure_cell(
            cell_addr=0, topology=0b0000000001,
            ctype=CTYPE_STANDARD, dtype=DTYPE_NUMERIC,
            input_addr=0x1000, output_addr=0x2000,
            is_first_boot=True)
        time.sleep(0.1)
        for val, exp in [(0, 1), (1, 0)]:
            self.inject(0x1000, val)
            r = self.wait_for_fire(2.0)
            got = r[1] if r else '?'
            print(f"  NOT({val})={got} (exp {exp}) {'✓' if got==exp else '✗'}")

    def demo_latch(self):
        print("\n[FPGA] Demo: LATCH cell")
        self.reconfigure_cell(
            cell_addr=0, topology=0b0000000001,
            ctype=CTYPE_LATCH, input_addr=0x1000, output_addr=0x2000)
        time.sleep(0.1)
        self.inject(0x1000, 0)
        for i in range(3):
            r = self.wait_for_fire(1.0)
            if r: print(f"  Tick {i+1}: {r[1]}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Imago UniCell FPGA Bridge v2")
    p.add_argument("--port",  required=True)
    p.add_argument("--baud",  type=int, default=115200)
    p.add_argument("--auth",  type=lambda x: int(x, 0), default=0,
                   help="11-bit auth token e.g. 0x2A5")
    p.add_argument("--demo",  action="store_true")
    p.add_argument("--reset", action="store_true")
    args = p.parse_args()

    bridge = FPGABridge(port=args.port, baud=args.baud,
                        auth_token=args.auth)
    if not bridge.connect(): sys.exit(1)
    if args.reset: bridge.reset()
    if args.demo:
        bridge.demo_not_gate()
        time.sleep(0.5)

    s = bridge.get_status()
    if s:
        print(f"\n[FPGA] cycles={s['cycles']} "
              f"injected={bridge.stats['injected']} "
              f"fired={bridge.stats['fired']} "
              f"errors={bridge.stats['errors']}")
    bridge.disconnect()


if __name__ == "__main__":
    main()
