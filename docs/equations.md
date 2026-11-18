# Equations used in the Smart Window Energy Simulator

This document lists every equation the program uses, in the order the program uses them.
For each equation it gives the symbols, the units, the reference and the function in the
code that contains it.

Sections are added as the project grows. So far: **1. Position of the sun**,
**2. Solar heat through the glass**, **3. The room model**,
**4. The Athens living room**, **5. Shade of the balcony** and
**6. Smart glass and its control rule**.

---

## 1. Position of the sun

Code: [`src/sun.py`](../src/sun.py). Equations 1.1 to 1.6 are from NOAA [5].
Equations 1.7 to 1.9 are derived here from the direction of the sun as a vector.

### Symbols

| Symbol | Meaning | Unit |
|---|---|---|
| $n$ | day of the year (1 = 1 January) | – |
| $t_{UTC}$ | clock time in UTC | h |
| $\lambda$ | longitude of the place, east positive | ° |
| $\varphi$ | latitude of the place, north positive | ° |
| $B$ | position of the Earth on its orbit ("fractional year") | rad |
| $E$ | equation of time | min |
| $\delta$ | declination of the sun | ° |
| $t_s$ | solar time | h |
| $\omega$ | hour angle | ° |
| $h$ | sun height above the horizon | ° |
| $\gamma_s$ | sun azimuth: 0 = south, east negative, west positive | ° |
| $\gamma$ | direction the window faces, same convention | ° |
| $\theta$ | incidence angle on the window | ° |
| $p$ | profile angle | ° |

### 1.1 Position of the Earth on its orbit

$$B = \frac{2\pi}{365}\left(n - 1 + \frac{t_{UTC} - 12}{24}\right)$$

### 1.2 Equation of time

A sundial and a clock do not agree. The difference changes during the year, because the
orbit of the Earth is an ellipse and its axis is tilted. In our data $E$ goes from
−14.3 to +16.4 minutes.

$$E = 229.18\,\big(0.000075 + 0.001868\cos B - 0.032077\sin B - 0.014615\cos 2B - 0.040849\sin 2B\big)$$

### 1.3 Declination

The angle between the sun's rays and the plane of the equator: +23.4° on 21 June,
0° at the equinoxes, −23.4° on 21 December. The result of this series is in radians.

$$\delta = 0.006918 - 0.399912\cos B + 0.070257\sin B - 0.006758\cos 2B + 0.000907\sin 2B - 0.002697\cos 3B + 0.00148\sin 3B$$

### 1.4 Solar time

At solar time 12:00 the sun is exactly in the south. The Earth turns 15° per hour,
so the longitude in degrees divided by 15 gives hours.

$$t_s = t_{UTC} + \frac{\lambda}{15} + \frac{E}{60}$$

### 1.5 Hour angle

$$\omega = 15\,(t_s - 12)$$

Negative in the morning, zero at solar noon, positive in the afternoon.

### 1.6 Sun height

$$\sin h = \sin\varphi\,\sin\delta + \cos\varphi\,\cos\delta\,\cos\omega$$

**Check by hand.** At solar noon $\omega = 0$, so $\sin h = \cos(\varphi - \delta)$ and

$$h_{noon} = 90^\circ - \varphi + \delta$$

For Athens ($\varphi = 37.98^\circ$): 21 June gives $90 - 37.98 + 23.45 = 75.47^\circ$ and
21 December gives $90 - 37.98 - 23.42 = 28.60^\circ$. The program gives the same two values.

### 1.7 Sun azimuth

Take axes $x$ = east, $y$ = north, $z$ = up at the place of the window. The unit vector
that points to the sun has these three parts (from the declination, the hour angle and
the latitude):

$$\vec{s} = \begin{pmatrix}
-\cos\delta\,\sin\omega \\
\sin\delta\,\cos\varphi - \cos\delta\,\sin\varphi\,\cos\omega \\
\sin\delta\,\sin\varphi + \cos\delta\,\cos\varphi\,\cos\omega
\end{pmatrix}$$

The third part is $\sin h$: this is equation 1.6. The azimuth is the direction of the
horizontal part of $\vec{s}$, measured from south towards west, so
$\tan\gamma_s = (-s_x)/(-s_y)$:

$$\tan\gamma_s = \frac{\sin\omega}{\cos\omega\,\sin\varphi - \tan\delta\,\cos\varphi}$$

The program uses the function `arctan2(numerator, denominator)`, which also puts the angle
in the right quarter of the circle (the sun can be north of east in summer).

**Check by hand.** At solar noon $\omega = 0$, so the numerator is 0 and $\gamma_s = 0$:
the sun is exactly in the south.

### 1.8 Incidence angle on a vertical window

Written with the sun height and azimuth, the same vector $\vec{s}$ and the unit vector
that points straight out of the window are

$$\vec{s} = \begin{pmatrix} -\cos h\,\sin\gamma_s \\ -\cos h\,\cos\gamma_s \\ \sin h \end{pmatrix}
\qquad
\vec{n} = \begin{pmatrix} -\sin\gamma \\ -\cos\gamma \\ 0 \end{pmatrix}$$

The incidence angle is the angle between them, so $\cos\theta = \vec{s}\cdot\vec{n}$:

$$\cos\theta = \cos h\,\cos(\gamma_s - \gamma)$$

If $\cos\theta \le 0$ the sun is behind the wall, and if $h \le 0$ it is below the horizon.
In both cases there is no direct sun on the window, and the program sets $\theta = 90^\circ$.

