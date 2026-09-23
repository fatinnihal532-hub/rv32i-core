"""One directed test per RV32I instruction (or closely related group), each
simulated in Icarus Verilog against the RTL and checked against a hand
computed expected value. Every case ends with `ecall` so the core halts
cleanly (as a no-op) and the harness reads out final state a few cycles
later.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from harness import run_program, s32  # noqa: E402


class TestRType(unittest.TestCase):
    def setUp(self):
        self.pre = "li t0, 12\nli t1, 5\n"

    def run_op(self, op, expect):
        st = run_program(self.pre + f"{op} t2, t0, t1\necall\n")
        self.assertEqual(st["regs"][7], expect & 0xFFFFFFFF, st["raw"])  # t2 = x7

    def test_add(self): self.run_op("add", 17)
    def test_sub(self): self.run_op("sub", 7)
    def test_and(self): self.run_op("and", 12 & 5)
    def test_or(self):  self.run_op("or", 12 | 5)
    def test_xor(self): self.run_op("xor", 12 ^ 5)
    def test_sll(self): self.run_op("sll", 12 << 5)
    def test_srl(self): self.run_op("srl", 12 >> 5)
    def test_slt(self): self.run_op("slt", 0)   # 12 < 5 is false
    def test_sltu(self): self.run_op("sltu", 0)

    def test_sub_produces_negative(self):
        st = run_program("li t0, 3\nli t1, 10\nsub t2, t0, t1\necall\n")
        self.assertEqual(s32(st["regs"][7]), -7, st["raw"])

    def test_sra_sign_extends(self):
        st = run_program("li t0, -8\nli t1, 1\nsra t2, t0, t1\necall\n")
        self.assertEqual(s32(st["regs"][7]), -4, st["raw"])


class TestIType(unittest.TestCase):
    def test_addi(self):
        st = run_program("li t0, 5\naddi t1, t0, 37\necall\n")
        self.assertEqual(st["regs"][6], 42, st["raw"])

    def test_addi_negative_immediate(self):
        st = run_program("li t0, 5\naddi t1, t0, -8\necall\n")
        self.assertEqual(s32(st["regs"][6]), -3, st["raw"])

    def test_andi_ori_xori(self):
        st = run_program("li t0, 12\nandi t1, t0, 10\nori t2, t0, 3\nxori t3, t0, 15\necall\n")
        self.assertEqual(st["regs"][6], 12 & 10)
        self.assertEqual(st["regs"][7], 12 | 3)
        self.assertEqual(st["regs"][28], 12 ^ 15)

    def test_slti_sltiu(self):
        st = run_program("li t0, 3\nslti t1, t0, 10\nsltiu t2, t0, 10\necall\n")
        self.assertEqual(st["regs"][6], 1)
        self.assertEqual(st["regs"][7], 1)

    def test_slli_srli_srai(self):
        st = run_program("li t0, 4\nslli t1, t0, 2\nsrli t2, t0, 1\nli t3, -16\nsrai t4, t3, 2\necall\n")
        self.assertEqual(st["regs"][6], 16)
        self.assertEqual(st["regs"][7], 2)
        self.assertEqual(s32(st["regs"][29]), -4)


class TestLoadStore(unittest.TestCase):
    def test_sw_lw_roundtrip(self):
        st = run_program("li t0, 0x123\nsw t0, 0(zero)\nlw t1, 0(zero)\necall\n")
        self.assertEqual(st["regs"][6], 0x123, st["raw"])

    def test_byte_and_half_stores_are_independent(self):
        st = run_program(
            "li t0, 0xAA\nsb t0, 0(zero)\nli t0, 0xBB\nsb t0, 1(zero)\n"
            "lbu t1, 0(zero)\nlbu t2, 1(zero)\nlhu t3, 0(zero)\necall\n"
        )
        self.assertEqual(st["regs"][6], 0xAA)
        self.assertEqual(st["regs"][7], 0xBB)
        self.assertEqual(st["regs"][28], 0xBBAA)

    def test_lb_sign_extends_lbu_does_not(self):
        st = run_program("li t0, 0xFF\nsb t0, 0(zero)\nlb t1, 0(zero)\nlbu t2, 0(zero)\necall\n")
        self.assertEqual(s32(st["regs"][6]), -1, st["raw"])
        self.assertEqual(st["regs"][7], 0xFF)


class TestBranches(unittest.TestCase):
    def check_branch(self, cond_asm, expect_taken):
        # If taken, skips the "li t1, 999" and t1 stays 0; else t1 becomes 999.
        st = run_program(f"{cond_asm}\nli t1, 999\nskip:\necall\n")
        if expect_taken:
            self.assertEqual(st["regs"][6], 0, st["raw"])
        else:
            self.assertEqual(st["regs"][6], 999, st["raw"])

    def test_beq_taken(self):
        self.check_branch("li t0, 5\nli t2, 5\nbeq t0, t2, skip", True)

    def test_beq_not_taken(self):
        self.check_branch("li t0, 5\nli t2, 6\nbeq t0, t2, skip", False)

    def test_bne_taken(self):
        self.check_branch("li t0, 5\nli t2, 6\nbne t0, t2, skip", True)

    def test_blt_taken(self):
        self.check_branch("li t0, 3\nli t2, 5\nblt t0, t2, skip", True)

    def test_bge_taken(self):
        self.check_branch("li t0, 5\nli t2, 5\nbge t0, t2, skip", True)

    def test_bltu_treats_operands_as_unsigned(self):
        # -1 as unsigned is huge, so -1 < 1 is false under bltu.
        self.check_branch("li t0, -1\nli t2, 1\nbltu t0, t2, skip", False)

    def test_bgeu_treats_operands_as_unsigned(self):
        self.check_branch("li t0, -1\nli t2, 1\nbgeu t0, t2, skip", True)


class TestUAndJTypes(unittest.TestCase):
    def test_lui(self):
        st = run_program("lui t0, 0x12345\necall\n")
        self.assertEqual(st["regs"][5], 0x12345000, st["raw"])

    def test_auipc(self):
        # auipc is the first instruction, so pc = 0 and the result is just the
        # immediate shifted into place.
        st = run_program("auipc t0, 0x1\necall\n")
        self.assertEqual(st["regs"][5], 0x1000, st["raw"])

    def test_jal_links_return_address_and_jumps(self):
        st = run_program("jal ra, target\nli t0, 111\ntarget:\nli t1, 222\necall\n")
        self.assertEqual(st["regs"][1], 4, st["raw"])   # ra = pc+4 = 4
        self.assertEqual(st["regs"][5], 0, st["raw"])   # skipped: t0 stays 0
        self.assertEqual(st["regs"][6], 222, st["raw"])

    def test_jalr_targets_register_plus_offset(self):
        st = run_program(
            "li t0, 16\njalr ra, t0, 0\nli t1, 111\nli t2, 222\necall\n"
        )
        # jumps to byte address 16 = the "ecall" 5th instruction (index 4);
        # both li's at addresses 8 and 12 are skipped.
        self.assertEqual(st["regs"][6], 0, st["raw"])
        self.assertEqual(st["regs"][7], 0, st["raw"])


if __name__ == "__main__":
    unittest.main()
