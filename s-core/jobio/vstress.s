# shared-RAM stress: repeats (header arg, word 6) times: for every input word  acc += word; out[0] = acc  (a shared load and a shared store per word).
# Final out[0] = repeats * sum(inputs).  Returns acc in a0.
main:
  push ra
  call lib_io_in
  mv t2,a0
  mv t3,a1
  call lib_io_out
  mv t4,a0
  li t0,0x10000
  lw t5,24(t0)
  li t6,0
outer:
  beqz t5,fin
  mv a2,t2
  mv a3,t3
inner:
  beqz a3,next
  lw t0,0(a2)
  add t6,t6,t0
  sw t6,0(t4)
  addi a2,a2,4
  addi a3,a3,-1
  j inner
next:
  addi t5,t5,-1
  j outer
fin:
  li a0,1
  call lib_io_done
  mv a0,t6
  pop ra
  ret
