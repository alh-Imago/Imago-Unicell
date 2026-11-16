# out[i] = (in[i] * gain) >> 8, gain = the job's arg word (0..255, 8.8 fixed point: 256 = 1.0).  The core has no multiply, so it is done by shift and add.
# Every input must be below 2^24 so that the product fits 32 bits.  Needs out_len >= in_len (else status 2).  Returns the number of words produced.
main:
  push ra
  call lib_io_in
  mv t2,a0
  mv t3,a1
  mv t4,a1
  li t0,0x10000
  lw t5,24(t0)
  andi t5,t5,255
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
  srli t6,t6,8
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
