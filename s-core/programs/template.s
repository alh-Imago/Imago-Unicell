# TEMPLATE for a job program.  Copy this file, change the part marked YOUR CODE, register it (see progs.py) and use it as a job kind.
#
# What the board gives you (the "job I/O convention", jobio.py):
#   * a window of the shared RAM that starts at byte address 0x10000: an 8-word header, then your input words, then room for your output words;
#   * lib_io_in   -> a0 = byte address of the inputs,  a1 = number of input words
#   * lib_io_out  -> a0 = byte address of the output area, a1 = its size in words
#   * lib_io_done (a0 = number of output words you produced): marks the job finished OK
#   * lib_io_fail (a0 = error code >= 2): marks the job refused / failed; also set a0 = 0 before returning
#   * these four functions change ONLY t0, t1, a0, a1: keep your own state in t2..t6 and a2..a7
#   * `main:` must end with `ret`; save ra on entry (push ra) and restore it (pop ra) because main calls the library
# What you must keep to:
#   * RV32I only, word loads and stores only (lw / sw): no lb / lh / sb / sh, no multiply or divide (jobiss.py refuses them)
#   * touch only your window and your private stack (16 words by default); anything else is a trap on the board
#   * at most about 100 instructions of code in all jobs of a batch together (the code store is 128 words incl. the library)
# The example below copies the inputs to the outputs (out = in).
main:
  push ra
  call lib_io_in
  mv t2,a0                 # t2 = input pointer
  mv t3,a1                 # t3 = inputs left
  mv t4,a1                 # t4 = number of input words (kept to report)
  call lib_io_out
  bltu a1,t4,bad           # output area too small: refuse (status 2)
loop:
  beqz t3,done
  lw t0,0(t2)
  # ---- YOUR CODE: compute from t0, leave the result in t0 ----
  sw t0,0(a0)
  addi t2,t2,4
  addi a0,a0,4
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
