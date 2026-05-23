import json
import math
import sys
from pathlib import Path

import pygame


SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
GRAVITY = 1800.0
BIKE_RADIUS = 20
COIN_RADIUS = 12
CHECKPOINT_RADIUS = 18
CRASH_RESPAWN_DELAY = 1.0
MAX_RACE_TIME_SECONDS = 300
DEFAULT_LEVEL_PATH = Path(__file__).resolve().parent / "levels" / "first_level.json"


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def load_level(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))

    terrain = [(float(x), float(y)) for x, y in data["terrain"]]
    terrain.sort(key=lambda point: point[0])

    finish_x = float(data["finish_x"])
    start_x = float(data.get("start_x", terrain[0][0]))

    coins = [
        {"x": float(x), "y": float(y), "collected": False}
        for x, y in data.get("coins", [])
    ]

    checkpoints = [
        {"x": float(x), "active": False}
        for x in sorted(data.get("checkpoints", []))
    ]

    return {
        "terrain": terrain,
        "finish_x": finish_x,
        "start_x": start_x,
        "coins": coins,
        "checkpoints": checkpoints,
    }


def terrain_height_at(points: list[tuple[float, float]], x: float) -> float:
    if x <= points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]

    for index in range(len(points) - 1):
        x1, y1 = points[index]
        x2, y2 = points[index + 1]
        if x1 <= x <= x2:
            t = (x - x1) / (x2 - x1)
            return y1 + (y2 - y1) * t

    return points[-1][1]


def format_race_time(milliseconds: int) -> str:
    total_cs = max(0, milliseconds // 10)
    minutes = total_cs // 6000
    seconds = (total_cs % 6000) // 100
    centiseconds = total_cs % 100
    return f"{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


class Bike:
    def __init__(self, terrain: list[tuple[float, float]], level_length: float, start_x: float) -> None:
        self.terrain = terrain
        self.level_length = level_length
        self.default_start_x = start_x
        self.reset(start_x)

    def reset(self, spawn_x: float | None = None) -> None:
        spawn = self.default_start_x if spawn_x is None else spawn_x
        self.x = clamp(spawn, 0.0, self.level_length)
        self.y = terrain_height_at(self.terrain, self.x) - BIKE_RADIUS
        self.vx = 0.0
        self.vy = 0.0
        self.angle = 0.0
        self.angular_velocity = 0.0
        self.on_ground = True
        self.crashed = False
        self.win = False

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper) -> None:
        if self.crashed or self.win:
            return

        accel = 0.0
        if keys[pygame.K_RIGHT]:
            accel += 1100.0
        if keys[pygame.K_LEFT]:
            accel -= 950.0
        self.vx += accel * dt
        if self.on_ground:
            self.vx *= 0.985
        self.vx = clamp(self.vx, -450.0, 760.0)

        if keys[pygame.K_UP]:
            self.angular_velocity -= 5.5 * dt * 60
        if keys[pygame.K_DOWN]:
            self.angular_velocity += 5.5 * dt * 60
        self.angular_velocity *= 0.98
        self.angle += self.angular_velocity * dt

        if keys[pygame.K_SPACE] and self.on_ground:
            self.vy = -650.0
            self.on_ground = False

        if not self.on_ground:
            self.vy += GRAVITY * dt

        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x = clamp(self.x, 0.0, self.level_length)

        ground = terrain_height_at(self.terrain, self.x)
        if self.y + BIKE_RADIUS >= ground:
            impact_speed = abs(self.vy)
            self.y = ground - BIKE_RADIUS
            self.vy = 0.0
            self.on_ground = True
            self.angular_velocity *= 0.9
            if impact_speed > 900.0 or abs(self.angle) > 1.2:
                self.crashed = True
        else:
            self.on_ground = False

        if self.y > SCREEN_HEIGHT + 250:
            self.crashed = True

    def draw(self, screen: pygame.Surface, camera_x: float) -> None:
        center = (int(self.x - camera_x), int(self.y))
        wheel_offset_x = 28
        wheel_offset_y = 14

        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)

        def rot(off_x: float, off_y: float) -> tuple[int, int]:
            rx = off_x * cos_a - off_y * sin_a
            ry = off_x * sin_a + off_y * cos_a
            return int(center[0] + rx), int(center[1] + ry)

        rear = rot(-wheel_offset_x, wheel_offset_y)
        front = rot(wheel_offset_x, wheel_offset_y)
        body = rot(0, -8)

        pygame.draw.circle(screen, (20, 20, 20), rear, 14)
        pygame.draw.circle(screen, (20, 20, 20), front, 14)
        pygame.draw.circle(screen, (170, 170, 170), rear, 8)
        pygame.draw.circle(screen, (170, 170, 170), front, 8)
        pygame.draw.line(screen, (220, 80, 80), rear, body, 5)
        pygame.draw.line(screen, (220, 80, 80), body, front, 5)
        pygame.draw.line(screen, (230, 230, 230), rear, front, 3)


