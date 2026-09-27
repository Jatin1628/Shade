"""Feasibility-gate figure: Pune land surface temperature at 30 m, ward averages,
and ward temperature against tree cover.

Colours follow the dataviz reference palette (light mode): temperature uses the
blue <-> red diverging pair with a neutral grey midpoint at the PMC average; the
red arm mirrors the documented blue ramp's lightness at the palette's red hue.

Usage:  python geo/05_lst_maps.py [--year 2026]
Output: docs/figures/lst_<year>_pune.png
"""
import argparse
import sys

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import LinearSegmentedColormap, Normalize, to_rgb
from matplotlib.ticker import MaxNLocator
from rasterio.features import geometry_mask
from rasterio.windows import Window, from_bounds
from shapely.geometry import Polygon
from shapely.ops import unary_union

from config import DEFAULT_YEAR, METRIC_CRS, RASTER, ROOT, WARDS

# Reference palette, light mode
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
MIDPOINT = "#f0efec"
SERIES_1 = "#2a78d6"
BLUE_ARM = ["#104281", "#256abf", "#5598e7", "#9ec5f4"]  # ramp steps 650, 500, 350, 200
RED_HUE_SOURCE = "#e34948"  # categorical red

SPAN_C = 6.0  # colour scale covers the PMC average ± 6 °C
MARGIN_M = 1000
N_LABELLED = 3  # hottest and coolest wards to label


def _to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _to_srgb(c):
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(np.clip(c, 0, None), 1 / 2.4) - 0.055)


def hex_to_oklch(color):
    r, g, b = _to_linear(np.array(to_rgb(color)))
    lms = np.cbrt([
        0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b,
        0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b,
        0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b,
    ])
    L = 0.2104542553 * lms[0] + 0.7936177850 * lms[1] - 0.0040720468 * lms[2]
    a = 1.9779984951 * lms[0] - 2.4285922050 * lms[1] + 0.4505937099 * lms[2]
    b_ = 0.0259040371 * lms[0] + 0.7827717662 * lms[1] - 0.8086757660 * lms[2]
    return L, np.hypot(a, b_), np.degrees(np.arctan2(b_, a)) % 360


