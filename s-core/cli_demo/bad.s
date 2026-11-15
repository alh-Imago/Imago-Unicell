# writes one word past the end of its shared window: the board must stop it
main:
  li t0,0x10000
  li t1,64
  sw t1,64(t0)
  li a0,7
  ret
