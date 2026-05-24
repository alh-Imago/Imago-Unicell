"""
test_display_pond.py — Display Pond system tests
"""

import os, sys
os.environ['SDL_VIDEODRIVER'] = 'offscreen'
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from display_pond import (
    DisplayConfig, DisplayPond, DisplayController, DisplayWindow,
    PixelFormat, Framebuffer, DeltaCollector, thermal_palette,
)
from unicell_array import UniCellArray

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def check_eq(name, got, expected):
    ok = got == expected
    results.append(("PASS" if ok else "FAIL", name))
    if not ok:
        print(f"  [FAIL] {name}  got={got!r}  expected={expected!r}")
    else:
        print(f"  [PASS] {name}")


def make_array():
    arr = UniCellArray(cell_count=200)
    arr.enforce_emission_limits = False
    return arr


# =============================================================================
print("\n=== DisplayConfig ===\n")
# =============================================================================

cfg = DisplayConfig(width=320, height=240,
                    pixel_format=PixelFormat.GREY8,
                    base_address=0x00F00000)

check_eq("cfg: width",           cfg.width, 320)
check_eq("cfg: height",          cfg.height, 240)
check_eq("cfg: format",          cfg.pixel_format, PixelFormat.GREY8)
check_eq("cfg: cells/pixel",     cfg.cells_per_pixel, 1)
check_eq("cfg: total_cells",     cfg.total_cells, 320*240)
check("cfg: describe",           "320×240" in cfg.describe())
check("cfg: vram_mb > 0",        cfg.vram_mb > 0)

# Pixel addressing
addr = cfg.pixel_address(10, 20)
check("cfg: pixel_address",      addr == cfg.base_address + 20*320 + 10)
x, y, ch = cfg.address_to_pixel(addr)
check_eq("cfg: address_to_pixel x", x, 10)
check_eq("cfg: address_to_pixel y", y, 20)
check_eq("cfg: address_to_pixel ch", ch, 0)

# Address range
check("cfg: base in range",     cfg.base_address in cfg.address_range)
check("cfg: end not in range",  cfg.base_address + cfg.total_cells not in cfg.address_range)

# RGBA32 format
cfg32 = DisplayConfig(width=100, height=100, pixel_format=PixelFormat.RGBA32,
                      base_address=0x01000000)
check_eq("RGBA32: cells/pixel",  cfg32.cells_per_pixel, 4)
check_eq("RGBA32: total_cells",  cfg32.total_cells, 100*100*4)

addr_r = cfg32.pixel_address(5, 3, 0)
addr_g = cfg32.pixel_address(5, 3, 1)
check_eq("RGBA32: R/G address diff", addr_g - addr_r, 1)

# RGB24
cfg24 = DisplayConfig(width=80, height=60, pixel_format=PixelFormat.RGB24,
                      base_address=0x02000000)
check_eq("RGB24: cells/pixel",   cfg24.cells_per_pixel, 3)

# MONO1
cfg1 = DisplayConfig(width=64, height=64, pixel_format=PixelFormat.MONO1,
                     base_address=0x03000000)
check_eq("MONO1: cells/pixel",   cfg1.cells_per_pixel, 1)

# IDX8
cfg8 = DisplayConfig(width=64, height=64, pixel_format=PixelFormat.IDX8,
                     base_address=0x04000000)
check_eq("IDX8: cells/pixel",    cfg8.cells_per_pixel, 1)


# =============================================================================
print("\n=== Thermal palette ===\n")
# =============================================================================

pal = thermal_palette()
check_eq("palette: length",      len(pal), 256)
check_eq("palette: 0 = blue",    pal[0],   (0, 0, 255))
check_eq("palette: 255 = red",   pal[255], (255, 0, 0))
check("palette: 128 = green",    pal[128][1] > 200)
check("palette: monotone R",     pal[255][0] > pal[128][0])


# =============================================================================
print("\n=== Framebuffer ===\n")
# =============================================================================

cfg_fb = DisplayConfig(width=100, height=80, pixel_format=PixelFormat.GREY8,
                       base_address=0x00F00000)
fb = Framebuffer(cfg_fb)

check_eq("fb: shape", fb.array.shape, (80, 100, 3))
check("fb: initial = black", np.all(fb.array == 0))

