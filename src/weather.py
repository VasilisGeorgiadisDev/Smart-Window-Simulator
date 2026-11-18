"""
weather.py
----------
Download and read hourly weather data from PVGIS
(Photovoltaic Geographical Information System, EU Joint Research Centre).

    https://re.jrc.ec.europa.eu/api/v5_3/seriescalc

What we ask PVGIS for:
    - hourly values for 10 real years (2014-2023)
    - solar irradiance on a VERTICAL (angle = 90 deg) wall facing SOUTH (aspect = 0)
    - split into direct (beam), diffuse and ground-reflected parts (components = 1)
    - air temperature at 2 m and wind speed at 10 m
    - satellite database PVGIS-SARAH3 (the PVGIS 5.3 default for Europe) for the sunlight
      (for Denver, used only for testing, PVGIS offers only the PVGIS-ERA5 database)
    - ERA5 reanalysis for temperature and wind (stated by PVGIS in the downloaded file)

PVGIS data are free to use IF THE SOURCE IS ACKNOWLEDGED ("PVGIS © European Communities,
2001-2026", JRC geospatial data download page). The temperatures come from ERA5 (Copernicus
Climate Change Service), which also asks for an acknowledgement, e.g. "Contains modified
Copernicus Climate Change Service information". Both lines are in the README.
Time stamps are in UTC (not Greek local time).

The raw file is saved in data/ (this folder is NOT uploaded to GitHub, see .gitignore).
The README will explain how to download it again.

Run this file directly to download the data and print a short summary:
    python src/weather.py
"""

import json
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

# Folder for downloaded files: <project>/data
DATA_FOLDER = Path(__file__).resolve().parent.parent / "data"

# PVGIS 5.3 "hourly radiation" tool
PVGIS_URL = "https://re.jrc.ec.europa.eu/api/v5_3/seriescalc"

# City coordinates in degrees (north and east are positive).
# Athens: city centre (Syntagma square area).
CITIES = {
    "Athens": (37.98, 23.73),
    # Amsterdam: city centre (Dam square area).
    "Amsterdam": (52.37, 4.89),
    # Denver (USA) is used only to TEST the room model against published results
    # (see validation.py). Coordinates of the BESTEST weather site, Denver airport.
    "Denver": (39.833, -104.65),
}

# Sunlight database used by PVGIS for each city.
# PVGIS-SARAH3 (satellite) covers Europe, Africa and Asia, but not America.
# For Denver, PVGIS 5.3 offers only PVGIS-ERA5 (a weather model, less detailed).
RADIATION_DATABASE = {
    "Athens": "PVGIS-SARAH3",
    "Amsterdam": "PVGIS-SARAH3",
    "Denver": "PVGIS-ERA5",
}

# Years to download (PVGIS-SARAH3 covers 2005-2023)
START_YEAR = 2014
END_YEAR = 2023

# Readable names for the PVGIS columns. All irradiance values are in W/m2,
# on the plane of the window (vertical, facing south).
COLUMN_NAMES = {
    "Gb(i)": "beam_W_m2",        # direct sunlight on the wall
    "Gd(i)": "diffuse_W_m2",     # diffuse light from the sky on the wall
    "Gr(i)": "reflected_W_m2",   # light reflected from the ground onto the wall
    "H_sun": "sun_height_deg",   # height of the sun above the horizon (degrees)
    "T2m":   "T_out_C",          # outdoor air temperature at 2 m (deg C)
    "WS10m": "wind_m_s",         # wind speed at 10 m (m/s)
    "Int":   "reconstructed",    # 1 = PVGIS had to reconstruct the radiation value
}


def raw_file_path(city):
    """Name of the downloaded file, e.g. data/pvgis_athens_2014_2023_south_vertical.json"""
    return DATA_FOLDER / f"pvgis_{city.lower()}_{START_YEAR}_{END_YEAR}_south_vertical.json"


