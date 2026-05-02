"""
device_bridge.py — Host OS Device Bridges

Each DeviceBridge sits behind a DEVICE Pond and translates between
the array's bus addresses and the host OS.

Architecture
============

    Array bus address → DeviceBridge.tick(bus) → host OS call → result on bus

The bridge is polled each tick or on demand via poll(). When the
array writes a command value to the device's command address, the
bridge executes the corresponding host OS operation and places the
result at the device's output bus address for the array to read.

Bus protocol (32-bit)
=====================

Every device uses the same simple protocol on the array side:

  CMD_ADDR  (32 bits) — command register written by the array
                        0 = idle, non-zero = command code
  DATA_ADDR (32 bits) — payload written by the array (write ops)
  OUT_ADDR  (32 bits) — result read by the array (read ops)
  STATUS_ADDR (8 bits) — 0=idle, 1=ready, 2=busy, 3=error

Command codes per device type are defined in each bridge class.

Built-in bridges
================

  KeyboardBridge  — non-blocking stdin read; produces keycode on OUT_ADDR
  MouseBridge     — pygame mouse events; position, buttons, wheel on OUT_ADDR
  AudioBridge     — STUB: USB audio output (no sim implementation)
  VideoBridge     — STUB: video capture/decode (no sim implementation)
  StorageBridge   — read/write host filesystem files by path handle
  NetworkBridge   — TCP client send/receive via host socket
  ConsoleBridge   — stdout write (simplest; no read)

All extend DeviceBridge. The DeviceManager registers bridges and
drives their tick() calls from the controller loop.

Usage
=====

    from device_bridge import DeviceManager, KeyboardBridge, StorageBridge

    mgr = DeviceManager(controller, shore)
    kb  = mgr.add(KeyboardBridge,  base_address=0x00C00000, name="keyboard")
    ms  = mgr.add(MouseBridge,     base_address=0x00C10000, name="mouse")
    # au  = mgr.add(AudioBridge,   base_address=0x00C20000, name="audio")   # stub
    # vd  = mgr.add(VideoBridge,   base_address=0x00C30000, name="video")   # stub
    sto = mgr.add(StorageBridge,   base_address=0x00D00000, name="storage")

    # In main loop:
    mgr.tick()   # polls all bridges, processes any pending I/O
"""

from __future__ import annotations

import os
import sys
import time
import queue
import socket
import threading
import select
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from controller import ImagoController
    from shore_v2 import ShoreV2


# ── Bus address layout ────────────────────────────────────────────────────────

# Each bridge occupies a fixed window of bus addresses.
# Offsets within the bridge's base_address:
OFFSET_CMD    = 0x00    # 32-bit command register  (array → device)
OFFSET_DATA   = 0x20    # 32-bit data register     (array → device, write ops)
OFFSET_OUT    = 0x40    # 32-bit output register   (device → array, read ops)
OFFSET_STATUS = 0x60    # 8-bit  status register   (device → array)
BRIDGE_WINDOW = 0x80    # total address window per bridge

# Status values
STATUS_IDLE  = 0
STATUS_READY = 1
STATUS_BUSY  = 2
STATUS_ERROR = 3

# Common command codes (device-specific codes start at 0x10)
CMD_IDLE     = 0x00
CMD_RESET    = 0x01
CMD_IDENTIFY = 0x02


# ── DeviceBridge base class ───────────────────────────────────────────────────

