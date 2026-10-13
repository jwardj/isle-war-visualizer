"""Registry of playable maps.

Procedural maps are built entirely in memory from a list of island sizes:
territories are scattered to FILL each island (a sunflower/phyllotaxis pattern
inside a tilted oblong), roads are derived from those positions (a proximity
graph), and sea-bridges link nearby islands. The same graph is written to a
world.dlv so the DLV agents see exactly what the engine does. Classic Isles
keeps its hand-authored layout. Everything is deterministic, so a map looks the
same every launch.
"""
import json
import math
import os
import random

from worldmap import load_world, WorldMap
import layout as classic26_layout

HERE = os.path.dirname(os.path.abspath(__file__))

GOLDEN = math.pi * (3 - math.sqrt(5))   # golden angle, for even sunflower fill

# island land colours (warm sand / soft greens, easy on the eye)
PALETTE = [
    (217, 199, 153), (176, 202, 156), (164, 198, 165), (206, 195, 152),
    (213, 191, 152), (192, 208, 223), (224, 176, 138), (199, 185, 216),
]

# Classic Isles keeps its hand layout but gets nicer names.
CLASSIC26_BONUS = {1: 2, 2: 3, 3: 3, 4: 5, 5: 2}
CLASSIC26_LABELS = {1: "Highmere", 2: "Westmarch", 3: "Aldershore",
                    4: "Kingspire", 5: "Saltcliff"}

# K-Town Small: the upstream StudentIsleWars `default_map` (26 territories,
# 5 continents). Same island shapes as Classic Isles but WITHOUT its three extra
# Sprawl<->Sunset sea-bridges, so it reuses the classic26 hand layout. Continent
# bonuses follow the StudentIsleWars rule (<=5: max(2, size-1); else size-2).
KTOWN_SMALL_CONTINENT_OF = {
    1: 1, 2: 1, 3: 1,
    4: 3, 5: 3, 6: 3, 7: 3, 8: 3,
    9: 2, 10: 2, 11: 2, 12: 2, 13: 2,
    14: 4, 15: 4, 16: 4, 17: 4, 18: 4, 19: 4, 20: 4, 21: 4, 22: 4, 23: 4,
    24: 5, 25: 5, 26: 5,
}
KTOWN_SMALL_EDGES = [
    (1, 2), (1, 13), (2, 3), (3, 4), (4, 5), (4, 6), (4, 7), (5, 6),
    (6, 7), (6, 8), (7, 8), (7, 9), (9, 10), (9, 11), (9, 14), (10, 11),
    (10, 12), (11, 12), (11, 13), (12, 13), (13, 15), (14, 15), (14, 18),
    (14, 24), (15, 16), (15, 17), (15, 18), (16, 17), (16, 20), (17, 18),
    (17, 19), (17, 20), (18, 19), (19, 20), (19, 21), (20, 21), (20, 22),
    (21, 22), (21, 23), (22, 23), (24, 25), (24, 26), (25, 26),
]
KTOWN_SMALL_BONUS = {1: 2, 2: 4, 3: 4, 4: 8, 5: 2}
KTOWN_SMALL_LABELS = {1: "Kingsport", 2: "Kettlebrook", 3: "Kraken Bay",
                      4: "Kingspire", 5: "Kelp Cove"}

# K-Town Large: the upstream StudentIsleWars `full_map` (48 territories, 9
# continents), built from its fixed adjacency and drawn with the procedural
# auto-layout (no hand layout exists for it). Bonuses use the same rule.
KTOWN_LARGE_CONTINENT_OF = {
    0: 1, 1: 1, 2: 1, 3: 1,
    9: 2, 10: 2, 11: 2, 12: 2, 13: 2,
    4: 3, 5: 3, 6: 3, 7: 3, 8: 3,
    14: 4, 15: 4, 16: 4, 17: 4, 18: 4, 19: 4, 20: 4, 21: 4, 22: 4, 23: 4,
    24: 5, 25: 5, 26: 5, 27: 5,
    28: 6, 29: 6, 30: 6, 31: 6, 32: 6, 33: 6, 34: 6,
    35: 7, 36: 7, 37: 7,
    38: 8, 39: 8, 40: 8, 41: 8, 42: 8, 43: 8, 44: 8,
    45: 9, 46: 9, 47: 9,
}
KTOWN_LARGE_EDGES = [
    (0, 1), (0, 13), (1, 2), (2, 3), (3, 4), (4, 5), (4, 6), (4, 7),
    (5, 6), (6, 7), (6, 8), (7, 8), (7, 9), (8, 28), (9, 10), (9, 11),
    (9, 14), (10, 11), (10, 12), (11, 12), (11, 13), (12, 13), (13, 15), (14, 15),
    (14, 18), (14, 24), (15, 16), (15, 17), (15, 18), (16, 17), (16, 20), (17, 18),
    (17, 19), (17, 20), (18, 19), (19, 20), (19, 21), (20, 21), (20, 22), (21, 22),
    (21, 23), (22, 23), (23, 26), (23, 33), (23, 47), (24, 25), (24, 26), (25, 27),
    (25, 28), (26, 27), (28, 29), (28, 30), (29, 30), (29, 31), (29, 32), (30, 31),
    (31, 32), (31, 34), (32, 33), (32, 34), (33, 34), (33, 38), (34, 35), (35, 36),
    (36, 37), (37, 40), (38, 39), (38, 40), (38, 47), (39, 40), (39, 41), (39, 42),
    (40, 41), (41, 42), (41, 43), (41, 44), (42, 44), (43, 44), (44, 45), (45, 46),
    (45, 47), (46, 47),
]
KTOWN_LARGE_BONUS = {1: 3, 2: 4, 3: 4, 4: 8, 5: 3, 6: 5, 7: 2, 8: 5, 9: 2}
KTOWN_LARGE_LABELS = {1: "Kingsport", 2: "Kettlebrook", 3: "Kraken Bay",
                      4: "Kingspire", 5: "Kelp Cove", 6: "Karthmoor",
                      7: "Kestrel Isle", 8: "Korvale", 9: "Kaldmere"}

