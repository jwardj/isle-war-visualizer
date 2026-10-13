"""Isle Wars — entry point. Start screen, game loop, AI auto-play, human input."""
import sys
import queue
import random
import threading
import pygame

import config
import engine as E
import driver
import asp_bridge as bridge
import maps
from gui import Renderer, Button, WIN_W, WIN_H, PANEL_X


class AIWorker:
    """Runs one AI player's whole turn on a background thread (each DLV solve
    is ~100ms and would otherwise freeze the window). Events are handed to the
    main thread one at a time through a size-1 queue, so the solver for the
    NEXT action runs while the CURRENT one is being animated -- the UI never
    blocks waiting on DLV."""

    def __init__(self, gs, controller, player):
        self.q = queue.Queue(maxsize=1)
        self._abort = threading.Event()
        self._t = threading.Thread(target=self._run, args=(gs, controller, player),
                                   daemon=True)
        self._t.start()

    def _put(self, item):
        while not self._abort.is_set():
            try:
                self.q.put(item, timeout=0.1)
                return
            except queue.Full:
                continue

    def _run(self, gs, controller, player):
        try:
            for ev in driver.ai_turn(gs, controller, player):
                if self._abort.is_set():
                    return
                self._put(ev)
        finally:
            self._put(None)  # sentinel: turn finished

    def abort(self):
        self._abort.set()
        try:
            while True:
                self.q.get_nowait()  # unblock a pending put()
        except queue.Empty:
            pass


def apply_event(gs, ev):
    """Reproduce an event's board change on the DISPLAY state. The authoritative
    mutation already happened on the worker's copy; this keeps what the player
    sees exactly in step with the animation being shown."""
    typ = ev["type"]
    if typ == "fortify":
        for t, n in ev["placements"]:
            gs.armies[t] += n
    elif typ == "battle":
        mt, et, out = ev["mt"], ev["et"], ev["outcome"]
        if out == "def_lost":
            gs.armies[et] -= 1
        elif out == "atk_lost":
            gs.armies[mt] -= 1
        elif out == "conquered":
            gs.armies[et] = 0
        elif out == "defeated":
            gs.armies[mt] = 1
            gs.owner[mt] = ev["defender"]
    elif typ == "conquer_move":
        mt, et, a = ev["mt"], ev["et"], ev["a"]
        gs.armies[mt] -= a
        gs.owner[et] = ev["player"]
        gs.armies[et] = a
    elif typ == "move" and ev.get("ok", True):
        gs.armies[ev["t1"]] -= ev["n"]
        gs.armies[ev["t2"]] += ev["n"]
    # pass / illegal / turn_capped: no board change


