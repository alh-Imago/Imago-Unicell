"""
fpga_bridge.py — Python Host Bridge for UniCell FPGA
Protocol v2.3 — unified 32-bit command bus, boot/run states, preload_sel, shift_sel

Ground truth: fpga/verilog/unicell.v v2.3

UART packet format (v2.3 — 9 bytes):
  [0]    0x01 UART_INJECT
  [1:4]  cmd_bus  (32-bit unified command word)
  [5:8]  cmd_data (32-bit payload)

  NOTE: uart_bridge.v must be updated to v2.3 to accept this format.
  For iCEBreaker bring-up with existing v2.2 Verilog, use _inject_raw_v22()
  which sends the old 8-byte format (opcode + addr16 + data32).
  Switch to _inject_raw() once uart_bridge.v is updated.

UART packet format (v2.2 legacy — 8 bytes, current iCEBreaker):
  [0]    0x01 UART_INJECT
  [1]    opcode (8-bit)
  [2:3]  cmd_addr (16-bit, physical ID or logical address)
  [4:7]  cmd_data (32-bit, auth[31:24]+payload[23:0])

Fired response (7 bytes — unchanged):
  [0]    0x10
  [1:2]  out_addr (16-bit)
  [3:6]  out_data (32-bit)

Status response (7 bytes — unchanged):
  [0]    0x11
  [1:2]  armed_count (16-bit)
  [3:6]  cycle_count (32-bit)

cmd_bus word layout (v2.3):
  bits  7:0   opcode        8-bit command code
  bit   8     gate_enable   0=broadcast, 1=filter by gate_set
  bits 16:9   gate_set      8-bit group tag
  bits 18:17  preload_sel   00=none 01=load 0x00000000 10=load 0xFFFFFFFF
  bits 20:19  shift_sel     bit19=shift_in_en  bit20=shift_out_en
  bits 28:21  auth_token    8-bit token
  bits 31:29  spare

Boot sequence (v2.3 — 2 transactions):
  1. CMD_BOOT_COMMIT: cmd_data[15:0]=logical_addr [23:16]=auth_mask [31:24]=group_tag
  2. CMD_RECONFIGURE: cmd_data = full cmd_latch word

Boot sequence (v2.2 legacy — 4 transactions, for current iCEBreaker):
  1. CMD_RECONFIGURE  — topology + flags + auth_mask in cmd_data[31:24]
  2. CMD_SET_LOGICAL  — logical input address
  3. CMD_SET_OUTPUT_ADDR — output address
  4. CMD_RELEASE      — arm cell

Retired from v2.2:
  make_cmd(auth, payload, mask, latch_a, latch_b) — auth was in cmd_data[31:24]
  CMD_PRELOAD + CMD_PRELOAD_HI two-step — use preload_sel bits in cmd_bus
  cell_id targeting in cmd_bus — replaced by gate_set filtering
"""

import struct
import time
import threading
import queue
import sys
import argparse
from typing import Optional, Callable

try:
    import serial
    _SERIAL_AVAILABLE = True
except ImportError:
    _SERIAL_AVAILABLE = False

# ── Command codes (match fpga/verilog/unicell.v v2.3 localparam exactly) ──────

CMD_NOP             = 0x00
CMD_DATA_WRITE      = 0x01
CMD_SET_INPUT_ADDR  = 0x02
CMD_SET_OUTPUT_ADDR = 0x03
CMD_RECONFIGURE     = 0x04
CMD_FREEZE          = 0x05
CMD_RELEASE         = 0x06
CMD_BOOT_COMMIT     = 0x07   # BOOT STATE ONLY: addr+auth+group → RUN state
CMD_PING            = 0x09
CMD_LATCH_IN_ON     = 0x0A
CMD_LATCH_IN_OFF    = 0x0B
CMD_MEM_CALL        = 0x0C
CMD_REARM           = 0x0D
CMD_SET_LOGICAL     = 0x0E   # legacy — use CMD_BOOT_COMMIT for new code
CMD_PRELOAD         = 0x0F   # DEPRECATED — use preload_sel bits in cmd_bus
CMD_CLEAR_ARRIVED   = 0x10
CMD_RESET_CELL      = 0x11
CMD_SWAP_AB         = 0x12
CMD_CAPTURE_REARM   = 0x13
CMD_SET_TOPO        = 0x14
CMD_SET_INVERT      = 0x15
CMD_PRELOAD_HI      = 0x16   # DEPRECATED — use preload_sel bits in cmd_bus

