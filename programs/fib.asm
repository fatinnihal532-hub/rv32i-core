# Iterative Fibonacci-style recurrence: s0,s1 start at 0,1 and each step
# advances (s0,s1) <- (s1, s0+s1), ten times. Final s1 is stored to
# data-memory address 0 for the testbench to check.
li   s0, 0
li   s1, 1
li   t0, 10
loop:
  beqz t0, done
  add  t2, s0, s1
  mv   s0, s1
  mv   s1, t2
  addi t0, t0, -1
  j    loop
done:
  sw   s1, 0(zero)
  ecall