class DeviceBridge:
    """
    Base class for all host OS device bridges.

    Subclasses implement:
      _on_command(cmd, data)  — handle a command from the array
      _device_type            — string identifier (e.g. "KEYBOARD")
      _device_description     — human-readable description

    The base class handles the bus protocol: reading CMD_ADDR,
    routing to _on_command(), writing results to OUT_ADDR/STATUS_ADDR.
    """

    _device_type        = "GENERIC"
    _device_description = "Generic device bridge"

    def __init__(self, base_address: int, name: str):
        self.base_address   = base_address
        self.name           = name
        self.cmd_addr       = base_address + OFFSET_CMD
        self.data_addr      = base_address + OFFSET_DATA
        self.out_addr       = base_address + OFFSET_OUT
        self.status_addr    = base_address + OFFSET_STATUS
        self._status        = STATUS_IDLE
        self._last_cmd      = CMD_IDLE
        self._tick_count    = 0
        self._error_count   = 0
        self._connected     = False

        self._open()

    def _open(self) -> None:
        """Open/initialise the host OS resource. Override in subclasses."""
        self._connected = True

    def close(self) -> None:
        """Close the host OS resource. Override in subclasses."""
        self._connected = False

    def tick(self, bus: dict) -> None:
        """
        Called each array tick. Reads CMD_ADDR from the bus, executes
        the command, and places results back on the bus.

        bus: the array's current bus state {address: value}
        """
        self._tick_count += 1

        # Read command from bus
        cmd_bits = self._read_bus_int(bus, self.cmd_addr, 32)
        if cmd_bits == CMD_IDLE:
            self._poll(bus)
            return

        # Execute every non-idle command.
        # Caller resets CMD_ADDR to 0 after each command so the same
        # command is never re-executed on the next tick unintentionally.
        self._last_cmd = cmd_bits
        data_bits = self._read_bus_int(bus, self.data_addr, 32)

        # Set busy
        self._write_bus_int(bus, self.status_addr, STATUS_BUSY, 8)

        try:
            result = self._on_command(cmd_bits, data_bits)
            if result is not None:
                self._write_bus_int(bus, self.out_addr, result, 32)
            self._write_bus_int(bus, self.status_addr, STATUS_READY, 8)
        except Exception as e:
            print(f"[DEVICE:{self.name}] Error on cmd {cmd_bits:#x}: {e}")
            self._error_count += 1
            self._write_bus_int(bus, self.status_addr, STATUS_ERROR, 8)

    def _poll(self, bus: dict) -> None:
        """
        Called each tick when no new command — check for async events
        (e.g. new keyboard input, network data). Override in subclasses.
        """
        pass

    def _on_command(self, cmd: int, data: int) -> Optional[int]:
        """
        Handle a command. Return integer result or None.
        Override in subclasses.
        """
        if cmd == CMD_RESET:
            self.close()
            self._open()
            return 0
        if cmd == CMD_IDENTIFY:
            return hash(self._device_type) & 0xFFFFFFFF
        return None

    def _read_bus_int(self, bus: dict, base: int, bits: int) -> int:
        """Read a multi-bit integer from consecutive bus addresses."""
        result = 0
        for bit in range(bits):
            v = bus.get(base + bit)
            if v:
                val = v[0] if isinstance(v, tuple) else v
                if val:
                    result |= (1 << bit)
        return result

    def _write_bus_int(self, bus: dict, base: int, value: int, bits: int) -> None:
        """Write a multi-bit integer to consecutive bus addresses."""
        for bit in range(bits):
            bus[base + bit] = (value >> bit) & 1

    def status(self) -> dict:
        return {
            "name":        self.name,
            "type":        self._device_type,
            "description": self._device_description,
            "base":        hex(self.base_address),
            "connected":   self._connected,
            "ticks":       self._tick_count,
            "errors":      self._error_count,
            "status":      {0:"IDLE",1:"READY",2:"BUSY",3:"ERROR"}.get(
                               self._status, "?"),
        }

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}('{self.name}' "
                f"@ {hex(self.base_address)} "
                f"{'connected' if self._connected else 'disconnected'})")


# ── KeyboardBridge ────────────────────────────────────────────────────────────

# Keyboard command codes
KB_CMD_READ    = 0x10   # read next keypress → keycode on OUT_ADDR
KB_CMD_POLL    = 0x11   # non-blocking check → 0 if no key, keycode if ready
KB_CMD_FLUSH   = 0x12   # discard all pending keypresses

