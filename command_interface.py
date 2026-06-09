"""
command_interface.py — Command bus interface.

Ground truth: fpga/verilog/unicell.v Protocol v2.3. Last updated 2026-05-30.

TWO STATES — BOOT and RUN:
  BOOT: cell exposes baked-in CELL_ID. Boot controller sends CMD_BOOT_COMMIT
        with logical address, auth_mask, and group_tag in one transaction.
        Cell stores all three and flips to RUN state permanently.
  RUN:  cell responds to logical input_address only. All commands require
        auth_token match against stored auth_mask.

cmd_bus word layout (v2.3 — 32-bit unified word):
  bits  7:0   opcode        8-bit command code (256 opcodes)
  bit   8     gate_enable   0=broadcast to all cells, 1=filter by gate_set
  bits 16:9   gate_set      8-bit group tag (matches cell's stored group_tag)
  bits 18:17  preload_sel   transient preload constant into a_data/a_arrived:
                            00=none, 01=0x00000000, 10=0xFFFFFFFF, 11=reserved
  bits 20:19  shift_sel     transient per-transaction shift modifier:
                            bit19=shift_in_en, bit20=shift_out_en
                            shift amount in cmd_data[3:0] (nibble count 0-7)
  bits 28:21  auth_token    8-bit token matched against cell's stored auth_mask
  bits 31:29  spare         reserved, must be zero

cmd_data [31:0] — payload meaning depends on opcode:
  CMD_BOOT_COMMIT:      [15:0]=logical_addr  [23:16]=auth_mask  [31:24]=group_tag
  CMD_SET_INPUT_ADDR:   [15:0]=address
  CMD_SET_OUTPUT_ADDR:  [15:0]=address
  CMD_RECONFIGURE:      [31:0]=full cmd_latch word (auth_mask in [30:23])
  shift ops:            [3:0]=nibble shift count

NOTE: build_cmd_bus() / decode_cmd_bus() produce the wire format for the FPGA
      bridge. The CommandInterface class itself operates on cell objects directly
      (VM path) and does not use raw cmd_bus words internally.

Retired from previous version (v2.2 layout — do not use):
  _CODE_MASK=0xF (4-bit codes)
  _AUTH_SHIFT=4, _AUTH_MASK=0x7FF (11-bit auth at bits 14-4)
  _RAW_BIT=1<<15
  _CELL_SHIFT=16, _CELL_MASK=0x7FF (11-bit cell_id at bits 26-16)
  build_cmd_bus(code, auth, cell_id) — cell_id targeting retired
  CMD_PRELOAD / CMD_PRELOAD_HI — use preload_sel bits 18:17 instead
"""

from __future__ import annotations
import imago_log

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from controller import ImagoController

# ── Command codes (match fpga/verilog/unicell.v localparam exactly) ───────────

CMD_NOP             = 0x00
CMD_DATA_WRITE      = 0x01   # data bus inject — no auth needed
CMD_SET_INPUT_ADDR  = 0x02
CMD_SET_OUTPUT_ADDR = 0x03
CMD_RECONFIGURE     = 0x04
CMD_FREEZE          = 0x05
CMD_RELEASE         = 0x06
CMD_BOOT_COMMIT     = 0x07   # BOOT STATE ONLY — sets addr+auth+group, → RUN
CMD_ARRAY_RESET     = 0x08   # System-wide authenticated hard reset → all cells → BOOT state
CMD_PING            = 0x09
CMD_LATCH_IN_ON     = 0x0A
CMD_LATCH_IN_OFF    = 0x0B
CMD_MEM_CALL        = 0x0C
CMD_REARM           = 0x0D
CMD_SET_LOGICAL     = 0x0E   # legacy — use CMD_BOOT_COMMIT for new code
CMD_PRELOAD         = 0x0F   # DEPRECATED — use preload_sel bits on cmd_bus
CMD_CLEAR_ARRIVED   = 0x10
CMD_RESET_CELL      = 0x11
CMD_SWAP_AB         = 0x12
CMD_CAPTURE_REARM   = 0x13
CMD_SET_TOPO        = 0x14
CMD_SET_INVERT      = 0x15
CMD_PRELOAD_HI      = 0x16   # DEPRECATED — use preload_sel bits on cmd_bus

