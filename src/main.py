r"""
main.py
-------
A simple numbered menu, like in my battery project:
press 1, 2, 3... to run each part. Start it from the project folder with:

    .venv\Scripts\python.exe src\main.py
"""

import os

import plots
from athens_bestest import run_athens_bestest
from ec_comparison import run_comparison
from excel_report import write_smart_window_report, RESULTS_FOLDER
from style import FIGURES_FOLDER
from validation import run_validation
from weather import print_summary

CITIES = ["Athens", "Amsterdam"]


def show_weather():
    """Download the weather data if needed, and describe it (source, units, size)."""
    for city in CITIES:
        print_summary(city)


def make_physics_figures():
    """The figures that explain the inputs: climate, sun path, glass angle, overhang shadow."""
    for city in CITIES:
        plots.plot_monthly_climate(city)
    plots.plot_sun_path("Athens")
    plots.plot_glass_angle("Athens")
    plots.plot_balcony_shadow("Athens")


def run_smart_window():
    """The main result: smart vs normal glass in both cities, then the figures and the Excel report."""
    run_comparison()
    plots.plot_ec_yearly()
    plots.plot_ec_monthly()
    write_smart_window_report()


def run_everything():
    """Options 1 to 5 one after the other."""
    show_weather()
    make_physics_figures()
    run_validation()
    run_athens_bestest()
    run_smart_window()


def open_in_windows(path):
    """Open a folder or file with the normal Windows program (Explorer, Excel...)."""
    if not path.exists():
        print(f"Not found: {path}  (run the calculation first)")
    elif hasattr(os, "startfile"):            # os.startfile exists only on Windows
        os.startfile(path)
    else:
        print(f"Open this yourself: {path}")


# Each menu option: (key to press, text shown, function to run)
MENU = [
    ("1", "Weather data: Athens and Amsterdam (source, units, size)", show_weather),
    ("2", "Figures of the inputs: climate, sun path, glass, shadow",  make_physics_figures),
    ("3", "Validation: BESTEST room in Denver vs professional programs", run_validation),
    ("4", "BESTEST room in Athens with normal glass",                   run_athens_bestest),
    ("5", "MAIN RESULT: smart vs normal glass, both cities (+ figures + Excel)",
          run_smart_window),
    ("6", "Run everything (1 to 5, takes a few minutes)",               run_everything),
    ("7", "Open the figures folder",          lambda: open_in_windows(FIGURES_FOLDER)),
    ("8", "Open the Excel report",
          lambda: open_in_windows(RESULTS_FOLDER / "smart_window_report.xlsx")),
]


def show_menu():
    print("\n" + "=" * 72)
    print("  Smart Window Energy Simulator")
    print("=" * 72)
    for key, text, _ in MENU:
        print(f"  {key}. {text}")
    print("  0. Exit")
    print("-" * 72)


def main():
    while True:                                   # repeat until the user presses 0
        show_menu()
        # strip() removes spaces; "﻿" is an invisible character some terminals add
        choice = input("Choose an option: ").strip().lstrip("﻿")

        if choice == "0":
            print("Bye!")
            break

        # Find the option the user chose
        actions = {key: function for key, _, function in MENU}
        if choice not in actions:
            print(f"'{choice}' is not an option. Please type a number from the menu.")
            continue

        try:
            actions[choice]()
            print("\nDone.")
        except Exception as error:                # show the problem, but keep the menu open
            print(f"\nSomething went wrong: {error}")


if __name__ == "__main__":
    main()
