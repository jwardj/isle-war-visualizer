"""Parse a world definition .dlv file into Python structures.

Single source of truth for territories, the neighbour graph and continents,
shared by the engine, the GUI and the layout. A process can load multiple
worlds (one per map) since nothing here is cached at module level.
"""
import os
import re

DEFAULT_WORLD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "maps", "classic26", "world.dlv")


class WorldMap:
    def __init__(self, territories, neighbors, continent_of, continent_bonus=None, path=None):
        self.territories = sorted(territories)            # list[int]
        self.neighbors = neighbors                        # dict[int, set[int]]
        self.continent_of = continent_of                  # dict[int, int]
        self.continent_bonus = continent_bonus or {}       # dict[int, int]
        self.path = path                                  # source world.dlv, for the DLV solver
        self.continents = {}                              # dict[int, list[int]]
        for t, c in continent_of.items():
            self.continents.setdefault(c, []).append(t)
        for c in self.continents:
            self.continents[c].sort()

    def are_neighbors(self, a, b):
        return b in self.neighbors.get(a, set())

    def neighbor_pairs(self):
        """Each undirected edge once, as sorted (a, b) tuples."""
        seen = set()
        for a, bs in self.neighbors.items():
            for b in bs:
                seen.add((min(a, b), max(a, b)))
        return sorted(seen)


_FACT = re.compile(r"^([a-z_]+)\s*\(([^)]*)\)$")


def load_world(path=DEFAULT_WORLD_FILE, continent_bonus=None):
    territories, continent_of = set(), {}
    neighbors = {}
    # strip line comments, then split the whole file into individual facts on '.'
    # (handles one-or-many facts per line, like DLV does)
    with open(path, "r") as f:
        text = f.read()
    cleaned = []
    for line in text.splitlines():
        i = line.find("%")
        cleaned.append(line if i < 0 else line[:i])
    for chunk in " ".join(cleaned).split("."):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = _FACT.match(chunk)
        if not m:
            continue
        pred, args = m.group(1), [a.strip() for a in m.group(2).split(",")]
        if pred == "territory":
            territories.add(int(args[0]))
        elif pred == "in_continent":
            continent_of[int(args[0])] = int(args[1])
        elif pred == "neighbor":
            a, b = int(args[0]), int(args[1])
            neighbors.setdefault(a, set()).add(b)
            neighbors.setdefault(b, set()).add(a)  # make symmetric for safety
    for t in territories:
        neighbors.setdefault(t, set())
    return WorldMap(territories, neighbors, continent_of, continent_bonus, path=path)


if __name__ == "__main__":
    w = load_world()
    print("territories:", len(w.territories))
    print("continents:", {c: ts for c, ts in sorted(w.continents.items())})
    print("edges:", len(w.neighbor_pairs()))