For a south window at solar noon, $\gamma_s = \gamma = 0$, so $\theta = h$.

### 1.9 Profile angle

Look at the wall from the side. The sun then appears at the profile angle $p$ above the
horizontal. It is larger than $h$ whenever the sun is not exactly in front of the wall.

$$\tan p = \frac{\tan h}{\cos(\gamma_s - \gamma)}$$

It follows from the vector $\vec{s}$ above: $\tan p$ is the vertical part of $\vec{s}$ divided by
its part along $\vec{n}$. Section 5 (balcony shade) will use it:
the shadow of a balcony of depth $d$ reaches a distance $d\,\tan p$ down the wall.

### Tests of section 1

Run `python src/sun.py`. Results for the 10 years 2014–2023:

| Test | Athens | Amsterdam | Denver |
|---|---|---|---|
| Sun height, ours minus PVGIS, mean | −0.02° | −0.03° | −0.02° |
| Sun height, ours minus PVGIS, largest difference | 0.47° | 0.34° | 0.43° |
| Hours with direct sun on the south wall in PVGIS while our sun is behind the wall or down | 19 of 87,648 (at most 2.6 W/m²) | 10 of 87,648 (at most 0.8 W/m²) | 18 of 87,648 (at most 1.9 W/m²) |
| Sun height at solar noon equals $90^\circ - \varphi + \delta$ | yes, to 0.01° | yes, to 0.01° | yes, to 0.01° |
| Sunrise and sunset azimuth on 20 March (expected −90° and +90°) | −89.1° and +89.4° | −89.0° and +89.3° | −89.3° and +89.6° |

PVGIS gives no sun azimuth, so the second test checks the azimuth indirectly.

### Not included

- Bending of light by the atmosphere (refraction), up to about 0.5° when the sun is on the horizon.
- The day number $n$ is taken from the UTC date. Far from Greenwich the local date can
  differ for a few hours; the declination changes by less than 0.4° per day.

---

## 2. Solar heat through the glass

Code: [`src/window.py`](../src/window.py). Reference: ASHRAE Standard 140 [6], Annex B6.

### Symbols

| Symbol | Meaning | Unit |
|---|---|---|
| $G_b$ | direct (beam) sunlight on the window | W/m² |
| $G_d$ | diffuse light from the sky on the window | W/m² |
| $G_r$ | light reflected from the ground onto the window | W/m² |
| $g_0$ | SHGC of the window for head-on sunlight ($\theta = 0$) | – |
| $g(\theta)$ | SHGC at incidence angle $\theta$ | – |
| $g_{dif}$ | SHGC for diffuse light (light from all directions at once) | – |
| $f(\theta)$ | angle factor | – |
| $f_{dif}$ | diffuse factor | – |
| $q_{sol}$ | solar heat entering through 1 m² of glass | W/m² |
| $A_w$ | glass area | m² |
| $Q_{sol}$ | solar heat entering the room | W |

$G_b$, $G_d$ and $G_r$ come from PVGIS for every hour. $\theta$ comes from section 1.8.

### 2.1 Angle factor

Glass reflects more light when the rays arrive at a flat angle, so the SHGC falls.
The angle factor is the SHGC at an angle divided by the head-on SHGC:

$$f(\theta) = \frac{g(\theta)}{g_0}$$

Values from [6], calculated there with the LBNL program WINDOW 7:

| $\theta$ | single clear | double clear | double low-E |
|---|---|---|---|
| 0° | 1.000 | 1.000 | 1.000 |
| 30° | 0.994 | 0.990 | 0.982 |
| 50° | 0.962 | 0.934 | 0.916 |
| 60° | 0.909 | 0.847 | 0.820 |
| 70° | 0.779 | 0.662 | 0.632 |
| 80° | 0.491 | 0.347 | 0.336 |
| 90° | 0 | 0 | 0 |

The table in [6] has one value every 10°. Between them the program draws straight lines.

### 2.2 Diffuse factor

Diffuse light arrives from all directions at once, so it has one fixed factor:

$$f_{dif} = \frac{g_{dif}}{g_0}$$

From [6]: 0.911 (single clear), 0.871 (double clear), 0.857 (double low-E).

### 2.3 Solar heat gain

$$q_{sol} = g_0\,\big[\,f(\theta)\,G_b + f_{dif}\,(G_d + G_r)\,\big]$$

$$Q_{sol} = A_w\,q_{sol}$$

Before this section the program used $q_{sol} = g_0\,(G_b + G_d + G_r)$, the same SHGC at every angle.

### Assumptions of section 2

- We use only the **shape** of the curves in [6] and multiply it by the head-on SHGC of our
  own windows. Each window takes the curve of the most similar glazing.
- For the electrochromic windows no curve is published. We use the double clear curve.
  With the double low-E curve instead, the yearly solar heat through the clear SageGlass
  window in Athens changes by −2.0 %.
- The ground-reflected light uses the same factor as the sky light.

### Tests and results of section 2

- With all factors set to 1, equation 2.3 gives exactly the old result
  (largest difference $10^{-13}$ W/m²).
- Athens, main normal window (double low-E, $g_0 = 0.568$), 10-year mean: the yearly solar heat
  through 1 m² of glass falls from 741 to 610 kWh (−18 %). The factor is 0.92 in January and
  0.69 in July, because the summer sun is high and hits a south window at a flat angle.
