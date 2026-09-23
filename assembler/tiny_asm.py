"""A minimal two-pass RV32I assembler.

Supports exactly the instructions the core implements (the full RV32I base
integer ISA, no pseudo-ops except the handful defined in PSEUDO below). It
exists so every test program in programs/ is built from source you can read,
rather than from a prebuilt binary -- there is no dependency on a full
riscv-gnu-toolchain install.

Not a general-purpose assembler: no macros, no .data directives beyond
`.word`, and only the addressing modes the test programs use.
"""
import re
import sys

REGS = {f"x{i}": i for i in range(32)}
ABI = ("zero ra sp gp tp t0 t1 t2 s0 s1 a0 a1 a2 a3 a4 a5 a6 a7 "
       "s2 s3 s4 s5 s6 s7 s8 s9 s10 s11 t3 t4 t5 t6").split()
for i, name in enumerate(ABI):
    REGS[name] = i
REGS["fp"] = 8

R_TYPE = {
    "add":  (0b0110011, 0b000, 0b0000000), "sub": (0b0110011, 0b000, 0b0100000),
    "sll":  (0b0110011, 0b001, 0b0000000), "slt": (0b0110011, 0b010, 0b0000000),
    "sltu": (0b0110011, 0b011, 0b0000000), "xor": (0b0110011, 0b100, 0b0000000),
    "srl":  (0b0110011, 0b101, 0b0000000), "sra": (0b0110011, 0b101, 0b0100000),
    "or":   (0b0110011, 0b110, 0b0000000), "and": (0b0110011, 0b111, 0b0000000),
}
I_TYPE_ARITH = {
    "addi": (0b0010011, 0b000), "slti": (0b0010011, 0b010), "sltiu": (0b0010011, 0b011),
    "xori": (0b0010011, 0b100), "ori":  (0b0010011, 0b110), "andi": (0b0010011, 0b111),
}
I_TYPE_SHIFT = {"slli": (0b0000000, 0b001), "srli": (0b0000000, 0b101), "srai": (0b0100000, 0b101)}
I_TYPE_LOAD = {
    "lb": 0b000, "lh": 0b001, "lw": 0b010, "lbu": 0b100, "lhu": 0b101,
}
S_TYPE = {"sb": 0b000, "sh": 0b001, "sw": 0b010}
B_TYPE = {"beq": 0b000, "bne": 0b001, "blt": 0b100, "bge": 0b101, "bltu": 0b110, "bgeu": 0b111}
PSEUDO = {"nop", "j", "jr", "ret", "li", "mv", "call", "beqz", "bnez"}


def reg(tok):
    tok = tok.strip().rstrip(",")
    if tok not in REGS:
        raise ValueError(f"unknown register '{tok}'")
    return REGS[tok]


def imm_val(tok, labels, pc):
    tok = tok.strip().rstrip(",")
    if tok in labels:
        return labels[tok] - pc
    return int(tok, 0)


def split_mem_operand(tok):
    # "off(reg)" -> (off, reg)
    m = re.match(r"(-?\w+)\((\w+)\)", tok.strip().rstrip(","))
    return int(m.group(1), 0), reg(m.group(2))


