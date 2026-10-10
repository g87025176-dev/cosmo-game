
import tkinter as tk
import random
import json
import os
import time

W, H = 900, 650
SAVE_FILE = "space_save.json"

PAPER = "#fff5df"
INK = "#40334f"
WHITE = "#fffdf5"
PURPLE = "#7353a6"
CORAL = "#e76f51"
BLUE = "#dff3ff"
GREEN = "#b9fbc0"
YELLOW = "#ffe29a"
PINK = "#ffb4c2"
LAVENDER = "#e4d4ff"

DIFFICULTIES = {
    "Легка": (0.78, 5, 38),
    "Нормальна": (1.0, 3, 32),
    "Складна": (1.28, 2, 27),
    "Божевільна": (1.58, 1, 23),
}

TARGETS = [50, 100, 200, 350, 500, 1000]

ACHIEVEMENTS = {
    "Перші кроки": "Набери 10 очок",
    "Зоряний пил": "Набери 50 очок",
    "Магнат": "Збери 100 монет загалом",
    "Магніт для зірок": "Збери 20 зірок за гру",
    "Кам'яна голова": "Зіткнися з астероїдом",
    "Сердечний герой": "Підбери сердечко",
    "Переможець": "Досягни своєї цілі",
    "На межі": "Переможи на Божевільній складності",
    "Без подряпин": "Переможи без втрати життя",
    "Колекціонер": "Збери 25 монет за гру",
}


# ---------------- ЗБЕРЕЖЕННЯ ----------------

def default_save():
    return {
        "best": 0,
        "coins": 0,
        "unlocked": [],
        "upgrades": {
            "speed": 0,
            "magnet": 0,
            "shield": 0
        }
    }


def load_save():
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)

        data = default_save()
        data["best"] = max(0, int(raw.get("best", 0)))
        data["coins"] = max(0, int(raw.get("coins", 0)))

        unlocked = raw.get("unlocked", [])
        if isinstance(unlocked, list):
            data["unlocked"] = [
                item for item in unlocked
                if isinstance(item, str)
            ]

        upgrades = raw.get("upgrades", {})
        if not isinstance(upgrades, dict):
            upgrades = {}

        for key in data["upgrades"]:
            data["upgrades"][key] = max(
                0, int(upgrades.get(key, 0))
            )

        return data

    except (OSError, ValueError, TypeError, AttributeError):
        return default_save()


save = load_save()


def save_game():
    try:
        with open(SAVE_FILE + ".tmp", "w", encoding="utf-8") as f:
            json.dump(save, f, ensure_ascii=False, indent=2)

        os.replace(SAVE_FILE + ".tmp", SAVE_FILE)

    except (OSError, TypeError):
        pass


# ---------------- ВІКНО ----------------

root = tk.Tk()
root.title("Paper Space: Reboot")
root.resizable(False, False)
root.configure(bg=PAPER)

canvas = tk.Canvas(
    root,
    width=W,
    height=H,
    bg=PAPER,
    highlightthickness=0
)
canvas.pack()

screen = "menu"
difficulty = "Нормальна"
target_score = 100

score = 0
lives = 3
level = 1

player_x = W // 2
player_y = H - 75

left = False
right = False
paused = False
running = False

objects = []
player_items = []
hud_items = []
toast_items = []

stars_collected = 0
coins_run = 0
rocks_hit = 0
hearts_collected = 0

initial_lives = 3
shield_time = 0
slow_time = 0
invulnerable_time = 0
spawn_timer = 0
frame = 0
toast_until = 0
last_time = time.monotonic()


# ---------------- МАЛЮВАННЯ ----------------

def text(x, y, value, size=14, color=INK,
         bold=False, anchor="center"):
    return canvas.create_text(
        x, y,
        text=value,
        fill=color,
        anchor=anchor,
        font=("Comic Sans MS", size,
              "bold" if bold else "normal")
    )


def clear():
    canvas.delete("all")
    hud_items.clear()
    player_items.clear()
    toast_items.clear()


