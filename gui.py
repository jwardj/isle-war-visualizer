"""Pygame rendering for Isle Wars: islands, country-shaped territories,
panel, start screen, widgets.

The Renderer is given a `session` object (see main.py) and reads its public
attributes; it owns no game logic.
"""
import math
import random
import pygame

import config
import maps

WIN_W, WIN_H = 1340, 800
PANEL_W = 312
PANEL_X = WIN_W - PANEL_W

# palette
BG = (16, 22, 33)
SEA_TOP = (34, 70, 112)
SEA_BOT = (16, 38, 70)
BEACH = (236, 223, 188)
COAST = (70, 110, 150)
INK = (236, 240, 248)
SUBINK = (165, 178, 198)
PANEL_BG = (26, 31, 43)
CARD = (42, 49, 64)
LANDLINE = (90, 96, 78)
SEAROUTE = (150, 200, 235)

# log colours per action type
LOG_FORTIFY = (120, 210, 130)   # green  - reinforce / fortify
LOG_ATTACK = (245, 140, 95)     # orange - attack (choose phase)
LOG_MOVE = (120, 200, 235)      # cyan   - reposition / move
LOG_CONQUER = (245, 205, 90)    # gold   - conquer
LOG_PASS = (140, 146, 160)      # grey   - pass
LOG_WARN = (228, 96, 96)        # red    - illegal / capped


def _log_color(line):
    """Colour a log line by the action it describes (see logline formats in
    main.py): fortify, attack/battle, reposition (move), conquer, pass, error."""
    s = line.lower()
    if "fortify" in s:
        return LOG_FORTIFY
    if "passes" in s:
        return LOG_PASS
    if "illegal" in s or "cap" in s:
        return LOG_WARN
    if "repositions" in s:
        return LOG_MOVE
    if "moves" in s or "conquered" in s:   # conquer move, or the conquering hit
        return LOG_CONQUER
    if "->" in s:                          # an attack roll line
        return LOG_ATTACK
    return (200, 208, 222)


# ---- geometry helpers -------------------------------------------------
def _hull(points):
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _clip_to_nearer(poly, p, q, frac=0.5):
    """Sutherland-Hodgman clip: keep the side of `poly` on p's side of the line
    perpendicular to p->q at the point `frac` of the way from p to q. frac=0.5 is
    the true Voronoi bisector (tiles same-island territories); a smaller frac cuts
    the cell short of q, leaving open water toward a different island."""
    mx, my = p[0] + (q[0] - p[0]) * frac, p[1] + (q[1] - p[1]) * frac
    nx, ny = q[0] - p[0], q[1] - p[1]

    def side(pt):
        return (pt[0] - mx) * nx + (pt[1] - my) * ny      # <=0 -> closer to p

    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        sa, sb = side(a), side(b)
        if sa <= 0:
            out.append(a)
            if sb > 0:
                t = sa / (sa - sb)
                out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
        elif sb <= 0:
            t = sa / (sa - sb)
            out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    return out


def _expand(poly, pad):
    if len(poly) < 3:
        return poly
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    out = []
    for x, y in poly:
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy) or 1
        out.append((x + dx / d * pad, y + dy / d * pad))
    return out


def _chaikin(poly, iters=3):
    for _ in range(iters):
        if len(poly) < 3:
            break
        new = []
        n = len(poly)
        for i in range(n):
            a = poly[i]
            b = poly[(i + 1) % n]
            new.append((a[0]*0.75 + b[0]*0.25, a[1]*0.75 + b[1]*0.25))
            new.append((a[0]*0.25 + b[0]*0.75, a[1]*0.25 + b[1]*0.75))
        poly = new
    return poly


def _blob(cx, cy, r, seed, n=9):
    """A soft, rounded territory cell -- gently irregular (so it reads as a
    hand-drawn map region) but never spiky."""
    rng = random.Random(seed)
    pts = []
    for i in range(n):
        ang = 2 * math.pi * i / n
        rr = r * (0.90 + 0.13 * rng.random())   # mild +-6% wobble
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    return _chaikin(pts, 2)


