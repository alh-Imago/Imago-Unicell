"""
command_interface.py — Three-Bus Command Interface

Translates the hardware command protocol (Bus 1: CMD+Auth, Bus 2: Data,
Bus 3: Address) into existing UniCell and controller operations.

This is Option C of the architecture migration — a translation layer that
sits above the existing sim abstraction. Cells, tiles, and the compiler
are unchanged. OS-level code (COMPANION, Ward, Shore, bridge setup) uses
this interface instead of directly manipulating cell state.

Architecture
============

Three 32-bit buses per command transaction:

  Bus 1 (Command & Control):
    bits  0-3:   command code (0-15)
    bits  4-14:  auth mask (11 bits checked against cell's stored mask)
    bit  15:     address mode (0=PTT-relative, 1=raw system address)
    bits 16-31:  reserved flags

  Bus 2 (Data Payload):
    bits 0-31:   value being written (data, address, or config bits)

  Bus 3 (Target Address):
    bits 0-31:   destination cell address (raw or PTT-relative)

Command Codes
=============

  0  DATA_WRITE         User+System   Bus2 → cell data latch
  1  SET_INPUT_ADDR     User+System   Bus2 → cell input_address
  2  SET_OUTPUT_ADDR    User+System   Bus2 → cell output_address
  3  RECONFIGURE        System only   Bus2 → config+mode registers (auth required)
  4  FREEZE             System only   Clear start_flag
  5  RELEASE            System only   Set start_flag
  6  COPY_DATA_TO_OUT   User+System   data latch → output_address register
  7  COPY_DATA_TO_IN    User+System   data latch → input_address register
  8  PING               Anyone        Return cell address if alive
  9-15 Reserved

Auth Model
==========

Each cell has a 12-bit auth_mask set at boot (Command 3 from BIOS).
The mask is stored as a write-only field — it can be set but never read
back. Subsequent Command 3 transactions must carry a matching auth value
on Bus 1 bits 4-14, otherwise the command is silently rejected.

In the sim, auth_mask is stored in the cell but never exposed via any
public interface. The CommandInterface holds the system auth token and
appends it to system-issued commands automatically.

Address Modes
=============

  PTT-relative (Bus 1 bit 15 = 0):
    Bus 3 is a PTT index. CommandInterface translates to raw address
    via the PTT registry. User-space commands use this mode.
    Cannot address cells outside the Pond's PTT-mapped range.

  Raw system address (Bus 1 bit 15 = 1):
    Bus 3 is a raw cell address. Requires valid auth on Bus 1.
    System-space commands use this mode.

Usage
=====

  from command_interface import CommandInterface, CMD_RECONFIGURE

  # System interface (has auth, uses raw addresses)
  sys_cmd = CommandInterface(controller, auth_token=0xA3F)

  # Configure a cell
  sys_cmd.reconfigure(cell_addr=0x1000,
                      gate_state=GS_NOT,
                      mode_flags=GS_LATCH,
                      input_address=0x2000,
                      output_address=0x3000)

  # User interface (no auth, PTT-relative addresses)
  user_cmd = CommandInterface(controller, auth_token=None, ptt=my_ptt)

  # Write data
  user_cmd.data_write(cell_addr=ptt_index_5, value=42)

  # Freeze a cell
  sys_cmd.freeze(cell_addr=0x1000)
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from controller import ImagoController

# ── Command codes ─────────────────────────────────────────────────────────────

CMD_DATA_WRITE       = 0
CMD_SET_INPUT_ADDR   = 1
CMD_SET_OUTPUT_ADDR  = 2
CMD_RECONFIGURE      = 3
CMD_FREEZE           = 4
CMD_RELEASE          = 5
CMD_COPY_DATA_TO_OUT = 6
CMD_COPY_DATA_TO_IN  = 7
CMD_PING             = 8

# Commands 9-15 reserved
# Commands 16-31 extended system commands (future)

# System-only commands — require auth
_SYSTEM_ONLY_CMDS = {CMD_RECONFIGURE, CMD_FREEZE, CMD_RELEASE}

# Auth mask bit position in Bus 1
_AUTH_SHIFT   = 4
_AUTH_MASK    = 0b11111111111   # 11 bits (fits 12-bit card token in 11 usable bits)
_ADDR_MODE_BIT = 1 << 15        # 0=PTT-relative, 1=raw
# Scope bits: Bus 1 bits 16-17 — indicate address width for Bus 3
# 00 = LOCAL    (Bus 3 is 32-bit, upper 32 bits ignored)
# 01 = SHORE    (Bus 3 bits 0-47 used, upper 16 = stack qualifier)
# 10 = EXTENDED (Bus 3 all 64 bits used)
# 11 = reserved
_SCOPE_SHIFT  = 16
_SCOPE_MASK   = 0b11
_SCOPE_LOCAL    = 0b00   # 32-bit address
_SCOPE_SHORE    = 0b01   # 48-bit address
_SCOPE_EXTENDED = 0b10   # 64-bit address

# ── ACK/REQ handshake field (Bus 1 bits 18-21) ───────────────────────────────
# Bridge-level acknowledgement and request signalling.
# Only meaningful on INBOUND and OUTBOUND bridge cells — ignored on compute cells.
# Travels with the command on Bus 1 — no extra bus wire required.
# The scope field (bits 16-17) implicitly identifies the level:
#   SCOPE_LOCAL    → pond-to-pond acknowledgement
#   SCOPE_SHORE    → card-to-card acknowledgement
#   SCOPE_EXTENDED → system-to-system acknowledgement (UniWave)
#
# 4 bits = 16 states. Currently assigned:
#   0x0  HANDSHAKE_NONE    — no handshake, normal data packet
#   0x1  HANDSHAKE_ACK     — received and accepted
#   0x2  HANDSHAKE_NAK     — received but rejected (mask mismatch, full, etc.)
#   0x3  HANDSHAKE_BUSY    — received, queued, not yet processed
#   0x4  HANDSHAKE_REQUEST — sender is requesting a resource or response
#   0x5  HANDSHAKE_GRANT   — request approved
#   0x6  HANDSHAKE_DENY    — request refused
#   0x7  HANDSHAKE_RETRY   — try again (transient timing issue)
#   0x8-0xF reserved for future scale-up
#
# The Ward monitors bridge handshake state — a bridge stuck in BUSY or
# receiving repeated NAK/DENY flags is surfaced as a health concern in the PTT.
#
_HS_SHIFT         = 18
_HS_MASK          = 0b1111   # 4 bits

HANDSHAKE_NONE    = 0x0   # normal packet, no handshake
HANDSHAKE_ACK     = 0x1   # accepted
HANDSHAKE_NAK     = 0x2   # rejected
HANDSHAKE_BUSY    = 0x3   # queued, pending
HANDSHAKE_REQUEST = 0x4   # requesting resource or response
HANDSHAKE_GRANT   = 0x5   # request approved
HANDSHAKE_DENY    = 0x6   # request refused
HANDSHAKE_RETRY   = 0x7   # transient — try again

# Bits 22-31 remain reserved for future use

# ── Bus 1 helpers ─────────────────────────────────────────────────────────────

def build_bus1(cmd: int, auth: int = 0, raw_addr: bool = True,
               scope: int = _SCOPE_LOCAL,
               handshake: int = HANDSHAKE_NONE) -> int:
    """Pack command code + auth + address mode + scope + handshake into Bus 1.

    handshake: HANDSHAKE_* constant — bridge-level ACK/REQ signal.
               Only meaningful on INBOUND/OUTBOUND bridge cells.
               Defaults to HANDSHAKE_NONE (normal data packet).
    scope:     _SCOPE_LOCAL (32-bit), _SCOPE_SHORE (48-bit),
               _SCOPE_EXTENDED (64-bit) — implicitly sets handshake level.
    """
    b1 = (cmd & 0xF)
    b1 |= ((auth & _AUTH_MASK) << _AUTH_SHIFT)
    if raw_addr:
        b1 |= _ADDR_MODE_BIT
    b1 |= ((scope     & _SCOPE_MASK) << _SCOPE_SHIFT)
    b1 |= ((handshake & _HS_MASK)    << _HS_SHIFT)
    return b1

def decode_bus1(bus1: int) -> tuple:
    """Unpack Bus 1 → (cmd_code, auth_bits, is_raw_addr, scope, handshake)."""
    cmd       = bus1 & 0xF
    auth      = (bus1 >> _AUTH_SHIFT) & _AUTH_MASK
    is_raw    = bool(bus1 & _ADDR_MODE_BIT)
    scope     = (bus1 >> _SCOPE_SHIFT) & _SCOPE_MASK
    handshake = (bus1 >> _HS_SHIFT)    & _HS_MASK
    return cmd, auth, is_raw, scope, handshake


# ── Cell auth extension ───────────────────────────────────────────────────────

def _get_cell_auth(cell) -> int:
    """Get the cell's stored auth mask (sim: stored as hidden attribute)."""
    return getattr(cell, '_auth_mask', 0)