class Session:
    def __init__(self):
        self.map_keys = maps.MAP_KEYS
        self.map_idx = 0
        self.mapdef = maps.build_map(self.map_keys[self.map_idx])
        self.world = self.mapdef["world"]
        self.mode = "START"
        self.num_players = config.NUM_PLAYERS
        self.controllers = list(config.DEFAULT_CONTROLLERS)
        self.choices = [config.HUMAN]
        self.refresh_choices()
        self.log = []
        self.speed_frac = 0.72
        self._build_start_widgets()
        self._build_play_widgets()
        self._reset_runtime()

    def refresh_choices(self):
        """Re-scan the agents/ folder so newly-dropped .dlv files show up
        next time the start screen is shown, without restarting the game."""
        self.choices = [config.HUMAN] + config.discover_agents()
        self.controllers = [c if c in self.choices else config.HUMAN for c in self.controllers]

    def cycle_slot(self, i, delta):
        """Advance player i's controller through the available choices."""
        cur = self.choices.index(self.controllers[i]) if self.controllers[i] in self.choices else 0
        self.controllers[i] = self.choices[(cur + delta) % len(self.choices)]

    def randomize_controllers(self):
        bots = config.discover_agents()
        pool = bots if bots else [config.HUMAN]
        for i in range(self.num_players):
            self.controllers[i] = random.choice(pool)

    def change_players(self, delta):
        self.num_players = max(2, min(config.NUM_PLAYERS, self.num_players + delta))
        self._layout_start_bottom()

    # ---- widgets ------------------------------------------------------
    def _build_start_widgets(self):
        cx = WIN_W // 2
        self.map_button = Button((cx - 170, 102, 340, 34), "")
        self.btn_pminus = Button((cx - 94, 164, 30, 30), "-")
        self.btn_pplus = Button((cx + 64, 164, 30, 30), "+")
        self.slot_base, self.row_h = 206, 54
        self.slot_buttons, self.slot_prev, self.slot_next = [], [], []
        for i in range(config.NUM_PLAYERS):
            y = self.slot_base + i * self.row_h
            self.slot_prev.append(Button((cx - 268, y, 32, 36), "<"))
            self.slot_buttons.append(Button((cx - 230, y, 228, 36), "", key=i))
            self.slot_next.append(Button((cx + 2, y, 32, 36), ">"))
        self.btn_all_human = Button((cx - 230, 0, 160, 34), "All Human")
        self.btn_random = Button((cx - 62, 0, 160, 34), "Random Bots")
        self.start_button = Button((cx - 110, 0, 220, 48), "START GAME")
        self._layout_start_bottom()

    def _layout_start_bottom(self):
        """Position the quick-fill + start buttons just under the last visible
        player row, so the panel stays tight as the player count changes."""
        cx = WIN_W // 2
        qy = self.slot_base + self.num_players * self.row_h + 12
        self.btn_all_human.rect.topleft = (cx - 230, qy)
        self.btn_random.rect.topleft = (cx - 62, qy)
        self.start_button.rect.topleft = (cx - 110, qy + 48)

    def _build_play_widgets(self):
        bx = PANEL_X + 16
        self.btn_pause = Button((bx, 372, 90, 30), "Pause")
        self.btn_step = Button((bx + 98, 372, 78, 30), "Step")
        self.btn_new = Button((bx + 184, 372, 96, 30), "New Game")
        self.btn_pass = Button((bx, 410, 130, 30), "End Turn")
        self.btn_minus = Button((bx, 410, 32, 30), "-")
        self.btn_plus = Button((bx + 40, 410, 32, 30), "+")
        self.btn_confirm = Button((bx + 80, 410, 110, 30), "Confirm")
        self.speed_rect = pygame.Rect(bx, 452, 280, 12)
        self.buttons = []

    # ---- runtime state ------------------------------------------------
    def _reset_runtime(self):
        if getattr(self, "worker", None) is not None:
            self.worker.abort()
        self.arrow = None
        self.dice = None
        self.selected = None
        self.legal_targets = set()
        self.prompt = []
        self.winner = None
        self.current = 0
        self.phase = E.FORTIFY
        self.turn_gen = None
        self.turn_started = False
        self.paused = False
        self.step_request = False
        self.worker = None
        self._auth = None
        self.anim_until = 0
        self.human_stage = None
        self.human_remaining = 0
        self.human_placements = {}
        self.conquer_val = 0
        self.conquer_ctx = None
        self.timer_ms = 0
        self._timer_last = pygame.time.get_ticks()

    def start_game(self):
        self.mapdef = maps.build_map(self.map_keys[self.map_idx])
        self.world = self.mapdef["world"]
        self.gs = E.GameState(num_players=self.num_players, world=self.world)
        self.log = []
        self._reset_runtime()
        self.current = driver.next_alive(self.gs, -1)
        self.mode = "PLAYING"
        self.paused = False

    def tick_timer(self):
        """Accumulate elapsed play time, excluding paused / non-playing time."""
        now = pygame.time.get_ticks()
        if self.mode == "PLAYING" and not self.paused:
            self.timer_ms += now - self._timer_last
        self._timer_last = now

    def timer_str(self):
        s = self.timer_ms // 1000
        return f"{s // 60:02d}:{s % 60:02d}"

    # ---- helpers ------------------------------------------------------
    def speed_label(self):
        return f"{1 + self.speed_frac * 59:.0f}x"

    def _visual_ms(self, base):
        # snappier across the board; near-instant at the top of the slider
        return int(base * (0.02 + 0.78 * (1 - self.speed_frac)))

    def _auto_delay_ms(self):
        return int(320 * (1 - self.speed_frac)) if not self.paused else 0

    def logline(self, s):
        self.log.append(s)
        if len(self.log) > 300:
            self.log = self.log[-300:]

    def name(self, p):
        return config.agent_label(self.controllers[p])


