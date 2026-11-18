"""
window.py
---------
Properties of the windows we compare. Every number has a reference.

    U     : U-value in W/(m2 K). Heat that flows through 1 m2 of glass for every
            1 K of difference between inside and outside temperature.
            Lower U = better insulation.
    SHGC  : Solar Heat Gain Coefficient (0 to 1), also called g-value in Europe.
            The fraction of the sunlight falling on the glass that ends up as heat
            inside the room (transmitted directly + absorbed in the glass and then
            released inwards).
    Tvis  : visible transmittance (0 to 1). The fraction of VISIBLE light that passes
            through (weighted by the sensitivity of the human eye). Tells us how
            bright the room is, not how much heat comes in.

All values are CENTRE-OF-GLASS values (the frame is not included):
    U    calculated for winter conditions: -18 C outside, 21 C inside, 5.5 m/s wind, no sun
    SHGC calculated for summer conditions: 32 C outside, 24 C inside, 2.8 m/s wind,
         783 W/m2 sun at normal incidence
(conditions as stated in the EnergyPlus file [1]).
ASSUMPTION: the SageGlass flyer [2] does not state its calculation conditions. It is a US
document in US units, so it most likely uses the US NFRC method, which we assume is close
to the EnergyPlus conditions. This is not proven.

Each window has one or more "states". A normal window has only one state.
An electrochromic (EC) window has a clear state and one or more tinted states.

References
----------
[1] EnergyPlus reference data set "WindowConstructs.idf" (U.S. Department of Energy,
    NREL / LBNL), GitHub repository NREL/EnergyPlus, folder datasets/, develop branch,
    accessed 13 Nov 2026.
    https://github.com/NREL/EnergyPlus/blob/develop/datasets/WindowConstructs.idf
[2] SageGlass (Saint-Gobain), "Performance & Acoustical Data" flyer, document MKT-043.7,
    product "SageGlass Clear with SR2.0": 6 mm clear with SR2.0, 0.76 mm PVB, 2.2 mm SageGlass,
    10 mm air space with 90 % argon, 6 mm clear. Accessed 13 Nov 2026.
    https://www.sageglass.com/sites/default/files/2024-03/mkt-043_performance_and_acoustical_data_flyer.pdf

[6] ANSI/ASHRAE Addendum a to ANSI/ASHRAE Standard 140-2017 (the BESTEST update of 2020),
    Informative Annex B6, Tables B6-1, B6-2 and B6-3: SHGC of three glazings at incidence
    angles from 0 to 90 degrees, calculated with the LBNL program WINDOW 7. Accessed 16 Nov 2026.
    https://www.ashrae.org/file%20library/technical%20resources/standards%20and%20guidelines/standards%20addenda/140_2017_a_galley_20200812.pdf

The angle of the sun
--------------------
The SHGC values above are for sunlight that hits the glass head-on (incidence angle 0).
Glass reflects more when the light arrives at a flat angle, so the SHGC falls.
ANGLE_CURVES below gives this fall for three glazings [6]. We use only the SHAPE of each curve
(SHGC at an angle divided by SHGC at 0) and multiply it by the SHGC of our own window.
ASSUMPTION: each of our windows follows the curve of the most similar glazing in [6].
For the two EC windows no curve is published; we use the clear double glazing curve
(chosen on 17 Nov 2026).
The equations are in docs/equations.md (section 2).

Run this file directly to print a table of all windows:
    python src/window.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

# 1 Btu/(h ft2 F) = 5.678 W/(m2 K)  (US units used in the SageGlass data sheet)
BTU_TO_SI = 5.678

RESULTS_FOLDER = Path(__file__).resolve().parent.parent / "results"

WINDOWS = {

    # ---------- Normal (static) windows ----------

    # Modern standard double glazing: low-E coating (emissivity 0.1) and argon.
    # This is the main reference case.
    "normal_lowE": {
        "name": "Double glazing, low-E, argon",
        "U": 1.493,
        "states": {"fixed": {"SHGC": 0.568, "Tvis": 0.745}},
        "source": "[1] 'Dbl LoE (e2=.1) Clr 6mm/13mm Arg'",
        "angle_curve": "double low-E",
    },

    # Older double glazing without coating (common in older buildings).
    "normal_clear": {
        "name": "Double glazing, clear, air",
        "U": 2.67,
        "states": {"fixed": {"SHGC": 0.703, "Tvis": 0.781}},
        "source": "[1] 'Dbl Clr 6mm/13mm Air'",
        "angle_curve": "double clear",
    },

    # ---------- Electrochromic windows ----------

    # Real commercial product. Main EC case.
    "ec_sageglass": {
        "name": "EC, SageGlass Clear with SR2.0",
        "U": round(0.29 * BTU_TO_SI, 2),   # data sheet gives 0.29 Btu/(h ft2 F), same in all states
        "states": {
            "clear":       {"SHGC": 0.41, "Tvis": 0.60},
            "light tint":  {"SHGC": 0.16, "Tvis": 0.18},
            "medium tint": {"SHGC": 0.11, "Tvis": 0.06},
            "full tint":   {"SHGC": 0.09, "Tvis": 0.01},
        },
        "source": "[2] MKT-043.7, 'SageGlass Clear with SR2.0'",
        "angle_curve": "double clear",   # assumption, see top of file
    },

    # Generic EC window from EnergyPlus (absorptive type, argon).
    # Same calculation method as the normal windows above, so it is a useful second case.
    "ec_generic": {
        "name": "EC, generic absorptive (EnergyPlus)",
        "U": 1.493,
        "states": {
            "clear":     {"SHGC": 0.745, "Tvis": 0.752},   # 'Dbl Elec Abs Bleached 6mm/13mm Arg'
            "full tint": {"SHGC": 0.158, "Tvis": 0.114},   # 'Dbl Elec Abs Colored 6mm/13mm Arg'
        },
        "source": "[1] 'Dbl Elec Abs Bleached/Colored 6mm/13mm Arg'",
        "angle_curve": "double clear",   # assumption, see top of file
    },
}


# Main comparison of the project (agreed on 13 Nov 2026):
# a modern normal window against a real commercial EC window.
# The other two windows are extra cases for comparison.
MAIN_NORMAL = "normal_lowE"
MAIN_EC = "ec_sageglass"


# ---------- The angle of the sun on the glass [6] ----------

# Incidence angles of the table (degrees): 0 = head-on, 90 = along the glass
ANGLES = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]

# SHGC at each of these angles, and for diffuse light (light from all directions at once,
# called "hemispherical" in [6])
ANGLE_CURVES = {
    "single clear": {     # Table B6-3
        "SHGC": [0.864, 0.864, 0.862, 0.859, 0.851, 0.831, 0.785, 0.673, 0.424, 0.000],
        "diffuse": 0.787,
    },
    "double clear": {     # Table B6-1
        "SHGC": [0.769, 0.768, 0.766, 0.761, 0.748, 0.718, 0.651, 0.509, 0.267, 0.000],
        "diffuse": 0.670,
    },
    "double low-E": {     # Table B6-2 (low-E coating, argon)
        "SHGC": [0.440, 0.443, 0.438, 0.432, 0.422, 0.403, 0.361, 0.278, 0.148, 0.000],
        "diffuse": 0.377,
    },
}


def angle_factor(curve, incidence_deg):
    """
    How much of the head-on SHGC is left at this incidence angle (1 = all, 0 = nothing).
    Between the angles of the table we draw straight lines (linear interpolation).
    """
    values = np.array(ANGLE_CURVES[curve]["SHGC"])
    return np.interp(incidence_deg, ANGLES, values / values[0])


def diffuse_factor(curve):
    """The same factor for diffuse light (from the sky and reflected from the ground)."""
    return ANGLE_CURVES[curve]["diffuse"] / ANGLE_CURVES[curve]["SHGC"][0]


def solar_gain_per_m2(weather, incidence_deg, shgc, curve, sunlit=1.0, sky=1.0):
    """
    Solar heat that enters the room through 1 m2 of glass, in W/m2, for every hour.

    weather       : table from weather.load_weather()
    incidence_deg : incidence angle of the sun on the window, from sun.incidence_angle()
    shgc          : head-on SHGC of the window (one number, or one value per hour)
    curve         : name of the angle curve, e.g. "double low-E"
    sunlit        : fraction of the window in direct sun (shading.sunlit_fraction), 1 = no shade
    sky           : fraction of the diffuse sky light that reaches the window
                    (shading.sky_fraction), 1 = no balcony
    """
    direct = shgc * angle_factor(curve, incidence_deg) * sunlit * weather["beam_W_m2"]
    diffuse = shgc * diffuse_factor(curve) * (sky * weather["diffuse_W_m2"] + weather["reflected_W_m2"])
    return direct + diffuse


def window_table():
    """All windows and states in one table (one row per state)."""
    rows = []
    for key, window in WINDOWS.items():
        for state, values in window["states"].items():
            rows.append({
                "key": key,
                "window": window["name"],
                "state": state,
                "U_W_m2K": window["U"],
                "SHGC": values["SHGC"],
                "Tvis": values["Tvis"],
                "source": window["source"],
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    table = window_table()
    pd.set_option("display.width", 200)
    print(table.drop(columns="key").to_string(index=False))

    print()
    print("Angle factor: SHGC at an angle divided by SHGC head-on [6]")
    angle_table = pd.DataFrame({curve: angle_factor(curve, ANGLES) for curve in ANGLE_CURVES},
                               index=pd.Index(ANGLES, name="angle_deg"))
    angle_table.loc["diffuse"] = [diffuse_factor(curve) for curve in ANGLE_CURVES]
    print(angle_table.round(3))

    RESULTS_FOLDER.mkdir(exist_ok=True)
    path = RESULTS_FOLDER / "window_properties.csv"
    table.to_csv(path, index=False)
    print(f"\nSaved: {path}")