# System-only commands — require auth_token match
_SYSTEM_ONLY_CMDS = {CMD_RECONFIGURE, CMD_FREEZE, CMD_RELEASE,
                     CMD_LATCH_IN_ON, CMD_LATCH_IN_OFF, CMD_MEM_CALL,
                     CMD_REARM, CMD_RESET_CELL, CMD_CLEAR_ARRIVED,
                     CMD_SWAP_AB, CMD_SET_TOPO, CMD_SET_INVERT}

# ── cmd_bus v2.3 bit layout ───────────────────────────────────────────────────

_OPCODE_MASK      = 0xFF          # bits 7:0  — 8-bit opcode
_GATE_EN_BIT      = 1 << 8        # bit  8    — gate_enable
_GATE_SET_SHIFT   = 9
_GATE_SET_MASK    = 0xFF          # bits 16:9 — 8-bit group tag
_PRELOAD_SHIFT    = 17
_PRELOAD_MASK     = 0x3           # bits 18:17 — preload_sel (2 bits)
_SHIFT_IN_BIT     = 1 << 19       # bit 19   — shift_in_en
_SHIFT_OUT_BIT    = 1 << 20       # bit 20   — shift_out_en
_AUTH_SHIFT       = 21
_AUTH_MASK        = 0xFF          # bits 28:21 — 8-bit auth token
# bits 31:29 spare

# Preload select values (preload_sel field)
PRELOAD_SEL_NONE  = 0b00   # Verilog: preload_sel=00 — no preload
PRELOAD_NONE      = PRELOAD_SEL_NONE   # legacy alias
PRELOAD_SEL_ZERO  = 0b01   # Verilog: preload_sel=01 — load 0x00000000
PRELOAD_ZERO      = PRELOAD_SEL_ZERO   # legacy alias
PRELOAD_SEL_ONES  = 0b10   # Verilog: preload_sel=10 — load 0xFFFFFFFF
PRELOAD_ONES      = PRELOAD_SEL_ONES   # legacy alias
PRELOAD_RESERVED  = 0b11

# Broadcast: gate_enable=0 means all cells see the command regardless of gate_set
BROADCAST         = 0             # gate_enable=0, gate_set ignored

# ── cmd_bus wire-format helpers ───────────────────────────────────────────────

def build_cmd_bus(opcode:       int,
                  auth:         int  = 0,
                  gate_enable:  bool = False,
                  gate_set:     int  = 0,
                  preload_sel:  int  = PRELOAD_SEL_NONE,
                  shift_in_en:  bool = False,
                  shift_out_en: bool = False) -> int:
    """
    Pack a v2.3 cmd_bus word (32-bit).

    opcode:      8-bit command code (CMD_* constants above)
    auth:        8-bit auth token (bits 28:21) — matched against cell's auth_mask
    gate_enable: True = filter by gate_set; False = broadcast to all cells
    gate_set:    8-bit group tag (bits 16:9) — only used when gate_enable=True
    preload_sel: PRELOAD_SEL_NONE/ZERO/ONES — transient a_data load (bits 18:17)
    shift_in_en: shift bus_data left by nibble count before gate tree (bit 19)
    shift_out_en:shift output right by nibble count before emit (bit 20)

    shift amount is carried separately in cmd_data[3:0].
    """
    w  =  (opcode      & _OPCODE_MASK)
    w |=  (_GATE_EN_BIT  if gate_enable  else 0)
    w |=  ((gate_set    & _GATE_SET_MASK) << _GATE_SET_SHIFT)
    w |=  ((preload_sel & _PRELOAD_MASK)  << _PRELOAD_SHIFT)
    w |=  (_SHIFT_IN_BIT  if shift_in_en  else 0)
    w |=  (_SHIFT_OUT_BIT if shift_out_en else 0)
    w |=  ((auth        & _AUTH_MASK)     << _AUTH_SHIFT)
    return w

def decode_cmd_bus(cmd_bus: int) -> dict:
    """
    Unpack a v2.3 cmd_bus word.
    Returns dict with all fields for inspection/debugging.
    """
    return {
        "opcode":       cmd_bus & _OPCODE_MASK,
        "gate_enable":  bool(cmd_bus & _GATE_EN_BIT),
        "gate_set":     (cmd_bus >> _GATE_SET_SHIFT) & _GATE_SET_MASK,
        "preload_sel":  (cmd_bus >> _PRELOAD_SHIFT)  & _PRELOAD_MASK,
        "shift_in_en":  bool(cmd_bus & _SHIFT_IN_BIT),
        "shift_out_en": bool(cmd_bus & _SHIFT_OUT_BIT),
        "auth_token":   (cmd_bus >> _AUTH_SHIFT)     & _AUTH_MASK,
        "spare":        (cmd_bus >> 29) & 0x7,
    }