def paper_background():
    canvas.configure(bg=PAPER)

    for _ in range(145):
        x = random.randint(0, W)
        y = random.randint(0, H)

        canvas.create_line(
            x, y,
            x + random.randint(1, 5), y,
            fill="#efe2c9"
        )

    for x, y in [(75, 88), (760, 110)]:
        for dx, dy, r in [
            (0, 10, 16),
            (22, 0, 22),
            (44, 12, 18),
            (23, 19, 19)
        ]:
            canvas.create_oval(
                x + dx - r, y + dy - r,
                x + dx + r, y + dy + r,
                fill=BLUE,
                outline=INK,
                width=2
            )

    for _ in range(25):
        x = random.randint(20, W - 20)
        y = random.randint(60, H - 20)

        canvas.create_text(
            x, y,
            text=random.choice(["✦", "·", "✧"]),
            fill=random.choice([
                "#e9c46a", "#c4b5fd", "#f4a6a6"
            ]),
            font=("Arial", random.randint(8, 16))
        )


def button(x, y, w, h, label, action,
           color=YELLOW, size=12):

    shadow = canvas.create_rectangle(
        x, y + 3, x + w, y + h + 3,
        fill="#d8c9b2",
        outline=INK,
        width=2
    )

    rect = canvas.create_rectangle(
        x, y, x + w, y + h,
        fill=color,
        outline=INK,
        width=2
    )

    caption = text(
        x + w / 2,
        y + h / 2,
        label,
        size,
        INK,
        True
    )

    def click(event):
        action()

    def enter(event):
        canvas.itemconfigure(rect, fill="#fff0bd")

    def leave(event):
        canvas.itemconfigure(rect, fill=color)

    for item in (shadow, rect, caption):
        canvas.tag_bind(item, "<Button-1>", click)
        canvas.tag_bind(item, "<Enter>", enter)
        canvas.tag_bind(item, "<Leave>", leave)


# ---------------- ГРАФІКА ГРАВЦЯ ----------------

def draw_player():
    for item in player_items:
        canvas.delete(item)

    player_items.clear()

    x, y = player_x, player_y

    flame = canvas.create_polygon(
        x - 8, y + 17,
        x, y + 35,
        x + 8, y + 17,
        fill=random.choice([
            "#ff8c42", "#ffd166", "#ffb4a2"
        ]),
        outline=INK,
        width=2
    )

    ship = canvas.create_polygon(
        x, y - 29,
        x - 22, y + 17,
        x - 9, y + 12,
        x, y + 19,
        x + 9, y + 12,
        x + 22, y + 17,
        fill="#83a4ff",
        outline=INK,
        width=3
    )

    window = canvas.create_oval(
        x - 8, y - 8,
        x + 8, y + 8,
        fill="#dffaff",
        outline=INK,
        width=2
    )

    player_items.extend([flame, ship, window])

    if shield_time > 0:
        player_items.append(canvas.create_oval(
            x - 32, y - 35,
            x + 32, y + 35,
            outline="#38bdf8",
            width=3
        ))

    if invulnerable_time > 0 and frame % 8 < 4:
        for item in player_items:
            canvas.itemconfigure(item, state="hidden")


def draw_hud():
    for item in hud_items:
        canvas.delete(item)

    hud_items.clear()

    hud_items.extend([
        canvas.create_rectangle(
            10, 10, W - 10, 49,
            fill=WHITE,
            outline=INK,
            width=2
        ),
        text(
            105, 29,
            f"★ {score}/{target_score}",
            13, PURPLE, True
        ),
        text(
            W / 2, 29,
            f"РІВЕНЬ {level}",
            13, CORAL, True
        ),
        text(
            W - 112, 29,
            "♥ " * max(0, lives),
            13, "#e84a72", True
        ),
        text(
            W - 62, 65,
            f"Монети: {save['coins']}",
            10, INK, True
        )
    ])


# ---------------- СПОВІЩЕННЯ ----------------

def toast(message):
    global toast_until

    for item in toast_items:
        canvas.delete(item)

    toast_items.clear()

    toast_items.extend([
        canvas.create_rectangle(
            245, 58, 655, 96,
            fill="#fff0a8",
            outline=INK,
            width=2
        ),
        text(
            W / 2, 77,
            message,
            11, INK, True
        )
    ])

    toast_until = time.monotonic() + 2


