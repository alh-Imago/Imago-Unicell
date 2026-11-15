
# lib_sum(a0 = byte address of the first word, a1 = number of words) -> a0 = sum.   Leaf: no stack.
lib_sum:
  li t0,0
lib_sum_loop:
  beqz a1, lib_sum_done
  lw t1,0(a0)
  add t0,t0,t1
  addi a0,a0,4
  addi a1,a1,-1
  j lib_sum_loop
lib_sum_done:
  mv a0,t0
  ret
# lib_fill(a0 = address, a1 = number of words, a2 = value).  Leaf.
lib_fill:
  beqz a1, lib_fill_done
  sw a2,0(a0)
  addi a0,a0,4
  addi a1,a1,-1
  j lib_fill
lib_fill_done:
  ret
# lib_fib(a0 = n) -> a0 = fib(n), plain recursion: three stack words per level.  Uses the caller's stack.
lib_fib:
  li t0,2
  blt a0,t0,lib_fib_end
  addi sp,sp,-12
  sw ra,8(sp)
  sw a0,4(sp)
  addi a0,a0,-1
  call lib_fib
  sw a0,0(sp)
  lw a0,4(sp)
  addi a0,a0,-2
  call lib_fib
  lw t0,0(sp)
  add a0,a0,t0
  lw ra,8(sp)
  addi sp,sp,12
lib_fib_end:
  ret
