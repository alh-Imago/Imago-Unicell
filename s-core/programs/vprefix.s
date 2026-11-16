# out[i] = in[0] + ... + in[i] (running sum, 32 bit wrap-around); needs out_len >= in_len (else status 2); returns the number of words produced.
main:
  push ra
  call lib_io_in
  mv t2,a0
  mv t3,a1
  mv t4,a1
  li t5,0
  call lib_io_out
  bltu a1,t4,bad
loop:
  beqz t3,done
  lw t0,0(t2)
  add t5,t5,t0
  sw t5,0(a0)
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
