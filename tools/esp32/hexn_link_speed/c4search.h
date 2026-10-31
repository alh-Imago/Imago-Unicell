// c4search.h -- small Connect Four alpha-beta search (bitboards), counts nodes. Plain C++: runs on the ESP32 and on a PC.
#pragma once
#include <stdint.h>
struct C4 {
  uint64_t cur = 0, all = 0; uint8_t h[7] = {0,0,0,0,0,0,0}; int plies = 0; uint32_t nodes = 0;
  static uint64_t bot(int c) { return 1ULL << (c * 7); }
  bool can(int c) const { return !(all & (bot(c) << 6)) && h[c] < 6; }
  void play(int c) { cur ^= all; all |= all + bot(c); h[c]++; plies++; }
  void undo(int c) { h[c]--; plies--; uint64_t top = bot(c) << h[c]; all ^= top; cur ^= all; }
  static bool four(uint64_t b) {
    uint64_t m = b & (b >> 7); if (m & (m >> 14)) return true;
    m = b & (b >> 6);  if (m & (m >> 12)) return true;
    m = b & (b >> 8);  if (m & (m >> 16)) return true;
    m = b & (b >> 1);  return (m & (m >> 2)) != 0;
  }
  // value for the side to move: +big win, -big loss, else a centre-weighted piece count
  int eval() const {
    static const int w[7] = {1,2,3,4,3,2,1}; int s = 0; uint64_t mine = cur, theirs = cur ^ all;
    for (int c = 0; c < 7; c++) for (int r = 0; r < 6; r++) { uint64_t b = 1ULL << (c * 7 + r); if (mine & b) s += w[c]; else if (theirs & b) s -= w[c]; }
    return s;
  }
  int negamax(int depth, int alpha, int beta) {
    nodes++;
    if (four(cur ^ all)) return -1000 - depth;      // the side that just moved has four
    if (plies == 42) return 0;
    if (depth == 0) return eval();
    static const int order[7] = {3,2,4,1,5,0,6};
    for (int i = 0; i < 7; i++) { int c = order[i]; if (!can(c)) continue;
      play(c); int v = -negamax(depth - 1, -beta, -alpha); undo(c);
      if (v > alpha) alpha = v; if (alpha >= beta) break; }
    return alpha;
  }
  int best(int depth) { nodes = 0; int bc = -1, bv = -100000; static const int order[7] = {3,2,4,1,5,0,6};
    for (int i = 0; i < 7; i++) { int c = order[i]; if (!can(c)) continue; play(c); int v = -negamax(depth - 1, -100000, 100000); undo(c); if (v > bv) { bv = v; bc = c; } }
    return bc; }
};
