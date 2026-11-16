# out[0] = largest (unsigned) input word; 0 if there are no inputs; needs out_len >= 1 (else status 2).  Returns 1 in a0.
main:
  push ra
  call lib_io_in
  mv t2,a0
  mv t3,a1
  li t4,0
loop:
  beqz t3,fin
  lw t0,0(t2)
  bgeu t4,t0,skip
  mv t4,t0
skip:
  addi t2,t2,4
  addi t3,t3,-1
  j loop
fin:
  call lib_io_out
  beqz a1,bad
  sw t4,0(a0)
  li a0,1
  call lib_io_done
  li a0,1
  j end
bad:
  li a0,2
  call lib_io_fail
  li a0,0
end:
  pop ra
  ret
