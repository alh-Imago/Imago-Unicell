# v3 Command Contract — AUTHORITATIVE reference (extracted from unicell64_v3.v)

Ground truth: `fpga/verilog/unicell64_v3.v`. Extracted 2026-07-03, verified field-by-field
against the RTL logic (not comments). This supersedes command_interface.py's stale v2.3 header.
The VM re-sync must match THIS exactly. Line numbers are into unicell64_v3.v at extraction time.

## AUTH (the thing the VM had wrong — 3 conflicting stale schemes)

Current v3 auth (VERIFIED, lines 626-641, 722, 776):
- `auth_mask = cmd_latch[63:53]`  — 11-bit, stored in the UPPER latch half.
- `auth_boot = (auth_mask == 0)`  — auth is OPEN while mask is zero (fresh boot).
- `auth_token = cmd_bus[29:19]`   — 11-bit token on the command bus.
- `auth_ok = auth_boot || (auth_token == auth_mask)`.
- Boot-write of mask: `CMD_LOAD_AT`/boot path writes `cmd_latch[63:53] <= cmd_data[30:20]` (11-bit),
  gated by `if (physical_mode)` (BOOT state only).
- `CMD_BOOT_COMMIT` writes `cmd_latch[63:53] <= {3'b0, cmd_data[23:16]}` (8 low bits of the mask;
  upper 3 default 0), sets `input_address <= cmd_data[15:0]`, flips `physical_mode <= 0` → RUN.
  NO auth required in BOOT (cell unconfigured); ignored in RUN.

RETIRED / STALE (must be removed from the VM):
- 8-bit auth at [28:21] (v2.3) — GONE.
- 11-bit auth at [14:4] (v2.2) — GONE.
- These were the drift that made our FPGA tcl auth framing wrong.

## COMMAND BUS wire field map (cmd_bus[31:0]), VERIFIED

- `[7:0]`   cmd_opcode / slot A opcode (line 632) — self-describing; IS the outer case dispatch.
- `[15:8]`  slot B opcode (two-slot decoder, line 800) — optional 2nd methodology.
- `[16]`    B_valid (line 799) — 1 = decode slot B; 0 = ignore.
- `[18]`    arm (line 809) — transient; sets `cmd_latch[22]` (start_flag) on the completing pass.
- `[29:19]` auth_token (11-bit, line 641).
- TRANSIENT wires REMOVED (fixed 2026-07-03, commit 1a6577e): preload_sel[18:17], t_shift_in_en
  [19], t_shift_out_en[20] were LIVE and COLLIDED — [19]/[20] with auth_token bits 0/1 (auth
  tokens silently forced shifts), [18] with arm (arming silently preloaded a_data=0xFFFFFFFF).
  Now: shift = stored methodology only (m_in/out_shift_en); transient preload removed. VM must NOT
  model these transient bits. This was likely part of the silicon auth confusion.
- `[31:30]` spare.

## cmd_latch[63:0] field map (cell state), VERIFIED — COMPLETE (corrected 2026-07-03)

CORRECTION: the earlier version of this map OMITTED the entire status/control flag block
[20:31]. Full map from actual Verilog reads (lines 339-626):

LOWER half [31:0] — identity + status + control flags:
- `[9:0]`   topology (line 339).
- `[10]`    is_command_cell (line 351; set by CMD_TOPO_COMMAND_EMIT / direct write).
- `[20]`    latch_A_dis (line 357) — disable A latch, live value flows through.
- `[21]`    latch_B_dis (line 358) — disable B trigger, stored value rebroadcast.
- `[22]`    start_flag / armed (line 352).
- `[24:23]` dtype (line 359) — NUMERIC / SIGNED / ALPHA / DATETIME.
- `[25]`    invert_out (line 353) — invert computed output.
- `[26]`    latch_in (line 354) — hold a_arrived set, single arrival fires. (Also set/cleared by
           CMD_LATCH_IN_ON/OFF at lines 853/857.)
- `[27]`    priority_f (line 360) — high-priority scheduling.
- `[28]`    trace (line 361) — log every fire to Ward. (Also output as dbg_trace.)
- `[29]`    breakpoint (line 362) — halt array on fire.
- `[30]`    one_shot (line 355) — fire once then disarm.
- `[31]`    loop_back (line 356) — feed computed output back to data_reg.

UPPER half [63:32] — methodology + auth:
- `[39:32]` m_nibble_mask (8-bit, line 368).
- `[40]`    m_mask_en (line 369).
- `[46:41]` m_shift_amt (6-bit: [44:41]=nibble*4, [46:45]=sub-nibble; line 370).
- `[47]`    m_in_shift_en (line 371).
- `[48]`    m_out_shift_en (line 372).
- `[51:49]` m_lane_cut (line 570).
- `[63:53]` auth_mask (11-bit, line 626).

TRULY FREE bits: [11:19] (9 bits, lower — old-auth vacated region + a couple) and [52] (1 bit,
upper). Only 10 free total. NOT 20 (earlier error).

These flags (dtype/invert/latch_in/latch_A_dis/latch_B_dis/priority/trace/breakpoint/one_shot/
loop_back) are written by CMD_RECONFIGURE / boot paths (lines 728-738, 758-768) from cmd_data
[11:22]. The VM MUST model all of them — they are live functionality, not dropped.

