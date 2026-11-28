# out[i] = in[i] // d for a CONSTANT d, with one multiply and one shift (ledger #1590; see divconst_v1.py).  arg packs the constant: arg = (k << 27) | M, M = ceil(2^k / d)
# (divconst_v1.pack(d)); the answer is (in[i] * M mod 2^32) >> k, exact for in[i] up to the xmax that divconst_v1.best(d) prints (about 47,000 or more for every d up to 300).
# Multiplies with lib_mul32 (the hardware unit on an hm build, shift and add elsewhere).  Needs out_len >= in_len (else status 2).  Returns the number of words produced.
main:
  push ra
  call lib_io_in
  mv t2,a0
  mv t3,a1
  mv t4,a1
  li t0,0x10000
  lw t5,24(t0)
  srli t6,t5,27
  slli t5,t5,5
  srli t5,t5,5
  call lib_io_out
  bltu a1,t4,bad
  mv a2,a0
loop:
  beqz t3,done
  lw a0,0(t2)
  mv a1,t5
  call lib_mul32
  srl a0,a0,t6
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
