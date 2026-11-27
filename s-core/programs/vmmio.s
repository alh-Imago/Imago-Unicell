# Cost of a memory-mapped multiply, measured with ordinary shared-RAM accesses (ledger #1580).  arg = the number of loop passes N.
# Each pass does what a memory-mapped multiply would do: two stores (the two operands) and one load (the product), all to the job's shared window,
# plus one add.  out[0] = out[1] = (in[0] + N) mod 2^32.  Needs out_len >= 2 and in_len >= 1 (else status 2).
main:
  push ra
  call lib_io_in
  mv t2,a0
  bnez a1,have
  li a0,2
  call lib_io_fail
  li a0,0
  j end
have:
  lw t3,0(t2)
  call lib_io_out
  li t0,2
  bltu a1,t0,bad
  mv a2,a0
  li t0,0x10000
  lw t2,24(t0)
loop:
  beqz t2,done
  sw t3,0(a2)
  sw t3,4(a2)
  lw t3,4(a2)
  addi t3,t3,1
  addi t2,t2,-1
  j loop
done:
  sw t3,0(a2)
  sw t3,4(a2)
  li a0,2
  call lib_io_done
  li a0,2
  j end
bad:
  li a0,2
  call lib_io_fail
  li a0,0
end:
  pop ra
  ret
