# Cell v3: three-latch addressing, trigger-push, cross-connection, widened split auth (PROPOSED)

The addressing insight (Alan, after the break) plus the auth-hardening. Converges fusion fix,
sentinel taps, relocatable models, command-cell self-command, and security. PROPOSED — prove on
a NEW CELL VARIANT (clone, never touch proven unicell64) in the SINGLE ZONE, AFTER the adder.

## 1. The reframe: identity is the OUT, not the IN (RTL-confirmed)
Identity/address was being read off the IN; it's actually the OUT (where the cell emits = the
cell's fixed point). Data flows ONE WAY: producer emits at its identity, consumers point their
mutable IN at that identity. Confirmed in unicell64.v line 552:
  addr_match = physical_mode ? (bus_addr==CELL_ID) : (bus_addr==input_address)
and addr_match currently gates BOTH config (LOAD_AT) AND data (input_val) on input_address — the
exact conflation that caused fusion. (CELL_ID already keys physical mode; out default = CELL_ID+1.)

## 2. Three distinct latches/roles (resolves fusion, keeps uniformity)
- **IN latch** — targetable, MUTABLE. What this cell listens to. Free to change; never affects
  identity. Two cells sharing an IN-target do NOT fuse (their identities differ).
- **IDENTITY = CELL_ID** — FIXED, permanent, unique. How config + the boot walk find the cell.
  The boot system walks the OUTS/CELL_IDs (the fixed identities), NOT the mutable INs.
- **PUSH latch (the old out latch, repurposed to "emit address only")** — where the cell emits
  WHEN it emits. Dormant for a normal compute cell (emits at its identity by default); USED by a
  command cell to target where it pushes. Keeps ONE cell type (uniformity/fungibility preserved
  — chose this over a compute/command cell-type SPLIT). 

THE REQUIRED CHANGE: split addr_match into CONFIG-match (keys on CELL_ID/identity) and DATA-match
(keys on mutable input_address). Config targets identity; data targets the listen. Then IN is
fully mutable without moving the cell's logical location; fusion is structurally impossible;
sentinel taps are clean (share a data IN-target, keep distinct identity). Cell stays DUMB +
ABSOLUTE ("I am N, I listen to M"); the LOADER/SAVER do the relative/offset arithmetic (heavy
lifting in software, not silicon). INs are absolute addresses; loader computes offset from root.

## 3. Trigger-push primitive (banked as future, not built)
With the push latch as a general "emit address", a cell can hold a target and PUSH to it ON
CONDITION/TRIGGER. A true primitive — independently serves:
- Sentinel: alert-on-detection. Ward: signal-on-event.
- Sensor: receive signal -> send trigger (clearest, safest use).
- LIF neuron: the SPIKE EMIT ("force the spike rather than waiting"). NB a LIF unit is a ~15-cell
  CLUSTER, not one cell — leak + accumulate are EXTRA cells (temporal integrate-and-leak toward
  threshold is a SEPARATE mechanism still to design; the push gives the emit half only).
That one mechanism serves security alerting, OS signalling, and neural spiking = sign of a true
primitive. AUTHORITY CAVEAT: a cell pushing a COMMAND (vs data) anywhere is powerful; its
authority must be auth-gated (see 4/5).

## 4. The cross-connection (already-confirmed command cell — corrected scope)
A command cell can put data in its a-latch -> COMMAND BUS, and also emit via the DATA BUS;
which bus is selected by the "I am a command cell" flag (else data bus). This = the
fabric-commands-itself mechanism (reconfigure data + its internal AUTH CODE travels with the
command, as designed). NOT an unguarded hole — auth-gated like the host's commands. It IS the
highest-stakes seam (data plane <-> command plane), so: command-emit and the command-cell flag
must be auth-gated >= boot strength; command cells SHOULD be trusted-base-only (ward/Shore/OS,
set at boot) so loaded USER models can't reach the command bus (data plane stays sandboxed).

## 5. Widened, split auth (the hardening)
Current auth = 8-bit token (cmd_bus bits 28:21, matched vs stored auth_mask cmd_latch[18:11]).
Entry condition is "if the authcode is known" -> widen it to raise the bar.
- Command bus has ~15 spare bits; the 2nd methodology half has 12 reserved (banked 20/32 used).
- PLAN: expand auth. The command-bus spare takes part of the wider secret; the SPILLOVER goes
  into the METHOD latch's reserved bits (costs method-latch runway, gains topology/auth latch).
  If splittable into two parts: the command auth stays on the command bus; the methodology gains
  a FEW EXTRA BITS of the secret too -> the overall auth secret EXPANDS across both, command bus
  + method-latch spillover.
- Give auth its OWN latch/lane: validated INDEPENDENTLY (auth checked before the command is
  latched), write-protected SEPARATELY (aligns with the existing write-once-boot-auth invariant),
  sized for security on the command bus without bloating data lanes.
- HONEST SCOPE: widening hardens the SHARED-SECRET gate against GUESSING/brute-force. It does NOT
  fix the LEAKED/extracted-secret case (a wider static secret, once leaked, opens the same door).
  Leak/replay is covered by the EXISTING asymmetric-signature + boot-ROM-fused-key layers
  (security_portability.md) — signatures can't be guessed OR replayed like a static code. So:
  widen as defense-in-depth on layer 1; the asymmetric/key layers remain the deep protection.

## Status / sequencing
PROPOSED, post-adder. Adder confirmed on the CURRENT cell first (its composition proof transfers
unchanged). THEN new cell variant: addr_match split (config=identity, data=listen), push latch =
emit-only, widened split auth, on the SINGLE ZONE (cheap/fast). Trigger-push + LIF-integrator +
whitelist-placement (in-bridge vs side cell) remain deferred sub-questions.