class KeyboardBridge(DeviceBridge):
    """
    Keyboard device bridge.

    Reads from host stdin in a background thread. Non-blocking from
    the array's perspective — KB_CMD_POLL returns 0 if no key ready,
    keycode if one is waiting. KB_CMD_READ blocks until a key arrives.

    Keycode encoding: ASCII value for printable chars, special codes
    for control keys (Enter=13, Escape=27, Tab=9, etc.).

    The background thread runs as a daemon so it doesn't block exit.
    """

    _device_type        = "KEYBOARD"
    _device_description = "Host stdin keyboard input"

    def _open(self) -> None:
        self._key_queue: queue.Queue = queue.Queue()
        self._running = True
        self._thread  = threading.Thread(
            target=self._read_thread, daemon=True)
        self._thread.start()
        self._connected = True
        print(f"[DEVICE:{self.name}] Keyboard bridge open (stdin)")

    def close(self) -> None:
        self._running = False
        self._connected = False

    def _read_thread(self) -> None:
        """Background thread reads stdin one char at a time."""
        try:
            import tty, termios
            try:
                fd = sys.stdin.fileno()
                old = termios.tcgetattr(fd)
                tty.setraw(fd)
                try:
                    while self._running:
                        r, _, _ = select.select([sys.stdin], [], [], 0.05)
                        if r:
                            ch = sys.stdin.read(1)
                            self._key_queue.put(ord(ch))
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old)
            except Exception:
                # Fallback: line-buffered input (e.g. not a real terminal)
                while self._running:
                    try:
                        r, _, _ = select.select([sys.stdin], [], [], 0.05)
                        if r:
                            line = sys.stdin.readline()
                            for ch in line:
                                self._key_queue.put(ord(ch))
                    except Exception:
                        break
        except ImportError:
            # Windows — termios/tty not available, use line-buffered fallback
            while self._running:
                try:
                    line = sys.stdin.readline()
                    for ch in line:
                        self._key_queue.put(ord(ch))
                except Exception:
                    break
                    time.sleep(0.1)

    def _poll(self, bus: dict) -> None:
        """Push latest keycode to OUT_ADDR if one is waiting."""
        if not self._key_queue.empty():
            try:
                code = self._key_queue.get_nowait()
                self._write_bus_int(bus, self.out_addr, code, 32)
                self._write_bus_int(bus, self.status_addr, STATUS_READY, 8)
            except queue.Empty:
                pass

    def _on_command(self, cmd: int, data: int) -> Optional[int]:
        if cmd == KB_CMD_READ:
            # Block until key available (with timeout)
            try:
                return self._key_queue.get(timeout=5.0)
            except queue.Empty:
                return 0
        if cmd == KB_CMD_POLL:
            try:
                return self._key_queue.get_nowait()
            except queue.Empty:
                return 0
        if cmd == KB_CMD_FLUSH:
            while not self._key_queue.empty():
                try:
                    self._key_queue.get_nowait()
                except queue.Empty:
                    break
            return 0
        return super()._on_command(cmd, data)




# ── MouseBridge ───────────────────────────────────────────────────────────────

# Mouse command codes
MS_CMD_POLL      = 0x20   # non-blocking: returns packed event or 0 if none
MS_CMD_READ      = 0x21   # blocking: wait for next event
MS_CMD_GET_X     = 0x22   # read current X position (0-65535 scaled)
MS_CMD_GET_Y     = 0x23   # read current Y position (0-65535 scaled)
MS_CMD_GET_BTN   = 0x24   # read button state bitmask (bit0=L, bit1=R, bit2=M)
MS_CMD_SET_REL   = 0x25   # switch to relative mode (delta X/Y per event)
MS_CMD_SET_ABS   = 0x26   # switch to absolute mode (scaled X/Y)
MS_CMD_FLUSH     = 0x27   # discard pending events

# Mouse event word (32-bit packed, written to OUT_ADDR on each event):
#   bits 31-24:  event type (0=move, 1=button_down, 2=button_up, 3=wheel)
#   bits 23-16:  button mask / wheel delta
#   bits 15-8:   X delta or absolute X high byte
#   bits  7-0:   Y delta or absolute Y high byte
# Full X/Y available via MS_CMD_GET_X / MS_CMD_GET_Y after event

MS_EVT_MOVE       = 0x00
MS_EVT_BTN_DOWN   = 0x01
MS_EVT_BTN_UP     = 0x02
MS_EVT_WHEEL      = 0x03

MS_BTN_LEFT       = 0x01
MS_BTN_RIGHT      = 0x02
MS_BTN_MIDDLE     = 0x04


