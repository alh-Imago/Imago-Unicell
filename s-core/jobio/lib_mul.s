# Multiply library (ledger #1582).  lib_mul32: a0 = (a0 * a1) mod 2^32, by shift and add (the software path: it works on every build).
# Touches ONLY a0, a1, t0 and t1, like the functions in lib_io.s, so a job keeps its state in t2..t6 / a2..a7 across the call.  The loop runs once per bit of a1
# (so put the number with fewer bits in a1 when you can); the cost on the hk card is about 224 instructions for a full 32-bit a1 (measured, #1577).
# Later (not built) the same routine will use a hardware multiply unit when the job header word 7 says there is one; callers will not change.
lib_mul32:
  mv t0,a0
  li a0,0
lm_loop:
  beqz a1,lm_done
  andi t1,a1,1
  beqz t1,lm_skip
  add a0,a0,t0
lm_skip:
  slli t0,t0,1
  srli a1,a1,1
  j lm_loop
lm_done:
  ret
