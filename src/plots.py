"""
plots.py
--------
All figures of the project, in my plot style (see style.py).
Every figure is saved as a 300 dpi PNG in figures/.

Run this file directly to make the climate figure for Athens:
    python src/plots.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from style import apply_plot_style, add_legend_on_top, add_panel_label, save_figure, PLOT_COLORS
from weather import load_weather, CITIES, START_YEAR, END_YEAR
from sun import one_day, incidence_angle, sun_position, profile_angle
from window import WINDOWS, MAIN_NORMAL, ANGLE_CURVES, angle_factor, solar_gain_per_m2
from shading import sunlit_fraction
import athens_flat as flat

# Folder for result tables: <project>/results
RESULTS_FOLDER = Path(__file__).resolve().parent.parent / "results"

# One fixed colour per city, used in every figure of the project
CITY_COLORS = {
    "Athens": PLOT_COLORS["red"],
    "Amsterdam": PLOT_COLORS["blue"],
}

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def monthly_climate(table):
    """
    Monthly climate numbers from the hourly table.

    Step 1: one value per (year, month), e.g. "mean temperature of July 2017".
    Step 2: for each month, the mean, lowest and highest of those 10 values.
            The lowest/highest show how much a month changes from year to year.
    """
    year = table.index.year.rename("year")
    month = table.index.month.rename("month")

    # Step 1
    temperature_each = table["T_out_C"].groupby([year, month]).mean()
    # Sum of hourly W/m2 = Wh/m2 for that month; divide by 1000 for kWh/m2
    sun_each = table["total_W_m2"].groupby([year, month]).sum() / 1000

    # Step 2 (group by the "month" level, so the 10 years are combined)
    temperature = temperature_each.groupby(level="month")
    sun = sun_each.groupby(level="month")

    return pd.DataFrame({
        "T_mean_C": temperature.mean(),
        "T_lowest_C": temperature.min(),
        "T_highest_C": temperature.max(),
        "sun_mean_kWh_m2": sun.mean(),
        "sun_lowest_kWh_m2": sun.min(),
        "sun_highest_kWh_m2": sun.max(),
    })


def plot_monthly_climate(city):
    """Figure: (a) monthly outdoor temperature, (b) monthly solar irradiation on a south facade."""
    climate = monthly_climate(load_weather(city))

    # Save the numbers behind the figure, so they can be checked
    RESULTS_FOLDER.mkdir(exist_ok=True)
    table_path = RESULTS_FOLDER / f"{city.lower()}_monthly_climate.csv"
    climate.round(1).to_csv(table_path)
    print(f"Saved: {table_path}")

    apply_plot_style()
    color = CITY_COLORS[city]
    months = climate.index                  # 1, 2, ..., 12
    years_text = f"{START_YEAR}–{END_YEAR}"

    fig, (ax_T, ax_sun) = plt.subplots(1, 2, figsize=(13, 5))

    # (a) Temperature: line = 10-year mean, shaded band = lowest to highest year
    ax_T.fill_between(months, climate["T_lowest_C"], climate["T_highest_C"],
                      color=color, alpha=0.25, linewidth=0,
                      label=f"Range {years_text}")
    ax_T.plot(months, climate["T_mean_C"], color=color, marker="o", markersize=7,
              label=f"{city}, mean")
    ax_T.set_ylabel("Outdoor temperature (°C)")
    ax_T.set_ylim(0, 35)

    # (b) Solar irradiation: bar = 10-year mean, error bar = lowest to highest year
    mean = climate["sun_mean_kWh_m2"]
    below = mean - climate["sun_lowest_kWh_m2"]
    above = climate["sun_highest_kWh_m2"] - mean
    ax_sun.bar(months, mean, width=0.7, color=color, label=f"{city}, mean")
    ax_sun.errorbar(months, mean, yerr=[below, above], fmt="none", ecolor="black",
                    elinewidth=1.5, capsize=4, capthick=1.5,
                    label=f"Range {years_text}")
    ax_sun.set_ylabel("Irradiation on south facade\n(kWh/m² per month)")
    ax_sun.set_ylim(0, 160)

    # Same month axis and legend style for both panels
    for ax in (ax_T, ax_sun):
        ax.set_xticks(months)
        ax.set_xticklabels(MONTH_NAMES)
        ax.set_xlim(0.4, 12.6)
        ax.set_xlabel("Month")
        add_legend_on_top(ax, columns=2)
    add_panel_label(ax_T, "(a)")
    add_panel_label(ax_sun, "(b)")

    fig.tight_layout(w_pad=4)
    save_figure(fig, f"{city.lower()}_monthly_climate.png")


# Three days that show the whole year: shortest day, equal day and night, longest day.
# One fixed colour per day (blue = winter, grey = spring, red = summer).
SUN_DAYS = {
    "21 December": ("2022-12-21", PLOT_COLORS["blue"]),
    "21 March": ("2022-03-21", PLOT_COLORS["grey"]),
    "21 June": ("2022-06-21", PLOT_COLORS["red"]),
}


def plot_sun_path(city):
    """
    Figure: (a) path of the sun in the sky on three days,
            (b) angle at which the sun's rays hit a south-facing window on the same days.
    """
    latitude, longitude = CITIES[city]
    apply_plot_style()
    fig, (ax_path, ax_angle) = plt.subplots(1, 2, figsize=(13, 5))

    for label, (date, color) in SUN_DAYS.items():
        day = one_day(date, latitude, longitude)
        day = day[day["sun_height_deg"] > 0]                 # keep only the hours with the sun up

        # (a) sun height against sun azimuth
        ax_path.plot(day["sun_azimuth_deg"], day["sun_height_deg"], color=color, label=label)

        # (b) incidence angle on a south window, only while the sun shines on it
        angle = incidence_angle(day, wall_azimuth=0)
        on_window = angle < 90
        ax_angle.plot(day["solar_time_h"][on_window], angle[on_window], color=color, label=label)

    # (a) The sun is BEHIND a south wall when it is north of east or north of west
    for left, right in [(-135, -90), (90, 135)]:
        ax_path.axvspan(left, right, color="#E6E6E6", linewidth=0)
    ax_path.text(-112.5, 86, "behind\nsouth\nwall", ha="center", va="top", fontsize=12)
    ax_path.text(112.5, 86, "behind\nsouth\nwall", ha="center", va="top", fontsize=12)
    ax_path.set_xlim(-135, 135)
    ax_path.set_xticks([-90, -45, 0, 45, 90])
    ax_path.set_xticklabels(["−90\nEast", "−45", "0\nSouth", "45", "90\nWest"])
    ax_path.set_xlabel("Sun azimuth (°)")
    ax_path.set_ylabel("Sun height (°)")
    ax_path.set_ylim(0, 90)
    ax_path.set_yticks(range(0, 91, 15))

    # (b)
    ax_angle.set_xlim(6, 18)
    ax_angle.set_xticks(range(6, 19, 2))
    ax_angle.set_xlabel("Solar time (h)")
    ax_angle.set_ylabel("Incidence angle on\nsouth window (°)")
    ax_angle.set_ylim(0, 90)
    ax_angle.set_yticks(range(0, 91, 15))

    for ax in (ax_path, ax_angle):
        add_legend_on_top(ax, columns=3)
    add_panel_label(ax_path, "(a)")
    add_panel_label(ax_angle, "(b)")

    fig.tight_layout(w_pad=4)
    save_figure(fig, f"{city.lower()}_sun_path.png")


# One fixed colour per type of glass
GLASS_COLORS = {
    "single clear": PLOT_COLORS["grey"],
    "double clear": PLOT_COLORS["purple"],
    "double low-E": PLOT_COLORS["green"],
}


def plot_glass_angle(city):
    """
    Figure: (a) how the SHGC of three types of glass falls when the sun hits the glass at an angle,
            (b) solar heat through 1 m2 of the main normal window, per month,
                without and with this effect.
    """
    latitude, longitude = CITIES[city]
    weather = load_weather(city)
    years = len(set(weather.index.year))

    # Solar heat through 1 m2 of glass, hour by hour, in two ways
    window = WINDOWS[MAIN_NORMAL]
    shgc = window["states"]["fixed"]["SHGC"]
    curve = window["angle_curve"]
    angle = incidence_angle(sun_position(weather.index, latitude, longitude), wall_azimuth=0)
    same_at_all_angles = shgc * weather["total_W_m2"]
    with_angle = solar_gain_per_m2(weather, angle, shgc, curve)

    # Monthly sums: W/m2 x 1 hour = Wh/m2; divide by 1000 for kWh/m2 and by the number of years
    month = weather.index.month
    monthly = pd.DataFrame({
        "same_SHGC_at_all_angles_kWh_m2": same_at_all_angles.groupby(month).sum() / 1000 / years,
        "with_sun_angle_kWh_m2": with_angle.groupby(month).sum() / 1000 / years,
    })
    monthly.index.name = "month"
    monthly["ratio"] = monthly["with_sun_angle_kWh_m2"] / monthly["same_SHGC_at_all_angles_kWh_m2"]
    RESULTS_FOLDER.mkdir(exist_ok=True)
    table_path = RESULTS_FOLDER / f"{city.lower()}_solar_gain_monthly.csv"
    monthly.round(2).to_csv(table_path)
    print(f"Saved: {table_path}")

    apply_plot_style()
    fig, (ax_curve, ax_gain) = plt.subplots(1, 2, figsize=(13, 5))

    # (a) angle factor of the three types of glass
    angles = range(0, 91)
    for name in ANGLE_CURVES:
        ax_curve.plot(angles, angle_factor(name, angles), color=GLASS_COLORS[name], label=name)
    ax_curve.set_xlabel("Incidence angle (°)")
    ax_curve.set_ylabel("SHGC relative to head-on")
    ax_curve.set_xlim(0, 90)
    ax_curve.set_xticks(range(0, 91, 15))
    ax_curve.set_ylim(0, 1.05)
    add_legend_on_top(ax_curve, columns=3)

    # (b) monthly solar heat through the main normal window
    months = monthly.index
    ax_gain.plot(months, monthly["same_SHGC_at_all_angles_kWh_m2"], color=PLOT_COLORS["grey"],
                 marker="o", markersize=7, linestyle="--", label="same SHGC at all angles")
    ax_gain.plot(months, monthly["with_sun_angle_kWh_m2"], color=GLASS_COLORS[curve],
                 marker="o", markersize=7, label="with sun angle")
    ax_gain.set_xticks(months)
    ax_gain.set_xticklabels(MONTH_NAMES)
    ax_gain.set_xlim(0.4, 12.6)
    ax_gain.set_xlabel("Month")
    ax_gain.set_ylabel("Solar heat through glass\n(kWh/m² per month)")
    ax_gain.set_ylim(0, 90)
    add_legend_on_top(ax_gain, columns=2)

    add_panel_label(ax_curve, "(a)")
    add_panel_label(ax_gain, "(b)")
    fig.tight_layout(w_pad=4)
    save_figure(fig, f"{city.lower()}_glass_angle.png")


# ---------------- Balcony shadow: 3D view and side view ----------------

def sun_at(date, solar_hour, latitude, longitude):
    """Sun position on one day at the given solar time (e.g. 10.0 = 10:00 solar time)."""
    day = one_day(date, latitude, longitude)
    row = (day["solar_time_h"] - solar_hour).abs().idxmin()
    return day.loc[[row]]


def sun_vector(sun):
    """
    Unit vector pointing to the sun, for the 3D drawing.
    Axes: x = east, y = north, z = up (a right-handed system, so the drawing is not mirrored).
    The south wall is the plane y = 0 and the balcony sticks out towards negative y (south).
    """
    h = np.radians(sun["sun_height_deg"].iloc[0])
    azimuth = np.radians(sun["sun_azimuth_deg"].iloc[0])      # 0 = south, west positive
    return np.array([-np.cos(h) * np.sin(azimuth), -np.cos(h) * np.cos(azimuth), np.sin(h)])


def clip_to_rectangle(points, x_min, x_max, z_min, z_max):
    """Cut a polygon (list of (x, z) points) to a rectangle (Sutherland-Hodgman method)."""
    def clip(polygon, inside, cross):
        result = []
        for i, current in enumerate(polygon):
            previous = polygon[i - 1]
            if inside(current):
                if not inside(previous):
                    result.append(cross(previous, current))
                result.append(current)
            elif inside(previous):
                result.append(cross(previous, current))
        return result

    def cross_x(x):
        return lambda p, q: (x, p[1] + (q[1] - p[1]) * (x - p[0]) / (q[0] - p[0]))

    def cross_z(z):
        return lambda p, q: (p[0] + (q[0] - p[0]) * (z - p[1]) / (q[1] - p[1]), z)

    polygon = list(points)
    for inside, cross in [(lambda p: p[0] >= x_min, cross_x(x_min)), (lambda p: p[0] <= x_max, cross_x(x_max)),
                          (lambda p: p[1] >= z_min, cross_z(z_min)), (lambda p: p[1] <= z_max, cross_z(z_max))]:
        polygon = clip(polygon, inside, cross)
        if not polygon:
            break
    return polygon


def draw_balcony_3d(ax, sun, title):
    """3D view of the south wall, the balcony door, the balcony above, and its shadow."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    half = flat.ROOM_WIDTH / 2                  # wall from x = -2 to +2 m
    top = flat.ROOM_HEIGHT                      # balcony underside at 2.7 m
    depth = flat.BALCONY_DEPTH
    door_half = flat.WINDOW_WIDTH / 2
    door_top = flat.WINDOW_HEIGHT

    def wall_polygon(points_xz):
        return [(x, 0.0, z) for x, z in points_xz]

    def add(polygon, order, **style):
        collection = Poly3DCollection([polygon], **style)
        collection.set_zorder(order)                  # drawing order: higher = on top
        ax.add_collection3d(collection)

    # Wall, door and balcony slab (the slab sticks out to the south, negative y)
    add(wall_polygon([(-half, 0), (half, 0), (half, top), (-half, top)]), 1,
        facecolor="#E6E6E6", edgecolor="black", linewidth=1.2)
    add(wall_polygon([(-door_half, 0), (door_half, 0), (door_half, door_top), (-door_half, door_top)]), 2,
        facecolor="#BFD7F5", edgecolor=PLOT_COLORS["blue"], linewidth=2)

    # Shadow: the front edge of the balcony, moved along the sun's rays until it reaches the wall
    s = sun_vector(sun)
    to_wall = depth / -s[1]                           # length along a ray from the edge to the wall
    # The model assumes a balcony much wider than the wall, so the shadow is cast by a long
    # front edge (here 40 m); only the part on our wall is drawn.
    front_x = [-20.0, 20.0]
    hits = [(x - to_wall * s[0], top - to_wall * s[2]) for x in front_x]
    shadow_xz = clip_to_rectangle([(-half, top), (half, top), hits[1], hits[0]], -half, half, 0, top)
    if shadow_xz:
        add(wall_polygon(shadow_xz), 3, facecolor=PLOT_COLORS["grey"], alpha=0.7, edgecolor="none")
    add([(-half, 0, top), (half, 0, top), (half, -depth, top), (-half, -depth, top)], 4,
        facecolor="#9A9A9A", edgecolor="black", linewidth=1.2)

    # Two sun rays that pass the front edge of the balcony and land at x = -0.5 and +0.5 m.
    # A ray stops where it reaches the wall (y = 0) or the floor of our balcony (z = 0).
    steps = min(to_wall, top / s[2])
    for end_x in (-0.5, 0.5):
        start_x = end_x + steps * s[0]
        if -half <= start_x <= half:
            ax.plot([start_x, end_x], [-depth, -depth - steps * s[1]], [top, top - steps * s[2]],
                    color=PLOT_COLORS["red"], linestyle="--", linewidth=2, zorder=5)
    # Direction of the sun: an arrow pointing towards it
    start = np.array([0.0, -2.4, 0.2])
    ax.quiver(*start, *(1.3 * s), color=PLOT_COLORS["red"], linewidth=2.5, arrow_length_ratio=0.2, zorder=6)
    ax.text(*(start + 1.45 * s), "to the sun", color=PLOT_COLORS["red"], fontsize=13,
            fontweight="bold", zorder=6)

    ax.set_xlim(-half, half)
    ax.set_ylim(-3, 0)
    ax.set_zlim(0, top)
    ax.set_box_aspect((2 * half, 3, top))
    ax.set_xticks([-2, -1, 0, 1, 2])
    ax.set_yticks([-3, -2, -1, 0])
    ax.set_yticklabels(["3", "2", "1", "0"])          # distance south of the wall
    ax.set_zticks([0, 1, 2])
    ax.set_xlabel("West ← → East (m)", labelpad=8)
    ax.set_ylabel("South of wall (m)", labelpad=6)
    ax.set_zlabel("Height (m)", labelpad=4)
    ax.view_init(elev=20, azim=-118)              # camera in front of the wall, to the south-west
    ax.xaxis.pane.set_visible(False)
    ax.yaxis.pane.set_visible(False)
    ax.zaxis.pane.set_visible(False)
    ax.grid(False)

    h = sun["sun_height_deg"].iloc[0]
    azimuth = sun["sun_azimuth_deg"].iloc[0]
    p = profile_angle(sun, wall_azimuth=0).iloc[0]
    lit = float(sunlit_fraction(p, depth, flat.BALCONY_GAP, door_top))
    ax.set_title(f"{title}\nsun height {h:.0f}°, azimuth {azimuth:.0f}°\n"
                 f"profile angle {p:.0f}°, door in sun {lit * 100:.0f} %", fontsize=13, fontweight="bold")


