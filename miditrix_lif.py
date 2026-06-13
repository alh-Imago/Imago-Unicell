#!/usr/bin/env python3
"""
miditrix_lif.py — play a MIDI melody to a tonotopic bank of LIF neurons.

[first iteration]  Demonstrates the MidiTrix front-end: a MIDI event stream
becomes timed input current to a bank of leaky integrate-and-fire neurons, one
per note (tonotopic). Each neuron integrates its note's drive and fires — the
cells respond to the music. The LIF tick itself is the real NeuroTrix tile
composition (lif_step_tiled), cross-checked against the reference LIFNeuron.step.

What this shows (and deliberately does not):
  * notes, velocity, timing -> spikes. Pitch selectivity (tonotopy) and
    intensity (velocity) are visible in the raster: a louder/held note fires
    sooner and more often.
  * NOT timbre / harmony / consonance — those live in the frequency domain and
    need a spectral (FFT / filterbank) front-end, left open by design for
    others to build. note_to_hz() is the tonotopic anchor it would bridge onto.

Tonotopy is topology: pitch -> neuron is the wiring, not a tile (see MidiTrix).
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from cell_format import FormatRegistry
from neurotrix_lif import LIFNeuron, LIFParams
from neurotrix_lif_mif import lif_step_tiled
from fp_tiles import TileLibrary

midi = FormatRegistry.get_default().get("MidiTrix")
lib  = TileLibrary()

# ── A little melody: (start_tick, duration, pitch, velocity) ──────────────────
# C major scale ascending, with a crescendo (rising velocity) to show that
# intensity is coded as firing rate; the final C5 is held longer.
MELODY = [
    (0,  4, 60,  70),   # C4
    (4,  4, 62,  80),   # D4
    (8,  4, 64,  90),   # E4
    (12, 4, 65, 100),   # F4
    (16, 4, 67, 110),   # G4
    (20, 4, 69, 120),   # A4
    (24, 4, 71, 127),   # B4
    (28, 8, 72, 127),   # C5 (held)
]
N_TICKS = 36


def active_current(pitch: int, t: int) -> float:
    """Total MidiTrix drive for `pitch` at tick `t` (summed over sounding notes)."""
    I = 0.0
    for (start, dur, p, vel) in MELODY:
        if p == pitch and start <= t < start + dur:
            I += midi.velocity_to_current(vel)
    return I


def run() -> int:
    pitches = sorted({p for (_, _, p, _) in MELODY})          # tonotopic bank
    params  = LIFParams(tau_m=20.0, dt=1.0, v_th=1.0, refrac=1)
    bank    = {p: LIFNeuron(params) for p in pitches}          # tiled path
    ref     = {p: LIFNeuron(params) for p in pitches}          # reference cross-check

    raster, tile_use = {p: [] for p in pitches}, {}
    max_step_depth = mismatches = 0

    for t in range(N_TICKS):
        for p in pitches:
            I = active_current(p, t)
            spike, region = lif_step_tiled(bank[p], I)
            if spike != ref[p].step(I):
                mismatches += 1
            raster[p].append(spike)
            for name, n in region.tiles.items():
                tile_use[name] = tile_use.get(name, 0) + n
            max_step_depth = max(max_step_depth, region.depth)

    # MIDI front-end critical path: velocity gain (MIF_MUL) then on/off gate (MIF_MUX)
    gain_d = lib.get("MIF_MUL").metadata.pipeline_depth
    gate_d = lib.get("MIF_MUX").metadata.pipeline_depth
    frontend_depth = gain_d + gate_d
    total_depth = frontend_depth + max_step_depth

    print("\u2b21 MidiTrix \u2014 a MIDI melody played to a tonotopic LIF bank  [iteration 1]")
    print("=" * 72)
    print(f"  cross-check vs LIFNeuron.step ({N_TICKS} ticks x {len(pitches)} neurons): "
          f"{'MATCH' if mismatches == 0 else str(mismatches) + ' MISMATCH'}")
    print()
    print("  Spike raster  (\u00b7 silent, | spike) \u2014 piano-roll, high notes on top, tick \u2192")
    for p in sorted(pitches, reverse=True):
        row = "".join("|" if s else "\u00b7" for s in raster[p])
        print(f"    n{p:3} {midi.note_to_hz(p):7.1f}Hz  {row}")
    print()
    print("  Per neuron-update cost (predicted ticks, critical path):")
    print(f"    MIDI front-end  (gain MIF_MUL {gain_d} + gate MIF_MUX {gate_d}) = {frontend_depth}")
    print(f"    LIF step        (NeuroTrix tiles)                            = {max_step_depth}")
    print(f"    total                                                        = {total_depth}")
    print("  Tiles used (aggregate): " + ", ".join(f"{k} x{v}" for k, v in sorted(tile_use.items())))
    print()
    print("  NOTE \u2014 first iteration: notes, velocity, timing only. Timbre, harmony")
    print("  and consonance live in the frequency domain and need a spectral")
    print("  (FFT / filterbank) front-end \u2014 left open by design for others to build.")
    print("  note_to_hz() is the tonotopic anchor that front-end would bridge onto.")
    return mismatches


if __name__ == "__main__":
    mm = run()
    print("\nAll demos passed \u2713" if mm == 0 else f"\nMISMATCH x{mm}")
    sys.exit(0 if mm == 0 else 1)