# Procedural maps: key -> (label, island sizes, island names). Ordered small to
# large so the start-screen toggle reads naturally.
PROC_MAPS = [
    ("trident", "Trident Coast", [6, 5, 6],
     ["Sunspire", "Blacksand", "Tidewatch"]),
    ("coral", "Coral Expanse", [5, 6, 5, 5],
     ["Coralmere", "Thornwell", "Saltreach", "Goldcoast"]),
    ("stormbreak", "Stormbreak Reach", [6, 4, 6, 5, 5],
     ["Stormcrag", "Frostmere", "Ironhold", "Emberfall", "Duskhaven"]),
    ("greater", "The Greater Reaches", [5, 5, 6, 5, 6, 5],
     ["Northreach", "Wyrmrest", "Ravenmoor", "Drakemont", "Greywater", "Mistral"]),
]

DEFAULT_SEA = ((34, 70, 112), (16, 38, 70))

# Each map gets its own land palette + sea tint so they read as different
# places, not recolours of one template.
THEMES = {
    "trident": {  # warm tropical sands, turquoise water
        "land": [(229, 211, 157), (233, 217, 169), (221, 201, 145),
                 (237, 221, 171), (215, 195, 141), (227, 207, 151)],
        "sea": ((40, 104, 134), (16, 56, 88)),
    },
    "coral": {  # lush greens & teal lagoons
        "land": [(150, 201, 159), (169, 207, 151), (140, 195, 169),
                 (177, 211, 157), (150, 197, 177), (161, 205, 151)],
        "sea": ((28, 96, 110), (12, 48, 70)),
    },
    "stormbreak": {  # cold slate isles, steel sea
        "land": [(170, 184, 198), (182, 194, 206), (158, 174, 192),
                 (192, 202, 212), (162, 178, 200), (176, 188, 202)],
        "sea": ((40, 60, 92), (12, 28, 52)),
    },
    "greater": {  # rich earthy continents, deep ocean
        "land": [(208, 178, 130), (192, 180, 122), (178, 162, 112),
                 (212, 186, 142), (200, 168, 118), (186, 174, 120)],
        "sea": ((32, 66, 106), (14, 34, 64)),
    },
}


def _dist(coords, a, b):
    return math.hypot(coords[a][0] - coords[b][0], coords[a][1] - coords[b][1])


def _mst_knn(items, dist, k):
    """Edges of a minimum spanning tree over `items` plus each item's k nearest
    neighbours -- a connected, natural-looking network with no long crossings.
    `items` are hashable & sortable (ints here). Returns a set of sorted pairs."""
    edges = set()
    items = list(items)
    if len(items) >= 2:
        inside = {items[0]}
        while len(inside) < len(items):
            best, bd = None, float("inf")
            for a in inside:
                for b in items:
                    if b in inside:
                        continue
                    d = dist(a, b)
                    if d < bd:
                        bd, best = d, (a, b)
            edges.add(tuple(sorted(best)))
            inside.add(best[1])
    for a in items:
        nb = sorted((b for b in items if b != a), key=lambda b: dist(a, b))
        for b in nb[:k]:
            edges.add(tuple(sorted((a, b))))
    return edges


