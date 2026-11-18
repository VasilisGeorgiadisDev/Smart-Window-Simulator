"""
sun.py
------
Where is the sun? For every hour we calculate the position of the sun in the sky,
and the angle at which its rays hit the window.

Every equation here is written out, with its symbols, in docs/equations.md (section 1).

Angles used in this file (all in degrees):

    declination      angle between the sun's rays and the plane of the equator.
                     +23.4 in June, 0 at the equinoxes, -23.4 in December.
    hour angle       0 at solar noon, 15 degrees for each hour (negative in the morning).
    sun height       angle of the sun above the horizon (0 = horizon, 90 = overhead).
    sun azimuth      compass direction of the sun: 0 = south, -90 = east, +90 = west.
                     (the same convention as PVGIS uses for the direction of a wall)
    incidence angle  angle between the sun's rays and the line that points straight out
                     of the window. 0 = rays hit the glass head-on, 90 = rays slide along it.
    profile angle    the sun height as seen in a SIDE VIEW of the wall. It gives the length
                     of the shadow of a balcony:  shadow = balcony depth x tan(profile angle).

References
----------
[5] NOAA Global Monitoring Division, "General Solar Position Calculations" (2 pages, free):
    fractional year, equation of time, declination, solar time, hour angle and sun height.
    https://gml.noaa.gov/grad/solcalc/solareqns.PDF
    The azimuth, the incidence angle and the profile angle are derived from the direction of
    the sun as a vector; the derivation is in docs/equations.md (sections 1.7 to 1.9).

Not included: bending of light by the atmosphere (refraction, up to about 0.5 degrees
when the sun is on the horizon).

Run this file directly to test the formulas against PVGIS:
    python src/sun.py
"""

import numpy as np
import pandas as pd

from weather import load_weather, CITIES, raw_file_path


def sun_position(times_utc, latitude, longitude):
    """
    Position of the sun for each time stamp.

    times_utc : dates and times in UTC (the index of the weather table)
    latitude  : degrees, north positive
    longitude : degrees, east positive
    Returns a table with one row per time stamp.
    """
    day = times_utc.day_of_year.to_numpy()                               # 1 ... 366
    hour_utc = (times_utc.hour + times_utc.minute / 60).to_numpy()       # e.g. 10.15 = 10:09

    # Position of the Earth on its orbit, as an angle (radians): about 0 on 1 January,
    # 2 pi one year later. NOAA calls it the "fractional year".
    B = 2 * np.pi / 365 * (day - 1 + (hour_utc - 12) / 24)

    # Equation of time (minutes): the sun is up to 16 minutes "early" or "late"
    # compared with a clock, because the Earth's orbit is an ellipse and its axis is tilted.
    equation_of_time = 229.18 * (0.000075
                                + 0.001868 * np.cos(B) - 0.032077 * np.sin(B)
                                - 0.014615 * np.cos(2 * B) - 0.040849 * np.sin(2 * B))

    # Declination (radians)
    declination = (0.006918
                   - 0.399912 * np.cos(B) + 0.070257 * np.sin(B)
                   - 0.006758 * np.cos(2 * B) + 0.000907 * np.sin(2 * B)
                   - 0.002697 * np.cos(3 * B) + 0.00148 * np.sin(3 * B))

    # Solar time (hours): 12:00 is the moment the sun is exactly in the south.
    # The Earth turns 15 degrees per hour, so longitude / 15 converts degrees to hours.
    solar_time = hour_utc + longitude / 15 + equation_of_time / 60

    # Hour angle (degrees), kept between -180 and +180
    hour_angle = 15 * (solar_time - 12)
    hour_angle = (hour_angle + 180) % 360 - 180

    phi = np.radians(latitude)
    omega = np.radians(hour_angle)

    # Sun height
    sin_height = np.sin(phi) * np.sin(declination) + np.cos(phi) * np.cos(declination) * np.cos(omega)
    height = np.arcsin(sin_height)

    # Sun azimuth (0 = south, west positive)
    azimuth = np.arctan2(np.sin(omega),
                         np.cos(omega) * np.sin(phi) - np.tan(declination) * np.cos(phi))

    return pd.DataFrame({
        "declination_deg": np.degrees(declination),
        "equation_of_time_min": equation_of_time,
        "solar_time_h": solar_time % 24,
        "hour_angle_deg": hour_angle,
        "sun_height_deg": np.degrees(height),
        "sun_azimuth_deg": np.degrees(azimuth),
    }, index=times_utc)