def encode_r(f7, rs2, rs1, f3, rd, opc):
    return (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | opc


def encode_i(imm12, rs1, f3, rd, opc):
    return ((imm12 & 0xFFF) << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | opc


def encode_s(imm12, rs2, rs1, f3, opc):
    imm12 &= 0xFFF
    return ((imm12 >> 5) << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | ((imm12 & 0x1F) << 7) | opc


def encode_b(imm13, rs2, rs1, f3, opc):
    imm13 &= 0x1FFE
    b12 = (imm13 >> 12) & 1
    b105 = (imm13 >> 5) & 0x3F
    b41 = (imm13 >> 1) & 0xF
    b11 = (imm13 >> 11) & 1
    return (b12 << 31) | (b105 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (b41 << 8) | (b11 << 7) | opc


def encode_u(imm20, rd, opc):
    return ((imm20 & 0xFFFFF) << 12) | (rd << 7) | opc


def encode_j(imm21, rd, opc):
    imm21 &= 0x1FFFFE
    b20 = (imm21 >> 20) & 1
    b101 = (imm21 >> 1) & 0x3FF
    b11 = (imm21 >> 11) & 1
    b1912 = (imm21 >> 12) & 0xFF
    return (b20 << 31) | (b101 << 21) | (b11 << 20) | (b1912 << 12) | (rd << 7) | opc


def assemble(lines):
    # Pass 1: strip comments/labels, record label addresses, expand pseudo-ops
    # 1:1 with the real instructions they expand to (so addresses stay simple).
    raw = []
    pc = 0
    labels = {}
    for line in lines:
        line = line.split("#")[0].strip()
        if not line:
            continue
        if ":" in line:
            label, _, rest = line.partition(":")
            labels[label.strip()] = pc
            line = rest.strip()
            if not line:
                continue
        raw.append((pc, line))
        pc += 4

    words = []
    for pc, line in raw:
        parts = re.split(r"[\s,]+", line.strip())
        mnem = parts[0].lower()
        args = parts[1:]

        if mnem == "nop":
            words.append(encode_i(0, 0, 0, 0, 0b0010011))
        elif mnem == "mv":
            words.append(encode_i(0, reg(args[1]), 0, reg(args[0]), 0b0010011))
        elif mnem == "li":
            rd = reg(args[0])
            val = int(args[1], 0)
            if not (-2048 <= val <= 2047):
                raise ValueError(
                    f"li {args[0]}, {args[1]}: {val} does not fit addi's 12-bit "
                    "immediate; this assembler's `li` expands only to `addi rd, x0, "
                    "imm` (no lui+addi fusion for large constants) -- build it with "
                    "explicit lui/addi/ori instead."
                )
            words.append(encode_i(val & 0xFFFFFFFF, 0, 0, rd, 0b0010011))
        elif mnem == "j":
            words.append(encode_j(imm_val(args[0], labels, pc), 0, 0b1101111))
        elif mnem == "jr":
            words.append(encode_i(0, reg(args[0]), 0, 0, 0b1100111))
        elif mnem == "ret":
            words.append(encode_i(0, 1, 0, 0, 0b1100111))
        elif mnem == "call":
            words.append(encode_j(imm_val(args[0], labels, pc), 1, 0b1101111))
        elif mnem == "beqz":
            words.append(encode_b(imm_val(args[1], labels, pc), 0, reg(args[0]), 0b000, 0b1100011))
        elif mnem == "bnez":
            words.append(encode_b(imm_val(args[1], labels, pc), 0, reg(args[0]), 0b001, 0b1100011))
        elif mnem in R_TYPE:
            opc, f3, f7 = R_TYPE[mnem]
            words.append(encode_r(f7, reg(args[2]), reg(args[1]), f3, reg(args[0]), opc))
        elif mnem in I_TYPE_ARITH:
            opc, f3 = I_TYPE_ARITH[mnem]
            words.append(encode_i(int(args[2], 0), reg(args[1]), f3, reg(args[0]), opc))
        elif mnem in I_TYPE_SHIFT:
            f7, f3 = I_TYPE_SHIFT[mnem]
            shamt = int(args[2], 0) & 0x1F
            words.append(encode_r(f7, shamt, reg(args[1]), f3, reg(args[0]), 0b0010011))
        elif mnem in I_TYPE_LOAD:
            f3 = I_TYPE_LOAD[mnem]
            off, base = split_mem_operand(args[1])
            words.append(encode_i(off, base, f3, reg(args[0]), 0b0000011))
        elif mnem in S_TYPE:
            f3 = S_TYPE[mnem]
            off, base = split_mem_operand(args[1])
            words.append(encode_s(off, reg(args[0]), base, f3, 0b0100011))
        elif mnem in B_TYPE:
            f3 = B_TYPE[mnem]
            words.append(encode_b(imm_val(args[2], labels, pc), reg(args[1]), reg(args[0]), f3, 0b1100011))
        elif mnem == "jal":
            if len(args) == 1:
                words.append(encode_j(imm_val(args[0], labels, pc), 1, 0b1101111))
            else:
                words.append(encode_j(imm_val(args[1], labels, pc), reg(args[0]), 0b1101111))
        elif mnem == "jalr":
            words.append(encode_i(int(args[2], 0) if len(args) > 2 else 0, reg(args[1]), 0, reg(args[0]), 0b1100111))
        elif mnem == "lui":
            words.append(encode_u(int(args[1], 0) >> 12 if int(args[1], 0) > 0xFFFFF else int(args[1], 0), reg(args[0]), 0b0110111))
        elif mnem == "auipc":
            words.append(encode_u(int(args[1], 0), reg(args[0]), 0b0010111))
        elif mnem == "ecall":
            words.append(0b1110011)
        else:
            raise ValueError(f"unknown mnemonic '{mnem}' in line: {line}")
    return words


def to_hex_bytes(words, path):
    """Write little-endian bytes, one hex byte per line -- $readmemh's format
    for a byte-addressable memory array."""
    with open(path, "w") as f:
        for w in words:
            for shift in (0, 8, 16, 24):
                f.write(f"{(w >> shift) & 0xFF:02x}\n")


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    with open(src) as f:
        words = assemble(f.readlines())
    to_hex_bytes(words, out)
    print(f"assembled {len(words)} instructions from {src} -> {out}")