- Denver test (`python src/validation.py`): cooling falls from 10.29 to 8.34 MWh per year.
  The accepted range is 5.00 to 6.83, so the model is still 22 % too high. Heating is
  4.52 MWh, inside the accepted range of 3.75 to 4.98.

---

## 3. The room model (ISO 13790, simple hourly method)

Code: [`src/room_model.py`](../src/room_model.py), function `simulate_5r1c`. Reference: [7].
The equation numbers C.1 to C.13 are those of ISO 13790, Annex C.

The model is an electric circuit with **5 resistances and 1 capacitor** ("5R1C").
Temperature plays the role of voltage and heat flow the role of current.
The room has three temperatures:

- $T_{air}$: the room air. The thermostat controls this one.
- $T_s$: the inner surfaces of the walls, the floor and the ceiling.
- $T_m$: the heavy material behind the surfaces. Only this one stores heat.

The sun's heat goes to the surfaces and the mass, **not** directly to the air.

### Symbols

| Symbol | Meaning | Unit |
|---|---|---|
| $T_e$ | outdoor air temperature | °C |
| $A_f$ | floor area | m² |
| $A_t$ | area of all surfaces that face the room | m² |
| $A_m$ | effective mass area | m² |
| $C_m$ | heat capacity of the mass | Wh/K |
| $\Delta t$ | time step, 1 hour | h |
| $H_{ve}$ | air ↔ outside, by fresh air | W/K |
| $H_w$ | surfaces ↔ outside, through the window | W/K |
| $H_{op}$ | total of walls, roof and floor, $\sum U A$ | W/K |
| $H_{is}$ | air ↔ surfaces | W/K |
| $H_{ms}$ | surfaces ↔ mass | W/K |
| $H_{em}$ | mass ↔ outside | W/K |
| $Q_{int}$ | heat from people and devices | W |
| $Q_{sol}$ | solar heat through the window (section 2) | W |
| $Q_{HC}$ | heating (+) or cooling (−) | W |

### 3.1 The five heat paths

$$H_{ve} = 0.33\,n\,V \qquad H_w = U_w A_w \qquad H_{op} = \sum U_i A_i$$

$n$ is the number of air changes per hour, $V$ the room volume, and 0.33 Wh/(m³K) the
heat capacity of air [4].

$$H_{is} = 3.45\,A_t \qquad H_{ms} = 9.1\,A_m \qquad A_m = 2.5\,A_f$$

$$H_{em} = \frac{1}{\dfrac{1}{H_{op}} - \dfrac{1}{H_{ms}}}$$

The last equation, ISO 13790 Equation (64) [8], splits the path through the walls into two
resistances in series, with the mass between them. Their total is again $1/H_{op}$, so the
steady heat loss through the walls stays $\sum U A$.

$A_m$ and $C_m$ can also be taken from the classes of ISO 13790, Table 12 [8]:

| Class | $A_m$ | $C_m$ (J/K) |
|---|---|---|
| Very light | $2.5\,A_f$ | $80\,000\,A_f$ |
| Light | $2.5\,A_f$ | $110\,000\,A_f$ |
| Medium | $2.5\,A_f$ | $165\,000\,A_f$ |
| Heavy | $3.0\,A_f$ | $260\,000\,A_f$ |
| Very heavy | $3.5\,A_f$ | $370\,000\,A_f$ |

### 3.2 Where the heat goes (C.1, C.2, C.3)

$$Q_{air} = 0.5\,Q_{int} + Q_{HC}$$

$$Q_m = \frac{A_m}{A_t}\,\big(0.5\,Q_{int} + Q_{sol}\big)$$

$$Q_s = \left(1 - \frac{A_m}{A_t} - \frac{H_w}{9.1\,A_t}\right)\big(0.5\,Q_{int} + Q_{sol}\big)$$

Half of the internal heat is assumed to be warm air, the other half is radiation, like the sun.
The three fractions do not add up to 1: the small rest, $H_w/(9.1\,A_t)$, counts as radiation
that is lost through the window.

### 3.3 Three short names (C.6, C.7, C.8)

$$H_1 = \frac{1}{\dfrac{1}{H_{ve}} + \dfrac{1}{H_{is}}} \qquad H_2 = H_1 + H_w \qquad H_3 = \frac{1}{\dfrac{1}{H_2} + \dfrac{1}{H_{ms}}}$$

### 3.4 Temperature of the mass after one hour (C.4, C.5)

The heat balance of the mass is $C_m\,dT_m/dt = H_{ms}(T_s - T_m) + H_{em}(T_e - T_m) + Q_m$.
It is solved with the Crank–Nicolson method (the mean of the old and the new temperature is
used on the right-hand side):

$$Q_{m,tot} = Q_m + H_{em} T_e + \frac{H_3}{H_2}\left[Q_s + H_w T_e + H_1\left(\frac{Q_{air}}{H_{ve}} + T_e\right)\right]$$

$$T_{m,new} = \frac{T_{m,old}\left(\dfrac{C_m}{\Delta t} - \dfrac{H_3 + H_{em}}{2}\right) + Q_{m,tot}}{\dfrac{C_m}{\Delta t} + \dfrac{H_3 + H_{em}}{2}}$$

### 3.5 The three temperatures of the hour (C.9, C.10, C.11)

$$T_m = \frac{T_{m,old} + T_{m,new}}{2}$$

$$T_s = \frac{H_{ms} T_m + Q_s + H_w T_e + H_1\left(T_e + \dfrac{Q_{air}}{H_{ve}}\right)}{H_{ms} + H_w + H_1}$$

