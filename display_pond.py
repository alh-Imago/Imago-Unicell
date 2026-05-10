"""
display_pond.py — Claudette v1.0 Display System

Maps a region of NOR cells directly to display pixels.
On each frame, only cells that fired since the last frame
update their pixels — delta rendering, not full redraws.

Pixel formats
=============

  MONO1   — 1 cell/pixel, output 0/1 → background/foreground colour
  GREY8   — 1 cell/pixel, output 0-255 → greyscale intensity
  IDX8    — 1 cell/pixel, output 0-255 → 256-colour palette lookup
  RGB16   — 2 cells/pixel, R5G6B5 packed across two cell values
  RGB24   — 3 cells/pixel, one cell per R/G/B channel (0-255 each)
  RGBA32  — 4 cells/pixel, R/G/B/A channels (full compositing)

Cell-to-pixel addressing
========================

  pixel(x, y) → cell addresses starting at:
    base_address + (y * width + x) * cells_per_pixel

  For RGBA32, pixel (3, 7) on a 320-wide display:
    R cell: base + (7*320 + 3)*4 + 0
    G cell: base + (7*320 + 3)*4 + 1
    B cell: base + (7*320 + 3)*4 + 2
    A cell: base + (7*320 + 3)*4 + 3

Delta update
============

  On each display tick:
    1. Collect fired_addresses (cells that wrote to bus this tick)
    2. Intersect with display_address_range
    3. Update only changed pixels in the numpy framebuffer
    4. pygame.surfarray.blit_array() → host window

  On typical frames (5-10% of pixels changing):
    Full 4K RGBA32 = 33M cells × 17 bytes = 564 MB
    Changed cells  = ~330K - 660K addresses per frame
    Delta update   = O(changed) not O(total) — essentially free

Host window
===========

  DisplayWindow wraps a pygame window.
  On your desktop: normal resizable window, title bar, close button.
  In the container: offscreen mode (SDL_VIDEODRIVER=offscreen).
  On real silicon: replace pygame backend with display controller driver.
  The DisplayPond and delta logic are unchanged either way.

Multiple windows
================

  Each DisplayPond is independent — different address range, different window.
  Windows can overlap in z-order (composited by DisplayController).
  A cell can write to multiple display regions simultaneously (BROADCAST flag).
  No coordination needed between windows — they're isolated Ponds.

Usage
=====

  from display_pond import DisplayPond, DisplayConfig, PixelFormat, DisplayWindow

  # Create a 320×240 GREY8 display
  cfg = DisplayConfig(width=320, height=240,
                      pixel_format=PixelFormat.GREY8,
                      base_address=0x00F00000)

  pond = DisplayPond("main_display", array, owner_id="system", config=cfg)
  window = DisplayWindow(cfg, title="Claudette v1.0")

  # Each frame: write values to cell addresses, then update
  array.bus[cfg.pixel_address(100, 100)] = (255, tick)   # white pixel at 100,100
  dirty = pond.collect_dirty(array.bus, last_tick)
  window.update(dirty, array.bus)
  window.flip()
"""

from __future__ import annotations
import imago_log

import os
import time
from dataclasses import dataclass, field
from typing import Optional, Callable

import numpy as np
from pond_types import SCOPE_LOCAL, SCOPE_SHORE, SCOPE_EXTENDED


# ── Pixel formats ─────────────────────────────────────────────────────────────

class PixelFormat:
    MONO1   = "MONO1"    # 1 cell/pixel — 0/1 → bg/fg colour
    GREY8   = "GREY8"    # 1 cell/pixel — 0-255 greyscale
    IDX8    = "IDX8"     # 1 cell/pixel — 0-255 palette index
    RGB16   = "RGB16"    # 2 cells/pixel — R5G6B5
    RGB24   = "RGB24"    # 3 cells/pixel — R8G8B8
    RGBA32  = "RGBA32"   # 4 cells/pixel — R8G8B8A8

    CELLS_PER_PIXEL = {
        MONO1: 1, GREY8: 1, IDX8: 1,
        RGB16: 2, RGB24: 3, RGBA32: 4,
    }

    @classmethod
    def cpp(cls, fmt: str) -> int:
        return cls.CELLS_PER_PIXEL.get(fmt, 1)


# ── Display configuration ─────────────────────────────────────────────────────

