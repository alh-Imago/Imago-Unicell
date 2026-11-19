# out[i] = in[i] XOR arg, arg = the job's arg word (any 32-bit value).  Needs out_len >= in_len (else status 2).  Returns the number of words produced.
# Made from template.s by changing the YOUR CODE line to one xor, and by reading the job's arg the way vgain.s does (word 6 of the header at 0x10000).
main:
  push ra
  call lib_io_in
  mv t2,a0
  mv t3,a1
  mv t4,a1
  li t0,0x10000
  lw t5,24(t0)             # t5 = arg
  call lib_io_out
  bltu a1,t4,bad
loop:
  beqz t3,done
  lw t0,0(t2)
  xor t0,t0,t5             # ---- YOUR CODE: the one line that is new
  sw t0,0(a0)
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