class MouseBridge(DeviceBridge):
    """
    Mouse device bridge.

    Reads mouse events from pygame in a background thread. Non-blocking
    from the array's perspective — MS_CMD_POLL returns 0 if no event
    waiting, packed event word if one is ready.

    Requires pygame to be initialised (DisplayPond handles this automatically
    when a display window is open). If pygame is not available or no display
    is open, the bridge runs in stub mode — all polls return 0.

    Event word format (32-bit, written to OUT_ADDR):
      bits 31-24:  event type  (MS_EVT_MOVE, MS_EVT_BTN_DOWN, etc.)
      bits 23-16:  button mask / wheel delta
      bits 15-8:   X component (delta or position high byte)
      bits  7-0:   Y component (delta or position high byte)

    Full position available via MS_CMD_GET_X / MS_CMD_GET_Y.

    Address layout (at base_address):
      base + 0x00:  CMD_ADDR  — write command code here
      base + 0x20:  DATA_ADDR — write command data here
      base + 0x40:  OUT_ADDR  — read event word / position here
      base + 0x60:  STATUS_ADDR — 0=idle, 1=ready, 2=busy, 3=error
    """

    _device_type        = "MOUSE"
    _device_description = "Host mouse input via pygame"

    def _open(self) -> None:
        self._event_queue: queue.Queue = queue.Queue(maxsize=64)
        self._x:     int  = 0
        self._y:     int  = 0
        self._btn:   int  = 0
        self._rel:   bool = False   # False=absolute, True=relative
        self._running     = True
        self._pygame_ok   = False

        # Try to hook into pygame event loop
        try:
            import pygame
            self._pygame_ok = True
        except ImportError:
            pass

        if self._pygame_ok:
            self._thread = threading.Thread(
                target=self._poll_thread, daemon=True)
            self._thread.start()
            self._connected = True
            print(f"[DEVICE:{self.name}] Mouse bridge open (pygame)")
        else:
            self._connected = True
            print(f"[DEVICE:{self.name}] Mouse bridge open (stub — pygame not available)")

    def close(self) -> None:
        self._running    = False
        self._connected  = False

    def _poll_thread(self) -> None:
        """Background thread collects pygame mouse events."""
        import pygame
        while self._running:
            try:
                for event in pygame.event.get([
                    pygame.MOUSEMOTION,
                    pygame.MOUSEBUTTONDOWN,
                    pygame.MOUSEBUTTONUP,
                    pygame.MOUSEWHEEL,
                ]):
                    packed = self._pack_event(event)
                    if packed is not None:
                        if not self._event_queue.full():
                            self._event_queue.put(packed)
            except Exception:
                pass
            time.sleep(0.005)   # 200Hz polling — fast enough for smooth cursor

    def _pack_event(self, event) -> Optional[int]:
        """Pack a pygame event into a 32-bit event word."""
        import pygame
        try:
            if event.type == pygame.MOUSEMOTION:
                self._x, self._y = event.pos
                dx = max(-127, min(127, event.rel[0]))
                dy = max(-127, min(127, event.rel[1]))
                return ((MS_EVT_MOVE << 24) |
                        (self._btn  << 16) |
                        ((dx & 0xFF) << 8) |
                        (dy & 0xFF))

            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._x, self._y = event.pos
                btn_bit = {1: MS_BTN_LEFT, 2: MS_BTN_MIDDLE,
                           3: MS_BTN_RIGHT}.get(event.button, 0)
                self._btn |= btn_bit
                return ((MS_EVT_BTN_DOWN << 24) |
                        (btn_bit         << 16) |
                        ((self._x >> 8)  <<  8) |
                        (self._y >> 8))

            elif event.type == pygame.MOUSEBUTTONUP:
                self._x, self._y = event.pos
                btn_bit = {1: MS_BTN_LEFT, 2: MS_BTN_MIDDLE,
                           3: MS_BTN_RIGHT}.get(event.button, 0)
                self._btn &= ~btn_bit
                return ((MS_EVT_BTN_UP << 24) |
                        (btn_bit       << 16) |
                        ((self._x >> 8) << 8) |
                        (self._y >> 8))

            elif event.type == pygame.MOUSEWHEEL:
                delta = max(-127, min(127, event.y))
                return ((MS_EVT_WHEEL << 24) |
                        ((delta & 0xFF) << 16))
        except Exception:
            pass
        return None

    def _poll(self, bus: dict) -> None:
        """Push latest mouse event to OUT_ADDR if one is waiting."""
        if not self._event_queue.empty():
            try:
                event_word = self._event_queue.get_nowait()
                self._write_bus_int(bus, self.out_addr, event_word, 32)
                self._write_bus_int(bus, self.status_addr, STATUS_READY, 8)
            except queue.Empty:
                pass

    def _on_command(self, cmd: int, data: int) -> Optional[int]:
        if cmd == MS_CMD_POLL:
            try:
                return self._event_queue.get_nowait()
            except queue.Empty:
                return 0

        elif cmd == MS_CMD_GET_X:
            return self._x & 0xFFFF

        elif cmd == MS_CMD_GET_Y:
            return self._y & 0xFFFF

        elif cmd == MS_CMD_GET_BTN:
            return self._btn & 0xFF

        elif cmd == MS_CMD_SET_REL:
            self._rel = bool(data)
            return STATUS_READY

        elif cmd == MS_CMD_SET_ABS:
            self._rel = False
            return STATUS_READY

        elif cmd == MS_CMD_FLUSH:
            while not self._event_queue.empty():
                try: self._event_queue.get_nowait()
                except queue.Empty: break
            return STATUS_READY

        return super()._on_command(cmd, data)


# ── AudioBridge (stub) ────────────────────────────────────────────────────────
#
# STUB ONLY — no simulation implementation.
#
# On real silicon: a USB audio device appears as a PERIPHERAL Pond.
# The cell array streams PCM samples to it at the audio clock rate.
# The bridge forwards samples to the USB audio driver.
#
# Simulation risk: audio streaming in Python alongside a cell array sim
# would require precise timing that the sim cannot guarantee. A 44,100 Hz
# sample rate means a new sample every 22 microseconds — the Python
# interpreter cannot reliably meet this deadline alongside array.tick().
# Real hardware has no such constraint — the audio clock is independent.
#
# When real silicon arrives: a hardware engineer will design the USB
# audio interface. The PERIPHERAL Pond model already supports it.
# The AudioBridge stub below defines the interface for that future work.

