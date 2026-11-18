"""
athens_bestest.py
-----------------
The BESTEST room (ANSI/ASHRAE Standard 140) in ATHENS: the fixed test environment of the
project (decided 17 Nov 2026).

The room is fixed by the standard [3]. It is the same room that passed the Denver test in
validation.py: 8 x 6 x 2.7 m, light (wood and insulation), 12 m2 of window facing south,
200 W of internal gains day and night, thermostat 20 C / 27 C, 24 hours a day.

Only these things change here:
    - the weather: Athens, PVGIS 2014-2023 (real hourly data)
    - the air leakage: 0.5 air changes per hour, the value of the standard at sea level [3]
      (the Denver test used 0.414 because of the thin air at 1650 m)
    - the window (glass only, as in the standard):
        1) the BESTEST window: clear double glazing, U 2.10, SHGC 0.769 [6]
           -> the same window as in the Denver test, so the two cities can be compared
        2) our normal window: double glazing, low-E, argon, U 1.493, SHGC 0.568 [1]
           -> the reference for the smart window in the next phase
    - Case 600: no shading. Case 610: the 1 m overhang of the standard, 0.5 m above the window.

Run:
    python src/athens_bestest.py
"""

from pathlib import Path

import pandas as pd

import room_model
from room_model import simulate_5r1c, yearly_demand, bestest_room
from shading import sunlit_fraction, sky_fraction
from sun import sun_position, incidence_angle, profile_angle
from validation import (BESTEST_WINDOW_U, BESTEST_WINDOW_SHGC, BESTEST_ANGLE_CURVE,
                        BESTEST_AIR_CHANGES, CASE_610_OVERHANG, check_5r1c)
from weather import load_weather, CITIES
from window import WINDOWS, MAIN_NORMAL, solar_gain_per_m2

RESULTS_FOLDER = Path(__file__).resolve().parent.parent / "results"

AIR_CHANGES_SEA_LEVEL = 0.5     # air changes per hour [3]

# The two windows: name -> (U, SHGC, angle curve)
normal = WINDOWS[MAIN_NORMAL]
TEST_WINDOWS = {
    "BESTEST window (double clear)": (BESTEST_WINDOW_U, BESTEST_WINDOW_SHGC, BESTEST_ANGLE_CURVE),
    "Normal window (double low-E)": (normal["U"], normal["states"]["fixed"]["SHGC"],
                                     normal["angle_curve"]),
}


def run_room(weather, city, window, overhang=False, air_changes=AIR_CHANGES_SEA_LEVEL):
    """Simulate the BESTEST room for one city, one window, with or without the overhang."""
    U, shgc, curve = window
    latitude, longitude = CITIES[city]
    room = bestest_room(U)
    # air leakage of this run (W/K) = 0.33 Wh/(m3 K) x air changes per hour x volume
    room["H_ventilation"] = room_model.AIR_HEAT_CAPACITY * air_changes * room_model.VOLUME

    sun = sun_position(weather.index, latitude, longitude)
    angle = incidence_angle(sun, wall_azimuth=0)
    if overhang:
        sunlit = sunlit_fraction(profile_angle(sun, wall_azimuth=0), **CASE_610_OVERHANG)
        sky = sky_fraction(**CASE_610_OVERHANG)
    else:
        sunlit, sky = 1.0, 1.0
    solar = solar_gain_per_m2(weather, angle, shgc, curve, sunlit=sunlit, sky=sky) \
        * room_model.WINDOW_AREA
    return room, simulate_5r1c(weather, room, solar)


def summary_row(name, result, years):
    """10-year mean, lowest and highest year, in kWh per year."""
    yearly = yearly_demand(result)
    return {
        "run": name,
        "solar_kWh": result["solar_gain_W"].sum() / 1000 / years,
        "heating_kWh": yearly["heating_kWh"].mean(),
        "heating_min": yearly["heating_kWh"].min(),
        "heating_max": yearly["heating_kWh"].max(),
        "cooling_kWh": yearly["cooling_kWh"].mean(),
        "cooling_min": yearly["cooling_kWh"].min(),
        "cooling_max": yearly["cooling_kWh"].max(),
    }


