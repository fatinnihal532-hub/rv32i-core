# Methodology

## Scope

`rv32i-core` is a single-cycle CPU implementing the RV32I base integer
instruction set (RISC-V, unprivileged spec): all R/I/S/B/U/J-type
instructions, i.e. every instruction except `FENCE`, `ECALL` and `EBREAK`,
which decode as no-ops (there are no traps, interrupts or CSRs in this
design). No M/A/F/D extension.

Single-cycle, not pipelined: each instruction fetches, decodes, executes,
accesses memory and writes back in one clock edge. This is a deliberate
choice for a first RTL/verification project -- it removes hazards
(structural, data and control) from the design entirely, so every bug is a
combinational logic bug or an encoding bug, not a pipeline hazard, which
keeps the design small enough to verify exhaustively by direct simulation
rather than by a hazard-aware testbench. A pipelined version is listed
under Future Work in the README specifically because it reintroduces those
hazards.

## Why there is no forwarding in the register file

An earlier version of `regfile.v` forwarded the write-port data back onto
the read ports combinationally when the write and read addresses matched,
reasoning (wrongly) that a "read-after-write in the same cycle" needed it.
In a single-cycle core it does not: the ALU's inputs for the instruction
executing *this* cycle must be the register values from *before* this
instruction's own write takes effect -- the write is this instruction's
*output*, not an input to it. Adding that forwarding path created a real
combinational cycle whenever an instruction's destination register was also
one of its sources (e.g. `addi t0, t0, -1`, which appears in `fib.asm`):
`rs1_data` (a regfile output) fed the ALU, whose result fed `wb_data`, which
was forwarded back into `rs1_data`. Icarus Verilog's simulator spent CPU
time evaluating that loop's delta cycles without the clock ever advancing,
which is what "the simulation hangs" looks like from the outside. The fix
was to delete the forwarding path, not add a stall or priority encoder --
the design was already correct without it.

## How the RTL is verified

There is no dependency on a full `riscv-gnu-toolchain` install. Test
programs in `programs/` are RISC-V assembly, hand-written and assembled by
`assembler/tiny_asm.py`, a two-pass assembler supporting exactly the
instructions and addressing modes this core implements (see its docstring
for what it deliberately does not support, e.g. `li` only expands to a
single `addi` and rejects constants outside its 12-bit range rather than
silently mis-assembling them).

`tests/harness.py` assembles a program, generates a testbench from
`tb/core_tb_template.v` with that program's hex file and a cycle budget,
compiles it against the RTL in `src/` with Icarus Verilog, runs it, and
parses out the final register file and the first 16 data-memory words.

- `tests/test_isa.py`: one directed test per instruction (or closely
  related group) -- 30 cases covering every opcode the core implements,
  including sign/zero-extension on loads, signed-vs-unsigned branches, and
  the `sub`/`sra` corner cases that are easy to get backwards.
- `tests/test_programs.py` and `verify.py`: two small end-to-end programs
  (`fib.asm`, a 10-step linear recurrence; `sort.asm`, a 6-element bubble
  sort) checked against an independent Python model of the same
  computation -- not against a re-derivation of the assembly, so the check
  cannot pass by construction.
- `verify.py` adds a few closed-form sanity checks: `x0` cannot be written,
  the assembler is deterministic, and the synthesized register file has
  exactly 31x32 = 992 flip-flops (`x0` has none).

## Synthesis: what "gate count" means here, and what it doesn't

`scripts/synth.tcl` runs each of `alu.v`, `regfile.v`, `imm_gen.v` and
`control.v` through Yosys (`synth -top <module>`, mapped to generic
`AND/OR/XOR/NAND/NOR/XNOR/MUX` gates via `abc -g`), and reports the cell
count per module. This estimates the logic that would still have to be
built from standard cells in a real implementation.

Deliberately **not** synthesized:

- The `mem` module (used for both instruction and data memory). At any
  real chip size this would be an SRAM macro from a memory compiler, not a
  behavioral flip-flop array with `$readmemh`; synthesizing it as flops
  would produce a meaningless area number driven entirely by `WORDS`, a
  simulation convenience parameter (currently 512/256 words, chosen for
  fast test-suite compile times, not for any target chip).
- `core.v` itself has no logic of its own; it is point-to-point wiring
  between the modules above and the two memories.

What the reported numbers are **not**:

- Not silicon area. There is no foundry standard-cell library (e.g.
  SkyWater 130nm) in this flow, so there is no `.lib` to map to and no
  real µm² number to report. Mapping to generic gates and counting them is
  a technology-independent proxy for logic complexity, nothing more.
- Not a clock frequency or timing number. Static timing analysis needs
  real cell delays from a `.lib`, which this flow does not have. No `fmax`
  or critical-path-in-ps claim is made anywhere in this repository.

Adding a real PDK (e.g. the open SkyWater 130nm library and an OpenROAD
place-and-route flow) to get true area, power and timing is listed under
Future Work.

## Reproducibility

Given the same source, `tiny_asm.py` and Yosys both produce byte-identical
output (checked directly for the assembler in `verify.py`; Yosys's
`abc -g` mapping is itself deterministic for a fixed netlist and version,
pinned in CI). No random seeds appear anywhere in this flow.