def plot_balcony_shadow(city="Athens"):
    """
    Figure: (a), (b) 3D view of the balcony shadow at 10:00 solar time on 21 June and 21 December,
            (c) side view: how the profile angle gives the length of the shadow.
    """
    latitude, longitude = CITIES[city]
    apply_plot_style()
    fig = plt.figure(figsize=(18, 6.2))

    days = {"21 June, 10:00": ("2022-06-21", PLOT_COLORS["red"]),
            "21 December, 10:00": ("2022-12-21", PLOT_COLORS["blue"])}
    for position, (title, (date, _)) in enumerate(days.items(), start=1):
        ax = fig.add_subplot(1, 3, position, projection="3d", computed_zorder=False)
        draw_balcony_3d(ax, sun_at(date, 10.0, latitude, longitude), title)

    # (c) Side view at solar noon
    ax = fig.add_subplot(1, 3, 3)
    top, depth, door_top = flat.ROOM_HEIGHT, flat.BALCONY_DEPTH, flat.WINDOW_HEIGHT
    ax.plot([0, 0], [0, top], color="black", linewidth=3)                          # wall
    ax.plot([0, 0], [0, door_top], color=PLOT_COLORS["blue"], linewidth=7)       # door
    ax.plot([0, depth], [top, top], color="#9A9A9A", linewidth=7)                  # balcony
    ax.plot([0, 3.2], [0, 0], color="black", linewidth=1.5)                        # floor of our balcony
    for label, (date, color) in days.items():
        noon = sun_at(date, 12.0, latitude, longitude)
        p = profile_angle(noon, wall_azimuth=0).iloc[0]
        shadow = depth * np.tan(np.radians(p))                     # m below the balcony
        if top - shadow >= 0:                                      # ray reaches the wall
            end_x, end_z = 0.0, top - shadow
        else:                                                      # ray reaches the floor first
            end_x, end_z = depth - top / np.tan(np.radians(p)), 0.0
        start_x, start_z = depth + 1.5, top + 1.5 * np.tan(np.radians(p))
        ax.plot([start_x, end_x], [start_z, end_z], color=color, linestyle="--",
                label=f"{label.split(',')[0]}, noon: p = {p:.0f}°")
    ax.annotate("", xy=(depth, top + 0.12), xytext=(0, top + 0.12),
                arrowprops=dict(arrowstyle="<->", linewidth=1.8))
    ax.text(depth / 2, top + 0.18, "d = 1.0 m", ha="center", va="bottom", fontsize=13)
    ax.text(0.08, top - 0.25, "gap 0.5 m", fontsize=12, va="center")
    ax.text(0.08, door_top / 2, "balcony\ndoor", fontsize=12, va="center", color=PLOT_COLORS["blue"])
    ax.text(1.05, 1.0, "shadow on the wall\n= d · tan(p)", fontsize=12)
    ax.set_xlim(-0.3, 3.0)
    ax.set_ylim(0, 3.6)
    ax.set_aspect("equal")
    ax.set_xlabel("Distance from the wall (m)")
    ax.set_ylabel("Height (m)")
    add_legend_on_top(ax, columns=1)

    for x, text in [(0.01, "(a)"), (0.34, "(b)"), (0.67, "(c)")]:
        fig.text(x, 0.96, text, fontsize=20, fontweight="bold", va="top")
    fig.tight_layout(w_pad=3)
    save_figure(fig, f"{city.lower()}_balcony_shadow.png")