# Topology preset opcodes (cold=even, armed=odd)
CMD_TOPO_PASS_A_COLD = 0x30;  CMD_TOPO_PASS_A = 0x31
CMD_TOPO_NOT_A_COLD  = 0x32;  CMD_TOPO_NOT_A  = 0x33
CMD_TOPO_NOR_COLD    = 0x34;  CMD_TOPO_NOR    = 0x35
CMD_TOPO_AND_COLD    = 0x36;  CMD_TOPO_AND    = 0x37
CMD_TOPO_OR_COLD     = 0x38;  CMD_TOPO_OR     = 0x39
CMD_TOPO_NAND_COLD   = 0x3A;  CMD_TOPO_NAND   = 0x3B
CMD_TOPO_PASS_B_COLD = 0x3C;  CMD_TOPO_PASS_B = 0x3D
CMD_TOPO_XNOR_COLD   = 0x3E;  CMD_TOPO_XNOR   = 0x3F
CMD_TOPO_XOR_COLD    = 0x40;  CMD_TOPO_XOR    = 0x41
CMD_TOPO_ZERO_COLD   = 0x42;  CMD_TOPO_ZERO   = 0x43
CMD_TOPO_ONE_COLD    = 0x44;  CMD_TOPO_ONE    = 0x45

# Topology hex values (for CMD_RECONFIGURE cmd_data / configure_cell)
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

# ── UART protocol bytes ────────────────────────────────────────────────────────

UART_INJECT  = 0x01   # host→FPGA: send command (9 bytes v2.3, 8 bytes v2.2)
UART_RESET   = 0x03   # host→FPGA: assert array_rst one cycle
UART_STATUS  = 0x04   # host→FPGA: request status response
UART_FREEZE  = 0x06   # host→FPGA: array-wide freeze (bus inactive)
UART_RELEASE = 0x07   # host→FPGA: array-wide release (bus live)

RSP_FIRED    = 0x10   # FPGA→host: cell fired (addr16 + data32)
RSP_STATUS   = 0x11   # FPGA→host: status (armed16 + cycles32)
RSP_ERROR    = 0xFF   # FPGA→host: error

# ── Data types (dtype field in cmd_latch[24:23]) ───────────────────────────────

DTYPE_NUMERIC  = 0b00
DTYPE_SIGNED   = 0b01
DTYPE_ALPHA    = 0b10
DTYPE_DATETIME = 0b11

# ── Preload select values (preload_sel field in cmd_bus[18:17]) ───────────────

PRELOAD_NONE  = 0b00   # no preload
PRELOAD_ZERO  = 0b01   # load 0x00000000 (AND false side, NOR constant)
PRELOAD_ONES  = 0b10   # load 0xFFFFFFFF (NOT/XOR/XNOR constant)

# ── cmd_bus v2.3 builder ───────────────────────────────────────────────────────

def build_cmd_bus(opcode:       int,
                  auth:         int  = 0,
                  gate_enable:  bool = False,
                  gate_set:     int  = 0,
                  preload_sel:  int  = PRELOAD_NONE,
                  shift_in_en:  bool = False,
                  shift_out_en: bool = False) -> int:
    """
    Build a v2.3 cmd_bus word (32-bit).

    opcode:      8-bit command code (CMD_* constant)
    auth:        8-bit auth token (cmd_bus[28:21])
    gate_enable: True = filter by gate_set; False = broadcast
    gate_set:    8-bit group tag (cmd_bus[16:9])
    preload_sel: PRELOAD_NONE/ZERO/ONES (cmd_bus[18:17])
    shift_in_en: left-shift bus_data before gate tree (cmd_bus[19])
    shift_out_en:right-shift output before emit (cmd_bus[20])

    Shift amount carried separately in cmd_data[3:0] (nibble count 0-7).
    """
    w  =  (opcode      & 0xFF)
    w |=  (0x100        if gate_enable  else 0)      # bit 8
    w |=  ((gate_set    & 0xFF)   << 9)              # bits 16:9
    w |=  ((preload_sel & 0x3)    << 17)             # bits 18:17
    w |=  (0x80000      if shift_in_en  else 0)      # bit 19
    w |=  (0x100000     if shift_out_en else 0)      # bit 20
    w |=  ((auth        & 0xFF)   << 21)             # bits 28:21
    return w


