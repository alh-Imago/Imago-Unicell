"""
command_interface.py — Command bus interface.

Ground truth: fpga/verilog/unicell.v (silicon-validated, iCEBreaker 2026-05-17).

cmd_bus word layout (confirmed on silicon):
  bits  3-0:   command code
  bits 14-4:   auth token (11 bits)
  bit   15:    raw_addr (host always sets 1)
  bits 26-16:  cell_id (11 bits — 0x7FF = broadcast)
  bits 31-27:  reserved

Command codes (match Verilog localparam exactly):
  0 = CMD_NOP
  2 = CMD_SET_INPUT_ADDR   — cmd_data → input_address
  3 = CMD_SET_OUTPUT_ADDR  — cmd_data → output_address
  4 = CMD_RECONFIGURE      — cmd_data → cmd_latch, arms cell
  5 = CMD_FREEZE           — disarm, suppress output
  6 = CMD_RELEASE          — re-arm
  9 = CMD_PING             — accepted, no response in baseline

Data bus (bus_data / cmd_data):
  All payloads are 32-bit. Addresses are 32-bit in the VM (16-bit on
  iCEBreaker — icm_loader handles truncation). cmd_latch words are 32-bit.

Retired from previous version:
  CMD_DATA_WRITE=0, CMD_SET_INPUT_ADDR=1, CMD_SET_OUTPUT_ADDR=2 (wrong codes)
  CMD_RECONFIGURE=3, CMD_FREEZE=4, CMD_RELEASE=5 (wrong codes)
  CMD_COPY_DATA_TO_OUT=6, CMD_COPY_DATA_TO_IN=7 (not in Verilog)
  CMD_PING=8 (wrong code — is 9)
  _SCOPE_EXTENDED, _SCOPE_SHORE (64-bit address model retired)
  set_addr_latch(), resolve_extended_address() (64-bit model retired)
  _config_upper path in CMD_RECONFIGURE
  FUNCTION_LOAD_PATTERN config protocol
  copy_data_to_out(), copy_data_to_in() (not in Verilog)
"""

from __future__ import annotations
import imago_log

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from controller import ImagoController

# ── Command codes (match fpga/verilog/unicell.v localparam exactly) ───────────

CMD_NOP             = 0
CMD_SET_INPUT_ADDR  = 2
CMD_SET_OUTPUT_ADDR = 3
CMD_RECONFIGURE     = 4
CMD_FREEZE          = 5
CMD_RELEASE         = 6
CMD_PING            = 9

# System-only commands — require auth
_SYSTEM_ONLY_CMDS = {CMD_RECONFIGURE, CMD_FREEZE, CMD_RELEASE}

# ── cmd_bus bit layout (confirmed on silicon) ─────────────────────────────────

_CODE_MASK    = 0xF           # bits 3-0
_AUTH_SHIFT   = 4
_AUTH_MASK    = 0x7FF         # 11 bits, bits 14-4
_RAW_BIT      = 1 << 15       # bit 15 — host always sets 1
_CELL_SHIFT   = 16
_CELL_MASK    = 0x7FF         # 11 bits, bits 26-16
_BROADCAST    = 0x7FF         # cell_id = all cells

# ── cmd_bus helpers ───────────────────────────────────────────────────────────

def build_cmd_bus(code: int,
                  auth: int = 0,
                  cell_id: int = _BROADCAST) -> int:
    """
    Pack a cmd_bus word.
    code:    command code (0-15)
    auth:    11-bit auth token (bits 14-4)
    cell_id: target cell (0-0x7FE) or 0x7FF for broadcast (bits 26-16)
    """
    w  = (code    & _CODE_MASK)
    w |= (auth    & _AUTH_MASK)  << _AUTH_SHIFT
    w |= _RAW_BIT
    w |= (cell_id & _CELL_MASK)  << _CELL_SHIFT
    return w

def decode_cmd_bus(cmd_bus: int) -> tuple:
    """Unpack cmd_bus → (code, auth, cell_id, is_broadcast)."""
    code      = cmd_bus & _CODE_MASK
    auth      = (cmd_bus >> _AUTH_SHIFT) & _AUTH_MASK
    cell_id   = (cmd_bus >> _CELL_SHIFT) & _CELL_MASK
    broadcast = cell_id == _BROADCAST
    return code, auth, cell_id, broadcast


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _get_cell_auth(cell) -> int:
    return getattr(cell, '_auth_mask', 0)

def _set_cell_auth(cell, auth: int) -> None:
    cell._auth_mask = auth & _AUTH_MASK

def _check_auth(cell, auth_presented: int) -> bool:
    stored = _get_cell_auth(cell)
    if stored == 0:
        return True   # boot bypass — not yet set
    return (auth_presented & _AUTH_MASK) == stored