# ---------------- Smart glass vs normal glass (results of ec_comparison.py) ----------------

# One fixed colour per glass, used in every figure of the smart-glass comparison.
# (Blue is not used here because blue already means Amsterdam in CITY_COLORS.)
EC_GLASS_COLORS = {
    "normal": PLOT_COLORS["grey"],
    "smart": PLOT_COLORS["green"],
}
EC_GLASS_LABELS = {
    "normal": "Normal glass (double low-E)",
    "smart": "Smart glass (SageGlass + rule)",
}
COMPARED_CITIES = ["Athens", "Amsterdam"]


def read_result_table(file_name, **options):
    """Read a table from results/. The smart-glass tables are made by ec_comparison.py."""
    path = RESULTS_FOLDER / file_name
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run first:  python src/ec_comparison.py")
    return pd.read_csv(path, **options)


def draw_glass_bars(ax, x, normal_values, smart_values, width=0.38):
    """Two bars side by side for every x: normal glass (left) and smart glass (right)."""
    # A thin black outline keeps the light green bars visible on the white background
    bars = {}
    for key, values, shift in (("normal", normal_values, -width / 2),
                               ("smart", smart_values, width / 2)):
        bars[key] = ax.bar(np.asarray(x) + shift, values, width=width, color=EC_GLASS_COLORS[key],
                           edgecolor="black", linewidth=0.8, label=EC_GLASS_LABELS[key])
    return bars


