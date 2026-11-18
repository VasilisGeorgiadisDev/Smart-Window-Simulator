"""
shading.py
----------
Shade of a balcony (a horizontal overhang) above a window.

Side view of the wall:

        balcony  ______________
        (depth d)              |
     wall |                    .  <- sun ray passing the front edge of the balcony
          |  gap g           .
          |----------      .        p = profile angle of the sun (sun.py)
          |  window  |   .          shadow on the wall reaches  d x tan(p)  below the balcony
          |  height H| .
          |----------

1) DIRECT sun: the part of the window height that is inside the shadow is in the shade.

       shadow length      s = d tan(p)
       shaded height      clip(s - g, 0, H)
       sunlit fraction    f_sun = 1 - shaded height / H

2) DIFFUSE light from the sky: the balcony hides part of the sky. For a point on the wall at a
   distance y below the balcony, only the sky between the horizon and the angle atan(y/d) is
   visible. With light coming equally from all parts of the sky, the visible fraction of the sky
   for that point is  y / sqrt(y^2 + d^2). The average over the window height is

       f_sky = ( sqrt((g + H)^2 + d^2) - sqrt(g^2 + d^2) ) / H

3) Light REFLECTED from the ground comes from below the horizon, so the balcony does not hide it.

The derivations are written out in docs/equations.md (section 5).

ASSUMPTIONS:
    - the balcony is much wider than the window, so no sun passes beside it (2D geometry)
    - the sky is equally bright in all directions (isotropic) for the diffuse part
    - light reflected by the balcony itself, and the balcony railing, are ignored

Run this file directly to print a few test values:
    python src/shading.py
"""

import numpy as np


def sunlit_fraction(profile_deg, depth, gap, window_height):
    """
    Fraction of the window that is in direct sun (1 = no shade, 0 = all in shade).

    profile_deg   : profile angle of the sun in degrees (from sun.profile_angle), NaN when
                    there is no direct sun on the wall (then the result does not matter: 1)
    depth         : depth of the balcony, m
    gap           : distance from the top of the window to the underside of the balcony, m
    window_height : height of the window, m
    """
    profile = np.radians(np.asarray(profile_deg, dtype=float))
    shadow = depth * np.tan(profile)                              # m below the balcony
    shaded_height = np.clip(shadow - gap, 0, window_height)
    fraction = 1 - shaded_height / window_height
    return np.where(np.isnan(fraction), 1.0, fraction)


def sky_fraction(depth, gap, window_height):
    """Fraction of the diffuse sky light that still reaches the window (1 = no balcony)."""
    top = np.sqrt(gap ** 2 + depth ** 2)
    bottom = np.sqrt((gap + window_height) ** 2 + depth ** 2)
    return (bottom - top) / window_height


if __name__ == "__main__":
    d, g, H = 1.0, 0.5, 2.2
    print(f"Balcony depth {d} m, gap {g} m, window height {H} m")
    print(f"Diffuse sky light reaching the window: {sky_fraction(d, g, H):.3f}")
    print(f"Without balcony (depth 0): {sky_fraction(0.0, g, H):.3f} (should be 1)")
    print("Profile angle -> sunlit fraction of the window:")
    for p in [10, 26.6, 28.6, 45, 60, 70.4, 75.5, 80]:
        print(f"  {p:5.1f} deg  shadow {d * np.tan(np.radians(p)):5.2f} m  "
              f"sunlit {float(sunlit_fraction(p, d, g, H)):.3f}")