def incidence_angle(sun, wall_azimuth=0.0):
    """
    Angle (degrees) between the sun's rays and the line straight out of a VERTICAL window.

    sun          : table from sun_position()
    wall_azimuth : direction the window faces (0 = south, -90 = east, +90 = west)
    Returns 90 when the sun is below the horizon or behind the wall (no direct sun).
    """
    height = np.radians(sun["sun_height_deg"])
    difference = np.radians(sun["sun_azimuth_deg"] - wall_azimuth)
    cos_incidence = np.cos(height) * np.cos(difference)
    cos_incidence = cos_incidence.where(sun["sun_height_deg"] > 0, 0)    # night
    cos_incidence = cos_incidence.clip(lower=0)                          # sun behind the wall
    return np.degrees(np.arccos(cos_incidence))


def profile_angle(sun, wall_azimuth=0.0):
    """
    Profile angle (degrees): the sun height seen in a side view of the wall.
    Empty (NaN) when there is no direct sun on the wall.
    """
    height = np.radians(sun["sun_height_deg"])
    difference = np.radians(sun["sun_azimuth_deg"] - wall_azimuth)
    in_front = (sun["sun_height_deg"] > 0) & (np.cos(difference) > 0)
    profile = np.degrees(np.arctan2(np.tan(height), np.cos(difference)))
    return profile.where(in_front)


def one_day(date, latitude, longitude, step_minutes=1):
    """
    Sun position for one whole LOCAL day, in small time steps. Used for tests and figures.
    The day starts at local midnight by the sun (UTC shifted by longitude / 15 hours),
    so that sunrise always comes before sunset, also far from Greenwich (e.g. Denver).
    """
    start = pd.Timestamp(date, tz="UTC") - pd.Timedelta(hours=longitude / 15)
    times = pd.date_range(start.round("min"), periods=24 * 60 // step_minutes,
                          freq=f"{step_minutes}min")
    return sun_position(times, latitude, longitude)


def test_against_pvgis(city):
    """Compare our sun with what PVGIS says in the weather file."""
    latitude, longitude = CITIES[city]
    weather = load_weather(city)
    sun = sun_position(weather.index, latitude, longitude)

    print(f"\n=== {city} (latitude {latitude}, longitude {longitude}) ===")

    # Test 1: PVGIS gives the sun height for every hour. Ours must be the same.
    daytime = weather["sun_height_deg"] > 0
    difference = (sun["sun_height_deg"] - weather["sun_height_deg"])[daytime]
    print(f"1) Sun height, ours minus PVGIS, {daytime.sum()} daytime hours: "
          f"mean {difference.mean():+.2f}, largest {difference.abs().max():.2f} degrees")

    # Test 2: PVGIS gives no azimuth, but it gives the DIRECT sunlight on the south wall.
    # If our azimuth is right, there is direct sunlight only when our sun is in front of the wall.
    no_direct_sun = incidence_angle(sun, wall_azimuth=0) >= 90
    wrong = weather["beam_W_m2"][no_direct_sun]
    print(f"2) Hours where PVGIS has direct sun on the wall but our sun is behind it or down: "
          f"{(wrong > 0).sum()} of {len(weather)} "
          f"(largest value {wrong.max():.1f} W/m2)")

    # Test 3: at solar noon the sun height must be 90 - latitude + declination (simple geometry)
    print("3) Sun at solar noon:")
    print(f"   {'day':12s} {'declination':>11s} {'height':>8s} {'90-lat+decl':>12s} "
          f"{'azimuth':>8s} {'incidence on south window':>26s}")
    for date in ["2022-03-21", "2022-06-21", "2022-09-21", "2022-12-21"]:
        day = one_day(date, latitude, longitude)
        noon = day.loc[day["sun_height_deg"].idxmax()]
        angle = incidence_angle(day, wall_azimuth=0).loc[noon.name]
        print(f"   {date:12s} {noon['declination_deg']:11.2f} {noon['sun_height_deg']:8.2f} "
              f"{90 - latitude + noon['declination_deg']:12.2f} {noon['sun_azimuth_deg']:8.2f} {angle:26.2f}")

    # Test 4: at the equinox the sun rises exactly in the east (-90) and sets in the west (+90)
    day = one_day("2022-03-20", latitude, longitude)
    up = day[day["sun_height_deg"] > 0]
    print(f"4) Equinox (20 March): sunrise azimuth {up['sun_azimuth_deg'].iloc[0]:.1f}, "
          f"sunset azimuth {up['sun_azimuth_deg'].iloc[-1]:.1f} degrees (should be -90 and +90)")


if __name__ == "__main__":
    for city_name in CITIES:
        if raw_file_path(city_name).exists():      # only cities that are already downloaded
            test_against_pvgis(city_name)