def build_boot_commit(logical_addr: int,
                      auth_mask:    int,
                      group_tag:    int = 0) -> tuple:
    """
    Build the CMD_BOOT_COMMIT transaction (BOOT STATE only, no auth needed).
    Returns (cmd_bus_word, cmd_data_word).

    logical_addr: cell's logical input_address (16-bit)
    auth_mask:    8-bit auth token to store in cell's cmd_latch[18:11]
    group_tag:    8-bit group membership tag for gate_set filtering

    cmd_data layout for CMD_BOOT_COMMIT:
      [15:0]  = logical_addr
      [23:16] = auth_mask
      [31:24] = group_tag
    """
    cmd_bus  = build_cmd_bus(CMD_BOOT_COMMIT, auth=0)   # no auth — cell unconfigured
    cmd_data = ((logical_addr & 0xFFFF)       |
                ((auth_mask   & 0xFF)   << 16) |
                ((group_tag   & 0xFF)   << 24))
    return cmd_bus, cmd_data


# ── Auth helpers (VM-side — operate on cell objects) ─────────────────────────

def _get_cell_auth(cell) -> int:
    return getattr(cell, '_auth_mask', 0)

def _set_cell_auth(cell, auth: int) -> None:
    cell._auth_mask = auth & _AUTH_MASK

def _check_auth(cell, auth_presented: int) -> bool:
    stored = _get_cell_auth(cell)
    if stored == 0:
        return True   # boot bypass — auth_mask not yet set
    return (auth_presented & _AUTH_MASK) == stored


# ── Handshake codes (bridge-level, VM/OS layer only — not in silicon) ────────

HANDSHAKE_NONE    = 0x0
HANDSHAKE_ACK     = 0x1
HANDSHAKE_NAK     = 0x2
HANDSHAKE_BUSY    = 0x3
HANDSHAKE_REQUEST = 0x4
HANDSHAKE_GRANT   = 0x5
HANDSHAKE_DENY    = 0x6
HANDSHAKE_RETRY   = 0x7


# ── CommandInterface ──────────────────────────────────────────────────────────