$$T_{air} = \frac{H_{is} T_s + H_{ve} T_e + Q_{air}}{H_{is} + H_{ve}}$$

### 3.6 Heating and cooling (C.13)

1. Calculate the hour with $Q_{HC} = 0$. This gives $T_{air,0}$.
2. If $T_{air,0}$ is between the two thermostat settings, nothing is needed.
3. If not, calculate the hour again with a trial power $Q_{10} = 10\ \mathrm{W/m^2} \times A_f$.
   This gives $T_{air,10}$. All equations are linear, so the power that brings the air
   exactly to the setting $T_{set}$ is

$$Q_{HC} = Q_{10}\,\frac{T_{set} - T_{air,0}}{T_{air,10} - T_{air,0}}$$

A positive $Q_{HC}$ is heating, a negative one is cooling.

### Assumptions of section 3

- $C_m$ of the test room is calculated from its real layers: only the layers on the inner
  side of the insulation store heat (plasterboard and timber floor, 536 Wh/K in total).
- $A_t$ of the test room is its real inner surface, 171.6 m².
- Fresh air enters at the outdoor temperature.
- Not included: sun on the outside of walls and roof, and heat radiated to the cold sky.

### Tests and results of section 3

Run `python src/validation.py`. The test is BESTEST Case 600 in Denver [3], [6].
Weather: PVGIS 2014–2023 (the standard uses one typical year). Values in MWh per year.

| Model | Heating | Cooling |
|---|---|---|
| 1) 1R1C, same SHGC at all angles | 4.43 | 10.29 |
| 2) 1R1C, SHGC with sun angle | 4.52 | 8.34 |
| 3) 5R1C, SHGC with sun angle | **3.95** | **6.66** |
| Reference programs [3] | 3.99 – 4.50 | 5.43 – 6.16 |
| Accepted range [3] | 3.75 – 4.98 | 5.00 – 6.83 |

Model 3 is inside both accepted ranges. Compared with the reference programs, its heating
is 1 % below the lowest and its cooling 8 % above the highest.

Sanity checks of model 3 over the 10 years:

- Energy balance: heat in − heat out − change of stored heat = $-1\times10^{-7}$ Wh,
  of $1.8\times10^{8}$ Wh that entered.
- Air temperature always between 20.00 and 27.00 °C.
- No hour with both heating and cooling.

The result depends on $C_m$. With half the value, heating is 4.46 and cooling 7.34 MWh.
With double the value, heating is 2.90 and cooling 5.32 MWh.

### The same room in Athens (the fixed test environment of the project)

Run `python src/athens_bestest.py`. The room, gains and thermostat are those of the standard.
Only the weather (Athens, PVGIS 2014–2023), the air leakage (0.5 air changes per hour, the
value of the standard at sea level [3]) and the window change. 10-year mean, kWh per year
(lowest and highest year in brackets):

| Window | Case | Heating | Cooling |
|---|---|---|---|
| BESTEST: double clear, $U = 2.10$, SHGC 0.769 [6] | 600 | 1187 (1026 – 1345) | 6685 (6186 – 7056) |
| BESTEST: double clear | 610 (overhang) | 1221 (1054 – 1383) | 4838 (4400 – 5243) |
| Normal: double low-E, $U = 1.493$, SHGC 0.568 [1] | 600 | 1094 (939 – 1245) | 4697 (4330 – 4980) |
| Normal: double low-E | 610 (overhang) | 1129 (965 – 1285) | 3382 (3060 – 3686) |

Same room and window (BESTEST, Case 600) in the two cities: Denver heating 3949, cooling 6661;
Athens heating 1187, cooling 6685 kWh per year.

With the normal window (Case 600), 60 % of the cooling happens while the outside air is
below 27 °C and 38 % from November to April. The standard room is sealed and light, with a
large south window, so the winter sun overheats it. Its results are for comparing windows
and climates in the same room, not the energy use of real homes.

---

## 4. The Athens living room

Code: [`src/athens_flat.py`](../src/athens_flat.py). The room is put into the model of
section 3. Values from TABULA [9], the Greek KENAK guide T.O.T.E.E. 20701-1 [10] and ISO 13790 [8].

**A side study**, not part of the main comparison (sections 3 and 6). The room size, the door
and the balcony are our own choices, and the neighbours are assumed to be at the same
temperature, so the results do not fully reflect a real flat.

### The case

The living room of a flat on a middle floor of an Athens apartment block built before 1980.
Only the south wall touches the outside. The other walls, the floor and the ceiling touch
rooms that are assumed to be at the same temperature, so no heat flows through them.

| Quantity | Value | Source |
|---|---|---|
| Room: width × depth × height | 4.0 × 5.0 × 2.7 m | our choice |
| Balcony door: width × height | 2.0 × 2.2 m | our choice |
| Wall: double brick, plastered, no insulation | $U = 2.20$ W/(m²K) | [9] Table 2.3 |
| Wall colour: light-coloured plaster (light grey) | solar absorptance $\alpha = 0.40$ | [10] Table 3.15 |
| Outside surface resistance | $R_{se} = 0.04$ m²K/W | [4] Table 1 |
| Window: single glass, **glass only** (no frame) | $U = 5.70$ W/(m²K) | [10] Table 3.8 |
| | $g_0 = 0.85$ (normal incidence) | [10] Table 3.17 |
| Air leaking through a single-glazed aluminium window | 8.05 m³/h per m² of window | [9] Table 4.5 |
| Fresh air | 0.75 m³/h per m² of floor | [9] Table 3.1 |
| Heat from people, devices, lamps | 4 + 2 + 0.64 W per m² of floor | [9] Table 3.1 |
| Thermostat | 20 °C heating, 26 °C cooling | [9] Table 3.1 |
| Hours of use | 18 per day | [9] Table 3.1 |
| Heat storage class | heavy | [8] Table 12 |