def _set_cell_auth(cell, auth: int) -> None:
    """Set the cell's auth mask (write-only in hardware, readable in sim for testing)."""
    cell._auth_mask = auth & _AUTH_MASK

def _check_auth(cell, auth_presented: int) -> bool:
    """True if the presented auth matches the cell's stored mask."""
    stored = _get_cell_auth(cell)
    if stored == 0:
        # Cell not yet initialised — accept any auth at boot time
        return True
    return (auth_presented & _AUTH_MASK) == stored


# ── CommandInterface ──────────────────────────────────────────────────────────

class CommandInterface:
    """
    Translates the three-bus command protocol into existing cell operations.

    Two privilege levels:
      System interface:  auth_token set, raw addresses, can issue CMD 3/4/5
      User interface:    auth_token=None, PTT-relative addresses, CMD 0-2/6-8 only
    """

    def __init__(self,
                 controller: "ImagoController",
                 auth_token: Optional[int] = None,
                 ptt: Optional[dict] = None):
        """
        controller:  ImagoController instance
        auth_token:  12-bit card auth token (system only; None = user space)
        ptt:         {ptt_index: raw_cell_address} for PTT-relative addressing
        """
        self._ctrl       = controller
        self._auth       = (auth_token & _AUTH_MASK) if auth_token is not None else None
        self._ptt        = ptt or {}
        self._is_system  = auth_token is not None
        self._cmd_count  = 0
        self._reject_count = 0

    # ── address resolution ────────────────────────────────────────────────────

    def _resolve(self, addr: int, raw: bool = True) -> Optional[int]:
        """
        Resolve addr to a raw cell address.
        If raw=True (system mode): addr is already a raw address.
        If raw=False (PTT mode): addr is a PTT index → look up raw address.
        """
        if raw:
            return addr
        raw_addr = self._ptt.get(addr)
        if raw_addr is None:
            print(f"[CMD] PTT index {addr} not found in PTT map")
        return raw_addr

    def _get_cell(self, addr: int):
        """Get UniCell object by raw address, or None if not found."""
        return self._ctrl.array.cells.get(addr)

    # ── auth check ────────────────────────────────────────────────────────────

    def _authorise(self, cmd: int, cell) -> bool:
        """Check auth for system-only commands. Returns True if allowed."""
        if cmd not in _SYSTEM_ONLY_CMDS:
            return True   # user commands need no auth check
        if not self._is_system:
            self._reject_count += 1
            print(f"[CMD] REJECTED: CMD {cmd} requires system auth (user interface)")
            return False
        if not _check_auth(cell, self._auth):
            self._reject_count += 1
            print(f"[CMD] REJECTED: CMD {cmd} auth mismatch on cell {hex(cell.address)}")
            return False
        return True

    # ── command implementations ───────────────────────────────────────────────

    def _issue(self, cmd: int, bus2: int, bus3: int, raw: bool = True,
               scope: int = 0) -> Optional[int]:
        """
        Issue a command. Returns result value for PING, None otherwise.
        bus2: data payload
        bus3: target address (raw or PTT-relative)
        raw:  True=raw address, False=PTT-relative
        scope: address scope (_SCOPE_LOCAL, _SCOPE_SHORE, _SCOPE_EXTENDED)
               used by CMD_RECONFIGURE to select config register half
        """
        self._cmd_count += 1
        self._last_bus1 = scope << 16  # store scope for CMD_RECONFIGURE handler

        raw_addr = self._resolve(bus3, raw)
        if raw_addr is None:
            return None

        cell = self._get_cell(raw_addr)
        if cell is None:
            # Cell not found — silent rejection (like hardware)
            return None

        if not self._authorise(cmd, cell):
            return None

        # Execute command
        if cmd == CMD_DATA_WRITE:
            cell.receive(bus2)

        elif cmd == CMD_SET_INPUT_ADDR:
            cell.input_address = bus2 & 0xFFFFFFFF

        elif cmd == CMD_SET_OUTPUT_ADDR:
            cell.output_address = bus2 & 0xFFFFFFFF

        elif cmd == CMD_RECONFIGURE:
            # CMD_RECONFIGURE extends to 64-bit config register via scope bits.
            # scope=LOCAL (00):    bus2 → lower 32 bits of config (gate_state etc)
            # scope=EXTENDED (10): bus2 → upper 32 bits of config (_config_upper)
            #                      upper config = forwarding address upper half
            #                      ZERO connection to data bus or NOR compute
            # Extract scope from bus1 (bits 16-17)
            _cmd_scope = (self._last_bus1 >> 16) & 0b11 if hasattr(self, '_last_bus1') else 0

            if _cmd_scope == _SCOPE_EXTENDED:
                # Write to upper config register — address path only
                if hasattr(cell, '_config_upper'):
                    cell._config_upper = bus2 & 0xFFFFFFFF
                return None

            # Normal lower config write
            from unicell import FUNCTION_LOAD_PATTERN
            gs        = bus2 & 0xFFFFFFFF
            in_addr   = getattr(cell, 'input_address',  0)
            out_addr  = getattr(cell, 'output_address', 0)
            # Set auth mask on first RECONFIGURE if not yet set
            if _get_cell_auth(cell) == 0 and self._auth is not None:
                _set_cell_auth(cell, self._auth)
            # Re-apply config via existing receive protocol
            cell._config_mode = True
            cell._config_step = 0
            cell.receive(gs)
            cell.receive(in_addr)
            cell.receive(out_addr)

        elif cmd == CMD_FREEZE:
            cell.start_flag = False

        elif cmd == CMD_RELEASE:
            cell.start_flag = True
            if bus2 != 0:
                cell.receive(bus2)   # optional data pre-load

        elif cmd == CMD_COPY_DATA_TO_OUT:
            sv = getattr(cell, '_stored_value', None)
            if sv is not None:
                cell.output_address = sv & 0xFFFFFFFF

        elif cmd == CMD_COPY_DATA_TO_IN:
            sv = getattr(cell, '_stored_value', None)
            if sv is not None:
                cell.input_address = sv & 0xFFFFFFFF

        elif cmd == CMD_PING:
            return raw_addr   # alive — return own address

        return None

    # ── public API ────────────────────────────────────────────────────────────

    def data_write(self, cell_addr: int, value: int) -> None:
        """CMD 0: Write value to cell data latch."""
        self._issue(CMD_DATA_WRITE, value, cell_addr, raw=self._is_system)

    def set_input_addr(self, cell_addr: int, input_address: int) -> None:
        """CMD 1: Set cell input address register."""
        self._issue(CMD_SET_INPUT_ADDR, input_address, cell_addr, raw=self._is_system)

    def set_output_addr(self, cell_addr: int, output_address: int) -> None:
        """CMD 2: Set cell output address register."""
        self._issue(CMD_SET_OUTPUT_ADDR, output_address, cell_addr, raw=self._is_system)

    def set_addr_latch(self, cell_addr: int,
                       lower_addr: int, upper_addr: int) -> bool:
        """Configure a bridge cell as a 64-bit address latch.

        lower_addr: bits  0-31 → output_address register (existing config field)
        upper_addr: bits 32-63 → _config_upper register  (extended config field)

        Both written via CMD_RECONFIGURE — same command bus connection already
        present for the lower config. Upper half uses scope=EXTENDED to select
        the upper 32 bits of the config register.

        The config register is already connected to the command bus.
        This just extends it to 64 bits. Zero new bus connections.
        Zero connection to data path or NOR compute.

        full_address = (upper_addr << 32) | lower_addr
        Resolved by ShoreKeeper PTT to full routable 64-bit address.
        """
        cell = self._resolve_cell(cell_addr)
        if cell is not None:
            # Set addr_latch mode flag
            cell.addr_latch     = True
            # Write lower address to output_address (existing config field)
            cell.output_address = lower_addr & 0xFFFFFFFF
            # Write upper address to _config_upper (extended config field)
            # Same command bus path — upper half of the 64-bit config register
            # NEVER touches data bus or NOR compute path
            cell._config_upper  = upper_addr & 0xFFFFFFFF
        return True

    def resolve_extended_address(self, cell_addr: int) -> int:
        """Return full 64-bit forwarding address for an addr_latch cell.
        Returns 0 if cell not found or not in addr_latch mode."""
        cell = self._resolve_cell(cell_addr)
        if cell is None or not getattr(cell, 'addr_latch', False):
            return 0
        upper = getattr(cell, '_config_upper', 0)
        lower = cell.output_address or 0
        return (upper << 32) | lower

    def _resolve_cell(self, cell_addr: int):
        """Return the UniCell whose input_address matches cell_addr.
        The controller assigns sequential internal keys — we search by
        input_address which is what CommandInterface addresses mean."""
        # Fast path: direct key lookup (works if key == input_address)
        cell = self._ctrl.array.cells.get(cell_addr)
        if cell is not None:
            return cell
        # Slow path: search by input_address
        for cell in self._ctrl.array.cells.values():
            if cell.input_address == cell_addr:
                return cell
        return None

    def reconfigure(self,
                    cell_addr: int,
                    gate_state: int,
                    input_address: Optional[int] = None,
                    output_address: Optional[int] = None) -> None:
        """
        CMD 3: Reconfigure cell (system only, auth required).
        Translates to existing FUNCTION_LOAD_PATTERN sequence internally.
        """
        cell = self._get_cell(cell_addr)
        if cell is None:
            return

        # Update address registers first if supplied
        if input_address is not None:
            cell.input_address = input_address & 0xFFFFFFFF
        if output_address is not None:
            cell.output_address = output_address & 0xFFFFFFFF

        self._issue(CMD_RECONFIGURE, gate_state, cell_addr, raw=True)

    def freeze(self, cell_addr: int) -> None:
        """CMD 4: Freeze cell (system only)."""
        self._issue(CMD_FREEZE, 0, cell_addr, raw=True)

    def release(self, cell_addr: int, preload: int = 0) -> None:
        """CMD 5: Release (arm) cell (system only)."""
        self._issue(CMD_RELEASE, preload, cell_addr, raw=True)

    def copy_data_to_out(self, cell_addr: int) -> None:
        """CMD 6: Copy data latch value to output address register."""
        self._issue(CMD_COPY_DATA_TO_OUT, 0, cell_addr, raw=self._is_system)

    def copy_data_to_in(self, cell_addr: int) -> None:
        """CMD 7: Copy data latch value to input address register."""
        self._issue(CMD_COPY_DATA_TO_IN, 0, cell_addr, raw=self._is_system)

    def ping(self, cell_addr: int) -> Optional[int]:
        """CMD 8: Test cell liveness. Returns address if alive, None if dead/absent."""
        return self._issue(CMD_PING, 0, cell_addr, raw=self._is_system)

    # ── bulk operations ───────────────────────────────────────────────────────

    def boot_cell(self,
                  cell_addr: int,
                  gate_state: int = 0,
                  input_address: int = 0,
                  output_address: int = 0) -> bool:
        """
        Full boot sequence for one cell:
          1. PING to verify alive
          2. RECONFIGURE with auth token (sets auth_mask + gate config)
          3. FREEZE (cell starts disarmed)

        Returns True if cell responded to PING, False if dead/absent.
        Used by the BIOS dead-cell-check pass.
        """
        if self.ping(cell_addr) is None:
            return False    # dead or absent

        cell = self._get_cell(cell_addr)
        if cell is None:
            return False

        # Set auth mask on this cell
        if self._auth is not None:
            _set_cell_auth(cell, self._auth)

        # Configure
        self.reconfigure(cell_addr, gate_state, input_address, output_address)

        # Leave frozen — COMPANION arms cells explicitly
        self.freeze(cell_addr)

        return True

    def boot_all_cells(self) -> dict:
        """
        BIOS dead-cell-check pass: ping + auth + freeze every cell.
        Returns {live: int, dead: int, auth_set: int}.
        Must be called with a system CommandInterface (auth_token set).
        """
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

        print(f"[CMD] Boot complete: {live} live, {dead} dead, "
              f"{auth_set} cells auth-set")
        return {"live": live, "dead": dead, "auth_set": auth_set}

    # ── diagnostics ──────────────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "commands_issued": self._cmd_count,
            "commands_rejected": self._reject_count,
            "is_system": self._is_system,
            "auth_set": self._auth is not None,
        }

    def __repr__(self) -> str:
        mode = "system" if self._is_system else "user"
        return (f"CommandInterface({mode}, "
                f"cmds={self._cmd_count}, "
                f"rejected={self._reject_count})")


# ── Convenience factory functions ─────────────────────────────────────────────

def make_system_interface(controller: "ImagoController",
                          auth_token: int) -> CommandInterface:
    """Create a system-level command interface with auth token."""
    return CommandInterface(controller, auth_token=auth_token)


def make_user_interface(controller: "ImagoController",
                        ptt: dict) -> CommandInterface:
    """Create a user-level command interface with PTT-relative addressing."""
    return CommandInterface(controller, auth_token=None, ptt=ptt)
