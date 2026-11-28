# out[i] = the HIGH 32 bits of the unsigned 64-bit product in[i] * arg (ledger #1598).  Calls lib_mulhu32: the hardware unit on a build with multiply level 2 or more (line hp / hq), shift and add elsewhere (about 350 instructions per word).
# Needs jobio_ext_v2.install (shell v12 and later).  Needs out_len >= in_len (else status 2).  Returns the number of words produced.
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
  mv a2,a0
loop:
  beqz t3,done
  lw a0,0(t2)
  mv a1,t5
  call lib_mulhu32
  sw a0,0(a2)
  addi t2,t2,4
  addi a2,a2,4
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