# ---------------- ДОСЯГНЕННЯ ----------------

def unlock(name):
    if name not in save["unlocked"]:
        save["unlocked"].append(name)
        save_game()

        if screen == "game":
            toast("🏅 " + name)


def check_achievements(won=False):
    if score >= 10:
        unlock("Перші кроки")

    if score >= 50:
        unlock("Зоряний пил")

    if save["coins"] >= 100:
        unlock("Магнат")

    if stars_collected >= 20:
        unlock("Магніт для зірок")

    if rocks_hit > 0:
        unlock("Кам'яна голова")

    if hearts_collected > 0:
        unlock("Сердечний герой")

    if coins_run >= 25:
        unlock("Колекціонер")

    if won:
        unlock("Переможець")

        if difficulty == "Божевільна":
            unlock("На межі")

        if lives >= initial_lives:
            unlock("Без подряпин")


# ---------------- ПРЕДМЕТИ ----------------

def spawn_object():
    x = random.randint(35, W - 35)
    roll = random.random()

    if roll < 0.56:
        kind = "star"
        symbol = "★"
        color = random.choice([
            "#ff7b7b", "#ffd166",
            "#8cafff", "#c4b5fd"
        ])

    elif roll < 0.73:
        kind, symbol, color = "rock", "●", "#b4a7c9"

    elif roll < 0.82:
        kind, symbol, color = "heart", "♥", "#f25f7a"

    elif roll < 0.93:
        kind, symbol, color = "coin", "¢", "#e0a51a"

    elif roll < 0.98:
        kind, symbol, color = "shield", "⬡", "#168aad"

    else:
        kind, symbol, color = "slow", "❄", "#4cc9f0"

    item = canvas.create_text(
        x, -25,
        text=symbol,
        fill=color,
        font=("Arial", 27, "bold")
    )

    speed_multiplier = DIFFICULTIES[difficulty][0]
    speed = (
        random.uniform(2.0, 3.5) * speed_multiplier
        + level * 0.12
    )

    objects.append({
        "x": float(x),
        "y": -25.0,
        "kind": kind,
        "item": item,
        "speed": speed
    })


def clear_objects():
    for obj in objects:
        canvas.delete(obj["item"])

    objects.clear()


def collect(obj):
    global score, lives
    global stars_collected, coins_run
    global rocks_hit, hearts_collected
    global shield_time, slow_time, invulnerable_time

    kind = obj["kind"]

    if kind == "star":
        score += 10
        stars_collected += 1

    elif kind == "coin":
        save["coins"] += 1
        coins_run += 1
        save_game()

    elif kind == "heart":
        lives = min(initial_lives + 2, lives + 1)
        hearts_collected += 1

    elif kind == "shield":
        shield_time = 220 + save["upgrades"]["shield"] * 45
        toast("🛡 Щит активовано!")

    elif kind == "slow":
        slow_time = 150
        toast("❄ Час сповільнився!")

    elif kind == "rock":
        rocks_hit += 1

        if shield_time > 0:
            shield_time = 0
            toast("🛡 Щит поглинув удар!")

        elif invulnerable_time <= 0:
            lives -= 1
            invulnerable_time = 70
            toast("💥 Мінус життя!")

    check_achievements()


# ---------------- МЕНЮ ----------------

