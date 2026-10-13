# Isle Wars — playable game + DLV agents

A desktop (Pygame) implementation of Isle Wars. Every player is driven by an
ASP **DLV 2.1.2** agent (via **embasp**) — or by a human at the keyboard/mouse.
The map, rules and agents are the ones from `../final`.

```
isle-wars-game/
  main.py          entry point (start screen + game loop + human input)
  config.py        paths, rules constants, players, default controllers
  worldmap.py      parses ../final/world.dlv (territories / neighbours / continents)
  layout.py        authored board coordinates + continent tints
  engine.py        rules: reinforcement, dice battles, conquer, elimination, victory
  asp_bridge.py    embasp wrapper: state -> EDB -> run agent .dlv -> parsed action
  driver.py        turn orchestration (generator of events) shared by GUI + headless
  gui.py           Pygame renderer + widgets
  headless_test.py run N AI-vs-AI games, print win statistics
  requirements.txt pygame, embasp
```

The agents live in `../final/`: `agent.dlv` (the smart "perfect" benchmark) plus
`agent_aggressive.dlv`, `agent_defensive.dlv`, `agent_greedy.dlv`,
`agent_continent.dlv`, and `testing_idb__1_.dlv` ("Adaptive (GA)", an
adaptive strategy-selecting agent with GA-tunable parameters). To add another
agent, drop a `.dlv` file in `../final/` and add it to `CHOICES` in `main.py`
and `AGENT_LABELS` in `config.py`.

## Setup

The repo already has a virtualenv with embasp at `../python-dlv-example/.venv`.
Just add pygame to it:

```
../python-dlv-example/.venv/Scripts/python.exe -m pip install pygame
```

(or make a fresh venv and `pip install -r requirements.txt`). The DLV2 solver
used is `../python-dlv-example/executable/dlv-2.1.2-win64.exe` (see `config.py`).

## Run the game

```
../python-dlv-example/.venv/Scripts/python.exe main.py
```

- **Start screen:** click each `P0..P5` slot to cycle its controller between
  *Human* and the available agents, then **Start Game**. Defaults: P0 & P5 =
  Smart, P1 = Aggressive, P2 = Defensive, P3 = Greedy, P4 = Continent-hunter.
- **Watching AI:** Pause/Resume, Step (one action while paused), and a Speed
  slider. The side panel shows live standings, the current phase, and a log.
- **Playing as Human:**
  - *Fortify* — left-click your territories to place 1 army each (right-click
    dumps all remaining there).
  - *Choose* — click your territory (≥2 armies) to select it, then click an
    adjacent **enemy** to attack (one battle), or an adjacent **ally** to move
    all-but-one there (ends turn). **End Turn** passes.
  - *Conquer* — when you empty an enemy territory, pick how many armies to move
    in with **− / + / Confirm**.

## Headless statistics

```
../python-dlv-example/.venv/Scripts/python.exe headless_test.py 16 2000
#                                                        ^games ^base-seed
```

Plays full AI-vs-AI games and reports per-agent win counts. In a 16-game run the
**Smart** agent is the clear best (~56% of wins, ahead of every other agent),
with Defensive the strongest rival.

## Rules notes (see also ../final/Isle Wars Documentation.pdf)

- A battle is one d6 each; **a tie loses for the attacker** (win prob 15/36).
- Losing a battle costs the attacker 1 army; if the attacking territory held
  exactly 2 and loses, it flips to the defender (you can lose land by attacking).
- Reinforcements per turn = `max(3, floor(owned/3)) + continent bonuses`
  (bonuses configurable in `config.py`; an assumption, not fixed by the PDF).
