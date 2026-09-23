"""Regenerates every figure in results/. Run: python3 scripts/make_figures.py"""
import os
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "rv32i-core"
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results")


def box(ax, xy, w, h, text, fc="#eef2f7", ec="#333"):
    b = FancyBboxPatch(xy, w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                        fc=fc, ec=ec, lw=1.2)
    ax.add_patch(b)
    ax.text(xy[0] + w / 2, xy[1] + h / 2, text, ha="center", va="center", fontsize=9)


def arrow(ax, p0, p1, color="#333"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=10,
                                  color=color, lw=1.1))


def fig_datapath():
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis("off")
    ax.set_title("rv32i-core: single-cycle datapath", fontsize=11)

    box(ax, (0.3, 5.0), 1.6, 1.0, "PC")
    box(ax, (2.3, 5.0), 2.0, 1.0, "Instruction\nmemory")
    box(ax, (5.0, 5.7), 1.8, 0.9, "Control")
    box(ax, (5.0, 4.3), 1.8, 0.9, "Immediate\ngenerator")
    box(ax, (2.3, 3.0), 2.2, 1.0, "Register file\n(x0..x31)")
    box(ax, (5.3, 2.2), 1.7, 1.0, "ALU")
    box(ax, (7.6, 2.2), 2.2, 1.0, "Data memory")
    box(ax, (10.2, 3.0), 1.5, 1.0, "Writeback\nmux")
    box(ax, (8.1, 4.3), 2.2, 1.0, "Branch / jump\ntarget logic")

    arrow(ax, (1.1, 5.0), (1.1, 4.0))
    arrow(ax, (1.1, 4.0), (2.3, 3.5))
    arrow(ax, (1.9, 5.5), (2.3, 5.5))
    arrow(ax, (4.3, 5.5), (5.0, 5.9))
    arrow(ax, (4.3, 5.4), (5.0, 4.6))
    arrow(ax, (4.5, 3.5), (5.3, 2.9))
    arrow(ax, (5.9, 4.3), (5.9, 3.2))
    arrow(ax, (7.0, 2.7), (7.6, 2.7))
    arrow(ax, (9.7, 2.7), (10.2, 3.2))
    arrow(ax, (9.8, 2.2), (10.9, 3.0), color="#888")
    arrow(ax, (5.9, 5.5), (8.1, 4.9))
    arrow(ax, (10.95, 4.0), (10.95, 6.3))
    arrow(ax, (10.95, 6.3), (1.9, 5.6))
    ax.text(6.3, 6.55, "writeback -> register file (this cycle's result becomes visible"
                        " to the NEXT instruction, not this one -- no forwarding needed)",
            ha="center", fontsize=7.3, color="#555")
    ax.text(1.1, 3.75, "pc+4 /\nbranch /\njump", ha="center", fontsize=7, color="#555")

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "datapath.svg"))
    plt.close(fig)


def fig_gate_counts():
    import csv
    rows = list(csv.DictReader(open(os.path.join(OUT, "synth_summary.csv"))))
    rows = [r for r in rows if r["module"] != "TOTAL"]
    names = [r["module"] for r in rows]
    comb = [int(r["combinational_cells"]) for r in rows]
    flops = [int(r["flops"]) for r in rows]

    fig, ax = plt.subplots(figsize=(6.4, 4))
    x = range(len(names))
    ax.bar(x, comb, label="combinational gates", color="#4C72B0")
    ax.bar(x, flops, bottom=comb, label="flip-flops", color="#DD8452")
    ax.set_xticks(list(x))
    ax.set_xticklabels(names)
    ax.set_ylabel("generic-cell count (yosys `abc -g`, no PDK)")
    ax.set_title("Synthesized cell count by module\n(instruction/data memory excluded -- see docs/methodology.md)",
                  fontsize=9.5)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "gate_counts.svg"))
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    fig_datapath()
    fig_gate_counts()
    print("wrote datapath.svg and gate_counts.svg to results/")