def menu():
    global screen, running, paused, left, right

    screen = "menu"
    running = False
    paused = False
    left = False
    right = False

    clear()
    clear_objects()
    paper_background()

    canvas.create_rectangle(
        115, 35, 785, 620,
        fill=WHITE,
        outline=INK,
        width=3
    )

    text(W / 2, 77, "PAPER SPACE", 32, PURPLE, True)
    text(
        W / 2, 115,
        "REBOOT ✦ КОСМІЧНА ПРИГОДА",
        15, CORAL, True
    )
    text(
        W / 2, 153,
        "ОБЕРИ СКЛАДНІСТЬ",
        12, INK, True
    )

    colors = [GREEN, YELLOW, PINK, LAVENDER]

    for i, name in enumerate(DIFFICULTIES):
        button(
            137 + i * 158, 174,
            150, 39, name,
            lambda n=name: choose_difficulty(n),
            "#ffd166" if difficulty == name else colors[i],
            10
        )

    text(
        W / 2, 237,
        "СКІЛЬКИ ОЧОК ДО ПЕРЕМОГИ?",
        12, INK, True
    )

    for i, amount in enumerate(TARGETS):
        button(
            139 + i * 104, 257,
            90, 36, str(amount),
            lambda a=amount: choose_target(a),
            "#ffd166" if target_score == amount else BLUE,
            10
        )

    text(
        W / 2, 316,
        f"Складність: {difficulty}   •   Ціль: {target_score}",
        12, INK, True
    )

    text(
        W / 2, 341,
        f"Монети: {save['coins']}   •   Рекорд: {save['best']}",
        12, PURPLE, True
    )

    text(
        W / 2, 369,
        "Лови зірки, збирай монети та уникай астероїдів!",
        11, INK
    )

    button(
        300, 390, 300, 47,
        "ПОЧАТИ ГРУ",
        start_game, YELLOW, 13
    )

    button(
        300, 447, 145, 42,
        "МАГАЗИН",
        shop, GREEN, 11
    )

    button(
        455, 447, 145, 42,
        "ДОСЯГНЕННЯ",
        achievement_screen, LAVENDER, 10
    )

    button(
        300, 500, 300, 40,
        "ЯК ГРАТИ",
        help_screen, BLUE, 11
    )

    text(
        W / 2, 572,
        "Керування: ← → / A D   •   P — пауза   •   Esc — меню",
        10, "#776b82"
    )

    text(
        W / 2, 594,
        f"Покращення: швидкість {save['upgrades']['speed']} • "
        f"магніт {save['upgrades']['magnet']} • "
        f"щит {save['upgrades']['shield']}",
        10, "#776b82"
    )


def choose_difficulty(name):
    global difficulty
    difficulty = name
    menu()


def choose_target(amount):
    global target_score
    target_score = amount
    menu()


# ---------------- ІНСТРУКЦІЯ ----------------

def help_screen():
    global screen

    screen = "help"
    clear()
    paper_background()

    text(W / 2, 75, "ЯК ГРАТИ", 27, PURPLE, True)

    lines = [
        "★ Зірка: +10 очок",
        "¢ Монета: +1 монета для магазину",
        "♥ Сердечко: +1 життя",
        "⬡ Щит: поглинає удар астероїда",
        "❄ Сніжинка: сповільнює предмети",
        "● Астероїд: забирає життя без щита",
        "",
        "Рухайся стрілками ← → або клавішами A / D.",
        "P — пауза. Esc — повернення в меню."
    ]

    y = 145

    for line in lines:
        text(
            W / 2, y, line,
            13 if line else 8, INK
        )
        y += 36

    button(
        320, 535, 260, 45,
        "У МЕНЮ",
        menu, BLUE
    )


# ---------------- МАГАЗИН ----------------

def shop():
    global screen

    screen = "shop"
    clear()
    paper_background()

    text(
        W / 2, 55,
        "МАГАЗИН ПОКРАЩЕНЬ",
        24, PURPLE, True
    )

    text(
        W / 2, 88,
        f"Твої монети: {save['coins']}",
        13, INK, True
    )

    items = [
        ("speed", "Швидкісна ракета",
         "Трохи швидший рух", 30),
        ("magnet", "Магніт зірок",
         "Притягує корисні предмети", 40),
        ("shield", "Посилений щит",
         "Збільшує тривалість щита", 50),
    ]

    for i, (key, name, desc, base_price) in enumerate(items):
        y = 125 + i * 112
        lvl = save["upgrades"][key]
        price = base_price * (lvl + 1)

        canvas.create_rectangle(
            145, y, 755, y + 91,
            fill=WHITE,
            outline=INK,
            width=2
        )

        text(
            170, y + 25,
            name, 14, INK, True, "w"
        )

        text(
            170, y + 51,
            f"{desc} • Рівень {lvl}",
            11, INK, False, "w"
        )

        text(
            170, y + 72,
            f"Наступна ціна: {price} монет",
            10, PURPLE, True, "w"
        )

        button(
            570, y + 24,
            155, 43,
            f"КУПИТИ · {price}",
            lambda k=key, p=price: buy_upgrade(k, p),
            YELLOW, 9
        )

    button(
        320, 490, 260, 43,
        "У ГОЛОВНЕ МЕНЮ",
        menu, BLUE, 11
    )

    text(
        W / 2, 557,
        "Ціна зростає після кожного покращення.",
        11, "#776b82"
    )


