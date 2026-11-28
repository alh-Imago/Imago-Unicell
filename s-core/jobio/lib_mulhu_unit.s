# High multiply library, unit version (ledger #1598): a0 = the high 32 bits of the unsigned product a0 * a1 from the hardware multiply unit (device window byte 0x20000: store A at +0, store B at +4, load the high half at +12).
# Needs a build with multiply level 2 or more (sc_sys_v24 and later, MULU 2); on a build without the high half the load traps (cause 2).  Touches a0 and t0 only.
lib_mulhu32:
  lui t0,0x20
  sw a0,0(t0)
  sw a1,4(t0)
  lw a0,12(t0)
  ret
