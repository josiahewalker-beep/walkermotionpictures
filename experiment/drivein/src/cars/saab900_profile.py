"""Side-view and plan geometry of the classic Saab 900 three-door (1987 facelift, SPG/Aero kit), drawn as exact curves
for car90.py. No photos were available (image hosts blocked), so these are drawn from published dimensions plus the
car's known side-view geometry; every number below is in the model frame (s forward, z up, metres, origin at the
footprint centre).

Published (1987 three-door / "coupe", US-bumper/SPG length): L 4740, W 1690, H 1420 (SPG lowered: ~1400-1415),
wheelbase 2517, track 1430 / 1440, ground clearance 135 mm, 15" wheels (SPG 195/60 R15).
Sources: carsguide.com.au 1987 Saab 900 dimensions; cars-data.com 900 hatchback specs; en.wikipedia.org/wiki/Saab_900.

Proportions (known side view of the car, not traced from a photo): long front overhang (~1.05 m: the 900 grew a
longer nose than the 99), long rear overhang (~1.17 m, fastback hatch over a deep tail), A-pillar base pinched far back
behind the front wheel with the deeply curved screen bulging forward at its lower corners (so the pillar reads steep in
side view while the screen centre is raked), tall glasshouse (belt ~0.87, roof ~1.41), thin body-colour B-pillar, small
rear quarter light ending in a broad C-pillar, long hatch glass, short deck with the SPG lip spoiler, upright tail.
"""
import numpy as np

L2 = 2.37                                  # half length (4.74 m)
WB = 2.517
OVF = 1.05
S_FA = L2 - OVF                            # 1.32
S_RA = S_FA - WB                           # -1.197
RT = 0.3075                                # 195/60 R15
BELT = 0.870
ROOF = 1.412

# --- windscreen (deeply curved): centre line and plan wrap that varies with height ---------------------------------
WS_C0 = (0.760, 0.860)                     # centre, at the cowl
WS_C1 = (0.300, 1.370)                     # centre, at the header
WS_WRAP = ((0.860, 0.290), (1.370, 0.110)) # (z, setback of the glass edge at |x| = 0.75) -> pillar ~30 deg from vertical

# --- hatch glass -----------------------------------------------------------------------------------------------------
BL_LINE = ((-2.02, 1.02), (-0.96, 1.42))
BL_WRAP = 0.08

# --- body curves -----------------------------------------------------------------------------------------------------
W = [(L2, 0.66), (2.32, 0.78), (2.20, 0.830), (1.90, 0.845), (0.0, 0.845), (-1.80, 0.845), (-2.20, 0.830), (-2.33, 0.790),
     (-L2, 0.72)]
# bonnet: slopes from the cowl (~0.86) down to the front edge sitting on the lamp band (~0.69)
ZTOP = [(L2, 0.62), (2.33, 0.665), (2.27, 0.695), (2.10, 0.722), (1.60, 0.772), (1.00, 0.822), (0.75, 0.845),
        (0.40, 0.860), (0.0, 0.866), (-1.0, 0.880), (-1.80, 0.925), (-2.10, 0.965), (-2.28, 0.970), (-L2, 0.955)]
ZBOT = [(L2, 0.205), (2.31, 0.150), (2.00, 0.145), (1.60, 0.170), (0.90, 0.190), (-0.80, 0.190), (-1.60, 0.200),
        (-2.20, 0.205), (-L2, 0.245)]
# nose profile, z -> s: SPG air dam (lip at 0.15), sloped 1987 bumper (0.40-0.56), slim slanted lamp/grille band
# (0.565-0.685, leaning back ~20 deg), bonnet edge curling down onto it
LF = [(0.13, 2.20), (0.16, 2.29), (0.22, 2.312), (0.33, 2.322), (0.40, 2.345), (0.47, 2.370), (0.53, 2.366),
      (0.556, 2.330), (0.572, 2.300), (0.685, 2.258), (0.705, 2.225), (0.74, 2.10), (0.78, 1.90)]
# tail profile, z -> s: valance, bumper, upright tail panel, deck edge
LR = [(0.17, -2.18), (0.24, -2.29), (0.33, -2.325), (0.40, -2.350), (0.47, -2.370), (0.55, -2.362), (0.58, -2.330),
      (0.62, -2.305), (0.85, -2.288), (0.95, -2.272), (1.00, -2.215), (1.04, -2.05), (1.08, -1.90)]
ZROOF = [(0.75, 0.98), (0.48, 1.25), (0.32, 1.355), (0.16, 1.395), (0.0, 1.408), (-0.60, ROOF), (-0.95, 1.402),
         (-1.20, 1.340), (-1.60, 1.210), (-2.00, 1.060), (-2.30, 0.980)]
WG = [(1.0, 0.66), (0.6, 0.73), (0.3, 0.750), (-0.8, 0.750), (-1.5, 0.740), (-2.0, 0.700), (-2.3, 0.620)]

# --- side glass (DLO) and door, (s, z) polygons -----------------------------------------------------------------------
DLO_TOP = 1.332
B_FRONT, B_REAR = -0.490, -0.555           # thin body-colour B-pillar between the door glass and the quarter light
QUARTER = [(B_REAR, BELT + 0.03), (B_REAR, DLO_TOP), (-0.97, DLO_TOP - 0.008), (-1.39, BELT + 0.03)]
DOOR_FRONT = 0.600                         # door shut line below the belt (the long front wing behind the arch)
DOOR_REAR = -0.522
SILL = 0.360                               # door bottom, just above the skirt line
SKIRT_Z = 0.345                            # SPG skirt: sculpted line along its top edge

# --- black bumpers + rubbing strip ---------------------------------------------------------------------------------
BUMP = (0.400, 0.560)
STRIP = (0.490, 0.025)                     # door rubbing strip centre, half height