@dataclass
class DisplayConfig:
    """
    Complete specification for one display Pond.
    Width × height × cells_per_pixel cells starting at base_address.
    """
    width:         int
    height:        int
    pixel_format:  str  = PixelFormat.GREY8
    base_address:  int  = 0x00F00000
    title:         str  = "Claudette v1.0"
    scale:         int  = 1        # integer upscale for small displays
    z_order:       int  = 0        # compositing order (higher = front)
    # Palette for IDX8 — list of 256 (R,G,B) tuples
    palette:       list = field(default_factory=lambda: _default_palette())
    # MONO1 colours
    bg_colour:     tuple = (0, 0, 0)        # colour for cell output 0
    fg_colour:     tuple = (255, 255, 255)  # colour for cell output 1
    # vsync callback — called each frame with (frame_count, dirty_pixels)
    vsync_cb:      Optional[Callable] = None

    @property
    def cells_per_pixel(self) -> int:
        return PixelFormat.cpp(self.pixel_format)

    @property
    def total_cells(self) -> int:
        return self.width * self.height * self.cells_per_pixel

    @property
    def address_range(self) -> range:
        return range(self.base_address,
                     self.base_address + self.total_cells)

    @property
    def vram_mb(self) -> float:
        return self.total_cells * 17 / (1024 * 1024)

    def pixel_address(self, x: int, y: int, channel: int = 0) -> int:
        """Bus address of pixel (x,y) channel offset."""
        return (self.base_address
                + (y * self.width + x) * self.cells_per_pixel
                + channel)

    def address_to_pixel(self, addr: int) -> tuple:
        """Convert bus address → (x, y, channel)."""
        offset  = addr - self.base_address
        channel = offset % self.cells_per_pixel
        pixel   = offset // self.cells_per_pixel
        y, x    = divmod(pixel, self.width)
        return x, y, channel

    def describe(self) -> str:
        cpp = self.cells_per_pixel
        return (f"{self.width}×{self.height} {self.pixel_format} "
                f"({cpp} cell/px, {self.total_cells:,} cells, "
                f"{self.vram_mb:.1f} MB VRAM)")


def _default_palette() -> list:
    """Default 256-colour palette — greyscale ramp."""
    return [(i, i, i) for i in range(256)]


def thermal_palette() -> list:
    """
    8-bit thermal palette:
      0   = deep blue  (cold)
      64  = cyan
      128 = green
      192 = yellow
      255 = red        (hot)
    """
    pal = []
    for i in range(256):
        if i < 64:        # blue → cyan
            pal.append((0, int(i * 4), 255))
        elif i < 128:     # cyan → green
            pal.append((0, 255, int((127 - i) * 4)))
        elif i < 192:     # green → yellow
            pal.append((int((i - 128) * 4), 255, 0))
        else:             # yellow → red
            pal.append((255, int((255 - i) * 4), 0))
    return pal


# ── Delta collector ───────────────────────────────────────────────────────────

class DeltaCollector:
    """
    Tracks which display cells changed since the last frame.
    Intersects the array bus with the display address range.
    """

    def __init__(self, config: DisplayConfig):
        self._cfg       = config
        self._base      = config.base_address
        self._end       = config.base_address + config.total_cells
        self._last_tick = 0
        self._total_dirty = 0
        self._frame_count = 0

    def collect(self, bus: dict, current_tick: int) -> dict:
        """
        Return {addr: value} for all display addresses that changed
        since last_tick. Updates last_tick to current_tick.
        """
        dirty = {}
        for addr, entry in bus.items():
            if self._base <= addr < self._end:
                val  = entry[0] if isinstance(entry, tuple) else entry
                tick = entry[1] if isinstance(entry, tuple) else 0
                if tick > self._last_tick:
                    dirty[addr] = val

        self._last_tick    = current_tick
        self._total_dirty += len(dirty)
        self._frame_count += 1
        return dirty

    def stats(self) -> dict:
        avg = (self._total_dirty / self._frame_count
               if self._frame_count > 0 else 0)
        return {
            "frames":      self._frame_count,
            "total_dirty": self._total_dirty,
            "avg_dirty":   round(avg, 1),
        }


# ── Framebuffer ───────────────────────────────────────────────────────────────

