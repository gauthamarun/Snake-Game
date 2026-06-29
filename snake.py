from tkinter import *
from enum import Enum
import random
import math

# ── Constants ─────────────────────────────────────────────
GAME_WIDTH   = 600
GAME_HEIGHT  = 600
SPACE_SIZE   = 25
BODY_PARTS   = 3
BASE_SPEED   = 120
MIN_SPEED    = 40
SPEED_STEP   = 3

BG_COLOR        = "#0a0a0f"
GRID_COLOR      = "#1a1a2e"
TEXT_COLOR      = "#e0e0e0"
HEAD_COLOR      = "#00ff88"
BODY_COLORS     = ["#00e87a", "#00d06c", "#00b85e", "#009f50", "#008742",
                   "#006f34", "#005726", "#003f18", "#00270a"]
FOOD_COLOR      = "#ff4444"
FOOD_GLOW       = "#ff8888"
PARTICLE_COLORS = ["#ff4444", "#ff8800", "#ffdd00", "#ff44aa"]

HIGH_SCORE_FILE = "highscore.txt"


# ── Helpers ───────────────────────────────────────────────
def lerp_color(c1: str, c2: str, t: float) -> str:
    """Linearly interpolate between two hex colors."""
    r1, g1, b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
    r2, g2, b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
    r = int(r1 + (r2-r1)*t)
    g = int(g1 + (g2-g1)*t)
    b = int(b1 + (b2-b1)*t)
    return f"#{r:02x}{g:02x}{b:02x}"


# ── Direction ─────────────────────────────────────────────
class Direction(Enum):
    UP    = "up"
    DOWN  = "down"
    LEFT  = "left"
    RIGHT = "right"

OPPOSITES = {
    Direction.UP:    Direction.DOWN,
    Direction.DOWN:  Direction.UP,
    Direction.LEFT:  Direction.RIGHT,
    Direction.RIGHT: Direction.LEFT,
}