def run_athens_bestest():
    athens = load_weather("Athens")
    years = len(set(athens.index.year))

    room = bestest_room(BESTEST_WINDOW_U)
    room["H_ventilation"] = room_model.AIR_HEAT_CAPACITY * AIR_CHANGES_SEA_LEVEL * room_model.VOLUME
    print("\n=== The BESTEST room in Athens (fixed by the standard) ===")
    print(f"Floor {room_model.FLOOR_AREA:.0f} m2, window {room_model.WINDOW_AREA:.0f} m2 facing south, "
          f"internal gains {room['internal_gains_W']:.0f} W, thermostat "
          f"{room['T_heating']:.0f} / {room['T_cooling']:.0f} C, 24 h")
    print(f"Heat loss (W/K): walls + roof + floor {room['H_opaque']:.1f}, "
          f"air {room['H_ventilation']:.1f}, window: U x 12 m2 (depends on the window)")
    print(f"Heat capacity {room['C_mass']:.0f} Wh/K (light building)")

    # ---- 1) Both windows, Case 600 and Case 610 ----
    rows, results = [], {}
    for window_name, window in TEST_WINDOWS.items():
        for case, overhang in (("600", False), ("610", True)):
            name = f"{window_name}, Case {case}"
            _, result = run_room(athens, "Athens", window, overhang=overhang)
            results[name] = result
            rows.append(summary_row(name, result, years))
    table = pd.DataFrame(rows).set_index("run")
    pd.set_option("display.width", 200)
    print("\n=== Athens, 10-year mean 2014-2023 (thermal energy, kWh per year) ===")
    print(table.round(0).to_string())

    # ---- 2) The same room and window in Denver and Athens ----
    denver = load_weather("Denver")
    window = TEST_WINDOWS["BESTEST window (double clear)"]
    _, denver_result = run_room(denver, "Denver", window, air_changes=BESTEST_AIR_CHANGES)
    athens_result = results["BESTEST window (double clear), Case 600"]
    print("\n=== Same room, same window (BESTEST, Case 600): Denver vs Athens (kWh per year) ===")
    for city, result, weather in (("Denver", denver_result, denver), ("Athens", athens_result, athens)):
        n = len(set(weather.index.year))
        print(f"  {city:7s} heating {result['heating_W'].sum() / 1000 / n:6.0f}   "
              f"cooling {result['cooling_W'].sum() / 1000 / n:6.0f}   "
              f"mean outside temperature {weather['T_out_C'].mean():4.1f} C   "
              f"sun on the south wall {weather['total_W_m2'].sum() / 1000 / n:5.0f} kWh/m2")

    # ---- 3) When does the room need cooling? (normal window, Case 600) ----
    main = results["Normal window (double low-E), Case 600"]
    cooling = main["cooling_W"]
    winter = main.index.month.isin([11, 12, 1, 2, 3, 4])
    print("\n=== Normal window, Case 600: when is cooling needed? ===")
    print(f"  cooling while the outside air is below 27 C: "
          f"{cooling[main['T_out_C'] < room['T_cooling']].sum() / cooling.sum() * 100:.0f} %")
    print(f"  cooling from November to April: {cooling[winter].sum() / cooling.sum() * 100:.0f} %")

    month = main.index.month
    monthly = pd.DataFrame({
        "solar_kWh": main["solar_gain_W"].groupby(month).sum() / 1000 / years,
        "heating_kWh": main["heating_W"].groupby(month).sum() / 1000 / years,
        "cooling_kWh": cooling.groupby(month).sum() / 1000 / years,
        "T_out_mean_C": main["T_out_C"].groupby(month).mean(),
    })
    monthly.index.name = "month"
    print("\n=== Normal window, Case 600: monthly mean ===")
    print(monthly.round(1).T.to_string())

    # ---- 4) Sanity checks ----
    for name in ("BESTEST window (double clear), Case 600", "Normal window (double low-E), Case 600"):
        print(f"\n{name}")
        check_5r1c(results[name], room)

    RESULTS_FOLDER.mkdir(exist_ok=True)
    path = RESULTS_FOLDER / "athens_bestest_yearly_demand.csv"
    table.round(1).to_csv(path)
    print(f"\nSaved: {path}")
    path = RESULTS_FOLDER / "athens_bestest_monthly_normal_window.csv"
    monthly.round(1).to_csv(path)
    print(f"Saved: {path}")
    return table, results


if __name__ == "__main__":
    run_athens_bestest()