# Apply delta
dirty = {
    cfg_fb.pixel_address(10, 10): 255,
    cfg_fb.pixel_address(50, 40): 128,
    cfg_fb.pixel_address(99, 79): 64,
}
updated = fb.apply_delta(dirty)
check_eq("fb: updated 3 pixels",  updated, 3)
check_eq("fb: white pixel",       tuple(fb.array[10, 10]), (255, 255, 255))
check_eq("fb: grey pixel",        tuple(fb.array[40, 50]), (128, 128, 128))
check_eq("fb: dark pixel",        tuple(fb.array[79, 99]), (64, 64, 64))

# Out-of-range address is ignored
dirty_bad = {0xDEADBEEF: 255}
updated_bad = fb.apply_delta(dirty_bad)
check_eq("fb: bad addr ignored",   updated_bad, 0)

# Fill
fb.fill(50, 100, 150)
check_eq("fb: fill colour",       tuple(fb.array[0, 0]), (50, 100, 150))

# Thermal fill
vals = np.zeros((80, 100), dtype=np.uint8)
vals[:] = 128   # green zone
fb.fill_thermal(vals)
check("fb: thermal green",        fb.array[0, 0][1] > 200)

# MONO1 format
cfg_mono = DisplayConfig(width=32, height=32, pixel_format=PixelFormat.MONO1,
                          base_address=0x05000000,
                          fg_colour=(255, 255, 0),
                          bg_colour=(0, 0, 50))
fb_mono = Framebuffer(cfg_mono)
check_eq("mono: bg at init",      tuple(fb_mono.array[0, 0]), (0, 0, 50))

dirty_mono = {cfg_mono.pixel_address(5, 5): 1}
fb_mono.apply_delta(dirty_mono)
check_eq("mono: fg on 1",         tuple(fb_mono.array[5, 5]), (255, 255, 0))

dirty_mono0 = {cfg_mono.pixel_address(5, 5): 0}
fb_mono.apply_delta(dirty_mono0)
check_eq("mono: bg on 0",         tuple(fb_mono.array[5, 5]), (0, 0, 50))

# RGB24 format
cfg_rgb = DisplayConfig(width=20, height=20, pixel_format=PixelFormat.RGB24,
                         base_address=0x06000000)
fb_rgb = Framebuffer(cfg_rgb)
dirty_rgb = {
    cfg_rgb.pixel_address(5, 5, 0): 200,
    cfg_rgb.pixel_address(5, 5, 1): 100,
    cfg_rgb.pixel_address(5, 5, 2): 50,
}
fb_rgb.apply_delta(dirty_rgb)
check_eq("RGB24: R channel",      fb_rgb.array[5, 5, 0], 200)
check_eq("RGB24: G channel",      fb_rgb.array[5, 5, 1], 100)
check_eq("RGB24: B channel",      fb_rgb.array[5, 5, 2], 50)


# =============================================================================
print("\n=== DeltaCollector ===\n")
# =============================================================================

cfg_dc = DisplayConfig(width=64, height=64, pixel_format=PixelFormat.GREY8,
                        base_address=0x00A00000)
dc = DeltaCollector(cfg_dc)

# Bus with some display and some non-display entries
bus = {
    cfg_dc.pixel_address(0, 0): (255, 5),    # display, tick 5
    cfg_dc.pixel_address(10, 10): (128, 3),  # display, tick 3
    0xDEADBEEF: (99, 5),                     # NOT display
}

dirty = dc.collect(bus, current_tick=5)
check_eq("dc: 2 display addresses", len(dirty), 2)
check("dc: non-display excluded",   0xDEADBEEF not in dirty)

# Second collection — tick didn't advance, nothing new
dirty2 = dc.collect(bus, current_tick=5)
check_eq("dc: same tick = 0 dirty", len(dirty2), 0)

# Advance tick — new entry
bus[cfg_dc.pixel_address(20, 20)] = (64, 6)
dirty3 = dc.collect(bus, current_tick=6)
check_eq("dc: new tick = 1 dirty",  len(dirty3), 1)

s = dc.stats()
check("dc: stats has frames",       "frames" in s)
check_eq("dc: stats frames = 3",    s["frames"], 3)


# =============================================================================
print("\n=== DisplayPond (headless) ===\n")
# =============================================================================

