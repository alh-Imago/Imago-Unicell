# sums the 16 words at the start of its shared window (the window is where the demo puts data)
main:
  push ra
  li t0,0x10000
  mv a0,t0
  li a1,16
  call lib_sum
  pop ra
  ret
