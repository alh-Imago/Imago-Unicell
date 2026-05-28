"""
fpga_bridge.py — Python Host Bridge for UniCell FPGA
Protocol v2.2 — compound opcodes, nibble mask, latch disable

Changes from v2.0:
  - New opcodes: CMD_CLEAR_ARRIVED, CMD_RESET_CELL, CMD_SWAP_AB,
    CMD_SET_TOPO, CMD_SET_INVERT
  - Topology preset opcodes (48-69): CMD_TOPO_PASS_A through CMD_TOPO_ONE
  - cmd_data payload layout v2.2:
      [31:24] auth_token
      [23]    mask_enable
      [22:15] nibble_mask (8-bit, one per nibble of 32-bit word)
      [14]    latch_B_dis
      [13]    latch_A_dis
      [12:0]  spare/payload
  - make_cmd() — single function to build any command word
  - configure_gate() — declarative cell configuration
  - auth token narrowed from 11-bit to 8-bit (cmd_data[31:24])
  - sync_wait retired — use latch_in or latch_A_dis/latch_B_dis
  - ctype retired — edge_mode flag replaces it

Command word (8 bytes):
  [0]    0x01 UART_INJECT
  [1]    opcode (8-bit)
  [2:3]  cmd_addr (16-bit, physical ID or logical address)
  [4:7]  cmd_data (32-bit, auth[31:24]+payload[23:0])

Fired response (7 bytes):
  [0]    0x10
  [1:2]  out_addr (16-bit)
  [3:6]  out_data (32-bit)

Status response (7 bytes):
  [0]    0x11
  [1:2]  armed_count (16-bit)
  [3:6]  cycle_count (32-bit)
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
CMD_NOP             = 0x00
CMD_DATA_WRITE      = 0x01
CMD_SET_INPUT_ADDR  = 0x02
CMD_SET_OUTPUT_ADDR = 0x03
CMD_RECONFIGURE     = 0x04
CMD_FREEZE          = 0x05
CMD_RELEASE         = 0x06
CMD_PING            = 0x09
CMD_LATCH_IN_ON     = 0x0A
CMD_LATCH_IN_OFF    = 0x0B
CMD_MEM_CALL        = 0x0C
CMD_REARM           = 0x0D
CMD_SET_LOGICAL     = 0x0E
CMD_PRELOAD         = 0x0F  # load a_data[23:0] from cmd_data[23:0], set a_arrived

# Cell state control (16-22)
CMD_CLEAR_ARRIVED   = 0x10  # clear a_arrived + a_data
CMD_RESET_CELL      = 0x11  # clear state + rearm
CMD_SWAP_AB         = 0x12  # load a_data from 13-bit payload, set a_arrived (legacy)
CMD_CAPTURE_REARM   = 0x13  # fire output + rearm one_shot
CMD_SET_TOPO        = 0x14  # write topology bits only
CMD_SET_INVERT      = 0x15  # toggle invert_out
CMD_PRELOAD_HI      = 0x16  # load a_data[31:16] from cmd_data[15:0] (upper half)

# Topology presets — cold=even (disarmed), armed=odd
# Python: CMD_TOPO_BASE + (gate_index * 2) + armed
CMD_TOPO_BASE       = 48
CMD_TOPO_PASS_A_COLD = 48;  CMD_TOPO_PASS_A = 49
CMD_TOPO_NOT_A_COLD  = 50;  CMD_TOPO_NOT_A  = 51
CMD_TOPO_NOR_COLD    = 52;  CMD_TOPO_NOR    = 53
CMD_TOPO_AND_COLD    = 54;  CMD_TOPO_AND    = 55
CMD_TOPO_OR_COLD     = 56;  CMD_TOPO_OR     = 57
CMD_TOPO_NAND_COLD   = 58;  CMD_TOPO_NAND   = 59
CMD_TOPO_PASS_B_COLD = 60;  CMD_TOPO_PASS_B = 61
CMD_TOPO_XNOR_COLD   = 62;  CMD_TOPO_XNOR   = 63
CMD_TOPO_XOR_COLD    = 64;  CMD_TOPO_XOR    = 65
CMD_TOPO_ZERO_COLD   = 66;  CMD_TOPO_ZERO   = 67
CMD_TOPO_ONE_COLD    = 68;  CMD_TOPO_ONE    = 69

# Topology hex values (for CMD_RECONFIGURE / CMD_SET_TOPO)
TOPO_PASS_A = 0x000
TOPO_NOT_A  = 0x001
TOPO_NOT_B  = 0x002
TOPO_NOR    = 0x004
TOPO_AND    = 0x007
TOPO_OR     = 0x024
TOPO_PASS_B = 0x02C
TOPO_NAND   = 0x027
TOPO_XNOR   = 0x03C
TOPO_XOR    = 0x0BC
TOPO_ZERO   = 0x030
TOPO_ONE    = 0x0B0

# ── UART protocol ──────────────────────────────────────────────────────────────
UART_INJECT  = 0x01
UART_RESET   = 0x03
UART_STATUS  = 0x04
UART_FREEZE  = 0x06
UART_RELEASE = 0x07

RSP_FIRED    = 0x10
RSP_STATUS   = 0x11
RSP_ERROR    = 0xFF

# ── Data types ────────────────────────────────────────────────────────────────
DTYPE_NUMERIC  = 0b00
DTYPE_SIGNED   = 0b01
DTYPE_ALPHA    = 0b10
DTYPE_DATETIME = 0b11


# ── Command word builder ───────────────────────────────────────────────────────

def make_cmd(auth:       int  = 0,
             payload:    int  = 0,
             mask:       int  = None,
             latch_a:    bool = False,
             latch_b:    bool = False) -> int:
    """
    Build 32-bit cmd_data word for any non-address opcode.

    auth    — 8-bit token, placed in [31:24]
    payload — up to 13-bit data, placed in [12:0]
    mask    — 8-bit nibble mask (None=disabled, 0xFF=all nibbles)
              bit7=nibble7[31:28] .. bit0=nibble0[3:0]
    latch_a — True=disable A latch store (PASS(B) effect)
    latch_b — True=disable B arrival trigger (PASS(A) effect)

    Examples:
      make_cmd(auth=0xA5)                          # auth only
      make_cmd(auth=0xA5, mask=0b00110000)         # upper two nibbles
      make_cmd(auth=0xA5, latch_a=True)            # PASS(B) mode
      make_cmd(payload=0x1234)                     # address payload
    """
    word  = payload & 0x1FFF                       # [12:0]  payload
    word |= (1 if latch_a else 0) << 13            # [13]    latch_A_dis
    word |= (1 if latch_b else 0) << 14            # [14]    latch_B_dis
    if mask is not None:
        word |= (mask & 0xFF) << 15                # [22:15] nibble_mask
        word |= 1 << 23                            # [23]    mask_enable
    word |= (auth & 0xFF) << 24                    # [31:24] auth_token
    return word


def build_config_word(topology:    int  = 0,
                      edge_mode:   bool = False,
                      dtype:       int  = DTYPE_NUMERIC,
                      invert_out:  bool = False,
                      latch_in:    bool = False,
                      latch_a_dis: bool = False,
                      latch_b_dis: bool = False,
                      priority:    bool = False,
                      trace:       bool = False,
                      breakpoint:  bool = False,
                      one_shot:    bool = False,
                      loop_back:   bool = False) -> int:
    """
    Build 23-bit config payload for CMD_RECONFIGURE cmd_data[22:0].
    Matches unicell.v v2.2 CMD_RECONFIGURE bit mapping:
      [9:0]   topology
      [10]    edge_mode
      [11]    start_flag (always 1)
      [12]    latch_A_dis
      [13]    latch_B_dis
      [15:14] dtype
      [16]    invert_out
      [17]    latch_in
      [18]    priority
      [19]    trace
      [20]    breakpoint
      [21]    one_shot
      [22]    loop_back
    auth_mask goes in cmd_data[31:24] via make_cmd().
    """
    w  = (topology    & 0x3FF)
    w |= (1 if edge_mode    else 0) << 10
    w |= 1                          << 11  # start_flag always set
    w |= (1 if latch_a_dis  else 0) << 12
    w |= (1 if latch_b_dis  else 0) << 13
    w |= (dtype        & 0x3)       << 14
    w |= (1 if invert_out   else 0) << 16
    w |= (1 if latch_in     else 0) << 17
    w |= (1 if priority     else 0) << 18
    w |= (1 if trace        else 0) << 19
    w |= (1 if breakpoint   else 0) << 20
    w |= (1 if one_shot     else 0) << 21
    w |= (1 if loop_back    else 0) << 22
    return w


class FPGABridge:
    """Host bridge to UniCell FPGA array via UART. Protocol v2.2."""

    def __init__(self, port: str, baud: int = 115200,
                 timeout: float = 2.0, auth_token: int = 0):
        self.port       = port
        self.baud       = baud
        self.timeout    = timeout
        self.auth_token = auth_token
        self._ser       = None
        self._rx_queue  = queue.Queue()
        self._rx_thread = None
        self._running   = False
        self._lock      = threading.Lock()
        self._fire_cbs  = []
        self.stats      = {'injected':0,'configured':0,'fired':0,'errors':0}

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
            if cmd == RSP_FIRED and len(buf) >= 7:
                addr = struct.unpack('>H', buf[1:3])[0]
                data = struct.unpack('>I', buf[3:7])[0]
                self._rx_queue.put(('fired', addr, data))
                self.stats['fired'] += 1
                for cb in self._fire_cbs:
                    try: cb(addr, data)
                    except: pass
                buf = buf[7:]
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
                buf = buf[1:]
        return buf

    # ── Low level TX ───────────────────────────────────────────────────────────

    def _send(self, data: bytes):
        with self._lock:
            if self._ser and self._ser.is_open:
                self._ser.write(data)

    def _inject_raw(self, opcode: int, cmd_addr: int, cmd_data: int):
        """Send 8-byte command frame: 0x01 + opcode(1) + addr(2) + data(4)."""
        pkt = struct.pack('>BBHI',
                          UART_INJECT,
                          opcode   & 0xFF,
                          cmd_addr & 0xFFFF,
                          cmd_data & 0xFFFFFFFF)
        self._send(pkt)
        self.stats['injected'] += 1

    # ── Cell configuration ────────────────────────────────────────────────────

    def boot_cell(self, cell_id:     int,
                        topology:    int  = TOPO_PASS_A,
                        input_addr:  int  = 0,
                        output_addr: int  = 0,
                        auth:        int  = None,
                        edge_mode:   bool = False,
                        latch_in:    bool = False,
                        latch_a_dis: bool = False,
                        latch_b_dis: bool = False,
                        one_shot:    bool = False,
                        loop_back:   bool = False,
                        dtype:       int  = DTYPE_NUMERIC) -> None:
        """
        Full 4-packet cell boot sequence:
          1. CMD_RECONFIGURE  — topology + flags + auth_mask
          2. CMD_SET_LOGICAL  — logical input address
          3. CMD_SET_OUTPUT_ADDR — output address
          4. CMD_RELEASE      — arm cell

        cell_id    — physical ID (matches CELL_ID parameter in Verilog)
        auth       — auth token (default: self.auth_token)
        """
        if auth is None:
            auth = self.auth_token

        cfg = build_config_word(
            topology=topology, edge_mode=edge_mode,
            latch_in=latch_in, latch_a_dis=latch_a_dis,
            latch_b_dis=latch_b_dis, dtype=dtype,
            one_shot=one_shot, loop_back=loop_back)

        # 1. RECONFIGURE — topology + flags, auth_mask set from token
        self._inject_raw(CMD_RECONFIGURE, cell_id,
                         make_cmd(auth=auth, payload=cfg))
        time.sleep(0.001)

        # 2. SET_LOGICAL — input address, switch from physical to logical
        self._inject_raw(CMD_SET_LOGICAL, cell_id,
                         make_cmd(auth=auth, payload=input_addr & 0xFFFF))
        time.sleep(0.001)

        # 3. SET_OUTPUT_ADDR — output address
        self._inject_raw(CMD_SET_OUTPUT_ADDR, cell_id,
                         make_cmd(auth=auth, payload=output_addr & 0xFFFF))
        time.sleep(0.001)

        # 4. RELEASE — arm cell
        self._inject_raw(CMD_RELEASE, cell_id, make_cmd(auth=auth))
        time.sleep(0.001)

        self.stats['configured'] += 1

    def configure_gate(self, cell_addr:  int,
                             opcode:     int,
                             mask:       int  = None,
                             latch_a:    bool = False,
                             latch_b:    bool = False) -> None:
        """
        Declarative gate configuration using topology preset opcodes.
        Single command replaces full RECONFIGURE ceremony.

        configure_gate(0x42, CMD_TOPO_AND)
        configure_gate(0x42, CMD_TOPO_AND, mask=0b00110000)  # upper 2 nibbles
        configure_gate(0x42, CMD_TOPO_PASS_A_COLD)           # config, stay cold
        """
        self._inject_raw(opcode, cell_addr,
                         make_cmd(auth=self.auth_token,
                                  mask=mask,
                                  latch_a=latch_a,
                                  latch_b=latch_b))

    def reconfigure_cell(self, cell_addr:   int,
                               topology:    int  = 0,
                               input_addr:  int  = 0,
                               output_addr: int  = 0,
                               edge_mode:   bool = False,
                               latch_in:    bool = False,
                               latch_a_dis: bool = False,
                               latch_b_dis: bool = False,
                               dtype:       int  = DTYPE_NUMERIC,
                               priority:    bool = False,
                               trace:       bool = False,
                               breakpoint_flag: bool = False,
                               one_shot:    bool = False,
                               loop_back:   bool = False,
                               # Legacy compat
                               sync_wait:   bool = False,
                               ctype:       int  = 0,
                               is_first_boot: bool = False) -> bool:
        """
        Reconfigure a running cell (already booted, has auth_mask set).
        For first boot use boot_cell() instead.
        sync_wait/ctype accepted for backward compatibility, ignored.
        """
        if sync_wait:
            latch_in = True  # sync_wait → latch_in in v2.2

        cfg = build_config_word(
            topology=topology, edge_mode=edge_mode,
            latch_in=latch_in, latch_a_dis=latch_a_dis,
            latch_b_dis=latch_b_dis, dtype=dtype,
            priority=priority, trace=trace,
            breakpoint=breakpoint_flag,
            one_shot=one_shot, loop_back=loop_back)

        self._inject_raw(CMD_RECONFIGURE, cell_addr,
                         make_cmd(auth=self.auth_token, payload=cfg))
        time.sleep(0.001)

        if input_addr:
            self._inject_raw(CMD_SET_LOGICAL, cell_addr,
                             make_cmd(auth=self.auth_token,
                                      payload=input_addr & 0xFFFF))
            time.sleep(0.001)
        if output_addr:
            self._inject_raw(CMD_SET_OUTPUT_ADDR, cell_addr,
                             make_cmd(auth=self.auth_token,
                                      payload=output_addr & 0xFFFF))
            time.sleep(0.001)

        self.stats['configured'] += 1
        return True

    # ── Runtime commands ───────────────────────────────────────────────────────

    def inject(self, addr: int, data: int,
               mask: int = None) -> bool:
        """
        Write data to a bus address.
        mask — optional 8-bit nibble mask for partial word write.
        """
        self._inject_raw(CMD_DATA_WRITE, addr & 0xFFFF,
                         make_cmd(payload=data & 0xFFFFFFFF, mask=mask))
        return True

    def ping(self, cell_addr: int = 0):
        self._inject_raw(CMD_PING, cell_addr & 0xFFFF, 0)

    def freeze_cell(self, cell_addr: int):
        self._inject_raw(CMD_FREEZE, cell_addr,
                         make_cmd(auth=self.auth_token))

    def release_cell(self, cell_addr: int):
        self._inject_raw(CMD_RELEASE, cell_addr,
                         make_cmd(auth=self.auth_token))

    def latch_in_on(self, cell_addr: int):
        self._inject_raw(CMD_LATCH_IN_ON, cell_addr,
                         make_cmd(auth=self.auth_token))

    def latch_in_off(self, cell_addr: int):
        self._inject_raw(CMD_LATCH_IN_OFF, cell_addr,
                         make_cmd(auth=self.auth_token))

    def mem_call(self, cell_addr: int):
        self._inject_raw(CMD_MEM_CALL, cell_addr,
                         make_cmd(auth=self.auth_token))

    def rearm(self, cell_addr: int):
        self._inject_raw(CMD_REARM, cell_addr,
                         make_cmd(auth=self.auth_token))

    def configure_cell(self, cell_addr: int, gate_state: int,
                       input_addr: int, output_addr: int) -> bool:
        """
        Configure a cell from a gate_state word + addresses (ICM loader API).

        Decodes gate_state bits into reconfigure_cell() parameters:
          bits 0-9:    topology
          bit  10:     edge_mode
          bit  25:     latch_in   (GS_LATCH_IN)
          bits 23-24:  dtype
          bit  26:     posedge output (GS_OUT_POSEDGE)
          bit  28:     priority
          bit  29:     trace
          bit  30:     breakpoint
          bit  31:     one_shot   (GS_ONE_SHOT)
          bit  32:     loop_back  (GS_LOOP_BACK)
        """
        from gate_states import (TOPO_MASK, GS_EDGE_MODE, GS_LATCH_IN,
                                  GS_DTYPE_MASK, GS_DTYPE_SHIFT,
                                  GS_OUT_POSEDGE, GS_PRIORITY,
                                  GS_TRACE, GS_BREAKPOINT,
                                  GS_ONE_SHOT, GS_LOOP_BACK)
        topology   = gate_state & TOPO_MASK
        edge_mode  = bool(gate_state & GS_EDGE_MODE)
        latch_in   = bool(gate_state & GS_LATCH_IN)
        dtype      = (gate_state & GS_DTYPE_MASK) >> GS_DTYPE_SHIFT
        posedge    = bool(gate_state & GS_OUT_POSEDGE)
        priority   = bool(gate_state & GS_PRIORITY)
        trace      = bool(gate_state & GS_TRACE)
        brk        = bool(gate_state & GS_BREAKPOINT)
        one_shot   = bool(gate_state & GS_ONE_SHOT)
        loop_back  = bool(gate_state & GS_LOOP_BACK)
        return self.reconfigure_cell(
            cell_addr   = cell_addr,
            topology    = topology,
            input_addr  = input_addr,
            output_addr = output_addr,
            edge_mode   = edge_mode,
            latch_in    = latch_in,
            dtype       = dtype,
            priority    = priority,
            trace       = trace,
            breakpoint_flag = brk,
            one_shot    = one_shot,
            loop_back   = loop_back,
        )

    def preload_cell(self, cell_addr: int, a_data: int) -> None:
        """
        Preload a_data into a cell and set a_arrived=True.

        Implements the preloaded-A pattern on silicon:
        cell fires immediately on first B arrival (no send-twice needed).

        Protocol:
          1. CMD_PRELOAD   → loads a_data[23:0], sets a_arrived=1
          2. CMD_PRELOAD_HI → loads a_data[31:16] (only if upper bits non-zero)

        Common cases:
          a_data = 0           → single CMD_PRELOAD (cmd_data[23:0] = 0)
          a_data = 0x00FFFFFF  → single CMD_PRELOAD (cmd_data[23:0] = 0xFFFFFF)
          a_data = 0xFFFFFFFF  → CMD_PRELOAD(0xFFFFFF) + CMD_PRELOAD_HI(0xFFFF)
          a_data = 0x00000001  → single CMD_PRELOAD (cmd_data[23:0] = 1)

        Requires: cell must be frozen (CMD_FREEZE) before preloading.
        """
        v = int(a_data) & 0xFFFFFFFF
        lo24 = v & 0x00FFFFFF
        hi16 = (v >> 16) & 0xFFFF

        # CMD_PRELOAD: loads a_data[23:0], clears a_data[31:24], sets a_arrived
        self._inject_raw(CMD_PRELOAD, cell_addr,
                         make_cmd(auth=self.auth_token, payload=lo24))
        import time; time.sleep(0.005)

        # CMD_PRELOAD_HI: only needed if upper 16 bits are non-zero
        if hi16:
            self._inject_raw(CMD_PRELOAD_HI, cell_addr,
                             make_cmd(auth=self.auth_token, payload=hi16))
            time.sleep(0.005)



    def clear_arrived(self, cell_addr: int):
        """Clear a_arrived and a_data — reset input state only."""
        self._inject_raw(CMD_CLEAR_ARRIVED, cell_addr,
                         make_cmd(auth=self.auth_token))

    def reset_cell(self, cell_addr: int):
        """Clear all state and rearm — single command reset."""
        self._inject_raw(CMD_RESET_CELL, cell_addr,
                         make_cmd(auth=self.auth_token))

    def swap_ab(self, cell_addr: int, new_a: int = 0):
        """Load a_data from 13-bit payload, set a_arrived."""
        self._inject_raw(CMD_SWAP_AB, cell_addr,
                         make_cmd(auth=self.auth_token,
                                  payload=new_a & 0x1FFF))

    def set_topology(self, cell_addr: int, topology: int):
        """Write topology bits only — no other flags changed."""
        self._inject_raw(CMD_SET_TOPO, cell_addr,
                         make_cmd(auth=self.auth_token,
                                  payload=topology & 0x3FF))

    def toggle_invert(self, cell_addr: int):
        """Toggle invert_out flag."""
        self._inject_raw(CMD_SET_INVERT, cell_addr,
                         make_cmd(auth=self.auth_token))

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
                 base_address: int = 0x1000) -> bool:
        print(f"[FPGA] Loading {len(cell_map)} cells from {hex(base_address)}")
        for i, rec in enumerate(cell_map):
            caddr = base_address + i
            if hasattr(rec, 'gate_state'):
                gs   = rec.gate_state
                topo = gs & 0x3FF
                ia, oa = rec.input_address, rec.output_address
            elif isinstance(rec, (list, tuple)) and len(rec) >= 3:
                topo, ia, oa = rec[0] & 0x3FF, rec[1], rec[2]
            else:
                print(f"[FPGA] Unknown record at {i}"); continue

            self.boot_cell(cell_id=caddr, topology=topo,
                           input_addr=ia, output_addr=oa)
            if i % 10 == 0:
                print(f"[FPGA] {i+1}/{len(cell_map)}...", end='\r')

        print(f"[FPGA] Done — {len(cell_map)} cells")
        return True


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Imago UniCell FPGA Bridge v2.2")
    p.add_argument("--port",  required=True)
    p.add_argument("--baud",  type=int, default=115200)
    p.add_argument("--auth",  type=lambda x: int(x, 0), default=0,
                   help="8-bit auth token e.g. 0xA5")
    p.add_argument("--reset", action="store_true")
    p.add_argument("--status", action="store_true")
    args = p.parse_args()

    bridge = FPGABridge(port=args.port, baud=args.baud,
                        auth_token=args.auth)
    if not bridge.connect(): sys.exit(1)
    if args.reset: bridge.reset()
    if args.status:
        s = bridge.get_status()
        if s:
            print(f"[FPGA] armed={s['armed']} cycles={s['cycles']}")

    bridge.disconnect()


if __name__ == "__main__":
    main()
