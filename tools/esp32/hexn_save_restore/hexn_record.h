// hexn_record.h -- Hex-N guarded record v1 (docs/hex-n/GUARDED_RECORD_v1.md). Plain C++ (no Arduino calls), so the same code is compiled on a PC and tested against tools/hexn_record_v1.py. 1 Nov 2026.
#pragma once
#include <stdint.h>
#define HR_MAGIC 0x4852UL
#define HR_VERSION 1
static inline int hr_cap(int k)  { switch (k) { case 1: case 2: return 256; case 3: return 256; case 4: case 5: return 64; case 6: return 8; case 7: return 64; } return 0; }
static inline int hr_width(int k){ switch (k) { case 1: case 2: case 5: case 7: return 32; case 3: return 6; case 4: return 8; case 6: return 16; } return 0; }
static inline uint32_t hr_sum(const uint32_t* w, int n) { uint32_t s = 0; for (int i = 0; i < n; i++) s += w[i]; return s; }
// pack: rec must have room for n + 4 words; returns n + 4
static inline int hr_pack(int kind, const uint32_t* payload, int n, uint32_t sid, uint32_t* rec) {
  rec[0] = (HR_MAGIC << 16) | ((uint32_t)HR_VERSION << 8) | (uint32_t)kind; rec[1] = ((uint32_t)n << 16) | ((uint32_t)hr_width(kind) << 8); rec[2] = sid;
  for (int i = 0; i < n; i++) rec[3 + i] = payload[i]; rec[3 + n] = hr_sum(rec, 3 + n); return n + 4; }
// verify: 0 ok, 1 bad magic/version/kind, 2 wrong geometry, 3 bad checksum, 4 truncated / too long / stray bits, 5 other structure. want_kind 0 = any.
static inline int hr_verify(const uint32_t* rec, int nw, int want_kind, uint32_t sid) {
  if (nw < 4) return 4;
  int k = (int)(rec[0] & 0xFF);
  if ((rec[0] >> 16) != HR_MAGIC || ((rec[0] >> 8) & 0xFF) != HR_VERSION || hr_cap(k) == 0 || (want_kind != 0 && k != want_kind)) return 1;
  int n = (int)(rec[1] >> 16), wd = hr_width(k);
  if (((rec[1] >> 8) & 0xFF) != (uint32_t)wd || (rec[1] & 0xFF) != 0 || n == 0 || n > hr_cap(k)) return 2;
  if (nw != n + 4) return 4;
  if (hr_sum(rec, n + 3) != rec[n + 3]) return 3;
  if (wd < 32) for (int i = 0; i < n; i++) if (rec[3 + i] >> wd) return 4;
  if (rec[2] != sid) return 5;
  return 0; }