AU_CMD_OPEN      = 0x30   # open audio device: data=sample_rate code
AU_CMD_CLOSE     = 0x31   # close audio device
AU_CMD_WRITE     = 0x32   # write PCM sample (16-bit or 24-bit)
AU_CMD_FLUSH     = 0x33   # flush output buffer
AU_CMD_SET_GAIN  = 0x34   # set output gain (0-255)
AU_CMD_STATUS    = 0x35   # read buffer fill level

# Sample rate codes for AU_CMD_OPEN
AU_RATE_44100    = 0x01   # CD quality
AU_RATE_48000    = 0x02   # professional standard
AU_RATE_96000    = 0x03   # high resolution
AU_RATE_192000   = 0x04   # studio master

# Address layout:
#   OUT_ADDR:     buffer level / status after each command
#   DATA_ADDR:    PCM sample value (16-bit or 24-bit, signed)
#   CMD_ADDR:     command code

class AudioBridge(DeviceBridge):
    """
    Audio device bridge — STUB ONLY.

    No simulation implementation. Prints a warning if instantiated.
    All commands return STATUS_ERROR in simulation.

    On real silicon: USB audio device → PERIPHERAL Pond → AudioBridge.
    PCM samples stream from cell array to USB audio driver.
    The audio clock is hardware-independent — no timing constraints
    on the cell array side.

    See device_bridge.py comments for design notes.
    """

    _device_type        = "AUDIO"
    _device_description = "USB audio output (stub — no sim implementation)"

    def _open(self) -> None:
        self._connected = True
        print(f"[DEVICE:{self.name}] AudioBridge is a STUB — "
              f"no audio simulation. Real hardware required.")
        print(f"[DEVICE:{self.name}] For real audio: connect a USB audio "
              f"device. It will appear as a PERIPHERAL Pond.")

    def _poll(self, bus: dict) -> None:
        pass   # stub — no polling

    def _on_command(self, cmd: int, data: int) -> Optional[int]:
        # All commands fail gracefully in simulation
        self._write_bus_int({}, self.status_addr, STATUS_ERROR, 8)
        return STATUS_ERROR


# ── VideoBridge (stub) ────────────────────────────────────────────────────────
#
# STUB ONLY — no simulation implementation.
#
# Video OUTPUT is already handled by DisplayPond — the cell array writes
# pixel values to display cell addresses and the DisplayPond renders them
# to a pygame host window. That IS the video output path.
#
# Video INPUT (capture) and video DECODE are not yet implemented.
#
# Video decode is compute-intensive: DCT, motion compensation, entropy
# coding. These require dedicated tile implementations (DCT tile,
# motion vector tile, etc.) that do not yet exist. When real silicon
# arrives a hardware engineer can design these tiles using the NOR cell
# fabric — the tile library pattern already supports this.
#
# USB video capture: same model as audio — a USB capture device appears
# as a PERIPHERAL Pond. The cell array reads frames from it.
# Not simulated for the same timing reasons as audio.

VD_CMD_OPEN      = 0x40   # open video source: data=format code
VD_CMD_CLOSE     = 0x41   # close video source
VD_CMD_READ      = 0x42   # read next frame (returns frame_id)
VD_CMD_SEEK      = 0x43   # seek to frame N (data=frame number)
VD_CMD_STATUS    = 0x44   # read decode status / buffer level

# Video format codes for VD_CMD_OPEN
VD_FMT_RAW_RGB24 = 0x01   # raw RGB24 — no decode needed, direct to DisplayPond
VD_FMT_H264      = 0x02   # H.264 — requires decode tile (not yet implemented)
VD_FMT_AV1       = 0x03   # AV1   — requires decode tile (not yet implemented)