def oklch_to_hex(L, C, H):
    """Nearest in-gamut sRGB colour, reducing chroma until it fits."""
    for c in np.linspace(C, 0, 400):
        a, b = c * np.cos(np.radians(H)), c * np.sin(np.radians(H))
        l_, m_, s_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3, \
                     (L - 0.1055613458 * a - 0.0638541728 * b) ** 3, \
                     (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
        rgb = np.array([
            4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
            -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
            -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
        ])
        if (rgb >= -1e-6).all() and (rgb <= 1 + 1e-6).all():
            return "#" + "".join(f"{round(v * 255):02x}" for v in _to_srgb(np.clip(rgb, 0, 1)))
    raise ValueError("no in-gamut colour")


def diverging_cmap():
    red_hue = hex_to_oklch(RED_HUE_SOURCE)[2]
    red_arm = [oklch_to_hex(*hex_to_oklch(c)[:2], red_hue) for c in BLUE_ARM]
    stops = BLUE_ARM + [MIDPOINT] + red_arm[::-1]
    lightness = [hex_to_oklch(c)[0] for c in stops]
    mid = len(BLUE_ARM)
    assert all(np.diff(lightness[: mid + 1]) > 0) and all(np.diff(lightness[mid:]) < 0), "ramp not monotone"
    return LinearSegmentedColormap.from_list("lst_diverging", stops), stops


def ink_for(rgba):
    r, g, b = _to_linear(np.array(rgba[:3]))
    return INK if 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.3 else "#ffffff"


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(colors=MUTED, labelcolor=INK_2, labelsize=9, length=0)
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "figure.facecolor": SURFACE})
    cmap, stops = diverging_cmap()
    cmap.set_bad(alpha=0)

    wards = gpd.read_file(WARDS).to_crs(METRIC_CRS)
    if "lst_mean" not in wards:
        sys.exit("wards.geojson has no lst_mean yet — run 04_ward_lst.py first")
    city = wards.union_all()
    # the city outline with its holes filled, so the raster map also shows Pune Cantonment
    city_filled = unary_union([Polygon(p.exterior) for p in getattr(city, "geoms", [city])])

    x0, y0, x1, y1 = city.bounds
    x0, y0, x1, y1 = x0 - MARGIN_M, y0 - MARGIN_M, x1 + MARGIN_M, y1 + MARGIN_M
    with rasterio.open(RASTER / f"lst_{args.year}.tif") as ds:
        full = ds.read(1, masked=True).astype(float)
        city_mean = full[~geometry_mask([city], ds.shape, ds.transform)].mean()
        w = from_bounds(x0, y0, x1, y1, ds.transform)
        window = Window(int(w.col_off), int(w.row_off), int(np.ceil(w.width)), int(np.ceil(w.height)))
        lst = ds.read(1, window=window, masked=True).astype(float)
        transform = ds.window_transform(window)
    outside = geometry_mask([city_filled], lst.shape, transform)
    lst = np.ma.masked_where(outside | lst.mask, lst)
    extent = (transform.c, transform.c + transform.a * lst.shape[1],
              transform.f + transform.e * lst.shape[0], transform.f)

    norm = Normalize(city_mean - SPAN_C, city_mean + SPAN_C)

    fig = plt.figure(figsize=(15, 6.6))
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 0.04], width_ratios=[1, 1, 1.05],
                          left=0.02, right=0.985, top=0.79, bottom=0.13, hspace=0.12, wspace=0.1)
    ax_a, ax_b = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
    ax_c, cax = fig.add_subplot(gs[0, 2]), fig.add_subplot(gs[1, 0:2])

    # (a) 30 m surface temperature
    ax_a.imshow(lst, cmap=cmap, norm=norm, extent=extent, interpolation="nearest")
    wards.boundary.plot(ax=ax_a, color=INK, linewidth=0.3, alpha=0.35)
    gpd.GeoSeries([city_filled], crs=METRIC_CRS).boundary.plot(ax=ax_a, color=INK_2, linewidth=0.8)
    bar_x, bar_y = x0 + 1500, y0 + 1200
    ax_a.plot([bar_x, bar_x + 5000], [bar_y, bar_y], color=INK_2, linewidth=1.5, solid_capstyle="butt")
    ax_a.text(bar_x + 2500, bar_y + 500, "5 km", ha="center", va="bottom", fontsize=8.5, color=INK_2)

    # (b) ward averages — surface-coloured gaps between wards, no drawn borders
    wards.plot(ax=ax_b, column="lst_mean", cmap=cmap, norm=norm, edgecolor=SURFACE, linewidth=0.9)
    gpd.GeoSeries([city], crs=METRIC_CRS).boundary.plot(ax=ax_b, color=AXIS, linewidth=0.6)
    ranked = wards.sort_values("lst_mean")
    for _, w in list(ranked.head(N_LABELLED).iterrows()) + list(ranked.tail(N_LABELLED).iterrows()):
        pt = w.geometry.representative_point()
        ax_b.text(pt.x, pt.y, str(w.ward_id), ha="center", va="center", fontsize=8.5, fontweight="semibold",
                  color=ink_for(cmap(norm(w.lst_mean))))

    for ax, title in ((ax_a, "Surface temperature, 30 m pixels"), (ax_b, "Ward averages (41 PMC wards)")):
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal")
        ax.set_axis_off()
        ax.set_title(title, loc="left", fontsize=11, fontweight="semibold", color=INK, pad=6)

    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation="horizontal", extend="both")
    cb.outline.set_visible(False)
    cb.ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    cb.ax.tick_params(colors=MUTED, labelcolor=INK_2, labelsize=9, length=0)
    cb.ax.axvline(city_mean, color=INK_2, linewidth=1)
    cb.set_label(f"°C  ·  grey = PMC average ({city_mean:.1f} °C), blue = cooler, red = hotter",
                 color=INK_2, fontsize=9)

    # (c) ward temperature vs tree cover
    x, y = wards["tree_frac_wc"] * 100, wards["lst_mean"]
    r = np.corrcoef(x, y)[0, 1]
    slope, intercept = np.polyfit(x, y, 1)
    xs = np.array([x.min(), x.max()])
    style_axes(ax_c)
    ax_c.plot(xs, intercept + slope * xs, color=MUTED, linewidth=1.5, zorder=2)
    ax_c.scatter(x, y, s=42, color=SERIES_1, edgecolors=SURFACE, linewidths=1.4, zorder=3)

    # same wards as the map; each number goes on the side farther from the fit line
    hottest, coolest = ranked.tail(N_LABELLED)[::-1], ranked.head(N_LABELLED)
    for _, w in list(hottest.iterrows()) + list(coolest.iterrows()):
        xi, yi = w.tree_frac_wc * 100, w.lst_mean
        right_gap = abs(intercept + slope * (xi + 2) - yi)
        left_gap = abs(intercept + slope * (xi - 2) - yi)
        dx, ha = (6, "left") if right_gap >= left_gap else (-6, "right")
        ax_c.annotate(str(w.ward_id), (xi, yi), xytext=(dx, 0), textcoords="offset points", ha=ha, va="center",
                      fontsize=8.5, fontweight="semibold", color=INK_2)

    ax_c.set_xlim(0, x.max() * 1.25)
    ax_c.set_xlabel("Tree cover (% of ward, ESA WorldCover 2021)", color=INK_2, fontsize=9.5)
    ax_c.set_ylabel("Ward average surface temperature (°C)", color=INK_2, fontsize=9.5)
    ax_c.set_title(f"Wards with more trees are cooler (r = {r:.2f})", loc="left", fontsize=11,
                   fontweight="semibold", color=INK, pad=6)
    ax_c.text(0.98, 0.98,
              f"Grey line: ≈ {abs(slope) * 10:.1f} °C cooler for every\n"
              "extra 10% of ward area under trees\n"
              "(simple fit, not yet controlled for other factors)",
              transform=ax_c.transAxes, ha="right", va="top", fontsize=8.5, color=MUTED, linespacing=1.4)

    fig.text(0.02, 0.955, "Pune's hottest surfaces are on the city's edge, where trees are scarce",
             fontsize=15, fontweight="semibold", color=INK)
    def names(group):
        return ", ".join(f"{w.ward_id} {w.ward_name.replace(' - ', '–')}" for _, w in group.iterrows())

    fig.text(0.02, 0.905,
             f"Land surface temperature from Landsat 8/9: median of 10 clear scenes, 5 Mar – 16 May {args.year}, "
             "each taken at about 10:57 am IST.",
             fontsize=10, color=INK_2)
    fig.text(0.02, 0.87, f"Numbered wards  ·  hottest: {names(hottest)}  ·  coolest: {names(coolest)}",
             fontsize=10, color=INK_2)
    fig.text(0.02, 0.025,
             "Sources: USGS Landsat Collection 2 Level-2 via Google Earth Engine · ESA WorldCover 2021 · "
             "PMC 2025 ward boundaries (OpenCity). Land surface temperature is how hot roofs and ground are, "
             "not air temperature. Blank area in the ward map: Pune Cantonment, not a PMC ward.",
             fontsize=8, color=MUTED)

    out = ROOT / "docs" / "figures" / f"lst_{args.year}_pune.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    print(f"ramp: {stops}")
    print(f"PMC area-weighted mean LST {city_mean:.2f} °C | r(tree, LST) = {r:.2f} | slope {slope * 10:.2f} °C per 10 pp")
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