class CommandInterface:
    """
    Translates the v2.3 command bus protocol into VM cell operations.

    Two privilege levels:
      System interface:  auth_token set — can issue RECONFIGURE/FREEZE/RELEASE
                         and all cell state control commands
      User interface:    auth_token=None — PTT-relative addresses, data only

    The VM path operates on cell objects directly — it does not construct raw
    cmd_bus words. build_cmd_bus() / decode_cmd_bus() are for the FPGA bridge.

    Boot sequence (v2.3):
      boot_cell() sends CMD_BOOT_COMMIT equivalent to set logical addr + auth.
      After that, CMD_RECONFIGURE configures topology and flags.
      Two transactions vs the old four (RECONFIGURE + SET_LOGICAL +
      SET_OUTPUT_ADDR + RELEASE).
    """

    def __init__(self,
                 controller: "ImagoController",
                 auth_token: Optional[int] = None,
                 ptt: Optional[dict] = None):
        self._ctrl         = controller
        self._auth         = (auth_token & _AUTH_MASK) if auth_token is not None else None
        self._ptt          = ptt or {}
        self._is_system    = auth_token is not None
        self._cmd_count    = 0
        self._reject_count = 0

    # ── address resolution ────────────────────────────────────────────────────

    def _resolve(self, addr: int, raw: bool = True) -> Optional[int]:
        if raw:
            return addr
        raw_addr = self._ptt.get(addr)
        if raw_addr is None:
            imago_log.info(f"[CMD] PTT index {addr} not found")
        return raw_addr

    def _get_cell(self, addr: int):
        cell = self._ctrl.array.cells.get(addr)
        if cell is not None:
            return cell
        for c in self._ctrl.array.cells.values():
            if c.input_address == addr:
                return c
        return None

    # ── auth check ────────────────────────────────────────────────────────────

    def _authorise(self, cmd: int, cell) -> bool:
        if cmd not in _SYSTEM_ONLY_CMDS:
            return True
        if not self._is_system:
            self._reject_count += 1
            imago_log.info(f"[CMD] REJECTED: CMD {cmd:#04x} requires system auth")
            return False
        if not _check_auth(cell, self._auth):
            self._reject_count += 1
            imago_log.info(f"[CMD] REJECTED: auth mismatch on {cell.address:#010x}")
            return False
        return True

    # ── core issue ────────────────────────────────────────────────────────────

    def _issue(self, cmd: int, cmd_data: int, cell_addr: int,
               raw: bool = True,
               preload_sel: int = PRELOAD_SEL_NONE) -> Optional[int]:
        """
        Issue one command to one cell.

        cmd:         command opcode (CMD_* constant)
        cmd_data:    32-bit payload (address, cmd_latch word, etc.)
        cell_addr:   target cell address (logical input_address)
        raw:         True=direct address, False=PTT-relative
        preload_sel: PRELOAD_SEL_NONE/ZERO/ONES — applied after opcode if auth_ok
                     PRELOAD_SEL_ZERO → a_data=0x00000000, a_arrived=True
                     PRELOAD_SEL_ONES → a_data=0xFFFFFFFF, a_arrived=True

        Returns cell address for CMD_PING, None otherwise.
        """
        self._cmd_count += 1

        addr = self._resolve(cell_addr, raw)
        if addr is None:
            return None

        cell = self._get_cell(addr)
        if cell is None:
            return None

        if not self._authorise(cmd, cell):
            return None

        # ── opcode dispatch ───────────────────────────────────────────────────
        if cmd == CMD_NOP:
            pass

        elif cmd == CMD_BOOT_COMMIT:
            # BOOT STATE ONLY — sets logical addr, auth_mask, group_tag.
            # No auth required — cell not yet configured.
            # cmd_data: [15:0]=logical_addr [23:16]=auth_mask [31:24]=group_tag
            logical_addr = cmd_data & 0xFFFF
            auth_mask    = (cmd_data >> 16) & 0xFF
            group_tag    = (cmd_data >> 24) & 0xFF
            cell.set_input_addr(logical_addr)
            _set_cell_auth(cell, auth_mask)
            cell._group_tag     = group_tag
            cell._physical_mode = False   # → RUN state
            imago_log.info(f"[CMD] BOOT_COMMIT: cell→addr={logical_addr:#06x} "
                           f"auth={auth_mask:#04x} group={group_tag:#04x}")

        elif cmd == CMD_SET_INPUT_ADDR:
            cell.set_input_addr(cmd_data)
            if addr in self._ctrl.array._armed:
                self._ctrl.array._armed.discard(addr)
                self._ctrl.array._armed.add(cell.address)

        elif cmd == CMD_SET_OUTPUT_ADDR:
            cell.set_output_addr(cmd_data)

        elif cmd == CMD_RECONFIGURE:
            # auth_mask in cmd_latch[30:23] — set on first RECONFIGURE (boot bypass)
            if _get_cell_auth(cell) == 0 and self._auth is not None:
                _set_cell_auth(cell, self._auth)
            cell.configure(cmd_data)
            if cell.start_flag:
                self._ctrl.array._armed.add(cell.address)

        elif cmd == CMD_FREEZE:
            cell.freeze()
            self._ctrl.array._armed.discard(cell.address)

        elif cmd == CMD_RELEASE:
            cell.release()
            self._ctrl.array._armed.add(cell.address)

        elif cmd == CMD_LATCH_IN_ON:
            cell._cmd_latch |= (1 << 26)   # set latch_in bit
            cell.latch_in = True

        elif cmd == CMD_LATCH_IN_OFF:
            cell._cmd_latch &= ~(1 << 26)  # clear latch_in bit
            cell.latch_in   = False
            cell.a_arrived  = False

        elif cmd == CMD_REARM:
            cell.start_flag    = True
            cell.one_shot_fired = False
            cell.a_arrived     = False
            self._ctrl.array._armed.add(cell.address)

        elif cmd == CMD_RESET_CELL:
            cell.a_arrived      = False
            cell.a_data         = 0
            cell.one_shot_fired = False
            cell.start_flag     = True
            self._ctrl.array._armed.add(cell.address)

        elif cmd == CMD_CLEAR_ARRIVED:
            cell.a_arrived = False
            cell.a_data    = 0

        elif cmd == CMD_PING:
            return addr

        else:
            imago_log.info(f"[CMD] Unknown opcode {cmd:#04x}")

        # ── preload_sel — applied after opcode, if auth passed ────────────────
        # Mirrors Verilog: transient modifier independent of opcode.
        # PRELOAD_SEL_ZERO → a_data=0x00000000 (AND tree false, NOR constant)
        # PRELOAD_SEL_ONES → a_data=0xFFFFFFFF (NOT/XOR/XNOR constant)
        if preload_sel != PRELOAD_SEL_NONE and self._authorise(CMD_RECONFIGURE, cell):
            if preload_sel == PRELOAD_SEL_ONES:
                cell.a_data = 0xFFFFFFFF
            else:  # PRELOAD_ZERO
                cell.a_data = 0x00000000
            cell.a_arrived = True

        return None

    # ── public API ────────────────────────────────────────────────────────────

    def reconfigure(self,
                    cell_addr: int,
                    cmd_latch: int,
                    input_address:  Optional[int] = None,
                    output_address: Optional[int] = None) -> None:
        """
        Configure a cell: optionally set addresses then load cmd_latch.
        Maps to silicon sequence: SET_INPUT_ADDR → SET_OUTPUT_ADDR → RECONFIGURE.
        """
        if input_address is not None:
            self._issue(CMD_SET_INPUT_ADDR, input_address, cell_addr)
        if output_address is not None:
            self._issue(CMD_SET_OUTPUT_ADDR, output_address, cell_addr)
        self._issue(CMD_RECONFIGURE, cmd_latch, cell_addr)

    def preload(self, cell_addr: int, value: int) -> None:
        """
        Preload a_data with an arbitrary 32-bit value and set a_arrived.
        For the two standard constants prefer preload_sel on _issue() —
        that matches silicon exactly. This method handles arbitrary values
        (VM only — silicon uses preload_sel for 0x00000000 and 0xFFFFFFFF).
        """
        cell = self._get_cell(cell_addr)
        if cell is None:
            return
        if not self._authorise(CMD_RECONFIGURE, cell):
            return
        cell.a_data    = value & 0xFFFFFFFF
        cell.a_arrived = True

    def set_input_addr(self, cell_addr: int, input_address: int) -> None:
        """CMD_SET_INPUT_ADDR."""
        self._issue(CMD_SET_INPUT_ADDR, input_address, cell_addr,
                    raw=self._is_system)

    def set_output_addr(self, cell_addr: int, output_address: int) -> None:
        """CMD_SET_OUTPUT_ADDR."""
        self._issue(CMD_SET_OUTPUT_ADDR, output_address, cell_addr,
                    raw=self._is_system)

    def freeze(self, cell_addr: int) -> None:
        """CMD_FREEZE — disarm cell."""
        self._issue(CMD_FREEZE, 0, cell_addr)

    def release(self, cell_addr: int) -> None:
        """CMD_RELEASE — re-arm cell."""
        self._issue(CMD_RELEASE, 0, cell_addr)

    def ping(self, cell_addr: int) -> Optional[int]:
        """CMD_PING — returns address if alive, None if absent."""
        return self._issue(CMD_PING, 0, cell_addr, raw=self._is_system)

    def data_write(self, cell_addr: int, value: int) -> None:
        """
        Deliver a data value directly to a cell's receive() method.
        VM equivalent of a bus_data write (not a cmd_bus command).
        Used by controller.start() and test harnesses.
        """
        cell = self._get_cell(cell_addr)
        if cell is not None:
            cell.receive(value)

    # ── bulk operations ───────────────────────────────────────────────────────

    def boot_cell(self,
                  cell_addr:      int,
                  cmd_latch:      int = 0,
                  input_address:  int = 0,
                  output_address: int = 0,
                  group_tag:      int = 0) -> bool:
        """
        Full boot sequence (v2.3):
          PING → CMD_BOOT_COMMIT (logical addr + auth + group) → RECONFIGURE → FREEZE.

        Returns True if cell responded to PING.
        CMD_BOOT_COMMIT replaces the old SET_LOGICAL + separate auth sequence.
        """
        if self.ping(cell_addr) is None:
            return False
        cell = self._get_cell(cell_addr)
        if cell is None:
            return False

        # CMD_BOOT_COMMIT: set logical addr, auth_mask, group_tag in one transaction
        auth = self._auth if self._auth is not None else 0
        boot_data = (input_address & 0xFFFF) | ((auth & 0xFF) << 16) | ((group_tag & 0xFF) << 24)
        self._issue(CMD_BOOT_COMMIT, boot_data, cell_addr)

        self.reconfigure(cell_addr, cmd_latch,
                         output_address=output_address)
        self.freeze(cell_addr)
        return True

    def boot_all_cells(self) -> dict:
        """BIOS boot pass: ping + boot_cell every cell in the array."""
        if not self._is_system:
            raise PermissionError("boot_all_cells requires system CommandInterface")
        live = dead = 0
        for addr in list(self._ctrl.array.cells.keys()):
            if self.boot_cell(addr):
                live += 1
            else:
                dead += 1
        auth_set = sum(1 for c in self._ctrl.array.cells.values()
                       if _get_cell_auth(c) != 0)
        imago_log.info(f"[CMD] Boot: {live} live, {dead} dead, {auth_set} auth-set")
        return {"live": live, "dead": dead, "auth_set": auth_set}

    # ── diagnostics ──────────────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "commands_issued":   self._cmd_count,
            "commands_rejected": self._reject_count,
            "is_system":         self._is_system,
            "auth_set":          self._auth is not None,
        }

    def __repr__(self) -> str:
        mode = "system" if self._is_system else "user"
        return (f"CommandInterface({mode}, "
                f"cmds={self._cmd_count}, "
                f"rejected={self._reject_count})")