class VideoBridge(DeviceBridge):
    """
    Video device bridge — STUB ONLY.

    No simulation implementation. Video OUTPUT is handled by DisplayPond.
    Video decode tiles (DCT, motion compensation) are not yet implemented.

    On real silicon: USB video capture → PERIPHERAL Pond → VideoBridge.
    Decoded frames written to a DisplayPond address range.

    Raw RGB24 input (VD_FMT_RAW_RGB24) could be implemented without
    decode tiles — it maps directly to DisplayPond cell addresses.
    This is the only format that could be simulated, but timing
    constraints make it impractical at the Python sim level.
    """

    _device_type        = "VIDEO"
    _device_description = "Video capture (stub — no sim implementation)"

    def _open(self) -> None:
        self._connected = True
        print(f"[DEVICE:{self.name}] VideoBridge is a STUB — "
              f"no video decode simulation. Real hardware required.")
        print(f"[DEVICE:{self.name}] Video OUTPUT: use DisplayPond directly.")
        print(f"[DEVICE:{self.name}] Video DECODE tiles: not yet implemented.")

    def _poll(self, bus: dict) -> None:
        pass   # stub

    def _on_command(self, cmd: int, data: int) -> Optional[int]:
        self._write_bus_int({}, self.status_addr, STATUS_ERROR, 8)
        return STATUS_ERROR


# ── StorageBridge ─────────────────────────────────────────────────────────────

# Storage command codes
ST_CMD_OPEN   = 0x10   # open file: data=handle_id, path set via ST_CMD_SETPATH
ST_CMD_READ   = 0x11   # read next chunk → bytes on OUT_ADDR (chunked 4 bytes)
ST_CMD_WRITE  = 0x12   # write 4 bytes from DATA_ADDR to open file
ST_CMD_CLOSE  = 0x13   # close file handle
ST_CMD_SEEK   = 0x14   # seek to byte position in DATA_ADDR
ST_CMD_SIZE   = 0x15   # return file size in bytes
ST_CMD_SETPATH= 0x16   # set path for next open (stores path char by char)
ST_CMD_EXISTS = 0x17   # check if path exists → 1/0
ST_CMD_DELETE = 0x18   # delete file at current path

class StorageBridge(DeviceBridge):
    """
    Storage device bridge.

    Maps host filesystem files to the array via open/read/write/close
    operations. Up to 8 files open simultaneously (handles 0-7).

    Path setting: call ST_CMD_SETPATH once per character (ASCII code
    in DATA_ADDR), then ST_CMD_OPEN with handle_id in DATA_ADDR.

    This is a direct host filesystem bridge — the array can read and
    write any file accessible to the Python process.
    """

    _device_type        = "STORAGE"
    _device_description = "Host filesystem storage bridge"
    MAX_HANDLES         = 8

    def _open(self) -> None:
        self._handles: dict[int, object] = {}   # handle_id → file object
        self._path_buf: str = ""                 # path being built
        self._connected = True
        print(f"[DEVICE:{self.name}] Storage bridge open")

    def close(self) -> None:
        for fh in self._handles.values():
            try:
                fh.close()
            except Exception:
                pass
        self._handles.clear()
        self._connected = False

    def _on_command(self, cmd: int, data: int) -> Optional[int]:
        if cmd == ST_CMD_SETPATH:
            # Accumulate path string char by char; null char (0) resets buffer
            if data == 0:
                self._path_buf = ""  # explicit reset
            else:
                self._path_buf += chr(data & 0xFF)
            return 0

        if cmd == ST_CMD_OPEN:
            handle_id = data & 0x7
            path = self._path_buf
            self._path_buf = ""   # always clear after use
            try:
                fh = open(path, 'r+b') if os.path.exists(
                    path) else open(path, 'w+b')
                self._handles[handle_id] = fh
                print(f"[DEVICE:{self.name}] Opened handle {handle_id}: "
                      f"'{fh.name}'")
                return handle_id
            except Exception as e:
                print(f"[DEVICE:{self.name}] Open failed: {e}")
                return 0xFF  # error sentinel

        if cmd == ST_CMD_READ:
            handle_id = data & 0x7
            fh = self._handles.get(handle_id)
            if fh is None:
                return 0
            chunk = fh.read(4)
            if not chunk:
                return 0xFFFFFFFF  # EOF
            # Pack up to 4 bytes into a 32-bit int (little-endian)
            val = int.from_bytes(chunk.ljust(4, b'\x00'), 'little')
            return val

        if cmd == ST_CMD_WRITE:
            # data encodes handle (bits 28-31) + 3 bytes payload (bits 0-23)
            handle_id = (data >> 28) & 0x7
            payload   = data & 0x00FFFFFF
            fh = self._handles.get(handle_id)
            if fh is None:
                return 0xFF
            fh.write(payload.to_bytes(3, 'little'))
            return 0

        if cmd == ST_CMD_CLOSE:
            handle_id = data & 0x7
            fh = self._handles.pop(handle_id, None)
            if fh:
                fh.close()
                print(f"[DEVICE:{self.name}] Closed handle {handle_id}")
            return 0

        if cmd == ST_CMD_SEEK:
            # data encodes handle (bits 28-31) + position (bits 0-27)
            handle_id = (data >> 28) & 0x7
            position  = data & 0x0FFFFFFF
            fh = self._handles.get(handle_id)
            if fh:
                fh.seek(position)
            return 0

        if cmd == ST_CMD_SIZE:
            handle_id = data & 0x7
            fh = self._handles.get(handle_id)
            if fh is None:
                return 0
            pos = fh.tell()
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(pos)
            return size & 0xFFFFFFFF

        if cmd == ST_CMD_EXISTS:
            return 1 if os.path.exists(self._path_buf) else 0

        if cmd == ST_CMD_DELETE:
            try:
                os.remove(self._path_buf)
                self._path_buf = ""
                return 0
            except Exception:
                return 0xFF

        return super()._on_command(cmd, data)


