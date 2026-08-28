import math

import pygame

from level import terrain_height_at
from settings import CHECKPOINT_RADIUS, COIN_RADIUS, SCREEN_HEIGHT, SCREEN_WIDTH


def format_race_time(milliseconds: int) -> str:
    total_cs = max(0, milliseconds // 10)
    minutes = total_cs // 6000
    seconds = (total_cs % 6000) // 100
    centiseconds = total_cs % 100
    return f"{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def draw_bike_visual(
    screen: pygame.Surface,
    center: tuple[int, int],
    angle: float,
    frame_color: tuple[int, int, int],
    front_compression: float = 0.0,
    rear_compression: float = 0.0,
    scale: float = 1.0,
    facing: float = 1.0,
) -> None:
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    def rot(off_x: float, off_y: float) -> tuple[int, int]:
        local_x = off_x * facing
        rx = local_x * cos_a - off_y * sin_a
        ry = local_x * sin_a + off_y * cos_a
        return int(center[0] + rx), int(center[1] + ry)

    def draw_suspension(top: tuple[int, int], bottom: tuple[int, int], width: int) -> None:
        pygame.draw.line(screen, (192, 196, 205), top, bottom, width)
        dx = bottom[0] - top[0]
        dy = bottom[1] - top[1]
        length = math.hypot(dx, dy)
        if length < 1:
            return
        perp_x = -dy / length
        perp_y = dx / length
        spring_radius = max(1, int(1.8 * scale))
        spring_offset = 2.3 * scale
        for index in range(6):
            t = (index + 1) / 7
            base_x = top[0] + dx * t
            base_y = top[1] + dy * t
            offset = spring_offset if index % 2 == 0 else -spring_offset
            spring_pos = (
                int(base_x + perp_x * offset),
                int(base_y + perp_y * offset),
            )
            pygame.draw.circle(screen, (80, 84, 94), spring_pos, spring_radius)

    wheel_offset_x = 34 * scale
    wheel_offset_y = 18 * scale
    wheel_radius = max(10, int(17 * scale))
    rim_radius = max(5, int(wheel_radius * 0.58))
    tube_width = max(3, int(5 * scale))
    bar_width = max(2, int(3 * scale))

    rear_comp = max(0.0, rear_compression) * scale
    front_comp = max(0.0, front_compression) * scale
    rear = rot(-wheel_offset_x, wheel_offset_y - rear_comp)
    front = rot(wheel_offset_x, wheel_offset_y - front_comp)
    body = rot(0, -14 * scale)
    seat = rot(-9 * scale, -20 * scale)
    handle = rot(18 * scale, -24 * scale)
    front_fork_top = rot(20 * scale, -18 * scale)
    front_fork_bottom = front
    rear_shock_top = rot(-13 * scale, -15 * scale)
    rear_shock_bottom = rear

    pygame.draw.circle(screen, (22, 22, 22), rear, wheel_radius)
    pygame.draw.circle(screen, (22, 22, 22), front, wheel_radius)
    pygame.draw.circle(screen, (168, 168, 170), rear, rim_radius)
    pygame.draw.circle(screen, (168, 168, 170), front, rim_radius)
    pygame.draw.line(screen, (128, 128, 132), rear, front, bar_width)

    pygame.draw.line(screen, frame_color, rear, body, tube_width)
    pygame.draw.line(screen, frame_color, body, front_fork_top, tube_width)
    pygame.draw.line(screen, frame_color, rear, seat, tube_width)
    pygame.draw.line(screen, frame_color, seat, handle, tube_width)

    draw_suspension(rear_shock_top, rear_shock_bottom, max(2, int(4 * scale)))
    draw_suspension(front_fork_top, front_fork_bottom, max(2, int(4 * scale)))

    hip = rot(-2 * scale, -28 * scale)
    shoulder = rot(4 * scale, -44 * scale)
    head = rot(8 * scale, -56 * scale)
    rear_foot = rot(-20 * scale, 1 * scale)
    front_foot = rot(6 * scale, 3 * scale)
    rear_hand = rot(8 * scale, -32 * scale)
    front_hand = rot(20 * scale, -25 * scale)

    pygame.draw.line(screen, (25, 25, 30), hip, shoulder, max(4, int(6 * scale)))
    pygame.draw.line(screen, (35, 35, 42), hip, rear_foot, max(3, int(5 * scale)))
    pygame.draw.line(screen, (35, 35, 42), hip, front_foot, max(3, int(5 * scale)))
    pygame.draw.line(screen, (25, 25, 30), shoulder, rear_hand, max(2, int(4 * scale)))
    pygame.draw.line(screen, (25, 25, 30), shoulder, front_hand, max(2, int(4 * scale)))

    helmet_radius = max(6, int(8 * scale))
    pygame.draw.circle(screen, (205, 212, 235), head, helmet_radius)
    pygame.draw.circle(
        screen,
        (86, 120, 180),
        (head[0] + int(helmet_radius * 0.35), head[1] + int(helmet_radius * 0.1)),
        max(3, int(helmet_radius * 0.45)),
    )
    glove_radius = max(2, int(3 * scale))
    pygame.draw.circle(screen, (240, 70, 70), rear_hand, glove_radius)
    pygame.draw.circle(screen, (240, 70, 70), front_hand, glove_radius)


def draw_sky(
    screen: pygame.Surface,
    animation_time: float,
    sky_top: tuple[int, int, int] | None = None,
    sky_bot: tuple[int, int, int] | None = None,
) -> None:
    if sky_top is not None and sky_bot is not None:
        for y in range(SCREEN_HEIGHT):
            t = y / SCREEN_HEIGHT
            r = int(sky_top[0] * (1 - t) + sky_bot[0] * t)
            g = int(sky_top[1] * (1 - t) + sky_bot[1] * t)
            b = int(sky_top[2] * (1 - t) + sky_bot[2] * t)
            pygame.draw.line(screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))
    else:
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


