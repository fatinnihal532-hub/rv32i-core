# Generic (technology-independent) synthesis of the core's control and
# datapath logic: the register file, ALU, immediate generator and control
# unit. This intentionally excludes the two `mem` instances (instruction
# and data memory) and the top-level `core` wiring between them: at any
# real chip size the memories would be SRAM macros from a memory compiler,
# not synthesizable flip-flop arrays, and the top-level module is pure
# point-to-point wiring with no logic of its own. What's synthesized here
# is exactly the part of the design a real implementation would still map
# to standard cells.
#
# Mapped to generic AND/OR/XOR/NAND/NOR/XNOR/MUX gates, not a foundry cell
# library, so the result is a gate count, not a silicon area or ps/GHz
# number -- see docs/methodology.md for why, and what a real PDK flow
# would add.
read_verilog src/alu.v src/regfile.v src/imm_gen.v src/control.v
synth -top alu; tee -o results/synth_stat.txt stat
design -reset

read_verilog src/alu.v src/regfile.v src/imm_gen.v src/control.v
synth -top regfile; tee -a results/synth_stat.txt stat
design -reset

read_verilog src/alu.v src/regfile.v src/imm_gen.v src/control.v
synth -top imm_gen; tee -a results/synth_stat.txt stat
design -reset

read_verilog src/alu.v src/regfile.v src/imm_gen.v src/control.v
synth -top control; tee -a results/synth_stat.txt stat
