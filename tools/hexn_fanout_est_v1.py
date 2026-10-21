"""Hex-N fan-out on a HEX GRID: an ESTIMATE by counting, not a layout and not a measurement. Usage: hexn_fanout_est_v1.py [K NB ...]  (prints a table for the usual sizes).
Facts used (from the cell): a face has 4 lanes, so one link between two neighbouring cells carries 4 wires; a cell has 6 faces. A detector with NB input wires therefore needs G = ceil(NB/4) input faces, plus 1 face for its output: G + 1 <= 6, so NB <= 20.
Assumptions (NOT checked by a layout): the NB wires are split into G groups of 4; each group needs to reach every one of the K detectors; a relay cell receives a group on one face and repeats it on up to 5 other faces (fan-out 5); a detector takes each of its G groups from a
different neighbouring relay. Lower bound on relays = G * ceil(K / 5) (every relay serves at most 5 detectors); the real number depends on the geometry and is likely higher, plus the relays that feed the relays.
Relay cost: (a) a purpose-built repeater (4 flip-flops, no logic: assumed 4 slots) or (b) a full hexn_cell_v2 used as a relay (about 1,500 slots on Gowin: 1,238-1,245 LUT4 + 257-261 ALU, measured).  Detector slots: measured hexn_det_v2 (LUT4 + ALU) 185 / 263 / 307 for 12 / 18 / 20 wires."""
import sys, math
DET = {12: 150 + 35, 18: 224 + 39, 20: 268 + 39}; FULL = 1500; REP = 4
def row(K, NB):
    G = math.ceil(NB / 4); assert G + 1 <= 6, "more than 20 wires does not fit the 6 faces"
    relays = G * math.ceil(K / 5); det = DET.get(NB, 185 + (NB - 12) * 15)
    return G, relays, K * det, relays * REP, relays * FULL
print("%-4s %-4s %-3s %-8s %-14s %-22s %-22s" % ("K", "NB", "G", "relays", "detectors", "relays as repeaters", "relays as full cells"))
cases = [(int(a), int(b)) for a, b in zip(sys.argv[1::2], sys.argv[2::2])] or [(4, 12), (8, 12), (16, 12), (8, 20), (16, 20)]
for K, NB in cases:
    G, rl, dt, rr, rf = row(K, NB)
    print("%-4d %-4d %-3d %-8d %-14d %-22s %-22s" % (K, NB, G, rl, dt, "%d slots (+%.1f%%)" % (rr, 100 * rr / dt), "%d slots (+%.0f%%)" % (rf, 100 * rf / dt)))