### 4.1 Areas

$$A_f = 4.0 \times 5.0 = 20\ \mathrm{m^2} \qquad V = A_f \times 2.7 = 54\ \mathrm{m^3}$$

$$A_w = 2.0 \times 2.2 = 4.4\ \mathrm{m^2} \qquad A_{wall} = 4.0 \times 2.7 - A_w = 6.4\ \mathrm{m^2}$$

$$A_t = 2A_f + 2\,(4.0 + 5.0) \times 2.7 = 88.6\ \mathrm{m^2}$$

### 4.2 Air

The leaking air and the fresh air are added together, as [9] states.

$$\dot V = 8.05\,A_w + 0.75\,A_f = 35.4 + 15.0 = 50.4\ \mathrm{m^3/h}$$

$$H_{ve} = 0.33\,\dot V = 16.6\ \mathrm{W/K}$$

This is $50.4/54 = 0.93$ air changes per hour.

### 4.3 Walls and window

$$H_w = 5.70 \times 4.4 = 25.1\ \mathrm{W/K} \qquad H_{op} = 2.20 \times 6.4 = 14.1\ \mathrm{W/K}$$

The window loses almost twice as much heat as the brick wall, on a smaller area.

### 4.4 Gains and heat storage

$$Q_{int} = (4 + 2 + 0.64)\,A_f = 132.8\ \mathrm{W}\ \text{during the 18 hours of use, } 0 \text{ at night}$$

$$C_m = \frac{260\,000\,A_f}{3600} = 1444\ \mathrm{Wh/K} \qquad A_m = 3.0\,A_f = 60\ \mathrm{m^2}$$

The time constant of the room is $C_m / (H_w + H_{op} + H_{ve}) = 1444/55.8 = 26$ hours.

### 4.5 Solar heat through the glass

Equation 2.3 with $g_0 = 0.85$, the single clear glass curve, and the window facing south
($\gamma = 0$).

**Why glass only, and not the TABULA window ($U_w = 6.1$, $g = 0.58$ [9] Table 2.4)?**
The Greek guide [10] (Eq. 3.9) defines the $g$ of a whole window as

$$g_w = (1 - F_f)\times 0.9\times g_0$$

where $F_f$ is the fraction of the opening covered by the frame and 0.9 is an average over
the angles of the sun. With $g_0 = 0.85$ and $F_f = 0.25$:
$0.75 \times 0.9 \times 0.85 = 0.57 \approx 0.58$. So the TABULA value already contains a frame and an
angle average. Our angle curve (section 2) would then count the angle a second time.
Also, the new and smart windows of the next phases only have glass values. To compare all
windows on the same basis, every window is modelled as glass only.

### 4.6 Sun on the brick wall

Sun absorbed at the outside surface of the wall heats that surface. In steady state the heat
splits into two paths: outwards through $R_{se}$ to the outside air, and inwards through the
rest of the wall, $R_{total} - R_{se}$, to the room. The two paths are in parallel, so the
fraction that flows inwards is

$$\frac{R_{se}}{R_{total}} = U\,R_{se}$$

and the heat reaching the room is

$$Q_{wall} = \alpha\,U\,R_{se}\,A_{wall}\,\big(f_{sun,wall}\,G_b + f_{sky,wall}\,G_d + G_r\big)$$

**Check by hand.** $U R_{se} = 2.20 \times 0.04 = 0.088$: only about 9 % of the absorbed sun
reaches the room. On a summer noon with 300 W/m² on the wall:
$0.40 \times 0.088 \times 6.4 \times 300 = 68$ W.

Without a balcony $f_{sun,wall} = f_{sky,wall} = 1$. With the balcony, they come from
section 5 with gap $g = 0$ and height $H = 2.7$ m (the whole wall height).
$Q_{wall}$ is added to the solar heat of the window in the room model (section 3).

### 4.7 Hours of use

The thermostat works from 06:00 to 24:00 Athens time (summer and winter time are taken into
account). From 00:00 to 06:00 there is no heating or cooling, and the room temperature
floats. ISO 13790 lists "night time switch off" as one of the normal modes of use [8].
The heat from people, devices and lamps is given only during the same 18 hours.

### Assumptions of section 4

- The rooms next to, above and below the living room are at the same temperature.
  This is the most important assumption: if the neighbours do not heat, the room loses more heat.
- The 18 hours of use are 06:00 to 24:00. [9] gives the number of hours, not which ones.
- Internal gains only during the hours of use; fresh air constant day and night.
- No window frame (all windows glass only, see 4.5).
- Sun on the wall reaches the room at once (steady state). A real heavy wall delays it by
  some hours. The wall-sun calculation uses the whole wall height, also where the door is.
- Not included: heat radiated from the wall and the glass to the cold night sky (no public
  source with the formula and its values was found; it would lower the net solar heat a little),
  opening the window.

### Results of section 4

Run `python src/athens_flat.py`. Old window, no balcony, 10-year mean (2014–2023):

