import math
import random
import sys

import pygame


SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
GRAVITY = 1800.0
LEVEL_LENGTH = 6000
TERRAIN_STEP = 80
BIKE_RADIUS = 20
START_X = 140.0


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def generate_terrain() -> list[tuple[float, float]]:
    random.seed(64)
    points: list[tuple[float, float]] = []
    height = SCREEN_HEIGHT * 0.75
    x = 0
    while x <= LEVEL_LENGTH:
        height += random.uniform(-48, 48)
        height = clamp(height, SCREEN_HEIGHT * 0.48, SCREEN_HEIGHT * 0.9)
        points.append((float(x), float(height)))
        x += TERRAIN_STEP
    if points[-1][0] < LEVEL_LENGTH:
        points.append((float(LEVEL_LENGTH), points[-1][1]))
    return points


def terrain_height_at(points: list[tuple[float, float]], x: float) -> float:
    if x <= points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]
    segment = int(x // TERRAIN_STEP)
    segment = clamp(segment, 0, len(points) - 2)
    i = int(segment)
    x1, y1 = points[i]
    x2, y2 = points[i + 1]
    t = (x - x1) / (x2 - x1)
    return y1 + (y2 - y1) * t


class Bike:
    def __init__(self, terrain: list[tuple[float, float]]) -> None:
        self.terrain = terrain
        self.reset()

    def reset(self) -> None:
        self.x = START_X
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
        self.x = clamp(self.x, 0.0, LEVEL_LENGTH)

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

        if self.x >= LEVEL_LENGTH - 30 and not self.crashed:
            self.win = True

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
        if sx < -TERRAIN_STEP or sx > SCREEN_WIDTH + TERRAIN_STEP:
            continue
        poly.append((sx, int(y)))
    if len(poly) >= 2:
        pygame.draw.lines(screen, (83, 54, 36), False, poly, 5)
        fill = poly + [(poly[-1][0], SCREEN_HEIGHT), (poly[0][0], SCREEN_HEIGHT)]
        pygame.draw.polygon(screen, (124, 82, 52), fill)


def main() -> int:
    pygame.init()
    pygame.display.set_caption("ElmaClone - v1")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 24)
    small_font = pygame.font.SysFont("consolas", 20)

    terrain = generate_terrain()
    bike = Bike(terrain)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                bike.reset()

        keys = pygame.key.get_pressed()
        bike.update(dt, keys)

        camera_x = clamp(bike.x - SCREEN_WIDTH * 0.35, 0.0, LEVEL_LENGTH - SCREEN_WIDTH)

        screen.fill((130, 190, 255))
        draw_terrain(screen, terrain, camera_x)
        bike.draw(screen, camera_x)

        finish_x = int(LEVEL_LENGTH - camera_x)
        pygame.draw.line(screen, (255, 255, 255), (finish_x, 0), (finish_x, SCREEN_HEIGHT), 3)

        speed_text = font.render(f"Speed: {int(bike.vx)}", True, (20, 20, 30))
        screen.blit(speed_text, (20, 16))
        controls = small_font.render(
            "LEFT/RIGHT move  UP/DOWN tilt  SPACE jump  R restart",
            True,
            (20, 20, 30),
        )
        screen.blit(controls, (20, 48))

        if bike.crashed:
            crash = font.render("CRASHED - Press R to restart", True, (200, 20, 20))
            screen.blit(crash, (SCREEN_WIDTH // 2 - crash.get_width() // 2, 80))
        elif bike.win:
            win = font.render("FINISH! Press R to play again", True, (10, 120, 10))
            screen.blit(win, (SCREEN_WIDTH // 2 - win.get_width() // 2, 80))

        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
