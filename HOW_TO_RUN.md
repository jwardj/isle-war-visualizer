# Isle Wars — how to run

A Risk-style island-conquest game where every AI player is a **DLV** (Answer Set
Programming) agent. You can drop in your own `.dlv` bots and watch them fight.

---

## Run it (Windows)

> **Cloned from GitHub?** The DLV solver isn't in the repo. Download
> DLV 2.1.2 for Windows from <https://dlv.demacs.unical.it> and save it as
> `bin\dlv-2.1.2-win64.exe` (or set the `DLV_EXE` environment variable).

**Just double-click `run.bat`.**

That's it. The first time, it sets up a small Python environment (needs an
internet connection, takes about a minute). Every run after that launches
instantly.

> Prefer the command line? From this folder:
> `.venv\Scripts\python main.py`  (or use whatever Python env you set up).

---

## Send it to a friend

1. **Zip this whole `Ilse war runner` folder** and send it to them.
   - You can delete the `.venv` folder first if it exists — it'll be rebuilt.
     (The DLV solver in `bin\` is included, so they don't need to download it.)
2. They need **Python 3** installed once, from
   <https://www.python.org/downloads/> — during install, tick
   **"Add Python to PATH."**
3. They **double-click `run.bat`**. First run installs the two dependencies
   automatically; then the game opens.

Everything the game needs is inside this folder — no other downloads.

> Windows only out of the box (the bundled DLV solver is a Windows program).
> On Mac/Linux, drop a matching DLV 2.x binary into `bin\` and run
> `python main.py` in a venv with `pip install -r requirements.txt`.

---

## Playing

On the start screen you can:

- **Map** — click to cycle 5 maps (size shown underneath).
- **Players: N** — use −/+ to play with 2–6 players.
- **Each player slot** — click (or the ◀ ▶ arrows) to set it to **Human** or any
  DLV bot. Built-in bots have a **gold tab + ★** and a difficulty badge
  (Easy → Expert). **All Human** / **Random Bots** fill every slot at once.
- **START GAME**.

In-game: a speed slider, Pause/Step, and **New Game** (back to this screen).

---

## Add your own bot

1. Save your agent as `<name>.dlv` in the **`custom\`** folder.
2. Launch the game — it appears automatically as a pickable controller.

The built-in bots we made live in **`bots\`** (gold ★ tab + difficulty badge);
your drop-ins go in **`custom\`**. See **`bots\README.md`** for the full rule
contract (what facts you're given each phase and what atoms to answer with).
`bots\_example_pass.dlv` is a minimal working example, and the built-in bots
(`overlord.dlv`, `berserker.dlv`, …) are good references.

---

## If something goes wrong

- **"Python was not found"** → install Python 3 (link above) and tick *Add to
  PATH*, then run `run.bat` again.
- **Setup failed** → check your internet connection (it needs to download
  `pygame` and `embasp-python` the first time).
- **A bot never does anything** → its `.dlv` likely has a rule error; the game
  safely falls back to "pass" so it can't crash the match. Test the file on its
  own, and check it follows `agents\README.md`.