| | Heating | Cooling |
|---|---|---|
| kWh per year | 198 (lowest year 119, highest 254) | 2127 (lowest 1955, highest 2265) |
| kWh per m² of floor | 10 | 106 |
| With the thermostat and the internal gains on 24 h a day | 205 | 2331 |

Solar heat per year: 4336 kWh through the glass, 294 kWh through the brick wall.

Sanity checks: energy balance error $1\times10^{-7}$ Wh; air between 20.00 and 26.00 °C
while the thermostat is on; no heating or cooling while it is off; never both in one hour.

---

## 5. Shade of the balcony

Code: [`src/shading.py`](../src/shading.py). Figure:
[`figures/athens_balcony_shadow.png`](../figures/athens_balcony_shadow.png).
The equations are derived here from geometry; they use the profile angle $p$ of section 1.9.

### Symbols

| Symbol | Meaning | Unit |
|---|---|---|
| $d$ | depth of the balcony (how far it sticks out) | m |
| $g$ | gap between the top of the window and the underside of the balcony | m |
| $H$ | height of the window | m |
| $p$ | profile angle of the sun (section 1.9) | ° |
| $s$ | how far the shadow reaches down the wall, measured from the balcony | m |
| $f_{sun}$ | fraction of the window in direct sun | – |
| $f_{sky}$ | fraction of the diffuse sky light that still reaches the window | – |

### 5.1 Length of the shadow

In a side view of the wall, the sun ray that just passes the front edge of the balcony makes
the angle $p$ with the horizontal. It travels the horizontal distance $d$ back to the wall,
so it reaches the wall a height $d\tan p$ below the balcony:

$$s = d\,\tan p$$

**Check by hand.** Athens, 21 June at noon: $p = 75.5^\circ$, so $s = 1.0 \times \tan 75.5^\circ = 3.87$ m.
The shadow is longer than the whole wall (2.7 m), so the door is completely in shade.
21 December at noon: $p = 28.6^\circ$, so $s = 0.55$ m. The shadow ends 0.05 m below the
top of the door, which is almost completely in sun.

### 5.2 Fraction of the window in direct sun

The top of the window is $g$ below the balcony. The part of the window inside the shadow has
the height $s - g$, but never less than 0 and never more than $H$:

$$f_{sun} = 1 - \frac{\min\big(\max(s - g,\ 0),\ H\big)}{H}$$

Because the balcony is assumed to be much wider than the window, the shadow edge is a
horizontal line, and this one-dimensional fraction is exact.

### 5.3 Fraction of the diffuse sky light

Take a point on the wall at a distance $y$ below the balcony. Looking out, it sees the sky
from the horizon up to the edge of the balcony, at the angle $\alpha$ with

$$\tan\alpha = \frac{y}{d}$$

Above $\alpha$ the balcony hides the sky. For a long, horizontal obstruction and a sky that
is equally bright in all directions, the light that a vertical surface receives from the band
between the horizon and $\alpha$ is proportional to $\sin\alpha$. (With Lambert's cosine law,
each direction at angle $\phi$ above the horizon contributes in proportion to $\cos\phi$, and
$\int_0^{\alpha}\cos\phi\,d\phi = \sin\alpha$.) Without a balcony, $\alpha = 90^\circ$ and
$\sin\alpha = 1$. So the fraction of the sky light that the point still receives is

$$\sin\alpha = \frac{y}{\sqrt{y^2 + d^2}}$$

The window goes from $y = g$ to $y = g + H$. The average over its height is

$$f_{sky} = \frac{1}{H}\int_g^{g+H}\frac{y}{\sqrt{y^2+d^2}}\,dy = \frac{\sqrt{(g+H)^2 + d^2} - \sqrt{g^2 + d^2}}{H}$$

**Check by hand.** With $d = 0$ (no balcony), $f_{sky} = \big((g+H) - g\big)/H = 1$.
For our door ($d = 1.0$, $g = 0.5$, $H = 2.2$):
$f_{sky} = (\sqrt{8.29} - \sqrt{1.25})/2.2 = (2.879 - 1.118)/2.2 = 0.80$.

### 5.4 Solar heat with the balcony

Equation 2.3 becomes

$$q_{sol} = g_0\,\big[\,f(\theta)\,f_{sun}\,G_b + f_{dif}\,(f_{sky}\,G_d + G_r)\,\big]$$

The light reflected from the ground $G_r$ comes from below the horizon, so the balcony does not hide it.

### Assumptions of section 5

- The balcony is much wider than the window (no sun passes beside it).
- The sky is equally bright in all directions. (PVGIS uses a more detailed sky model to give
  $G_d$; we only use the isotropic sky to calculate what the balcony hides.)
- Light reflected by the balcony itself, and the balcony railing, are ignored.
- Athens room: the underside of the balcony is at our ceiling level, so $g = 2.7 - 2.2 = 0.5$ m.
  The depth $d = 1.0$ m is our choice.

### Tests and results of section 5

**Validation: BESTEST Case 610** [3]. The same Denver room as in section 3, with a 1 m deep
overhang 0.5 m above the 2 m high windows. Run `python src/validation.py`.

| | Our model, Case 600 → 610 | Reference programs, mean, 600 → 610 | Case 610 accepted range |
|---|---|---|---|
| Heating (MWh/yr) | 3.95 → 4.05 (+2 %) | 4.21 → 4.31 (+2 %) | 3.61 – 5.27 |
| Cooling (MWh/yr) | 6.66 → 4.71 (−29 %) | 5.86 → 4.26 (−27 %) | 2.74 – 6.03 |