# ── Particle ──────────────────────────────────────────────
class Particle:
    def __init__(self, canvas: Canvas, x: int, y: int):
        self.canvas = canvas
        angle  = random.uniform(0, 2 * math.pi)
        speed  = random.uniform(2, 6)
        self.vx    = math.cos(angle) * speed
        self.vy    = math.sin(angle) * speed
        self.x     = x + SPACE_SIZE / 2
        self.y     = y + SPACE_SIZE / 2
        self.life  = random.randint(8, 14)
        size       = random.randint(3, 6)
        color      = random.choice(PARTICLE_COLORS)
        self.id    = canvas.create_oval(
            self.x - size, self.y - size,
            self.x + size, self.y + size,
            fill=color, outline=""
        )

    def update(self) -> bool:
        """Move particle, fade it. Returns False when dead."""
        self.life -= 1
        if self.life <= 0:
            self.canvas.delete(self.id)
            return False
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.4          # gravity
        self.canvas.move(self.id, self.vx, self.vy)
        # fade by shrinking
        s = max(1, self.life // 3)
        self.canvas.coords(self.id,
            self.x - s, self.y - s,
            self.x + s, self.y + s)
        return True


# ── Snake ─────────────────────────────────────────────────
class Snake:
    def __init__(self, canvas: Canvas):
        self.canvas      = canvas
        self.coordinates = [[0, 0]] * BODY_PARTS
        self.squares     = []
        self.eye_ids     = []

        for i, (x, y) in enumerate(self.coordinates):
            color = HEAD_COLOR if i == 0 else self._body_color(i, BODY_PARTS)
            sq = canvas.create_rectangle(
                x + 1, y + 1,
                x + SPACE_SIZE - 1, y + SPACE_SIZE - 1,
                fill=color, outline="", tag="snake"
            )
            self.squares.append(sq)

        self._draw_eyes(0, 0, Direction.DOWN)

    def _body_color(self, index: int, length: int) -> str:
        t = min(index / max(length - 1, 1), 1.0)
        steps = len(BODY_COLORS)
        idx   = min(int(t * (steps - 1)), steps - 2)
        local = t * (steps - 1) - idx
        return lerp_color(BODY_COLORS[idx], BODY_COLORS[idx + 1], local)

    def _draw_eyes(self, hx: int, hy: int, direction: Direction):
        for eid in self.eye_ids:
            self.canvas.delete(eid)
        self.eye_ids = []

        s = SPACE_SIZE
        offsets = {
            Direction.RIGHT: [(s-6, 4),   (s-6, s-7)],
            Direction.LEFT:  [(3,   4),   (3,   s-7)],
            Direction.DOWN:  [(4,   s-6), (s-7, s-6)],
            Direction.UP:    [(4,   3),   (s-7, 3)],
        }
        for ox, oy in offsets[direction]:
            ex, ey = hx + ox, hy + oy
            eid = self.canvas.create_oval(
                ex, ey, ex + 4, ey + 4,
                fill="white", outline=""
            )
            self.eye_ids.append(eid)

    def refresh_colors(self):
        """Recolor all segments to update gradient after growth."""
        total = len(self.squares)
        for i, sq in enumerate(self.squares):
            color = HEAD_COLOR if i == 0 else self._body_color(i, total)
            self.canvas.itemconfig(sq, fill=color)


# ── Food ──────────────────────────────────────────────────
class Food:
    def __init__(self, canvas: Canvas, occupied: list):
        self.canvas      = canvas
        self.coordinates = self._random_position(occupied)
        self._pulse_growing = True
        self._draw()
        self._pulse()

    def _random_position(self, occupied: list) -> list:
        cols = GAME_WIDTH  // SPACE_SIZE
        rows = GAME_HEIGHT // SPACE_SIZE
        while True:
            x = random.randint(0, cols - 1) * SPACE_SIZE
            y = random.randint(0, rows - 1) * SPACE_SIZE
            if [x, y] not in occupied:
                return [x, y]

    def _draw(self):
        x, y = self.coordinates
        pad = 3
        self.glow_id = self.canvas.create_oval(
            x, y, x + SPACE_SIZE, y + SPACE_SIZE,
            fill=FOOD_GLOW, outline="", tag="food"
        )
        self.food_id = self.canvas.create_oval(
            x + pad, y + pad,
            x + SPACE_SIZE - pad, y + SPACE_SIZE - pad,
            fill=FOOD_COLOR, outline="", tag="food"
        )
        self._size = 0

    def _pulse(self):
        if not self.canvas.winfo_exists():
            return
        try:
            self.canvas.coords(self.food_id)  # raises if deleted
        except TclError:
            return

        x, y = self.coordinates
        if self._pulse_growing:
            self._size = min(self._size + 1, 3)
            if self._size >= 3:
                self._pulse_growing = False
        else:
            self._size = max(self._size - 1, 0)
            if self._size <= 0:
                self._pulse_growing = True

        pad = 3 - self._size
        self.canvas.coords(
            self.food_id,
            x + pad, y + pad,
            x + SPACE_SIZE - pad, y + SPACE_SIZE - pad
        )
        self.canvas.after(80, self._pulse)


# ── High score ────────────────────────────────────────────
def load_high_score() -> int:
    try:
        with open(HIGH_SCORE_FILE) as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0

def save_high_score(score: int) -> None:
    with open(HIGH_SCORE_FILE, "w") as f:
        f.write(str(score))


# ── Game ──────────────────────────────────────────────────
class Game:
    def __init__(self):
        self.window = Tk()
        self.window.title("Snake")
        self.window.resizable(False, False)
        self.window.configure(bg="#0a0a0f")

        self.high_score = load_high_score()
        self._build_ui()
        self._bind_keys()
        self._center_window()
        self.start()

    # ── UI ────────────────────────────────────────────────
    def _build_ui(self):
        self.score_label = Label(
            self.window,
            text=self._score_text(0),
            font=("Consolas", 16),
            bg="#0d0d1a", fg="#00ff88",
            padx=10, pady=6
        )
        self.score_label.pack(fill=X)

        self.canvas = Canvas(
            self.window,
            bg=BG_COLOR,
            height=GAME_HEIGHT,
            width=GAME_WIDTH,
            highlightthickness=2,
            highlightbackground="#00ff88"
        )
        self.canvas.pack()

    def _score_text(self, score: int) -> str:
        star = " ★" if score > 0 and score >= self.high_score else ""
        return f"  Score: {score}{star}   |   Best: {self.high_score}   |   [Space] Pause  [R] Restart"

    def _bind_keys(self):
        self.window.bind("<Left>",  lambda e: self._change_direction(Direction.LEFT))
        self.window.bind("<Right>", lambda e: self._change_direction(Direction.RIGHT))
        self.window.bind("<Up>",    lambda e: self._change_direction(Direction.UP))
        self.window.bind("<Down>",  lambda e: self._change_direction(Direction.DOWN))
        self.window.bind("<space>", lambda e: self._toggle_pause())
        self.window.bind("<r>",     lambda e: self._restart())
        self.window.bind("<R>",     lambda e: self._restart())

    def _center_window(self):
        self.window.update()
        w = self.window.winfo_width()
        h = self.window.winfo_height()
        x = (self.window.winfo_screenwidth()  - w) // 2
        y = (self.window.winfo_screenheight() - h) // 2
        self.window.geometry(f"{w}x{h}+{x}+{y}")

    # ── Grid ──────────────────────────────────────────────
    def _draw_grid(self):
        for x in range(0, GAME_WIDTH + 1, SPACE_SIZE):
            self.canvas.create_line(x, 0, x, GAME_HEIGHT,
                                    fill=GRID_COLOR, tag="grid")
        for y in range(0, GAME_HEIGHT + 1, SPACE_SIZE):
            self.canvas.create_line(0, y, GAME_WIDTH, y,
                                    fill=GRID_COLOR, tag="grid")

    # ── Game state ────────────────────────────────────────
    def start(self):
        self.score           = 0
        self.direction       = Direction.DOWN
        self._dir_queue: list[Direction] = []   # buffered inputs
        self.paused     = False
        self.running    = True
        self._after_id  = None
        self._particles: list[Particle] = []
        self._score_popups: list        = []

        self.canvas.delete(ALL)
        self._draw_grid()
        self.score_label.config(text=self._score_text(0))

        self.snake = Snake(self.canvas)
        self.food  = Food(self.canvas, self.snake.coordinates)
        self._schedule_turn()

    def _restart(self):
        if self._after_id:
            self.window.after_cancel(self._after_id)
        self.start()

    # ── Game loop ─────────────────────────────────────────
    def _schedule_turn(self):
        speed = max(MIN_SPEED, BASE_SPEED - self.score * SPEED_STEP)
        self._after_id = self.window.after(speed, self._next_turn)

    def _next_turn(self):
        if not self.running or self.paused:
            return

        # consume one buffered direction per tick
        if self._dir_queue:
            self.direction = self._dir_queue.pop(0)

        x, y = self.snake.coordinates[0]
        if   self.direction == Direction.UP:    y -= SPACE_SIZE
        elif self.direction == Direction.DOWN:  y += SPACE_SIZE
        elif self.direction == Direction.LEFT:  x -= SPACE_SIZE
        elif self.direction == Direction.RIGHT: x += SPACE_SIZE

        # wall wrap
        x = x % GAME_WIDTH
        y = y % GAME_HEIGHT

        self.snake.coordinates.insert(0, [x, y])
        sq = self.canvas.create_rectangle(
            x + 1, y + 1,
            x + SPACE_SIZE - 1, y + SPACE_SIZE - 1,
            fill=HEAD_COLOR, outline=""
        )
        self.snake.squares.insert(0, sq)

        # Recolor body segment that's no longer the head
        if len(self.snake.squares) > 1:
            self.canvas.itemconfig(
                self.snake.squares[1],
                fill=self.snake._body_color(1, len(self.snake.squares))
            )

        # Update eyes
        self.snake._draw_eyes(x, y, self.direction)

        ate = ([x, y] == self.food.coordinates)

        if ate:
            self.score += 1
            if self.score > self.high_score:
                self.high_score = self.score
                save_high_score(self.high_score)
            self.score_label.config(text=self._score_text(self.score))
            self.canvas.delete("food")
            self._spawn_particles(x, y)
            self._spawn_score_popup(x, y)
            self.food = Food(self.canvas, self.snake.coordinates)
            self.snake.refresh_colors()
        else:
            del self.snake.coordinates[-1]
            self.canvas.delete(self.snake.squares[-1])
            del self.snake.squares[-1]

        self._update_particles()

        if self._check_collisions():
            self._death_flash()
        else:
            self._schedule_turn()

    # ── Controls ──────────────────────────────────────────
    def _change_direction(self, new_dir: Direction):
        # Determine what the "current" direction will be after queued inputs
        last = self._dir_queue[-1] if self._dir_queue else self.direction
        # Only accept if not reversing, and don't queue the same direction twice
        if new_dir != OPPOSITES[last] and new_dir != last:
            self._dir_queue.append(new_dir)

    def _toggle_pause(self):
        if not self.running:
            return
        self.paused = not self.paused
        if self.paused:
            # dim overlay
            self.canvas.create_rectangle(
                0, 0, GAME_WIDTH, GAME_HEIGHT,
                fill="#000000", stipple="gray50",
                tag="pause_overlay"
            )
            self.canvas.create_text(
                GAME_WIDTH / 2, GAME_HEIGHT / 2,
                font=("Consolas", 52, "bold"),
                text="PAUSED",
                fill="#ffdd00", tag="pause_overlay"
            )
            self.canvas.create_text(
                GAME_WIDTH / 2, GAME_HEIGHT / 2 + 55,
                font=("Consolas", 18),
                text="press Space to continue",
                fill="#aaaaaa", tag="pause_overlay"
            )
        else:
            self.canvas.delete("pause_overlay")
            self._schedule_turn()

    # ── Particles ─────────────────────────────────────────
    def _spawn_particles(self, x: int, y: int):
        for _ in range(12):
            self._particles.append(Particle(self.canvas, x, y))

    def _update_particles(self):
        self._particles = [p for p in self._particles if p.update()]

    # ── Score pop ─────────────────────────────────────────
    def _spawn_score_popup(self, x: int, y: int):
        tid = self.canvas.create_text(
            x + SPACE_SIZE // 2, y,
            text="+1", font=("Consolas", 14, "bold"),
            fill="#ffdd00"
        )
        self._animate_popup(tid, 0)

    def _animate_popup(self, tid: int, step: int):
        if step >= 12:
            self.canvas.delete(tid)
            return
        self.canvas.move(tid, 0, -2)
        alpha_colors = ["#ffdd00", "#ffcc00", "#ffbb00", "#ffaa00",
                        "#ff9900", "#ff8800", "#cc6600", "#994400",
                        "#773300", "#552200", "#331100", "#110000"]
        self.canvas.itemconfig(tid, fill=alpha_colors[step])
        self.window.after(40, self._animate_popup, tid, step + 1)

    # ── Death flash ───────────────────────────────────────
    def _death_flash(self, flashes: int = 0):
        if flashes >= 6:
            self._game_over()
            return
        color = "#ff2222" if flashes % 2 == 0 else HEAD_COLOR
        for sq in self.snake.squares:
            self.canvas.itemconfig(sq, fill=color)
        self.window.after(80, self._death_flash, flashes + 1)

    # ── Collision ─────────────────────────────────────────
    def _check_collisions(self) -> bool:
        x, y = self.snake.coordinates[0]
        return [x, y] in self.snake.coordinates[1:]

    # ── Game over ─────────────────────────────────────────
    def _game_over(self):
        self.running = False
        cx, cy = GAME_WIDTH / 2, GAME_HEIGHT / 2

        # dark overlay
        self.canvas.create_rectangle(
            0, 0, GAME_WIDTH, GAME_HEIGHT,
            fill="#000000", stipple="gray75",
            tag="gameover"
        )
        self.canvas.create_text(
            cx, cy - 50,
            font=("Consolas", 58, "bold"),
            text="GAME OVER",
            fill="#ff2222", tag="gameover"
        )
        self.canvas.create_text(
            cx, cy + 20,
            font=("Consolas", 22),
            text=f"Score: {self.score}   |   Best: {self.high_score}",
            fill=TEXT_COLOR, tag="gameover"
        )
        self.canvas.create_text(
            cx, cy + 65,
            font=("Consolas", 16),
            text="Press R to restart",
            fill="#666666", tag="gameover"
        )

    # ── Run ───────────────────────────────────────────────
    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    Game().run()
