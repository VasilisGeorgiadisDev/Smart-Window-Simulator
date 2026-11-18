"""
style.py
--------
My plot style, copied from my NASA Battery Degradation project
(src/plots.py there). Use it for every figure in this project:

    from style import apply_plot_style, add_legend_on_top, save_figure, PLOT_COLORS

    - Arial, everything bold (numbers, axis labels, legend)
    - thick lines and a thick black frame on all four sides
    - ticks pointing outwards, no grid
    - legend above the plot, in one row, without a box
    - five fixed colours, always used in the same order

Every figure is saved as PNG at 300 dpi in the figures/ folder.
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt

# Hide harmless "findfont: Failed to find font weight bold..." messages.
# matplotlib always loads one maths font (cmex10) that has no bold version.
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)


# Folder where the figures are saved: <project>/figures
FIGURES_FOLDER = Path(__file__).resolve().parent.parent / "figures"

# My five plot colours, always used in this order.
PLOT_COLORS = {
    "grey":   "#515151",
    "red":    "#F14040",
    "blue":   "#1A6FDF",
    "green":  "#37AD6B",
    "purple": "#B177DE",
}

# Line and frame thickness (in points). Change these to make all plots thicker/thinner.
LINE_WIDTH = 2.2
FRAME_WIDTH = 1.8


def apply_plot_style():
    """Set matplotlib's defaults so every plot has my plot style."""
    plt.rcParams.update({
        # Font: Arial, bold everywhere
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.weight": "bold",
        "axes.labelweight": "bold",
        # Maths text (subscripts like T$_{out}$) also in bold Arial, not matplotlib's own fonts
        "mathtext.fontset": "custom",
        "mathtext.rm": "Arial:bold",
        "mathtext.it": "Arial:bold:italic",
        "mathtext.bf": "Arial:bold",
        "mathtext.default": "bf",
        "mathtext.fallback": None,         # no backup maths fonts (avoids "findfont" warnings)
        # Font sizes
        "font.size": 13,
        "axes.labelsize": 17,
        "xtick.labelsize": 14,
        "ytick.labelsize": 14,
        "legend.fontsize": 14,
        # Thick black frame on all four sides
        "axes.linewidth": FRAME_WIDTH,
        "axes.edgecolor": "black",
        # Ticks: outwards, thick, only on the bottom and left axes
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 6,
        "ytick.major.size": 6,
        "xtick.major.width": FRAME_WIDTH,
        "ytick.major.width": FRAME_WIDTH,
        # Lines
        "lines.linewidth": LINE_WIDTH,
        # No grid, white background
        "axes.grid": False,
        "figure.facecolor": "white",
        # Saving
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    })


def add_legend_on_top(ax, columns):
    """Legend above the plot, without a box."""
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=columns,
              frameon=False, handlelength=2.2, columnspacing=1.6)


def add_panel_label(ax, text):
    """Bold '(a)', '(b)' label at the top-left, outside the plot."""
    ax.text(-0.16, 1.10, text, transform=ax.transAxes,
            fontsize=20, fontweight="bold", va="bottom")


def save_figure(fig, file_name):
    """Save a figure in figures/ as a 300 dpi PNG and tell the user where it is."""
    FIGURES_FOLDER.mkdir(exist_ok=True)
    path = FIGURES_FOLDER / file_name
    try:
        fig.savefig(path)
        print(f"Saved: {path}")
    except OSError:
        # Windows "locks" a file while another program (e.g. Photos) has it open
        print(f"\nCould NOT save {path}")
        print("The image is probably open in another program. Close it and run again.\n")
    plt.close(fig)                  # free the memory used by the figure
    return path
