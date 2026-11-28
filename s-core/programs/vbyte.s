# out[i] = lb(w,0) + lbu(w,1) + lb(w,2) + lbu(w,3) + lh(w,0) + lhu(w,2) (mod 2^32) for the input word w = in[i], using the byte and halfword LOADS (ledger #1598).
# Needs a build with byte/half loads (line hp / hq; sc_sys_v26 and later) and jobio_ext_v2 (shell v12 and later).  arg is not used.  Needs out_len >= in_len (else status 2).
main:
  push ra
  call lib_io_in
  mv t2,a0
  mv t3,a1
  mv t4,a1
  call lib_io_out
  bltu a1,t4,bad
  mv a2,a0
loop:
  beqz t3,done
  lb a3,0(t2)
  lbu a4,1(t2)
  add a3,a3,a4
  lb a4,2(t2)
  add a3,a3,a4
  lbu a4,3(t2)
  add a3,a3,a4
  lh a4,0(t2)
  add a3,a3,a4
  lhu a4,2(t2)
  add a3,a3,a4
  sw a3,0(a2)
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
