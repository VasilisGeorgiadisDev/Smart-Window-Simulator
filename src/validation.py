"""
validation.py
-------------
Test of our room model against professional building simulation programs.

The test is "BESTEST Case 600" of ANSI/ASHRAE Standard 140: a simple room in Denver (USA),
calculated by many programs (EnergyPlus, TRNSYS, ESP-r, ...). Their results are published,
so we can see how far our simple model is from them.

What is the same as in the standard:
    - the room (size, walls, roof, floor, 12 m2 south window), from room_model.py [3]
    - the window: clear double glazing, U = 2.10 W/(m2 K), SHGC = 0.769 [6]
    - air leakage 0.5 air changes per hour at sea level = 0.414 in the thin air of Denver [3]
    - internal gains 200 W, thermostat 20 C / 27 C [3]

What is different (so a perfect match is not expected):
    - weather: the standard uses one "typical year" file for Denver airport.
      We use 10 real years (2014-2023) from PVGIS, with sunlight from the ERA5 weather model.
    - our model is much simpler than the professional programs.
    - not in our model: sun on the outside of walls and roof, and heat radiated to the cold sky.

Three versions of our model are tested, to show what each improvement did:
    1) 1R1C, the same SHGC at every angle of the sun     (the first, simplest version)
    2) 1R1C, SHGC depends on the angle of the sun        (second version)
    3) 5R1C of ISO 13790, SHGC depends on the angle      (the MAIN model)

References
----------
[3] LBNL Modelica Buildings Library, BESTEST validation (see room_model.py). Its user guide
    prints the results of the reference programs and the acceptance limits used below.
[6] ANSI/ASHRAE Addendum a to Standard 140-2017 (see window.py): Table 5-11 (window U-value
    and SHGC) and Annex B6 (SHGC at each incidence angle).

Run:
    python src/validation.py
"""

from pathlib import Path

import pandas as pd

import room_model
from shading import sunlit_fraction, sky_fraction
from sun import sun_position, incidence_angle, profile_angle
from weather import load_weather, CITIES
from window import solar_gain_per_m2

RESULTS_FOLDER = Path(__file__).resolve().parent.parent / "results"

# The BESTEST Case 600 window [6]
BESTEST_WINDOW_U = 2.10
BESTEST_WINDOW_SHGC = 0.769
BESTEST_ANGLE_CURVE = "double clear"

# Air leakage in Denver, corrected for the thin air at 1650 m altitude [3]
BESTEST_AIR_CHANGES = 0.414

# Published results for Case 600, in MWh per year [3]
REFERENCE = {
    "heating": {"programs": (3.993, 4.504), "accepted": (3.75, 4.98)},
    "cooling": {"programs": (5.432, 6.162), "accepted": (5.00, 6.83)},
}

# Case 610 = Case 600 with a 1 m deep overhang 0.5 m above the 2 m high south windows,
# along the whole south wall [3], [6]. Published results in MWh per year [3].
CASE_610_OVERHANG = {"depth": 1.0, "gap": 0.5, "window_height": 2.0}
REFERENCE_610 = {
    "heating": {"programs": (4.066, 4.592), "accepted": (3.61, 5.27)},
    "cooling": {"programs": (4.117, 4.382), "accepted": (2.74, 6.03)},
}


def verdict(value, limits):
    """Is the value inside the limits?"""
    low, high = limits
    if value < low:
        return f"{(value / low - 1) * 100:+.0f} % (too low)"
    if value > high:
        return f"{(value / high - 1) * 100:+.0f} % (too high)"
    return "inside"


def run_validation():
    """Run BESTEST Case 600 in Denver and compare with the published results."""
    # Use the Denver air leakage for this test only.
    # "finally" puts the original value back in every case, even if the test stops with an error.
    original_air_changes = room_model.AIR_CHANGES_PER_HOUR
    room_model.AIR_CHANGES_PER_HOUR = BESTEST_AIR_CHANGES
    try:
        return denver_tests()
    finally:
        room_model.AIR_CHANGES_PER_HOUR = original_air_changes


