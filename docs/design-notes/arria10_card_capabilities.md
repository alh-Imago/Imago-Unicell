# Arria 10 GX660 (10AX066H2F34E2SG) — card capabilities for the HYBRID model

The accurate DSP + BRAM data the hybrid version needs (the prerequisite flagged in the pivot).
Sources: Intel/Altera "Arria 10 Native Floating-Point DSP IP User Guide" (UG-20028, 683759) and
"Arria 10 Core Fabric and General Purpose I/Os Handbook" (683461), Chapter 2 Embedded Memory.
Device resource COUNTS from the last Quartus fit (top_arria10_zone1): 251,680 ALMs, 1,687 DSP,
2,131 M20K RAM blocks, 43,642,880 total block-memory bits, 64 PLLs, 24 HSSI channels.

## DSP BLOCK — as a floating-point unit (the zone->DSP bridge target)

All I/O is 32-bit IEEE-754 single-precision FLOAT. Signals: ax[31:0], ay[31:0], az[31:0] in;
result[31:0] out; chainin[31:0]/chainout[31:0] for block-to-block chaining; accumulate (runtime
1-bit); clk[2:0], ena[2:0], aclr[1:0].

Six operating MODES (the bridge picks one):
- MULTIPLY:            Out = Ay * Az
- ADD/SUB:             Out = Ay ± Ax
- MULTIPLY-ADD:        Out = (Ay*Az) ± chainin  OR  (Ay*Az) ± Ax
- MULTIPLY-ACCUMULATE: Out(t) = Ay*Az ± Out(t-1)  [accumulate=1] ; = Ay*Az [accumulate=0]
                       -> running accumulation, accumulate toggled at RUNTIME.
- VECTOR MODE 1:       (Ay*Az) ± chainin, chainout=Ax  -> chained reductions.
- VECTOR MODE 2:       Out = Ax ± chainin, chainout = Ay*Az.

KEY for the architecture: chainin/chainout let DSP blocks CHAIN block-to-block — a strip of DSPs
does a whole dot-product / sum-of-products internally, results flowing forward without returning to
the fabric. The DSP chain is itself a bridge/backbone (fits the "results flow forward" pattern).
accumulate is a runtime bridge signal (dynamic control, not just static config).

NOTE: this is the FLOATING-POINT DSP guide. The block ALSO has a fixed-point/integer mode (18x19,
27x27 int multiply) covered by a SEPARATE guide (variable-precision DSP) — needed only if a zone
does INTEGER multiply (INT32 models). FP32 math (MIF, fluid dynamics) is fully covered here.

## M20K BRAM — the zone->BRAM bridge target (Handbook ch.2)

Two memory types:
- M20K: 20 Kb (20,480 bits) dedicated blocks. THIS device has 2,131 of them (~42.6 Mb total).
  The main storage/buffer resource for zones.
- MLAB: 640-bit blocks made from LABs (dual-purpose logic). One 32x20 simple-dual-port SRAM per
  MLAB. Ideal for wide-shallow arrays, FIFO buffers, filter delay lines.

M20K width x depth configurations (the port contract a bridge uses):
- Single-port: up to 512-deep at wide widths (512 x N), narrower widths go deeper.
- Simple dual-port: 512x32, 512x40 (and mixed-width variants) — one read port + one write port.
- True dual-port: two independent R/W ports to the same memory (512x-class), supports two writes.
- Modes: single-port, simple dual-port, true dual-port; read-during-write (same-port and
  mixed-port) behaviours documented; byte-enable and parity supported.

So a zone->BRAM bridge picks: block type (M20K for real storage / MLAB for small FIFO), port mode
(single / simple-dual / true-dual), and width x depth (e.g. M20K as 512x40 simple-dual-port). Two
ports on true-dual-port means a zone can read and write concurrently, or two zones can share (one
read, one write) — relevant to inter-zone data handoff via shared BRAM.

## Hybrid modelling implications (VM)
- DSP bridge contract: inputs {ay, az, [ax], [chainin]}, mode selector (6 modes), runtime
  accumulate bit; outputs {result, [chainout]}; all FP32. Chaining = a DSP strip as a reduction.
- BRAM bridge contract: {block_type, port_mode, width, depth, addr, [wr]data, [rd]data}.
  True-dual-port BRAM is a candidate mechanism for inter-zone handoff (shared buffer) — possibly
  cleaner than a data-mux backbone for zone->zone results.
- Both are FREE-STANDING device resources (1,687 DSP + 2,131 M20K, all 0% used in the last fit) —
  bridging to them costs NO cell budget, only the bridge logic itself.
- INTEGER DSP (18x19/27x27) needs the separate variable-precision DSP guide if int-multiply zones
  are required (INT32 models). FP side is complete.