def plot_ec_yearly():
    """Figure: yearly heating, cooling and total, normal vs smart glass, (a) Athens, (b) Amsterdam."""
    table = read_result_table("city_comparison.csv", index_col="city")

    apply_plot_style()
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)
    groups = ["Heating", "Cooling", "Total"]
    x = np.arange(len(groups))

    for ax, city, panel in zip(axes, COMPARED_CITIES, ("(a)", "(b)")):
        row = table.loc[city]
        normal = [row["normal_heating_kWh"], row["normal_cooling_kWh"],
                  row["normal_heating_kWh"] + row["normal_cooling_kWh"]]
        smart = [row["smart_heating_kWh"], row["smart_cooling_kWh"],
                 row["smart_heating_kWh"] + row["smart_cooling_kWh"]]
        bars = draw_glass_bars(ax, x, normal, smart)

        # The number on top of every bar (only six bars, so this stays readable)
        for key in ("normal", "smart"):
            ax.bar_label(bars[key], fmt="%.0f", padding=3, fontsize=12, fontweight="bold")
        # The saving of the total, above the two "Total" bars
        ax.text(x[2], max(normal[2], smart[2]) + 750, f"Saved {row['saved_%']:.0f} %",
                ha="center", fontsize=14, fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels(groups)
        ax.set_xlim(-0.6, 2.6)
        ax.set_ylim(0, 7500)
        ax.text(0.03, 0.95, city, transform=ax.transAxes, fontsize=17, fontweight="bold", va="top")
        add_panel_label(ax, panel)
        ax.tick_params(labelleft=True)          # numbers on both y-axes (sharey hides them)
    axes[0].set_ylabel("Heat demand (kWh per year)")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2,
               frameon=False, handlelength=2.2, columnspacing=2.0)
    fig.tight_layout(w_pad=4)
    save_figure(fig, "ec_vs_normal_yearly.png")


