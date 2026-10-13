"""Run full AI-vs-AI games with no GUI: verify the game always terminates
with a winner and report per-agent win statistics.

Usage:
    python headless_test.py [num_games] [base_seed]
"""
import sys
import time
from collections import Counter

import config
import driver


def run(num_games=10, base_seed=1000, controllers=None):
    if controllers is None:
        agents = config.discover_agents()
        if not agents:
            print(f"No .dlv agents found in {config.AGENTS_DIR} -- drop some in "
                  "(see agents/README.md) before running headless AI-vs-AI games.")
            return
        controllers = [agents[i % len(agents)] for i in range(config.NUM_PLAYERS)]
    print("Controllers:")
    for i, c in enumerate(controllers):
        print(f"  P{i}: {config.agent_label(c)}  ({c})")
    print(f"\nPlaying {num_games} games...\n")

    wins = Counter()
    by_agent = Counter()
    capped_games = 0
    t0 = time.time()
    for g in range(num_games):
        seed = base_seed + g
        winner, gs, turns, capped = driver.play_game(controllers, seed=seed)
        terts, _ = gs.stats()
        wins[winner] += 1
        by_agent[controllers[winner]] += 1
        capped_games += 1 if capped else 0
        print(f"  game {g:2d} seed={seed}: winner P{winner} "
              f"({config.agent_label(controllers[winner])}) "
              f"in {turns} turns; final territories={terts}"
              f"{'  [CAPPED]' if capped else ''}")

    dt = time.time() - t0
    print(f"\nDone in {dt:.1f}s ({dt/num_games:.1f}s/game). "
          f"{capped_games} game(s) hit the turn cap.\n")
    print("Wins by player slot:")
    for p in range(len(controllers)):
        print(f"  P{p} {config.agent_label(controllers[p]):18s}: {wins[p]}")
    print("\nWins by agent type:")
    for ag, n in by_agent.most_common():
        print(f"  {config.agent_label(ag):18s}: {n}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    s = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    run(n, s)
