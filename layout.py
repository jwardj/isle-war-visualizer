"""Authored screen positions for the 26-territory map.

world.dlv has no coordinates, so we place each territory by hand. Positions
are chosen so that *within-continent* neighbours sit next to each other and
the cross-continent links (1-13, 3-4, 7-9, 9-14, 14-24) are short, clean
spans between island clusters -- the graph draws with very few crossings.

Coordinates live in a native board space of BOARD_W x BOARD_H pixels.
"""

BOARD_W = 1000
BOARD_H = 760

# territory id -> (x, y) in board space
COORDS = {
    # Continent 1  "Northshore"  (chain 1-2-3); 1->13 (C2), 3->4 (C3)
    1:  (150, 110),
    2:  (275, 80),
    3:  (400, 120),
    # Continent 3  "Highreach"   (4 enters from C1, 7 exits to C2)
    4:  (560, 150),
    5:  (665, 90),
    6:  (705, 205),
    7:  (610, 300),
    8:  (805, 250),
    # Continent 2  "Midlands"    (strip; both ends drop to C4: 9->14, 13->15)
    13: (175, 420),
    12: (262, 402),
    11: (350, 350),
    10: (442, 408),
    9:  (522, 358),
    # Continent 4  "The Sprawl"  (the big one; 14 enters from C2, exits to C5)
    14: (548, 462),
    15: (432, 520),
    18: (562, 548),
    16: (348, 600),
    17: (468, 606),
    19: (676, 586),
    20: (560, 676),
    21: (686, 690),
    22: (455, 700),
    23: (576, 712),
    # Continent 5  "Sunset Isles" (triangle; 24 enters from C4)
    24: (822, 500),
    25: (912, 560),
    26: (822, 612),
    # Continent 6  "Frostmark"   (bottom-left; 27->13 C2, 28->16 C4)
    27: (108, 588),
    28: (198, 648),
    29: (110, 706),
    30: (214, 720),
    # Continent 7  "Emberreach"  (right; 31->8 C3, 33->24 & 26 C5)
    31: (882, 250),
    32: (964, 318),
    33: (892, 386),
}

# Per-continent land colour (the island fill) and a label.
CONTINENT_LAND = {
    1: (214, 196, 150),   # sand
    2: (172, 200, 150),   # green
    3: (160, 196, 162),   # green
    4: (203, 192, 150),   # savanna
    5: (210, 188, 150),   # sand
    6: (190, 206, 222),   # icy blue-white
    7: (222, 172, 132),   # warm ember
}
CONTINENT_LABEL = {
    1: "Northshore",
    2: "Midlands",
    3: "Highreach",
    4: "The Sprawl",
    5: "Sunset Isles",
    6: "Frostmark",
    7: "Emberreach",
}


def bounds_check(world):
    missing = [t for t in world.territories if t not in COORDS]
    if missing:
        raise ValueError(f"layout missing coords for territories: {missing}")
    return True
