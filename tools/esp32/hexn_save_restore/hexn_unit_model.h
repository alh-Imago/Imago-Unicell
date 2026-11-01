// hexn_unit_model.h -- C++ model of arith_block_v9 at WIDTH 18 (the block in the Hex-N gated unit), 1 Nov 2026. Plain C++ so it is compiled and tested on a PC against tests/vm/test_arith_block_v9_v1.py's model. Used by the ESP32 sketch to know what the unit SHOULD answer.
#pragma once
#include <stdint.h>
struct UnitModel {
  static const int W = 18; uint32_t M, mode, step, topo, held, armed, total, out, v;
  UnitModel() { M = (1UL << W) - 1; mode = step = topo = held = armed = total = out = v = 0; }
  static int32_t sgn(uint32_t x) { x &= (1UL << W) - 1; return (x >> (W - 1)) ? (int32_t)x - (1L << W) : (int32_t)x; }
  static uint32_t tt(uint32_t t) { switch (t) { case 0x000: return 10; case 0x02C: return 12; case 0x001: return 5; case 0x002: return 3; case 0x004: return 1; case 0x007: return 8; case 0x024: return 14; case 0x027: return 7; case 0x0BC: return 6; case 0x03C: return 9; case 0x030: return 0; case 0x0B0: return 15; } return 10; }
  void config(uint32_t cd) { mode = cd & 7; step = (cd >> 8) & 255; topo = (cd >> 16) & 1023; held = (cd >> 26) & 1; armed = 1; total = 0; out = 0; v = 0; }
  // one clock with a valid word; returns the result (also in out)
  uint32_t word(uint32_t a, uint32_t b) {
    a &= M; b &= M; uint32_t inc = a & 1, dec = (a >> 1) & 1, r = 0, sh = b & 31, sm = (1UL << 18) - 1;
    switch (mode) {
      case 0: r = (a + b) & M; break;
      case 1: r = (a - b) & M; break;
      case 2: r = (sgn(a) >= sgn(b)) ? 1 : 0; break;
      case 3: { int32_t x = sgn(a), y = sgn(b); r = x < y ? 0 : x == y ? 1 : 2; break; }
      case 4: r = (total + ((inc && !dec) ? step : (dec && !inc) ? (uint32_t)(-(int32_t)step) : 0)) & M; break;
      case 5: r = (sh < 32) ? (((a & sm) << sh) & sm) : 0; break;
      case 6: r = (sh < 32) ? ((a & sm) >> sh) : 0; break;
      default: { uint32_t keep = 0; for (int i = 0; i < 8; i++) if ((step >> i) & 1) keep |= 15UL << (4 * i); keep &= M; uint32_t nh = held ? keep : b, t = tt(topo); r = 0;
        for (int i = 0; i < W; i++) r |= ((t >> (2 * ((a >> i) & 1) + ((nh >> i) & 1))) & 1UL) << i; }
    }
    if (mode == 4 && (inc || dec)) total = r;
    out = r; v = armed; return r; }
};
