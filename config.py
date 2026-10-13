"""Static configuration for the Isle Wars game."""
import glob
import os

# --- Paths -------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # ...\Italy


def _find_dlv():
    """Locate the DLV solver. Checks (in order): the DLV_EXE env var, a bundled
    bin/ folder inside the game (the portable, shareable location), and the
    original PYTHONDLVEXAMPLE checkout. Returns the first that exists, else the
    bundled path (so error messages point somewhere sensible)."""
    candidates = []
    env = os.environ.get("DLV_EXE")
    if env:
        candidates.append(env)
    candidates += sorted(glob.glob(os.path.join(HERE, "bin", "dlv*")))
    candidates.append(os.path.join(ROOT, "PYTHONDLVEXAMPLE", "executable",
                                   "dlv-2.1.2-win64.exe"))
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return os.path.join(HERE, "bin", "dlv-2.1.2-win64.exe")


DLV_EXE = _find_dlv()

# Bots live in two folders, both auto-discovered:
#   bots/   -- the built-in bots that ship with the game (the ones we wrote)
#   custom/ -- drop YOUR .dlv files here (see bots/README.md for the contract)
BUILTIN_DIR = os.path.join(HERE, "bots")
CUSTOM_DIR = os.path.join(HERE, "custom")
AGENTS_DIR = CUSTOM_DIR          # back-compat alias; the drop-in folder

# --- Rules (assumptions, see plan) ------------------------------------
# Reinforcements at the start of a turn:
#   A = max(MIN_REINFORCE, floor(owned / 3)) + sum(continent bonus for fully-owned continents)
MIN_REINFORCE = 3
TERRITORY_DIVISOR = 3

# Safety cap: max actions a single player may take in one choose-phase
# (guards against an agent that never passes).
MAX_ACTIONS_PER_TURN = 300


def _dlvs_in(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(f for f in os.listdir(folder)
                  if f.endswith(".dlv") and not f.startswith("_"))


def discover_agents():
    """All selectable agents: the built-in bots first, then custom drop-ins."""
    return _dlvs_in(BUILTIN_DIR) + _dlvs_in(CUSTOM_DIR)


def agent_path(controller):
    """Absolute path to an agent file, checking built-in then custom folders."""
    for folder in (BUILTIN_DIR, CUSTOM_DIR):
        p = os.path.join(folder, controller)
        if os.path.isfile(p):
            return p
    return os.path.join(CUSTOM_DIR, controller)


def agent_label(controller):
    """Display label for a controller token (HUMAN or an agent filename)."""
    if controller in AGENT_LABELS:
        return AGENT_LABELS[controller]
    name = controller[:-4] if controller.endswith(".dlv") else controller
    return name.replace("_", " ").replace("-", " ").title()


def agent_desc(controller):
    """One-line playstyle hint shown on the start screen."""
    return AGENT_DESC.get(controller, "Custom DLV agent")


# Difficulty of each built-in bot (how tough it is to beat). Berserker just
# rushes blindly so it's the easiest; Overlord plays nearly optimally.
AGENT_DIFFICULTY = {
    "berserker.dlv": "Easy",
    "landgrabber.dlv": "Easy",
    "turtle.dlv": "Medium",
    "continent_hunter.dlv": "Hard",
    "overlord.dlv": "Expert",
}
DIFFICULTY_COLOR = {
    "Easy": (120, 210, 130),
    "Medium": (240, 205, 90),
    "Hard": (245, 150, 70),
    "Expert": (240, 95, 95),
}


def agent_difficulty(controller):
    return AGENT_DIFFICULTY.get(controller)


# Bots that ship with the game (the ones we wrote). Marked with a star and a
# gold tab on the start screen so they stand out from drop-in agents.
BUILTIN_AGENTS = {
    "overlord.dlv", "berserker.dlv", "turtle.dlv",
    "landgrabber.dlv", "continent_hunter.dlv",
}


def is_builtin(controller):
    return (controller in BUILTIN_AGENTS
            or os.path.isfile(os.path.join(BUILTIN_DIR, controller)))

# --- Players -----------------------------------------------------------
NUM_PLAYERS = 6

# Distinct, high-contrast player colours (RGB).
PLAYER_COLORS = [
    (66, 135, 245),   # 0 blue
    (235, 64, 52),    # 1 red
    (52, 199, 89),    # 2 green
    (255, 184, 28),   # 3 amber
    (175, 82, 222),   # 4 purple
    (90, 200, 200),   # 5 teal
]
PLAYER_NAMES = ["P0", "P1", "P2", "P3", "P4", "P5"]

# Special controller token for a human-driven slot.
HUMAN = "HUMAN"

# Default controller per player slot. Each is either HUMAN or an agent
# filename (in bots/ or custom/). Overridable on the start screen.
# Pre-loaded lineup: your two bots (agent 13 + Jonah) vs the built-in bots.
DEFAULT_CONTROLLERS = [
    "agent13.dlv",            # P0 - Team 6 agent 13 (custom/)
    "Jonah-version13.dlv",    # P1 - Jonah (custom/)
    "berserker.dlv",          # P2 - built-in
    "turtle.dlv",             # P3 - built-in
    "landgrabber.dlv",        # P4 - built-in
    "continent_hunter.dlv",   # P5 - built-in
]
# Fresh clones don't ship the custom/ agents; fall back to a built-in bot.
DEFAULT_CONTROLLERS = [c if c == HUMAN or os.path.isfile(agent_path(c)) else "overlord.dlv"
                       for c in DEFAULT_CONTROLLERS]

# Short labels shown on the start screen for known agents.
AGENT_LABELS = {
    HUMAN: "Human",
    "overlord.dlv": "Overlord (strongest)",
    "berserker.dlv": "Berserker (rush)",
    "turtle.dlv": "Turtle (defensive)",
    "landgrabber.dlv": "Landgrabber (greedy)",
    "continent_hunter.dlv": "Continent Hunter",
    "team6-agent4.dlv": "Team 6 (v4)",
    "agent13.dlv": "Team 6 (v13)",
    "Jonah-version13.dlv": "Jonah (v13)",
    "agent.dlv": "Smart (perfect)",
    "agent_aggressive.dlv": "Aggressive",
    "agent_defensive.dlv": "Defensive",
    "agent_greedy.dlv": "Greedy",
    "agent_continent.dlv": "Continent-hunter",
    "testing_idb__1_.dlv": "Aiden",
    "team6.dlv": "team 6",
    "version5.dlv": "Alex",
}

# One-line playstyle hints (start screen). Unknown agents fall back to a
# generic line via agent_desc().
AGENT_DESC = {
    HUMAN: "You control this slot",
    "overlord.dlv": "Strongest: safe fights + continents",
    "berserker.dlv": "All-out attacker, never holds back",
    "turtle.dlv": "Defensive; only overwhelming strikes",
    "landgrabber.dlv": "Greedy; grabs the weakest land",
    "continent_hunter.dlv": "Chases continent bonuses",
}
