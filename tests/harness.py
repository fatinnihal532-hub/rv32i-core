"""Assembles a short RV32I program, simulates it with Icarus Verilog against
the RTL in src/, and returns the final architectural state (registers x1-x31
and the first 16 data-memory words) as plain Python dicts/lists.

This is the only place that touches the simulator, so every test in
test_isa.py and test_programs.py is really exercising the Verilog in src/.
"""
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "assembler"))
import tiny_asm  # noqa: E402

SRC = [os.path.join(ROOT, "src", f) for f in
       ("alu.v", "regfile.v", "imm_gen.v", "control.v", "mem.v", "core.v")]
TB_TEMPLATE = os.path.join(ROOT, "tb", "core_tb_template.v")


def run_program(asm_text, max_cycles=200):
    with tempfile.TemporaryDirectory() as td:
        hex_path = os.path.join(td, "prog.hex")
        words = tiny_asm.assemble(asm_text.splitlines())
        tiny_asm.to_hex_bytes(words, hex_path)

        with open(TB_TEMPLATE) as f:
            tb_src = f.read()
        tb_src = tb_src.replace("__IMEM_FILE__", hex_path.replace("\\", "\\\\"))
        tb_src = tb_src.replace("__MAX_CYCLES__", str(max_cycles))
        tb_path = os.path.join(td, "tb.v")
        with open(tb_path, "w") as f:
            f.write(tb_src)

        vvp_path = os.path.join(td, "sim.vvp")
        compile_cmd = ["iverilog", "-g2012", "-o", vvp_path, tb_path] + SRC
        r = subprocess.run(compile_cmd, capture_output=True, text=True, cwd=td)
        if r.returncode != 0:
            raise RuntimeError(f"iverilog failed:\n{r.stdout}\n{r.stderr}")

        r = subprocess.run(["vvp", vvp_path], capture_output=True, text=True, cwd=td)
        if r.returncode != 0:
            raise RuntimeError(f"vvp failed:\n{r.stdout}\n{r.stderr}")
        return _parse(r.stdout, words)


def _parse(output, words):
    reg_vals, mem_vals = [], []
    for line in output.splitlines():
        m = re.match(r"REG ([0-9a-fA-F]{8})", line)
        if m:
            reg_vals.append(int(m.group(1), 16))
            continue
        m = re.match(r"MEM ([0-9a-fA-F]{8})", line)
        if m:
            mem_vals.append(int(m.group(1), 16))
    regs = [0] + reg_vals  # x0 = 0, then x1..x31 as the testbench printed them
    return {"regs": regs, "mem": mem_vals, "n_instr": len(words), "raw": output}


def s32(u):
    """Interpret a 32-bit unsigned Python int as a signed one, for asserting
    against negative expected values."""
    return u - (1 << 32) if u & 0x8000_0000 else u
