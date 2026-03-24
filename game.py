#!/usr/bin/env python3
"""
T-REX RUNNER — ASCII EDITION (Optimized)
SPACE/UP = Jump · DOWN = Duck · Q = Quit
"""

import curses
import random

# ─── Chrome Dino style sprites ────────────────────────────
# Faithful recreation of the iconic Chrome offline T-Rex:
# flat-top head, dot eye, open jaw, tiny arm, tapered tail

RUN1 = [
    "            ████████  ",
    "          ██████████  ",
    "          █ ████████  ",
    "          ██████████  ",
    "          ██████      ",
    "  █      ███████████  ",
    "  ██   █████████████  ",
    "  ███ ██████████████  ",
    "  ██████████████████  ",
    "  ██ █████████████    ",
    "  █  ████████████     ",
    "      ███████████     ",
    "       ████  ██       ",
    "       ███    █       ",
    "       ██             ",
]
RUN2 = [
    "            ████████  ",
    "          ██████████  ",
    "          █ ████████  ",
    "          ██████████  ",
    "          ██████      ",
    "  █      ███████████  ",
    "  ██   █████████████  ",
    "  ███ ██████████████  ",
    "  ██████████████████  ",
    "  ██ █████████████    ",
    "  █  ████████████     ",
    "      ███████████     ",
    "       ███  ████      ",
    "       ██    ███      ",
    "              ██      ",
]
DUCK1 = [
    "                    ████████  ",
    "  █      ██████████████████  ",
    "  ██   █ ██████████████████  ",
    "  ███ ████████████████████   ",
    "  ████████████████████       ",
    "  ██ █████████████           ",
    "  █  ████████████            ",
    "       ████  ██              ",
    "       ███    █              ",
    "       ██                    ",
]
DUCK2 = [
    "                    ████████  ",
    "  █      ██████████████████  ",
    "  ██   █ ██████████████████  ",
    "  ███ ████████████████████   ",
    "  ████████████████████       ",
    "  ██ █████████████           ",
    "  █  ████████████            ",
    "       ███  ████             ",
    "       ██    ███             ",
    "              ██             ",
]
DEAD = [
    "            ████████  ",
    "          ██████████  ",
    "          █X██X█████  ",
    "          ██████████  ",
    "          ██████      ",
    "  █      ███████████  ",
    "  ██   █████████████  ",
    "  ███ ██████████████  ",
    "  ██████████████████  ",
    "  ██ █████████████    ",
    "  █  ████████████     ",
    "      ███████████     ",
    "       ████  ████     ",
    "       ███    ███     ",
]

# ─── Obstacles (Chrome style) ─────────────────────────────
CACT_S = [
    "  █  ",
    "  █  ",
    "█ █  ",
    "█ █ █",
    "█ █ █",
    " ███ ",
    "  █  ",
    "  █  ",
]
CACT_B = [
    "  █      ",
    "  █   █  ",
    "  █   █  ",
    "  █ █ █  ",
    "█ █ █ █ █",
    "█ █ █ █ █",
    "█ ███ █ █",
    " █████ █ ",
    "  █████  ",
    "  █████  ",
    "   ███   ",
]
CACT_D = [
    "  █    █ ",
    "  █    █ ",
    "█ █  █ █ ",
    "█ █  █ █ ",
    "█ ████ █ ",
    " ██████  ",
    "  █  █   ",
    "  █  █   ",
]
BIRD1 = [
    " ██      ",
    "████     ",
    " ██████  ",
    "  ██████ ",
    "   ████  ",
]
BIRD2 = [
    "   ████  ",
    "  ██████ ",
    " ██████  ",
    "████     ",
    " ██      ",
]

# ─── Constants ─────────────────────────────────────────────
GRAVITY = 0.9
JUMP_VEL = -9.5
FPS = 33  # ~30 fps via curses timeout


def overlap(a, b):
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def hbox(y, x, sprite, mx=2, my=1):
    h = len(sprite)
    w = max(len(r) for r in sprite)
    return (int(y) + my, x + mx, int(y) + h - my, x + w - mx)


def draw(win, sprite, y, x, rows, cols):
    for i, row in enumerate(sprite):
        ry = int(y) + i
        if not (0 <= ry < rows):
            continue
        for j, ch in enumerate(row):
            cx = x + j
            if ch == " " or cx < 0 or cx >= cols:
                continue
            try:
                win.addch(ry, cx, ch)
            except curses.error:
                pass


