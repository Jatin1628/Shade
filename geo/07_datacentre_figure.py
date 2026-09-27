"""Figure for the data-centre analysis: land-cover-adjusted surface temperature and tree
cover by distance ring, for each operating data-centre campus.

Colours follow the dataviz reference palette (light mode): categorical slots 1-3 for the
three site groups (validated all-pairs), a neutral grey wash for the look-alike range.

Usage:  python geo/07_datacentre_figure.py [--year 2026]
Input:  data/datacentre_rings.csv (from 06_datacentre_rings.py)
Output: docs/figures/datacentre_rings_<year>.png
"""
import argparse
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator

from config import DATA, DEFAULT_YEAR, ROOT

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]  # categorical slots 1-3
TICKS = ["Campus\n0–0.2 km", "0.2–0.5 km", "0.5–1 km", "1–2 km", "2–4 km\n(reference)"]


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(colors=MUTED, labelcolor=INK_2, labelsize=9, length=0)
    ax.grid(True, axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_xticks(range(len(TICKS)), TICKS)
    ax.set_xlabel("Distance from the data centre", color=INK_2, fontsize=9.5)


def line(ax, x, y, color):
    ax.plot(x, y, color=color, linewidth=1.8, solid_capstyle="round", zorder=3)
    ax.scatter(x, y, s=46, color=color, edgecolors=SURFACE, linewidths=1.4, zorder=4)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "figure.facecolor": SURFACE})

    t = pd.read_csv(DATA / "datacentre_rings.csv").sort_values(["site_group", "ring_index"])
    groups = list(dict.fromkeys(pd.read_csv(DATA / "datacentre_rings.csv")["site_group"]))
    colors = dict(zip(groups, SERIES))
    band = t.groupby("ring_index")[["lookalike_excess_p5", "lookalike_excess_p95"]].mean()
    x = np.arange(len(TICKS))

    fig = plt.figure(figsize=(13, 6.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1], left=0.06, right=0.98, top=0.74, bottom=0.31, wspace=0.18)
    ax_a, ax_b = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])

    # (a) excess heat vs the look-alike range
    style_axes(ax_a)
    ax_a.fill_between(x, band["lookalike_excess_p5"], band["lookalike_excess_p95"], color=MUTED, alpha=0.14,
                      linewidth=0, zorder=1)
    ax_a.axhline(0, color=AXIS, linewidth=1, zorder=2)
    for g in groups:
        d = t[t.site_group == g]
        line(ax_a, x, d["lst_excess"], colors[g])
        ax_a.text(-0.18, d["lst_excess"].iloc[0], g, ha="right", va="center", fontsize=9, color=INK_2)
    ax_a.text(2.5, band["lookalike_excess_p95"].iloc[2] + 0.12,
              "range around 200 look-alike spots per site (5th–95th percentile)",
              ha="center", va="bottom", fontsize=8.5, color=MUTED)
    lim = max(abs(band.values).max(), abs(t["lst_excess"]).max()) + 0.6
    ax_a.set_ylim(-lim, lim)
    ax_a.set_xlim(-1.75, len(TICKS) - 0.6)
    ax_a.set_ylabel("Hotter (+) or cooler (−) than its ground cover predicts (°C)", color=INK_2, fontsize=9.5)
    ax_a.set_title("Surface temperature, after accounting for ground cover", loc="left", fontsize=11,
                   fontweight="semibold", color=INK, pad=8)

    # (b) tree cover
    style_axes(ax_b)
    for g in groups:
        d = t[t.site_group == g]
        line(ax_b, x, d["trees_pct"], colors[g])
    ax_b.set_ylim(0, max(20, t["trees_pct"].max() * 1.2))
    ax_b.yaxis.set_major_locator(MultipleLocator(5))
    ax_b.set_xlim(-0.4, len(TICKS) - 0.6)
    ax_b.set_ylabel("Tree cover (% of area, Dynamic World)", color=INK_2, fontsize=9.5)
    ax_b.set_title("Tree cover is lowest on the campuses themselves", loc="left", fontsize=11,
                   fontweight="semibold", color=INK, pad=8)

    rings = t[t.ring_index < t.ring_index.max()]
    outside = rings[(rings.lst_excess < rings.lookalike_excess_p5) | (rings.lst_excess > rings.lookalike_excess_p95)]
    verdict = ("Every ring sits inside the range seen around ordinary built-up spots." if outside.empty else
               f"{len(outside)} of {len(rings)} rings fall outside the range seen around ordinary built-up spots.")
    fig.text(0.06, 0.94, "Pune's data centres don't show up as surface hot spots" if outside.empty else
             "Data-centre surroundings compared with ordinary built-up land", fontsize=15,
             fontweight="semibold", color=INK)
    fig.text(0.06, 0.895,
             f"Land surface temperature around the three operating data-centre campuses, Mar–May {args.year} "
             f"(Landsat 8/9, about 10:57 am IST). {verdict}",
             fontsize=10, color=INK_2)
    handles = [Line2D([], [], color=colors[g], linewidth=1.8, marker="o", markersize=6,
                      markeredgecolor=SURFACE, label=g) for g in groups]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.055, 0.875), ncol=len(groups), frameon=False,
               fontsize=9.5, labelcolor=INK_2, handlelength=2.2, columnspacing=1.8)
    fig.text(0.06, 0.075,
             "Method: in the 2–4 km ring, temperature is modelled from 2026 ground cover (Dynamic World built, trees, bare, "
             "grass, crops, water) and elevation; each ring's value is measured minus predicted.\n"
             "Look-alike spots: equally built-up places ≥ 4 km from any data centre. Excluded: Microsoft Pimpri "
             "(still a construction site in 2026).\n"
             "Daytime surface temperature shows sun-heated roofs and ground; waste heat vented into the air by cooling "
             "systems is not captured, so a night-time thermal check would be the stronger test.",
             fontsize=8, color=MUTED, linespacing=1.5)
    fig.text(0.06, 0.035, "Sources: USGS Landsat Collection 2 Level-2 · Google Dynamic World · NASADEM, via Google "
             "Earth Engine. Site locations checked on satellite imagery. Table: data/datacentre_rings.csv",
             fontsize=8, color=MUTED)

    out = ROOT / "docs" / "figures" / f"datacentre_rings_{args.year}.png"
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
