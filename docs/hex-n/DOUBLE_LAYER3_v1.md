# Double Layer 3: one shared data set, a live front end and a planning front end (30 Oct 2026)

Status: DESIGN ONLY. Nothing here is built, simulated or measured, except the facts marked "measured" or "from the model", which point at the file they come from. Written at Alan's request (30 Oct 2026, 10:37 and 14:10): use Layer 3 twice, one for the current inputs and outputs, one as the predictive model for Layer 4, "using the shared ram sets of data".

## 1. The idea in one paragraph
There is ONE set of remembered data (the snapshot IDs, the moment IDs and the path memory with its weighted followers). Two front ends use it:
- **Live** (A): takes the real inputs, builds moments, learns (the only writer), makes the real choices, receives goals and rewards.
- **Plan** (B): reads the same data on behalf of Layer 4, starting from any history Layer 4 gives it, including histories that have not happened yet. It never writes.

So the "second Layer 3" is not a second copy of the memory. It is a second set of the small private parts (a history cursor and a read port) looking at the same memory.

## 2. What exists today (facts, so the design starts from them)
- **Python model.** Layer 4 already works this way. `l3_cols` in `tools/hexn_connect4_layer4_v1.py` copies the Layer 3 object shallowly, swaps in the history and snapshot it wants, and reads the tables. The tables are shared and untouched. The live Layer 3 keeps learning meanwhile.
- **Staleness result** (`tools/hexn_connect4_stale_v2.py`, 30 Oct, 6 seeds x 100 games, Python, layer 4 only): a planning copy refreshed every game or every 10 games played as well as the live one (0.80 / 0.83 and 0.78 / 0.83 wins, against 0.74 / 0.81 live); a copy frozen for 50 games was about 0.11 lower later on (0.70 against 0.81). So a small lag between A's writes and B's reads is harmless, at least in this game.
- **Learned model can hurt** (`tools/hexn_connect4_stale_v3.py`): against lookahead(2) with 20% random moves an EMPTY model gave 0.98 wins and the live one 0.71 to 0.74. So B's output needs the confidence-blend idea of section 7.
- **The tier** (`rtl/hexn_tier_v8.v`, proven on the Kintex card, key 24 bits, value 24 bits): ONE request at a time (`cmd_valid`, `cmd_we`, `busy`, `done`, `found`, `rdata`). In the model (`tools/hexn_tier_ref_v3.py`) a GET that is not a fast-level hit **promotes** the entry: it is removed from its slower level and inserted into the fast level, which pushes the previous occupant down a level. **So a read changes the tier's layout.** A planner doing thousands of reads per move would keep pushing the live Layer 3's entries out of the fast level.
- **Layer 3 hardware plan** (`docs/hex-n/LAYER3_HW_v1.md`): no Layer 3 RTL exists. The needed read ("walk all followers of a matched context, ranked") is also not built; store v5 returns only the best follower.
- The tier is not yet joined to the core (open item).

## 3. What is shared and what is private

| Part | Shared (one copy) | Live (A) only | Plan (B) only |
|---|---|---|---|
| Snapshot table (value to ID) | yes | adds new entries | reads |
| Moment table | yes | adds new entries | reads |
| Path memory: context to followers with weights | yes (in the tier) | updates weights, adds contexts, forgets | reads |
| Channel latches and the moment builder | | yes | |
| Current history (last L snapshots) | | yes (real) | yes (imagined; see below) |
| Goal, choice, reward, feedback to layer 2 | | yes | |
| History cursor stack | | | yes: one entry per ply of the tree, depth up to the cap (10 in the model) |
| Small read cache keyed by history | | | yes (the model's `cache` dict per move) |

**Single-writer rule:** only A writes. There is then no write-write conflict to solve.

**Imagined history:** B's cursor is pushed with a hypothetical event when the tree goes one ply deeper and popped when it comes back, exactly like the board in Layer 4's search. Nothing is fed into the shared data.

## 4. How the two get at the memory
Proposed, not built.
- A request carries: source (A or B), operation (get or put), key, and a **no-promote** flag.
- B's reads are always no-promote, so they do not reshuffle the tier. This needs a new tier version (clone of `hexn_tier_v8`, not an edit) and a test against the model. The model gets a `get_nopromote` first.
- An arbiter in front of the tier: A has priority (it is the real-time side), B waits in a queue. Requests carry the source tag so answers go back to the right front end.
- Whole-line writes: the tier writes a 576-bit DDR3 line at once, so a reader sees an old or a new line, not a torn one. This is a design requirement to verify, not something tested for two requesters.
- No snapshot or locking for B, because the staleness result says small lag does not matter. If a later game says otherwise, a periodic snapshot (which needs the dump restore, not yet built) is the fallback.

## 5. What B asks for
For each opponent node the planner needs the ranked followers of the history key, longest context first (PPM-style blend, per mask). That is several tier reads per node. **Not measured:** how many reads per node and per move, and the time per read on chip. Needed before sizing anything: the counts from the Python model (reads per planner move), and a cycle count for a tier read in simulation. The only on-card speed so far is the JTAG test rate, about 1,340 steps per second, which says nothing about on-chip speed.

## 6. Open decisions (for Alan)
1. **Shared data (this design) or a real copy.** Shared has zero lag and no extra memory; a copy isolates the two completely but doubles the RAM and needs a sync step.
2. **How a context and its followers sit in a key/value tier.** Options: one key per (context, slot) with the follower and weight in the value; or one key per context with a packed value (limited by 24 bits). Not chosen.
3. **Priority and fairness:** strict A first (B may wait a long time while A is busy) or a small guaranteed share for B.
4. **First target:** the Kintex card (the tier exists and is proven) or the Tang (BSRAM store v5, much smaller, no DDR3).

## 7. Where the "do not trust an unreliable model" idea goes
B's output stage blends the learned reply with a flat spread, weighted by how often A's top prediction has been right (a hit counter kept by A, read by B). This is an idea from the 12:10 row of `HEXN_DESIGN.md`, untested.

## 8. Order of work (proposal)
1. Python: add `get_nopromote` to the tier model; count reads per planner move in Connect Four; run Layer 4 with the shared-data setup and compare with the copy setup.
2. Python: a fixed-point model of the ranked read and of the confidence blend.
3. RTL: tier v9 (clone of v8) with source tag, no-promote flag and the A/B arbiter; testbench and a test that fails when the flag is broken.
4. RTL: the Layer 3 live block (moment builder, store, ranked read); then the plan cursor with its stack.
5. Join to Layer 4's search block (to be specified).
Nothing in 1 to 5 has been started.

## 9. Limits of this document
Designed from the Python model and from the tier's counters and interface only. No timing, no area, no RTL. The staleness and empty-model results are Python results for Layer 4 in Connect Four, 6 seeds, one noise level.