def auto_layout(world, board_w=1280, board_h=860, seed_base=0):
    """Scatter each island's territories to FILL a tilted oblong (sunflower
    pattern) and push a few out into jagged peninsulas with a territory at the
    tip, so islands read as solid, irregular landmasses. Islands are packed to
    use the board (zoomed in) yet kept clear of each other. `seed_base` makes
    each map's island shapes unique. Returns the coordinates; colours/labels
    are set by the caller."""
    continents = sorted(world.continents.keys())
    nC = len(continents)
    margin_x, margin_y = 84, 64

    # pick the rows x cols grid that makes the cells (and so the islands) largest
    best = None
    for rows in range(1, nC + 1):
        cols = math.ceil(nC / rows)
        s = min((board_w - 2 * margin_x) / cols, (board_h - 2 * margin_y) / rows)
        if best is None or s > best[0]:
            best = (s, cols, rows)
    span, cols, rows = best
    cell_w = (board_w - 2 * margin_x) / cols
    cell_h = (board_h - 2 * margin_y) / rows
    used_rows = math.ceil(nC / cols)

    coords = {}
    for i, c in enumerate(continents):
        gc, gr = i % cols, i // cols
        # centre a short final row so the map isn't lopsided
        in_row = min(cols, nC - gr * cols)
        row_off = (cols - in_row) / 2.0 if gr == used_rows - 1 else 0.0
        rng = random.Random(c * 9173 + 41 + seed_base)
        ccx = margin_x + cell_w * (gc + row_off + 0.5) + rng.uniform(-1, 1) * cell_w * 0.05
        ccy = margin_y + cell_h * (gr + 0.5) + rng.uniform(-1, 1) * cell_h * 0.05
        ts = world.continents[c]
        n = len(ts)

        stretch = rng.uniform(1.16, 1.5)                # oblong
        radius = min(span * (0.18 + 0.013 * n), span * 0.26)
        orient = rng.uniform(0, math.pi)                # random tilt
        co, so = math.cos(orient), math.sin(orient)

        def place(t, lx, ly):
            coords[t] = (ccx + lx * co - ly * so, ccy + lx * so + ly * co)

        # most islands sprout 1-3 jagged tips; some fling a territory far out
        # on its own for a really ragged, varied coastline.
        spur = n >= 4 and rng.random() < 0.85
        tips = 0
        if spur:
            tips = 1 + (rng.random() < 0.5) + (n >= 8 and rng.random() < 0.4)
        n_main = n - tips

        for j in range(n_main):
            rr = radius * math.sqrt((j + 0.5) / max(1, n_main)) * rng.uniform(0.9, 1.13)
            a = j * GOLDEN + rng.uniform(-0.16, 0.16)
            place(ts[j], rr * stretch * math.cos(a), rr * math.sin(a))
        for k in range(tips):
            ta = rng.uniform(0, 2 * math.pi)
            if rng.random() < 0.4:
                td = radius * rng.uniform(1.9, 2.5)     # super spike / lone islet
            else:
                td = radius * rng.uniform(1.3, 1.7)     # ordinary peninsula
            place(ts[n_main + k], td * math.cos(ta), td * math.sin(ta))

    for c in continents:
        _space_territories(coords, world.continents[c], min_sep=36)
    _separate_islands(world, coords, board_w, board_h)
    return coords


def _space_territories(coords, ts, min_sep, iters=80):
    """Push any two territories on the same island that landed too close apart,
    so the renderer (radius = 0.46 * nearest-neighbour) never draws overlapping
    territories. Spurs sit far out, so this only nudges clustered inland ones."""
    for _ in range(iters):
        moved = False
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                a, b = ts[i], ts[j]
                dx, dy = coords[b][0] - coords[a][0], coords[b][1] - coords[a][1]
                d = math.hypot(dx, dy) or 0.01
                if d < min_sep:
                    push = (min_sep - d) / 2 + 0.4
                    ux, uy = dx / d, dy / d
                    coords[a] = (coords[a][0] - ux * push, coords[a][1] - uy * push)
                    coords[b] = (coords[b][0] + ux * push, coords[b][1] + uy * push)
                    moved = True
        if not moved:
            break


def _separate_islands(world, coords, board_w, board_h, gap=14, pad=56):
    """Push whole islands apart (rigid translation) until none overlap, keeping
    a clear `gap` of water between their coastlines. `pad` is a generous
    allowance for the drawn coastline beyond the outermost territory centre."""
    conts = sorted(world.continents)
    ts = {c: world.continents[c] for c in conts}

    def centroid(c):
        xs = [coords[t][0] for t in ts[c]]
        ys = [coords[t][1] for t in ts[c]]
        return [sum(xs) / len(xs), sum(ys) / len(ys)]

    cen = {c: centroid(c) for c in conts}
    brad = {c: max(math.hypot(coords[t][0] - cen[c][0], coords[t][1] - cen[c][1])
                   for t in ts[c]) + pad for c in conts}

    for _ in range(200):
        disp = {c: [0.0, 0.0] for c in conts}
        worst = 0.0
        for ii in range(len(conts)):
            for jj in range(ii + 1, len(conts)):
                a, b = conts[ii], conts[jj]
                dx, dy = cen[b][0] - cen[a][0], cen[b][1] - cen[a][1]
                d = math.hypot(dx, dy) or 0.01
                need = brad[a] + brad[b] + gap
                if d < need:
                    worst = max(worst, need - d)
                    ux, uy, push = dx / d, dy / d, (need - d) / 2 + 0.5
                    disp[a][0] -= ux * push; disp[a][1] -= uy * push
                    disp[b][0] += ux * push; disp[b][1] += uy * push
        if worst < 0.5:
            break
        for c in conts:
            nx = min(max(cen[c][0] + disp[c][0], brad[c]), board_w - brad[c])
            ny = min(max(cen[c][1] + disp[c][1], brad[c]), board_h - brad[c])
            ddx, ddy = nx - cen[c][0], ny - cen[c][1]
            cen[c] = [nx, ny]
            for t in ts[c]:
                coords[t] = (coords[t][0] + ddx, coords[t][1] + ddy)