def build_cmd_data_reconfigure(topology:    int  = TOPO_PASS_A,
                                edge_mode:   bool = False,
                                latch_a_dis: bool = False,
                                latch_b_dis: bool = False,
                                dtype:       int  = DTYPE_NUMERIC,
                                invert_out:  bool = False,
                                latch_in:    bool = False,
                                priority:    bool = False,
                                trace:       bool = False,
                                breakpoint:  bool = False,
                                one_shot:    bool = False,
                                loop_back:   bool = False,
                                auth_mask:   int  = 0) -> int:
    """
    Build 32-bit cmd_data payload for CMD_RECONFIGURE.

    Maps to cmd_latch via unicell.v v2.3 CMD_RECONFIGURE decode:
      cmd_data[9:0]   → topology
      cmd_data[10]    → edge_mode
      cmd_data[11]    → start_flag (always 1 — arm on configure)
      cmd_data[12]    → latch_A_dis
      cmd_data[13]    → latch_B_dis
      cmd_data[15:14] → dtype
      cmd_data[16]    → invert_out
      cmd_data[17]    → latch_in
      cmd_data[18]    → priority
      cmd_data[19]    → trace
      cmd_data[20]    → breakpoint
      cmd_data[21]    → one_shot
      cmd_data[22]    → loop_back
      cmd_data[30:23] → auth_mask (stored in cmd_latch[18:11])

    NOTE: auth_mask is now in cmd_data[30:23], NOT cmd_data[31:24] as in v2.2.
    The auth_token for the transaction itself is in cmd_bus[28:21].
    """
    w  = (topology     & 0x3FF)
    w |= (1 if edge_mode    else 0) << 10
    w |= 1                          << 11   # start_flag always set on RECONFIGURE
    w |= (1 if latch_a_dis  else 0) << 12
    w |= (1 if latch_b_dis  else 0) << 13
    w |= (dtype         & 0x3)      << 14
    w |= (1 if invert_out   else 0) << 16
    w |= (1 if latch_in     else 0) << 17
    w |= (1 if priority     else 0) << 18
    w |= (1 if trace        else 0) << 19
    w |= (1 if breakpoint   else 0) << 20
    w |= (1 if one_shot     else 0) << 21
    w |= (1 if loop_back    else 0) << 22
    w |= (auth_mask     & 0xFF)     << 23   # cmd_data[30:23] → cmd_latch[18:11]
    return w


# ── Legacy v2.2 helpers (for current iCEBreaker Verilog) ──────────────────────

def _make_cmd_v22(auth:    int  = 0,
                  payload: int  = 0,
                  mask:    int  = None,
                  latch_a: bool = False,
                  latch_b: bool = False) -> int:
    """
    Build 32-bit cmd_data word for v2.2 UART protocol.
    auth in [31:24], payload in [12:0].
    Used by _inject_raw_v22() for current iCEBreaker bring-up.
    """
    word  = payload & 0x1FFF
    word |= (1 if latch_a else 0) << 13
    word |= (1 if latch_b else 0) << 14
    if mask is not None:
        word |= (mask & 0xFF) << 15
        word |= 1 << 23
    word |= (auth & 0xFF) << 24
    return word


