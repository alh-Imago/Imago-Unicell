# out[0] = the standard CRC-32 (the one in zlib, zip, Ethernet) of the input words taken as bytes, least significant byte of each word first.
# Reflected algorithm, polynomial 0xEDB88320, start value 0xFFFFFFFF, final inversion.  XOR a whole word into the register, then 32 single-bit steps
# (the same as four byte steps).  No multiply, no table: only shifts, and / xor, and branches.  Needs out_len >= 1 (else status 2).
main:
  push ra
  call lib_io_in
  mv t2,a0
  mv t3,a1
  li t4,-1
  li t5,0xEDB88320
wloop:
  beqz t3,fin
  lw t0,0(t2)
  xor t4,t4,t0
  li t6,32
bit:
  andi t0,t4,1
  srli t4,t4,1
  beqz t0,nox
  xor t4,t4,t5
nox:
  addi t6,t6,-1
  bnez t6,bit
  addi t2,t2,4
  addi t3,t3,-1
  j wloop
fin:
  xori t4,t4,-1
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
