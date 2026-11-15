# fib(12) = 144, recursive, stack in the shared window
main:
  push ra
  li a0,12
  call lib_fib
  pop ra
  ret