def draw_sky(screen: pygame.Surface, animation_time: float) -> None:
    screen.fill((62, 132, 235))
    pulse = 0.5 + 0.5 * math.sin(animation_time * 0.25)
    clouds = [
        (0.08, 0.12, 260, 170),
        (0.42, 0.30, 300, 190),
        (0.78, 0.16, 220, 150),
        (0.22, 0.74, 290, 175),
        (0.62, 0.66, 250, 165),
        (0.93, 0.84, 280, 185),
    ]

    for nx, ny, base_r, drift in clouds:
        x = int(nx * SCREEN_WIDTH + math.sin(animation_time * 0.08 + nx * 11.0) * drift * 0.1)
        y = int(ny * SCREEN_HEIGHT + math.cos(animation_time * 0.09 + ny * 8.0) * drift * 0.08)
        for index, alpha in enumerate((60, 42, 28, 16)):
            radius = int(base_r * (1.0 - index * 0.18) * (0.9 + pulse * 0.2))
            glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (180, 215, 255, alpha), (radius, radius), radius)
            screen.blit(glow, (x - radius, y - radius))


def draw_terrain(screen: pygame.Surface, terrain: list[tuple[float, float]], camera_x: float) -> None:
    poly = [(int(x - camera_x), int(y)) for x, y in terrain]
    if len(poly) < 2:
        return

    fill = poly + [(poly[-1][0], SCREEN_HEIGHT), (poly[0][0], SCREEN_HEIGHT)]
    terrain_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    pygame.draw.polygon(terrain_layer, (171, 45, 26), fill)

    brick_w = 52
    brick_h = 24
    mortar = (231, 183, 150, 128)
    for row_y in range(0, SCREEN_HEIGHT + brick_h, brick_h):
        pygame.draw.line(terrain_layer, mortar, (0, row_y), (SCREEN_WIDTH, row_y), 2)
    for row in range(0, SCREEN_HEIGHT // brick_h + 2):
        row_y = row * brick_h
        offset = 0 if row % 2 == 0 else brick_w // 2
        for col_x in range(-brick_w, SCREEN_WIDTH + brick_w, brick_w):
            x = col_x + offset
            pygame.draw.line(terrain_layer, mortar, (x, row_y), (x, row_y + brick_h), 2)

    screen.blit(terrain_layer, (0, 0))
    pygame.draw.lines(screen, (36, 117, 24), False, poly, 14)
    pygame.draw.lines(screen, (88, 222, 58), False, poly, 8)


def draw_trees(screen: pygame.Surface, terrain: list[tuple[float, float]], camera_x: float) -> None:
    tree_positions = [500.0, 1550.0, 2450.0, 3500.0, 4650.0, 5550.0]
    for index, tree_x in enumerate(tree_positions):
        px = int(tree_x - camera_x)
        if px < -220 or px > SCREEN_WIDTH + 220:
            continue

        ground_y = terrain_height_at(terrain, tree_x)
        scale = 0.82 + (index % 3) * 0.14
        trunk_w = int(34 * scale)
        trunk_h = int(104 * scale)
        trunk_top = int(ground_y - trunk_h)
        trunk_rect = pygame.Rect(px - trunk_w // 2, trunk_top, trunk_w, trunk_h)
        pygame.draw.rect(screen, (173, 87, 31), trunk_rect, border_radius=max(8, trunk_w // 3))
        pygame.draw.rect(screen, (85, 45, 20), trunk_rect, 2, border_radius=max(8, trunk_w // 3))

        canopy_center = (px, trunk_top - int(20 * scale))
        canopy_radius = int(52 * scale)
        for dx, dy, radius in (
            (-40, 8, canopy_radius),
            (0, -14, canopy_radius + 8),
            (38, 10, canopy_radius),
            (0, 22, canopy_radius + 4),
        ):
            pygame.draw.circle(
                screen,
                (56, 150, 42),
                (canopy_center[0] + int(dx * scale), canopy_center[1] + int(dy * scale)),
                max(20, int(radius * scale)),
            )
            pygame.draw.circle(
                screen,
                (16, 70, 16),
                (canopy_center[0] + int(dx * scale), canopy_center[1] + int(dy * scale)),
                max(20, int(radius * scale)),
                2,
            )


def draw_collectibles(
    screen: pygame.Surface,
    coins: list[dict],
    checkpoints: list[dict],
    terrain: list[tuple[float, float]],
    camera_x: float,
) -> None:
    for coin in coins:
        if coin["collected"]:
            continue
        cx = int(coin["x"] - camera_x)
        cy = int(coin["y"])
        if -40 <= cx <= SCREEN_WIDTH + 40:
            pygame.draw.circle(screen, (204, 30, 26), (cx, cy), COIN_RADIUS)
            pygame.draw.circle(screen, (244, 95, 86), (cx - 3, cy - 3), 5)
            pygame.draw.line(screen, (76, 50, 24), (cx, cy - 10), (cx + 1, cy - 15), 2)
            pygame.draw.ellipse(screen, (74, 165, 54), pygame.Rect(cx + 1, cy - 16, 8, 5))

    for checkpoint in checkpoints:
        x = checkpoint["x"]
        y = terrain_height_at(terrain, x)
        px = int(x - camera_x)
        py = int(y)
        if -30 <= px <= SCREEN_WIDTH + 30:
            color = (40, 200, 90) if checkpoint["active"] else (80, 80, 80)
            pygame.draw.line(screen, color, (px, py - 56), (px, py - 6), 4)
            pygame.draw.circle(screen, color, (px, py - 60), CHECKPOINT_RADIUS // 2)


def main() -> int:
    pygame.init()
    pygame.display.set_caption("ElmaClone - v1.1")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 24)
    small_font = pygame.font.SysFont("consolas", 20)

    level = load_level(DEFAULT_LEVEL_PATH)
    terrain = level["terrain"]
    finish_x = level["finish_x"]
    coins = level["coins"]
    checkpoints = level["checkpoints"]

    bike = Bike(terrain, finish_x, level["start_x"])
    checkpoint_spawn_x = level["start_x"]
    crash_timer = 0.0
    race_start_ms = pygame.time.get_ticks()
    finish_elapsed_ms: int | None = None

    def reset_level_state() -> None:
        nonlocal checkpoint_spawn_x, crash_timer, race_start_ms, finish_elapsed_ms
        checkpoint_spawn_x = level["start_x"]
        for coin in coins:
            coin["collected"] = False
        for checkpoint in checkpoints:
            checkpoint["active"] = False
        bike.reset(level["start_x"])
        crash_timer = 0.0
        race_start_ms = pygame.time.get_ticks()
        finish_elapsed_ms = None

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                reset_level_state()

        keys = pygame.key.get_pressed()
        bike.update(dt, keys)

        if bike.crashed:
            crash_timer += dt
            if crash_timer >= CRASH_RESPAWN_DELAY:
                bike.reset(checkpoint_spawn_x)
                crash_timer = 0.0
        else:
            crash_timer = 0.0

            for checkpoint in checkpoints:
                if not checkpoint["active"] and bike.x >= checkpoint["x"]:
                    checkpoint["active"] = True
                    checkpoint_spawn_x = checkpoint["x"]

            for coin in coins:
                if coin["collected"]:
                    continue
                dx = bike.x - coin["x"]
                dy = bike.y - coin["y"]
                if dx * dx + dy * dy <= (BIKE_RADIUS + COIN_RADIUS) ** 2:
                    coin["collected"] = True

        collected = sum(1 for coin in coins if coin["collected"])
        total_coins = len(coins)

        if not bike.crashed and bike.x >= finish_x - 30 and collected == total_coins:
            if not bike.win:
                finish_elapsed_ms = pygame.time.get_ticks() - race_start_ms
            bike.win = True

        camera_x = clamp(bike.x - SCREEN_WIDTH * 0.35, 0.0, max(finish_x - SCREEN_WIDTH, 0.0))

        draw_sky(screen, pygame.time.get_ticks() / 1000.0)
        draw_terrain(screen, terrain, camera_x)
        draw_trees(screen, terrain, camera_x)
        draw_collectibles(screen, coins, checkpoints, terrain, camera_x)
        bike.draw(screen, camera_x)

        finish_screen_x = int(finish_x - camera_x)
        pygame.draw.line(screen, (255, 255, 255), (finish_screen_x, 0), (finish_screen_x, SCREEN_HEIGHT), 3)

        speed_text = font.render(f"Speed: {int(bike.vx)}", True, (14, 26, 50))
        coins_text = font.render(f"Apples: {collected}/{total_coins}", True, (14, 26, 50))
        screen.blit(speed_text, (20, 16))
        screen.blit(coins_text, (20, 48))

        elapsed_ms = finish_elapsed_ms
        if elapsed_ms is None:
            elapsed_ms = pygame.time.get_ticks() - race_start_ms
        elapsed_ms = min(elapsed_ms, MAX_RACE_TIME_SECONDS * 1000)
        timer_text = font.render(format_race_time(elapsed_ms), True, (20, 45, 90))
        timer_bg = pygame.Surface((timer_text.get_width() + 22, timer_text.get_height() + 10), pygame.SRCALPHA)
        timer_bg.fill((225, 238, 255, 120))
        timer_x = SCREEN_WIDTH - timer_bg.get_width() - 20
        timer_y = 18
        screen.blit(timer_bg, (timer_x, timer_y))
        screen.blit(timer_text, (timer_x + 11, timer_y + 5))

        controls = small_font.render(
            "LEFT/RIGHT move  UP/DOWN tilt  SPACE jump  R full restart",
            True,
            (20, 20, 30),
        )
        screen.blit(controls, (20, 80))

        if bike.crashed:
            crash = font.render("CRASHED - Respawning from checkpoint...", True, (200, 20, 20))
            screen.blit(crash, (SCREEN_WIDTH // 2 - crash.get_width() // 2, 110))
        elif bike.win:
            win = font.render("FINISH! All coins collected - Press R to replay", True, (10, 120, 10))
            screen.blit(win, (SCREEN_WIDTH // 2 - win.get_width() // 2, 110))
        elif bike.x >= finish_x - 30 and collected < total_coins:
            need = font.render("Collect all coins before finishing", True, (120, 70, 0))
            screen.blit(need, (SCREEN_WIDTH // 2 - need.get_width() // 2, 110))

        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
