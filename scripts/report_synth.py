"""Parses results/synth_stat.txt (produced by scripts/synth.tcl) and writes a
short human-readable summary plus a CSV, so the numbers quoted in the README
are generated from the actual yosys run rather than typed in by hand.
"""
import csv
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAT_FILE = os.path.join(ROOT, "results", "synth_stat.txt")


def parse(path):
    with open(path) as f:
        text = f.read()
    modules = {}
    for block in re.split(r"\n\n(?=\d+\. Printing statistics\.)", text):
        m = re.search(r"=== (\w+) ===", block)
        if not m:
            continue
        name = m.group(1)
        cells_total = int(re.search(r"Number of cells:\s+(\d+)", block).group(1))
        dff = sum(int(n) for n in re.findall(r"\$_DFFE?_\w*_\s+(\d+)", block))
        modules[name] = {"total_cells": cells_total, "flops": dff, "combinational": cells_total - dff}
    return modules


def main():
    modules = parse(STAT_FILE)
    total_comb = sum(m["combinational"] for m in modules.values())
    total_flop = sum(m["flops"] for m in modules.values())

    out_txt = os.path.join(ROOT, "results", "synth_summary.txt")
    out_csv = os.path.join(ROOT, "results", "synth_summary.csv")

    with open(out_txt, "w") as f:
        f.write("Technology-independent gate count (generic AND/OR/XOR/NAND/NOR/XNOR/MUX + DFF)\n")
        f.write("Excludes the two `mem` instances -- see docs/methodology.md.\n")
        f.write("=" * 70 + "\n")
        for name, m in sorted(modules.items()):
            f.write(f"{name:10s}  combinational={m['combinational']:5d}  flops={m['flops']:4d}\n")
        f.write("-" * 70 + "\n")
        f.write(f"{'TOTAL':10s}  combinational={total_comb:5d}  flops={total_flop:4d}\n")

    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["module", "combinational_cells", "flops", "total_cells"])
        for name, m in sorted(modules.items()):
            w.writerow([name, m["combinational"], m["flops"], m["total_cells"]])
        w.writerow(["TOTAL", total_comb, total_flop, total_comb + total_flop])

    print(open(out_txt).read())


if __name__ == "__main__":
    main()
