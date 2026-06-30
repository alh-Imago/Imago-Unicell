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

## COMPUTED COMMANDS — the fabric can compute its own reconfiguration (safe-by-construction)

Realisation: a command cell takes its latch A and presents it to the command bus. So the command
WORD can be DATA — built by a chain of ordinary data cells before the command cell. The data path
COMPUTES the command; the command cell ISSUES it. This turns the fabric from self-reconfiguring
(fixed/pre-loaded commands) into self-PROGRAMMING (computed/conditional commands): the foundation
for conditional reconfigure, parameterised commands (computed target/topology), adaptive
structures, sentinel countermeasure-deployment, ward reallocation, and neuromorphic PLASTICITY
(compute which connections to change, issue the topology change).

### The security boundary (the body/authority split)
A COMPUTED command is only as trustworthy as the data path that built it — and that path may be
an untrusted user model. So the split:
- DATA PATH supplies ONLY the OPCODE / body (the "what": opcode, target, topology). Inert on its
  own — an opcode without auth does nothing. Safe to compute (a proposal, not an order).
- COMMAND CELL supplies the AUTH + START/ARM FLAGS (the "may"), from its OWN protected credential.
  Stamped on emit. The data path's bits in the auth/flag positions are STRUCTURALLY IGNORED /
  overwritten — the command cell sources those bits from its protected latch, not from latch A.
=> "the data path PROPOSES, the command cell AUTHORISES." A user model can compute any command
body but CANNOT make it execute (can't supply/forge auth or arm it). Forgery impossible BY
CONSTRUCTION (auth/flag bits aren't sourced from the computable latch), not by policy.

### Why it's airtight: the boot-only / run-sealed seal (the SAME invariant as everything else)
The command cell's auth credential is reachable ONLY in BOOT mode (set up at boot), then the
physical->run switch flips and it is SEALED for the life of the boot. In RUN mode there is NO path
to it — not for the data fabric, not for a computed command, not for anything short of a GLOBAL
RESET back to boot. So a live, untrusted, computing fabric cannot forge authority: the credential
it would need to forge is physically unreachable until reboot. Requires (already invariants):
auth latch boot-set + WRITE-ONCE + write-protected in run.

COHERENCE: this needs NO new security mechanism — it rides the SAME boot-only/run-sealed switch
that already protects auth integrity, address uniqueness, and command-cell authority. EVERY
security-critical property in the system rests on this ONE switch (the physical->run transition).
One lock, reused everywhere — far stronger than bespoke locks per property. "Is X safe?" always
reduces to "X's protected state is boot-set and run-sealed -> yes."

This also CONFIRMS the split/widened-auth design is structurally NECESSARY (not just hardening):
auth MUST be in its own write-protected latch separate from latch A, precisely so a computed
command can't carry a computed auth. The two realisations (computed commands + split auth) are
complementary — split auth is what makes computed commands safe.

## PRIVILEGE / WHITELIST as one model with the CAST discovery system (recognised, not new)

The whitelist on the v3 command/reprogram features is the SAME security principle already built
into the CAST/RIPPLE discovery system (cast.py) — "no privilege, no see" — extended from
DISCOVERY to ACTION. One model, two layers:
- DISCOVERY (cast, already built): visibility levels — ANONYMOUS (owner only, invisible to other
  occupants), PRIVATE (owner + known contacts), PUBLIC (all), SILENT (no cast). Rule: "owner
  always knows; other occupants see ONLY what the visibility level allows." = privilege-gated VIEW.
- ACTION (whitelist on v3 features): a fabric-altering action (command emit / reprogram) carries
  the actor's privilege/whitelist; the action call checks the whitelist mask. = privilege-gated
  REACH.
Both fail DARK: no privilege -> no response, indistinguishable from "not there at all" (defeats
reconnaissance — an attacker can't even enumerate what exists). For the fabric this is natural:
"whitelist fail = no match = no response" is the same silence as addressing an empty cell, so
dark-failure falls out of the addressing model, not bolted on.

Unified privilege model (capstone of the security threads):
- ONE mechanism over ALL fabric-altering actions AND discovery — command issuance, reprogramming,
  loading, AND visibility are the same privileged question gated by the same privilege/whitelist.
- DEFAULT-DENY: base level = no commands, no reprogram, no view. Privilege GRANTS bounded
  exceptions (allowlist, not blocklist).
- INHERITED + escalation-proof: an actor's privilege is bounded by its creator's. No actor can
  CREATE above its own level; privilege flows down-or-equal only. Closes escalation.
- APPLIES TO ALL ACTORS uniformly — cells, files (stored command sequences, checked by the LOADER
  as reference monitor at load = the STATIC half), the workbench, and the USER (no trusted-human
  exception). Computed commands are the DYNAMIC half (command-cell auth from the boot-sealed
  credential catches commands that don't exist at load time). Static (loader/file scan) + dynamic
  (command-cell auth) = covers declared AND emergent commands.
- File privilege level must be SIGNATURE/HASH-BOUND so a file can't forge its level.
- Enforced by the SAME boot-only/run-sealed switch as auth/identity: privilege is boot-established,
  cannot be self-elevated in run.

CAVEAT (usability): dark-failure for UNPRIVILEGED actors; sufficiently-privileged / debug contexts
should get INFORMATIVE failure so legitimate development can tell "denied" from "broken" (else the
system is undebuggable for those who should see). Privilege-tiered failure verbosity.

MECHANISM vs POLICY: the gate (one check, default-deny, dark-fail) is the easy part and is
conceptually settled. The PER-LEVEL GRANT POLICY (what each privilege level permits, so the system
is both safe AND usable) is deferred OS-layer work. Separating them is the right structure —
build the gate, tune the policy later without changing the mechanism.
