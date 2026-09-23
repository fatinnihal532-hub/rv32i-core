# Bubble-sorts a 6-word array in data memory (addresses 0..20) ascending.
# Fixed pass count (n-1) rather than an early-exit flag, so correctness
# does not depend on branch prediction of any kind -- there is none here.
li t0, 5
sw t0, 0(zero)
li t0, 3
sw t0, 4(zero)
li t0, 8
sw t0, 8(zero)
li t0, 1
sw t0, 12(zero)
li t0, 9
sw t0, 16(zero)
li t0, 2
sw t0, 20(zero)

li  s0, 6
addi s0, s0, -1     # s0 = n-1 = number of adjacent pairs per pass
mv  s1, s0          # s1 = passes remaining

outer:
  beqz s1, end_outer
  li  t3, 0          # t3 = byte address of a[j]
  mv  t4, s0         # t4 = pairs left to compare this pass
inner:
  beqz t4, end_inner
  lw   t0, 0(t3)
  lw   t1, 4(t3)
  bge  t1, t0, no_swap
  sw   t1, 0(t3)
  sw   t0, 4(t3)
no_swap:
  addi t3, t3, 4
  addi t4, t4, -1
  j    inner
end_inner:
  addi s1, s1, -1
  j    outer
end_outer:
  ecall