Both results of our model are inside the accepted ranges, and the change caused by the
overhang is almost the same as in the professional programs.

**Athens living room, old window**, 10-year mean (2014–2023), kWh per year.
Run `python src/athens_flat.py`.

| | Solar heat through the door | Solar heat through the wall | Heating | Cooling |
|---|---|---|---|---|
| Case A: balcony above (1.0 m) | 3354 | 189 | 243 | 1421 |
| Case B: no balcony | 4336 | 294 | 198 | 2127 |
| Balcony effect | −23 % | −36 % | +23 % (+45 kWh) | −33 % (−706 kWh) |

Other balcony depths (Case A):

| Depth (m) | 0 | 0.5 | 1.0 | 1.5 | 2.0 |
|---|---|---|---|---|---|
| Heating | 198 | 210 | 243 | 304 | 378 |
| Cooling | 2127 | 1844 | 1421 | 1130 | 943 |

The sanity checks of section 4 pass for both cases.

---

## 6. Smart glass and its control rule

Code: [`src/ec_comparison.py`](../src/ec_comparison.py), rule in `simulate_5r1c` of
[`src/room_model.py`](../src/room_model.py). Room: BESTEST Case 600 (section 3), in Athens
and in Amsterdam, with 0.5 air changes per hour (both cities are at sea level).

| Glass | U (W/m²K) | State | SHGC | $T_{vis}$ | Source |
|---|---|---|---|---|---|
| Normal: double low-E, argon | 1.49 | fixed | 0.568 | 0.745 | [1] |
| Smart: SageGlass Clear with SR2.0 | 1.65 | clear | 0.41 | 0.60 | [2] |
| | | light tint | 0.16 | 0.18 | [2] |
| | | full tint | 0.09 | 0.01 | [2] |

### 6.1 The control rule

Every hour, the model first calculates the free room temperature (no heating or cooling)
with the glass clear, $T_{air,0}^{clear}$ (section 3.6). Then

$$\text{state} = \begin{cases} \text{tinted} & \text{if } T_{air,0}^{clear} > \theta_{cool} \text{ and the sun is shining} \\ \text{clear} & \text{otherwise} \end{cases}$$

with $\theta_{cool} = 27$ °C. If the glass tints, the hour is calculated again with the solar
heat of the tinted state, and heating or cooling follow as in section 3.6.

This is a simple rule in an *ideal* form: it knows the room temperature of the hour in advance.
It is **not** the best possible rule: the rule with the full tint (run 5 below) saves more in
both cities, and the tint temperature of 27 °C is a choice that is not optimised here. A real
controller works with sensors, so it would likely save a little less than this ideal version of
the same rule.

**Why light tint is the main case:** the full tint saves more energy, but it lets through almost
no daylight. In Athens, the mean $T_{vis}$ over the daylight hours is 0.28 with the rule and the
full tint, and 0.01 when always tinted, against 0.36 with the rule and the light tint. Lamps are
not in the model, so a very dark glass would look better here than in reality.

### Assumptions of section 6

- The glass switches within the hour (real EC glass needs some minutes).
- All states follow the angle curve of clear double glazing (section 2).
- Electric light is not modelled. The mean $T_{vis}$ over the daylight hours is reported, so
  that a darker room is not hidden.

### Results of section 6

Athens, BESTEST Case 600, 10-year mean, kWh of heat per year:

| Run | Heating | Cooling | Total | Total vs normal | Glass tinted (% of daylight hours) | Mean $T_{vis}$ in daylight |
|---|---|---|---|---|---|---|
| 1) Normal glass | 1094 | 4697 | 5791 | – | – | 0.74 |
| 2) Smart, always clear | 1208 | 3198 | 4406 | −24 % | 0 | 0.60 |
| 3) Smart, always full tint | 1670 | 833 | 2503 | −57 % | 100 | 0.01 |
| 4) Smart + rule, light tint | 1247 | 1342 | 2588 | −55 % | 56 | 0.36 |
| 5) Smart + rule, full tint | 1255 | 947 | 2202 | −62 % | 54 | 0.28 |

All values in this section are rounded to whole numbers, so a total can differ by 1 from the
sum of its parts.

Of the saving of run 4 (3203 kWh), 1385 kWh (43 %) comes from the smart glass in its clear
state (run 1 → 2), and 1818 kWh (57 %) from switching (run 2 → 4). This is one way of
splitting the saving: taking the steps in a different order would give different shares.
The clear state differs from the normal glass in three ways (SHGC, U-value and angle curve);
the table at the end of this section shows what each one does.

With the rule (run 4), 1618 kWh of the 3355 kWh of cooling saved (48 %) falls from November
to April. The BESTEST room overheats in the winter sun because its window can never be opened
(section 3); this part of the saving is specific to the test room.

**Amsterdam**, same room and glass, 10-year mean, kWh of heat per year:

| Run | Heating | Cooling | Total | Total vs normal | Glass tinted (% of daylight hours) | Mean $T_{vis}$ in daylight |
|---|---|---|---|---|---|---|
| 1) Normal glass | 3286 | 1792 | 5078 | – | – | 0.74 |
| 2) Smart, always clear | 3600 | 934 | 4534 | −11 % | 0 | 0.60 |
| 3) Smart, always full tint | 4566 | 42 | 4608 | −9 % | 100 | 0.01 |
| 4) Smart + rule, light tint | 3636 | 201 | 3838 | −24 % | 19 | 0.52 |
| 5) Smart + rule, full tint | 3644 | 87 | 3732 | −27 % | 17 | 0.50 |

