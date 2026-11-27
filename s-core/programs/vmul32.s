# out[i] = (in[i] * arg) mod 2^32, arg = the job's arg word, a full 32-bit multiplier (any value 0..2^32-1; the product wraps).  The core has no multiply, so it is done by shift and add.
# Written for the multiply cost test (ledger #1576): the loop count is the bit length of arg, so arg = 0xFFFFFFFF is the worst case (32 steps), arg = 1 the cheapest.
# Needs out_len >= in_len (else status 2).  Returns the number of words produced.  Clone of vgain.s without the >> 8 and without the 8-bit mask.
main:
  push ra
  call lib_io_in
  mv t2,a0
  mv t3,a1
  mv t4,a1
  li t0,0x10000
  lw t5,24(t0)
  call lib_io_out
  bltu a1,t4,bad
loop:
  beqz t3,done
  lw t0,0(t2)
  mv t1,t5
  li t6,0
mul:
  beqz t1,mdone
  andi a2,t1,1
  beqz a2,mskip
  add t6,t6,t0
mskip:
  slli t0,t0,1
  srli t1,t1,1
  j mul
mdone:
  sw t6,0(a0)
  addi t2,t2,4
  addi a0,a0,4
  addi t3,t3,-1
  j loop
done:
  mv a0,t4
  call lib_io_done
  mv a0,t4
  j end
bad:
  li a0,2
  call lib_io_fail
  li a0,0
end:
  pop ra
  ret
