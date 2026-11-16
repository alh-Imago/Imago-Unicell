# Job I/O library.  Every job's shared window starts with an 8-word header (see jobio.py):
#   w0 in_off  w1 in_len  w2 out_off  w3 out_len  w4 status (0 pending, 1 ok, >=2 error)  w5 n_out (words produced)  w6 arg  w7 spare
# These four functions touch ONLY t0, t1, a0 and a1, so a job can keep its state in t2..t6 / a2..a7 across calls and only has to save ra.
# offsets are in words from the start of the job's window; the window starts at byte address 0x10000.
lib_io_in:                     # -> a0 = byte address of the inputs, a1 = number of input words
  li t0,0x10000
  lw t1,0(t0)
  slli t1,t1,2
  add a0,t0,t1
  lw a1,4(t0)
  ret
lib_io_out:                    # -> a0 = byte address of the output area, a1 = its size in words
  li t0,0x10000
  lw t1,8(t0)
  slli t1,t1,2
  add a0,t0,t1
  lw a1,12(t0)
  ret
lib_io_done:                   # a0 = number of output words produced: records it and sets status 1 (ok)
  li t0,0x10000
  sw a0,20(t0)
  li t1,1
  sw t1,16(t0)
  ret
lib_io_fail:                   # a0 = error code (>= 2): sets the status
  li t0,0x10000
  sw a0,16(t0)
  ret
