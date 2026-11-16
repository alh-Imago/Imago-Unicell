# sums the input words, writes the sum as the single output word; returns the sum in a0
main:
  push ra
  call lib_io_in
  li t2,0
sl:
  beqz a1,se
  lw t3,0(a0)
  add t2,t2,t3
  addi a0,a0,4
  addi a1,a1,-1
  j sl
se:
  call lib_io_out
  beqz a1,bad
  sw t2,0(a0)
  li a0,1
  call lib_io_done
  mv a0,t2
  j end
bad:
  li a0,2
  call lib_io_fail
  li a0,0
end:
  pop ra
  ret
