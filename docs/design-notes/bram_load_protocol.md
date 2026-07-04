# BRAM load protocol — fixed 3-cycle wire format + icmP / icmS split

Status: RTL DONE + sim-proven (`tb_v3_load_done.v`, `tb_v3_three_cycle_load.v`,
commits adding `CMD_LOAD_DONE` and the `CMD_LOAD_AT` bank-2 extension). This
note is the canon reference for the wire format and the file-format split that
follows from it — read before building the BRAM loader FSM or any ICM save/
load tooling.

## Why a fixed cycle count

Deterministic beats variable-length: every cell costs exactly 3 command words
(after one-time SET_TARGET), cycle 3 is ALWAYS the confirm. No "another
methodology or terminator?" parsing. `METH_NONE` (0) pads any methodology slot
a given cell doesn't need — a few no-op bits, cheap at load-time, and it keeps
the BRAM read-back counter in lockstep with the write-target counter with no
length field anywhere in the stream.

## The 3-cycle wire sequence (per cell, after SET_TARGET)

```
SET_TARGET(addr)      — opcode 24 (top-only). Holds this cell's CELL_ID on the
                         address lane for the three words that follow. One-time
                         per cell, not counted as one of the 3 cycles.

CYCLE 1  CMD_LOAD_AT   — opcode 23. Sets topology + all lower-latch control
  (topology +            flags (cmd_data, as before) AND, if cmd_bus[16]=1,
   methodology 1)        one bank-2 methodology: cmd_bus[15:8] = methodology
                         opcode (METH_SET_MASK/SHIFT_IN/SHIFT_OUT/LANE),
                         payload in cmd_data[30:23] (8 bits — the one range
                         LOAD_AT's own payload never uses post-boot; NOT the
                         same offset as CMD_SET_METHOD's slot B, which sits at
                         cmd_data[23:16] because THOSE bits were free instead).
                         Only active when !physical_mode.

CYCLE 2  CMD_SET_METHOD — opcode = whichever METH_SET_* is slot A (self-
  (methodology 2 +        describing, cmd_bus[7:0]). Slot B optional via
   methodology 3)         cmd_bus[16]=1 + cmd_bus[15:8], payload cmd_data[23:16].
                         METH_NONE (0) in either slot = no-op pad.
                         CAVEAT: shift_amount[46:41] is ONE shared register for
                         both shift_in and shift_out — if both enables are set
                         in the same cycle, whichever slot decodes last (slot B)
                         wins the value. Fine if in/out want the same amount;
                         if they must differ, that's two separate cycles (breaks
                         the fixed-3 count for that one cell — flag it in the
                         loader if it ever comes up, not designed for yet).

CYCLE 3  CMD_LOAD_DONE  — opcode 27. config_match+auth gated like CMD_LOAD_AT.
  (finish)                On receipt: cell EMITS one command-bus pulse
                         (cmd_emit_bus/data/valid) at output_address (the
                         "push address", pre-set via SET_OUTPUT_ADDR to point
                         at the loader's write-counter listener), with
                         cmd_bus[17] = 1 (completion flag) and opcode field =
                         CMD_NOP. Also sets cmd_latch[52] (debug-only, readable
                         via the existing dbg_bank/dbg_cmd_latch path).
```

A BRAM-driven loader walks records serially: read SET_TARGET, apply; read
cycle 1, apply; read cycle 2, apply; read cycle 3, apply — then watch for the
completion pulse at the known push address before stepping its write-counter
to the next cell's SET_TARGET. Read-counter still steps on bridge-out
(latency-agnostic, from last session); write-counter now steps on a REAL
per-cell confirm instead of a fixed delay.

## Bit layout — resolved, no new collisions

Alan's request was: bank-1 opcode (8b) / bank-2 opcode (8b) / bank-valid flag
(1b) / auth (11b) / complete flag (1b) / spare (2b). Packed tight in that literal
order, auth lands on `[27:17]` — which eats bit 18, currently `arm` on the
`CMD_SET_METHOD` word (cycle 2 needs auth checked too, so the same word would
need bit 18 to mean both "part of the auth token" and "arm" — the exact
collision pattern that caused the two real bugs fixed earlier this project).

**Resolution: don't move anything that already works.** Auth stays at its
current, tested position `cmd_bus[29:19]` (unchanged). `arm` stays at
`cmd_bus[18]` (unchanged, meaningful only on methodology words). The
completion flag takes the next genuinely free bit: `cmd_bus[17]` — which is
*already* the bit the cell sets in its own emitted confirm pulse (built before
this question came up), so the flag now means the same thing everywhere in the
protocol: bit 17 = completion, incoming or outgoing. Spare stays `[31:30]`.
Net RTL cost: only the `CMD_LOAD_AT` bank-2 extension above was new; `CMD_SET_METHOD`
and `CMD_LOAD_DONE` needed no changes.

## File formats: icmP (pure program) vs icmS (save/state)