arr = make_array()
cfg_dp = DisplayConfig(width=64, height=64,
                        pixel_format=PixelFormat.GREY8,
                        base_address=0x00F00000)
dp = DisplayPond("test", arr, "owner", cfg_dp, headless=True)

dp.open()
check("dp: is_open after open",   dp.is_open)

# Write a pixel via write_pixel
dp.write_pixel(10, 10, r=255, tick=1)
check("dp: pixel in bus",
      cfg_dp.pixel_address(10, 10) in arr.bus)

# Tick
updated = dp.tick()
check("dp: tick returns int",     isinstance(updated, int))

s = dp.stats()
check("dp: stats has name",       s["name"] == "test")
check("dp: stats has resolution", "64×64" in s["resolution"])

dp.close()
check("dp: closed",               not dp.is_open)


# =============================================================================
print("\n=== Multiple formats via write_pixel ===\n")
# =============================================================================

arr_rgb = make_array()
cfg_rgb2 = DisplayConfig(width=32, height=32,
                          pixel_format=PixelFormat.RGB24,
                          base_address=0x07000000)
dp_rgb = DisplayPond("rgb_test", arr_rgb, "owner", cfg_rgb2, headless=True)
dp_rgb.open()
dp_rgb.write_pixel(5, 5, r=200, g=100, b=50, tick=1)

# Check all 3 channels in bus
for ch, expected in enumerate([200, 100, 50]):
    addr = cfg_rgb2.pixel_address(5, 5, ch)
    val  = arr_rgb.bus.get(addr)
    if val is not None:
        actual = val[0] if isinstance(val, tuple) else val
        check_eq(f"RGB24 write: ch{ch}", actual, expected)
    else:
        check(f"RGB24 write: ch{ch} in bus", False)

dp_rgb.close()


# =============================================================================
print("\n=== DisplayController ===\n")
# =============================================================================

ctrl = DisplayController()
check_eq("ctrl: initial displays", len(ctrl._ponds), 0)

arr1 = make_array()
dp1 = DisplayPond("win1", arr1, "owner",
                   DisplayConfig(32, 32, PixelFormat.GREY8,
                                 0x00F00000, z_order=0),
                   headless=True)
arr2 = make_array()
dp2 = DisplayPond("win2", arr2, "owner",
                   DisplayConfig(32, 32, PixelFormat.GREY8,
                                 0x01000000, z_order=1),
                   headless=True)

ctrl.register(dp1)
ctrl.register(dp2)
check_eq("ctrl: 2 displays",       len(ctrl._ponds), 2)

# Z-order sorting
check_eq("ctrl: z-order 0 first",  ctrl._ponds[0].name, "win1")
check_eq("ctrl: z-order 1 second", ctrl._ponds[1].name, "win2")

# Tick
summary = ctrl.tick()
check("ctrl: summary has win1",    "win1" in summary)
check("ctrl: summary has win2",    "win2" in summary)

hb = ctrl.heartbeat()
check("ctrl: heartbeat displays",  hb["displays"] == 2)
check("ctrl: heartbeat fps",       "fps" in hb)

ctrl.close_all()
check_eq("ctrl: closed all",       len(ctrl._ponds), 0)


# =============================================================================
print("\n=== Resolution scaling ===\n")
# =============================================================================

resolutions = [
    ("320×240 GREY8",     320,  240,  PixelFormat.GREY8,  1),
    ("1080p RGBA32",     1920, 1080,  PixelFormat.RGBA32,  4),
    ("4K RGB24",         3840, 2160,  PixelFormat.RGB24,   3),
    ("8K GREY8",         7680, 4320,  PixelFormat.GREY8,   1),
]
for name, w, h, fmt, cpp in resolutions:
    cfg_r = DisplayConfig(w, h, fmt, 0x10000000)
    check(f"{name}: total_cells",
          cfg_r.total_cells == w * h * cpp)
    check(f"{name}: vram > 0",
          cfg_r.vram_mb > 0)
    # Verify a pixel round-trip
    addr_t = cfg_r.pixel_address(w//2, h//2)
    x_t, y_t, ch_t = cfg_r.address_to_pixel(addr_t)
    check(f"{name}: pixel round-trip",
          x_t == w//2 and y_t == h//2 and ch_t == 0)


# =============================================================================
print("\n=== Results ===\n")
# =============================================================================

passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed:
    print("\nFailed:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