class Framebuffer:
    """
    numpy array backing the display surface.
    Shape: (height, width, 3) uint8 — RGB for pygame.
    Delta writes update only changed pixels.
    """

    def __init__(self, config: DisplayConfig):
        self._cfg = config
        self._buf = np.zeros(
            (config.height, config.width, 3), dtype=np.uint8)
        # Pre-fill MONO1 with background colour
        if config.pixel_format == PixelFormat.MONO1:
            self._buf[:] = config.bg_colour

    def apply_delta(self, dirty: dict) -> int:
        """
        Apply delta {addr: value} to the framebuffer.
        Returns count of pixels actually updated.
        """
        cfg   = self._cfg
        fmt   = cfg.pixel_format
        buf   = self._buf
        updated = 0

        for addr, val in dirty.items():
            x, y, ch = cfg.address_to_pixel(addr)
            if not (0 <= x < cfg.width and 0 <= y < cfg.height):
                continue

            val = int(val) & 0xFF   # clamp to byte

            if fmt == PixelFormat.MONO1:
                colour = cfg.fg_colour if val else cfg.bg_colour
                buf[y, x] = colour
                updated += 1

            elif fmt == PixelFormat.GREY8:
                buf[y, x] = (val, val, val)
                updated += 1

            elif fmt == PixelFormat.IDX8:
                idx = val % 256
                r, g, b = cfg.palette[idx]
                buf[y, x] = (r, g, b)
                updated += 1

            elif fmt == PixelFormat.RGB16:
                # R5G6B5: ch=0 → low byte, ch=1 → high byte
                # Reconstruct 16-bit value from two cell outputs
                if ch == 0:
                    # Store low byte; pixel drawn when high byte arrives
                    # For now treat val as R channel approximation
                    buf[y, x, 0] = (val & 0x1F) << 3   # R5
                    buf[y, x, 1] = ((val >> 5) & 0x7) << 5   # G3 low
                else:
                    buf[y, x, 1] |= (val & 0x7) << 2   # G3 high
                    buf[y, x, 2] = (val >> 3) << 3      # B5
                updated += 1

            elif fmt == PixelFormat.RGB24:
                # ch 0=R, 1=G, 2=B
                buf[y, x, ch % 3] = val
                updated += 1

            elif fmt == PixelFormat.RGBA32:
                # ch 0=R, 1=G, 2=B, 3=A (alpha blended against black)
                if ch < 3:
                    buf[y, x, ch] = val
                else:
                    # Apply alpha: composite against black background
                    alpha = val / 255.0
                    buf[y, x] = (buf[y, x] * alpha).astype(np.uint8)
                updated += 1

        return updated

    def fill(self, r: int = 0, g: int = 0, b: int = 0) -> None:
        """Fill entire framebuffer with a colour."""
        self._buf[:] = (r, g, b)

    def fill_thermal(self, values: np.ndarray) -> None:
        """
        Fill from a 2D numpy array of 0-255 thermal values using
        the thermal palette. values.shape = (height, width).
        """
        pal = np.array(thermal_palette(), dtype=np.uint8)
        idx = np.clip(values, 0, 255).astype(np.uint8)
        self._buf[:] = pal[idx]

    @property
    def array(self) -> np.ndarray:
        return self._buf


# ── DisplayWindow ─────────────────────────────────────────────────────────────