Two different things were being asked to share one shape, and pulling them
apart removes the "funkiness" Alan flagged:

- **icmP — pure programming file.** Exactly what the 3-cycle protocol above
  consumes: per cell, `(target, cycle1_word, cycle2_word)` — cmd_latch lower
  (topology) + cmd_latch upper (methodology). This is CONFIGURATION ONLY. It
  has no opinion about what's currently latched in a running cell because
  there isn't a running cell yet — this is what boots one into existence.
  Cycle 3 (LOAD_DONE) is loader protocol, not file content — the loader emits
  it after applying a record, it isn't stored in the file.

- **icmS — save / live-state file.** A snapshot of an ALREADY-RUNNING cell,
  five fields per cell, in the save order Alan specified (this is also the
  restore/load order — same shape read forwards or backwards):
  1. Command latch lower (topology)      — cmd_latch[31:0]
  2. Command latch upper (methodology)   — cmd_latch[63:32]
  3. Watching address (the in-latch)     — input_address
  4. Push address (the out-latch)        — output_address
  5. A-data latch contents                — a_data (current value, not a
                                            compile-time constant — this is
                                            live register state, distinct from
                                            the VM-level `init` preload field
                                            in today's ICM_FORMAT.md, which is
                                            a *designed* starting constant for
                                            preloaded-A pattern cells, not a
                                            captured runtime value)

  icmP's restore path is 3 opcodes (SET_TARGET, LOAD_AT+bank2, SET_METHOD).
  icmS's restore path is those 3 PLUS SET_INPUT_ADDR, SET_OUTPUT_ADDR, and
  CMD_SWAP_AB (opcode 18 — loads a_data directly, `auth_ok`-gated only, NOT
  restricted to physical_mode, confirmed still usable in RUN state) to put the
  A-latch value back. Same target/address-lane addressing throughout.

**Why the overlap with cell-move isn't a smell after all:** icmS is a
serialization of *cell state*, not a file-specific artifact. A save-to-disk
and a live move-to-another-cell are the same content going to two different
sinks — write the 5 fields to a file, or write them directly into a different
physical cell via the same opcodes. That's the "BRAM as universal primitive"
pattern one level up: one state shape, multiple transports. The thing to keep
clean is not merging the two FILE KINDS (icmP stays program-only, icmS stays
state-only) — not avoiding the reuse of icmS's shape for a move, which is a
feature.

**Root+offset stays exactly as already canon (ARCHITECTURE.md "Relocatable
models"):** a saved/moved cell's identity is never stored as a bare absolute
CELL_ID. The saver computes `offset = CELL_ID - model_root` at save time; the
loader/mover computes `CELL_ID = new_root + offset` at restore time. The cell
itself only ever holds an absolute ID — it has no idea it's part of a
relocatable model. This is unchanged by any of the above; the icmS record's
"identity" field is the offset, not the raw ID.

## Deferred (explicitly, per Alan)

- The actual move operation (Ward live migration using icmS end-to-end) —
  next question, not this one.
- Building the icmS Python read/write tooling — the format is specified above;
  the loader (icmP, BRAM-driven, one zone) is the next concrete build target.

## Bug found building the first BRAM loader test (top_arria10_zone1_v3.v)

The `cpu_addr_w` mux in the top-level transport whitelists specific opcodes to
read the held `load_target` (SET_TARGET's latch) instead of `cpu_data[15:0]`.
It listed `CMD_SET_METHOD` (opcode 25) as the cycle-2 opcode — but opcode 25
has **no case match in the v3.1 cell any more** (the collapsed, self-describing
encoding dispatches cycle 2 directly on `METH_SET_MASK/SHIFT_IN/SHIFT_OUT/LANE`,
opcodes 30-33, as `cmd_opcode` itself — see the "Methodology opcodes are
TOP-LEVEL and SELF-DESCRIBING" comment in `unicell64_v3.v`). Opcode 25's entry
was vestigial from an earlier encoding.

Consequence: any real cycle-2 word (opcode 30-33) fell through to the mux's
default (`cpu_data[15:0]`) instead of the held target — silently clobbering
`bus_addr` back toward whatever raw value happened to be in that cycle's
`cmd_data`, the next time cycle 2 ran, for every cell after the first one
loaded in a session. This is exactly the kind of thing sim catches and
diagram-reasoning misses: `tb_bram_loader_v3.v` (loading 3 cells back-to-back
through the real transport) showed cell 0 loading fine, then cell 1's and
cell 2's completion pulses firing on the wrong (stale) address — topology
still landed correctly (cycle 1 ran before the corruption), but the cycle-3
confirm was misattributed to cell 0 twice.

Fixed: added opcodes 30/31/32/33 to the whitelist (load_target), alongside the
existing entries. Kept the harmless opcode-25 entry (costs nothing, opcode 25
is simply never sent by anything real). All six v3 testbenches green after the
fix, including the new BRAM loader test.