def draw_weather_overlays(
    screen: pygame.Surface,
    weather: "WeatherSystem",
    camera_x: float,
    camera_y: float,
    bike_screen_x: float,
    bike_screen_y: float,
    facing_right: bool,
) -> None:
    from weather import WeatherSystem

    if not isinstance(weather, WeatherSystem):
        return

    weather.set_camera_x(camera_x)
    weather.draw_stars(screen, weather.darkness)
    weather.draw_particles(screen)
    weather.draw_fog_overlay(screen, camera_x, camera_y)
    weather.draw_night_overlay(screen)
    weather.draw_headlight(screen, bike_screen_x, bike_screen_y, facing_right)


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


def draw_menu_screen(
    screen: pygame.Surface,
    title_font: pygame.font.Font,
    body_font: pygame.font.Font,
    level_name: str,
) -> None:
    draw_sky(screen, pygame.time.get_ticks() / 1000.0)
    title = title_font.render("ElmaClone", True, (255, 255, 255))
    subtitle = body_font.render("Main Menu", True, (240, 245, 255))
    options = [
        "ENTER - Start ride",
        f"L - Change level ({level_name})",
        "D - Design your bike",
        "ESC - Quit",
    ]
    panel = pygame.Surface((620, 330), pygame.SRCALPHA)
    panel.fill((10, 20, 40, 150))
    panel_x = SCREEN_WIDTH // 2 - panel.get_width() // 2
    panel_y = SCREEN_HEIGHT // 2 - panel.get_height() // 2
    screen.blit(panel, (panel_x, panel_y))
    screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, panel_y + 35))
    screen.blit(subtitle, (SCREEN_WIDTH // 2 - subtitle.get_width() // 2, panel_y + 95))

    for index, option in enumerate(options):
        text = body_font.render(option, True, (230, 235, 250))
        screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, panel_y + 145 + index * 36))


def draw_design_screen(
    screen: pygame.Surface,
    title_font: pygame.font.Font,
    body_font: pygame.font.Font,
    color_name: str,
    color_value: tuple[int, int, int],
    dampening_name: str,
) -> None:
    draw_sky(screen, pygame.time.get_ticks() / 1000.0)
    panel = pygame.Surface((700, 380), pygame.SRCALPHA)
    panel.fill((10, 20, 40, 160))
    panel_x = SCREEN_WIDTH // 2 - panel.get_width() // 2
    panel_y = SCREEN_HEIGHT // 2 - panel.get_height() // 2
    screen.blit(panel, (panel_x, panel_y))

    title = title_font.render("Design your bike", True, (255, 255, 255))
    screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, panel_y + 28))

    color_text = body_font.render(f"Color: {color_name}", True, (235, 240, 250))
    damp_text = body_font.render(f"Dampening: {dampening_name}", True, (235, 240, 250))
    screen.blit(color_text, (panel_x + 50, panel_y + 108))
    screen.blit(damp_text, (panel_x + 50, panel_y + 150))

    preview_center_x = SCREEN_WIDTH // 2
    preview_center_y = panel_y + 245
    draw_bike_visual(
        screen,
        (preview_center_x, preview_center_y),
        -0.08,
        color_value,
        scale=1.35,
    )

    controls = [
        "LEFT/RIGHT - Change color",
        "UP/DOWN - Change dampening",
        "ENTER or ESC - Back to menu",
    ]
    for index, line in enumerate(controls):
        text = body_font.render(line, True, (220, 230, 245))
        screen.blit(text, (panel_x + 50, panel_y + 292 + index * 26))


def draw_level_complete_screen(
    screen: pygame.Surface,
    title_font: pygame.font.Font,
    body_font: pygame.font.Font,
    level_name: str,
    time_ms: int,
    apples: int,
    total_apples: int,
    deaths: int,
) -> None:
    draw_sky(screen, pygame.time.get_ticks() / 1000.0)
    panel = pygame.Surface((680, 380), pygame.SRCALPHA)
    panel.fill((10, 20, 40, 165))
    panel_x = SCREEN_WIDTH // 2 - panel.get_width() // 2
    panel_y = SCREEN_HEIGHT // 2 - panel.get_height() // 2
    screen.blit(panel, (panel_x, panel_y))

    title = title_font.render("Level Complete!", True, (120, 230, 120))
    screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, panel_y + 28))

    level_text = body_font.render(level_name, True, (235, 240, 250))
    screen.blit(level_text, (SCREEN_WIDTH // 2 - level_text.get_width() // 2, panel_y + 92))

    time_text = body_font.render(f"Time: {format_race_time(time_ms)}", True, (240, 245, 255))
    apples_text = body_font.render(f"Apples: {apples}/{total_apples}", True, (240, 245, 255))
    deaths_text = body_font.render(f"Deaths: {deaths}", True, (240, 245, 255))
    screen.blit(time_text, (SCREEN_WIDTH // 2 - time_text.get_width() // 2, panel_y + 152))
    screen.blit(apples_text, (SCREEN_WIDTH // 2 - apples_text.get_width() // 2, panel_y + 192))
    screen.blit(deaths_text, (SCREEN_WIDTH // 2 - deaths_text.get_width() // 2, panel_y + 232))

    continue_text = body_font.render("ENTER - Next level", True, (150, 220, 150))
    menu_text = body_font.render("ESC - Menu", True, (200, 205, 220))
    screen.blit(continue_text, (SCREEN_WIDTH // 2 - continue_text.get_width() // 2, panel_y + 292))
    screen.blit(menu_text, (SCREEN_WIDTH // 2 - menu_text.get_width() // 2, panel_y + 324))