**Athens vs Amsterdam** (run 1 against run 4):

| | Athens | Amsterdam |
|---|---|---|
| Mean outside temperature (°C) | 18.2 | 11.3 |
| Sun on the south wall (kWh/m² per year) | 1305 | 943 |
| Energy saved by the smart glass (kWh per year) | 3203 | 1240 |
| Energy saved (%) | 55 % | 24 % |
| – of which May to October | 1731 | 992 |
| – of which November to April | 1472 | 248 |
| – from the lower SHGC of the clear state (run 1 → 2) | 1385 | 543 |
| – from switching (run 2 → 4) | 1818 | 697 |
| Extra heating caused by the smart glass | +152 | +350 |

**What the clear state does.** Run 1 → run 2 changes three things at once. Two extra runs
change them one at a time (kWh saved per year; a negative value means more energy):

| Change, normal glass → smart glass (clear) | Athens | Amsterdam |
|---|---|---|
| SHGC 0.568 → 0.41 | 1471 | 656 |
| U-value 1.49 → 1.65 W/(m²K) | −12 | −84 |
| Angle curve: double low-E → double clear (our assumption, section 2) | −74 | −28 |
| Total, run 1 → run 2 | 1385 | 543 |

All of the saving comes from the lower SHGC; the other two changes take a little of it back.
The higher U-value costs more in Amsterdam, where the room needs more heating. The angle curve that we assumed for the smart glass costs it energy
in both cities, so this assumption makes the smart glass look slightly worse, not better.

**How much depends on the sealed test room?** The window of the test room can never be opened,
so the room also needs cooling when it is mild outside. From May to October, with normal
glass, this share of the cooling happens while the outside air is cooler than the room:

| Outside air | Athens | Amsterdam |
|---|---|---|
| below 27 °C | 36 % | 91 % |
| below 24 °C | 16 % | 78 % |

In a real home, opening a window would remove part of this heat. So the real savings are
probably smaller than shown, most of all in Amsterdam, where almost all the cooling happens
with cool outside air. The answer to the main question stays the same: the smart glass saves
more in Athens, probably by an even larger factor.

Sanity checks of runs 4 and 5, both cities: energy balance error $\approx 10^{-7}$ Wh; air
between 20.00 and 27.00 °C; never heating and cooling in the same hour; never heating while
the glass is tinted.

---

## References

[1] EnergyPlus reference data set "WindowConstructs.idf" (U.S. Department of Energy,
NREL / LBNL), window 'Dbl LoE (e2=.1) Clr 6mm/13mm Arg'.
https://github.com/NREL/EnergyPlus/blob/develop/datasets/WindowConstructs.idf

[2] SageGlass (Saint-Gobain), "Performance & Acoustical Data" flyer, document MKT-043.7,
product "SageGlass Clear with SR2.0".
https://www.sageglass.com/sites/default/files/2024-03/mkt-043_performance_and_acoustical_data_flyer.pdf

[3] LBNL Modelica Buildings Library, BESTEST validation cases (ANSI/ASHRAE Standard 140):
room, constructions and the published results of the reference programs.
https://simulationresearch.lbl.gov/modelica/releases/latest/help/Buildings_ThermalZones_Detailed_Validation_BESTEST_Cases6xx.html

[4] ISO 6946:2007, surface resistances and the heat capacity of air.

[5] NOAA Global Monitoring Division, "General Solar Position Calculations" (2 pages, free).
https://gml.noaa.gov/grad/solcalc/solareqns.PDF

[6] ANSI/ASHRAE Addendum a to ANSI/ASHRAE Standard 140-2017 (the BESTEST update of 2020),
Informative Annex B6, Tables B6-1, B6-2 and B6-3.
https://www.ashrae.org/file%20library/technical%20resources/standards%20and%20guidelines/standards%20addenda/140_2017_a_galley_20200812.pdf

[7] ISO 13790:2008, "Energy performance of buildings - Calculation of energy use for space
heating and cooling", simple hourly method (Annex C). The standard is not free. The equations
were taken from the open-source program RC_BuildingSimulator (ETH Zurich), which quotes the
equation numbers of the standard.
https://github.com/architecture-building-systems/RC_BuildingSimulator

[8] ISO/FDIS 13790:2007 (final draft of ISO 13790), clause 12.2.2, Equations (64) and (65),
and clause 12.3.1.2, Table 12. Public copy: appendix 2 of a final-year project at the
Escuela Técnica Superior de Ingenieros, Sevilla.
https://ereding.etsi.us.es/bibing/proyectos/abreproy/80004/

[9] TABULA project, "Scientific report Greece", National Observatory of Athens (NOA),
Tables 2.3, 2.4, 3.1 and 4.5.
https://episcope.eu/fileadmin/tabula/public/docs/scientific/GR_TABULA_ScientificReport_NOA.pdf

[10] Technical Chamber of Greece (TEE), T.O.T.E.E. 20701-1/2017, "Detailed national
specifications of parameters for the calculation of the energy performance of buildings and
the issue of the energy performance certificate" (in Greek), 1st edition, 2017.
Table 3.8 (U of glass), Equation 3.9 and Table 3.17 (g of glass), Table 3.15 (solar
absorptance of plaster colours). Copy used: university course page,
https://eclass.hmu.gr/modules/document/file.php/TH200/TOTEE_20701-1_2017_TEE_1st_Edition.pdf