# ── Convenience factories ─────────────────────────────────────────────────────

def make_system_interface(controller: "ImagoController",
                          auth_token: int) -> CommandInterface:
    """Create a system-level CommandInterface (auth required for config ops)."""
    return CommandInterface(controller, auth_token=auth_token)

def make_user_interface(controller: "ImagoController",
                        ptt: dict) -> CommandInterface:
    """Create a user-level CommandInterface (data ops only, PTT-relative)."""
    return CommandInterface(controller, auth_token=None, ptt=ptt)


# ── Backward-compatibility aliases ───────────────────────────────────────────
# v2.2 build_cmd_bus signature (code, auth, cell_id) is retired.
# Kept as a shim that logs a deprecation warning and returns a best-effort word.

def _build_cmd_bus_legacy(code: int, auth: int = 0, cell_id: int = 0x7FF) -> int:
    """DEPRECATED: v2.2 cmd_bus builder. Use build_cmd_bus() with named args."""
    imago_log.info("[CMD] WARNING: build_cmd_bus(code, auth, cell_id) is v2.2 format. "
                   "Update caller to v2.3 build_cmd_bus(opcode, auth=..., gate_enable=..., gate_set=...).")
    return build_cmd_bus(opcode=code & 0xFF, auth=auth & _AUTH_MASK)