def _circle_poly(cx, cy, r, n=24):
    """A clean regular n-gon -- the starting 'cap' a territory's cell is carved
    out of (roughening adds the organic wobble afterwards)."""
    return [(cx + r * math.cos(2 * math.pi * i / n),
             cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _capsule(a, b, hw):
    """A rectangle of half-width `hw` along segment a->b -- a land 'isthmus' that
    keeps an island in one piece even when a territory sits far out on a spur."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = math.hypot(dx, dy) or 1.0
    px, py = -dy / d * hw, dx / d * hw
    return [(a[0] + px, a[1] + py), (b[0] + px, b[1] + py),
            (b[0] - px, b[1] - py), (a[0] - px, a[1] - py)]


def _rough(poly, amp=5.0, seg=15):
    """Subdivide a polygon's edges and nudge every point by an offset that
    depends ONLY on its location (a hash of the rounded coordinate). Because the
    offset is positional, an edge shared by two cells is roughened identically in
    both, so the jagged coastlines/borders stay perfectly matched -- no gaps or
    overlaps -- while looking hand-drawn and bumpy like the real Isle Wars art."""
    if len(poly) < 3:
        return poly
    dense = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        k = max(1, int(d // seg))
        for j in range(k):
            t = j / k
            dense.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    out = []
    for x, y in dense:
        h = (int(round(x * 2)) * 73856093) ^ (int(round(y * 2)) * 19349663)
        h &= 0x7fffffff
        ang = (h % 6283) / 1000.0
        mag = amp * (0.45 + 0.55 * (((h >> 11) % 1000) / 1000.0))
        out.append((x + math.cos(ang) * mag, y + math.sin(ang) * mag))
    return out


def _point_in_poly(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi):
            inside = not inside
        j = i
    return inside


def _shade(col, f):
    return tuple(max(0, min(255, int(c * f))) for c in col)


class Button:
    def __init__(self, rect, label, key=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.key = key
        self.enabled = True
        self.hot = False

    def hit(self, pos):
        return self.enabled and self.rect.collidepoint(pos)


class Renderer:
    def __init__(self, screen, world, mapdef):
        self.screen = screen
        self.world = world
        self.coords = mapdef["coords"]
        self.board_w = mapdef["board_w"]
        self.board_h = mapdef["board_h"]
        self.continent_land = mapdef["continent_land"]
        self.continent_label = mapdef["continent_label"]
        # optional authentic per-territory outlines (board-space points). When
        # present the board is drawn from the real shapes instead of blobs.
        self.src_polys = mapdef.get("polys")
        self.real = self.src_polys is not None
        self.regular = mapdef.get("regular", False)
        self.sea_top = mapdef.get("sea_top", SEA_TOP)
        self.sea_bot = mapdef.get("sea_bot", SEA_BOT)
        pygame.font.init()
        self.f_small = pygame.font.SysFont("consolas", 14)
        self.f_med = pygame.font.SysFont("segoeui", 17)
        self.f_big = pygame.font.SysFont("segoeui", 23, bold=True)
        self.f_huge = pygame.font.SysFont("segoeui", 50, bold=True)
        self.f_node = pygame.font.SysFont("segoeui", 21, bold=True)
        self.f_tiny = pygame.font.SysFont("consolas", 11)
        self._compute_transform()
        self._build_geometry()
        self._build_sea()

    def _compute_transform(self):
        self.board_rect = pygame.Rect(15, 15, PANEL_X - 30, WIN_H - 30)
        fit = min(self.board_rect.w / self.board_w, self.board_rect.h / self.board_h)
        # Normalise so a territory is a consistent SMALL size on every map, with
        # the islands sitting in open water rather than stretched to fill the
        # board. Capped at `fit` so a big map still fits. Uses the median
        # nearest-neighbour spacing (board space).
        ts = self.world.territories
        nn = []
        for t in ts:
            x, y = self.coords[t]
            nn.append(min((math.hypot(x - self.coords[o][0], y - self.coords[o][1])
                           for o in ts if o != t), default=90.0))
        nn.sort()
        med = nn[len(nn) // 2] if nn else 90.0
        target = 64.0   # desired screen gap between adjacent territory centres
        self.scale = min(fit, target / med) if med else fit
        self.offx = self.board_rect.x + (self.board_rect.w - self.board_w * self.scale) / 2
        self.offy = self.board_rect.y + (self.board_rect.h - self.board_h * self.scale) / 2

    def tx(self, t):
        x, y = self.coords[t]
        return (self.offx + x * self.scale, self.offy + y * self.scale)

    def _txp(self, x, y):
        return (self.offx + x * self.scale, self.offy + y * self.scale)

    def _build_geometry(self):
        w = self.world
        centers = {t: self.tx(t) for t in w.territories}
        # nearest-neighbour distance per territory (sets cell size so they touch)
        nn = {}
        for t in w.territories:
            cx, cy = centers[t]
            nn[t] = min((math.hypot(cx-centers[o][0], cy-centers[o][1])
                         for o in w.territories if o != t), default=80)

        # radius = 0.46 * nearest-neighbour (no lower clamp) is provably
        # overlap-free: two blobs span 1.03*0.46*(nn_a+nn_b) <= 0.95*dist < dist.
        # The layout's min-spacing pass keeps that from making any territory tiny.
        self.radius = {t: min(42, nn[t] * 0.46) for t in w.territories}
        if self.real:
            # authentic outlines from the source mask: transform to screen space
            self.poly = {t: [self._txp(x, y) for x, y in self.src_polys[t]]
                         for t in w.territories}
            land = {t: self.poly[t] for t in w.territories}
            beach_pad = 11
        else:
            # every other map gets the same look: territories are roughened
            # Voronoi cells that tile their island like the K-Town Large board.
            self.poly, land = self._voronoi_cells(w, centers)
            beach_pad = 6

        # The island landmass is the UNION of the territory land shapes (each
        # expanded a touch for a sandy coast). The cells tile, so there is never
        # water inside an island; only the channels carved between continents.
        self.island_label = {}
        self.island_backing = {}
        for c, ts in w.continents.items():
            self.island_backing[c] = [(_expand(land[t], beach_pad),
                                       _expand(land[t], 3)) for t in ts]
            allpts = [p for t in ts for p in land[t]]
            lx = sum(p[0] for p in allpts) / len(allpts)
            ly = min(p[1] for p in allpts) - 16
            self.island_label[c] = (lx, ly)

        # Land isthmuses along within-island links guarantee each island is a
        # SINGLE connected landmass (no same-continent territory drifts off as its
        # own islet), even where the layout flung one out on a spur.
        if not self.real:
            for a, b in w.neighbor_pairs():
                if w.continent_of[a] != w.continent_of[b]:
                    continue
                cap = _rough(_capsule(centers[a], centers[b], 17), amp=3.0)
                self.island_backing[w.continent_of[a]].insert(
                    0, (_expand(cap, beach_pad), _expand(cap, 3)))

    def _voronoi_cells(self, w, centers):
        """Tile each island so the territories fill it like the authentic Isle
        Wars board.

        Every territory starts as a big disc whose radius reaches the bisector
        with its FARTHEST same-island neighbour -- so the cell, once carved by the
        Voronoi bisectors against its own island, runs ALL THE WAY up against each
        neighbour (full shared borders, no gaps), while the sea-facing side stays
        a rounded coast (no thin spikes). The disc is also cut short of every
        OTHER island so a clear water channel always stays between continents.

        The island LAND is the union of those discs (always solid -- never water
        inside an island). The owner cell is the carved Voronoi cell, inset a
        little so the land shows through as a thin border. Outlines are roughened
        into jagged, hand-drawn coasts.

        Returns (poly, land): owner fills and the land discs (drawn as the union)."""
        poly, land = {}, {}
        cont = w.continent_of
        others_of = {c: [o for o in w.territories if cont[o] != c]
                     for c in w.continents}

        def dist(a, b):
            return math.hypot(centers[a][0] - centers[b][0],
                              centers[a][1] - centers[b][1])

        for c, ts in w.continents.items():
            for t in ts:
                same = [o for o in ts if o != t]
                # size from the farthest same-island NEIGHBOUR (graph adjacency)
                # so every neighbour-facing side reaches its shared border.
                gnb = [o for o in w.neighbors[t] if cont[o] == c]
                if gnb:
                    R = max(34.0, min(96.0, max(dist(t, o) for o in gnb) * 0.56))
                elif same:
                    R = max(34.0, min(86.0, min(dist(t, o) for o in same) * 0.9))
                else:
                    R = 66.0
                disc = _circle_poly(centers[t][0], centers[t][1], R, 30)
                # cut the land back from every other island -> open water channel
                for o in others_of[c]:
                    disc = _clip_to_nearer(disc, centers[t], centers[o], frac=0.36)
                    if len(disc) < 3:
                        break
                if len(disc) < 3:
                    disc = _circle_poly(centers[t][0], centers[t][1], self.radius[t], 16)
                land[t] = _rough(disc, amp=5.0)
                # owner cell: full Voronoi within the island (touches every
                # neighbour), then inset a touch so the land reads as a border.
                cell = disc
                for o in same:
                    cell = _clip_to_nearer(cell, centers[t], centers[o])
                    if len(cell) < 3:
                        break
                cell = _expand(cell, -2) if len(cell) >= 3 else disc
                poly[t] = _rough(cell if len(cell) >= 3 else disc, amp=4.0)
        return poly, land

    def _make_ocean(self, w, h, seed=7):
        """A vertical sea gradient flecked with subtle wave glints."""
        top, bot = self.sea_top, self.sea_bot
        surf = pygame.Surface((w, h))
        for y in range(h):
            f = y / h
            col = tuple(int(top[i] + (bot[i] - top[i]) * f) for i in range(3))
            pygame.draw.line(surf, col, (0, y), (w, y))
        rng = random.Random(seed)
        for _ in range(int(w * h / 6200)):
            x, y = rng.randint(0, w), rng.randint(0, h)
            ln = rng.randint(6, 18)
            pygame.draw.line(surf, _shade(top, 1.16), (x, y), (x + ln, y), 1)
        return surf

    def _vignette(self):
        """Cached soft edge-darkening overlay for the start screen."""
        if getattr(self, "_vig", None) is None:
            vig = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
            cx, cy = WIN_W / 2, WIN_H / 2
            maxd = math.hypot(cx, cy)
            for radius in range(int(maxd), 60, -5):
                a = int(110 * (radius / maxd) ** 2.6)
                pygame.draw.circle(vig, (3, 7, 14, a), (int(cx), int(cy)), radius, 7)
            self._vig = vig
        return self._vig

    def _build_sea(self):
        br = self.board_rect
        self.sea = self._make_ocean(br.w, br.h)
        # a full-window ocean for the start screen (no panel seam)
        self.start_bg = self._make_ocean(WIN_W, WIN_H, seed=21)

    def territory_at(self, pos):
        for t, poly in self.poly.items():
            if _point_in_poly(pos, poly):
                return t
        return None

    # ------------------------------------------------------------------
    def draw_game(self, s):
        self.screen.fill(BG)
        self._draw_board(s)
        self._draw_panel(s)
        if s.mode == "OVER":
            self._draw_winner(s)

    def _draw_board(self, s):
        self.screen.blit(self.sea, (self.board_rect.x, self.board_rect.y))
        gs, world = s.gs, s.world

        # islands drawn as the union of their territory shapes (shadow, sandy
        # coast, land) -- same authentic style for every map.
        self._draw_real_land()

        # connections: the territories of an island already touch, so only the
        # cross-continent sea-bridges are drawn -- dashed, over open water,
        # exactly like the original board's island links.
        for a, b in world.neighbor_pairs():
            if world.continent_of[a] == world.continent_of[b]:
                continue
            self._dashed(self.tx(a), self.tx(b), SEAROUTE, 3, 12)

        # attack / move arrow
        if s.arrow:
            self._draw_arrow(self.tx(s.arrow[0]), self.tx(s.arrow[1]),
                             config.PLAYER_COLORS[s.arrow[2]])

        # countries
        for t in world.territories:
            self._draw_country(s, t)

        # island name labels (on a dark pill so they read over land or sea)
        for c, (lx, ly) in self.island_label.items():
            lab = self.f_small.render(self.continent_label[c].upper(), True, (224, 234, 246))
            pw, ph = lab.get_width() + 14, lab.get_height() + 6
            pill = pygame.Surface((pw, ph), pygame.SRCALPHA)
            pygame.draw.rect(pill, (10, 16, 26, 180), pill.get_rect(), border_radius=8)
            self.screen.blit(pill, (lx - pw/2, ly - 3))
            self.screen.blit(lab, (lx - lab.get_width()/2, ly))

        if s.selected is not None:
            pygame.draw.polygon(self.screen, (255, 255, 255), self.poly[s.selected], 4)
        if s.dice:
            self._draw_dice(s)

    def _draw_real_land(self):
        """Draw authentic islands as the union of the real territory shapes:
        one drop shadow, a sandy coastal fringe, then the land fill. The union
        gives each island its true concave coastline and keeps islands apart."""
        sh = pygame.Surface((self.screen.get_width(), self.screen.get_height()),
                            pygame.SRCALPHA)
        for items in self.island_backing.values():
            for beach, _land in items:
                pygame.draw.polygon(sh, (0, 0, 0, 70),
                                    [(x + 5, y + 7) for x, y in beach])
        self.screen.blit(sh, (0, 0))
        for items in self.island_backing.values():
            for beach, _land in items:
                pygame.draw.polygon(self.screen, BEACH, beach)
        for c, items in self.island_backing.items():
            land = self.continent_land[c]
            for _beach, land_poly in items:
                pygame.draw.polygon(self.screen, land, land_poly)

    def _draw_country(self, s, t):
        gs = s.gs
        poly = self.poly[t]
        owner = gs.owner[t]
        col = config.PLAYER_COLORS[owner]
        cx, cy = self.tx(t)
        r = self.radius[t]
        if s.legal_targets and t in s.legal_targets:
            pygame.draw.polygon(self.screen, (255, 236, 120), _expand(poly, 5), 4)
        # soft drop shadow gives the land a little lift off the sea
        pygame.draw.polygon(self.screen, _shade(col, 0.34), [(x + 2, y + 3) for x, y in poly])
        pygame.draw.polygon(self.screen, col, poly)
        # subtle top highlight + darker rim -> hand-painted look
        pygame.draw.polygon(self.screen, _shade(col, 1.16), _expand(poly, -3), 2)
        pygame.draw.polygon(self.screen, _shade(col, 0.5), poly, 2)
        # army disc (scales with the territory) with a dark ring for contrast
        rc = max(12, int(r * 0.5))
        pygame.draw.circle(self.screen, (18, 22, 30), (int(cx), int(cy)), rc + 2)
        pygame.draw.circle(self.screen, _shade(col, 0.8), (int(cx), int(cy)), rc)
        txt = self.f_node.render(str(gs.armies[t]), True, (252, 252, 254))
        self.screen.blit(txt, (cx - txt.get_width()/2, cy - txt.get_height()/2))
        idt = self.f_tiny.render(str(t), True, (12, 16, 24))
        self.screen.blit(idt, (cx - idt.get_width()/2, cy - r + 2))

    def _dashed(self, a, b, col, width, dash):
        dx, dy = b[0]-a[0], b[1]-a[1]
        dist = math.hypot(dx, dy) or 1
        ux, uy = dx/dist, dy/dist
        n = int(dist // (dash*2))
        for i in range(n + 1):
            s0 = i * dash * 2
            s1 = min(s0 + dash, dist)
            pygame.draw.line(self.screen, col,
                             (a[0]+ux*s0, a[1]+uy*s0), (a[0]+ux*s1, a[1]+uy*s1), width)

    def _draw_arrow(self, a, b, col):
        pygame.draw.line(self.screen, (250, 250, 250), a, b, 7)
        pygame.draw.line(self.screen, col, a, b, 4)
        ang = math.atan2(b[1]-a[1], b[0]-a[0])
        for da in (-0.4, 0.4):
            ex = b[0] - 20 * math.cos(ang + da)
            ey = b[1] - 20 * math.sin(ang + da)
            pygame.draw.line(self.screen, col, b, (ex, ey), 5)

    def _draw_dice(self, s):
        mt, et = s.dice["mt"], s.dice["et"]
        a, b = self.tx(mt), self.tx(et)
        mid = ((a[0]+b[0])//2, (a[1]+b[1])//2)
        self._die(mid[0]-44, mid[1]-22, s.dice["atk"], config.PLAYER_COLORS[s.dice["pa"]], s.dice["win"] == "attacker")
        self._die(mid[0]+8, mid[1]-22, s.dice["deff"], config.PLAYER_COLORS[s.dice["pd"]], s.dice["win"] == "defender")

    def _die(self, x, y, val, col, winner):
        rect = pygame.Rect(x, y, 36, 44)
        pygame.draw.rect(self.screen, (250, 250, 250), rect, border_radius=7)
        pygame.draw.rect(self.screen, (40, 200, 90) if winner else (200, 60, 60), rect, 3, border_radius=7)
        pygame.draw.rect(self.screen, col, (x+4, y+4, 28, 6), border_radius=3)
        d = self.f_big.render(str(val), True, (20, 22, 28))
        self.screen.blit(d, (x + 18 - d.get_width()/2, y + 24 - d.get_height()/2))

    # ------------------------------------------------------------------
    def _draw_panel(self, s):
        pygame.draw.rect(self.screen, PANEL_BG, (PANEL_X, 0, PANEL_W, WIN_H))
        x = PANEL_X + 16
        y = 14
        self.screen.blit(self.f_big.render("ISLE WARS", True, INK), (x, y))
        clk = self.f_med.render(s.timer_str(), True, (150, 210, 250))
        self.screen.blit(clk, (PANEL_X + PANEL_W - 16 - clk.get_width(), y + 4))
        y += 38

        terts, army = s.gs.stats()
        order = sorted(range(s.gs.num_players), key=lambda p: -terts[p])
        for p in order:
            alive = s.gs.is_alive(p)
            box = pygame.Rect(x, y, PANEL_W - 32, 30)
            cur = (p == s.current and s.mode == "PLAYING")
            pygame.draw.rect(self.screen, CARD if not cur else (66, 74, 96), box, border_radius=6)
            pygame.draw.rect(self.screen, config.PLAYER_COLORS[p], (x+6, y+6, 18, 18), border_radius=4)
            name = config.agent_label(s.controllers[p])
            c = INK if alive else (110, 110, 120)
            self.screen.blit(self.f_small.render(f"P{p} {name}"[:26], True, c), (x+30, y+3))
            nisl = len(s.gs.continents_owned(p))   # fully-owned islands/continents
            self.screen.blit(self.f_small.render(
                f"{terts[p]:2d} terr  {army[p]:3d} arm  {nisl} isl", True, SUBINK), (x+30, y+15))
            if cur:
                pygame.draw.polygon(self.screen, (255, 220, 90),
                                    [(x+PANEL_W-30, y+8), (x+PANEL_W-30, y+22), (x+PANEL_W-22, y+15)])
            y += 34
        y += 6

        if s.mode == "PLAYING":
            self.screen.blit(self.f_med.render(f"Turn {s.gs.turn_count}  -  {s.phase.upper()}", True, (255, 230, 140)), (x, y))
            y += 26
            for line in s.prompt:
                self.screen.blit(self.f_small.render(line[:42], True, INK), (x, y)); y += 17

        for b in s.buttons:
            self._draw_button(b)

        self.screen.blit(self.f_small.render(f"Speed: {s.speed_label()}", True, SUBINK), (x, s.speed_rect.y - 18))
        pygame.draw.rect(self.screen, CARD, s.speed_rect, border_radius=4)
        kx = s.speed_rect.x + int(s.speed_frac * (s.speed_rect.w - 12))
        pygame.draw.rect(self.screen, (120, 180, 250), (kx, s.speed_rect.y-3, 12, s.speed_rect.h+6), border_radius=4)

        ly = s.speed_rect.bottom + 14
        self.screen.blit(self.f_small.render("LOG", True, SUBINK), (x, ly))
        # tiny colour legend next to the LOG header
        lx = x + 34
        for lbl, col in (("fortify", LOG_FORTIFY), ("attack", LOG_ATTACK),
                         ("move", LOG_MOVE), ("conquer", LOG_CONQUER)):
            pygame.draw.rect(self.screen, col, (lx, ly + 3, 8, 8))
            t = self.f_tiny.render(lbl, True, SUBINK)
            self.screen.blit(t, (lx + 10, ly + 1))
            lx += 10 + t.get_width() + 8
        ly += 18
        for line in s.log[-((WIN_H - ly) // 16):]:
            txt = line[:40]
            col = _log_color(line)
            # colour the leading "P<n>" player tag with that player's map colour
            if len(txt) >= 2 and txt[0] == "P" and txt[1].isdigit():
                p = int(txt[1])
                pc = config.PLAYER_COLORS[p] if p < len(config.PLAYER_COLORS) else col
                tag = self.f_small.render(txt[:2], True, pc)
                self.screen.blit(tag, (x, ly))
                self.screen.blit(self.f_small.render(txt[2:], True, col),
                                 (x + tag.get_width(), ly))
            else:
                self.screen.blit(self.f_small.render(txt, True, col), (x, ly))
            ly += 16

    def _draw_button(self, b, accent=None):
        base = (70, 80, 105) if b.enabled else (50, 54, 64)
        if b.hot and b.enabled:
            base = (92, 104, 134)
        if accent:
            base = (accent[0] + 18, accent[1] + 16, accent[2] + 10) if (b.hot and b.enabled) else accent
        pygame.draw.rect(self.screen, base, b.rect, border_radius=7)
        if accent:
            pygame.draw.rect(self.screen, (235, 205, 90), b.rect, 2, border_radius=7)
        c = INK if b.enabled else (120, 124, 134)
        t = self.f_med.render(b.label, True, c)
        self.screen.blit(t, (b.rect.centerx - t.get_width()/2, b.rect.centery - t.get_height()/2))

    def _draw_winner(self, s):
        surf = pygame.Surface((self.board_rect.w, self.board_rect.h), pygame.SRCALPHA)
        surf.fill((10, 12, 18, 180))
        self.screen.blit(surf, (self.board_rect.x, self.board_rect.y))
        w = s.gs.winner_id if s.gs.winner_id is not None else s.winner
        name = config.agent_label(s.controllers[w])
        t1 = self.f_huge.render(f"P{w} WINS", True, config.PLAYER_COLORS[w])
        t2 = self.f_big.render(name, True, INK)
        cx = self.board_rect.centerx
        cy = self.board_rect.centery
        self.screen.blit(t1, (cx - t1.get_width()/2, cy - 74))
        self.screen.blit(t2, (cx - t2.get_width()/2, cy - 14))
        turns = s.gs.turn_count
        stats = self.f_med.render(
            f"Won in {turns} turn{'' if turns == 1 else 's'}   -   time {s.timer_str()}",
            True, (150, 210, 250))
        self.screen.blit(stats, (cx - stats.get_width()/2, cy + 26))
        t3 = self.f_med.render("Click 'New Game' to play again", True, SUBINK)
        self.screen.blit(t3, (cx - t3.get_width()/2, cy + 62))

    # ------------------------------------------------------------------
    def draw_start(self, s):
        # full-window ocean background + a soft darkening veil and vignette
        self.screen.blit(self.start_bg, (0, 0))
        veil = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        veil.fill((10, 16, 26, 150))
        self.screen.blit(veil, (0, 0))
        self.screen.blit(self._vignette(), (0, 0))
        cx = WIN_W // 2
        # title with a soft shadow for depth
        for dy, c in ((3, (6, 10, 18)), (0, INK)):
            t = self.f_huge.render("ISLE WARS", True, c)
            self.screen.blit(t, (cx - t.get_width()/2, 14 + dy))
        sub = self.f_med.render("Pick a map and players, then Start.   * = built-in bot.",
                                True, (206, 218, 236))
        self.screen.blit(sub, (cx - sub.get_width()/2, 72))

        self._draw_button(s.map_button)
        size = self.f_small.render(maps.map_size_str(s.map_keys[s.map_idx]),
                                   True, (150, 196, 232))
        self.screen.blit(size, (cx - size.get_width()/2, s.map_button.rect.bottom + 4))

        # player-count stepper
        self._draw_button(s.btn_pminus)
        self._draw_button(s.btn_pplus)
        pc = self.f_med.render(f"Players: {s.num_players}", True, INK)
        self.screen.blit(pc, (cx - pc.get_width()/2, 168))

        # card behind only the ACTIVE player rows
        top = s.slot_prev[0].rect.top - 14
        bot = s.slot_prev[s.num_players - 1].rect.bottom + 14
        card = pygame.Rect(cx - 360, top, 720, bot - top)
        panel = pygame.Surface((card.w, card.h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (18, 24, 36, 175), panel.get_rect(), border_radius=16)
        self.screen.blit(panel, card.topleft)

        for i in range(s.num_players):
            b = s.slot_buttons[i]
            y = b.rect.y
            builtin = config.is_builtin(s.controllers[i])
            pygame.draw.rect(self.screen, config.PLAYER_COLORS[i],
                             (card.x + 18, y + 7, 24, 24), border_radius=5)
            self.screen.blit(self.f_med.render(f"P{i}", True, INK), (card.x + 50, y + 8))
            self._draw_button(s.slot_prev[i])
            self._draw_button(b, accent=(74, 64, 36) if builtin else None)
            self._draw_button(s.slot_next[i])
            dx = cx + 54
            diff = config.agent_difficulty(s.controllers[i])
            if diff:
                dcol = config.DIFFICULTY_COLOR.get(diff, INK)
                badge = self.f_small.render(diff.upper(), True, (18, 22, 30))
                bw = badge.get_width() + 12
                pygame.draw.rect(self.screen, dcol, (dx, y + 9, bw, 20), border_radius=6)
                self.screen.blit(badge, (dx + 6, y + 11))
                dx += bw + 8
            col = (235, 208, 110) if builtin else (160, 174, 196)
            desc = self.f_small.render(config.agent_desc(s.controllers[i]), True, col)
            self.screen.blit(desc, (dx, y + 11))

        self._draw_button(s.btn_all_human)
        self._draw_button(s.btn_random)
        self._draw_button(s.start_button)

        n = len(config.discover_agents())
        tip = self.f_small.render(
            f"{n} bots available   -   drop your own .dlv files in the custom/ folder",
            True, (188, 198, 216))
        self.screen.blit(tip, (cx - tip.get_width()/2, s.start_button.rect.bottom + 14))