# ----------------------------------------------------------------------
def process_event(s, ev):
    """Visualise an event that has already mutated the state; set animation."""
    s.dice = None
    s.arrow = None
    p = ev.get("player")
    typ = ev["type"]
    vis = 180
    if typ == "fortify":
        s.phase = E.CHOOSE
        placed = ", ".join(f"{n}->T{t}" for t, n in ev["placements"])
        s.logline(f"P{p} fortify +{ev['amount']}: {placed}")
    elif typ == "battle" or ev.get("atk_die"):
        s.arrow = (ev["mt"], ev["et"], p)
        s.dice = {"mt": ev["mt"], "et": ev["et"], "atk": ev["atk_die"],
                  "deff": ev["def_die"], "win": ev["winner"],
                  "pa": p, "pd": ev["defender"]}
        out = ev["outcome"]
        vis = 340
        word = {"def_lost": "hit", "atk_lost": "lost a unit",
                "conquered": "CONQUERED", "defeated": "was repelled & lost MT"}[out]
        s.logline(f"P{p} {ev['mt']}->{ev['et']} [{ev['atk_die']}v{ev['def_die']}] {word}")
    elif typ == "conquer_move":
        s.arrow = (ev["mt"], ev["et"], p)
        s.logline(f"P{p} moves {ev['a']} into T{ev['et']}")
    elif typ == "move":
        s.arrow = (ev["t1"], ev["t2"], p)
        s.logline(f"P{p} repositions {ev['n']}: T{ev['t1']}->T{ev['t2']}")
    elif typ == "pass":
        s.logline(f"P{p} passes")
        vis = 90
    elif typ == "illegal":
        s.logline(f"P{p} produced an illegal action -> turn ends")
    elif typ == "turn_capped":
        s.logline(f"P{p} hit the action cap")
    now = pygame.time.get_ticks()
    s.anim_until = now + s._visual_ms(vis) + s._auto_delay_ms()


def advance_turn(s):
    """Move to the next alive player; check victory."""
    if s.gs.check_winner() is not None:
        s.winner = s.gs.winner_id
        s.mode = "OVER"
        s.logline(f"== P{s.winner} ({s.name(s.winner)}) wins! ==")
        return
    s.current = driver.next_alive(s.gs, s.current)
    s.turn_started = False
    s.turn_gen = None
    s.human_stage = None
    s.selected = None
    s.legal_targets = set()
    s.prompt = []


def pump_ai(s):
    """Drive the current AI player's turn via a background worker. The worker
    solves the next action while the previous one animates, so the window
    keeps running at 60fps no matter how long DLV takes."""
    now = pygame.time.get_ticks()
    if now < s.anim_until:
        return
    if not (not s.paused or s.step_request):
        return
    if s.worker is None:
        # hand the worker an authoritative copy; the renderer keeps reading
        # the display state (s.gs), which we sync event-by-event below.
        s._auth = s.gs.clone()
        s.gs.turn_count += 1               # keep the panel's turn counter live
        s.worker = AIWorker(s._auth, s.controllers[s.current], s.current)
    try:
        ev = s.worker.q.get_nowait()
    except queue.Empty:
        return                              # still thinking; UI stays smooth
    s.step_request = False
    if ev is None:                          # turn finished
        s.gs = s._auth                      # adopt authoritative state
        s._auth = None
        s.worker = None
        advance_turn(s)
    else:
        apply_event(s.gs, ev)
        process_event(s, ev)


# ---- human input ------------------------------------------------------
def human_begin_turn(s):
    amount = s.gs.begin_turn(s.current)
    s.phase = E.FORTIFY
    s.human_stage = "fortify"
    s.human_remaining = amount
    s.human_placements = {}
    s.legal_targets = set(s.gs.owned_by(s.current))
    _human_prompt(s)


