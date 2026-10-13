"""Isle Wars game engine: state + rules. No GUI / solver dependencies."""
import copy
import random

import config
from worldmap import load_world

# Phases
FORTIFY = "fortify"
CHOOSE = "choose"
CONQUER = "conquer"

# Initial army distribution -- matches StudentIsleWars (max_armies = 6: every
# territory starts with a random 1..6 armies).
MAX_START_ARMIES = 6


class GameState:
    def __init__(self, num_players=config.NUM_PLAYERS, world=None, rng=None, seed=None):
        self.world = world or load_world()
        self.num_players = num_players
        self.rng = rng or random.Random(seed)
        self.owner = {}      # territory -> player id
        self.armies = {}     # territory -> int
        self.phase = FORTIFY
        self.current = 0     # index into self.order
        self.pending_conquer = None  # (mt, et) while phase == CONQUER
        self.to_fortify = 0  # reinforcements owed to the current player
        self.winner_id = None
        self.turn_count = 0
        self._distribute()
        self.order = list(range(num_players))
        self.current = 0
        self.phase = FORTIFY

    # ---- setup --------------------------------------------------------
    def _distribute(self):
        """Assign territories and starting armies exactly like StudentIsleWars'
        load_territories: each player gets floor(N / players) territories, any
        leftover territories go to random players, the whole assignment is
        shuffled, and every territory starts with a random 1..MAX_START_ARMIES."""
        terts = list(self.world.territories)
        n = len(terts)
        assigns = []
        for p in range(self.num_players):
            assigns.extend([p] * (n // self.num_players))
        while len(assigns) < n:
            assigns.append(self.rng.randint(0, self.num_players - 1))
        self.rng.shuffle(assigns)
        for t, p in zip(terts, assigns):
            self.owner[t] = p
            self.armies[t] = self.rng.randint(1, MAX_START_ARMIES)

    def clone(self):
        """A deep-ish copy that SHARES the (immutable) world but copies all
        mutable game state, including an independent RNG. Used so an AI turn
        can run on a background thread without the renderer seeing it mutate."""
        g = GameState.__new__(GameState)
        g.world = self.world                  # shared, never mutated
        g.num_players = self.num_players
        g.rng = copy.deepcopy(self.rng)       # independent stream
        g.owner = dict(self.owner)
        g.armies = dict(self.armies)
        g.phase = self.phase
        g.current = self.current
        g.pending_conquer = self.pending_conquer
        g.to_fortify = self.to_fortify
        g.winner_id = self.winner_id
        g.turn_count = self.turn_count
        g.order = list(self.order)
        return g

    # ---- queries ------------------------------------------------------
    def owned_by(self, p):
        return sorted(t for t in self.world.territories if self.owner[t] == p)

    def is_alive(self, p):
        return any(self.owner[t] == p for t in self.world.territories)

    def alive_players(self):
        return [p for p in range(self.num_players) if self.is_alive(p)]

    def continents_owned(self, p):
        out = []
        for c, ts in self.world.continents.items():
            if all(self.owner[t] == p for t in ts):
                out.append(c)
        return out

    def compute_reinforcements(self, p):
        owned = len(self.owned_by(p))
        base = max(config.MIN_REINFORCE, owned // config.TERRITORY_DIVISOR)
        bonus = sum(self.world.continent_bonus.get(c, 0) for c in self.continents_owned(p))
        return base + bonus

    def legal_attack(self, p, mt, et):
        return (
            self.owner.get(mt) == p
            and self.owner.get(et) is not None
            and self.owner[et] != p
            and self.world.are_neighbors(mt, et)
            and self.armies[mt] >= 2
            and self.armies[mt] >= self.armies[et]   # doc: "at least as many"
        )

    # ---- mutations ----------------------------------------------------
    def begin_turn(self, p):
        self.phase = FORTIFY
        self.to_fortify = self.compute_reinforcements(p)
        self.turn_count += 1
        return self.to_fortify

    def apply_fortify(self, p, placements):
        """placements: list of (territory, n). Tolerant: if the set is not a
        valid full allocation of `to_fortify` onto owned territories, fall
        back to dumping everything on the lowest-id owned territory.
        Returns the list of (t, n) actually applied."""
        A = self.to_fortify
        valid = [(t, n) for (t, n) in placements
                 if self.owner.get(t) == p and n > 0]
        if valid and sum(n for _, n in valid) == A:
            applied = valid
        else:
            owned = self.owned_by(p)
            applied = [(owned[0], A)] if owned else []
        for t, n in applied:
            self.armies[t] += n
        self.to_fortify = 0
        self.phase = CHOOSE
        return applied

    def resolve_attack(self, mt, et):
        """One battle. Returns an event dict describing dice + outcome and
        mutates state. Outcomes:
          'def_lost'  defender lost an army
          'atk_lost'  attacker lost an army
          'conquered' defender hit 0 -> phase CONQUER (pending set)
          'defeated'  attacker held 2 and lost -> MT flips, turn ends
        """
        atk = self.rng.randint(1, 6)
        deff = self.rng.randint(1, 6)
        ev = {"type": "battle", "mt": mt, "et": et,
              "atk_die": atk, "def_die": deff}
        if atk > deff:
            self.armies[et] -= 1
            if self.armies[et] <= 0:
                self.armies[et] = 0
                self.phase = CONQUER
                self.pending_conquer = (mt, et)
                ev["outcome"] = "conquered"
            else:
                ev["outcome"] = "def_lost"
        else:
            # attacker loses the battle (strictly-less OR tie)
            if self.armies[mt] == 2:
                self.armies[mt] = 1
                self.owner[mt] = self.owner[et]
                ev["outcome"] = "defeated"
            else:
                self.armies[mt] -= 1
                ev["outcome"] = "atk_lost"
        ev["winner"] = "attacker" if atk > deff else "defender"
        return ev

    def apply_conquer_move(self, mt, et, a):
        """Move `a` armies from mt into the just-emptied et. Tolerant of bad
        a (clamped to [1, armies[mt]-1]). Returns the a actually moved."""
        max_a = self.armies[mt] - 1
        if a < 1:
            a = 1
        if a > max_a:
            a = max_a
        attacker = self.owner[mt]
        self.armies[mt] -= a
        self.owner[et] = attacker
        self.armies[et] = a
        self.phase = CHOOSE
        self.pending_conquer = None
        return a

    def apply_move(self, p, t1, t2, n):
        """Reposition n armies between two owned neighbours. Returns bool ok."""
        if (self.owner.get(t1) == p and self.owner.get(t2) == p
                and self.world.are_neighbors(t1, t2)
                and 1 <= n <= self.armies[t1] - 1):
            self.armies[t1] -= n
            self.armies[t2] += n
            return True
        return False

    def check_winner(self):
        alive = self.alive_players()
        if len(alive) == 1:
            self.winner_id = alive[0]
        return self.winner_id

    # ---- stats --------------------------------------------------------
    def stats(self):
        terts = {p: 0 for p in range(self.num_players)}
        army = {p: 0 for p in range(self.num_players)}
        for t in self.world.territories:
            terts[self.owner[t]] += 1
            army[self.owner[t]] += self.armies[t]
        return terts, army
