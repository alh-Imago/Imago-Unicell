# out[0] = how many input words are bigger (unsigned) than the job's arg; 0 if there are no inputs; needs out_len >= 1 (else status 2).  Returns 1 in a0.
# Made from vmax.s: the running "biggest" (t4) became a counter that starts at 0 and goes up by one for every input that is bigger than arg (t5),
# and arg is read from word 6 of the header the way vgain.s does.
main:
  push ra
  call lib_io_in
  mv t2,a0
  mv t3,a1
  li t4,0                  # t4 = the count so far
  li t0,0x10000
  lw t5,24(t0)             # t5 = arg (the threshold)
loop:
  beqz t3,fin
  lw t0,0(t2)
  bgeu t5,t0,skip          # threshold >= this input: not bigger, do not count it
  addi t4,t4,1             # bigger: count it
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
