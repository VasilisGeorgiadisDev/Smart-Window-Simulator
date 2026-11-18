"""
athens_flat.py
--------------
A SIDE STUDY (not part of the main comparison): the living room of an OLD flat in Athens.
It does not fully reflect reality: the room size, the door and the balcony are our own
choices, and the rooms next door are assumed to be at the same temperature.

    - apartment block built before 1980 (no insulation), concrete frame and brick walls
    - middle floor, free view to the south
    - only ONE wall touches the outside: the south wall, with a balcony door
    - the other walls, the floor and the ceiling touch rooms of the same flat or of the
      neighbours, which are assumed to be at the same temperature: no heat flows through them
    - the OLD window: single glass (modelled as glass only, without its frame, see below)
    - two cases on the same floor, identical except for one thing (agreed 16 Nov 2026):
          Case A: a balcony above the window (the balcony of the flat above), 1.0 m deep
          Case B: no balcony above the window

Values and their sources (all values are checked again in docs/equations.md, section 4):

    Wall: double brick, plastered on both sides, no insulation   U = 2.20 W/(m2 K)   [9] Table 2.3
    Wall colour "light-coloured plaster (e.g. light grey)": solar absorptance 0.40  [10] Table 3.15
    Outside surface resistance R_se = 0.04 m2 K/W                                  [4] Table 1
    Single glass, glass only: U = 5.70 W/(m2 K)                                    [10] Table 3.8
    Single glass, glass only: g = 0.85 at normal incidence                         [10] Table 3.17
    Air leaking through a single-glazed aluminium window  8.05 m3/h per m2 of window [9] Table 4.5
    Fresh air needed                                   0.75 m3/h per m2 of floor    [9] Table 3.1
    Heat from people / devices / lamps                 4 / 2 / 0.64 W per m2 floor  [9] Table 3.1
    Thermostat                                         20 C heating, 26 C cooling   [9] Table 3.1
    Hours of use                                       18 hours per day             [9] Table 3.1
    Thermal bridges before 1980                        none                         [9] Table 4.5
    Heavy building: heat capacity 260 000 J/K and mass area 3.0 m2 per m2 of floor  [8] Table 12

Our own choices (no reference needed, they DEFINE the case; agreed on 17 Nov 2026):

    Living room 4 m wide (along the south wall), 5 m deep, 2.7 m high
    Balcony door 2.0 m wide, 2.2 m high
    Balcony depth 1.0 m (Case A)
    The whole opaque wall is brick (concrete columns and beams are ignored)
    Wall colour light grey (chosen 17 Nov 2026)
    No window frame: every window (old, new, smart) is modelled as glass only, so that all
    of them are compared on the same basis (chosen 17 Nov 2026; no published frame data
    for smart windows was found)

ASSUMPTIONS (not from a source):

    - The underside of the balcony above is at the level of our ceiling (2.7 m), so the gap
      between the top of the door (2.2 m) and the balcony is 0.5 m. The thickness of the
      floor slab is ignored. The balcony is much wider than the door. Its railing is ignored.

    - The 18 hours of use are 06:00 to 24:00 Athens time. From 00:00 to 06:00 there is no
      heating or cooling. [9] gives the number of hours but not which hours.
    - Heat from people, devices and lamps is given only during the 18 hours of use
      (nobody is in the living room at night). The fresh air is constant day and night.
    - The fresh air and the leaking air are added together, as stated in [9]:
      "The infiltration load is added to the ventilation load".
    - The whole 2.0 m x 2.2 m opening is glass (no frame). The glass follows the angle curve of
      single clear glass [6]. Why not the TABULA window values (U 6.1, g 0.58 [9])? They
      include a frame and an average over the sun angles: with [10] Eq. 3.9,
      (1 - 0.25 frame) x 0.9 x 0.85 = 0.57. Our angle curve would count the angle twice, and
      the new and smart windows only have glass values.
    - Sun on the brick wall: the part U x R_se of the absorbed sun reaches the room
      (steady state, as in ISO 13790). It is added to the solar heat at once; the real wall
      delays it by some hours. The balcony shades the wall like the door, using the full
      wall height (gap 0, height 2.7 m).

Not included: heat radiated from the wall and the glass to the cold night sky (no public
source with the formula and its values was found; it would lower the net solar heat a
little), and opening the window.

References
----------
[6] ASHRAE Standard 140, Annex B6 (see window.py)
[8] ISO/FDIS 13790:2007, Table 12 (see room_model.py)
[4] ISO 6946:2007, Table 1 (see room_model.py)
[9] TABULA project, "Scientific report Greece", National Observatory of Athens (NOA),
    Tables 2.3, 2.4, 3.1 and 4.5. Accessed 17 Nov 2026.
    https://episcope.eu/fileadmin/tabula/public/docs/scientific/GR_TABULA_ScientificReport_NOA.pdf
[10] Technical Chamber of Greece (TEE), T.O.T.E.E. 20701-1/2017, "Detailed national
    specifications of parameters for the calculation of the energy performance of buildings
    and the issue of the energy performance certificate" (in Greek), 1st edition 2017.
    Table 3.8 (U of glass), Eq. 3.9 and Table 3.17 (g of glass), Table 3.15 (solar
    absorptance of plaster colours). Accessed 17 Nov 2026 from a university course copy:
    https://eclass.hmu.gr/modules/document/file.php/TH200/TOTEE_20701-1_2017_TEE_1st_Edition.pdf

Run:
    python src/athens_flat.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

from room_model import simulate_5r1c, yearly_demand, AIR_HEAT_CAPACITY, R_SE
from shading import sunlit_fraction, sky_fraction
from sun import sun_position, incidence_angle, profile_angle
from weather import load_weather, CITIES
from window import solar_gain_per_m2

RESULTS_FOLDER = Path(__file__).resolve().parent.parent / "results"

# ---------------- Our choices: the room ----------------
ROOM_WIDTH = 4.0        # m, along the south wall
ROOM_DEPTH = 5.0        # m
ROOM_HEIGHT = 2.7       # m
WINDOW_WIDTH = 2.0      # m, balcony door
WINDOW_HEIGHT = 2.2     # m
WALL_AZIMUTH = 0.0      # the window faces south
BALCONY_DEPTH = 1.0     # m, Case A (chosen 17 Nov 2026)
BALCONY_GAP = ROOM_HEIGHT - WINDOW_HEIGHT   # 0.5 m, see the assumption above

# The two cases of the project: name -> balcony depth in m
CASES = {"A: balcony above": BALCONY_DEPTH, "B: no balcony": 0.0}

# ---------------- Values from the references ----------------
U_WALL = 2.20                     # W/(m2 K), double brick, plastered, no insulation [9]
WALL_ABSORPTANCE = 0.40           # light-coloured plaster, e.g. light grey [10] Table 3.15
OLD_WINDOW = {
    "name": "Old window: single glass",
    "U": 5.70,                    # W/(m2 K), glass only [10] Table 3.8
    "g": 0.85,                    # glass only, normal incidence [10] Table 3.17
    "leakage_m3_h_per_m2": 8.05,  # m3/h per m2 of window, single glass, aluminium [9]
    "angle_curve": "single clear",
}
FRESH_AIR_M3_H_PER_M2 = 0.75      # m3/h per m2 of floor [9]
GAINS_W_PER_M2 = {"people": 4.0, "devices": 2.0, "lamps": 0.64}   # W per m2 of floor [9]
T_HEATING = 20.0                  # C [9]
T_COOLING = 26.0                  # C [9]
HEAVY_CAPACITY_J_K_PER_M2 = 260_000    # J/K per m2 of floor, class "heavy" [8]
HEAVY_MASS_AREA_PER_M2 = 3.0           # m2 per m2 of floor, class "heavy" [8]

# ---------------- Assumption: hours of use ----------------
FIRST_HOUR_ON = 6       # thermostat on from 06:00 ...
LAST_HOUR_ON = 23       # ... until 24:00 (the hour 23:00-24:00 is the last one on)


def flat_room(window):
    """The living room as the list of numbers that the 5R1C model needs."""
    floor_area = ROOM_WIDTH * ROOM_DEPTH                            # 20 m2
    volume = floor_area * ROOM_HEIGHT                               # 54 m3
    window_area = WINDOW_WIDTH * WINDOW_HEIGHT                      # 4.4 m2
    wall_area = ROOM_WIDTH * ROOM_HEIGHT - window_area              # 6.4 m2 of brick

    # Air: leaking through the window + fresh air, added together [9]
    air_m3_h = window["leakage_m3_h_per_m2"] * window_area + FRESH_AIR_M3_H_PER_M2 * floor_area

    return {
        "name": "Athens living room, " + window["name"],
        "floor_area": floor_area,
        "volume": volume,
        "window_area": window_area,
        "wall_area": wall_area,
        "air_m3_h": air_m3_h,
        # all surfaces that face the room: floor + ceiling + four walls (with the window)
        "inner_surface_area": 2 * floor_area + 2 * (ROOM_WIDTH + ROOM_DEPTH) * ROOM_HEIGHT,
        "H_window": window["U"] * window_area,                      # W/K
        "H_opaque": U_WALL * wall_area,                             # W/K, only the south wall
        "H_ventilation": AIR_HEAT_CAPACITY * air_m3_h,              # W/K
        "C_mass": HEAVY_CAPACITY_J_K_PER_M2 * floor_area / 3600,    # J/K -> Wh/K
        "mass_area": HEAVY_MASS_AREA_PER_M2 * floor_area,           # m2
        # heat from people, devices and lamps while the room is in use (W);
        # simulate_flat() switches it off outside the hours of use
        "internal_gains_W": sum(GAINS_W_PER_M2.values()) * floor_area,
        "T_heating": T_HEATING,
        "T_cooling": T_COOLING,
    }


def hours_of_use(times_utc):
    """True for the hours when the thermostat is on (06:00 to 24:00 Athens time)."""
    local_hour = times_utc.tz_convert("Europe/Athens").hour
    return (local_hour >= FIRST_HOUR_ON) & (local_hour <= LAST_HOUR_ON)


def wall_solar_gain(weather, profile, balcony_depth, room):
    """
    Sun absorbed by the outside of the brick wall that reaches the room (W, one value per hour).

    Of the sun absorbed at the outside surface, the fraction U x R_se flows inwards
    (steady state): for our wall 2.20 x 0.04 = 0.088, so about 9 %.
    The balcony shades the wall over its full height (gap 0, height = room height).
    """
    sunlit = sunlit_fraction(profile, balcony_depth, 0.0, ROOM_HEIGHT)
    sky = sky_fraction(balcony_depth, 0.0, ROOM_HEIGHT)
    sun_on_wall = (sunlit * weather["beam_W_m2"] + sky * weather["diffuse_W_m2"]
                   + weather["reflected_W_m2"])                       # W/m2
    return WALL_ABSORPTANCE * U_WALL * R_SE * room["wall_area"] * sun_on_wall


def simulate_flat(weather, window, balcony_depth=0.0, use_schedule=True):
    """
    Hour-by-hour simulation of the living room with the given window.
    balcony_depth: depth of the balcony above the window in m (0 = no balcony).
    use_schedule : True = thermostat and internal gains only during the 18 hours of use,
                   False = both on 24 hours a day.
    """
    latitude, longitude = CITIES["Athens"]
    room = flat_room(window)
    sun = sun_position(weather.index, latitude, longitude)
    angle = incidence_angle(sun, WALL_AZIMUTH)
    profile = profile_angle(sun, WALL_AZIMUTH)
    sunlit = sunlit_fraction(profile, balcony_depth, BALCONY_GAP, WINDOW_HEIGHT)
    sky = sky_fraction(balcony_depth, BALCONY_GAP, WINDOW_HEIGHT)
    window_solar = solar_gain_per_m2(weather, angle, window["g"], window["angle_curve"],
                                     sunlit=sunlit, sky=sky) * room["window_area"]
    wall_solar = wall_solar_gain(weather, profile, balcony_depth, room)

    if use_schedule:
        schedule = hours_of_use(weather.index)
        # people, devices and lamps only while the room is in use
        room["internal_gains_W"] = np.where(schedule, room["internal_gains_W"], 0.0)
    else:
        schedule = None
    result = simulate_5r1c(weather, room, window_solar + wall_solar, thermostat_on=schedule)
    result["window_solar_W"] = np.asarray(window_solar)
    result["wall_solar_W"] = np.asarray(wall_solar)
    return room, result


def describe_room(room):
    """Print the numbers of the room."""
    print(f"Floor {room['floor_area']:.1f} m2, volume {room['volume']:.1f} m3, "
          f"window {room['window_area']:.1f} m2, brick wall {room['wall_area']:.1f} m2")
    print(f"Air through the room: {room['air_m3_h']:.1f} m3/h "
          f"= {room['air_m3_h'] / room['volume']:.2f} air changes per hour")
    H = {"window": room["H_window"], "brick wall": room["H_opaque"], "air": room["H_ventilation"]}
    total = sum(H.values())
    print("Heat loss coefficient H (W/K):")
    for name, value in H.items():
        print(f"  {name:12s} {value:6.1f}  ({value / total * 100:4.1f} %)")
    print(f"  {'TOTAL':12s} {total:6.1f}")
    print(f"Heat capacity {room['C_mass']:.0f} Wh/K, time constant {room['C_mass'] / total:.0f} hours")
    print(f"Heat from people, devices and lamps: {room['internal_gains_W']:.1f} W while in use")
    print(f"Sun on the brick wall: {WALL_ABSORPTANCE:.2f} absorbed, "
          f"{U_WALL * R_SE * 100:.1f} % of that reaches the room")


def check_result(room, result):
    """Sanity checks: these test the maths, not the physics."""
    heat_in = (result["solar_gain_W"] + result["internal_gain_W"] + result["heating_W"]).sum()
    heat_out = (result["cooling_W"] + result["loss_W"] + result["radiant_loss_W"]).sum()
    stored = room["C_mass"] * (result["T_mass_end_C"].iloc[-1] - room["T_heating"])
    on = hours_of_use(result.index)
    hvac_off = ((result["heating_W"] > 0) | (result["cooling_W"] > 0))[~on].sum()
    both = ((result["heating_W"] > 0) & (result["cooling_W"] > 0)).sum()
    print(f"  1) energy balance error {heat_in - heat_out - stored:.1e} Wh of {heat_in:.1e} Wh")
    print(f"  2) air {result['T_in_C'][on].min():.2f} to {result['T_in_C'][on].max():.2f} C "
          f"while the thermostat is on")
    print(f"  3) hours with heating or cooling while the thermostat is off: {hvac_off}")
    print(f"  4) hours with heating AND cooling: {both}")


def run_athens_flat():
    """Simulate the old flat with the old window, Case A and Case B, and print the results."""
    weather = load_weather("Athens")
    years = len(set(weather.index.year))

    room = flat_room(OLD_WINDOW)
    print(f"\n=== {room['name']} ===")
    describe_room(room)
    print(f"Balcony (Case A): depth {BALCONY_DEPTH} m, gap above the door {BALCONY_GAP:.1f} m, "
          f"diffuse sky light reaching the door "
          f"{sky_fraction(BALCONY_DEPTH, BALCONY_GAP, WINDOW_HEIGHT):.2f}")

    results = {}
    yearly_tables = []
    for case, depth in CASES.items():
        _, result = simulate_flat(weather, OLD_WINDOW, balcony_depth=depth)
        results[case] = result
        yearly = yearly_demand(result)
        yearly.columns = [f"{case[0]}_{column}" for column in yearly.columns]
        yearly_tables.append(yearly)
    yearly = pd.concat(yearly_tables, axis=1)

    print("\n=== Yearly demand, both cases (thermal energy, kWh) ===")
    print(yearly.round(0))

    print("\n=== 10-year mean (kWh per year) ===")
    rows = []
    for case, result in results.items():
        cooling = result["cooling_W"]
        rows.append({
            "case": case,
            "sun_window": result["window_solar_W"].sum() / 1000 / years,
            "sun_wall": result["wall_solar_W"].sum() / 1000 / years,
            "internal": result["internal_gain_W"].sum() / 1000 / years,
            "heating": result["heating_W"].sum() / 1000 / years,
            "cooling": cooling.sum() / 1000 / years,
            "cooling_outside_below_26C_%": cooling[result["T_out_C"] < T_COOLING].sum()
                                           / cooling.sum() * 100,
        })
    summary = pd.DataFrame(rows).set_index("case")
    print(summary.round(0).to_string())
    a, b = summary.iloc[0], summary.iloc[1]
    print(f"Balcony effect (A - B): heating {a['heating'] - b['heating']:+.0f} kWh "
          f"({(a['heating'] / b['heating'] - 1) * 100:+.0f} %), "
          f"cooling {a['cooling'] - b['cooling']:+.0f} kWh "
          f"({(a['cooling'] / b['cooling'] - 1) * 100:+.0f} %)")

    month = weather.index.month
    monthly = pd.DataFrame({
        f"{case[0]}_{name}": results[case][column].groupby(month).sum() / 1000 / years
        for case in results
        for name, column in (("solar", "solar_gain_W"), ("heating", "heating_W"),
                             ("cooling", "cooling_W"))
    })
    monthly.index.name = "month"
    print("\n=== Monthly mean (kWh per month) ===")
    print(monthly.round(0).T.to_string())

    print("\n=== Other balcony depths (kWh per year) ===")
    for depth in (0.0, 0.5, 1.0, 1.5, 2.0):
        _, result = simulate_flat(weather, OLD_WINDOW, balcony_depth=depth)
        print(f"  depth {depth:.1f} m: heating {result['heating_W'].sum() / 1000 / years:5.0f}, "
              f"cooling {result['cooling_W'].sum() / 1000 / years:5.0f}")

    print("\n=== Sanity checks ===")
    for case, result in results.items():
        print(case)
        check_result(room, result)

    RESULTS_FOLDER.mkdir(exist_ok=True)
    path = RESULTS_FOLDER / "athens_flat_old_window_yearly_demand.csv"
    yearly.round(1).to_csv(path)
    print(f"\nSaved: {path}")
    path = RESULTS_FOLDER / "athens_flat_old_window_monthly.csv"
    monthly.round(1).to_csv(path)
    print(f"Saved: {path}")
    return results


if __name__ == "__main__":
    run_athens_flat()
