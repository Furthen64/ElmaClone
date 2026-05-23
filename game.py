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


def draw_terrain(screen: pygame.Surface, terrain: list[tuple[float, float]], camera_x: float) -> None:
    poly = []
    for x, y in terrain:
        sx = int(x - camera_x)
        if sx < -120 or sx > SCREEN_WIDTH + 120:
            continue
        poly.append((sx, int(y)))
    if len(poly) >= 2:
        pygame.draw.lines(screen, (83, 54, 36), False, poly, 5)
        fill = poly + [(poly[-1][0], SCREEN_HEIGHT), (poly[0][0], SCREEN_HEIGHT)]
        pygame.draw.polygon(screen, (124, 82, 52), fill)


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
            pygame.draw.circle(screen, (245, 205, 40), (cx, cy), COIN_RADIUS)
            pygame.draw.circle(screen, (255, 240, 140), (cx, cy), 6)

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

    def reset_level_state() -> None:
        nonlocal checkpoint_spawn_x, crash_timer
        checkpoint_spawn_x = level["start_x"]
        for coin in coins:
            coin["collected"] = False
        for checkpoint in checkpoints:
            checkpoint["active"] = False
        bike.reset(level["start_x"])
        crash_timer = 0.0

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
            bike.win = True

        camera_x = clamp(bike.x - SCREEN_WIDTH * 0.35, 0.0, max(finish_x - SCREEN_WIDTH, 0.0))

        screen.fill((130, 190, 255))
        draw_terrain(screen, terrain, camera_x)
        draw_collectibles(screen, coins, checkpoints, terrain, camera_x)
        bike.draw(screen, camera_x)

        finish_screen_x = int(finish_x - camera_x)
        pygame.draw.line(screen, (255, 255, 255), (finish_screen_x, 0), (finish_screen_x, SCREEN_HEIGHT), 3)

        speed_text = font.render(f"Speed: {int(bike.vx)}", True, (20, 20, 30))
        coins_text = font.render(f"Coins: {collected}/{total_coins}", True, (20, 20, 30))
        screen.blit(speed_text, (20, 16))
        screen.blit(coins_text, (20, 48))

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
