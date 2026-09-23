"""Checks the RTL against hand-computed / independently modelled results.
Exits non-zero if any check fails. Run: python3 verify.py (about 5 s)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tests"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "assembler"))
from harness import run_program, s32  # noqa: E402
import tiny_asm  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  [{'pass' if ok else 'FAIL'}] {name}")
    if detail:
        print(f"         {detail}")


def rel(a, b):
    return abs(a - b) / abs(b) if b else abs(a - b)


def main():
    print("rv32i-core - checks against hand-computed and modelled results")
    print("=" * 70)

    st = run_program("li t0, 12\nli t1, 5\nadd t2, t0, t1\nsub t3, t0, t1\necall\n")
    check("R-type: add and sub match integer arithmetic", st["regs"][7] == 17 and st["regs"][28] == 7,
          f"add={st['regs'][7]} (17) sub={st['regs'][28]} (7)")

    st = run_program("addi x0, x0, 5\nadd t0, x0, x0\necall\n")
    check("x0 stays zero even when written", st["regs"][5] == 0, f"t0={st['regs'][5]}")

    st = run_program("li t0, -8\nli t1, 1\nsra t2, t0, t1\nsrl t3, t0, t1\necall\n")
    check("SRA sign-extends, SRL does not (-8 >>> 1 = -4, -8 >> 1 = 0x7FFFFFFC)",
          s32(st["regs"][7]) == -4 and st["regs"][28] == 0x7FFFFFFC,
          f"sra={s32(st['regs'][7])} srl=0x{st['regs'][28]:08x}")

    st = run_program(
        "li t0, -1\nli t1, 1\nblt t0, t1, is_less\nli t2, 0\nj end\n"
        "is_less:\nli t2, 1\nend:\n"
        "bltu t0, t1, unreachable\nli t3, 1\nj done\n"
        "unreachable:\nli t3, 0\ndone:\necall\n"
    )
    check("BLT is signed, BLTU is unsigned, on the same -1-vs-1 comparison",
          st["regs"][7] == 1 and st["regs"][28] == 1,
          f"blt(-1<1)={st['regs'][7]} (expect 1, signed) bltu(-1<1)={st['regs'][28]} (expect 1: t3 unset means bltu was NOT taken)")

    # Built byte-by-byte (rather than with `li`, whose 12-bit immediate can't
    # hold 0xDEAD) to land the half-word 0xDEAD at address 4.
    st = run_program(
        "li t0, 0xAD\nsb t0, 4(zero)\nli t0, 0xDE\nsb t0, 5(zero)\n"
        "lh t1, 4(zero)\nlhu t2, 4(zero)\necall\n"
    )
    check("LH sign-extends a negative half-word, LHU does not (0xDEAD)",
          s32(st["regs"][6]) == s32(0xFFFFDEAD) and st["regs"][7] == 0xDEAD,
          f"lh={s32(st['regs'][6])} lhu=0x{st['regs'][7]:x}")

    with open(os.path.join(os.path.dirname(__file__), "programs", "fib.asm")) as f:
        fib_src = f.read()
    a, b = 0, 1
    for _ in range(10):
        a, b = b, a + b
    st = run_program(fib_src, max_cycles=100)
    check(f"fib.asm's 10-step recurrence matches an independent Python model (expect {b})",
          st["mem"][0] == b, f"core produced {st['mem'][0]}")

    with open(os.path.join(os.path.dirname(__file__), "programs", "sort.asm")) as f:
        sort_src = f.read()
    original = [5, 3, 8, 1, 9, 2]
    st = run_program(sort_src, max_cycles=400)
    check("sort.asm's bubble sort matches Python's sorted() on the same array",
          st["mem"][:6] == sorted(original), f"core produced {st['mem'][:6]}")

    words_a = tiny_asm.assemble(fib_src.splitlines())
    words_b = tiny_asm.assemble(fib_src.splitlines())
    check("assembling the same source twice is deterministic", words_a == words_b)

    stat_path = os.path.join(os.path.dirname(__file__), "results", "synth_stat.txt")
    if os.path.exists(stat_path):
        import re
        text = open(stat_path).read()
        dffs = sum(int(n) for n in re.findall(r"===\s*regfile\s*===.*?\$_DFFE?_\w*_\s+(\d+)", text, re.S))
        check("synthesized register file has exactly 31x32 = 992 flops (x0 has none)",
              dffs == 992, f"found {dffs} (run `yosys -s scripts/synth.tcl` first if this is 0)")
    else:
        check("synthesis results present (run `yosys -s scripts/synth.tcl` first)", False,
              "results/synth_stat.txt not found")

    print("=" * 70)
    print(f"{len(PASS)} checks passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