def buy_upgrade(key, price):
    if save["coins"] < price:
        shop()
        toast("Не вистачає монет!")
        return

    save["coins"] -= price
    save["upgrades"][key] += 1

    save_game()
    shop()


# ---------------- ДОСЯГНЕННЯ ----------------

def achievement_screen():
    global screen

    screen = "achievements"
    clear()
    paper_background()

    text(
        W / 2, 45,
        "КНИЖКА ДОСЯГНЕНЬ",
        23, PURPLE, True
    )

    y = 88

    for name, desc in ACHIEVEMENTS.items():
        got = name in save["unlocked"]

        canvas.create_rectangle(
            135, y, 765, y + 42,
            fill="#c9f2d0" if got else WHITE,
            outline=INK,
            width=2
        )

        text(
            153, y + 13,
            ("✓ " if got else "☆ ") + name,
            11, INK, True, "w"
        )

        text(
            153, y + 30,
            desc, 9, INK, False, "w"
        )

        y += 46

    button(
        320, 560, 260, 42,
        "НАЗАД",
        menu, BLUE, 11
    )


# ---------------- ПОЧАТОК ГРИ ----------------

def start_game():
    global screen, score, lives, level
    global player_x, player_y
    global left, right, paused, running
    global stars_collected, coins_run
    global rocks_hit, hearts_collected
    global shield_time, slow_time, spawn_timer
    global initial_lives, invulnerable_time
    global frame, last_time, toast_until

    screen = "game"

    score = 0
    level = 1
    lives = DIFFICULTIES[difficulty][1]
    initial_lives = lives

    player_x = W // 2
    player_y = H - 75

    left = False
    right = False
    paused = False

    stars_collected = 0
    coins_run = 0
    rocks_hit = 0
    hearts_collected = 0

    shield_time = 0
    slow_time = 0
    spawn_timer = 0
    invulnerable_time = 0
    frame = 0
    toast_until = 0

    running = True

    clear()
    clear_objects()
    paper_background()
    draw_player()
    draw_hud()

    last_time = time.monotonic()

    game_loop()


# ---------------- РЕЗУЛЬТАТ ----------------

def end_screen(won):
    global screen, running, paused, left, right

    screen = "result"
    running = False
    paused = False
    left = False
    right = False

    save["best"] = max(save["best"], score)

    if won:
        check_achievements(won=True)

    save_game()

    clear()
    paper_background()

    canvas.create_rectangle(
        180, 95, 720, 585,
        fill=WHITE,
        outline=INK,
        width=3
    )

    text(
        W / 2, 145,
        "ПЕРЕМОГА!" if won else "РАКЕТА ВТОМИЛАСЯ",
        25, GREEN if won else CORAL, True
    )

    text(
        W / 2, 205,
        f"Результат: {score} очок",
        17, INK, True
    )

    text(
        W / 2, 239,
        f"Монет за гру: {coins_run}",
        13, INK
    )

    text(
        W / 2, 270,
        f"Рекорд: {save['best']}   •   Рівень: {level}",
        13, PURPLE, True
    )

    text(
        W / 2, 302,
        f"Зірки: {stars_collected}   •   Астероїди: {rocks_hit}",
        11, INK
    )

    button(
        300, 340, 300, 45,
        "ГРАТИ ЩЕ",
        start_game, GREEN, 12
    )

    button(
        300, 394, 300, 42,
        "МАГАЗИН",
        shop, YELLOW, 11
    )

    button(
        300, 445, 300, 42,
        "ДОСЯГНЕННЯ",
        achievement_screen, LAVENDER, 11
    )

    button(
        300, 496, 300, 42,
        "ГОЛОВНЕ МЕНЮ",
        menu, BLUE, 11
    )