## OPCODES (localparams, VERIFIED lines 244-304)

Core:
  CMD_NOP=0, CMD_SET_INPUT_ADDR=2, CMD_SET_OUTPUT_ADDR=3, CMD_RECONFIGURE=4,
  CMD_FREEZE=5, CMD_RELEASE=6, CMD_BOOT_COMMIT=7, CMD_ARRAY_RESET=8, CMD_PING=9,
  CMD_LATCH_IN_ON=10, CMD_LATCH_IN_OFF=11, CMD_MEM_CALL=12, CMD_REARM=13,
  CMD_SET_LOGICAL=14 (compat; use BOOT_COMMIT), CMD_PRELOAD=15 (DEPRECATED),
  CMD_CLEAR_ARRIVED=16, CMD_RESET_CELL=17, CMD_SWAP_AB=18, CMD_CAPTURE_REARM=19,
  CMD_SET_TOPO=20, CMD_SET_INVERT=21, CMD_PRELOAD_HI=22 (DEPRECATED),
  CMD_LOAD_AT=23 (targeted reconfigure, addr_match-gated, auth-verified, per-cell heterogeneous),
  CMD_SET_METHOD=25 (two-slot decoder — but NOTE below).

Methodology opcodes (self-describing, TOP-LEVEL — dispatched directly, NOT under SET_METHOD):
  METH_SET_MASK=30      → cmd_latch[39:32]=data, [40]=1
  METH_SET_SHIFT_IN=31  → cmd_latch[46:41]=data, [47]=1
  METH_SET_SHIFT_OUT=32 → cmd_latch[46:41]=data, [48]=1
  METH_SET_LANE=33      → cmd_latch[51:49]=data
  METH_NONE=0

IMPORTANT (two-slot decoder reality, lines 786-806): the methodology opcodes are their OWN
top-level cases `METH_SET_MASK, METH_SET_SHIFT_IN, METH_SET_SHIFT_OUT, METH_SET_LANE:`. Slot A =
cmd_opcode = cmd_bus[7:0] IS the opcode (no CMD_SET_METHOD wrapper consumed for slot A). Slot B
(cmd_bus[15:8]) is an optional 2nd methodology, applied only if B_valid (cmd_bus[16])=1, guarded so
only methodology opcodes are accepted in B (topology in B = no-op). Both write only [51:32]; NEVER
touch auth [63:53]. Slot-A data from cmd_data[low], slot-B data from cmd_data[high half].

Topology opcodes (cold=armed0 / hot=armed1 pairs, lines 281-304):
  PASS_A 48/49 (topo 0x000), NOT_A 50/51 (0x001), NOR 52/53 (0x004), AND 54/55 (0x007),
  OR 56/57 (0x024), NAND 58/59 (0x027), PASS_B 60/61 (0x02C), XNOR 62/63 (0x03C),
  XOR 64/65 (0x0BC), ZERO 66/67 (0x030), ONE 68/69 (0x0B0), COMMAND_EMIT 70/71 (sets [10]).

CORRECTION (points.md #56, 2026-07-29): the above 12 are the named, single-command-settable
ops (each has a dedicated cold/hot opcode pair). There is a 13th real, decoded topology value
with NO dedicated opcode: `10'h002` = NOT_B (`computed_output`'s case statement, ~line 625),
verified against the same A=0xDEADBEEF/B=0xCAFEBABE vectors the RTL cites. Reachable only via
CMD_LOAD_AT's raw `topology[9:0]` field write (which accepts any 10-bit value), not via a
convenience opcode. Any combinatorics/count of the topology field should use 13, not 12.

## cmd_data payloads (per opcode), VERIFIED

- CMD_BOOT_COMMIT: [15:0]=logical_addr, [23:16]=auth_mask (8 low bits → [63:53]).
- CMD_LOAD_AT (boot): [9:0]=topology, [30:20]=11-bit auth_mask (→[63:53], physical_mode only).
- METH_SET_MASK (slot A): cmd_data[7:0]=mask;  (slot B): cmd_data[23:16]=mask.
- METH_SET_SHIFT_IN/OUT (slot A): cmd_data[5:0]=amt; (slot B): cmd_data[21:16]=amt.
- METH_SET_LANE (slot A): cmd_data[2:0]=lane; (slot B): cmd_data[18:16]=lane.

## VM RE-SYNC CHECKLIST (command_interface.py)
- [ ] Replace all auth encoding with 11-bit token @ cmd_bus[29:19], mask @ cmd_latch[63:53].
- [ ] Remove transient preload_sel[18:17]/shift_sel[19:20] from the wire model.
- [ ] Add slot B[15:8], B_valid[16], arm[18].
- [ ] Add METH_SET_MASK/SHIFT_IN/SHIFT_OUT/LANE (30-33) + their field writes.
- [ ] Methodology opcodes are TOP-LEVEL, self-describing (no SET_METHOD wrapper for slot A).
- [ ] Update CMD_BOOT_COMMIT payload (auth_mask [23:16] → [63:53]).
- [ ] Update header "Ground truth" to unicell64_v3.v (from stale unicell.v v2.3).
- [ ] Verify build_cmd_bus()/decode_cmd_bus() emit this exact wire format.
