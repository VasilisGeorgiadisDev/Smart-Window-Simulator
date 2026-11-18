"""
excel_report.py
---------------
Formatted Excel report of the smart-window comparison, in the same style as the battery
project (asked by Vasilis):

    header rows -> dark blue background, white bold text
    data rows   -> alternating light blue / white ("banded rows")

    write_smart_window_report() -> results/smart_window_report.xlsx

Sheets:
    "Summary"    : the two comparison figures, the main tables and short notes
    "Monthly"    : month by month, one block of columns per city
    "Inputs"     : the glass properties (with sources) and the room settings
    "Validation" : the BESTEST test in Denver (our model against professional programs)

The numbers are read from the tables in results/, made by ec_comparison.py and
validation.py, so the report always shows exactly what the scripts calculated.
"""

from pathlib import Path

import pandas as pd
import xlsxwriter
from PIL import Image          # only used to read the size of the PNG files

from style import FIGURES_FOLDER
from window import WINDOWS, MAIN_NORMAL, MAIN_EC

RESULTS_FOLDER = Path(__file__).resolve().parent.parent / "results"
REPORT_PATH = RESULTS_FOLDER / "smart_window_report.xlsx"
CITIES = ["Athens", "Amsterdam"]

# ----- Colours and sizes (change them here) -----------------------------------
DARK_BLUE = "#1F3864"
LIGHT_BLUE = "#DDEBF7"
WHITE = "#FFFFFF"
BORDER_GREY = "#B4C6E7"

SUMMARY_COLUMN_WIDTH = 15   # width of the table columns on the Summary sheet
GAP_WIDTH = 3               # width of the empty column between two cities


# =============================================================================
# Building blocks (the same as in the battery project)
# =============================================================================

def make_formats(workbook):
    """Create the fixed cell styles: headers, titles and notes."""
    header = {"bold": True, "font_color": WHITE, "bg_color": DARK_BLUE,
              "align": "center", "valign": "vcenter", "text_wrap": True,
              "border": 1, "border_color": DARK_BLUE}
    return {
        "workbook": workbook,
        "header": workbook.add_format(header),
        "block_title": workbook.add_format({**header, "font_size": 13}),
        "page_title": workbook.add_format({"bold": True, "font_size": 16,
                                           "font_color": DARK_BLUE}),
        "table_title": workbook.add_format({"bold": True, "font_size": 12,
                                            "font_color": DARK_BLUE}),
        "note": workbook.add_format({"italic": True, "font_color": "#595959"}),
    }


def row_format(formats, colour_name, number_format):
    """Style of a data cell: light blue or white, with a number format.
    Each style is created the first time it is needed, then reused."""
    key = (colour_name, number_format)
    if key not in formats:
        settings = {"bg_color": LIGHT_BLUE if colour_name == "light" else WHITE,
                    "align": "center", "border": 1, "border_color": BORDER_GREY}
        if number_format:
            settings["num_format"] = number_format
        formats[key] = formats["workbook"].add_format(settings)
    return formats[key]


def write_table(sheet, first_row, first_col, table, columns, formats, empty_text="–"):
    """Write a pandas table: dark blue header row, then banded rows.

    columns    : list of (pandas column, header text, number format)
                 number format: "0.00" = 2 decimals, "0.0" = 1 decimal, "0" = whole number
    empty_text : what to write in empty cells
    Returns the row number just below the table.
    """
    sheet.set_row(first_row, 36)                       # taller, so 2-line headers fit
    for i, (_, header_text, _) in enumerate(columns):
        sheet.write(first_row, first_col + i, header_text, formats["header"])

    for n, (_, values) in enumerate(table.iterrows()):
        row = first_row + 1 + n
        colour_name = "light" if n % 2 == 0 else "white"
        for i, (column_name, _, number_format) in enumerate(columns):
            value = values[column_name]
            cell_format = row_format(formats, colour_name, number_format)
            if pd.isna(value):
                sheet.write(row, first_col + i, empty_text, cell_format)
            else:
                sheet.write(row, first_col + i, value, cell_format)
    return first_row + 1 + len(table)