class DisplayWindow:
    """
    Host OS window backed by pygame.
    Receives delta updates from the Framebuffer and blits to screen.

    On desktop: real window with title bar, close button, resize.
    In container: offscreen (SDL_VIDEODRIVER=offscreen auto-detected).
    On silicon: replace with display controller driver — same interface.
    """

    def __init__(self, config: DisplayConfig, headless: bool = False):
        self._cfg      = config
        self._headless = headless or (os.environ.get('SDL_VIDEODRIVER') == 'offscreen')
        self._open     = False
        self._screen   = None
        self._surface  = None
        self._fb       = Framebuffer(config)
        self._delta    = DeltaCollector(config)
        self._frame    = 0
        self._t_open   = 0.0
        self._fps_samples: list = []

        # Scaled window dimensions
        self._win_w = config.width  * config.scale
        self._win_h = config.height * config.scale

    def open(self) -> None:
        """Open the host window."""
        if self._open:
            return

        if not self._headless:
            # Only set offscreen if no display available
            try:
                import pygame
                pygame.init()
                self._screen = pygame.display.set_mode(
                    (self._win_w, self._win_h),
                    pygame.RESIZABLE)
                pygame.display.set_caption(self._cfg.title)
            except Exception:
                self._headless = True

        if self._headless:
            os.environ.setdefault('SDL_VIDEODRIVER', 'offscreen')
            import pygame
            pygame.init()
            self._screen = pygame.display.set_mode(
                (self._win_w, self._win_h))

        import pygame
        self._surface = pygame.Surface((self._cfg.width, self._cfg.height))
        self._open    = True
        self._t_open  = time.perf_counter()
        imago_log.info(f"[DISPLAY] '{self._cfg.title}' opened — "
              f"{self._cfg.describe()}"
              + (" [headless]" if self._headless else ""))

    def close(self) -> None:
        """Close the host window."""
        if self._open:
            import pygame
            pygame.display.quit()
            self._open = False
            imago_log.info(f"[DISPLAY] '{self._cfg.title}' closed — "
                  f"{self._frame} frames, "
                  f"{self.fps():.1f} avg fps")

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    # ── Frame update ─────────────────────────────────────────────────────────

    def tick(self, bus: dict, current_tick: int) -> int:
        """
        Full frame update cycle:
          1. Collect dirty cells from bus
          2. Apply delta to framebuffer
          3. Blit to screen
          4. Call vsync callback if set
          5. Process host window events

        Returns count of dirty pixels updated.
        """
        if not self._open:
            self.open()

        dirty   = self._delta.collect(bus, current_tick)
        updated = self._fb.apply_delta(dirty)
        self._blit()
        self._frame += 1

        if self._cfg.vsync_cb:
            self._cfg.vsync_cb(self._frame, updated)

        self._handle_events()
        return updated

    def update_direct(self, pixel_array: np.ndarray) -> None:
        """
        Direct full-frame update from a numpy array.
        Shape must be (height, width, 3) uint8.
        Used for thermal visualiser and test patterns.
        """
        if not self._open:
            self.open()
        np.copyto(self._fb.array, pixel_array)
        self._blit()
        self._frame += 1
        self._handle_events()

    def fill(self, r: int = 0, g: int = 0, b: int = 0) -> None:
        """Fill display with solid colour."""
        self._fb.fill(r, g, b)
        self._blit()
        self._frame += 1

    def _blit(self) -> None:
        """Blit framebuffer to screen."""
        import pygame
        pygame.surfarray.blit_array(
            self._surface,
            self._fb.array.swapaxes(0, 1))  # pygame is (w,h), numpy is (h,w)

        if self._cfg.scale == 1:
            self._screen.blit(self._surface, (0, 0))
        else:
            scaled = pygame.transform.scale(
                self._surface, (self._win_w, self._win_h))
            self._screen.blit(scaled, (0, 0))

        pygame.display.flip()

    def _handle_events(self) -> None:
        """Process host window events (close button, resize, etc.)."""
        import pygame
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._open = False
            elif event.type == pygame.VIDEORESIZE:
                self._win_w = event.w
                self._win_h = event.h
                self._screen = pygame.display.set_mode(
                    (self._win_w, self._win_h), pygame.RESIZABLE)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def fps(self) -> float:
        elapsed = time.perf_counter() - self._t_open
        return self._frame / elapsed if elapsed > 0 else 0.0

    def stats(self) -> dict:
        return {
            "frame":       self._frame,
            "fps":         round(self.fps(), 1),
            "delta":       self._delta.stats(),
            "open":        self._open,
            "headless":    self._headless,
            "format":      self._cfg.pixel_format,
            "resolution":  f"{self._cfg.width}×{self._cfg.height}",
        }

    @property
    def is_open(self) -> bool:
        return self._open

    @property
    def framebuffer(self) -> Framebuffer:
        return self._fb


# ── DisplayPond ───────────────────────────────────────────────────────────────