def download_weather(city):
    """Ask PVGIS for the hourly data of one city and save the answer as a JSON file."""
    latitude, longitude = CITIES[city]
    settings = {
        "lat": latitude,
        "lon": longitude,
        "startyear": START_YEAR,
        "endyear": END_YEAR,
        "angle": 90,                  # 90 deg from horizontal = vertical wall
        "aspect": 0,                  # 0 = south (90 = west, -90 = east)
        "components": 1,              # give beam, diffuse and reflected separately
        "usehorizon": 1,              # include shading by hills/mountains on the horizon
        "raddatabase": RADIATION_DATABASE[city],
        "outputformat": "json",
    }
    url = PVGIS_URL + "?" + urllib.parse.urlencode(settings)
    print(f"Downloading {city} weather data from PVGIS ...")
    print(url)

    with urllib.request.urlopen(url, timeout=120) as answer:
        text = answer.read().decode("utf-8")

    DATA_FOLDER.mkdir(exist_ok=True)
    path = raw_file_path(city)
    path.write_text(text, encoding="utf-8")
    print(f"Saved: {path}  ({path.stat().st_size / 1e6:.1f} MB)")
    return path


def load_weather(city):
    """Read the saved PVGIS file and return a table (pandas DataFrame), one row per hour."""
    path = raw_file_path(city)
    if not path.exists():
        download_weather(city)

    content = json.loads(path.read_text(encoding="utf-8"))
    table = pd.DataFrame(content["outputs"]["hourly"])

    # e.g. "20140101:0009" -> 1 January 2014, 00:09 UTC
    # (the minutes differ per place and database: Athens :09, Amsterdam :11, Denver :30)
    table["time_utc"] = pd.to_datetime(table["time"], format="%Y%m%d:%H%M", utc=True)
    table = table.drop(columns="time").set_index("time_utc")
    table = table.rename(columns=COLUMN_NAMES)

    # Total irradiance on the window = beam + diffuse + reflected
    table["total_W_m2"] = table["beam_W_m2"] + table["diffuse_W_m2"] + table["reflected_W_m2"]
    return table


def print_summary(city):
    """Print what is inside the data: size, units, missing values and yearly numbers."""
    table = load_weather(city)          # downloads the file first if it is not in data/ yet
    content = json.loads(raw_file_path(city).read_text(encoding="utf-8"))

    print(f"\n=== {city}: what PVGIS says about the location ===")
    location = content["inputs"]["location"]
    print(f"Latitude {location['latitude']}, longitude {location['longitude']}, "
          f"elevation {location['elevation']} m")
    print(f"Radiation database: {content['inputs']['meteo_data']['radiation_db']}")

    print("\n=== Variables and units, as described by PVGIS ===")
    for name, info in content["meta"]["outputs"]["hourly"]["variables"].items():
        print(f"  {name:6s} [{info.get('units', '-')}]  {info['description']}")

    print("\n=== Size of the table ===")
    print(f"Rows (hours): {len(table)}")
    print(f"First time stamp: {table.index[0]}")
    print(f"Last time stamp:  {table.index[-1]}")
    print(f"Missing values: {int(table.isna().sum().sum())}")
    print(f"Hours with reconstructed radiation: {int((table['reconstructed'] == 1).sum())}")

    print("\n=== First 5 rows ===")
    print(table.head())

    print("\n=== Yearly numbers ===")
    # Each row is one hour, so the sum of W/m2 over a year gives Wh/m2. Divide by 1000 for kWh/m2.
    yearly = pd.DataFrame({
        "hours": table["T_out_C"].groupby(table.index.year).count(),
        "mean_T_C": table["T_out_C"].groupby(table.index.year).mean(),
        "min_T_C": table["T_out_C"].groupby(table.index.year).min(),
        "max_T_C": table["T_out_C"].groupby(table.index.year).max(),
        "facade_kWh_m2": table["total_W_m2"].groupby(table.index.year).sum() / 1000,
    })
    print(yearly.round(1))


if __name__ == "__main__":
    for city_name in CITIES:
        print_summary(city_name)
