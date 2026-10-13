# Built-in bots + the agent rule contract

This `bots/` folder holds the **built-in bots that ship with the game** (the
ones marked with a gold ★ tab and a difficulty badge): `overlord.dlv`,
`berserker.dlv`, `turtle.dlv`, `landgrabber.dlv`, `continent_hunter.dlv`. Read
them as worked examples, and `_example_pass.dlv` for the simplest possible
agent.

## To add YOUR OWN agent

Put your `*.dlv` file in the **`custom/`** folder (one level up, next to this
one) — NOT here. Anything in `custom/` is auto-discovered and appears on the
start screen as a pickable controller.

1. Save your **IDB only** as `custom/<name>.dlv` (e.g. `custom/team7.dlv`).
2. Launch the game (double-click `run.bat`).
3. Click a player slot until it shows your filename, then **Start Game**.

That's it — copy the file in, it works. The rest of this file is the rule
contract your agent must follow.

## Rules for the file you drop in

- **IDB only.** Do not include world facts (`territory`, `neighbor`,
  `in_continent`) or state facts (`owner`, `armies_present`, `my_id`,
  `phase`, `to_fortify`, `conquered`) — the game supplies all of those at
  decision time.
- **No `#show` statements.** Comment them out or delete them; the game reads
  every atom in the answer set itself.
- One file is reused for every phase. Guard phase-specific rules with
  `phase(fortify)`, `phase(choose)`, or `phase(conquer)` in the body where it
  matters.
- **Full DLV 2.1.2 is available.** Standard aggregates (`#count`, `#sum`,
  `#min`, `#max`), choice rules (`{a(X):b(X)}=1`), weak constraints
  (`:~ body. [w@p, t]`), interval terms (`n(1..K)`) and the external
  arithmetic atoms (`&int(L,U;X)`, `&mod(X,M;R)`, ...) all work. Files may be
  saved in any common encoding (UTF-8 / UTF-8-BOM / Windows-1252).

## Bots that ship with the game (read these for examples)

| File | Style |
|------|-------|
| `overlord.dlv` | Strongest all-rounder: only safe winning fights, completes continents, defends after conquest. |
| `berserker.dlv` | Attacks at every opportunity, biggest advantage first. |
| `turtle.dlv` | Defensive; only strikes with an overwhelming edge. |
| `landgrabber.dlv` | Greedy; hits the weakest enemy for cheap captures. |
| `continent_hunter.dlv` | Pushes into the continent it most nearly owns. |

## What you're given, per phase

Always present:
```
territory(T).            % every territory id
in_continent(T,C).       % territory T is in continent C
neighbor(T1,T2).         % T1 and T2 are adjacent (already reflexive)
my_id(N).                % your player number
owner(T,N).              % territory T is owned by player N
armies_present(T,C).     % territory T holds C armies
phase(P).                % P is fortify | choose | conquer
```

**`phase(fortify)`** — also given `to_fortify(A)` (armies you must place).
Respond with one or more `fortify(T,N)` atoms that add up to exactly `A`.

**`phase(choose)`** — respond with exactly one of:
- `pass` — end your turn.
- `move(T1,T2,N)` — move `N` armies T1 -> T2 (both yours, adjacent); ends turn.
- `attack(MT,ET)` — attack enemy territory `ET` from your `MT`. Requires
  `MT`/`ET` adjacent, `armies_present(MT,_) >= 2`, and at least as many
  armies in `MT` as the enemy has in `ET`. One battle: both sides roll a
  d6; attacker needs to roll *strictly higher* to win (ties favor the
  defender). Lose with exactly 2 armies in `MT` and you lose `MT` itself.

**`phase(conquer)`** — given `conquered(MT,ET)` (you just emptied `ET` from
`MT`). Respond with `move(MT,ET,A)`, `0 < A < armies_present(MT,_)`. If you
don't answer, the game defaults to moving everything but one army in.

See `_example_pass.dlv` in this folder for a minimal valid agent.