def _build_config_word_v22(topology:    int  = 0,
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
    Build 23-bit config payload for v2.2 CMD_RECONFIGURE (bits [22:0] of cmd_data).
    auth_mask was in cmd_data[31:24] in v2.2 — passed separately via make_cmd().
    Kept for iCEBreaker bring-up with existing Verilog.
    """
    w  = (topology    & 0x3FF)
    w |= (1 if edge_mode    else 0) << 10
    w |= 1                          << 11
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
    """
    Host bridge to UniCell FPGA array via UART.

    Protocol mode:
      v2.3 (default):  9-byte packets: UART_INJECT + cmd_bus(4) + cmd_data(4)
                        Requires uart_bridge.v updated to v2.3.
      v2.2 (legacy):   8-byte packets: UART_INJECT + opcode(1) + addr(2) + data(4)
                        For current iCEBreaker bring-up with existing Verilog.

    Set protocol_v22=True to use legacy format during iCEBreaker bring-up.
    Switch to default (v2.3) once uart_bridge.v is updated.
    """

    def __init__(self, port: str, baud: int = 115200,
                 timeout: float = 2.0, auth_token: int = 0,
                 protocol_v22: bool = True):
        """
        protocol_v22: True = use v2.2 legacy 8-byte packets (current iCEBreaker)
                      False = use v2.3 9-byte packets (after uart_bridge.v update)
        """
        self.port         = port
        self.baud         = baud
        self.timeout      = timeout
        self.auth_token   = auth_token & 0xFF
        self.protocol_v22 = protocol_v22
        self._ser         = None
        self._rx_queue    = queue.Queue()
        self._rx_thread   = None
        self._running     = False
        self._lock        = threading.Lock()
        self._fire_cbs    = []
        self.stats        = {'injected':0,'configured':0,'fired':0,'errors':0}

    # ── Connection ─────────────────────────────────────────────────────────────

    def connect(self) -> bool:
        if not _SERIAL_AVAILABLE:
            print("[FPGA] pyserial not available")
            return False
        try:
            self._ser = serial.Serial(
                port=self.port, baudrate=self.baud,
                bytesize=8, parity='N', stopbits=1, timeout=self.timeout)
            self._running = True
            self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
            self._rx_thread.start()
            time.sleep(0.1)
            status = self.get_status()
            if status is None:
                print(f"[FPGA] No response from {self.port}")
                return False
            proto = "v2.2-legacy" if self.protocol_v22 else "v2.3"
            print(f"[FPGA] Connected {self.port} @ {self.baud} protocol={proto}")
            print(f"[FPGA] Cycles: {status['cycles']}")
            return True
        except Exception as e:
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
                if self._running:
                    print(f"[FPGA] RX: {e}")

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

    # ── Low-level TX ───────────────────────────────────────────────────────────

    def _send(self, data: bytes):
        with self._lock:
            if self._ser and self._ser.is_open:
                self._ser.write(data)

    def _inject_raw(self, opcode: int, cmd_data: int,
                    auth:         int  = None,
                    gate_enable:  bool = False,
                    gate_set:     int  = 0,
                    preload_sel:  int  = PRELOAD_NONE,
                    shift_in_en:  bool = False,
                    shift_out_en: bool = False):
        """
        Send a command frame using v2.3 9-byte format:
          UART_INJECT(1) + cmd_bus(4) + cmd_data(4)

        opcode:   command code (CMD_* constant)
        cmd_data: 32-bit payload
        auth:     auth token (default: self.auth_token)

        Use this once uart_bridge.v is updated to v2.3.
        """
        if auth is None:
            auth = self.auth_token
        cmd_bus = build_cmd_bus(opcode, auth=auth, gate_enable=gate_enable,
                                gate_set=gate_set, preload_sel=preload_sel,
                                shift_in_en=shift_in_en, shift_out_en=shift_out_en)
        pkt = struct.pack('>BII', UART_INJECT,
                          cmd_bus  & 0xFFFFFFFF,
                          cmd_data & 0xFFFFFFFF)
        self._send(pkt)
        self.stats['injected'] += 1

    def _inject_raw_v22(self, opcode: int, cmd_addr: int, cmd_data: int):
        """
        Send a command frame using v2.2 legacy 8-byte format:
          UART_INJECT(1) + opcode(1) + addr(2) + data(4)

        Used for current iCEBreaker bring-up with existing uart_bridge.v.
        Switch to _inject_raw() once uart_bridge.v is updated to v2.3.
        """
        pkt = struct.pack('>BBHI', UART_INJECT,
                          opcode   & 0xFF,
                          cmd_addr & 0xFFFF,
                          cmd_data & 0xFFFFFFFF)
        self._send(pkt)
        self.stats['injected'] += 1

    def _tx(self, opcode: int, cmd_data: int,
            cell_addr:   int  = 0,
            auth:        int  = None,
            preload_sel: int  = PRELOAD_NONE,
            shift_in_en: bool = False,
            shift_out_en:bool = False):
        """
        Dispatch to correct packet format based on self.protocol_v22.
        Central send point — all higher-level methods call this.
        """
        if self.protocol_v22:
            self._inject_raw_v22(opcode, cell_addr, cmd_data)
        else:
            self._inject_raw(opcode, cmd_data, auth=auth,
                             preload_sel=preload_sel,
                             shift_in_en=shift_in_en,
                             shift_out_en=shift_out_en)

    # ── Cell boot sequence ─────────────────────────────────────────────────────

    def boot_cell(self, cell_id:     int,
                        topology:    int  = TOPO_PASS_A,
                        input_addr:  int  = 0,
                        output_addr: int  = 0,
                        auth:        int  = None,
                        group_tag:   int  = 0,
                        edge_mode:   bool = False,
                        latch_in:    bool = False,
                        latch_a_dis: bool = False,
                        latch_b_dis: bool = False,
                        one_shot:    bool = False,
                        loop_back:   bool = False,
                        dtype:       int  = DTYPE_NUMERIC) -> None:
        """
        Full cell boot sequence.

        v2.3 mode (protocol_v22=False) — 2 transactions:
          1. CMD_BOOT_COMMIT: logical addr + auth_mask + group_tag → RUN state
          2. CMD_RECONFIGURE: topology + flags

        v2.2 mode (protocol_v22=True, current iCEBreaker) — 4 transactions:
          1. CMD_RECONFIGURE  — topology + flags + auth_mask in cmd_data[31:24]
          2. CMD_SET_LOGICAL  — logical input address
          3. CMD_SET_OUTPUT_ADDR — output address
          4. CMD_RELEASE      — arm cell

        cell_id: physical CELL_ID (Verilog parameter) — only used in BOOT state
        auth:    auth token (default: self.auth_token)
        """
        if auth is None:
            auth = self.auth_token

        if self.protocol_v22:
            # ── v2.2 legacy sequence (current iCEBreaker) ────────────────────
            cfg = _build_config_word_v22(
                topology=topology, edge_mode=edge_mode,
                latch_in=latch_in, latch_a_dis=latch_a_dis,
                latch_b_dis=latch_b_dis, dtype=dtype,
                one_shot=one_shot, loop_back=loop_back)

            self._inject_raw_v22(CMD_RECONFIGURE, cell_id,
                                 _make_cmd_v22(auth=auth, payload=cfg))
            time.sleep(0.001)
            self._inject_raw_v22(CMD_SET_LOGICAL, cell_id,
                                 _make_cmd_v22(auth=auth, payload=input_addr & 0xFFFF))
            time.sleep(0.001)
            self._inject_raw_v22(CMD_SET_OUTPUT_ADDR, cell_id,
                                 _make_cmd_v22(auth=auth, payload=output_addr & 0xFFFF))
            time.sleep(0.001)
            self._inject_raw_v22(CMD_RELEASE, cell_id,
                                 _make_cmd_v22(auth=auth))
            time.sleep(0.001)
        else:
            # ── v2.3 sequence — CMD_BOOT_COMMIT + CMD_RECONFIGURE ────────────
            # 1. BOOT_COMMIT: set logical addr + auth_mask + group_tag
            boot_data = ((input_addr & 0xFFFF)        |
                         ((auth      & 0xFF)   << 16) |
                         ((group_tag & 0xFF)   << 24))
            self._inject_raw(CMD_BOOT_COMMIT, boot_data, auth=0)  # no auth yet
            time.sleep(0.001)

            # 2. RECONFIGURE: topology + flags (auth now set, required)
            cfg = build_cmd_data_reconfigure(
                topology=topology, edge_mode=edge_mode,
                latch_in=latch_in, latch_a_dis=latch_a_dis,
                latch_b_dis=latch_b_dis, dtype=dtype,
                one_shot=one_shot, loop_back=loop_back,
                auth_mask=auth)
            self._inject_raw(CMD_RECONFIGURE, cfg, auth=auth)
            time.sleep(0.001)

            # Set output address
            self._inject_raw(CMD_SET_OUTPUT_ADDR, output_addr & 0xFFFF, auth=auth)
            time.sleep(0.001)

        self.stats['configured'] += 1

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
                               sync_wait:   bool = False) -> bool:
        """
        Reconfigure a running cell (already booted, auth_mask set).
        sync_wait accepted for backward compatibility — maps to latch_in.
        """
        if sync_wait:
            latch_in = True

        if self.protocol_v22:
            cfg = _build_config_word_v22(
                topology=topology, edge_mode=edge_mode,
                latch_in=latch_in, latch_a_dis=latch_a_dis,
                latch_b_dis=latch_b_dis, dtype=dtype,
                priority=priority, trace=trace,
                breakpoint=breakpoint_flag,
                one_shot=one_shot, loop_back=loop_back)
            self._inject_raw_v22(CMD_RECONFIGURE, cell_addr,
                                 _make_cmd_v22(auth=self.auth_token, payload=cfg))
            time.sleep(0.001)
            if input_addr:
                self._inject_raw_v22(CMD_SET_LOGICAL, cell_addr,
                                     _make_cmd_v22(auth=self.auth_token,
                                                   payload=input_addr & 0xFFFF))
                time.sleep(0.001)
            if output_addr:
                self._inject_raw_v22(CMD_SET_OUTPUT_ADDR, cell_addr,
                                     _make_cmd_v22(auth=self.auth_token,
                                                   payload=output_addr & 0xFFFF))
                time.sleep(0.001)
        else:
            cfg = build_cmd_data_reconfigure(
                topology=topology, edge_mode=edge_mode,
                latch_in=latch_in, latch_a_dis=latch_a_dis,
                latch_b_dis=latch_b_dis, dtype=dtype,
                priority=priority, trace=trace,
                breakpoint=breakpoint_flag,
                one_shot=one_shot, loop_back=loop_back)
            self._inject_raw(CMD_RECONFIGURE, cfg, auth=self.auth_token)
            time.sleep(0.001)
            if input_addr:
                self._inject_raw(CMD_SET_INPUT_ADDR, input_addr & 0xFFFF,
                                 auth=self.auth_token)
                time.sleep(0.001)
            if output_addr:
                self._inject_raw(CMD_SET_OUTPUT_ADDR, output_addr & 0xFFFF,
                                 auth=self.auth_token)
                time.sleep(0.001)

        self.stats['configured'] += 1
        return True

    def configure_cell(self, cell_addr: int, gate_state: int,
                       input_addr: int, output_addr: int) -> bool:
        """
        Configure a cell from a gate_state word + addresses (ICM loader API).
        Decodes cmd_latch bits (v2.3 layout) into reconfigure_cell() parameters.

        cmd_latch bit positions (v2.3, from gate_states.py):
          bits 9:0   topology
          bit  10    edge_mode
          bit  25    invert_out   (separate from latch_in — v2.3 correction)
          bit  26    latch_in     (was incorrectly merged with invert_out in v2.2)
          bits 24:23 dtype
          bit  27    priority
          bit  28    trace
          bit  29    breakpoint
          bit  30    one_shot
          bit  31    loop_back
        """
        from gate_states import (TOPO_MASK, GS_EDGE_MODE, GS_LATCH_IN,
                                  GS_INVERT_OUT_BIT, GS_DTYPE_MASK, GS_DTYPE_SHIFT,
                                  GS_PRIORITY, GS_TRACE, GS_BREAKPOINT,
                                  GS_ONE_SHOT, GS_LOOP_BACK)
        topology   = gate_state & TOPO_MASK
        edge_mode  = bool(gate_state & GS_EDGE_MODE)
        latch_in   = bool(gate_state & GS_LATCH_IN)        # bit 26
        invert_out = bool(gate_state & GS_INVERT_OUT_BIT)  # bit 25 (separate)
        dtype      = (gate_state & GS_DTYPE_MASK) >> GS_DTYPE_SHIFT
        priority   = bool(gate_state & GS_PRIORITY)
        trace      = bool(gate_state & GS_TRACE)
        brk        = bool(gate_state & GS_BREAKPOINT)
        one_shot   = bool(gate_state & GS_ONE_SHOT)
        loop_back  = bool(gate_state & GS_LOOP_BACK)
        return self.reconfigure_cell(
            cell_addr       = cell_addr,
            topology        = topology,
            input_addr      = input_addr,
            output_addr     = output_addr,
            edge_mode       = edge_mode,
            latch_in        = latch_in,
            dtype           = dtype,
            priority        = priority,
            trace           = trace,
            breakpoint_flag = brk,
            one_shot        = one_shot,
            loop_back       = loop_back,
        )

    # ── Runtime commands ───────────────────────────────────────────────────────

    def inject(self, addr: int, data: int) -> bool:
        """Write data to a bus address (data bus, not command bus)."""
        self._tx(CMD_DATA_WRITE, data & 0xFFFFFFFF, cell_addr=addr & 0xFFFF)
        return True

    def preload_cell(self, cell_addr: int, a_data: int) -> None:
        """
        Preload a_data into a cell and set a_arrived=True.
        Implements the preloaded-A pattern — cell fires on first B arrival.

        v2.3 mode: uses preload_sel bits in cmd_bus.
          0x00000000 → CMD_NOP with preload_sel=PRELOAD_ZERO  (1 transaction)
          0xFFFFFFFF → CMD_NOP with preload_sel=PRELOAD_ONES  (1 transaction)
          other      → CMD_RECONFIGURE with arbitrary value in cmd_data
                       (VM/Python-side only, not supported in v2.3 silicon for
                        arbitrary values — use 0 or 0xFFFFFFFF on hardware)

        v2.2 mode (legacy): CMD_PRELOAD + optional CMD_PRELOAD_HI (2 transactions).
        Cell must be frozen (CMD_FREEZE) before preloading in both modes.
        """
        v = int(a_data) & 0xFFFFFFFF

        if self.protocol_v22:
            # v2.2: two-step CMD_PRELOAD + CMD_PRELOAD_HI
            lo24 = v & 0x00FFFFFF
            hi16 = (v >> 16) & 0xFFFF
            self._inject_raw_v22(CMD_PRELOAD, cell_addr,
                                 _make_cmd_v22(auth=self.auth_token, payload=lo24))
            time.sleep(0.005)
            if hi16:
                self._inject_raw_v22(CMD_PRELOAD_HI, cell_addr,
                                     _make_cmd_v22(auth=self.auth_token, payload=hi16))
                time.sleep(0.005)
        else:
            # v2.3: single preload_sel bit — only 0x00000000 and 0xFFFFFFFF supported
            if v == 0xFFFFFFFF:
                self._inject_raw(CMD_NOP, 0, auth=self.auth_token,
                                 preload_sel=PRELOAD_ONES)
            elif v == 0x00000000:
                self._inject_raw(CMD_NOP, 0, auth=self.auth_token,
                                 preload_sel=PRELOAD_ZERO)
            else:
                raise ValueError(
                    f"preload_cell: v2.3 silicon only supports 0x00000000 or "
                    f"0xFFFFFFFF via preload_sel. Got {v:#010x}. "
                    f"Use protocol_v22=True for arbitrary values (iCEBreaker).")

    def ping(self, cell_addr: int = 0):
        """CMD_PING — check if cell is alive."""
        self._tx(CMD_PING, 0, cell_addr=cell_addr & 0xFFFF)

    def freeze_cell(self, cell_addr: int):
        """CMD_FREEZE — disarm cell."""
        self._tx(CMD_FREEZE, 0, cell_addr=cell_addr, auth=self.auth_token)

    def release_cell(self, cell_addr: int):
        """CMD_RELEASE — re-arm cell."""
        self._tx(CMD_RELEASE, 0, cell_addr=cell_addr, auth=self.auth_token)

    def latch_in_on(self, cell_addr: int):
        self._tx(CMD_LATCH_IN_ON, 0, cell_addr=cell_addr, auth=self.auth_token)

    def latch_in_off(self, cell_addr: int):
        self._tx(CMD_LATCH_IN_OFF, 0, cell_addr=cell_addr, auth=self.auth_token)

    def mem_call(self, cell_addr: int):
        self._tx(CMD_MEM_CALL, 0, cell_addr=cell_addr, auth=self.auth_token)

    def rearm(self, cell_addr: int):
        self._tx(CMD_REARM, 0, cell_addr=cell_addr, auth=self.auth_token)

    def clear_arrived(self, cell_addr: int):
        """Clear a_arrived and a_data — reset input state only."""
        self._tx(CMD_CLEAR_ARRIVED, 0, cell_addr=cell_addr, auth=self.auth_token)

    def reset_cell(self, cell_addr: int):
        """Clear all state and rearm."""
        self._tx(CMD_RESET_CELL, 0, cell_addr=cell_addr, auth=self.auth_token)

    def swap_ab(self, cell_addr: int, new_a: int = 0):
        """Load a_data from 13-bit payload, set a_arrived."""
        if self.protocol_v22:
            self._inject_raw_v22(CMD_SWAP_AB, cell_addr,
                                 _make_cmd_v22(auth=self.auth_token,
                                               payload=new_a & 0x1FFF))
        else:
            self._inject_raw(CMD_SWAP_AB, new_a & 0x1FFF, auth=self.auth_token)

    def set_topology(self, cell_addr: int, topology: int):
        """Write topology bits only — no other flags changed."""
        if self.protocol_v22:
            self._inject_raw_v22(CMD_SET_TOPO, cell_addr,
                                 _make_cmd_v22(auth=self.auth_token,
                                               payload=topology & 0x3FF))
        else:
            self._inject_raw(CMD_SET_TOPO, topology & 0x3FF, auth=self.auth_token)

    def reset(self):
        """Assert array_rst for one cycle."""
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
                if rsp[0] == 'fired':
                    return (rsp[1], rsp[2])
            except queue.Empty:
                pass
        return None

    def on_fire(self, cb: Callable):
        """Register a callback for fired events: cb(addr, data)."""
        self._fire_cbs.append(cb)

    def load_map(self, cell_map: list, base_address: int = 0x1000) -> bool:
        """Load a list of CellMapRecord / (topo, in_addr, out_addr) tuples."""
        print(f"[FPGA] Loading {len(cell_map)} cells from {hex(base_address)}")
        for i, rec in enumerate(cell_map):
            caddr = base_address + i
            if hasattr(rec, 'gate_state'):
                self.configure_cell(caddr, rec.gate_state,
                                    rec.input_address, rec.output_address)
            elif isinstance(rec, (list, tuple)) and len(rec) >= 3:
                topo, ia, oa = rec[0] & 0x3FF, rec[1], rec[2]
                self.boot_cell(cell_id=caddr, topology=topo,
                               input_addr=ia, output_addr=oa)
            else:
                print(f"[FPGA] Unknown record at {i}")
                continue
            if i % 10 == 0:
                print(f"[FPGA] {i+1}/{len(cell_map)}...", end='\r')
        print(f"[FPGA] Done — {len(cell_map)} cells")
        return True


# ── Backward-compatibility shims ──────────────────────────────────────────────
# v2.2 callers used make_cmd() and build_config_word() at module level.
# Redirect to the v2.2 legacy helpers.

def make_cmd(auth: int = 0, payload: int = 0, mask: int = None,
             latch_a: bool = False, latch_b: bool = False) -> int:
    """Backward compat: v2.2 cmd_data builder. New code: use build_cmd_bus()."""
    return _make_cmd_v22(auth=auth, payload=payload, mask=mask,
                         latch_a=latch_a, latch_b=latch_b)

def build_config_word(topology: int = 0, edge_mode: bool = False,
                      dtype: int = DTYPE_NUMERIC, invert_out: bool = False,
                      latch_in: bool = False, latch_a_dis: bool = False,
                      latch_b_dis: bool = False, priority: bool = False,
                      trace: bool = False, breakpoint: bool = False,
                      one_shot: bool = False, loop_back: bool = False) -> int:
    """Backward compat: v2.2 config word builder. New code: use build_cmd_data_reconfigure()."""
    return _build_config_word_v22(
        topology=topology, edge_mode=edge_mode, dtype=dtype,
        latch_in=latch_in, latch_a_dis=latch_a_dis, latch_b_dis=latch_b_dis,
        priority=priority, trace=trace, breakpoint=breakpoint,
        one_shot=one_shot, loop_back=loop_back)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Imago UniCell FPGA Bridge v2.3")
    p.add_argument("--port",   required=True)
    p.add_argument("--baud",   type=int, default=115200)
    p.add_argument("--auth",   type=lambda x: int(x, 0), default=0,
                   help="8-bit auth token e.g. 0xA5")
    p.add_argument("--v23",    action="store_true",
                   help="Use v2.3 protocol (default: v2.2 legacy for iCEBreaker)")
    p.add_argument("--reset",  action="store_true")
    p.add_argument("--status", action="store_true")
    args = p.parse_args()

    bridge = FPGABridge(port=args.port, baud=args.baud,
                        auth_token=args.auth,
                        protocol_v22=not args.v23)
    if not bridge.connect():
        sys.exit(1)
    if args.reset:
        bridge.reset()
    if args.status:
        s = bridge.get_status()
        if s:
            print(f"[FPGA] armed={s['armed']} cycles={s['cycles']}")
    bridge.disconnect()


if __name__ == "__main__":
    main()