def _island_roads(world, coords):
    edges = set()
    for ts in world.continents.values():
        edges |= _mst_knn(ts, lambda a, b: _dist(coords, a, b), k=2)
    return edges


def _sea_bridges(world, coords):
    """Sea-bridges between islands: MST over island centroids + each island's
    THREE nearest neighbours, every link joining the closest coastal pair, so
    there are lots of contested crossings but none cut across a third island."""
    conts = sorted(world.continents.keys())
    ts = {c: world.continents[c] for c in conts}
    cen = {c: (sum(coords[t][0] for t in ts[c]) / len(ts[c]),
               sum(coords[t][1] for t in ts[c]) / len(ts[c])) for c in conts}

    def cdist(a, b):
        return math.hypot(cen[a][0] - cen[b][0], cen[a][1] - cen[b][1])

    island_edges = _mst_knn(conts, cdist, k=3)
    bridges = set()
    for a, b in island_edges:
        best, bd = None, float("inf")
        for x in ts[a]:
            for y in ts[b]:
                d = _dist(coords, x, y)
                if d < bd:
                    bd, best = d, (x, y)
        if best:
            bridges.add(best)
    return bridges


def _write_world(key, world):
    """Write the whole graph to maps/<key>/world.dlv for the DLV agents."""
    d = os.path.join(HERE, "maps", key)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "world.dlv")
    lines = [f"territory({t})." for t in world.territories]
    lines += [f"in_continent({t},{world.continent_of[t]})." for t in world.territories]
    for a, b in world.neighbor_pairs():
        lines.append(f"neighbor({a},{b}).")
        lines.append(f"neighbor({b},{a}).")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def _proc(key, label, sizes, names):
    continent_of, tid = {}, 0
    for ci, sz in enumerate(sizes):
        for _ in range(sz):
            continent_of[tid] = ci + 1
            tid += 1
    territories = list(range(tid))
    world = WorldMap(territories, {t: set() for t in territories}, continent_of)
    world.continent_bonus = {c: max(2, len(ts) - 2)
                             for c, ts in world.continents.items()}

    theme = THEMES.get(key, {})
    land_pal = theme.get("land", PALETTE)
    sea_top, sea_bot = theme.get("sea", DEFAULT_SEA)
    seed_base = sum(ord(ch) for ch in key) * 131       # unique island shapes

    board_w, board_h = 1280, 860
    coords = auto_layout(world, board_w, board_h, seed_base)
    for a, b in _island_roads(world, coords) | _sea_bridges(world, coords):
        world.neighbors[a].add(b)
        world.neighbors[b].add(a)
    world.path = _write_world(key, world)

    conts = sorted(world.continents)
    return {
        "label": label,
        "world": world,
        "coords": coords,
        "board_w": board_w,
        "board_h": board_h,
        "continent_land": {c: land_pal[(c - 1) % len(land_pal)] for c in conts},
        "continent_label": {c: names[(c - 1) % len(names)] for c in conts},
        "sea_top": sea_top,
        "sea_bot": sea_bot,
        "regular": False,
    }


# Every map is a SUBSET of the authentic 48-territory Isle Wars board: we keep
# the territories a map needs and delete the rest, reusing the real shapes,
# positions and adjacency from the original art (maps/ktown_large/shapes.json +
# the full-board KTOWN_LARGE_* tables). Each map is themed as a different Fortnite
# season, so its islands get that season's POI names (see _MAP_SPECS) -- every
# island name is unique across all maps.
_FULL_SHAPES = None


def _full_shapes():
    global _FULL_SHAPES
    if _FULL_SHAPES is None:
        with open(os.path.join(HERE, "maps", "ktown_large", "shapes.json"),
                  encoding="utf-8") as f:
            _FULL_SHAPES = json.load(f)
    return _FULL_SHAPES


def _islands(*continent_ids):
    """All full-board territory ids that live on the given real islands."""
    cs = set(continent_ids)
    return {t for t, c in KTOWN_LARGE_CONTINENT_OF.items() if c in cs}


def _spread_islands(coords, polys, continent_of, w, h, factor=1.3, margin=40):
    """Move each island outward from the board centre by `factor` (its shape is
    unchanged) so more open water sits between continents, then re-fit everything
    into a fresh board box. Returns (coords, polys, board_w, board_h)."""
    cx = sum(p[0] for p in coords.values()) / len(coords)
    cy = sum(p[1] for p in coords.values()) / len(coords)
    isl = {}
    for c in set(continent_of.values()):
        ts = [t for t in coords if continent_of[t] == c]
        isl[c] = (sum(coords[t][0] for t in ts) / len(ts),
                  sum(coords[t][1] for t in ts) / len(ts))
    off = {c: ((isl[c][0] - cx) * (factor - 1.0),
               (isl[c][1] - cy) * (factor - 1.0)) for c in isl}

    nc, npoly = {}, {}
    for t in coords:
        ox, oy = off[continent_of[t]]
        nc[t] = (coords[t][0] + ox, coords[t][1] + oy)
        npoly[t] = [(x + ox, y + oy) for x, y in polys[t]]

    xs = [x for p in npoly.values() for x, _ in p]
    ys = [y for p in npoly.values() for _, y in p]
    minx, miny = min(xs) - margin, min(ys) - margin
    nc = {t: (x - minx, y - miny) for t, (x, y) in nc.items()}
    npoly = {t: [(x - minx, y - miny) for x, y in p] for t, p in npoly.items()}
    return nc, npoly, max(xs) - minx + margin, max(ys) - miny + margin


