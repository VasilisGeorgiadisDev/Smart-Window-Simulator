"""
room_model.py
-------------
Hourly energy balance of one room with one south-facing window.
Three models are included, from the simplest to the best:

1) STEADY-STATE model (no thermal mass) - simulate_steady()
   The room reacts to sun and outside temperature immediately.

       heat loss coefficient   H  = sum(U x A) + ventilation                [W/K]
       gains                   Q  = SHGC x A_window x G_facade + internal   [W]
       free temperature        T_free = T_out + Q / H
       heating if T_free < 20 C, cooling if T_free > 27 C

2) 1R1C model (one resistance, one capacitance) - simulate_rc()
   Like an RC circuit: R = 1/H is the path for heat to the outside,
   C is the heat stored in the room air and in the inner layers of walls, roof and floor.

       C dT/dt = Q + Q_hvac - H (T - T_out)

   Q_hvac is heating (+) or cooling (-), just enough to keep T between 20 and 27 C.
   Solved hour by hour with the implicit (backward) Euler method, which is always stable:

       C (T_new - T_old) / dt = Q + Q_hvac - H (T_new - T_out)

   If C -> 0, the 1R1C model becomes exactly the steady-state model (we test this).

3) 5R1C model (five resistances, one capacitance) - simulate_5r1c()
   The "simple hourly method" of the standard ISO 13790 [7]. This is the MAIN model.
   The room has three temperatures: the air, the inner surfaces, and the heavy mass.
   The sun's heat goes to the surfaces and the mass, not directly to the air, so the room
   reacts more slowly and more realistically than in model 2.
   Tested against professional programs in validation.py.
   All its equations are written out in docs/equations.md (section 3).

The room is the BESTEST "Case 600" test room (ANSI/ASHRAE Standard 140), a light-weight
room used worldwide to test building simulation programs.

References
----------
[3] BESTEST Case 600 as implemented in the LBNL Modelica Buildings Library
    (ANSI/ASHRAE Standard 140), model Buildings.ThermalZones.Detailed.Validation.BESTEST.Cases6xx,
    https://simulationresearch.lbl.gov/modelica/releases/latest/help/Buildings_ThermalZones_Detailed_Validation_BESTEST_Cases6xx.html
    accessed 13 Nov 2026. Gives: room size, window size, wall/roof/floor layers (thickness,
    conductivity, density, specific heat), infiltration 0.5 air changes per hour (at sea level),
    internal gains 200 W, setpoints 20 C (heating) and 27 C (cooling).
[4] ISO 6946:2007, "Building components and building elements - Thermal resistance and
    thermal transmittance - Calculation method". Table 1: surface resistances
    R_si = 0.13 and R_se = 0.04 m2K/W (horizontal heat flow, also advised when the direction
    of heat flow changes). Eq. (3): heat capacity of air 0.33 Wh/(m3 K).

[7] ISO 13790:2008, "Energy performance of buildings - Calculation of energy use for space
    heating and cooling", simple hourly method (clause 7.2.2 and Annex C). The standard is
    not free. The equations C.1 to C.13 were taken from the open-source program
    RC_BuildingSimulator (ETH Zurich), file rc_simulator/building_physics.py, which quotes
    the equation numbers of the standard:
    https://github.com/architecture-building-systems/RC_BuildingSimulator
    accessed 17 Nov 2026. It also gives the constants 3.45 and 9.1 W/(m2 K) and the mass
    area of 2.5 x floor area.
[8] ISO/FDIS 13790:2007 (final draft of the standard), clause 12.2.2, Equations (64) and (65):
    split of the wall path into H_em and H_ms; clause 12.3.1.2, Table 12: default heat
    capacity and mass area for five classes (very light to very heavy). Public copy:
    appendix 2 of a final-year project, Escuela Tecnica Superior de Ingenieros, Sevilla,
    https://ereding.etsi.us.es/bibing/proyectos/abreproy/80004/

Run this file directly to compare the models for Athens with the normal window:
    python src/room_model.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

from weather import load_weather
from window import WINDOWS, MAIN_NORMAL

RESULTS_FOLDER = Path(__file__).resolve().parent.parent / "results"

# ---------------- Room geometry [3] ----------------
LENGTH = 8.0          # m, south and north walls
WIDTH = 6.0           # m, east and west walls
HEIGHT = 2.7          # m
WINDOW_AREA = 12.0    # m2, south wall (two windows of 3 m x 2 m), frame ignored

FLOOR_AREA = LENGTH * WIDTH                  # 48 m2
VOLUME = FLOOR_AREA * HEIGHT                 # 129.6 m3
WALL_AREA = 2 * (LENGTH + WIDTH) * HEIGHT - WINDOW_AREA   # opaque walls: 63.6 m2

# ---------------- Constructions [3] ----------------
# Each layer: (thickness in m, thermal conductivity in W/(m K)), from outside to inside
WALL_LAYERS = [(0.009, 0.140),     # wood siding
               (0.066, 0.040),     # insulation
               (0.012, 0.160)]     # plasterboard
ROOF_LAYERS = [(0.019, 0.140),     # roof deck
               (0.1118, 0.040),    # insulation
               (0.010, 0.160)]     # plasterboard
FLOOR_LAYERS = [(1.003, 0.040),    # very thick insulation (floor almost adiabatic)
                (0.025, 0.140)]    # timber floor

# Surface resistances [4], m2 K/W
R_SI = 0.13           # inside surface
R_SE = 0.04           # outside surface

# ---------------- Thermal mass (for the 1R1C model) ----------------
# ASSUMPTION: only the layers on the INSIDE of the insulation store heat for the room
# (the insulation separates the outer layers from the room). Values from [3]:
# (name, area m2, thickness m, density kg/m3, specific heat J/(kg K))
INNER_MASS_LAYERS = [
    ("wall plasterboard", WALL_AREA, 0.012, 950, 840),
    ("roof plasterboard", FLOOR_AREA, 0.010, 950, 840),
    ("timber floor", FLOOR_AREA, 0.025, 650, 1200),
]

# ---------------- Air, people, devices, thermostat ----------------
AIR_CHANGES_PER_HOUR = 0.5      # infiltration [3]
AIR_HEAT_CAPACITY = 0.33        # Wh/(m3 K) [4]
INTERNAL_GAINS_W = 200.0        # constant, day and night [3]
T_HEATING = 20.0                # deg C [3]
T_COOLING = 27.0                # deg C [3]


def u_value(layers):
    """U-value of a wall made of layers: U = 1 / (R_si + sum(thickness/conductivity) + R_se)."""
    resistance = R_SI + sum(thickness / conductivity for thickness, conductivity in layers) + R_SE
    return 1 / resistance


def heat_loss_coefficients(window_U):
    """Heat loss coefficient of each part of the room, in W/K (= U x A, or ventilation)."""
    return {
        "walls": u_value(WALL_LAYERS) * WALL_AREA,
        "roof": u_value(ROOF_LAYERS) * FLOOR_AREA,
        "floor": u_value(FLOOR_LAYERS) * FLOOR_AREA,
        "window": window_U * WINDOW_AREA,
        # 0.33 Wh/(m3 K) x air changes per hour x volume = W/K
        "ventilation": AIR_HEAT_CAPACITY * AIR_CHANGES_PER_HOUR * VOLUME,
    }


def heat_capacities():
    """Heat capacity of each part that stores heat, in Wh/K (1 Wh = 3600 J)."""
    parts = {name: area * thickness * density * specific_heat / 3600
             for name, area, thickness, density, specific_heat in INNER_MASS_LAYERS}
    parts["room air"] = AIR_HEAT_CAPACITY * VOLUME
    return parts


def gains(weather, shgc):
    """Solar gain through the window and internal gains, in W (one value per hour)."""
    solar = shgc * WINDOW_AREA * weather["total_W_m2"]
    return solar, pd.Series(INTERNAL_GAINS_W, index=weather.index)


def simulate_steady(weather, window_U, shgc):
    """Steady-state model (no thermal mass). shgc: one number, or one value per hour."""
    H = sum(heat_loss_coefficients(window_U).values())          # W/K
    solar, internal = gains(weather, shgc)

    result = pd.DataFrame(index=weather.index)
    result["T_out_C"] = weather["T_out_C"]
    result["solar_gain_W"] = solar
    result["internal_gain_W"] = internal
    T_free = result["T_out_C"] + (solar + internal) / H
    result["heating_W"] = (H * (T_HEATING - T_free)).clip(lower=0)
    result["cooling_W"] = (H * (T_free - T_COOLING)).clip(lower=0)
    result["T_in_C"] = T_free.clip(lower=T_HEATING, upper=T_COOLING)
    return result


def simulate_rc(weather, window_U, shgc, capacity_Wh_K=None):
    """
    1R1C model. shgc: one number, or one value per hour.
    capacity_Wh_K: heat capacity C of the room; if not given, use heat_capacities().
    """
    H = sum(heat_loss_coefficients(window_U).values())          # W/K
    if capacity_Wh_K is None:
        capacity_Wh_K = sum(heat_capacities().values())
    C_per_step = capacity_Wh_K / 1.0     # C / dt in W/K, with a time step dt of 1 hour

    solar, internal = gains(weather, shgc)
    T_out = weather["T_out_C"].to_numpy()
    Q = (solar + internal).to_numpy()

    hours = len(T_out)
    T_in = np.zeros(hours)
    heating = np.zeros(hours)
    cooling = np.zeros(hours)
    T_old = T_HEATING                    # start the simulation at 20 C

    for i in range(hours):
        # Temperature at the end of this hour WITHOUT heating or cooling
        T_free = (C_per_step * T_old + H * T_out[i] + Q[i]) / (C_per_step + H)

        if T_free < T_HEATING:
            T_new = T_HEATING
        elif T_free > T_COOLING:
            T_new = T_COOLING
        else:
            T_new = T_free

        # Heating/cooling power needed to reach T_new (from the balance equation)
        Q_hvac = (C_per_step + H) * T_new - C_per_step * T_old - H * T_out[i] - Q[i]
        if Q_hvac > 0:
            heating[i] = Q_hvac
        else:
            cooling[i] = -Q_hvac

        T_in[i] = T_new
        T_old = T_new

    result = pd.DataFrame(index=weather.index)
    result["T_out_C"] = T_out
    result["solar_gain_W"] = solar
    result["internal_gain_W"] = internal
    result["heating_W"] = heating
    result["cooling_W"] = cooling
    result["T_in_C"] = T_in
    return result


# ---------------- 5R1C model: simple hourly method of ISO 13790 [7] ----------------
# The numbers in the names of the equations (C.1, C.2, ...) are those of ISO 13790, Annex C.
H_AIR_SURFACE = 3.45             # W/(m2 K), between the room air and the inner surfaces
H_SURFACE_MASS = 9.1             # W/(m2 K), between the inner surfaces and the heavy mass
MASS_AREA_PER_FLOOR_AREA = 2.5   # effective mass area / floor area, light and medium rooms [8]


def bestest_room(window_U):
    """The BESTEST Case 600 room, as the list of numbers that the 5R1C model needs."""
    parts = heat_loss_coefficients(window_U)
    capacities = heat_capacities()
    return {
        "name": "BESTEST Case 600",
        "floor_area": FLOOR_AREA,                                              # m2
        # all surfaces that face the room: floor + ceiling + four walls (with the window)
        "inner_surface_area": 2 * FLOOR_AREA + 2 * (LENGTH + WIDTH) * HEIGHT,  # m2
        "H_window": parts["window"],                                           # W/K
        "H_opaque": parts["walls"] + parts["roof"] + parts["floor"],           # W/K
        "H_ventilation": parts["ventilation"],                                 # W/K
        # heat stored in the walls, roof and floor (the room air is not counted in this model)
        "C_mass": sum(capacities.values()) - capacities["room air"],           # Wh/K
        "internal_gains_W": INTERNAL_GAINS_W,
        "T_heating": T_HEATING,
        "T_cooling": T_COOLING,
    }


def simulate_5r1c(weather, room, solar_gain_W, thermostat_on=None, solar_gain_tinted_W=None):
    """
    5R1C model (5 resistances, 1 capacitance): the simple hourly method of ISO 13790.

    The room has three temperatures instead of one:
        T_air      the room air (this is what the thermostat feels)
        T_surface  the inner surfaces of walls, floor and ceiling
        T_mass     the heavy material behind the surfaces, which stores heat
    The sun's heat goes to the surfaces and the mass, NOT directly to the air.

    weather      : table from weather.load_weather()
    room         : dictionary of room numbers, e.g. from bestest_room()
    solar_gain_W : solar heat entering the room (window, and the sun on the walls if used),
                   in W, one value per hour
    room["internal_gains_W"] may be one number (constant) or one value per hour.
    thermostat_on: True/False for every hour (False = no heating or cooling in that hour).
                   If not given, the thermostat works 24 hours a day.
    solar_gain_tinted_W: only for a smart (EC) window. solar_gain_W is then the solar heat
                   with the glass CLEAR, and this one with the glass TINTED, one value per hour.
                   Control rule, every hour: if the room with clear glass would become warmer
                   than the cooling setpoint, the glass tints for that hour; otherwise it
                   stays clear. The column "tinted" of the result says what the glass did.
    """
    A_total = room["inner_surface_area"]
    # Effective mass area: the room may give its own (heavy buildings), otherwise 2.5 x floor
    A_mass = room.get("mass_area", MASS_AREA_PER_FLOOR_AREA * room["floor_area"])
    C = room["C_mass"] / 1.0             # C / dt in W/K, with a time step dt of 1 hour

    # The five heat paths (conductances, W/K)
    H_ve = room["H_ventilation"]                    # air <-> outside (fresh air)
    H_w = room["H_window"]                          # surfaces <-> outside (through the window)
    H_is = H_AIR_SURFACE * A_total                  # air <-> surfaces
    H_ms = H_SURFACE_MASS * A_mass                  # surfaces <-> mass
    H_em = 1 / (1 / room["H_opaque"] - 1 / H_ms)    # mass <-> outside, ISO eq. (64) [8]
    # Three combinations that make the equations shorter (C.6, C.7, C.8)
    H_1 = 1 / (1 / H_ve + 1 / H_is)
    H_2 = H_1 + H_w
    H_3 = 1 / (1 / H_2 + 1 / H_ms)

    def one_hour(T_mass_old, T_out, Q_internal, Q_solar, Q_hvac):
        """Temperatures at the end of one hour, for a given heating (+) or cooling (-) power."""
        # Where the heat goes (C.1, C.2, C.3). Heating and cooling go to the air.
        Q_air = 0.5 * Q_internal + Q_hvac
        Q_mass = A_mass / A_total * (0.5 * Q_internal + Q_solar)
        Q_surface = (1 - A_mass / A_total - H_w / (H_SURFACE_MASS * A_total)) \
            * (0.5 * Q_internal + Q_solar)
        # New temperature of the mass (C.4, C.5), Crank-Nicolson method
        Q_mass_total = Q_mass + H_em * T_out \
            + H_3 * (Q_surface + H_w * T_out + H_1 * (Q_air / H_ve + T_out)) / H_2
        T_mass_new = (T_mass_old * (C - 0.5 * (H_3 + H_em)) + Q_mass_total) / (C + 0.5 * (H_3 + H_em))
        # Mean mass temperature during the hour (C.9), then surfaces (C.10) and air (C.11)
        T_mass = (T_mass_new + T_mass_old) / 2
        T_surface = (H_ms * T_mass + Q_surface + H_w * T_out + H_1 * (T_out + Q_air / H_ve)) \
            / (H_ms + H_w + H_1)
        T_air = (H_is * T_surface + H_ve * T_out + Q_air) / (H_is + H_ve)
        return T_mass_new, T_mass, T_surface, T_air

    T_out = weather["T_out_C"].to_numpy()
    Q_solar = np.asarray(solar_gain_W, dtype=float)
    Q_tinted = None if solar_gain_tinted_W is None else np.asarray(solar_gain_tinted_W, dtype=float)
    Q_used = Q_solar.copy()               # the solar heat that really entered, hour by hour
    tinted = np.zeros(len(T_out), dtype=bool)
    # Heat from people, devices and lamps: one number (the same every hour) or one value per hour.
    # np.broadcast_to turns a single number into a list with the same value for every hour.
    Q_internal = np.broadcast_to(np.asarray(room["internal_gains_W"], dtype=float), T_out.shape)
    Q_test = 10.0 * room["floor_area"]    # a trial heating power of 10 W per m2 of floor (C.4.2)

    hours = len(T_out)
    T_air = np.zeros(hours)
    T_surface = np.zeros(hours)
    T_mass = np.zeros(hours)
    T_mass_end = np.zeros(hours)
    heating = np.zeros(hours)
    cooling = np.zeros(hours)
    T_mass_old = room["T_heating"]        # start the simulation at the heating setpoint
    if thermostat_on is not None:
        thermostat_on = np.asarray(thermostat_on, dtype=bool)

    for i in range(hours):
        # Step 1: the hour WITHOUT heating or cooling (a smart window is clear)
        state = one_hour(T_mass_old, T_out[i], Q_internal[i], Q_solar[i], 0.0)
        T_air_free = state[3]

        # Smart window rule: would the room get too warm with clear glass? Then tint.
        # (Only when tinting changes something, i.e. when the sun is shining.)
        if Q_tinted is not None and T_air_free > room["T_cooling"] and Q_tinted[i] < Q_solar[i]:
            tinted[i] = True
            Q_used[i] = Q_tinted[i]
            state = one_hour(T_mass_old, T_out[i], Q_internal[i], Q_used[i], 0.0)
            T_air_free = state[3]

        # Step 2: is the thermostat on, and is the air outside its range?
        if thermostat_on is not None and not thermostat_on[i]:
            T_target = None
        elif T_air_free < room["T_heating"]:
            T_target = room["T_heating"]
        elif T_air_free > room["T_cooling"]:
            T_target = room["T_cooling"]
        else:
            T_target = None

        # Step 3: if yes, find the power that brings the air exactly to the setpoint.
        # The equations are linear, so one trial with a known power is enough (C.13).
        if T_target is not None:
            T_air_test = one_hour(T_mass_old, T_out[i], Q_internal[i], Q_used[i], Q_test)[3]
            Q_hvac = Q_test * (T_target - T_air_free) / (T_air_test - T_air_free)
            state = one_hour(T_mass_old, T_out[i], Q_internal[i], Q_used[i], Q_hvac)
            if Q_hvac > 0:
                heating[i] = Q_hvac
            else:
                cooling[i] = -Q_hvac

        T_mass_end[i], T_mass[i], T_surface[i], T_air[i] = state
        T_mass_old = T_mass_end[i]

    result = pd.DataFrame(index=weather.index)
    result["T_out_C"] = T_out
    result["solar_gain_W"] = Q_used
    result["internal_gain_W"] = Q_internal
    result["tinted"] = tinted
    result["heating_W"] = heating
    result["cooling_W"] = cooling
    result["T_in_C"] = T_air                 # room air temperature
    result["T_surface_C"] = T_surface
    result["T_mass_C"] = T_mass              # mean of the hour
    result["T_mass_end_C"] = T_mass_end      # at the end of the hour

    # In ISO 13790 a small part of the radiant heat (sun and half of the internal gains)
    # is not given to any of the three temperatures: it counts as lost through the window.
    result["radiant_loss_W"] = H_w / (H_SURFACE_MASS * A_total) * (0.5 * Q_internal + Q_used)

    # Heat that leaves the room in each hour through the three paths to the outside (W).
    # Used for the energy balance test.
    result["loss_W"] = (H_ve * (T_air - T_out) + H_w * (T_surface - T_out)
                        + H_em * (T_mass - T_out))
    return result


def yearly_demand(result):
    """Heating and cooling demand per year in kWh (each row is 1 hour, so W -> Wh)."""
    by_year = result.groupby(result.index.year)
    return pd.DataFrame({
        "heating_kWh": by_year["heating_W"].sum() / 1000,
        "cooling_kWh": by_year["cooling_W"].sum() / 1000,
    })


def run_normal_window(city="Athens"):
    """Calculate, check and print the demand with the main normal window, both models."""
    window = WINDOWS[MAIN_NORMAL]
    window_U = window["U"]
    shgc = window["states"]["fixed"]["SHGC"]
    weather = load_weather(city)
    years = len(set(weather.index.year))

    print(f"\n=== Room: BESTEST Case 600, {city}, window: {window['name']} ===")
    print(f"U-values (W/m2K): walls {u_value(WALL_LAYERS):.3f}, roof {u_value(ROOF_LAYERS):.3f}, "
          f"floor {u_value(FLOOR_LAYERS):.3f}, window {window_U:.3f}")
    parts = heat_loss_coefficients(window_U)
    H = sum(parts.values())
    print("Heat loss coefficient H (W/K):")
    for name, value in parts.items():
        print(f"  {name:18s} {value:6.1f}  ({value / H * 100:4.1f} %)")
    print(f"  {'TOTAL':18s} {H:6.1f}")

    capacities = heat_capacities()
    C = sum(capacities.values())
    print("Heat capacity C (Wh/K):")
    for name, value in capacities.items():
        print(f"  {name:18s} {value:6.1f}  ({value / C * 100:4.1f} %)")
    print(f"  {'TOTAL':18s} {C:6.1f}")
    print(f"Time constant C/H = {C / H:.1f} hours")

    steady = simulate_steady(weather, window_U, shgc)
    rc = simulate_rc(weather, window_U, shgc)
    yearly = yearly_demand(rc)

    print("\n=== Yearly demand, 1R1C model (thermal energy, kWh) ===")
    print(yearly.round(0))

    print("\n=== Model comparison (10-year mean, kWh/year) ===")
    print(f"{'model':32s} {'heating':>8s} {'cooling':>8s}")
    for name, result in [("steady state (no mass)", steady),
                         ("1R1C, C x 0.5", simulate_rc(weather, window_U, shgc, C * 0.5)),
                         ("1R1C, C as calculated", rc),
                         ("1R1C, C x 2", simulate_rc(weather, window_U, shgc, C * 2))]:
        print(f"{name:32s} {result['heating_W'].sum() / 1000 / years:8.0f} "
              f"{result['cooling_W'].sum() / 1000 / years:8.0f}")

    print("\n=== Monthly mean, 1R1C model (kWh per month) ===")
    month = rc.index.month
    monthly = pd.DataFrame({
        "heating_kWh": rc["heating_W"].groupby(month).sum() / 1000 / years,
        "cooling_kWh": rc["cooling_W"].groupby(month).sum() / 1000 / years,
        "solar_gain_kWh": rc["solar_gain_W"].groupby(month).sum() / 1000 / years,
    })
    print(monthly.round(0))

    print("\n=== Sanity checks (1R1C model) ===")
    # 1) Energy balance over the whole period: energy in = energy out + change of stored heat
    stored_change = C * (rc["T_in_C"].iloc[-1] - T_HEATING)                       # Wh
    energy_in = (rc["heating_W"] + rc["solar_gain_W"] + rc["internal_gain_W"]).sum()
    energy_out = (rc["cooling_W"] + H * (rc["T_in_C"] - rc["T_out_C"])).sum()
    print(f"1) Energy balance error over 10 years: {energy_in - energy_out - stored_change:.2e} Wh "
          f"(should be ~0)")
    # 2) With a tiny C, the 1R1C model must give the steady-state result
    tiny = simulate_rc(weather, window_U, shgc, capacity_Wh_K=1e-9)
    difference = (tiny["heating_W"] - steady["heating_W"]).abs().max() + \
                 (tiny["cooling_W"] - steady["cooling_W"]).abs().max()
    print(f"2) 1R1C with C -> 0 vs steady state, largest difference: {difference:.2e} W (should be ~0)")
    # 3) Indoor temperature always between the setpoints
    print(f"3) Indoor temperature range: {rc['T_in_C'].min():.2f} to {rc['T_in_C'].max():.2f} C "
          f"(should be 20 to 27)")
    # 4) Heating and cooling never in the same hour
    both = ((rc["heating_W"] > 0) & (rc["cooling_W"] > 0)).sum()
    print(f"4) Hours with heating AND cooling: {both} (should be 0)")

    RESULTS_FOLDER.mkdir(exist_ok=True)
    path = RESULTS_FOLDER / f"{city.lower()}_{MAIN_NORMAL}_yearly_demand.csv"
    yearly.round(1).to_csv(path)
    print(f"\nSaved: {path}")
    return rc


if __name__ == "__main__":
    run_normal_window("Athens")
