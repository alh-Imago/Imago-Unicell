# Imago UniCell — Active TODO
**Last updated: May 2026 (post immediate-items session)**

---

## IMMEDIATE — Unblocked, ready to implement

### iCEBreaker bring-up
- [ ] Full iCEBreaker bring-up sequence — load ICM via icm_loader.py, verify live
      CMD_PRELOAD firmware command (preload_cell() stub in fpga_bridge.py needs wiring)
- [ ] unicell_v3.v testbench: add specific tests for one_shot + loop_back interaction

---

## SHORT TERM — After iCEBreaker validation

### Kintex-7
- [ ] Kintex-7: swap bus_hit → bus_hit_r in timing-critical paths (bus_hit_r now available)
      Add 1 cycle to KS_DEPTH in run_int32_function when targeting Kintex-7
- [ ] PCIe bring-up on Optiplex 9020 (Intel platform, more compatible)
      Try lspci — if card enumerates, install xdma.ko and test unicell_xdma.py
- [ ] unicell_xdma.py info — test against live card once enumerated
- [ ] Kintex-7 top-level skeleton module

### Compiler
- [ ] INT32_MIN/MAX signed overflow boundary — ripple borrow doesn't handle
      INT_MAX vs -1 correctly. Consider KS-based signed comparison instead.
- [ ] load_int32_function: extend to work correctly for single-operand tiles
      (e.g. NOT, bit-shift, mask operations where B is truly independent of A)

---

## MEDIUM TERM — Silicon features

### FPGA / Hardware
- [ ] CMD_PRELOAD in unicell.v firmware — wire preload_cell() in fpga_bridge.py
      Needed for preloaded-A pattern on silicon (currently stub)
- [ ] VM vs silicon diff tool (imago_diff.py)
- [ ] FPGA read-back command in Verilog state machine

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