# ── Handshake codes (bridge-level, carried in cmd_bus reserved bits) ──────────
# Bits 31-27 reserved in Verilog — handshake is a VM/OS-layer concept only.
# Not in silicon at this time. Kept as Python constants for bridge protocol.

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
    Translates the Verilog command bus protocol into VM cell operations.

    Two privilege levels:
      System interface:  auth_token set, can issue RECONFIGURE/FREEZE/RELEASE
      User interface:    auth_token=None, PTT-relative addresses, data only

    All commands map directly to cell.configure() / cell.freeze() etc —
    no intermediate LOAD_PATTERN sequences, no multi-step config.
    """

    def __init__(self,
                 controller: "ImagoController",
                 auth_token: Optional[int] = None,
                 ptt: Optional[dict] = None):
        self._ctrl        = controller
        self._auth        = (auth_token & _AUTH_MASK) if auth_token is not None else None
        self._ptt         = ptt or {}
        self._is_system   = auth_token is not None
        self._cmd_count   = 0
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
        # Direct lookup first, then search by input_address
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
            imago_log.info(f"[CMD] REJECTED: CMD {cmd} requires system auth")
            return False
        if not _check_auth(cell, self._auth):
            self._reject_count += 1
            imago_log.info(f"[CMD] REJECTED: auth mismatch on {cell.address:#010x}")
            return False
        return True

    # ── core issue ────────────────────────────────────────────────────────────

    def _issue(self, cmd: int, cmd_data: int, cell_addr: int,
               raw: bool = True) -> Optional[int]:
        """
        Issue one command to one cell.
        cmd:       command code
        cmd_data:  32-bit payload (address or cmd_latch word)
        cell_addr: target cell address
        raw:       True=direct address, False=PTT-relative
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

        if cmd == CMD_NOP:
            pass

        elif cmd == CMD_SET_INPUT_ADDR:
            cell.set_input_addr(cmd_data)
            if addr in self._ctrl.array._armed:
                self._ctrl.array._armed.discard(addr)
                self._ctrl.array._armed.add(cell.address)

        elif cmd == CMD_SET_OUTPUT_ADDR:
            cell.set_output_addr(cmd_data)

        elif cmd == CMD_RECONFIGURE:
            # Set auth mask on first RECONFIGURE (boot bypass)
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

        elif cmd == CMD_PING:
            return addr

        else:
            imago_log.info(f"[CMD] Unknown command code {cmd}")

        return None

    # ── public API ────────────────────────────────────────────────────────────

    def reconfigure(self,
                    cell_addr: int,
                    cmd_latch: int,
                    input_address: Optional[int] = None,
                    output_address: Optional[int] = None) -> None:
        """
        Configure a cell: optionally set addresses then load cmd_latch.
        Matches the silicon sequence: SET_INPUT_ADDR, SET_OUTPUT_ADDR, RECONFIGURE.
        """
        if input_address is not None:
            self._issue(CMD_SET_INPUT_ADDR, input_address, cell_addr, raw=True)
        if output_address is not None:
            self._issue(CMD_SET_OUTPUT_ADDR, output_address, cell_addr, raw=True)
        self._issue(CMD_RECONFIGURE, cmd_latch, cell_addr, raw=True)

    def set_input_addr(self, cell_addr: int, input_address: int) -> None:
        """CMD_SET_INPUT_ADDR."""
        self._issue(CMD_SET_INPUT_ADDR, input_address, cell_addr, raw=self._is_system)

    def set_output_addr(self, cell_addr: int, output_address: int) -> None:
        """CMD_SET_OUTPUT_ADDR."""
        self._issue(CMD_SET_OUTPUT_ADDR, output_address, cell_addr, raw=self._is_system)

    def freeze(self, cell_addr: int) -> None:
        """CMD_FREEZE — disarm cell."""
        self._issue(CMD_FREEZE, 0, cell_addr, raw=True)

    def release(self, cell_addr: int) -> None:
        """CMD_RELEASE — re-arm cell."""
        self._issue(CMD_RELEASE, 0, cell_addr, raw=True)

    def ping(self, cell_addr: int) -> Optional[int]:
        """CMD_PING — returns address if alive, None if absent."""
        return self._issue(CMD_PING, 0, cell_addr, raw=self._is_system)

    def data_write(self, cell_addr: int, value: int) -> None:
        """
        Deliver a data value directly to a cell's receive() method.
        This is the VM equivalent of a bus_data write (not a cmd_bus command).
        Used by controller.start() and test harnesses.
        """
        cell = self._get_cell(cell_addr)
        if cell is not None:
            cell.receive(value)

    # ── bulk operations ───────────────────────────────────────────────────────

    def boot_cell(self,
                  cell_addr: int,
                  cmd_latch: int = 0,
                  input_address: int = 0,
                  output_address: int = 0) -> bool:
        """
        Full boot sequence: PING → SET_ADDRS → RECONFIGURE → FREEZE.
        Returns True if cell responded to PING.
        """
        if self.ping(cell_addr) is None:
            return False
        cell = self._get_cell(cell_addr)
        if cell is None:
            return False
        if self._auth is not None:
            _set_cell_auth(cell, self._auth)
        self.reconfigure(cell_addr, cmd_latch, input_address, output_address)
        self.freeze(cell_addr)
        return True

    def boot_all_cells(self) -> dict:
        """BIOS boot pass: ping + configure + freeze every cell."""
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
    return CommandInterface(controller, auth_token=auth_token)

def make_user_interface(controller: "ImagoController",
                        ptt: dict) -> CommandInterface:
    return CommandInterface(controller, auth_token=None, ptt=ptt)
