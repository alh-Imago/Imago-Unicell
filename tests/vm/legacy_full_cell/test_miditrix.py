#!/usr/bin/env python3
"""
test_miditrix.py — MidiTrix MIDI->LIF front-end (first iteration).

Covers the format (registration, tuning, velocity coding, packing, tonotopy as
topology) and the runner (the tonotopic LIF bank responds to the melody, and the
tile path matches the reference LIFNeuron.step).
"""
import os, sys, math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cell_format import FormatRegistry
import miditrix_lif as demo

passed = failed = 0
fails = []
def check(label, cond):
    global passed, failed
    if cond: passed += 1
    else: failed += 1; fails.append(label)

m = FormatRegistry.get_default().get("MidiTrix")

# ── Format registration ──────────────────────────────────────────────────────
check("MidiTrix is registered", m is not None)
check("MidiTrix name/domain", m.name == "MidiTrix" and m.domain == "MidiTrix")

# ── Tuning: equal temperament, A4 = 440 ──────────────────────────────────────
check("A4 (note 69) = 440 Hz", abs(m.note_to_hz(69) - 440.0) < 1e-9)
check("octave doubles frequency (C5 = 2*C4)", abs(m.note_to_hz(72) - 2 * m.note_to_hz(60)) < 1e-6)
check("a semitone is the 12th root of 2",
      abs((m.note_to_hz(61) / m.note_to_hz(60)) - 2 ** (1 / 12)) < 1e-9)

# ── Tonotopy: frequency is monotonic in pitch (the wiring axis) ──────────────
freqs = [m.note_to_hz(n) for n in range(40, 90)]
check("note->frequency is strictly increasing (tonotopic axis)",
      all(b > a for a, b in zip(freqs, freqs[1:])))

# ── Velocity coding ──────────────────────────────────────────────────────────
check("velocity 0 -> no current", m.velocity_to_current(0) == 0.0)
check("velocity 127 -> full current scale", abs(m.velocity_to_current(127) - m.CURRENT_SCALE) < 1e-12)
check("velocity_to_current is monotonic",
      all(m.velocity_to_current(v) <= m.velocity_to_current(v + 1) for v in range(0, 127)))

# ── Event packing round-trip ─────────────────────────────────────────────────
check("pack/unpack note-on round-trips", m.unpack_event(m.pack_event(60, 100, True)) == (60, 100, True))
check("pack/unpack note-off round-trips", m.unpack_event(m.pack_event(72, 0, False)) == (72, 0, False))

# ── Tonotopy is topology: no MIDI_ROUTE tile; front-end tiles are valid ──────
check("MIDI_GAIN is a valid MidiTrix tile", m.validate_tile("MIDI_GAIN")[0])
check("no MIDI_ROUTE tile (routing is wiring, not an op)", "MIDI_ROUTE" not in m.valid_tiles)
check("a foreign tile (LBM_COLLIDE) is not valid here", not m.validate_tile("LBM_COLLIDE")[0])

# ── Source semantics: produces drive, consumes nothing on the bus ───────────
check("MidiTrix produces input_current", "input_current" in m.produces)
check("MidiTrix is a source (consumes nothing)", m.consumes == {})

# ── Runner: the bank responds, and the tile path matches the reference ──────
pitches = sorted({p for (_, _, p, _) in demo.MELODY})
bank = {p: demo.LIFNeuron(demo.LIFParams(tau_m=20.0, dt=1.0, v_th=1.0, refrac=1)) for p in pitches}
ref  = {p: demo.LIFNeuron(demo.LIFParams(tau_m=20.0, dt=1.0, v_th=1.0, refrac=1)) for p in pitches}
fired = {p: 0 for p in pitches}
mism = 0
for t in range(demo.N_TICKS):
    for p in pitches:
        I = demo.active_current(p, t)
        spk, _ = demo.lif_step_tiled(bank[p], I)
        if spk != ref[p].step(I):
            mism += 1
        fired[p] += spk
check("tile LIF path matches reference LIFNeuron.step over the melody", mism == 0)
check("every note's neuron fired at least once (tonotopic response)",
      all(fired[p] >= 1 for p in pitches))
check("silent neuron stays silent (a note never played does not fire)",
      demo.LIFNeuron(demo.LIFParams()).step(0.0) == 0)

print(f"\nResults: {passed} passed, {failed} failed out of {passed + failed} tests")
if fails:
    print("Failed tests:")
    for f_ in fails:
        print(f"  {f_}")
    sys.exit(1)
print("ALL TESTS PASSED")
