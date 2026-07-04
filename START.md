# Session Start — Imago UniCell

## Read these first (in order)
```bash
git pull
cat fpga/verilog/unicell64_v3.v                       # GROUND TRUTH — the canonical v3 cell. Verilog logic wins every argument.
cat docs/design-notes/v3_command_contract.md          # verified command contract (opcodes, cmd_bus, cmd_latch map, auth)
cat docs/design-notes/arria10_card_capabilities.md    # DSP (FP+int) + BRAM + chaining specs for the hybrid
cat docs/ARCHITECTURE.md                              # overall scheme + design intent
cat sessions/latest.md                                # current state + recent decisions (most recent at TOP)
cat PLAN.md                                           # what needs doing
```

## GROUND TRUTH
**`fpga/verilog/unicell64_v3.v` is the canonical cell — build everything on it.**
Verilog LOGIC (not comments) wins every argument. But ground truth can have bugs: verify the
Verilog's INTERNAL consistency (does the logic match the field map?), not just contract-vs-Verilog.
Two real bugs and a missing-flags error were found this way (2026-07). The header of unicell64_v3.v
now carries an AUTHORITATIVE FIELD MAP — trust that block, re-verify against logic when in doubt.

Core discipline: sim-first then silicon; smallest-test-first; isolate-the-variable; clone don't
modify proven files; prose over heavy formatting; honest assessment over enthusiasm.

## Canonical v3 stack
- `fpga/verilog/unicell64_v3.v`        — THE cell (ground truth)
- `fpga/verilog/unicell_array64_v3.v`  — array
- `fpga/verilog/unicell_zone64_v3.v`   — zone (pass .DEBUG_SELECT(1) for per-cell readback+bank switch)
- `fpga/verilog/top_arria10_zone1_v3.v`— silicon top (has DEBUG_SELECT(1))
- `fpga/quartus/Unicell-Q-zone1-v3.qsf`— build from THIS (references the v3 top, not the old one)

## Sim (primary verification — testbenches are oracles, not smoke tests)
```bash
cd fpga/verilog
iverilog -o /tmp/t.vvp -g2012 tb_v3_twoslot.v      unicell64_v3.v && vvp /tmp/t.vvp   # 15/15 decoder+compose+auth
iverilog -o /tmp/t.vvp -g2012 tb_v3_auth_relocate.v unicell64_v3.v && vvp /tmp/t.vvp   # 11-bit auth @ [63:53]
iverilog -o /tmp/t.vvp -g2012 tb_v3_bank.v          unicell64_v3.v && vvp /tmp/t.vvp   # op26 bank switch
```
VM tests: `PYTHONPATH=. python3 tests/vm/test_fp_tiles.py` and `tests/vm/test_compiler_int32.py`.

## SILICON — reflash FIRST
Mustang-F100 Arria 10 config is VOLATILE SRAM (PCIe-powered) — any host restart/sleep/PCIe
re-enumeration WIPES it. JTAG IDCODE still enumerates (misleading). Reflash before any quartus_stp test.
- When in doubt, run `fpga/icm64_readstate.tcl` as the KNOWN-GOOD baseline (it authenticates
  correctly, lands config, reads a real latch, and has a cycle-tick snapshot-health check).
- Our test tcl auth framing must MATCH what the bitstream's boot stores (a mismatch = config
  silently auth-rejected — the cause of the long silicon chase; auth GATE works on silicon).
- Debug/readback path (ISSP bridge, DEBUG_SELECT) is a SECURITY DOOR — strip + lock JTAG in production.

## Real fitted numbers (full card, standalone64, 25 cells/zone, Quartus 25.1, 2026-06-28)
- Logic 74% (185,445/251,680 ALMs); 16 zones x 25 = 400 cells; ~4.6% marginal per zone (loaded);
  ~464 ALM/cell. DSP 0/1687, BRAM 0, PLL 0/64, HSSI 0/24 — all hardened silicon IDLE.
- FMAX 56.2 MHz — THE number to watch (>logic%); likely wired-OR-bus-limited; island separation
  should raise it. Card gains packing efficiency when fully loaded (single zone ~6% -> 4.6% loaded).

## Where the project is (2026-07)
Strategic pivot: stop forcing the FPGA to be silicon. TWO versions on a shared foundation:
- PURE-CELL (VM-first, demonstrates the thesis, hosts compiler + Tier-2) — proceeds now.
- HYBRID (card: cells for topology/control, DSP+BRAM for math/storage via bridges) — data prereq
  now closed (see arria10_card_capabilities.md).
Deployment = CAFÉ: 8 cards + 1 SBC (SBC runs host-side ward+PTT; cards compute). Card = a POND
(surfaces via PTT; workbench reads it). BRAM = universal primitive (buffer + PCIe-port + program
store); PCIe DMAs to BRAM direct (no I/O cells). Backpressure = command-cell watchdog freeze (no
interrupts); propagates upstream; keep feedback loops zone-local. Product: uni-lab parallel platform,
EOL GX660 ~£450 café to seed / current GX1150 ~£1050 to sustain (128 models/café).

## NEXT (build order — VM outward, on the v3 ground truth)
1. Re-sync `command_interface.py` to v3 (foundation; verify field-by-field vs the contract doc —
   the VM is stale at v2.3 with wrong auth). Serves BOTH versions.
2. Card-as-Pond VM model (16 zones as PTT entries, health+result).
3. Model DSP/BRAM bridge access in the VM (new capability).
4. Confirm RTL device-portability GX660<->GX1150 (both Arria 10).
5. Fit ONE hybrid cell (confirm cost < 464 ALM) and a test DSP chain (confirm tap/feedback routing).

## Git
```bash
git config user.email "session@imago.local"; git config user.name "Imago Session"
git remote set-url origin https://<PAT>@github.com/alh-Imago/Imago-Unicell.git
git ls-remote   # confirm actual remote state ("ahead N" in status is a false alarm)
```
