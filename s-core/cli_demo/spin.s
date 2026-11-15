# counts to 200 and returns it: a job that takes a while
main:
  li a0,0
  li t0,200
loop:
  addi a0,a0,1
  bne a0,t0,loop
  ret
