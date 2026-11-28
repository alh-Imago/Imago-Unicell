# Multiply library, UNIT version (ledger #1584).  lib_mul32: a0 = (a0 * a1) mod 2^32 by the memory-mapped multiply unit of the build (sc_sys_v23, MULU=1):
# store operand A and B to the device window (byte 0x20000, +4) and load the product (+8).  Touches only a0, a1 and t0.  Linked instead of lib_mul.s when the build has
# multiply units (jobio_ext_v1.install(units > 0)); on a build WITHOUT the unit this traps (cause 2), so the host must link the software version there (it does: count 0).
lib_mul32:
  lui t0,0x20
  sw a0,0(t0)
  sw a1,4(t0)
  lw a0,8(t0)
  ret