def insert_figures(sheet, first_row, figure_paths, scale):
    """Put the PNG figures one below the other. Returns the first free row below them."""
    row = first_row
    for path in figure_paths:
        width_px, height_px = Image.open(path).size
        # PNGs are 300 dpi; Excel shows images at 96 dpi
        shown_height = height_px * 96 / 300 * scale
        sheet.insert_image(row, 0, str(path), {
            "x_scale": scale, "y_scale": scale,
            "object_position": 3,                      # don't stretch when columns change
        })
        row += int(shown_height / 20) + 2              # a normal Excel row is 20 px tall
    return row


def write_city_blocks(formats, sheet_name, tables_by_city, block_columns):
    """A sheet with one block of columns per city, one empty column between blocks.

    block_columns : list of (pandas column, header text, width, number format)
    """
    sheet = formats["workbook"].add_worksheet(sheet_name)
    first_col = 0
    for city, table in tables_by_city.items():
        last_col = first_col + len(block_columns) - 1
        # Row 1: city name across the whole block (merged cells)
        sheet.merge_range(0, first_col, 0, last_col, city, formats["block_title"])
        # Row 2 and below: header and data
        columns = [(name, header, fmt) for name, header, _, fmt in block_columns]
        write_table(sheet, 1, first_col, table, columns, formats)
        for i, (_, _, width, _) in enumerate(block_columns):
            sheet.set_column(first_col + i, first_col + i, width)
        sheet.set_column(last_col + 1, last_col + 1, GAP_WIDTH)
        first_col = last_col + 2                       # +1 empty column
    sheet.set_row(0, 22)
    sheet.freeze_panes(2, 0)                           # titles + headers stay visible


def save_workbook(workbook, excel_path):
    """Save. If the file is open in Excel, Windows does not allow overwriting it."""
    try:
        workbook.close()
        print(f"Saved: {excel_path}")
    except (PermissionError, xlsxwriter.exceptions.FileCreateError):
        print(f"\nCould NOT save {excel_path}")
        print("The file is probably open in Excel. Close it and run the script again.\n")


def read_result(file_name, **options):
    """Read a table from results/ (made by ec_comparison.py or validation.py)."""
    path = RESULTS_FOLDER / file_name
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run the calculation first (menu options 3 and 5).")
    return pd.read_csv(path, **options)


# =============================================================================
# The tables of the report
# =============================================================================

def glass_table():
    """One row per glass state, with its source."""
    rows = []
    for key, role in ((MAIN_NORMAL, "Normal glass"), (MAIN_EC, "Smart glass")):
        window = WINDOWS[key]
        for state, values in window["states"].items():
            if state == "medium tint":
                continue                               # not used in the comparison
            rows.append({"role": role, "name": window["name"], "state": state,
                         "U": window["U"], "SHGC": values["SHGC"], "Tvis": values["Tvis"],
                         "source": window["source"]})
    return pd.DataFrame(rows)


def room_table():
    """The fixed settings of the comparison, as text."""
    rows = [
        ("Room", "BESTEST Case 600 (ANSI/ASHRAE Standard 140): 8 x 6 x 2.7 m, light building"),
        ("Window", "12 m2, facing south, no shading"),
        ("Internal gains", "200 W, day and night"),
        ("Thermostat", "heating below 20 C, cooling above 27 C, 24 hours a day"),
        ("Air leakage", "0.5 air changes per hour (both cities are at sea level)"),
        ("Weather", "PVGIS 5.3, hourly 2014-2023, sunlight PVGIS-SARAH3, temperature ERA5"),
        ("Room model", "ISO 13790 simple hourly method (5R1C), SHGC depends on the angle of the sun"),
        ("Smart-glass rule", "each hour: tint if the room with clear glass would exceed 27 C"),
        ("Energy", "thermal energy (heat added or removed), not electricity"),
    ]
    return pd.DataFrame(rows, columns=["item", "value"])


