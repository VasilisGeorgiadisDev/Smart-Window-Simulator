"""
ec_comparison.py
----------------
Smart (electrochromic, EC) glass against normal glass, in the BESTEST room,
in ATHENS and in AMSTERDAM. Main question of the project:
    in which climate does a smart window save more energy, and why?

Room and model: as in athens_bestest.py (BESTEST Case 600, no shading, 0.5 air changes per
hour at sea level, thermostat 20 / 27 C, 24 h). Both cities are at sea level, so the room is
exactly the same. Only the weather (PVGIS 2014-2023) and the glass change [1], [2]:

    Normal glass : double glazing, low-E, argon       U 1.49, SHGC 0.568, Tvis 0.745 [1]
    Smart glass  : SageGlass Clear with SR2.0         U 1.65 in all states [2]
                       clear        SHGC 0.41   Tvis 0.60
                       light tint   SHGC 0.16   Tvis 0.18
                       full tint    SHGC 0.09   Tvis 0.01

Control rule of the smart glass (in room_model.simulate_5r1c), every hour:
    if the room with CLEAR glass would become warmer than the cooling setpoint (27 C),
    the glass tints for that hour; otherwise it stays clear.
This is a simple rule in an "ideal" form: it knows the room temperature of the hour in advance.
It is NOT the best possible rule: a darker tint (run 5) saves more, and the tint temperature
(27 C) is a choice that is not optimised here. A real controller works with sensors, so it
would likely save a little less than this ideal version of the same rule.

Five runs per city:
    1) normal glass
    2) smart glass, always clear        (the smart glass never switches)
    3) smart glass, always full tint    (dark all year: shows the most sun it can block)
    4) smart glass + rule, tint = light tint      <- main smart-glass case
    5) smart glass + rule, tint = full tint

Two extra results for the comparison of the two cities:
    - Run 1 -> run 2 changes three things at once: the SHGC, the U-value and the angle curve.
      Two extra runs change them one at a time, to show what each one does.
    - The test room can never open a window. So we report how much of the May-October cooling
      (normal glass) happens while the outside air is below 27 C and below 24 C (24 C is our
      choice: clearly cooler than the room). In a real home, part of this cooling would not
      be needed, because a window could be opened.

ASSUMPTIONS:
    - The glass switches within the hour. (Real EC glass needs some minutes to switch.)
    - All states follow the angle curve of clear double glazing (see window.py).
    - Lamps are not modelled: a darker room may need more electric light. We report the
      visible transmittance (Tvis) so that this is not hidden.

Run:
    python src/ec_comparison.py
"""

from pathlib import Path

import pandas as pd

import room_model
from room_model import simulate_5r1c, bestest_room
from sun import sun_position, incidence_angle
from validation import check_5r1c
from weather import load_weather, CITIES
from window import WINDOWS, MAIN_NORMAL, MAIN_EC, solar_gain_per_m2
from athens_bestest import AIR_CHANGES_SEA_LEVEL

RESULTS_FOLDER = Path(__file__).resolve().parent.parent / "results"
CITY_LIST = ["Athens", "Amsterdam"]
MAIN_SMART_RUN = "4) smart + rule, light tint"
SUMMER = [5, 6, 7, 8, 9, 10]          # May to October
WINTER = [11, 12, 1, 2, 3, 4]         # November to April
# Outside air temperatures (C) for the "sealed room" check:
# 27 = the cooling setpoint, 24 = clearly cooler than the room (our choice)
OUTSIDE_LIMITS_C = (27, 24)


def solar_W(weather, angle, window, state):
    """Solar heat through the 12 m2 window in one state (W, one value per hour)."""
    shgc = window["states"][state]["SHGC"]
    return solar_gain_per_m2(weather, angle, shgc, window["angle_curve"]) * room_model.WINDOW_AREA


def make_room(window):
    """The BESTEST room with this window, air leakage at sea level."""
    room = bestest_room(window["U"])
    room["H_ventilation"] = room_model.AIR_HEAT_CAPACITY * AIR_CHANGES_SEA_LEVEL * room_model.VOLUME
    return room


