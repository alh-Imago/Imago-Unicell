"""Library + stack test programs (shared by test_link_sim.py and run_link_board.py).  Built with sclink.Linker."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sclink

LIB = """
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
"""
def fib(n): return n if n < 2 else fib(n - 1) + fib(n - 2)

def build(shared_words=256, code_words=None):
    L = sclink.Linker(shared_words=shared_words, private_words=32, code_words=code_words)
    L.library(LIB)
    sb = L.shared_base_addr
    # class 0: sum 16 shared words through the library (data prepared by the host)
    L.add_class(0, "main:\n push ra\n li a0,%d\n li a1,16\n call lib_sum\n pop ra\n ret\n" % sb, stack='private', data_words=16)
    # class 1: recursive fib(7) on the PRIVATE stack (7 levels x 3 words fits in 32 words)
    L.add_class(1, "main:\n push ra\n li a0,7\n call lib_fib\n pop ra\n ret\n", stack='private')
    # class 2: fib(12) on a SHARED stack (36 words are too many for the private memory)
    L.add_class(2, "main:\n push ra\n li a0,12\n call lib_fib\n pop ra\n ret\n", stack='shared', stack_words=48)
    # class 3: the same fib(12) on the private stack: the stack runs off the bottom of the private memory -> trap
    L.add_class(3, "main:\n push ra\n li a0,12\n call lib_fib\n pop ra\n ret\n", stack='private')
    # class 4: fill 8 words of its shared window through the library, then sum them: 8 * 3 = 24;  own non-leaf function with push/pop
    L.add_class(4, "main:\n push ra\n li a0,%d\n li a1,8\n li a2,3\n call lib_fill\n li a0,%d\n li a1,8\n call lib_sum\n pop ra\n ret\n" % (sb, sb),
                stack='private', data_words=8)
    # class 5: two classes with the SAME label names (loop) - proves the label prefixing; counts to 20 and returns 20
    L.add_class(5, "main:\n li a0,0\n li t0,20\nloop:\n addi a0,a0,1\n bne a0,t0,loop\n ret\n", stack='private')
    L.add_class(6, "main:\n li a0,0\n li t0,5\nloop:\n addi a0,a0,2\n addi t0,t0,-1\n bnez t0,loop\n ret\n", stack='private')
    # class 7: jumps into the code window of class 1 (neither its own window nor the library) -> trap
    L.add_class(7, "main:\n li a0,1\n j c1_main\n ret\n", stack='private')
    # class 8: library function reaches data outside the caller's window: lib_sum over 16 words from a window of 4 -> trap (runs under CALLER's limits)
    L.add_class(8, "main:\n push ra\n li a0,%d\n li a1,16\n call lib_sum\n pop ra\n ret\n" % sb, stack='private', data_words=4)
    L.clone_class(12, 2)          # a second window for a second fib(12) running at the same time
    L.clone_class(14, 4)
    L.preload_shared(0, list(range(1, 17)))          # class 0's window is [0,16): 1..16
    return L.link()

# class -> (expected a0 or None, expect trap)
EXPECT = {12: (144, False), 14: (24, False), 0: (136, False), 1: (fib(7), False), 2: (fib(12), False), 3: (None, True), 4: (24, False), 5: (20, False), 6: (10, False), 7: (None, True), 8: (None, True)}