def _human_prompt(s):
    if s.human_stage == "fortify":
        s.prompt = [f"Place {s.human_remaining} armies.",
                    "L-click your land = +1, R-click = all here."]
    elif s.human_stage == "choose":
        if s.selected is None:
            s.prompt = ["Select one of your territories (>=2 armies).",
                        "Then click an enemy to attack or ally to move.",
                        "'End Turn' to stop."]
        else:
            s.prompt = [f"T{s.selected} selected.",
                        "Click adjacent enemy = attack, ally = move all-but-1."]
    elif s.human_stage == "conquer":
        mt, et = s.conquer_ctx
        s.prompt = [f"Conquered T{et}! Move how many from T{mt}?",
                    f"Value: {s.conquer_val} (max {s.gs.armies[mt]-1}). Confirm."]


def human_click(s, t, button):
    p = s.current
    if s.human_stage == "fortify":
        if s.gs.owner[t] == p:
            add = s.human_remaining if button == 3 else 1
            s.human_placements[t] = s.human_placements.get(t, 0) + add
            s.human_remaining -= add
            if s.human_remaining <= 0:
                placements = list(s.human_placements.items())
                applied = s.gs.apply_fortify(p, placements)
                s.logline(f"P{p} (you) fortify: " + ", ".join(f"{n}->T{tt}" for tt, n in applied))
                s.human_stage = "choose"
                s.selected = None
                s.legal_targets = _human_choose_targets(s)
        _human_prompt(s)
    elif s.human_stage == "choose":
        if s.selected is None:
            if s.gs.owner[t] == p and s.gs.armies[t] >= 2:
                s.selected = t
                s.legal_targets = set(s.world.neighbors[t])
        else:
            mt = s.selected
            if t == mt:
                s.selected = None
                s.legal_targets = _human_choose_targets(s)
            elif s.gs.owner[t] == p and s.world.are_neighbors(mt, t):
                # move all but one, ends turn
                n = s.gs.armies[mt] - 1
                if n >= 1 and s.gs.apply_move(p, mt, t, n):
                    s.logline(f"P{p} (you) move {n}: T{mt}->T{t}")
                    s.arrow = (mt, t, p)
                    advance_turn(s)
                    return
            elif s.gs.legal_attack(p, mt, t):
                _human_attack(s, mt, t)
        _human_prompt(s)


def _human_choose_targets(s):
    p = s.current
    return {t for t in s.gs.owned_by(p) if s.gs.armies[t] >= 2
            and any(True for _ in s.world.neighbors[t])}


def _human_attack(s, mt, et):
    p = s.current
    defender = s.gs.owner[et]
    ev = s.gs.resolve_attack(mt, et)
    ev["player"] = p
    ev["defender"] = defender
    process_event(s, ev)
    if ev["outcome"] == "defeated":
        advance_turn(s)
    elif ev["outcome"] == "conquered":
        s.human_stage = "conquer"
        s.conquer_ctx = (mt, et)
        s.conquer_val = s.gs.armies[mt] - 1
        s.selected = None
        s.legal_targets = set()
    else:
        if s.gs.armies[mt] < 2:
            s.selected = None
            s.legal_targets = _human_choose_targets(s)


def human_confirm_conquer(s):
    mt, et = s.conquer_ctx
    moved = s.gs.apply_conquer_move(mt, et, s.conquer_val)
    s.logline(f"P{s.current} (you) move {moved} into T{et}")
    s.arrow = (mt, et, s.current)
    s.human_stage = "choose"
    s.selected = None
    s.legal_targets = _human_choose_targets(s)
    _human_prompt(s)


# ---- panel button wiring ---------------------------------------------
def play_buttons(s):
    is_human = s.controllers[s.current] == config.HUMAN and s.mode == "PLAYING"
    s.btn_pause.label = "Resume" if s.paused else "Pause"
    s.btn_pause.enabled = not is_human
    s.btn_step.enabled = (not is_human) and s.paused
    btns = [s.btn_pause, s.btn_step, s.btn_new]
    if is_human and s.human_stage == "choose":
        btns.append(s.btn_pass)
    if is_human and s.human_stage == "conquer":
        btns += [s.btn_minus, s.btn_plus, s.btn_confirm]
    s.buttons = btns
    return btns