def plot_ec_monthly():
    """Figure: monthly heating (top) and cooling (bottom), normal vs smart glass, both cities."""
    apply_plot_style()
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharey=True)
    months = np.arange(1, 13)

    for column, city in enumerate(COMPARED_CITIES):
        monthly = read_result_table(f"{city.lower()}_ec_monthly.csv", index_col="month")
        for row, what in enumerate(("heating", "cooling")):
            ax = axes[row, column]
            draw_glass_bars(ax, months, monthly[f"normal_{what}_kWh"], monthly[f"smart_{what}_kWh"])
            ax.set_xticks(months)
            ax.set_xticklabels([name[0] for name in MONTH_NAMES])   # J F M A ...
            ax.set_xlim(0.4, 12.6)
            ax.set_ylim(0, 750)
            ax.tick_params(labelleft=True)
            if row == 0:
                ax.set_title(city, fontsize=18, fontweight="bold", pad=12)
            else:
                ax.set_xlabel("Month")
            if column == 0:
                ax.set_ylabel(f"{what.capitalize()}\n(kWh per month)")
            add_panel_label(ax, "(" + "abcd"[row * 2 + column] + ")")

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2,
               frameon=False, handlelength=2.2, columnspacing=2.0)
    fig.tight_layout(h_pad=3, w_pad=4)
    save_figure(fig, "ec_vs_normal_monthly.png")


if __name__ == "__main__":
    plot_monthly_climate("Athens")
    plot_sun_path("Athens")
    plot_glass_angle("Athens")
    plot_balcony_shadow("Athens")
    plot_ec_yearly()
    plot_ec_monthly()