# ---------------- ПАУЗА ----------------

def toggle_pause():
    global paused, last_time

    if screen != "game" or not running:
        return

    paused = not paused

    if paused:
        canvas.create_rectangle(
            230, 240, 670, 385,
            fill=WHITE,
            outline=INK,
            width=3,
            tags="pause_overlay"
        )

        canvas.create_text(
            W / 2, 285,
            text="ПАУЗА",
            fill=CORAL,
            font=("Comic Sans MS", 26, "bold"),
            tags="pause_overlay"
        )

        canvas.create_text(
            W / 2, 325,
            text="Натисни P, щоб продовжити",
            fill=INK,
            font=("Comic Sans MS", 12),
            tags="pause_overlay"
        )

    else:
        canvas.delete("pause_overlay")
        last_time = time.monotonic()


# ---------------- ІГРОВИЙ ЦИКЛ ----------------

def game_loop():
    global player_x, score, lives, level
    global spawn_timer, running, paused
    global shield_time, slow_time
    global frame, last_time, invulnerable_time

    if not running or screen != "game":
        return

    if paused:
        root.after(40, game_loop)
        return

    frame += 1

    dt = min(
        1.8,
        max(
            0.6,
            (time.monotonic() - last_time) / 0.025
        )
    )

    last_time = time.monotonic()

    move_speed = 7 + min(
        5, save["upgrades"]["speed"] * 0.8
    )

    if left:
        player_x -= move_speed * dt

    if right:
        player_x += move_speed * dt

    player_x = max(30, min(W - 30, player_x))

    if shield_time > 0:
        shield_time -= 1

    if slow_time > 0:
        slow_time -= 1

    if invulnerable_time > 0:
        invulnerable_time -= 1

    spawn_timer += 1

    spawn_delay = max(
        10,
        DIFFICULTIES[difficulty][2] - (level - 1)
    )

    if spawn_timer >= spawn_delay:
        spawn_object()
        spawn_timer = 0

    remaining = []
    magnet_level = save["upgrades"]["magnet"]

    for obj in objects:
        if (
            magnet_level
            and obj["kind"] in ("star", "coin", "heart")
            and abs(obj["y"] - player_y) < 150
        ):
            pull = min(0.12, 0.025 * magnet_level)
            obj["x"] += (player_x - obj["x"]) * pull

        obj["y"] += obj["speed"] * dt * (
            0.48 if slow_time > 0 else 1
        )

        canvas.coords(
            obj["item"],
            obj["x"],
            obj["y"]
        )

        if (
            abs(obj["x"] - player_x) < 30
            and abs(obj["y"] - player_y) < 32
        ):
            canvas.delete(obj["item"])
            collect(obj)

        elif obj["y"] < H + 35:
            remaining.append(obj)

        else:
            canvas.delete(obj["item"])

    objects[:] = remaining

    level = 1 + score // 100

    draw_player()
    draw_hud()

    if toast_until and time.monotonic() > toast_until:
        for item in toast_items:
            canvas.delete(item)

        toast_items.clear()
        toast_until = 0

    if score >= target_score:
        end_screen(True)
        return

    if lives <= 0:
        end_screen(False)
        return

    root.after(25, game_loop)


# ---------------- КЕРУВАННЯ ----------------

def key_down(event):
    global left, right

    key = event.keysym.lower()

    if key in ("left", "a"):
        left = True

    elif key in ("right", "d"):
        right = True

    elif key == "p":
        toggle_pause()

    elif key == "escape":
        menu()


def key_up(event):
    global left, right

    key = event.keysym.lower()

    if key in ("left", "a"):
        left = False

    elif key in ("right", "d"):
        right = False


def on_close():
    save_game()
    root.destroy()


# bind_all допомагає ловити клавіші навіть після кліків мишкою
root.bind_all("<KeyPress>", key_down)
root.bind_all("<KeyRelease>", key_up)
root.protocol("WM_DELETE_WINDOW", on_close)

menu()
root.mainloop()
