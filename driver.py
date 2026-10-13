"""Turn orchestration shared by the headless runner and the GUI.

`ai_turn` is a generator that mutates the GameState and yields event dicts
(one per atomic action / battle) so callers can animate. Headless callers
just exhaust the generator.
"""
import config
import engine as E
import asp_bridge as bridge


def ai_turn(gs: "E.GameState", agent_file, p, cap=config.MAX_ACTIONS_PER_TURN):
    """Run player p's whole turn with the given DLV agent, yielding events."""
    amount = gs.begin_turn(p)
    f = bridge.decide_fortify(agent_file, gs, p)
    applied = gs.apply_fortify(p, f["placements"])
    yield {"type": "fortify", "player": p, "placements": applied, "amount": amount}

    actions = 0
    while True:
        actions += 1
        if actions > cap:
            yield {"type": "turn_capped", "player": p}
            return
        if not gs.is_alive(p):
            return
        act = bridge.decide_choose(agent_file, gs, p)
        if act["type"] == "pass":
            yield {"type": "pass", "player": p}
            return
        if act["type"] == "move":
            ok = gs.apply_move(p, act["t1"], act["t2"], act["n"])
            yield {"type": "move", "player": p, "ok": ok,
                   "t1": act["t1"], "t2": act["t2"], "n": act["n"]}
            return
        # attack
        mt, et = act["mt"], act["et"]
        if not gs.legal_attack(p, mt, et):
            yield {"type": "illegal", "player": p, "mt": mt, "et": et}
            return
        defender = gs.owner[et]
        ev = gs.resolve_attack(mt, et)
        ev["player"] = p
        ev["defender"] = defender
        yield ev
        if ev["outcome"] == "defeated":
            return
        if ev["outcome"] == "conquered":
            cq = bridge.decide_conquer(agent_file, gs, p, mt, et)
            moved = gs.apply_conquer_move(mt, et, cq["a"])
            yield {"type": "conquer_move", "player": p,
                   "mt": mt, "et": et, "a": moved}
        # otherwise loop and let the agent decide again


def next_alive(gs, after):
    """Index of the next alive player strictly after `after` (wraps)."""
    n = gs.num_players
    for step in range(1, n + 1):
        cand = (after + step) % n
        if gs.is_alive(cand):
            return cand
    return after


def leader(gs):
    """Player with the most territories (tie -> lowest id)."""
    terts, _ = gs.stats()
    return max(range(gs.num_players), key=lambda p: (terts[p], -p))


def play_game(controllers, seed=None, max_turns=4000, event_cb=None, world=None):
    """Run a full AI-vs-AI game. Returns (winner, gs, turns, capped_out)."""
    gs = E.GameState(num_players=len(controllers), seed=seed, world=world)
    p = -1
    turns = 0
    capped = False
    while gs.check_winner() is None and turns < max_turns:
        p = next_alive(gs, p)
        for ev in ai_turn(gs, controllers[p], p):
            if event_cb:
                event_cb(gs, ev)
            if ev.get("type") == "turn_capped":
                capped = True
        turns += 1
    winner = gs.check_winner()
    if winner is None:
        winner = leader(gs)  # decide by territory count if it ran long
    return winner, gs, turns, capped