# =============================================================================
# The report
# =============================================================================

def write_smart_window_report(excel_path=REPORT_PATH):
    comparison = read_result("city_comparison.csv")
    runs = pd.concat([read_result(f"{city.lower()}_ec_comparison.csv").assign(city=city)
                      for city in CITIES], ignore_index=True)
    monthly = {city: read_result(f"{city.lower()}_ec_monthly.csv") for city in CITIES}
    validation = read_result("denver_validation.csv")
    figures = [FIGURES_FOLDER / "ec_vs_normal_yearly.png", FIGURES_FOLDER / "ec_vs_normal_monthly.png"]
    for path in figures:
        if not path.exists():
            raise FileNotFoundError(f"{path} not found. Make the figures first (menu option 5).")

    workbook = xlsxwriter.Workbook(excel_path)
    formats = make_formats(workbook)

    # ---- Sheet "Summary" ----
    sheet = workbook.add_worksheet("Summary")
    sheet.hide_gridlines(2)                            # clean white background
    sheet.set_column(0, 13, SUMMARY_COLUMN_WIDTH)
    sheet.write(0, 0, "Smart window vs normal glass: Athens and Amsterdam (BESTEST room)",
                formats["page_title"])
    row = insert_figures(sheet, 2, figures, 0.55)

    sheet.write(row, 0, "Table 1. Athens vs Amsterdam: normal glass vs smart glass "
                        "(SageGlass + rule, light tint), kWh of heat per year", formats["table_title"])
    row = write_table(sheet, row + 1, 0, comparison, [
        ("city",                       "City",                          None),
        ("mean_T_out_C",               "Mean outside\ntemperature (°C)", "0.0"),
        ("sun_on_facade_kWh_m2",       "Sun on south wall\n(kWh/m²)",   "0"),
        ("normal_heating_kWh",         "Normal glass:\nheating",         "0"),
        ("normal_cooling_kWh",         "Normal glass:\ncooling",         "0"),
        ("smart_heating_kWh",          "Smart glass:\nheating",          "0"),
        ("smart_cooling_kWh",          "Smart glass:\ncooling",          "0"),
        ("saved_kWh",                  "Saved\n(kWh)",                   "0"),
        ("saved_%",                    "Saved\n(%)",                     "0.0"),
        ("saved_May_Oct_kWh",          "Saved\nMay–Oct",                 "0"),
        ("saved_Nov_Apr_kWh",          "Saved\nNov–Apr",                 "0"),
        ("saved_from_clear_state_kWh", "Saved by the\nclear state",      "0"),
        ("saved_from_switching_kWh",   "Saved by\nswitching",            "0"),
    ], formats) + 2

    sheet.write(row, 0, "Table 2. All five runs, kWh of heat per year", formats["table_title"])
    row = write_table(sheet, row + 1, 0, runs, [
        ("city",                 "City",                       None),
        ("run",                  "Run",                        None),
        ("heating_kWh",          "Heating",                    "0"),
        ("cooling_kWh",          "Cooling",                    "0"),
        ("total_kWh",            "Total",                      "0"),
        ("total_vs_normal_%",    "Total vs\nnormal glass (%)", "0"),
        ("tinted_%_of_daylight", "Glass tinted\n(% of daylight hours)", "0"),
        ("mean_Tvis_daylight",   "Mean visible\ntransmittance", "0.00"),
    ], formats) + 2
    sheet.set_column(1, 1, 30)                         # the run names are long

    # Share of the May-October cooling (normal glass) while the outside air is below 27 C
    below_27 = dict(zip(comparison["city"], comparison["cooling_May_Oct_T_out_below_27C_%"]))
    notes = [
        "Same room (BESTEST Case 600) and same glass in both cities: only the weather changes.",
        "The rule is simple but ideal (it knows the room temperature of the hour). "
        "Other rules can save more (see run 5); a real controller with sensors would likely save a little less.",
        "The test room can never open a window, so it also needs cooling when it is mild outside: from May to "
        f"October, {below_27['Athens']:.0f} % (Athens) and {below_27['Amsterdam']:.0f} % (Amsterdam) "
        "of the cooling with normal glass happens while the outside air is below 27 °C.",
        "In a real home part of this cooling would not be needed, so the real savings are probably smaller, "
        "most of all in Amsterdam.",
        "Thermal energy, not electricity. Lamps are not modelled: see the visible transmittance.",
        "Numbers are rounded, so a total can differ by 1 from the sum of its parts.",
        "All equations and sources: docs/equations.md.",
    ]
    for i, line in enumerate(notes):
        sheet.write(row - 1 + i, 0, line, formats["note"])

    # ---- Sheet "Monthly" ----
    write_city_blocks(formats, "Monthly", monthly, [
        ("month",                "Month",                         7,  "0"),
        ("T_out_mean_C",         "Mean outside temp. (°C)",       11, "0.0"),
        ("sun_on_facade_kWh_m2", "Sun on south wall (kWh/m²)",    11, "0"),
        ("normal_heating_kWh",   "Normal glass: heating (kWh)",   11, "0"),
        ("normal_cooling_kWh",   "Normal glass: cooling (kWh)",   11, "0"),
        ("smart_heating_kWh",    "Smart glass: heating (kWh)",    11, "0"),
        ("smart_cooling_kWh",    "Smart glass: cooling (kWh)",    11, "0"),
        ("smart_tinted_hours",   "Hours tinted",                  9,  "0"),
    ])

    # ---- Sheet "Inputs" ----
    sheet = workbook.add_worksheet("Inputs")
    sheet.hide_gridlines(2)
    sheet.write(0, 0, "Inputs of the comparison", formats["page_title"])
    sheet.write(2, 0, "Table 1. Glass properties (centre of glass)", formats["table_title"])
    row = write_table(sheet, 3, 0, glass_table(), [
        ("role",   "Role",              None),
        ("name",   "Glass",             None),
        ("state",  "State",             None),
        ("U",      "U (W/m²K)",         "0.00"),
        ("SHGC",   "SHGC",              "0.000"),
        ("Tvis",   "Visible\ntransmittance", "0.000"),
        ("source", "Source",            None),
    ], formats) + 2
    sheet.write(row, 0, "Table 2. Room and calculation", formats["table_title"])
    write_table(sheet, row + 1, 0, room_table(), [("item", "Item", None), ("value", "Value", None)],
                formats)
    for column, width in enumerate((16, 32, 12, 11, 9, 13, 46)):
        sheet.set_column(column, column, width)

    # ---- Sheet "Validation" ----
    sheet = workbook.add_worksheet("Validation")
    sheet.hide_gridlines(2)
    sheet.write(0, 0, "Validation: BESTEST Case 600 in Denver, MWh per year", formats["page_title"])
    row = write_table(sheet, 2, 0, validation, [
        ("model",               "Model",                   None),
        ("heating_MWh",         "Heating (MWh)",           "0.00"),
        ("heating_vs_accepted", "Heating vs\naccepted range", None),
        ("cooling_MWh",         "Cooling (MWh)",           "0.00"),
        ("cooling_vs_accepted", "Cooling vs\naccepted range", None),
    ], formats) + 1
    sheet.set_column(0, 0, 32)
    sheet.set_column(1, 4, 16)
    for i, line in enumerate([
        "Accepted ranges (ANSI/ASHRAE Standard 140): heating 3.75–4.98, cooling 5.00–6.83 MWh per year.",
        "Model 3 (5R1C, SHGC with the sun angle) is the model used for all results of this report.",
    ]):
        sheet.write(row + i, 0, line, formats["note"])

    save_workbook(workbook, excel_path)


if __name__ == "__main__":
    write_smart_window_report()