def run_city(city):
    """The five runs for one city. Returns the summary table and the hourly results."""
    weather = load_weather(city)
    years = len(set(weather.index.year))
    latitude, longitude = CITIES[city]
    angle = incidence_angle(sun_position(weather.index, latitude, longitude), wall_azimuth=0)
    sunny = (weather["total_W_m2"] > 0).to_numpy()          # hours with daylight on the window

    normal, ec = WINDOWS[MAIN_NORMAL], WINDOWS[MAIN_EC]
    normal_room, ec_room = make_room(normal), make_room(ec)
    tvis = {state: values["Tvis"] for state, values in ec["states"].items()}

    # name -> (room, solar with clear/fixed glass, solar when tinted or None, Tvis clear, Tvis tinted)
    runs = {
        "1) normal glass": (normal_room, solar_W(weather, angle, normal, "fixed"), None,
                            normal["states"]["fixed"]["Tvis"], None),
        "2) smart, always clear": (ec_room, solar_W(weather, angle, ec, "clear"), None,
                                   tvis["clear"], None),
        "3) smart, always full tint": (ec_room, solar_W(weather, angle, ec, "full tint"), None,
                                       tvis["full tint"], None),
        "4) smart + rule, light tint": (ec_room, solar_W(weather, angle, ec, "clear"),
                                        solar_W(weather, angle, ec, "light tint"),
                                        tvis["clear"], tvis["light tint"]),
        "5) smart + rule, full tint": (ec_room, solar_W(weather, angle, ec, "clear"),
                                       solar_W(weather, angle, ec, "full tint"),
                                       tvis["clear"], tvis["full tint"]),
    }

    results, rows = {}, []
    for name, (room, solar, solar_tinted, tvis_clear, tvis_tinted) in runs.items():
        result = simulate_5r1c(weather, room, solar, solar_gain_tinted_W=solar_tinted)
        results[name] = result
        tinted = result["tinted"].to_numpy()
        # mean visible transmittance over the daylight hours (how bright the room is)
        tvis_hourly = pd.Series(tvis_clear, index=result.index)
        if tvis_tinted is not None:
            tvis_hourly[tinted] = tvis_tinted
        # share of the daylight hours with the glass tinted
        if name == "1) normal glass":
            tinted_share = float("nan")                  # a normal glass cannot tint ("–")
        elif name == "3) smart, always full tint":
            tinted_share = 100.0                         # dark all the time
        else:
            tinted_share = tinted[sunny].sum() / sunny.sum() * 100
        rows.append({
            "run": name,
            "solar_kWh": result["solar_gain_W"].sum() / 1000 / years,
            "heating_kWh": result["heating_W"].sum() / 1000 / years,
            "cooling_kWh": result["cooling_W"].sum() / 1000 / years,
            "tinted_%_of_daylight": tinted_share,
            "mean_Tvis_daylight": tvis_hourly[sunny].mean(),
        })
    table = pd.DataFrame(rows).set_index("run")
    table["total_kWh"] = table["heating_kWh"] + table["cooling_kWh"]
    base = table.loc["1) normal glass"]
    for what in ("heating", "cooling", "total"):
        table[f"{what}_vs_normal_%"] = (table[f"{what}_kWh"] / base[f"{what}_kWh"] - 1) * 100

    print(f"\n==================== {city} ====================")
    print("10-year mean 2014-2023, kWh of heat per year:")
    print(table[["solar_kWh", "heating_kWh", "cooling_kWh", "total_kWh", "total_vs_normal_%"]]
          .round(0).to_string())
    print("\nChange against the normal glass (%), tinting and daylight:")
    print(table[["heating_vs_normal_%", "cooling_vs_normal_%", "tinted_%_of_daylight",
                 "mean_Tvis_daylight"]].round(2).to_string())

    for name in ("4) smart + rule, light tint", "5) smart + rule, full tint"):
        result = results[name]
        print(f"\n{city}, {name}")
        check_5r1c(result, ec_room)
        both = (result["tinted"] & (result["heating_W"] > 0)).sum()
        print(f"5) Hours with the glass tinted AND heating: {both} (should be 0)")

    clear_state = clear_state_steps(weather, angle, table)
    print(f"\n{city}, run 1 -> run 2, one change at a time (kWh saved per year, negative = more energy):")
    for what, saved in clear_state.items():
        print(f"  {what:12s} {saved:7.0f}")
    return weather, table, results, clear_state


def clear_state_steps(weather, angle, table):
    """
    Run 1 -> run 2 changes three things at once: the SHGC, the U-value and the angle curve.
    Two extra runs change them one at a time, to see what each one does.
    Returns the kWh saved per year by each change (negative = more energy).
    """
    years = len(set(weather.index.year))
    normal, ec = WINDOWS[MAIN_NORMAL], WINDOWS[MAIN_EC]
    shgc_clear = ec["states"]["clear"]["SHGC"]
    # Step a: the normal glass, but with the SHGC of the clear smart glass
    only_shgc = {"U": normal["U"], "angle_curve": normal["angle_curve"],
                 "states": {"clear": {"SHGC": shgc_clear}}}
    # Step b: also the U-value of the smart glass (adding its angle curve too gives run 2)
    shgc_and_u = {"U": ec["U"], "angle_curve": normal["angle_curve"],
                  "states": {"clear": {"SHGC": shgc_clear}}}

    total = {"run 1": table.loc["1) normal glass", "total_kWh"],
             "run 2": table.loc["2) smart, always clear", "total_kWh"]}
    for step, window in (("a", only_shgc), ("b", shgc_and_u)):
        result = simulate_5r1c(weather, make_room(window), solar_W(weather, angle, window, "clear"))
        total[step] = (result["heating_W"] + result["cooling_W"]).sum() / 1000 / years
    return {
        "SHGC": total["run 1"] - total["a"],
        "U-value": total["a"] - total["b"],
        "angle curve": total["b"] - total["run 2"],
    }