def obs_sprite(kind, frame):
    if kind == "cs":
        return CACT_S
    if kind == "cb":
        return CACT_B
    if kind == "cd":
        return CACT_D
    return BIRD1 if (frame // 4) % 2 == 0 else BIRD2


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(FPS)

    rows, cols = stdscr.getmaxyx()
    gy = rows - 4

    # state
    dy = 0.0
    dvy = 0.0
    jumping = False
    ducking = False
    alive = True
    dframe = 0
    score = 0
    hi = 0
    speed = 4
    stimer = 40
    started = False
    obstacles = []
    clouds = []

    def reset():
        nonlocal dy, dvy, jumping, ducking, alive, dframe, score, speed, stimer, obstacles, clouds
        dy = dvy = 0.0
        jumping = ducking = False
        alive = True
        dframe = score = 0
        speed = 4
        stimer = 40
        obstacles.clear()
        clouds.clear()

    def get_sprite():
        if not alive:
            return DEAD
        if ducking and not jumping:
            return DUCK1 if dframe % 6 < 3 else DUCK2
        return RUN1 if dframe % 6 < 3 else RUN2

    while True:
        # ── collect input (drain queue to prevent lag) ──
        key = -1
        jump_pressed = False
        duck_pressed = False
        while True:
            k = stdscr.getch()
            if k == -1:
                break
            if k in (ord("q"), ord("Q")):
                return
            if k in (ord(" "), curses.KEY_UP):
                jump_pressed = True
            if k == curses.KEY_DOWN:
                duck_pressed = True

        rows, cols = stdscr.getmaxyx()
        gy = rows - 4
        stdscr.erase()

        # ── title screen ──
        if not started:
            t = [
                "╔══════════════════════════════════════════╗",
                "║       T-REX  RUNNER  ·  ASCII            ║",
                "║                                          ║",
                "║   SPACE / UP  ➜  Jump                    ║",
                "║   DOWN        ➜  Duck                    ║",
                "║   Q           ➜  Quit                    ║",
                "║                                          ║",
                "║       Press SPACE to start!               ║",
                "╚══════════════════════════════════════════╝",
            ]
            ty = rows // 2 - len(t) // 2
            for i, ln in enumerate(t):
                if 0 <= ty + i < rows:
                    tx = max(0, cols // 2 - len(ln) // 2)
                    try:
                        stdscr.addnstr(ty + i, tx, ln, cols - tx - 1)
                    except curses.error:
                        pass
            sp = get_sprite()
            draw(stdscr, sp, gy - len(sp), 2, rows, cols)
            try:
                stdscr.addnstr(gy, 0, ("▓" * (cols - 1)), cols - 1)
            except curses.error:
                pass
            if jump_pressed:
                started = True
                jumping = True
                dvy = JUMP_VEL
            stdscr.refresh()
            continue

        # ── game over screen ──
        if not alive:
            sp = get_sprite()
            draw(stdscr, sp, int(dy), 2, rows, cols)
            for ox, oy, ok, of in obstacles:
                draw(stdscr, obs_sprite(ok, of), oy, ox, rows, cols)
            try:
                stdscr.addnstr(gy, 0, ("▓" * (cols - 1)), cols - 1)
            except curses.error:
                pass
            go = [
                "╔═══════════════════════════╗",
                "║        GAME  OVER         ║",
                f"║   Score: {score:<16} ║",
                f"║   High:  {hi:<16} ║",
                "║                           ║",
                "║  SPACE retry  ·  Q quit   ║",
                "╚═══════════════════════════╝",
            ]
            gy2 = rows // 2 - len(go) // 2
            for i, ln in enumerate(go):
                if 0 <= gy2 + i < rows:
                    gx = max(0, cols // 2 - len(ln) // 2)
                    try:
                        stdscr.addnstr(gy2 + i, gx, ln, cols - gx - 1)
                    except curses.error:
                        pass
            hud = f" {score}  HI:{hi} "
            try:
                stdscr.addnstr(0, max(0, cols - len(hud) - 1), hud, cols - 1)
            except curses.error:
                pass
            if jump_pressed:
                reset()
                jumping = True
                dvy = JUMP_VEL
            stdscr.refresh()
            continue

        # ── handle input ──
        if jump_pressed and not jumping:
            jumping = True
            dvy = JUMP_VEL
            ducking = False
        ducking = duck_pressed

        # ── update ──
        dframe += 1
        score += 1
        if score > hi:
            hi = score
        speed = min(11, 4 + score // 250)

        # dino physics
        if jumping:
            dvy += GRAVITY
            dy += dvy
            sp = get_sprite()
            rest = gy - len(sp)
            if dy >= rest:
                dy = rest
                dvy = 0
                jumping = False
        else:
            sp = get_sprite()
            dy = gy - len(sp)

        # spawn obstacles — guarantee safe gap for jumping
        #
        # Jump physics: v0 = -9.5, g = 0.9
        #   air time ≈ 2 * |v0| / g ≈ 21 frames
        #   horizontal distance in air = air_time * speed
        # The dino needs: land + react + jump + clear next obstacle
        #   min_gap_pixels = speed * (air_frames + react_frames)
        #   react_frames = ~8 at low speed, ~6 at high speed
        #
        JUMP_AIR_FRAMES = 21
        REACT_FRAMES = 8
        min_gap = speed * (JUMP_AIR_FRAMES + REACT_FRAMES)
        # also add obstacle width so gap is measured edge-to-edge
        min_gap += 12

        # find the rightmost obstacle edge
        rightmost_edge = -999
        for o in obstacles:
            s = obs_sprite(o[2], o[3])
            edge = o[0] + max(len(r) for r in s)
            if edge > rightmost_edge:
                rightmost_edge = edge

        # only attempt spawn when timer fires
        stimer -= speed
        if stimer <= 0:
            # the new obstacle spawns at cols+3; check gap from rightmost
            spawn_x = cols + 3
            gap = spawn_x - rightmost_edge

            if gap >= min_gap:
                kinds = ["cs", "cb", "cd"]
                if score > 250:
                    kinds.append("bird")
                k = random.choice(kinds)
                if k == "bird":
                    # low bird = jump over, high bird = duck under
                    boy = gy - len(BIRD1) - random.choice([1, 10])
                    obstacles.append([cols + 3, boy, k, 0])
                else:
                    s = obs_sprite(k, 0)
                    obstacles.append([cols + 3, gy - len(s), k, 0])
                # next spawn: randomize but enforce minimum frames
                min_timer = max(15, min_gap // speed)
                max_timer = min_timer + 25
                stimer = random.randint(min_timer, max_timer)
            else:
                # not safe yet — retry next frame
                stimer = 1

        # move obstacles & prune
        new_obs = []
        for o in obstacles:
            o[0] -= speed
            o[3] += 1
            s = obs_sprite(o[2], o[3])
            if o[0] + max(len(r) for r in s) > 0:
                new_obs.append(o)
        obstacles = new_obs

        # clouds
        if random.random() < 0.012:
            clouds.append([cols + 2, random.randint(1, max(2, gy // 3))])
        clouds = [[c[0] - 1, c[1]] for c in clouds if c[0] > -12]

        # collision
        sp = get_sprite()
        dbox = hbox(dy, 2, sp, mx=2, my=1)
        for o in obstacles:
            s = obs_sprite(o[2], o[3])
            if overlap(dbox, hbox(o[1], o[0], s, mx=1, my=0)):
                alive = False
                break

        # ── draw ──
        # clouds
        cloud_sprite = ["    ░░    ", " ░░░░░░░░ ", "░░░░░░░░░░"]
        for c in clouds:
            for ci, crow in enumerate(cloud_sprite):
                ry = c[1] + ci
                if 0 <= ry < rows:
                    for cj, ch in enumerate(crow):
                        cx = c[0] + cj
                        if ch != " " and 0 <= cx < cols:
                            try:
                                stdscr.addch(ry, cx, ch)
                            except curses.error:
                                pass

        for o in obstacles:
            draw(stdscr, obs_sprite(o[2], o[3]), o[1], o[0], rows, cols)

        draw(stdscr, sp, int(dy), 2, rows, cols)

        # ground line
        shift = (dframe * speed) % 4
        gchars = []
        for i in range(cols - 1):
            p = (i + shift) % 20
            if p < 2:
                gchars.append("▓")
            elif p < 4:
                gchars.append("░")
            else:
                gchars.append("▓")
        try:
            stdscr.addnstr(gy, 0, "".join(gchars), cols - 1)
        except curses.error:
            pass

        # pebble row below ground
        pebble_row = gy + 1
        if pebble_row < rows:
            pebbles = []
            for i in range(cols - 1):
                p = (i + shift * 2 + 7) % 13
                if p == 0:
                    pebbles.append(".")
                elif p == 5:
                    pebbles.append(",")
                elif p == 9:
                    pebbles.append("'")
                else:
                    pebbles.append(" ")
            try:
                stdscr.addnstr(pebble_row, 0, "".join(pebbles), cols - 1)
            except curses.error:
                pass

        # HUD
        hud = f" Score: {score}   HI: {hi}   Speed: {speed} "
        try:
            stdscr.addnstr(0, max(0, cols - len(hud) - 1), hud, cols - 1)
        except curses.error:
            pass

        stdscr.refresh()


if __name__ == "__main__":
    curses.wrapper(main)