def denver_tests():
    """The calculations of the validation (called by run_validation)."""
    city = "Denver"
    latitude, longitude = CITIES[city]
    weather = load_weather(city)
    years = len(set(weather.index.year))

    # Solar heat through 1 m2 of glass, with the angle of the sun
    sun = sun_position(weather.index, latitude, longitude)
    angle = incidence_angle(sun, wall_azimuth=0)
    gain_per_m2 = solar_gain_per_m2(weather, angle, BESTEST_WINDOW_SHGC, BESTEST_ANGLE_CURVE)

    # Version 1: 1R1C, the same SHGC at every angle
    version_1 = room_model.simulate_rc(weather, BESTEST_WINDOW_U, BESTEST_WINDOW_SHGC)

    # Version 2: 1R1C with the angle of the sun.
    # The 1R1C function multiplies "its" SHGC by the total sunlight on the wall. So we give it,
    # for every hour, the SHGC that produces exactly the solar gain we calculated.
    hourly_shgc = (gain_per_m2 / weather["total_W_m2"]).fillna(0)      # 0/0 at night -> 0
    version_2 = room_model.simulate_rc(weather, BESTEST_WINDOW_U, hourly_shgc)

    # Version 3: 5R1C (ISO 13790) with the angle of the sun
    room = room_model.bestest_room(BESTEST_WINDOW_U)
    version_3 = room_model.simulate_5r1c(weather, room, gain_per_m2 * room_model.WINDOW_AREA)

    rows = []
    for name, result in [("1) 1R1C, SHGC constant", version_1),
                         ("2) 1R1C, SHGC with sun angle", version_2),
                         ("3) 5R1C, SHGC with sun angle", version_3)]:
        heating = result["heating_W"].sum() / 1e6 / years        # MWh per year
        cooling = result["cooling_W"].sum() / 1e6 / years
        rows.append({
            "model": name,
            "heating_MWh": round(heating, 2),
            "heating_vs_accepted": verdict(heating, REFERENCE["heating"]["accepted"]),
            "cooling_MWh": round(cooling, 2),
            "cooling_vs_accepted": verdict(cooling, REFERENCE["cooling"]["accepted"]),
        })
    table = pd.DataFrame(rows)

    print("\n=== BESTEST Case 600, Denver: our model against the published results ===")
    print(f"Weather: PVGIS {min(weather.index.year)}-{max(weather.index.year)}, "
          f"mean of {years} years (MWh per year)")
    pd.set_option("display.width", 200)
    print(table.to_string(index=False))
    print("\nPublished results [3]:")
    for what, ranges in REFERENCE.items():
        print(f"  {what}: reference programs {ranges['programs'][0]} to {ranges['programs'][1]}, "
              f"accepted range {ranges['accepted'][0]} to {ranges['accepted'][1]} MWh per year")

    print("\n=== Year by year, model 3 (MWh) ===")
    print((room_model.yearly_demand(version_3) / 1000).round(2).rename(
        columns={"heating_kWh": "heating_MWh", "cooling_kWh": "cooling_MWh"}))

    check_5r1c(version_3, room)

    # ---------------- Case 610: the same room with an overhang ----------------
    profile = profile_angle(sun, wall_azimuth=0)
    sunlit = sunlit_fraction(profile, **CASE_610_OVERHANG)
    sky = sky_fraction(**CASE_610_OVERHANG)
    gain_610 = solar_gain_per_m2(weather, angle, BESTEST_WINDOW_SHGC, BESTEST_ANGLE_CURVE,
                                 sunlit=sunlit, sky=sky)
    case_610 = room_model.simulate_5r1c(weather, room, gain_610 * room_model.WINDOW_AREA)
    print()
    print("=== BESTEST Case 610 (1 m overhang), model 3 against the published results ===")
    rows_610 = []
    for what, result_column in (("heating", "heating_W"), ("cooling", "cooling_W")):
        ours_600 = version_3[result_column].sum() / 1e6 / years
        ours_610 = case_610[result_column].sum() / 1e6 / years
        ref = REFERENCE_610[what]
        rows_610.append({
            "": what,
            "ours_600_MWh": round(ours_600, 2),
            "ours_610_MWh": round(ours_610, 2),
            "change_600_to_610_%": round((ours_610 / ours_600 - 1) * 100),
            "programs_610_MWh": f"{ref['programs'][0]} - {ref['programs'][1]}",
            "verdict_610": verdict(ours_610, ref["accepted"]),
        })
    print(pd.DataFrame(rows_610).to_string(index=False))
    print(f"Solar heat through the window, 600 -> 610: "
          f"{gain_per_m2.sum() / 1000 / years:.0f} -> {gain_610.sum() / 1000 / years:.0f} kWh per m2 of glass per year")
    print("Published means of the reference programs: heating 4.213 -> 4.311 (+2 %), "
          "cooling 5.856 -> 4.256 (-27 %)")

    RESULTS_FOLDER.mkdir(exist_ok=True)
    path = RESULTS_FOLDER / "denver_validation.csv"
    table.to_csv(path, index=False)
    print(f"\nSaved: {path}")
    return table


def check_5r1c(result, room):
    """Sanity checks of the 5R1C model: these test the maths, not the physics."""
    print("\n=== Sanity checks, model 3 ===")
    # 1) Energy balance over the whole period:
    #    heat in = heat out + heat counted as lost through the window + change of stored heat
    heat_in = (result["solar_gain_W"] + result["internal_gain_W"] + result["heating_W"]).sum()
    heat_out = (result["cooling_W"] + result["loss_W"] + result["radiant_loss_W"]).sum()
    stored = room["C_mass"] * (result["T_mass_end_C"].iloc[-1] - room["T_heating"])
    print(f"1) Energy balance error: {heat_in - heat_out - stored:.2e} Wh "
          f"of {heat_in:.2e} Wh that entered (should be ~0)")
    # 2) The air temperature must stay between the thermostat settings
    print(f"2) Air temperature: {result['T_in_C'].min():.2f} to {result['T_in_C'].max():.2f} C "
          f"(should be {room['T_heating']:.0f} to {room['T_cooling']:.0f})")
    # 3) Heating and cooling never in the same hour
    both = ((result["heating_W"] > 0) & (result["cooling_W"] > 0)).sum()
    print(f"3) Hours with heating AND cooling: {both} (should be 0)")
    # 4) Surfaces and mass may be warmer or colder than the air, but must stay reasonable
    print(f"4) Surface temperature: {result['T_surface_C'].min():.1f} to "
          f"{result['T_surface_C'].max():.1f} C, mass temperature: "
          f"{result['T_mass_C'].min():.1f} to {result['T_mass_C'].max():.1f} C")


if __name__ == "__main__":
    run_validation()
