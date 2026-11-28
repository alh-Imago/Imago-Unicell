# High multiply library (ledger #1598).  lib_mulhu32: a0 = the HIGH 32 bits of the unsigned 64-bit product a0 * a1, by shift and add (the software path: it works on every build).
# Touches a0, a1, t0 and t1 like lib_mul32 (t2 and t3 are saved on the stack and put back), so a job keeps its state in t2..t6 / a2..a7 across the call.
# 32 rounds of about 11 instructions.  Unit version: jobio/lib_mulhu_unit.s (build with multiply level 2 or more; chosen when the job is linked).
lib_mulhu32:
  push t2
  push t3
  mv t0,a0
  mv t1,a1
  li a0,0
  li t2,32
lh_loop:
  andi t3,t1,1
  beqz t3,lh_noadd
  add a0,a0,t0
  sltu t3,a0,t0
  j lh_shift
lh_noadd:
  li t3,0
lh_shift:
  slli a1,a0,31
  srli t1,t1,1
  or t1,t1,a1
  slli t3,t3,31
  srli a0,a0,1
  or a0,a0,t3
  addi t2,t2,-1
  bnez t2,lh_loop
  pop t3
  pop t2
  ret