# ── NetworkBridge ─────────────────────────────────────────────────────────────

# Network command codes
NET_CMD_CONNECT    = 0x10  # connect to host:port (host set via NET_CMD_SETHOST)
NET_CMD_DISCONNECT = 0x11  # close connection
NET_CMD_SEND       = 0x12  # send 4 bytes from DATA_ADDR
NET_CMD_RECV       = 0x13  # receive up to 4 bytes → OUT_ADDR (0 if none ready)
NET_CMD_SETHOST    = 0x14  # set host char by char (like ST_CMD_SETPATH)
NET_CMD_SETPORT    = 0x15  # set port number in DATA_ADDR
NET_CMD_LISTEN     = 0x16  # listen on port for incoming connection
NET_CMD_ACCEPT     = 0x17  # accept waiting connection → 1 if got one
NET_CMD_STATUS     = 0x18  # → 1 if connected, 0 if not

class NetworkBridge(DeviceBridge):
    """
    Network device bridge.

    TCP client/server via host socket. Supports connect (client) and
    listen/accept (server). Non-blocking receive — NET_CMD_RECV returns
    0 if no data ready.

    One connection at a time per bridge instance. Add multiple
    NetworkBridge instances for multiple connections.
    """

    _device_type        = "NETWORK"
    _device_description = "Host TCP network bridge"

    def _open(self) -> None:
        self._sock:     Optional[socket.socket] = None
        self._server:   Optional[socket.socket] = None
        self._host_buf: str  = ""
        self._port:     int  = 0
        self._recv_buf: bytes = b""
        self._connected = False
        print(f"[DEVICE:{self.name}] Network bridge ready")

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass
            self._server = None
        self._connected = False

    def _poll(self, bus: dict) -> None:
        """Check for incoming data without blocking."""
        if self._sock is None:
            return
        try:
            r, _, _ = select.select([self._sock], [], [], 0)
            if r:
                chunk = self._sock.recv(4)
                if chunk:
                    self._recv_buf += chunk
        except Exception:
            pass

    def _on_command(self, cmd: int, data: int) -> Optional[int]:
        if cmd == NET_CMD_SETHOST:
            if data == 0:
                self._host_buf = ""  # explicit reset
            else:
                self._host_buf += chr(data & 0xFF)
            return 0

        if cmd == NET_CMD_SETPORT:
            self._port = data & 0xFFFF
            return 0

        if cmd == NET_CMD_CONNECT:
            self.close()
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.0)
                s.connect((self._host_buf, self._port))
                s.setblocking(False)
                self._sock = s
                self._connected = True
                self._host_buf = ""
                print(f"[DEVICE:{self.name}] Connected to "
                      f"{self._host_buf or '?'}:{self._port}")
                return 1
            except Exception as e:
                print(f"[DEVICE:{self.name}] Connect failed: {e}")
                return 0

        if cmd == NET_CMD_DISCONNECT:
            self.close()
            return 0

        if cmd == NET_CMD_SEND:
            if self._sock is None:
                return 0xFF
            try:
                payload = data.to_bytes(4, 'little')
                self._sock.sendall(payload)
                return 4
            except Exception as e:
                print(f"[DEVICE:{self.name}] Send error: {e}")
                return 0

        if cmd == NET_CMD_RECV:
            if len(self._recv_buf) >= 4:
                chunk = self._recv_buf[:4]
                self._recv_buf = self._recv_buf[4:]
                return int.from_bytes(chunk, 'little')
            elif self._recv_buf:
                chunk = self._recv_buf.ljust(4, b'\x00')
                self._recv_buf = b""
                return int.from_bytes(chunk, 'little')
            return 0  # no data ready

        if cmd == NET_CMD_LISTEN:
            self.close()
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('', self._port))
                s.listen(1)
                s.setblocking(False)
                self._server = s
                print(f"[DEVICE:{self.name}] Listening on port {self._port}")
                return 1
            except Exception as e:
                print(f"[DEVICE:{self.name}] Listen failed: {e}")
                return 0

        if cmd == NET_CMD_ACCEPT:
            if self._server is None:
                return 0
            try:
                r, _, _ = select.select([self._server], [], [], 0)
                if r:
                    conn, addr = self._server.accept()
                    conn.setblocking(False)
                    self._sock = conn
                    self._connected = True
                    print(f"[DEVICE:{self.name}] Accepted from {addr}")
                    return 1
            except Exception:
                pass
            return 0

        if cmd == NET_CMD_STATUS:
            return 1 if self._connected else 0

        return super()._on_command(cmd, data)