def monthly_table(weather, results):
    """Month by month: normal glass vs the main smart-glass case (kWh per month, mean of the years)."""
    years = len(set(weather.index.year))
    month = weather.index.month
    pairs = {"normal": results["1) normal glass"], "smart": results[MAIN_SMART_RUN]}
    monthly = pd.DataFrame({
        f"{key}_{what}_kWh": result[f"{what}_W"].groupby(month).sum() / 1000 / years
        for key, result in pairs.items() for what in ("heating", "cooling")
    })
    monthly["smart_tinted_hours"] = pairs["smart"]["tinted"].groupby(month).sum() / years
    monthly["T_out_mean_C"] = weather["T_out_C"].groupby(month).mean()
    monthly["sun_on_facade_kWh_m2"] = weather["total_W_m2"].groupby(month).sum() / 1000 / years
    monthly.index.name = "month"
    return monthly


def city_comparison(city, weather, table, results, clear_state):
    """One row of the final comparison table."""
    years = len(set(weather.index.year))
    normal, smart = results["1) normal glass"], results[MAIN_SMART_RUN]
    month = weather.index.month
    summer = month.isin(SUMMER)
    saved = table.loc["1) normal glass", "total_kWh"] - table.loc[MAIN_SMART_RUN, "total_kWh"]
    saved_summer = ((normal["heating_W"] + normal["cooling_W"])[summer].sum()
                    - (smart["heating_W"] + smart["cooling_W"])[summer].sum()) / 1000 / years
    row = {
        "city": city,
        "mean_T_out_C": weather["T_out_C"].mean(),
        "sun_on_facade_kWh_m2": weather["total_W_m2"].sum() / 1000 / years,
        "normal_heating_kWh": table.loc["1) normal glass", "heating_kWh"],
        "normal_cooling_kWh": table.loc["1) normal glass", "cooling_kWh"],
        "smart_heating_kWh": table.loc[MAIN_SMART_RUN, "heating_kWh"],
        "smart_cooling_kWh": table.loc[MAIN_SMART_RUN, "cooling_kWh"],
        "saved_kWh": saved,
        "saved_%": saved / table.loc["1) normal glass", "total_kWh"] * 100,
        "saved_May_Oct_kWh": saved_summer,
        "saved_Nov_Apr_kWh": saved - saved_summer,
        "saved_from_clear_state_kWh": table.loc["1) normal glass", "total_kWh"]
                                      - table.loc["2) smart, always clear", "total_kWh"],
        "saved_from_switching_kWh": table.loc["2) smart, always clear", "total_kWh"]
                                    - table.loc[MAIN_SMART_RUN, "total_kWh"],
        # what each difference of the clear state does (see clear_state_steps)
        "clear_state_SHGC_kWh": clear_state["SHGC"],
        "clear_state_U_value_kWh": clear_state["U-value"],
        "clear_state_angle_curve_kWh": clear_state["angle curve"],
    }
    # The test room can never open a window. How much of the summer cooling (normal glass)
    # happens while the outside air is cooler than the room?
    summer_cooling = normal["cooling_W"][summer]
    summer_T_out = weather["T_out_C"][summer]
    for limit in OUTSIDE_LIMITS_C:
        row[f"cooling_May_Oct_T_out_below_{limit}C_%"] = (
            summer_cooling[summer_T_out < limit].sum() / summer_cooling.sum() * 100)
    return row


def run_comparison():
    pd.set_option("display.width", 220)
    RESULTS_FOLDER.mkdir(exist_ok=True)
    rows = []
    for city in CITY_LIST:
        weather, table, results, clear_state = run_city(city)
        monthly = monthly_table(weather, results)
        print(f"\n{city}, month by month: normal glass vs smart glass + rule (light tint)")
        print(monthly.round(0).T.to_string())
        rows.append(city_comparison(city, weather, table, results, clear_state))
        table.round(2).to_csv(RESULTS_FOLDER / f"{city.lower()}_ec_comparison.csv")
        monthly.round(2).to_csv(RESULTS_FOLDER / f"{city.lower()}_ec_monthly.csv")

    comparison = pd.DataFrame(rows).set_index("city")
    print("\n==================== Athens vs Amsterdam (same room, same glass) ====================")
    print("Smart glass = SageGlass with the rule, light tint. kWh of heat per year.")
    print(comparison.round(1).T.to_string())
    path = RESULTS_FOLDER / "city_comparison.csv"
    comparison.round(2).to_csv(path)
    print(f"\nSaved: {path}, and the tables of each city in {RESULTS_FOLDER}")
    return comparison


if __name__ == "__main__":
    run_comparison()