def handle_play_click(s, pos):
    for b in s.buttons:
        if b.hit(pos):
            if b is s.btn_pause:
                s.paused = not s.paused
            elif b is s.btn_step:
                s.step_request = True
            elif b is s.btn_new:
                if s.worker is not None:
                    s.worker.abort()
                    s.worker = None
                    s._auth = None
                s.mode = "START"
                s.refresh_choices()
            elif b is s.btn_pass:
                advance_turn(s)
            elif b is s.btn_minus:
                s.conquer_val = max(1, s.conquer_val - 1)
                _human_prompt(s)
            elif b is s.btn_plus:
                mt = s.conquer_ctx[0]
                s.conquer_val = min(s.gs.armies[mt] - 1, s.conquer_val + 1)
                _human_prompt(s)
            elif b is s.btn_confirm:
                human_confirm_conquer(s)
            return True
    if s.speed_rect.collidepoint(pos):
        s.speed_frac = max(0.0, min(1.0, (pos[0] - s.speed_rect.x) / s.speed_rect.w))
        return True
    return False


# ---- main loop --------------------------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Isle Wars")
    clock = pygame.time.Clock()
    s = Session()
    r = Renderer(screen, s.world, s.mapdef)

    running = True
    dragging_speed = False
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.MOUSEBUTTONDOWN:
                if s.mode == "START":
                    if s.start_button.hit(e.pos):
                        s.start_game()
                        r = Renderer(screen, s.world, s.mapdef)
                    elif s.map_button.hit(e.pos):
                        s.map_idx = (s.map_idx + 1) % len(s.map_keys)
                    elif s.btn_pminus.hit(e.pos):
                        s.change_players(-1)
                    elif s.btn_pplus.hit(e.pos):
                        s.change_players(+1)
                    elif s.btn_all_human.hit(e.pos):
                        s.controllers = [config.HUMAN] * config.NUM_PLAYERS
                    elif s.btn_random.hit(e.pos):
                        s.randomize_controllers()
                    else:
                        for i in range(s.num_players):
                            if s.slot_prev[i].hit(e.pos):
                                s.cycle_slot(i, -1)
                                break
                            if s.slot_next[i].hit(e.pos):
                                s.cycle_slot(i, +1)
                                break
                            if s.slot_buttons[i].hit(e.pos):
                                s.cycle_slot(i, -1 if e.button == 3 else +1)
                                break
                else:
                    if handle_play_click(s, e.pos):
                        if s.speed_rect.collidepoint(e.pos):
                            dragging_speed = True
                    elif s.mode == "PLAYING" and s.controllers[s.current] == config.HUMAN:
                        t = r.territory_at(e.pos)
                        if t is not None and s.human_stage in ("fortify", "choose"):
                            human_click(s, t, e.button)
            elif e.type == pygame.MOUSEBUTTONUP:
                dragging_speed = False
            elif e.type == pygame.MOUSEMOTION:
                if dragging_speed:
                    s.speed_frac = max(0.0, min(1.0, (e.pos[0] - s.speed_rect.x) / s.speed_rect.w))
                if s.mode == "START":
                    for b in ([s.map_button, s.btn_pminus, s.btn_pplus,
                               s.btn_all_human, s.btn_random, s.start_button]
                              + s.slot_buttons + s.slot_prev + s.slot_next):
                        b.hot = b.rect.collidepoint(e.pos)
                for b in getattr(s, "buttons", []):
                    b.hot = b.rect.collidepoint(e.pos)

        # advance game
        s.tick_timer()
        if s.mode == "PLAYING":
            play_buttons(s)
            if not s.turn_started:
                s.turn_started = True
                if s.controllers[s.current] == config.HUMAN:
                    human_begin_turn(s)
                else:
                    s.turn_gen = None
            if s.controllers[s.current] != config.HUMAN:
                pump_ai(s)

        # render
        if s.mode == "START":
            s.map_button.label = f"Map: {maps.MAP_LABELS[s.map_keys[s.map_idx]]}  (click to change)"
            for b in s.slot_buttons:
                lbl = config.agent_label(s.controllers[b.key])
                b.label = ("* " + lbl) if config.is_builtin(s.controllers[b.key]) else lbl
            r.draw_start(s)
        else:
            play_buttons(s)
            r.draw_game(s)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
