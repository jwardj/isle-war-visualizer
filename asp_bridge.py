"""Bridge between the Python engine and the DLV agents, via embasp.

For each decision we assemble  world facts + a state EDB + the player's
agent rules, run DLV 2.1.2 through embasp, take DLV's optimal answer set
(the last one it emits) and parse the chosen action atom(s).
Every entry point has a safe fallback so a broken agent can never crash or
stall the game.
"""
import io
import os
import re
import contextlib
import subprocess

import config

# --- robust DLV subprocess handling ------------------------------------
# embasp launches dlv.exe with a plain subprocess.Popen in text mode. We patch
# Popen so that EVERY solve:
#   1. starts hidden -- under a windowed host (pythonw) a console window would
#      otherwise flash and steal focus dozens of times a turn;
#   2. talks UTF-8 on stdin/stdout -- otherwise the program is sent in the OS
#      locale encoding, so an agent file containing non-ASCII characters (smart
#      quotes / em-dashes pasted from a doc) would corrupt the program and make
#      DLV drop rules. This is what makes `&int`, `&mod` and every agent work
#      reliably regardless of how the .dlv file was saved.
_OrigPopen = subprocess.Popen


class _SafePopen(_OrigPopen):
    def __init__(self, *args, **kwargs):
        if hasattr(subprocess, "CREATE_NO_WINDOW") and "creationflags" not in kwargs:
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        if kwargs.get("universal_newlines") or kwargs.get("text"):
            kwargs.setdefault("encoding", "utf-8")
            kwargs.setdefault("errors", "replace")
        super().__init__(*args, **kwargs)


subprocess.Popen = _SafePopen

from embasp.platforms.desktop.desktop_handler import DesktopHandler
from embasp.specializations.dlv2.desktop.dlv2_desktop_service import DLV2DesktopService
from embasp.languages.asp.asp_input_program import ASPInputProgram

import engine as E

_ATOM = re.compile(r"^([a-z_][a-zA-Z0-9_]*)(?:\((.*)\))?$")

# Cache static / agent file contents so we read each file at most once.
_FILE_CACHE = {}


def _read(path):
    if path not in _FILE_CACHE:
        # read tolerantly: UTF-8 (with optional BOM) first, then legacy cp1252,
        # so any .dlv a friend drops in is decoded correctly.
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                _FILE_CACHE[path] = f.read()
        except UnicodeDecodeError:
            with open(path, "r", encoding="cp1252") as f:
                _FILE_CACHE[path] = f.read()
    return _FILE_CACHE[path]


def _world_text(world):
    return _read(world.path)


def _agent_text(agent_file):
    return _read(config.agent_path(agent_file))


def parse_atom(atom):
    """'attack(9,10)' -> ('attack', [9, 10]);  'pass' -> ('pass', [])."""
    m = _ATOM.match(atom.strip())
    if not m:
        return None, []
    name = m.group(1)
    args = []
    if m.group(2):
        for a in m.group(2).split(","):
            a = a.strip()
            args.append(int(a) if re.fullmatch(r"-?\d+", a) else a)
    return name, args


def build_edb(state: "E.GameState", player, phase, extra=None):
    """Return the dynamic EDB facts as a single ASP string."""
    lines = [f"my_id({player}).", f"phase({phase})."]
    for t in state.world.territories:
        lines.append(f"owner({t},{state.owner[t]}).")
        lines.append(f"armies_present({t},{state.armies[t]}).")
    if phase == E.FORTIFY:
        lines.append(f"to_fortify({state.to_fortify}).")
    elif phase == E.CONQUER and extra:
        mt, et = extra
        lines.append(f"conquered({mt},{et}).")
    return "\n".join(lines)


def _solve(agent_file, world, edb_text):
    """Run DLV and return the atom-string list of the optimal answer set
    (last one DLV emits), or [] on any failure."""
    handler = DesktopHandler(DLV2DesktopService(config.DLV_EXE))
    prog = ASPInputProgram()
    prog.add_program(_world_text(world))
    prog.add_program(edb_text)
    prog.add_program(_agent_text(agent_file))
    handler.add_program(prog)
    # The service prints the command line + timing to stdout; silence it.
    with contextlib.redirect_stdout(io.StringIO()):
        out = handler.start_sync()
    if out.get_errors():
        return []
    sets = out.get_answer_sets()
    if not sets:
        return []
    return sets[-1].get_answer_set()  # DLV emits the optimum last


# ---- public decision API ---------------------------------------------
def decide_fortify(agent_file, state, player):
    edb = build_edb(state, player, E.FORTIFY)
    placements = []
    for atom in _solve(agent_file, state.world, edb):
        name, args = parse_atom(atom)
        if name == "fortify" and len(args) == 2:
            placements.append((args[0], args[1]))
    return {"type": "fortify", "placements": placements}


def decide_choose(agent_file, state, player):
    edb = build_edb(state, player, E.CHOOSE)
    atoms = _solve(agent_file, state.world, edb)
    for atom in atoms:
        name, args = parse_atom(atom)
        if name == "attack" and len(args) == 2:
            return {"type": "attack", "mt": args[0], "et": args[1]}
        if name == "move" and len(args) == 3:
            return {"type": "move", "t1": args[0], "t2": args[1], "n": args[2]}
    # 'pass' or nothing -> end the turn
    return {"type": "pass"}


def decide_conquer(agent_file, state, player, mt, et):
    edb = build_edb(state, player, E.CONQUER, extra=(mt, et))
    a = None
    for atom in _solve(agent_file, state.world, edb):
        name, args = parse_atom(atom)
        if name == "move" and len(args) == 3 and args[0] == mt and args[1] == et:
            a = args[2]
            break
    if a is None:
        a = state.armies[mt] - 1  # fallback: push all but one
    return {"type": "conquer", "mt": mt, "et": et, "a": a}
