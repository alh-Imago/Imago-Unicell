# out[i] = in[i] with its four bytes reversed (arg = 0, written with four sb) or its two halfwords swapped (arg = 1, written with two sh) (ledger #1598).
# Needs a build with the byte-store unit (multiply level 3, line hp): the assembler expands sb / sh into the device sequence (clobbers t0 and t1; see asm_ext_v1.py) - jobio_ext_v2 (shell v12 and later).
# The output words are not cleared first: every byte (or halfword) of an output word is written.  Needs out_len >= in_len (else status 2).
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
  lw a3,0(t2)
  bnez t5,half
  srli a4,a3,24
  sb a4,0(a2)
  srli a4,a3,16
  sb a4,1(a2)
  srli a4,a3,8
  sb a4,2(a2)
  sb a3,3(a2)
  j next
half:
  srli a4,a3,16
  sh a4,0(a2)
  sh a3,2(a2)
next:
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