# ── ConsoleBridge ─────────────────────────────────────────────────────────────

CON_CMD_WRITE = 0x10   # write char from DATA_ADDR to stdout
CON_CMD_WRITELN = 0x11 # write char + newline
CON_CMD_FLUSH = 0x12   # flush stdout

class ConsoleBridge(DeviceBridge):
    """
    Console output bridge. Write-only.
    Writes ASCII characters to host stdout.
    Simplest possible device — no input, no buffering complexity.
    """

    _device_type        = "CONSOLE"
    _device_description = "Host stdout console output"

    def _open(self) -> None:
        self._connected = True
        self._line_buf  = ""
        print(f"[DEVICE:{self.name}] Console bridge open (stdout)")

    def close(self) -> None:
        sys.stdout.flush()
        self._connected = False

    def _on_command(self, cmd: int, data: int) -> Optional[int]:
        if cmd == CON_CMD_WRITE:
            ch = chr(data & 0xFF)
            sys.stdout.write(ch)
            sys.stdout.flush()
            return 0
        if cmd == CON_CMD_WRITELN:
            ch = chr(data & 0xFF)
            sys.stdout.write(ch + '\n')
            sys.stdout.flush()
            return 0
        if cmd == CON_CMD_FLUSH:
            sys.stdout.flush()
            return 0
        return super()._on_command(cmd, data)


# ── DeviceManager ─────────────────────────────────────────────────────────────

class DeviceManager:
    """
    Manages all device bridges for one system instance.

    Registers each bridge as a DEVICE Pond with Shore, and drives
    their tick() calls from the main loop.

    Usage:
        mgr = DeviceManager(controller, shore)
        kb  = mgr.add(KeyboardBridge,  base_address=0x00C00000, name="keyboard")
        sto = mgr.add(StorageBridge,   base_address=0x00D00000, name="storage")
        net = mgr.add(NetworkBridge,   base_address=0x00E00000, name="network")
        con = mgr.add(ConsoleBridge,   base_address=0x00F00000, name="console")

        # Each tick:
        mgr.tick(controller.array.bus)
    """

    def __init__(self, controller=None, shore=None):
        self._controller = controller
        self._shore      = shore
        self._bridges:  dict[str, DeviceBridge] = {}

    def add(self, bridge_class, base_address: int,
            name: str, **kwargs) -> DeviceBridge:
        """
        Create and register a device bridge.

        Registers the bridge as a DEVICE Pond with Shore (if available)
        so Cast/Ripple can discover it.
        """
        bridge = bridge_class(base_address=base_address, name=name, **kwargs)
        self._bridges[name] = bridge

        # Register with Shore
        if self._shore is not None:
            from shore_v2 import ShoreEntry
            # device_type stored in parent_pond field (repurposed as type label)
            # capabilities_word low 16 bits = device type hash for mask comparison
            dev_type = getattr(bridge, '_device_type', 'GENERIC')
            self._shore.register(ShoreEntry(
                name              = f"device_{name}",
                resource_type     = "DEVICE",
                local_address     = base_address,
                base_address      = base_address,
                offset            = 0,
                pond_id           = abs(hash(name)) & 0xFFFF,
                ward_state        = "HEALTHY",
                parent_pond       = dev_type,
                capabilities_word = abs(hash(dev_type)) & 0xFFFF,
                view_mask         = 0xFFFFFFFF,
            ))
            print(f"[DEVICE_MGR] '{name}' registered with Shore "
                  f"@ {hex(base_address)}")

        return bridge

    def tick(self, bus: dict) -> None:
        """Poll all bridges. Call each array tick or on demand."""
        for bridge in self._bridges.values():
            if bridge._connected:
                bridge.tick(bus)

    def get(self, name: str) -> Optional[DeviceBridge]:
        return self._bridges.get(name)

    def close_all(self) -> None:
        for bridge in self._bridges.values():
            bridge.close()

    def status(self) -> dict:
        return {name: b.status() for name, b in self._bridges.items()}

    def __repr__(self) -> str:
        names = list(self._bridges.keys())
        return f"DeviceManager({len(names)} devices: {names})"