def _seg_dist(p, a, b):
    """Distance from point p to segment a-b, and the closest point on it."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    ll = dx * dx + dy * dy
    if ll < 1e-9:
        return math.hypot(p[0] - ax, p[1] - ay), a
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / ll))
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(p[0] - qx, p[1] - qy), (qx, qy)


def _declutter_islands(coords, polys, continent_of, neighbors, margin=40,
                       clear=34.0, gap=34.0, iters=900):
    """Slide whole islands around (rigid translations) so that NO sea-bridge ever
    crosses another island's land, and no two islands overlap. Each cross-island
    bridge is a segment between its two coastal territories; any OTHER island that
    the segment runs too close to is pushed perpendicularly off it (the user's
    'move the island up' fix, automated). Returns (coords, polys, board_w, board_h)."""
    isl = {}
    for t in coords:
        isl.setdefault(continent_of[t], []).append(t)
    ids = sorted(isl)
    off = {c: [0.0, 0.0] for c in ids}

    def cen(c):
        ts = isl[c]
        return (sum(coords[t][0] + off[c][0] for t in ts) / len(ts),
                sum(coords[t][1] + off[c][1] for t in ts) / len(ts))

    # bounding radius of each island (from its real outlines)
    rad = {}
    for c in ids:
        cx, cy = cen(c)
        rad[c] = max(math.hypot(px - cx, py - cy)
                     for t in isl[c] for px, py in polys[t])

    bridges = set()
    for a in coords:
        for b in neighbors[a]:
            if continent_of[a] != continent_of[b]:
                bridges.add((min(a, b), max(a, b)))
    bridges = list(bridges)

    for _ in range(iters):
        disp = {c: [0.0, 0.0] for c in ids}
        cc = {c: cen(c) for c in ids}
        moved = False
        # keep islands from overlapping
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                ci, cj = ids[i], ids[j]
                dx, dy = cc[cj][0] - cc[ci][0], cc[cj][1] - cc[ci][1]
                d = math.hypot(dx, dy) or 0.01
                need = rad[ci] + rad[cj] + gap
                if d < need:
                    push = (need - d) / 2.0
                    ux, uy = dx / d, dy / d
                    disp[ci][0] -= ux * push; disp[ci][1] -= uy * push
                    disp[cj][0] += ux * push; disp[cj][1] += uy * push
                    moved = True
        # push islands off any bridge they sit on
        for a, b in bridges:
            ia, ib = continent_of[a], continent_of[b]
            pa = (coords[a][0] + off[ia][0], coords[a][1] + off[ia][1])
            pb = (coords[b][0] + off[ib][0], coords[b][1] + off[ib][1])
            for c in ids:
                if c == ia or c == ib:
                    continue
                # nearest of this island's territories to the bridge segment
                best_d, best_q, best_p = 1e9, None, None
                for t in isl[c]:
                    pt = (coords[t][0] + off[c][0], coords[t][1] + off[c][1])
                    d, q = _seg_dist(pt, pa, pb)
                    if d < best_d:
                        best_d, best_q, best_p = d, q, pt
                need = clear + 28.0
                if best_d < need:
                    dx, dy = best_p[0] - best_q[0], best_p[1] - best_q[1]
                    dd = math.hypot(dx, dy) or 0.01
                    ux, uy = dx / dd, dy / dd
                    push = need - best_d
                    # push the crossed island off the bridge, and swing the
                    # bridge's own two islands the OTHER way, so the gap opens
                    # from both sides (handles an island wedged between two others).
                    disp[c][0] += ux * push; disp[c][1] += uy * push
                    disp[ia][0] -= ux * push * 0.9; disp[ia][1] -= uy * push * 0.9
                    disp[ib][0] -= ux * push * 0.9; disp[ib][1] -= uy * push * 0.9
                    moved = True
        for c in ids:
            off[c][0] += disp[c][0] * 0.5
            off[c][1] += disp[c][1] * 0.5
        if not moved:
            break

    nc, npoly = {}, {}
    for t in coords:
        ox, oy = off[continent_of[t]]
        nc[t] = (coords[t][0] + ox, coords[t][1] + oy)
        npoly[t] = [(x + ox, y + oy) for x, y in polys[t]]
    xs = [x for p in npoly.values() for x, _ in p]
    ys = [y for p in npoly.values() for _, y in p]
    minx, miny = min(xs) - margin, min(ys) - margin
    nc = {t: (x - minx, y - miny) for t, (x, y) in nc.items()}
    npoly = {t: [(x - minx, y - miny) for x, y in p] for t, p in npoly.items()}
    return nc, npoly, max(xs) - minx + margin, max(ys) - miny + margin


def _ensure_connections(keep, continent_of, neighbors, centroids, target_fn=None,
                        forbid=()):
    """Add sea-bridges so no island is left with fewer than its size-based
    minimum of DISTINCT island connections (>=2, and more for bigger islands),
    capped at the number of other islands. Each new bridge joins the closest
    coastal territory pair to the nearest island not already connected, so the
    links stay short and over open water. `forbid` is a set of frozenset island
    pairs that must never be bridged. Mutates `neighbors` in place."""
    islands = {}
    for t in keep:
        islands.setdefault(continent_of[t], []).append(t)
    ids = sorted(islands)
    n = len(ids)
    cen = {c: (sum(centroids[t][0] for t in islands[c]) / len(islands[c]),
               sum(centroids[t][1] for t in islands[c]) / len(islands[c]))
           for c in ids}
    rad = {c: max(math.hypot(centroids[t][0] - cen[c][0],
                             centroids[t][1] - cen[c][1]) for t in islands[c]) + 46
           for c in ids}
    conn = {c: set() for c in ids}
    for a in keep:
        for b in neighbors[a]:
            if continent_of[a] != continent_of[b]:
                conn[continent_of[a]].add(continent_of[b])

    def target(c):
        s = len(islands[c])
        base = target_fn(s) if target_fn else (2 if s <= 5 else 3 if s <= 9 else 4)
        return min(n - 1, base)

    def d2(p, q):
        return (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2

    def crosses(c, o):  # would a c<->o bridge pass over a third island?
        for k in ids:
            if k == c or k == o:
                continue
            if _seg_dist(cen[k], cen[c], cen[o])[0] < rad[k]:
                return True
        return False

    def routes(c):  # number of sea-bridge ENDS on island c
        return sum(1 for t in islands[c] for u in neighbors[t]
                   if continent_of[u] != c)

    def ok(c, o):  # is a c<->o bridge allowed?
        return frozenset((c, o)) not in forbid

    def add_bridge(c, o):  # join the closest not-yet-bridged coastal pair
        if not ok(c, o):
            return False
        pairs = [(x, y) for x in islands[c] for y in islands[o] if y not in neighbors[x]]
        if not pairs:
            return False
        a, b = min(pairs, key=lambda pr: d2(centroids[pr[0]], centroids[pr[1]]))
        neighbors[a].add(b)
        neighbors[b].add(a)
        conn[c].add(o)
        conn[o].add(c)
        return True

    # Pass 1: give each island its size-based number of DISTINCT connections.
    # Prefer a bridge that doesn't cross a third island, but allow a crossing one
    # if that's the only way to reach a new island -- the later declutter step
    # moves islands so it no longer crosses, and `_repair_crossings` turns any
    # genuinely-unfixable crossing into a clean parallel bridge.
    progress = True
    while progress:
        progress = False
        for c in ids:
            if len(conn[c]) >= target(c):
                continue
            # connect only to islands that ALSO still want a connection (and via
            # a non-crossing bridge), so no island gets over-connected past its
            # target. If none qualify, leave it -- pass 2 / connectivity fix up.
            want = [o for o in ids if o != c and o not in conn[c]
                    and len(conn[o]) < target(o) and not crosses(c, o) and ok(c, o)]
            if not want:
                continue
            o = min(want, key=lambda x: d2(cen[c], cen[x]))
            if add_bridge(c, o):
                progress = True

    # keep the island graph connected (join components with the nearest bridge,
    # preferring clean ones)
    while True:
        seen, root = set(), {}
        for c in ids:
            if c in seen:
                continue
            stack = [c]
            while stack:
                x = stack.pop()
                if x in seen:
                    continue
                seen.add(x); root[x] = c
                stack.extend(conn[x] - seen)
        if len(set(root.values())) <= 1:
            break
        best = None
        for c in ids:
            for o in ids:
                if root[c] == root[o] or not ok(c, o):
                    continue
                pen = 1e12 if crosses(c, o) else 0   # avoid crossing when possible
                d = d2(cen[c], cen[o]) + pen
                if best is None or d < best[0]:
                    best = (d, c, o)
        if best is None or not add_bridge(best[1], best[2]):
            break

    # Pass 2: no island may have only one sea ROUTE. Prefer a clean new bridge,
    # else a clean parallel one to the nearest island.
    progress = True
    while progress:
        progress = False
        for c in ids:
            if routes(c) >= 2:
                continue
            opts = []
            for o in ids:
                if o == c or crosses(c, o) or not ok(c, o):
                    continue
                pairs = [(x, y) for x in islands[c] for y in islands[o]
                         if y not in neighbors[x]]
                if pairs:
                    a, b = min(pairs, key=lambda pr: d2(centroids[pr[0]], centroids[pr[1]]))
                    opts.append((d2(centroids[a], centroids[b]), o))
            if not opts:
                continue
            if add_bridge(c, min(opts)[1]):
                progress = True


def _repair_crossings(neighbors, continent_of, coords, polys, protected=(),
                      forbid=()):
    """Run AFTER the islands are positioned. Any sea-bridge that still passes
    over a third island's land (the declutter couldn't separate them) is removed
    and replaced with the nearest CLEAN bridge, so every island keeps >=2 sea
    routes and nothing crosses land. `protected` edges (forced links) are never
    removed; `forbid` island pairs are never created. Uses final positions."""
    isl = {}
    for t in coords:
        isl.setdefault(continent_of[t], []).append(t)
    ids = sorted(isl)
    rad_t = {}
    for t in coords:
        cx = sum(p[0] for p in polys[t]) / len(polys[t])
        cy = sum(p[1] for p in polys[t]) / len(polys[t])
        rad_t[t] = max(math.hypot(px - cx, py - cy) for px, py in polys[t])

    def crosses(a, b):
        ia, ib = continent_of[a], continent_of[b]
        for c in ids:
            if c == ia or c == ib:
                continue
            for t in isl[c]:
                if _seg_dist(coords[t], coords[a], coords[b])[0] < rad_t[t] * 0.92:
                    return True
        return False

    def routes(c):
        return sum(1 for t in isl[c] for u in neighbors[t] if continent_of[u] != c)

    def add_clean(c):
        best = None
        for o in ids:
            if o == c or frozenset((c, o)) in forbid:
                continue
            for x in isl[c]:
                for y in isl[o]:
                    if y in neighbors[x] or crosses(x, y):
                        continue
                    d = math.hypot(coords[x][0] - coords[y][0], coords[x][1] - coords[y][1])
                    if best is None or d < best[0]:
                        best = (d, x, y)
        if best:
            neighbors[best[1]].add(best[2])
            neighbors[best[2]].add(best[1])
            return True
        return False

    for _ in range(12):
        changed = False
        seen = set()
        for a in list(coords):
            for b in list(neighbors[a]):
                if continent_of[a] == continent_of[b] or (b, a) in seen:
                    continue
                seen.add((a, b))
                if (min(a, b), max(a, b)) in protected:
                    continue
                if crosses(a, b):
                    neighbors[a].discard(b)
                    neighbors[b].discard(a)
                    changed = True
        for c in ids:
            tries = 0
            while routes(c) < 2 and tries < 6:
                tries += 1
                if not add_clean(c):
                    break
        if not changed:
            break


def _subset_map(key, label, keep_ids, names, edges=None, spread=1.18,
                conn_target=None, minimal_bridges=False, force_links=None,
                forbid_links=None):
    """Build a map from a subset of the real Isle Wars board: keep `keep_ids`
    (delete the rest), reuse their authentic shapes/positions, take the real
    bridges among them (or `edges`), renumber the surviving islands 1..k, give
    them this season's POI `names`, ensure enough sea connections (`conn_target`
    overrides the size->#connections rule; `minimal_bridges` drops the source
    inter-island bridges and rebuilds the minimum from scratch; `force_links` is
    a list of (island-name, island-name) pairs always bridged; `forbid_links`
    pairs are never bridged), then slide the islands around so no sea-route ever
    crosses land. Carries `"polys"`."""
    shp = _full_shapes()
    keep = sorted(keep_ids)
    keepset = set(keep)
    used = sorted({KTOWN_LARGE_CONTINENT_OF[t] for t in keep})   # surviving islands
    remap = {orig: i + 1 for i, orig in enumerate(used)}
    continent_of = {t: remap[KTOWN_LARGE_CONTINENT_OF[t]] for t in keep}
    name_to_c = {names[c - 1]: c for c in range(1, len(used) + 1)}
    forbid = {frozenset((name_to_c[a], name_to_c[b])) for a, b in (forbid_links or [])}

    src_edges = KTOWN_LARGE_EDGES if edges is None else edges
    neighbors = {t: set() for t in keep}
    for a, b in src_edges:
        if a in keepset and b in keepset:
            ca, cb = continent_of[a], continent_of[b]
            # minimal_bridges: keep only WITHIN-island land edges; sea-bridges are
            # rebuilt to the bare minimum by _ensure_connections.
            if minimal_bridges and ca != cb:
                continue
            if ca != cb and frozenset((ca, cb)) in forbid:   # never a forbidden link
                continue
            neighbors[a].add(b)
            neighbors[b].add(a)

    coords = {t: tuple(shp["centroids"][str(t)]) for t in keep}
    polys = {t: [tuple(p) for p in shp["polys"][str(t)]] for t in keep}

    # explicit, always-kept bridges between named islands (closest coastal pair)
    protected = set()
    if force_links:
        isl_terr = {}
        for t in keep:
            isl_terr.setdefault(continent_of[t], []).append(t)
        for na, nb in force_links:
            ca, cb = name_to_c[na], name_to_c[nb]
            a, b = min(((x, y) for x in isl_terr[ca] for y in isl_terr[cb]),
                       key=lambda pr: (coords[pr[0]][0] - coords[pr[1]][0]) ** 2
                       + (coords[pr[0]][1] - coords[pr[1]][1]) ** 2)
            neighbors[a].add(b)
            neighbors[b].add(a)
            protected.add((min(a, b), max(a, b)))

    # make sure every island has enough sea connections (>=2, more if big)
    _ensure_connections(keep, continent_of, neighbors, coords, conn_target, forbid)

    sizes = {}
    for c in continent_of.values():
        sizes[c] = sizes.get(c, 0) + 1
    bonus = {c: (max(2, s - 1) if s <= 5 else s - 2) for c, s in sizes.items()}

    world = WorldMap(keep, neighbors, continent_of, continent_bonus=bonus)

    # spread islands into open water, then slide them so no bridge crosses land,
    # then repair any bridge that still crosses into a clean one
    coords, polys, _bw, _bh = _spread_islands(coords, polys, continent_of,
                                              shp["w"], shp["h"], factor=spread)
    coords, polys, bw, bh = _declutter_islands(coords, polys, continent_of,
                                               neighbors)
    _repair_crossings(neighbors, continent_of, coords, polys, protected, forbid)
    world.path = _write_world(key, world)   # write AFTER the final adjacency
    conts = sorted(world.continents)
    return {
        "label": label,
        "world": world,
        "coords": coords,
        "polys": polys,
        "board_w": bw,
        "board_h": bh,
        "continent_land": {c: PALETTE[(used[c - 1] - 1) % len(PALETTE)] for c in conts},
        "continent_label": {c: names[c - 1] for c in conts},
        "regular": False,
    }


# Each map is themed differently and its islands get unique POI names (no name
# repeats across any map). ktown_large is the original full board, labelled
# "Isle Wars Default" with the Chapter-1-Season-1 POIs. Each spec is a dict;
# `opts` carries optional kwargs for _subset_map. Ordered small -> large.
_MAP_SPECS = [
    dict(key="trident", label="Chapter 3: Season 1", keep=_islands(7, 8, 9),
         names=["Sleepy Sound", "Camp Cuddle", "Coney Crossroads"],
         opts=dict(spread=1.22)),
    dict(key="coral", label="Chapter 2: Season 1", keep=_islands(1, 2, 3, 6),
         names=["Sweaty Sands", "Misty Meadows", "Slurpy Swamp", "Holly Hedges"],
         opts=dict(spread=1.20,
                   force_links=[("Holly Hedges", "Misty Meadows"),
                                ("Slurpy Swamp", "Holly Hedges")])),
    dict(key="stormbreak", label="Chapter 1: Season 7", keep=_islands(2, 3, 5, 6, 7),
         names=["Frosty Flights", "Polar Peak", "Happy Hamlet",
                "Expedition Outpost", "Lonely Lodge"],
         opts=dict(spread=1.18,
                   force_links=[("Frosty Flights", "Happy Hamlet")])),
    # K-Town Small (default_map): drop the dense default bridges and rebuild just
    # the minimum (2 each) so it isn't over-connected.
    dict(key="ktown_small", label="Chapter 1: Season 5", keep=set(range(1, 27)),
         names=["Paradise Palms", "Lazy Links", "Lucky Landing", "Salty Springs",
                "Loot Lake"],
         opts=dict(edges=KTOWN_SMALL_EDGES, spread=1.18,
                   conn_target=(lambda s: 2), minimal_bridges=True,
                   force_links=[("Loot Lake", "Lucky Landing"),
                                ("Lazy Links", "Salty Springs"),
                                ("Loot Lake", "Lazy Links"),
                                ("Paradise Palms", "Lucky Landing"),
                                ("Paradise Palms", "Lazy Links"),
                                ("Loot Lake", "Salty Springs")])),
    dict(key="greater", label="Chapter 2: Season 2", keep=_islands(3, 4, 5, 6, 8, 9),
         names=["The Agency", "The Rig", "The Shark", "The Grotto", "The Yacht",
                "Lazy Lake"], opts=dict(spread=1.16)),
    dict(key="ktown_large", label="Isle Wars Default", keep=set(range(0, 48)),
         names=["Tilted Towers", "Pleasant Park", "Retail Row", "Greasy Grove",
                "Dusty Depot", "Tomato Town", "Wailing Woods", "Moisty Mire",
                "Fatal Fields"], opts=dict(spread=1.30)),
]


def _make_subset_builder(spec):
    return lambda: _subset_map(spec["key"], spec["label"], spec["keep"],
                               spec["names"], **spec["opts"])


_BUILDERS, MAP_LABELS, MAP_SIZE = {}, {}, {}
for _spec in _MAP_SPECS:
    _islcount = len({KTOWN_LARGE_CONTINENT_OF[t] for t in _spec["keep"]})
    MAP_SIZE[_spec["key"]] = (_islcount, len(_spec["keep"]))
    MAP_LABELS[_spec["key"]] = _spec["label"]
    _BUILDERS[_spec["key"]] = _make_subset_builder(_spec)

MAP_KEYS = list(_BUILDERS.keys())


def map_size_str(key):
    isles, terr = MAP_SIZE[key]
    cat = ("Small" if terr <= 18 else "Medium" if terr <= 23 else
           "Large" if terr <= 29 else "Huge")
    return f"{isles} islands, {terr} territories  ({cat})"


def build_map(key):
    """Fresh mapdef dict (new WorldMap + geometry) for the given map key."""
    return _BUILDERS[key]()
