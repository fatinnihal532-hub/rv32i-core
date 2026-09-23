"""End-to-end checks: run the actual test programs in programs/ through the
simulator and compare the architectural result against a golden model
written independently in Python (not by re-deriving it from the assembly).
"""
import os
import unittest
import sys

sys.path.insert(0, os.path.dirname(__file__))
from harness import run_program  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    with open(os.path.join(ROOT, "programs", name)) as f:
        return f.read()


class TestFibonacci(unittest.TestCase):
    def test_ten_step_recurrence_matches_python_model(self):
        a, b = 0, 1
        for _ in range(10):
            a, b = b, a + b
        st = run_program(load("fib.asm"), max_cycles=100)
        self.assertEqual(st["mem"][0], b, st["raw"])
        self.assertEqual(st["regs"][9], b, st["raw"])  # s1 = x9


class TestBubbleSort(unittest.TestCase):
    def test_six_element_array_sorted_ascending(self):
        original = [5, 3, 8, 1, 9, 2]
        st = run_program(load("sort.asm"), max_cycles=400)
        self.assertEqual(st["mem"][:6], sorted(original), st["raw"])


if __name__ == "__main__":
    unittest.main()
