# Imago UniCell — Active TODO
**Last updated: May 2026 (post fp_tiles session)**

---

## IMMEDIATE — Unblocked, ready to implement

### Compiler / IR
- [ ] Compiler IR lowering: target internal NOR gate tree (gate_state bits 0–8)
      rather than multi-cell bus chains for AND/OR/XOR etc.
      Currently correct but inefficient — each binary op uses a separate cell
      when the 9-gate internal tree could handle all in one tick.
      **Note: not blocking anything, correctness first**

- [ ] load(A) / run(B) API separation in run_int32_function
      Currently re-runs Python forward sim on every call even when A is fixed.
      Split into: load_int32_function(src, fn, A) → preloads cells
                  run_int32_function(region_id, B) → injects B, returns result
      Straightforward — region.preloaded_a already carries the data.

- [ ] Remove duplicate make_int32_min / make_int32_max definitions in fp_tiles.py
      Lines 869/901 (unsigned, with carry-in) are shadowed by 1917/1861 (signed).
      Decide which to keep or rename to INT32_MIN_U / INT32_MIN_S.

### iCEBreaker bring-up
- [ ] Full iCEBreaker bring-up sequence — SYNC_WAIT test on 4-cell topology
- [ ] one_shot and loop bits in unicell_v3.v with testbench updates
- [ ] Pre-register bus_hit in array for Kintex-7 fan-out prep

---

## SHORT TERM — After iCEBreaker validation

### Kintex-7
- [ ] Kintex-7 top-level skeleton module
- [ ] PCIe bring-up on Optiplex 9020 (Intel platform, more compatible)
      Try `lspci` — if card enumerates, install xdma.ko and test unicell_xdma.py
- [ ] unicell_xdma.py info — test against live card once enumerated

### Compiler
- [ ] INT32_MIN_S / INT32_MIN_U naming cleanup (fix duplicate definitions first)
- [ ] INT32_MIN/MAX signed overflow boundary — ripple borrow doesn't handle
      INT_MAX vs -1 correctly. Consider KS-based signed comparison instead.

---

## MEDIUM TERM — Silicon features

### FPGA / Hardware
- [ ] VM vs silicon diff tool (imago_diff.py)
- [ ] FPGA read-back command in Verilog state machine
- [ ] Wire thermal sensor to dedicated bus address at bring-up

### Counter / ECC Bridge
- [ ] CMD_DATA_COUNTED (0x0F) — opcode for sequence-tagged data packets
- [ ] Counter cell pattern: SELECT + confirmed-increment + CLEAR feedback
- [ ] NORBuilder: emit_packet_counter(N, base_address) helper

---

## LONG TERM — Deferred

### OS Layer (silicon)
- [ ] Ward as silicon program (~20-30 cells scanning PTT entries)
- [ ] PTT cell word comparison in silicon
- [ ] Shore table in silicon (resident pond)
- [ ] Multiple WORKSPACE ponds per PondManager

### 64-bit Addressing
- [ ] Widen bus_addr/bus_data to 64-bit when silicon arrives

### ASIC Investigation
- [ ] Install OpenLane, run synthesis on unicell.v
- [ ] TinyTapeout area estimate
- [ ] Draft chipIgnite application (Efabless priority)

### INT64 / Future
- [ ] INT64: extend compiler_int32 to 64-bit

---

## SECURITY PROPERTIES (design locked, implementation pending)
- [ ] Cell silently ignores CMD_RECONFIGURE if auth token does not match
- [ ] auth_mask register not readable via any bus operation
- [ ] auth_mask set exactly once and cannot be changed
- [ ] Bridge does not reveal whether it accepted or rejected a transaction