class DisplayPond:
    """
    A Pond whose cell address space maps directly to display pixels.

    Extends the standard Pond concept:
    - cells at base_address through base_address+total_cells ARE the pixels
    - writing to those bus addresses updates the display
    - no separate framebuffer, no copy, no DMA on silicon

    For the simulator: wraps a DisplayWindow for host display.
    On silicon: the cell output lines drive the display controller.
    """

    def __init__(self,
                 name:        str,
                 array,                   # UniCellArray
                 owner_id:    str,
                 config:      DisplayConfig,
                 headless:    bool = False,
                 scope:       str  = SCOPE_SHORE,
                 object_id:   int  = 0):
        self.name        = name
        self._array      = array
        self.owner_id    = owner_id
        self.config      = config
        # DisplayPond is a SHORE object by default — visible card-wide
        # object_id assigned by ShoreKeeper at registration
        self.scope       = scope
        self.object_id   = object_id
        self._window     = DisplayWindow(config, headless=headless)
        self._tick_count = 0
        self._last_array_tick = 0

        imago_log.info(f"[DISPLAY_POND] '{name}' created — {config.describe()}")

    def open(self) -> None:
        """Open the host display window."""
        self._window.open()

    def close(self) -> None:
        """Close the host display window."""
        self._window.close()

    def tick(self) -> int:
        """
        Advance the display by one frame.
        Collects dirty cells from the array bus and updates the window.
        Returns count of pixels updated.
        """
        self._tick_count += 1
        current_tick = getattr(self._array, '_tick_count', self._tick_count)
        updated = self._window.tick(self._array.bus, current_tick)
        self._last_array_tick = current_tick
        return updated

    def write_pixel(self, x: int, y: int,
                    r: int = 255, g: int = 255, b: int = 255,
                    tick: int = 1) -> None:
        """
        Directly write a pixel to the array bus.
        Simulates a cell firing and writing its output to the display address.
        """
        cfg = self.config
        fmt = cfg.pixel_format

        if fmt in (PixelFormat.GREY8, PixelFormat.MONO1, PixelFormat.IDX8):
            addr = cfg.pixel_address(x, y)
            self._array.bus[addr] = (r, tick)

        elif fmt == PixelFormat.RGB24:
            for ch, val in enumerate([r, g, b]):
                addr = cfg.pixel_address(x, y, ch)
                self._array.bus[addr] = (val, tick)

        elif fmt == PixelFormat.RGBA32:
            for ch, val in enumerate([r, g, b, 255]):
                addr = cfg.pixel_address(x, y, ch)
                self._array.bus[addr] = (val, tick)

    def fill(self, r: int = 0, g: int = 0, b: int = 0) -> None:
        """Fill entire display with a colour."""
        self._window.fill(r, g, b)

    def thermal_view(self, values: np.ndarray) -> None:
        """
        Render a thermal heatmap directly from a 2D numpy array.
        values.shape = (height, width), values range 0-255.
        Uses the thermal palette (blue=cold → red=hot).
        """
        self._window.framebuffer.fill_thermal(values)
        self._window._blit()

    @property
    def is_open(self) -> bool:
        return self._window.is_open

    def stats(self) -> dict:
        s = self._window.stats()
        s["name"] = self.name
        s["total_cells"] = self.config.total_cells
        return s

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()


# ── DisplayController ─────────────────────────────────────────────────────────

class DisplayController:
    """
    Manages multiple DisplayPonds, composited in z-order.
    Called each vsync tick; updates all registered displays.
    Reports to ShoreKeeper as a monitoring-aware component.
    """

    def __init__(self):
        self._ponds:    list = []   # sorted by z_order
        self._tick      = 0
        self._frame     = 0
        self._t_start   = time.perf_counter()

    def register(self, pond: DisplayPond) -> None:
        """Register a DisplayPond with this controller."""
        self._ponds.append(pond)
        self._ponds.sort(key=lambda p: p.config.z_order)
        if not pond.is_open:
            pond.open()
        imago_log.info(f"[DISPLAY_CTRL] Registered '{pond.name}' "
              f"z={pond.config.z_order}")

    def unregister(self, pond: DisplayPond) -> None:
        """Remove a DisplayPond."""
        if pond in self._ponds:
            self._ponds.remove(pond)
            pond.close()

    def tick(self, array_tick: int = 0) -> dict:
        """
        Advance all displays by one frame.
        Returns {pond_name: dirty_pixels} summary.
        """
        self._tick  = array_tick or self._tick + 1
        self._frame += 1
        summary = {}
        for pond in self._ponds:
            if pond.is_open:
                updated = pond.tick()
                summary[pond.name] = updated
        return summary

    def close_all(self) -> None:
        for pond in list(self._ponds):
            pond.close()
        self._ponds.clear()

    def fps(self) -> float:
        elapsed = time.perf_counter() - self._t_start
        return self._frame / elapsed if elapsed > 0 else 0.0

    def heartbeat(self) -> dict:
        """Compact status for ShoreKeeper reporting."""
        return {
            "displays":    len(self._ponds),
            "frame":       self._frame,
            "fps":         round(self.fps(), 1),
            "display_stats": {p.name: p.stats() for p in self._ponds},
        }

    def __repr__(self) -> str:
        return f"DisplayController({len(self._ponds)} displays, frame={self._frame})"