def build_bus1(address: int, gate_state: int = 0,
               output_address: int = None) -> list:
    """Deprecated: build_bus1 is a v1 helper. Use ImagoController.load_map()."""
    from controller import CellMapRecord
    out = output_address if output_address is not None else address + 1
    return [CellMapRecord(gate_state=gate_state,
                          input_address=address,
                          output_address=out)]

def decode_bus1(data: int) -> tuple:
    """Deprecated: decode_bus1 is a v1 helper. Returns (address, value) tuple."""
    return (data >> 16) & 0xFFFF, data & 0xFFFF

# Scope constants — retired
_SCOPE_LOCAL    = 0
_SCOPE_GLOBAL   = 1
_SCOPE_BRIDGE   = 2
_SCOPE_SHORE    = 3
_SCOPE_EXTENDED = 4

# Re-export commonly imported command constants
try:
    from controller import (
        CMD_NOP, CMD_DATA_WRITE, CMD_SET_INPUT_ADDR, CMD_SET_OUTPUT_ADDR,
        CMD_RECONFIGURE, CMD_FREEZE, CMD_RELEASE, CMD_PING,
        CMD_LATCH_IN_ON, CMD_LATCH_IN_OFF, CMD_REARM, CMD_RESET_CELL,
        CMD_CLEAR_ARRIVED, CMD_SWAP_AB, CMD_PRELOAD, CMD_BOOT_COMMIT,
    )
except ImportError:
    pass   # use the constants defined above
